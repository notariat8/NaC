from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, fields
import os
from pathlib import Path
import sys
from typing import BinaryIO, Mapping, Protocol, runtime_checkable


PLATFORM_SECURITY_BACKEND_UNAVAILABLE = "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"


class SecurityBoundaryError(RuntimeError):
    """Stable, non-sensitive failure raised before a protected side effect."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class PlatformSecurityBackendUnavailable(SecurityBoundaryError):
    def __init__(self) -> None:
        super().__init__(PLATFORM_SECURITY_BACKEND_UNAVAILABLE)


@dataclass(frozen=True, slots=True)
class SecurityCapabilities:
    handle_bound_files: bool
    private_owner_acl: bool
    reparse_protection: bool
    durable_atomic_writes: bool
    durable_append: bool
    exclusive_run_lock: bool
    abandoned_lock_detection: bool
    suspended_process_launch: bool
    job_object_containment: bool
    process_image_attestation: bool

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(
            field.name for field in fields(self) if not getattr(self, field.name)
        )

    @property
    def complete(self) -> bool:
        return not self.missing


@dataclass(frozen=True, slots=True)
class OperatorBinding:
    sid_sha256: str


@dataclass(frozen=True, slots=True)
class BoundFileSnapshot:
    path_sha256: str
    volume_serial: int
    file_id: int
    size: int
    sha256: str
    owner_sid_sha256: str
    security_descriptor_sha256: str
    dacl_sha256: str
    reparse_point: bool


@dataclass(frozen=True, slots=True)
class SecureDirectoryBinding:
    path_sha256: str
    volume_serial: int
    file_id: int
    owner_sid_sha256: str
    security_descriptor_sha256: str
    dacl_sha256: str


@dataclass(frozen=True, slots=True)
class ProcessSpec:
    executable: Path
    arguments: tuple[str, ...]
    cwd: Path
    environment: Mapping[str, str]
    executable_sha256: str
    timeout_seconds: float = 60.0
    maximum_output_bytes: int = 1024 * 1024
    allowed_exit_codes: tuple[int, ...] = (0,)
    credential_write_guard: bool = False


@dataclass(frozen=True, slots=True)
class ProcessResult:
    exit_code: int
    stdout: bytes
    stderr: bytes
    image_sha256: str
    job_object_assigned: bool


@runtime_checkable
class RunLock(Protocol):
    status: str
    mutex_name_sha256: str
    journal_sha256: str

    def close(self) -> None: ...


@runtime_checkable
class SecureDirectorySession(Protocol):
    binding: SecureDirectoryBinding

    def canonical_child_path(self, name: str) -> Path: ...

    def inspect_optional_child(
        self, name: str, purpose: str
    ) -> BoundFileSnapshot | None: ...

    def open_regular_descriptor(self, name: str, *, create: bool) -> int: ...

    def read_bounded(self, name: str, maximum_bytes: int) -> bytes | None: ...

    def atomic_write(self, name: str, payload: bytes) -> BoundFileSnapshot: ...

    def append_and_flush(
        self, name: str, payload: bytes
    ) -> BoundFileSnapshot: ...

    def delete_child(self, name: str) -> bool: ...

    def flush(self) -> None: ...

    def close(self) -> None: ...


@runtime_checkable
class ActivationSecurityBackend(Protocol):
    def capabilities(self) -> SecurityCapabilities: ...

    def current_operator_binding(self) -> OperatorBinding: ...

    def inspect_private_path(
        self, path: Path, purpose: str
    ) -> BoundFileSnapshot: ...

    def inspect_open_file_descriptor(
        self, descriptor: int, purpose: str
    ) -> BoundFileSnapshot: ...

    def validate_private_directory(self, path: Path) -> str: ...

    def open_secure_directory(
        self, path: Path, *, create: bool, require_current_owner: bool = True
    ) -> SecureDirectorySession: ...

    def open_bound_read(
        self, path: Path, expected_binding: BoundFileSnapshot
    ) -> AbstractContextManager[BinaryIO]: ...

    def atomic_write(self, path: Path, payload: bytes) -> BoundFileSnapshot: ...

    def append_and_flush(self, path: Path, payload: bytes) -> BoundFileSnapshot: ...

    def flush_directory(self, path: Path) -> None: ...

    def acquire_run_lock(self, target_binding: str) -> RunLock: ...

    def launch_attested_process(self, spec: ProcessSpec) -> ProcessResult: ...

    def inspect_process_image(self, process_handle: int) -> str: ...


def get_platform_security_backend() -> ActivationSecurityBackend:
    """Select from trusted runtime facts only; configuration cannot override it."""

    if os.name == "nt" and sys.platform == "win32":
        from .activation_security_windows import WindowsActivationSecurityBackend

        backend: ActivationSecurityBackend = WindowsActivationSecurityBackend()
    elif os.name == "posix" and sys.platform == "linux":
        from .activation_security_linux import LinuxActivationSecurityBackend

        backend = LinuxActivationSecurityBackend()
    else:
        raise PlatformSecurityBackendUnavailable()
    if not backend.capabilities().complete:
        raise PlatformSecurityBackendUnavailable()
    return backend


__all__ = [
    "ActivationSecurityBackend",
    "BoundFileSnapshot",
    "OperatorBinding",
    "PLATFORM_SECURITY_BACKEND_UNAVAILABLE",
    "PlatformSecurityBackendUnavailable",
    "ProcessResult",
    "ProcessSpec",
    "RunLock",
    "SecureDirectoryBinding",
    "SecureDirectorySession",
    "SecurityBoundaryError",
    "SecurityCapabilities",
    "get_platform_security_backend",
]
