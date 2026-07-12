from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import stat
from collections.abc import Iterable, Mapping
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any, Iterator


INDEX_SCHEMA_VERSION = "nac.business-case-type-migration-quarantine-index/v0.1"
_RECORD_ID = re.compile(r"[0-9a-f]{64}")
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_READ_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
    | getattr(os, "O_CLOEXEC", 0)
)
_MAX_RECORD_BYTES = 16 * 1024
_MAX_INDEX_BYTES = 32 * 1024 * 1024
_MAX_DIRECTORY_ENTRIES = 100_128
_LOCK_FLAGS = (
    os.O_RDWR
    | getattr(os, "O_CLOEXEC", 0)
    | getattr(os, "O_NOFOLLOW", 0)
    | getattr(os, "O_NONBLOCK", 0)
)
_LOCK_NAME = ".quarantine.lock"


class ArtifactWriteError(RuntimeError):
    """Fixed fail-closed error exposed by local artifact persistence."""

    def __init__(self) -> None:
        super().__init__("artifact_write_failed")


def canonical_contained_path(path: Path | str, *, root: Path | str) -> Path:
    """Return a lexical path below root after verifying existing components by FD."""

    try:
        candidate = _normalized_absolute(path)
        boundary = _normalized_absolute(root)
        if candidate == boundary:
            raise ArtifactWriteError()
        candidate.relative_to(boundary)
        _verify_existing_directory_components(boundary)
        _verify_existing_directory_components(candidate.parent)
        _reject_final_symlink(candidate)
        return candidate
    except ArtifactWriteError:
        raise
    except (OSError, RuntimeError, ValueError):
        raise ArtifactWriteError() from None


class QuarantineStore:
    """Persistent append-only local quarantine with a reconstructable index."""

    def __init__(self, state_dir: Path | str) -> None:
        self.state_dir = _normalized_absolute(state_dir)
        self.records_dir = self.state_dir / "records"
        self.index_path = self.state_dir / "index.json"
        self._lock = RLock()

    def reconcile(self) -> dict[str, Any]:
        """Validate indexed records, recover complete orphans, and replace the index."""

        with self._lock:
            try:
                with self._open_store() as (state_fd, records_fd):
                    return self._reconcile_open(state_fd, records_fd)
            except ArtifactWriteError:
                raise
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                raise ArtifactWriteError() from None

    def persist(self, records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        """Publish records and release the filesystem lock after reconciliation."""

        with self.persist_locked(records) as index:
            return index

    @contextmanager
    def persist_locked(
        self,
        records: Iterable[Mapping[str, Any]],
    ) -> Iterator[dict[str, Any]]:
        """Publish records and hold both locks while the caller commits related output."""

        with self._lock:
            store_context = self._open_store()
            try:
                state_fd, records_fd = store_context.__enter__()
            except (
                ArtifactWriteError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ):
                raise ArtifactWriteError() from None
            try:
                try:
                    self._reconcile_open(state_fd, records_fd)
                    for record in records:
                        if not isinstance(record, Mapping):
                            raise ArtifactWriteError()
                        record_id = record.get("record_id")
                        if (
                            not isinstance(record_id, str)
                            or _RECORD_ID.fullmatch(record_id) is None
                        ):
                            raise ArtifactWriteError()
                        self._publish_record(
                            records_fd,
                            record_id,
                            _canonical_json_bytes(dict(record)),
                        )
                    index = self._reconcile_open(state_fd, records_fd)
                except ArtifactWriteError:
                    raise
                except (OSError, TypeError, ValueError, json.JSONDecodeError):
                    raise ArtifactWriteError() from None
                yield index
            finally:
                store_context.__exit__(None, None, None)

    def store_record(self, record_id: str, record: Mapping[str, Any]) -> dict[str, Any]:
        """Compatibility-friendly singular API; the domain remains the ID authority."""

        if record.get("record_id") != record_id:
            raise ArtifactWriteError()
        return self.persist((record,))

    @contextmanager
    def _open_store(self) -> Iterator[tuple[int, int]]:
        state_fd = _open_absolute_directory(self.state_dir, create=True)
        lock_fd = -1
        try:
            lock_fd = _open_exclusive_lock_at(state_fd, _LOCK_NAME)
            _reconcile_previous_at(state_fd, "index.json")
            records_fd = _open_child_directory(state_fd, "records", create=True)
            try:
                yield state_fd, records_fd
            finally:
                os.close(records_fd)
        finally:
            if lock_fd >= 0:
                os.close(lock_fd)
            os.close(state_fd)

    def _reconcile_open(self, state_fd: int, records_fd: int) -> dict[str, Any]:
        indexed_ids = self._read_index_ids(state_fd)
        disk_ids = self._read_all_records(records_fd)
        if not indexed_ids.issubset(disk_ids):
            raise ArtifactWriteError()
        index = self._make_index(disk_ids)
        _atomic_replace_json_at(state_fd, "index.json", index)
        return index

    def _read_index_ids(self, state_fd: int) -> set[str]:
        raw = _read_regular_file_at(
            state_fd,
            "index.json",
            missing_ok=True,
            max_bytes=_MAX_INDEX_BYTES,
        )
        if raw is None:
            return set()
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"schema_version", "records"}:
            raise ArtifactWriteError()
        records = value.get("records")
        if value.get("schema_version") != INDEX_SCHEMA_VERSION or not isinstance(records, list):
            raise ArtifactWriteError()
        ids: list[str] = []
        for item in records:
            if not isinstance(item, dict) or set(item) != {"record_id", "path"}:
                raise ArtifactWriteError()
            record_id = item.get("record_id")
            if (
                not isinstance(record_id, str)
                or _RECORD_ID.fullmatch(record_id) is None
                or item.get("path") != f"records/{record_id}.json"
            ):
                raise ArtifactWriteError()
            ids.append(record_id)
        if ids != sorted(set(ids)):
            raise ArtifactWriteError()
        return set(ids)

    def _read_all_records(self, records_fd: int) -> set[str]:
        result: set[str] = set()
        entry_count = 0
        with os.scandir(records_fd) as entries:
            for entry in entries:
                entry_count += 1
                if entry_count > _MAX_DIRECTORY_ENTRIES:
                    raise ArtifactWriteError()
                name = entry.name
                if name.startswith(".tmp-"):
                    _require_regular_entry(records_fd, name)
                    continue
                if not name.endswith(".json"):
                    raise ArtifactWriteError()
                record_id = name[:-5]
                if _RECORD_ID.fullmatch(record_id) is None:
                    raise ArtifactWriteError()
                self._read_record(records_fd, record_id)
                result.add(record_id)
        return result

    def _read_record(self, records_fd: int, record_id: str) -> bytes:
        raw = _read_regular_file_at(
            records_fd,
            f"{record_id}.json",
            max_bytes=_MAX_RECORD_BYTES,
        )
        assert raw is not None
        value = json.loads(raw)
        if not isinstance(value, dict) or value.get("record_id") != record_id:
            raise ArtifactWriteError()
        if raw != _canonical_json_bytes(value):
            raise ArtifactWriteError()
        return raw

    def _publish_record(self, records_fd: int, record_id: str, payload: bytes) -> None:
        target = f"{record_id}.json"
        temporary = _write_temporary_at(records_fd, payload)
        try:
            try:
                os.link(
                    temporary,
                    target,
                    src_dir_fd=records_fd,
                    dst_dir_fd=records_fd,
                    follow_symlinks=False,
                )
                os.fsync(records_fd)
            except FileExistsError:
                if self._read_record(records_fd, record_id) != payload:
                    raise ArtifactWriteError()
            if self._read_record(records_fd, record_id) != payload:
                raise ArtifactWriteError()
        finally:
            try:
                os.unlink(temporary, dir_fd=records_fd)
                os.fsync(records_fd)
            except FileNotFoundError:
                pass

    @staticmethod
    def _make_index(record_ids: set[str]) -> dict[str, Any]:
        return {
            "schema_version": INDEX_SCHEMA_VERSION,
            "records": [
                {"record_id": record_id, "path": f"records/{record_id}.json"}
                for record_id in sorted(record_ids)
            ],
        }


def write_redacted_output(
    output_path: Path | str,
    payload: Mapping[str, Any],
    *,
    allowed_root: Path | str | None = None,
) -> None:
    """Atomically replace a redacted output while retaining the old file on failure."""

    try:
        output = _normalized_absolute(output_path)
        boundary = _normalized_absolute(allowed_root) if allowed_root is not None else output.parent
        output = canonical_contained_path(output, root=boundary)
        relative = output.relative_to(boundary)
        boundary_fd = _open_absolute_directory(boundary, create=True)
        try:
            parent_fd = _open_relative_directory(
                boundary_fd,
                relative.parts[:-1],
                create=True,
            )
            lock_fd = -1
            try:
                lock_fd = _open_exclusive_lock_at(
                    parent_fd,
                    _lock_name(relative.name),
                )
                _reconcile_previous_at(parent_fd, relative.name)
                _atomic_replace_json_at(parent_fd, relative.name, dict(payload))
            finally:
                if lock_fd >= 0:
                    os.close(lock_fd)
                os.close(parent_fd)
        finally:
            os.close(boundary_fd)
    except ArtifactWriteError:
        raise
    except (OSError, TypeError, ValueError):
        raise ArtifactWriteError() from None


def _atomic_replace_json_at(parent_fd: int, name: str, value: Any) -> None:
    prior = _regular_entry_stat(parent_fd, name, missing_ok=True)
    previous = _previous_name(name)
    temporary = _write_temporary_at(parent_fd, _canonical_json_bytes(value))
    replacement_stat = os.stat(temporary, dir_fd=parent_fd, follow_symlinks=False)
    previous_created = False
    try:
        if prior is not None:
            _link_previous_at(parent_fd, name, previous, prior)
            previous_created = True
            os.fsync(parent_fd)

        try:
            os.replace(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
            temporary = ""
            os.fsync(parent_fd)
        except BaseException:
            if previous_created and _entry_matches(parent_fd, name, replacement_stat):
                try:
                    os.replace(
                        previous,
                        name,
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                    )
                    previous_created = False
                    os.fsync(parent_fd)
                except OSError:
                    pass
            elif (
                previous_created
                and prior is not None
                and _entry_matches(parent_fd, name, prior)
            ):
                try:
                    os.unlink(previous, dir_fd=parent_fd)
                    previous_created = False
                    os.fsync(parent_fd)
                except OSError:
                    pass
            elif prior is None and _entry_matches(parent_fd, name, replacement_stat):
                try:
                    os.unlink(name, dir_fd=parent_fd)
                    os.fsync(parent_fd)
                except OSError:
                    pass
            raise

        # The replacement is durable; declared recovery-marker cleanup is best-effort.
        if previous_created:
            try:
                os.unlink(previous, dir_fd=parent_fd)
            except OSError:
                pass
            else:
                previous_created = False
                try:
                    os.fsync(parent_fd)
                except OSError:
                    pass
    finally:
        if temporary:
            try:
                os.unlink(temporary, dir_fd=parent_fd)
            except FileNotFoundError:
                pass


def _link_previous_at(
    parent_fd: int,
    name: str,
    previous: str,
    expected: os.stat_result,
) -> None:
    try:
        os.link(
            name,
            previous,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
    except FileExistsError:
        raise ArtifactWriteError() from None

    try:
        previous_stat = _regular_entry_stat(parent_fd, previous)
        current = _regular_entry_stat(parent_fd, name)
        assert previous_stat is not None and current is not None
        expected_identity = (expected.st_dev, expected.st_ino)
        if (
            (previous_stat.st_dev, previous_stat.st_ino) != expected_identity
            or (current.st_dev, current.st_ino) != expected_identity
        ):
            raise ArtifactWriteError()
    except BaseException:
        try:
            os.unlink(previous, dir_fd=parent_fd)
        except OSError:
            pass
        raise


def _reconcile_previous_at(parent_fd: int, name: str) -> None:
    previous = _previous_name(name)
    previous_stat = _regular_entry_stat(parent_fd, previous, missing_ok=True)
    if previous_stat is None:
        return
    target = _regular_entry_stat(parent_fd, name, missing_ok=True)
    if target is None:
        os.replace(
            previous,
            name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
    else:
        os.unlink(previous, dir_fd=parent_fd)
    os.fsync(parent_fd)


def _lock_name(name: str) -> str:
    return f".{name}.lock"


def _previous_name(name: str) -> str:
    return f".{name}.previous"


def _entry_matches(parent_fd: int, name: str, expected: os.stat_result) -> bool:
    try:
        current = _regular_entry_stat(parent_fd, name)
    except (ArtifactWriteError, OSError):
        return False
    return current is not None and (current.st_dev, current.st_ino) == (
        expected.st_dev,
        expected.st_ino,
    )


def _open_exclusive_lock_at(parent_fd: int, name: str) -> int:
    created = False
    try:
        try:
            descriptor = os.open(
                name,
                _LOCK_FLAGS | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=parent_fd,
            )
            created = True
        except FileExistsError:
            descriptor = os.open(name, _LOCK_FLAGS, dir_fd=parent_fd)
    except OSError:
        raise ArtifactWriteError() from None

    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise ArtifactWriteError()
        if created:
            os.fsync(parent_fd)
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        current = _regular_entry_stat(parent_fd, name)
        if current is None or current.st_nlink != 1 or (
            current.st_dev,
            current.st_ino,
        ) != (opened.st_dev, opened.st_ino):
            raise ArtifactWriteError()
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _write_temporary_at(parent_fd: int, payload: bytes) -> str:
    for _ in range(128):
        name = f".tmp-{secrets.token_hex(16)}"
        try:
            descriptor = os.open(
                name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=parent_fd,
            )
            break
        except FileExistsError:
            continue
    else:
        raise ArtifactWriteError()
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            os.unlink(name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    return name


def _read_regular_file_at(
    parent_fd: int,
    name: str,
    *,
    missing_ok: bool = False,
    max_bytes: int = _MAX_RECORD_BYTES,
) -> bytes | None:
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ArtifactWriteError()
    try:
        descriptor = os.open(name, _READ_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > max_bytes:
            raise ArtifactWriteError()
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ArtifactWriteError()
        return b"".join(chunks)
    finally:
        os.close(descriptor)

def _require_regular_entry(parent_fd: int, name: str, *, missing_ok: bool = False) -> None:
    _regular_entry_stat(parent_fd, name, missing_ok=missing_ok)


def _regular_entry_stat(
    parent_fd: int,
    name: str,
    *,
    missing_ok: bool = False,
) -> os.stat_result | None:
    try:
        result = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        if missing_ok:
            return None
        raise
    if not stat.S_ISREG(result.st_mode):
        raise ArtifactWriteError()
    return result


def _open_absolute_directory(path: Path, *, create: bool) -> int:
    if not path.is_absolute():
        raise ArtifactWriteError()
    descriptor = os.open(path.anchor, _DIRECTORY_FLAGS)
    try:
        for component in path.parts[1:]:
            next_descriptor = _open_child_directory(descriptor, component, create=create)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_relative_directory(parent_fd: int, components: tuple[str, ...], *, create: bool) -> int:
    descriptor = os.dup(parent_fd)
    try:
        for component in components:
            next_descriptor = _open_child_directory(descriptor, component, create=create)
            os.close(descriptor)
            descriptor = next_descriptor
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_child_directory(parent_fd: int, name: str, *, create: bool) -> int:
    if name in {"", ".", ".."} or os.sep in name:
        raise ArtifactWriteError()
    try:
        return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError:
        if not create:
            raise
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
            os.fsync(parent_fd)
        except FileExistsError:
            pass
        return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)


def _verify_existing_directory_components(path: Path) -> None:
    descriptor = os.open(path.anchor, _DIRECTORY_FLAGS)
    try:
        for component in path.parts[1:]:
            try:
                next_descriptor = _open_child_directory(descriptor, component, create=False)
            except FileNotFoundError:
                return
            os.close(descriptor)
            descriptor = next_descriptor
    finally:
        os.close(descriptor)


def _reject_final_symlink(path: Path) -> None:
    try:
        parent_fd = _open_absolute_directory(path.parent, create=False)
    except FileNotFoundError:
        return
    try:
        try:
            mode = os.stat(path.name, dir_fd=parent_fd, follow_symlinks=False).st_mode
        except FileNotFoundError:
            return
        if stat.S_ISLNK(mode):
            raise ArtifactWriteError()
    finally:
        os.close(parent_fd)


def _normalized_absolute(path: Path | str) -> Path:
    return Path(os.path.normpath(os.fspath(Path(path).absolute())))


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
