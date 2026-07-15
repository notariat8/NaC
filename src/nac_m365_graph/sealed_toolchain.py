from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Iterator, Sequence


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MAX_TOOL_BYTES = 512 * 1024 * 1024


class SealedToolchainError(RuntimeError):
    """Raised when a tool cannot be bound to immutable execution bytes."""


@dataclass(frozen=True)
class SealedToolchain:
    paths: tuple[str, ...]
    pass_fds: tuple[int, ...]


def verified_tool_bytes(
    path: Path,
    *,
    executable: bool,
    expected_sha256: str,
) -> bytes:
    """Read one path exactly once and return only stable digest-matched bytes."""

    return _read_verified_bytes(
        Path(path),
        executable=executable,
        expected_sha256=expected_sha256,
    )


@contextmanager
def sealed_toolchain(
    specifications: Sequence[tuple[Path, bool, str]],
) -> Iterator[SealedToolchain]:
    """Copy verified executable bytes into sealed memfds."""

    descriptors: list[int] = []
    try:
        for path, executable, expected_sha256 in specifications:
            descriptors.append(
                _sealed_snapshot(
                    Path(path),
                    executable=executable,
                    expected_sha256=expected_sha256,
                )
            )
        yield SealedToolchain(
            paths=tuple(f"/proc/self/fd/{descriptor}" for descriptor in descriptors),
            pass_fds=tuple(descriptors),
        )
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


@contextmanager
def sealed_payloads(
    payloads: Sequence[tuple[str, bytes, bool]],
) -> Iterator[SealedToolchain]:
    """Copy already verified in-memory payloads into sealed memfds."""

    descriptors: list[int] = []
    try:
        for name, payload, executable in payloads:
            descriptors.append(
                _sealed_payload(name, payload, executable=executable)
            )
        yield SealedToolchain(
            paths=tuple(f"/proc/self/fd/{descriptor}" for descriptor in descriptors),
            pass_fds=tuple(descriptors),
        )
    finally:
        for descriptor in reversed(descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _sealed_snapshot(
    path: Path,
    *,
    executable: bool,
    expected_sha256: str,
) -> int:
    payload = _read_verified_bytes(
        path,
        executable=executable,
        expected_sha256=expected_sha256,
    )
    return _sealed_payload(path.name, payload, executable=executable)


def _sealed_payload(name: str, payload: bytes, *, executable: bool) -> int:
    if (
        not payload
        or len(payload) > _MAX_TOOL_BYTES
        or not hasattr(os, "memfd_create")
        or not Path("/proc/self/fd").is_dir()
    ):
        raise SealedToolchainError("SEALED_TOOLCHAIN_UNAVAILABLE")

    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "-", name)[:80] or "payload"
    sealed_fd = -1
    try:
        sealed_fd = os.memfd_create(
            f"nac-{safe_name}",
            flags=getattr(os, "MFD_CLOEXEC", 0)
            | getattr(os, "MFD_ALLOW_SEALING", 0),
        )
        _write_all(sealed_fd, payload)
        os.fchmod(sealed_fd, 0o500 if executable else 0o400)
        os.lseek(sealed_fd, 0, os.SEEK_SET)
        seal_flags = (
            getattr(fcntl, "F_SEAL_SEAL", 0)
            | getattr(fcntl, "F_SEAL_SHRINK", 0)
            | getattr(fcntl, "F_SEAL_GROW", 0)
            | getattr(fcntl, "F_SEAL_WRITE", 0)
        )
        add_seals = getattr(fcntl, "F_ADD_SEALS", None)
        get_seals = getattr(fcntl, "F_GET_SEALS", None)
        if add_seals is None or get_seals is None or not seal_flags:
            raise SealedToolchainError("SEALED_TOOLCHAIN_UNAVAILABLE")
        fcntl.fcntl(sealed_fd, add_seals, seal_flags)
        if fcntl.fcntl(sealed_fd, get_seals) & seal_flags != seal_flags:
            raise SealedToolchainError("SEALED_TOOLCHAIN_SEAL_FAILED")
        result = sealed_fd
        sealed_fd = -1
        return result
    except (OSError, ValueError) as exc:
        raise SealedToolchainError("SEALED_TOOLCHAIN_FAILED") from exc
    finally:
        if sealed_fd >= 0:
            os.close(sealed_fd)


def _read_verified_bytes(
    path: Path,
    *,
    executable: bool,
    expected_sha256: str,
) -> bytes:
    if (
        not path.is_absolute()
        or not _SHA256_RE.fullmatch(expected_sha256)
        or not _trusted_parent_chain(path.parent)
    ):
        raise SealedToolchainError("SEALED_TOOLCHAIN_UNAVAILABLE")
    descriptor = -1
    try:
        metadata = path.lstat()
        descriptor = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
        )
        opened = os.fstat(descriptor)
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(opened.st_mode)
            or (metadata.st_dev, metadata.st_ino)
            != (opened.st_dev, opened.st_ino)
            or opened.st_uid not in {0, os.geteuid()}
            or opened.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (executable and not opened.st_mode & 0o111)
            or opened.st_size < 1
            or opened.st_size > _MAX_TOOL_BYTES
        ):
            raise SealedToolchainError("SEALED_TOOLCHAIN_INPUT_UNTRUSTED")

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_TOOL_BYTES:
                raise SealedToolchainError("SEALED_TOOLCHAIN_INPUT_UNTRUSTED")
        final = os.fstat(descriptor)
        payload = b"".join(chunks)
        if (
            opened.st_dev,
            opened.st_ino,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        ) != (
            final.st_dev,
            final.st_ino,
            final.st_size,
            final.st_mtime_ns,
            final.st_ctime_ns,
        ) or total != opened.st_size:
            raise SealedToolchainError("SEALED_TOOLCHAIN_INPUT_CHANGED")
        if hashlib.sha256(payload).hexdigest() != expected_sha256:
            raise SealedToolchainError("SEALED_TOOLCHAIN_SHA256_MISMATCH")
        return payload
    except (OSError, ValueError) as exc:
        raise SealedToolchainError("SEALED_TOOLCHAIN_FAILED") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise SealedToolchainError("SEALED_TOOLCHAIN_WRITE_FAILED")
        offset += written


def _trusted_parent_chain(path: Path) -> bool:
    current = path
    try:
        while current != current.parent:
            metadata = current.lstat()
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid not in {0, os.geteuid()}
                or (
                    metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                    and not (
                        metadata.st_uid == 0
                        and metadata.st_mode & stat.S_ISVTX
                    )
                )
            ):
                return False
            current = current.parent
    except OSError:
        return False
    return True
