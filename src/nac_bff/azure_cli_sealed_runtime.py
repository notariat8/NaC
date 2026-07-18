from __future__ import annotations

import fcntl
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import stat
import zipfile


_CHUNK_SIZE = 1024 * 1024
_TAMPER_EXIT = 86
_ISOLATION_EXIT = 87


@dataclass(slots=True)
class SealedAzureCliRuntime:
    interpreter_fd: int
    bootstrap_fd: int
    manifest_fd: int
    package_fd: int
    _closed: bool = False

    @property
    def pass_fds(self) -> tuple[int, int, int, int]:
        return (
            self.interpreter_fd,
            self.bootstrap_fd,
            self.manifest_fd,
            self.package_fd,
        )

    def command(self, azure_argv: list[str]) -> list[str]:
        return [
            f"/proc/self/fd/{self.interpreter_fd}",
            "-I",
            "-B",
            f"/proc/self/fd/{self.bootstrap_fd}",
            f"/proc/self/fd/{self.manifest_fd}",
            f"/proc/self/fd/{self.package_fd}",
            *azure_argv,
        ]

    def close(self) -> None:
        if self._closed:
            return
        for attribute in (
            "interpreter_fd",
            "bootstrap_fd",
            "manifest_fd",
            "package_fd",
        ):
            descriptor = getattr(self, attribute)
            try:
                os.close(descriptor)
            except OSError:
                pass
            setattr(self, attribute, -1)
        self._closed = True

    def __enter__(self) -> SealedAzureCliRuntime:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


def prepare_sealed_azure_cli_runtime(
    *,
    package_root: Path,
    package_digest: str,
    interpreter_path: Path,
    interpreter_digest: str,
    allowed_uids: set[int],
    cloud_selection_sha256: str | None,
) -> SealedAzureCliRuntime | None:
    """Bind executable bytes and a complete package manifest to sealed memfds."""

    manifest = _package_manifest(package_root, allowed_uids=allowed_uids)
    if manifest is None or manifest[0] != package_digest:
        return None
    tree_digest, payload = manifest
    payload["tree_digest"] = tree_digest
    if cloud_selection_sha256 is not None and (
        not isinstance(cloud_selection_sha256, str)
        or len(cloud_selection_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in cloud_selection_sha256
        )
    ):
        return None
    payload["cloud_selection_sha256"] = cloud_selection_sha256

    interpreter = _read_regular_file(
        interpreter_path,
        allowed_uids={0},
        executable=True,
    )
    if (
        interpreter is None
        or hashlib.sha256(interpreter).hexdigest() != interpreter_digest
    ):
        return None

    package_fd = _sealed_package_memfd(
        package_root,
        payload,
        tree_digest=tree_digest,
        allowed_uids=allowed_uids,
    )
    if package_fd is None:
        return None
    payload.pop("source_root", None)

    descriptors: list[int] = [package_fd]
    try:
        interpreter_fd = _sealed_memfd(
            "nac-azure-cli-python",
            interpreter,
            executable=True,
        )
        descriptors.append(interpreter_fd)
        bootstrap_fd = _sealed_memfd(
            "nac-azure-cli-bootstrap",
            _BOOTSTRAP_SOURCE.encode("utf-8"),
            executable=False,
        )
        descriptors.append(bootstrap_fd)
        manifest_fd = _sealed_memfd(
            "nac-azure-cli-manifest",
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            executable=False,
        )
        descriptors.append(manifest_fd)
    except (OSError, ValueError):
        for descriptor in descriptors:
            os.close(descriptor)
        return None
    return SealedAzureCliRuntime(
        interpreter_fd=interpreter_fd,
        bootstrap_fd=bootstrap_fd,
        manifest_fd=manifest_fd,
        package_fd=package_fd,
    )


def sealed_runtime_failure_code(returncode: int) -> str | None:
    if returncode == _TAMPER_EXIT:
        return "AZURE_CLI_RUNTIME_TAMPERED"
    if returncode == _ISOLATION_EXIT:
        return "AZURE_CLI_RUNTIME_ISOLATION_UNAVAILABLE"
    return None


def _package_manifest(
    root: Path,
    *,
    allowed_uids: set[int],
) -> tuple[str, dict[str, object]] | None:
    if not _trusted_directory(root, allowed_uids=allowed_uids):
        return None
    digest = hashlib.sha256()
    directories: list[dict[str, object]] = []
    files: list[dict[str, object]] = []
    snapshots: list[tuple[Path, tuple[int, ...]]] = []
    try:
        for current_text, child_directories, child_files in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            current = Path(current_text)
            current_metadata = current.lstat()
            if not _trusted_directory(current, allowed_uids=allowed_uids):
                return None
            snapshots.append((current, _stat_signature(current_metadata)))
            child_directories.sort()
            child_files.sort()
            for name in child_directories:
                child = current / name
                metadata = child.lstat()
                if not _trusted_directory(child, allowed_uids=allowed_uids):
                    return None
                relative = child.relative_to(root).as_posix()
                mode = stat.S_IMODE(metadata.st_mode)
                _digest_update(
                    digest,
                    "directory",
                    relative,
                    str(metadata.st_uid),
                    oct(mode),
                )
                directories.append(
                    {"path": relative, "mode": mode, "uid": metadata.st_uid}
                )
            for name in child_files:
                child = current / name
                metadata = child.lstat()
                content = _read_regular_file(child, allowed_uids=allowed_uids)
                if content is None:
                    return None
                relative = child.relative_to(root).as_posix()
                mode = stat.S_IMODE(metadata.st_mode)
                content_digest = hashlib.sha256(content).hexdigest()
                _digest_update(
                    digest,
                    "file",
                    relative,
                    str(metadata.st_uid),
                    oct(mode),
                    content_digest,
                )
                files.append(
                    {
                        "path": relative,
                        "mode": mode,
                        "uid": metadata.st_uid,
                        "size": len(content),
                        "sha256": content_digest,
                    }
                )
    except (OSError, RuntimeError, ValueError):
        return None
    for directory, signature in snapshots:
        try:
            if _stat_signature(directory.lstat()) != signature:
                return None
        except OSError:
            return None
    return digest.hexdigest(), {
        "schema": "nac-azure-cli-sealed-runtime-v1",
        "source_root": str(root),
        "directories": directories,
        "files": files,
    }


def _read_regular_file(
    path: Path,
    *,
    allowed_uids: set[int],
    executable: bool = False,
) -> bytes | None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        path_before = path.lstat()
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        before = os.fstat(descriptor)
        if (
            stat.S_ISLNK(path_before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_uid not in allowed_uids
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (executable and not before.st_mode & stat.S_IXUSR)
            or (before.st_dev, before.st_ino)
            != (path_before.st_dev, path_before.st_ino)
        ):
            return None
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, _CHUNK_SIZE)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = path.lstat()
    except OSError:
        return None
    if (
        _stat_signature(before) != _stat_signature(after)
        or _stat_signature(after) != _stat_signature(path_after)
    ):
        return None
    return b"".join(chunks)


def _trusted_directory(path: Path, *, allowed_uids: set[int]) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid in allowed_uids
        and not metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )


def _sealed_package_memfd(
    source_root: Path,
    manifest: dict[str, object],
    *,
    tree_digest: str,
    allowed_uids: set[int],
) -> int | None:
    if not hasattr(os, "memfd_create"):
        return None
    descriptor = os.memfd_create(
        "nac-azure-cli-package",
        getattr(os, "MFD_CLOEXEC", 0) | getattr(os, "MFD_ALLOW_SEALING", 0),
    )
    try:
        files = manifest["files"]
        if not isinstance(files, list):
            raise ValueError("invalid package manifest")
        with os.fdopen(os.dup(descriptor), "w+b") as stream:
            with zipfile.ZipFile(
                stream,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            ) as archive:
                seen: set[str] = set()
                for record in files:
                    if not isinstance(record, dict):
                        raise ValueError("invalid file record")
                    relative = str(record["path"])
                    relative_path = PurePosixPath(relative)
                    if (
                        relative_path.is_absolute()
                        or not relative_path.parts
                        or any(part in {"", ".", ".."} for part in relative_path.parts)
                        or relative in seen
                    ):
                        raise ValueError("unsafe package path")
                    seen.add(relative)
                    source = source_root / relative
                    content = _read_regular_file(
                        source,
                        allowed_uids=allowed_uids,
                    )
                    metadata = source.lstat()
                    expected_mode = int(record["mode"])
                    expected_uid = int(record["uid"])
                    expected_size = int(record["size"])
                    expected_sha256 = str(record["sha256"])
                    if (
                        content is None
                        or metadata.st_uid != expected_uid
                        or stat.S_IMODE(metadata.st_mode) != expected_mode
                        or len(content) != expected_size
                        or hashlib.sha256(content).hexdigest() != expected_sha256
                    ):
                        raise OSError("package changed while sealing")
                    archive_info = zipfile.ZipInfo(relative)
                    archive_info.compress_type = zipfile.ZIP_DEFLATED
                    archive_info.external_attr = (expected_mode & ~0o222) << 16
                    archive.writestr(archive_info, content)
        refreshed = _package_manifest(source_root, allowed_uids=allowed_uids)
        if refreshed is None or refreshed[0] != tree_digest:
            raise OSError("package changed after sealing")
        os.fchmod(descriptor, 0o400)
        fcntl.fcntl(
            descriptor,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL,
        )
        os.lseek(descriptor, 0, os.SEEK_SET)
    except (KeyError, OSError, RuntimeError, TypeError, ValueError):
        os.close(descriptor)
        return None
    return descriptor


def _sealed_memfd(name: str, payload: bytes, *, executable: bool) -> int:
    if not hasattr(os, "memfd_create"):
        raise OSError("memfd unavailable")
    descriptor = os.memfd_create(
        name,
        getattr(os, "MFD_CLOEXEC", 0) | getattr(os, "MFD_ALLOW_SEALING", 0),
    )
    try:
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short memfd write")
            view = view[written:]
        os.fchmod(descriptor, 0o500 if executable else 0o400)
        fcntl.fcntl(
            descriptor,
            fcntl.F_ADD_SEALS,
            fcntl.F_SEAL_WRITE
            | fcntl.F_SEAL_GROW
            | fcntl.F_SEAL_SHRINK
            | fcntl.F_SEAL_SEAL,
        )
        os.lseek(descriptor, 0, os.SEEK_SET)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _stat_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _digest_update(digest: object, *values: str) -> None:
    for value in values:
        encoded = value.encode("utf-8", errors="surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)


_BOOTSTRAP_SOURCE = r'''from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import runpy
import select
import signal
import stat
import sys
import tempfile
import time
import zipfile

TAMPER_EXIT = 86
ISOLATION_EXIT = 87
CHUNK_SIZE = 1024 * 1024
MAX_CLOUD_SELECTION_BYTES = 4096
MAX_ACCOUNT_ASSERTION_BYTES = 16384
ACCOUNT_ASSERTION_TIMEOUT_SECONDS = 30.0
EXPECTED_CLOUD_NAME = "AzureCloud"
EXPECTED_TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
EXPECTED_SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
ACCOUNT_ASSERTION_FIELDS = frozenset(
    {"id", "tenantId", "environmentName", "state"}
)
WRITE_COMMAND_PREFIXES = (
    ("provider", "register"),
    ("group", "create"),
    ("deployment", "group", "create"),
    ("functionapp", "deployment", "source", "config-zip"),
)
REQUIRED_APPARMOR_PROFILE = "nac-azure-cli-sealed-runtime (unconfined)"

def fail(code):
    raise SystemExit(code)

def signature(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid, value.st_gid, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

def safe_archive_path(value):
    try:
        candidate = PurePosixPath(value)
    except (TypeError, ValueError):
        return False
    return (
        not candidate.is_absolute()
        and bool(candidate.parts)
        and all(part not in {"", ".", ".."} for part in candidate.parts)
    )

def archive_target(root, value):
    if not safe_archive_path(value):
        fail(TAMPER_EXIT)
    return root.joinpath(*PurePosixPath(value).parts)

def validate_package_archive(archive, records):
    try:
        expected = [record["path"] for record in records]
        infos = archive.infolist()
    except (KeyError, TypeError, ValueError):
        fail(TAMPER_EXIT)
    if (
        len(expected) != len(set(expected))
        or any(not safe_archive_path(value) for value in expected)
        or [info.filename for info in infos] != expected
        or any(
            info.is_dir()
            or info.flag_bits & 0x1
            or info.file_size != record["size"]
            for info, record in zip(infos, records)
        )
    ):
        fail(TAMPER_EXIT)

def copy_archived_verified(archive, destination, record):
    digest = hashlib.sha256()
    size = 0
    try:
        source = archive.open(record["path"], mode="r")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source, destination.open("xb") as output:
            while True:
                chunk = source.read(CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
    except (KeyError, OSError, RuntimeError, ValueError, zipfile.BadZipFile):
        fail(TAMPER_EXIT)
    if size != record["size"] or digest.hexdigest() != record["sha256"]:
        fail(TAMPER_EXIT)
    os.chmod(destination, record["mode"] & ~0o222)

def copy_config_file(source, destination):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        path_before = source.lstat()
        descriptor = os.open(source, flags)
    except OSError:
        fail(TAMPER_EXIT)
    try:
        before = os.fstat(descriptor)
        if (stat.S_ISLNK(path_before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_uid not in {0, os.getuid()} or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or (before.st_dev, before.st_ino) != (path_before.st_dev, path_before.st_ino)):
            fail(TAMPER_EXIT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as output:
            while True:
                chunk = os.read(descriptor, CHUNK_SIZE)
                if not chunk:
                    break
                output.write(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = source.lstat()
    except OSError:
        fail(TAMPER_EXIT)
    if signature(before) != signature(after) or signature(after) != signature(path_after):
        fail(TAMPER_EXIT)
    os.chmod(destination, stat.S_IMODE(before.st_mode) & ~0o022)

def config_file_digest(source):
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        path_before = source.lstat()
        if path_before.st_size > MAX_CLOUD_SELECTION_BYTES:
            fail(TAMPER_EXIT)
        descriptor = os.open(source, flags)
    except OSError:
        fail(TAMPER_EXIT)
    digest = hashlib.sha256()
    try:
        before = os.fstat(descriptor)
        if (stat.S_ISLNK(path_before.st_mode) or not stat.S_ISREG(before.st_mode) or before.st_uid not in {0, os.getuid()} or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH) or before.st_size > MAX_CLOUD_SELECTION_BYTES or (before.st_dev, before.st_ino) != (path_before.st_dev, path_before.st_ino)):
            fail(TAMPER_EXIT)
        while True:
            chunk = os.read(descriptor, CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        path_after = source.lstat()
    except OSError:
        fail(TAMPER_EXIT)
    if signature(before) != signature(after) or signature(after) != signature(path_after):
        fail(TAMPER_EXIT)
    return digest.hexdigest()

def copy_private_azure_config(source, destination, expected_cloud_selection_sha256):
    if not source.is_absolute():
        fail(TAMPER_EXIT)
    try:
        root = source.lstat()
    except FileNotFoundError:
        if expected_cloud_selection_sha256 is not None:
            fail(TAMPER_EXIT)
        return
    except OSError:
        fail(TAMPER_EXIT)
    if stat.S_ISLNK(root.st_mode) or not stat.S_ISDIR(root.st_mode):
        fail(TAMPER_EXIT)
    root_signature = signature(root)
    cloud_selection_seen = False
    for current_text, directories, files in os.walk(source, topdown=True, followlinks=False):
        current = Path(current_text)
        relative = current.relative_to(source)
        directories.sort()
        files.sort()
        for name in directories:
            if relative == Path(".") and name == "clouds.config":
                fail(TAMPER_EXIT)
            metadata = (current / name).lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                fail(TAMPER_EXIT)
            (destination / relative / name).mkdir(parents=True, exist_ok=True)
        for name in files:
            if relative == Path(".") and name == "clouds.config":
                if (
                    expected_cloud_selection_sha256 is None
                    or config_file_digest(current / name)
                    != expected_cloud_selection_sha256
                ):
                    fail(TAMPER_EXIT)
                cloud_selection_seen = True
                continue
            copy_config_file(current / name, destination / relative / name)
    try:
        root_after = source.lstat()
    except OSError:
        fail(TAMPER_EXIT)
    if signature(root_after) != root_signature:
        fail(TAMPER_EXIT)
    if cloud_selection_seen != (expected_cloud_selection_sha256 is not None):
        fail(TAMPER_EXIT)
    if (destination / "clouds.config").exists():
        fail(TAMPER_EXIT)

def install_private_azure_cloud_config(config_root):
    config = config_root / "config"
    try:
        if config.exists() or config.is_symlink():
            metadata = config.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
                fail(TAMPER_EXIT)
            config.unlink()
        descriptor = os.open(
            config,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL
            | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            payload = b"[cloud]\nname = AzureCloud\n"
            if os.write(descriptor, payload) != len(payload):
                fail(TAMPER_EXIT)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        fail(TAMPER_EXIT)

def validate_host_userns_profile(
    restriction_path=Path("/proc/sys/kernel/apparmor_restrict_unprivileged_userns"),
    label_path=Path("/proc/self/attr/current"),
):
    try:
        restriction = restriction_path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return
    except OSError:
        fail(ISOLATION_EXIT)
    if restriction != "1":
        return
    try:
        label = label_path.read_text(encoding="ascii").strip()
    except OSError:
        fail(ISOLATION_EXIT)
    if label != REQUIRED_APPARMOR_PROFILE:
        fail(ISOLATION_EXIT)

def close_fd(descriptor):
    try:
        os.close(descriptor)
    except OSError:
        pass

def close_inherited_descriptors():
    try:
        maximum = os.sysconf("SC_OPEN_MAX")
    except (OSError, TypeError, ValueError):
        fail(TAMPER_EXIT)
    if not isinstance(maximum, int) or maximum < 3 or maximum > 2 ** 24:
        fail(TAMPER_EXIT)
    os.closerange(3, maximum)

def write_proc_mapping(path, payload):
    flags = os.O_WRONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        if os.write(descriptor, payload) != len(payload):
            raise OSError("short proc mapping write")
    finally:
        os.close(descriptor)

def write_id_maps(pid, uid, gid, proc_root=Path("/proc")):
    process_root = proc_root / str(pid)
    try:
        write_proc_mapping(process_root / "setgroups", b"deny")
    except OSError:
        pass
    try:
        write_proc_mapping(
            process_root / "uid_map",
            f"0 {uid} 1\n".encode("ascii"),
        )
        write_proc_mapping(
            process_root / "gid_map",
            f"0 {gid} 1\n".encode("ascii"),
        )
    except (OSError, ValueError):
        return False
    return True

def kill_account_process_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

def terminate_account_child(pid):
    kill_account_process_group(pid)
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass

def terminate_child(pid):
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        os.waitpid(pid, 0)
    except ChildProcessError:
        pass

def arm_parent_death_signal(libc, parent_pid):
    pr_set_pdeathsig = 1
    if libc.prctl(pr_set_pdeathsig, signal.SIGKILL, 0, 0, 0) != 0:
        return False
    return os.getppid() == parent_pid

def exit_with_child_status(pid):
    def forward(signum, _frame):
        try:
            os.kill(pid, signum)
        except ProcessLookupError:
            pass

    for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, forward)
    try:
        _, status = os.waitpid(pid, 0)
    except (ChildProcessError, OSError):
        terminate_child(pid)
        fail(ISOLATION_EXIT)
    if os.WIFEXITED(status):
        os._exit(os.WEXITSTATUS(status))
    if os.WIFSIGNALED(status):
        signum = os.WTERMSIG(status)
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)
        os._exit(128 + signum)
    os._exit(ISOLATION_EXIT)

def wait_child_exit_without_reap(pid, deadline):
    while True:
        try:
            result = os.waitid(
                os.P_PID,
                pid,
                os.WEXITED | os.WNOHANG | os.WNOWAIT,
            )
        except (ChildProcessError, OSError):
            terminate_account_child(pid)
            fail(TAMPER_EXIT)
        if result is not None:
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            terminate_account_child(pid)
            fail(TAMPER_EXIT)
        time.sleep(min(0.01, remaining))

def verify_write_account_binding(azure_argv):
    if not any(
        tuple(azure_argv[:len(prefix)]) == prefix
        for prefix in WRITE_COMMAND_PREFIXES
    ):
        return
    parent_pid = os.getpid()
    try:
        output_read, output_write = os.pipe2(os.O_CLOEXEC)
    except OSError:
        fail(TAMPER_EXIT)
    try:
        pid = os.fork()
    except OSError:
        close_fd(output_read)
        close_fd(output_write)
        fail(TAMPER_EXIT)
    if pid == 0:
        close_fd(output_read)
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            if not arm_parent_death_signal(libc, parent_pid):
                os._exit(TAMPER_EXIT)
            os.setsid()
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(output_write, 1)
            os.dup2(devnull, 2)
            close_fd(output_write)
            close_fd(devnull)
            close_inherited_descriptors()
            sys.argv = [
                "az", "account", "show",
                "--subscription", EXPECTED_SUBSCRIPTION_ID,
                "--query",
                "{id:id,tenantId:tenantId,environmentName:environmentName,state:state}",
                "--output", "json", "--only-show-errors",
            ]
            exit_code = 0
            try:
                runpy.run_module("azure.cli", run_name="__main__")
            except SystemExit as exc:
                exit_code = exc.code if isinstance(exc.code, int) else 1
            try:
                sys.stdout.flush()
            except (AttributeError, OSError):
                exit_code = 1
            os._exit(exit_code)
        except BaseException:
            os._exit(TAMPER_EXIT)
    close_fd(output_write)
    payload = bytearray()
    oversized = False
    deadline = time.monotonic() + ACCOUNT_ASSERTION_TIMEOUT_SECONDS
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                terminate_account_child(pid)
                fail(TAMPER_EXIT)
            try:
                readable, _, _ = select.select(
                    [output_read], [], [], remaining
                )
            except (OSError, ValueError):
                terminate_account_child(pid)
                fail(TAMPER_EXIT)
            if not readable:
                terminate_account_child(pid)
                fail(TAMPER_EXIT)
            chunk = os.read(output_read, CHUNK_SIZE)
            if not chunk:
                break
            payload.extend(chunk)
            if len(payload) > MAX_ACCOUNT_ASSERTION_BYTES:
                oversized = True
                break
    except OSError:
        terminate_account_child(pid)
        fail(TAMPER_EXIT)
    finally:
        close_fd(output_read)
    if oversized:
        terminate_account_child(pid)
        fail(TAMPER_EXIT)
    wait_child_exit_without_reap(pid, deadline)
    kill_account_process_group(pid)
    try:
        _, status = os.waitpid(pid, 0)
    except (ChildProcessError, OSError):
        fail(TAMPER_EXIT)
    if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:
        fail(TAMPER_EXIT)
    validate_account_binding_payload(bytes(payload))

def validate_account_binding_payload(payload):
    def unique_object(pairs):
        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            fail(TAMPER_EXIT)
        return dict(pairs)

    try:
        account = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=unique_object,
        )
    except (AttributeError, UnicodeDecodeError, TypeError, ValueError):
        fail(TAMPER_EXIT)
    if (
        not isinstance(account, dict)
        or set(account) != ACCOUNT_ASSERTION_FIELDS
        or account.get("environmentName") != EXPECTED_CLOUD_NAME
        or str(account.get("tenantId", "")).lower()
            != EXPECTED_TENANT_ID
        or str(account.get("id", "")).lower()
            != EXPECTED_SUBSCRIPTION_ID
        or account.get("state") != "Enabled"
    ):
        fail(TAMPER_EXIT)

def enter_mapped_user_namespace(libc, clone_newuser, uid, gid):
    parent_pid = os.getpid()
    try:
        ready_read, ready_write = os.pipe()
        continue_read, continue_write = os.pipe()
    except OSError:
        fail(ISOLATION_EXIT)
    try:
        pid = os.fork()
    except OSError:
        for descriptor in (ready_read, ready_write, continue_read, continue_write):
            close_fd(descriptor)
        fail(ISOLATION_EXIT)
    if pid == 0:
        if not arm_parent_death_signal(libc, parent_pid):
            for descriptor in (
                ready_read,
                ready_write,
                continue_read,
                continue_write,
            ):
                close_fd(descriptor)
            fail(ISOLATION_EXIT)
        close_fd(ready_read)
        close_fd(continue_write)
        if libc.unshare(clone_newuser) != 0:
            close_fd(ready_write)
            close_fd(continue_read)
            fail(ISOLATION_EXIT)
        try:
            if os.write(ready_write, b"R") != 1:
                fail(ISOLATION_EXIT)
            close_fd(ready_write)
            if os.read(continue_read, 1) != b"G":
                fail(ISOLATION_EXIT)
        except OSError:
            fail(ISOLATION_EXIT)
        finally:
            close_fd(ready_write)
            close_fd(continue_read)
        return
    close_fd(ready_write)
    close_fd(continue_read)
    try:
        child_ready = os.read(ready_read, 1) == b"R"
        if not child_ready or not write_id_maps(pid, uid, gid):
            terminate_child(pid)
            fail(ISOLATION_EXIT)
        if os.write(continue_write, b"G") != 1:
            terminate_child(pid)
            fail(ISOLATION_EXIT)
    except OSError:
        terminate_child(pid)
        fail(ISOLATION_EXIT)
    finally:
        close_fd(ready_read)
        close_fd(continue_write)
    exit_with_child_status(pid)

def isolate():
    libc = ctypes.CDLL(None, use_errno=True)
    clone_newns = 0x00020000
    clone_newuser = 0x10000000
    uid = os.getuid()
    gid = os.getgid()
    enter_mapped_user_namespace(libc, clone_newuser, uid, gid)
    if libc.unshare(clone_newns) != 0:
        fail(ISOLATION_EXIT)
    ms_rec = 16384
    ms_private = 1 << 18
    if libc.mount(None, b"/", None, ms_rec | ms_private, None) != 0:
        fail(ISOLATION_EXIT)
    mountpoint = Path(tempfile.mkdtemp(prefix="nac-azure-cli-sealed-"))
    if libc.mount(b"tmpfs", os.fsencode(mountpoint), b"tmpfs", 0, b"mode=0700") != 0:
        fail(ISOLATION_EXIT)
    config_mountpoint = Path(tempfile.mkdtemp(prefix="nac-azure-cli-config-"))
    if libc.mount(b"tmpfs", os.fsencode(config_mountpoint), b"tmpfs", 0, b"mode=0700") != 0:
        fail(ISOLATION_EXIT)
    return mountpoint, config_mountpoint, libc

def main():
    if len(sys.argv) < 3:
        fail(TAMPER_EXIT)
    try:
        manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        fail(TAMPER_EXIT)
    if manifest.get("schema") != "nac-azure-cli-sealed-runtime-v1":
        fail(TAMPER_EXIT)
    package_archive_path = Path(sys.argv[2])
    verify_only = len(sys.argv) >= 5 and sys.argv[3] == "--nac-internal-verify-only"
    if verify_only:
        destination = Path(sys.argv[4])
        azure_argv = []
        libc = None
        private_config = None
    else:
        try:
            source_config = Path(os.environ.get("AZURE_CONFIG_DIR") or (Path(os.environ["HOME"]) / ".azure"))
        except (KeyError, TypeError, ValueError):
            fail(TAMPER_EXIT)
        expected_cloud_selection_sha256 = manifest.get(
            "cloud_selection_sha256"
        )
        if expected_cloud_selection_sha256 is not None and (
            not isinstance(expected_cloud_selection_sha256, str)
            or len(expected_cloud_selection_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in expected_cloud_selection_sha256
            )
        ):
            fail(TAMPER_EXIT)
        validate_host_userns_profile()
        destination, private_config, libc = isolate()
        copy_private_azure_config(
            source_config,
            private_config,
            expected_cloud_selection_sha256,
        )
        install_private_azure_cloud_config(private_config)
        azure_argv = sys.argv[3:]
    try:
        with zipfile.ZipFile(package_archive_path, mode="r") as package_archive:
            validate_package_archive(package_archive, manifest["files"])
            for record in manifest["directories"]:
                archive_target(destination, record["path"]).mkdir(
                    parents=True,
                    exist_ok=True,
                )
            for record in manifest["files"]:
                copy_archived_verified(
                    package_archive,
                    archive_target(destination, record["path"]),
                    record,
                )
        extension_root = destination / ".nac-empty-extensions"
        extension_root.mkdir(mode=0o500)
        for record in reversed(manifest["directories"]):
            os.chmod(
                archive_target(destination, record["path"]),
                record["mode"] & ~0o222,
            )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, zipfile.BadZipFile):
        fail(TAMPER_EXIT)
    if verify_only:
        return
    ms_remount = 32
    ms_rdonly = 1
    if libc.mount(None, os.fsencode(destination), None, ms_remount | ms_rdonly, None) != 0:
        fail(ISOLATION_EXIT)
    import sysconfig
    stdlib = Path(sysconfig.get_path("stdlib"))
    platstdlib = Path(sysconfig.get_path("platstdlib"))
    trusted_paths = [destination, stdlib, platstdlib]
    for root in (stdlib, platstdlib):
        dynload = root / "lib-dynload"
        if dynload not in trusted_paths:
            trusted_paths.append(dynload)
    sys.path[:] = [str(path) for path in trusted_paths]
    # Override both user-configured and system extension roots with one empty,
    # read-only directory inside the isolated mount. Empty dev_sources masks any
    # mutable config-file value; dynamic installation is disabled explicitly.
    extension_root = destination / ".nac-empty-extensions"
    os.environ["AZURE_EXTENSION_DIR"] = str(extension_root)
    os.environ["AZURE_EXTENSION_SYS_DIR"] = str(extension_root)
    os.environ["AZURE_EXTENSION_DEV_SOURCES"] = ""
    os.environ["AZURE_EXTENSION_USE_DYNAMIC_INSTALL"] = "no"
    os.environ["AZURE_CONFIG_DIR"] = str(private_config)
    verify_write_account_binding(azure_argv)
    sys.argv = ["az", *azure_argv]
    runpy.run_module("azure.cli", run_name="__main__")

main()
'''
