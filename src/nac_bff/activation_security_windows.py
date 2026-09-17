from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import io
import msvcrt
import os
from pathlib import Path
import tempfile
import threading
from typing import BinaryIO, Iterator

from .activation_security_backend import (
    BoundFileSnapshot,
    OperatorBinding,
    ProcessResult,
    ProcessSpec,
    SecurityBoundaryError,
    SecurityCapabilities,
)


if os.name != "nt":  # pragma: no cover - module is selected only on Windows
    raise ImportError("Windows activation security backend requires Windows")


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

kernel32.CreateFileW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.HANDLE,
)
kernel32.CreateFileW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.GetCurrentProcess.argtypes = ()
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.DuplicateHandle.argtypes = (
    wintypes.HANDLE,
    wintypes.HANDLE,
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.DWORD,
    wintypes.BOOL,
    wintypes.DWORD,
)
kernel32.DuplicateHandle.restype = wintypes.BOOL
kernel32.GetFileInformationByHandle.argtypes = (
    wintypes.HANDLE,
    wintypes.LPVOID,
)
kernel32.GetFileInformationByHandle.restype = wintypes.BOOL
kernel32.GetFileType.argtypes = (wintypes.HANDLE,)
kernel32.GetFileType.restype = wintypes.DWORD
kernel32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
kernel32.FlushFileBuffers.restype = wintypes.BOOL
kernel32.SetFilePointerEx.argtypes = (
    wintypes.HANDLE,
    ctypes.c_longlong,
    ctypes.POINTER(ctypes.c_longlong),
    wintypes.DWORD,
)
kernel32.SetFilePointerEx.restype = wintypes.BOOL
kernel32.GetFinalPathNameByHandleW.argtypes = (
    wintypes.HANDLE,
    wintypes.LPWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
)
kernel32.GetFinalPathNameByHandleW.restype = wintypes.DWORD
kernel32.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
kernel32.ReleaseMutex.restype = wintypes.BOOL
kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
kernel32.LocalFree.restype = wintypes.HLOCAL
kernel32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
advapi32.OpenProcessToken.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
)
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
)
advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.GetLengthSid.argtypes = (wintypes.LPVOID,)
advapi32.GetLengthSid.restype = wintypes.DWORD
advapi32.ConvertSidToStringSidW.argtypes = (
    wintypes.LPVOID,
    ctypes.POINTER(wintypes.LPWSTR),
)
advapi32.ConvertSidToStringSidW.restype = wintypes.BOOL
advapi32.GetSecurityInfo.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.LPVOID),
    ctypes.POINTER(wintypes.LPVOID),
    ctypes.POINTER(wintypes.LPVOID),
    ctypes.POINTER(wintypes.LPVOID),
    ctypes.POINTER(wintypes.LPVOID),
)
advapi32.GetSecurityInfo.restype = wintypes.DWORD
advapi32.GetSecurityDescriptorLength.argtypes = (wintypes.LPVOID,)
advapi32.GetSecurityDescriptorLength.restype = wintypes.DWORD
advapi32.GetAce.argtypes = (
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.LPVOID),
)
advapi32.GetAce.restype = wintypes.BOOL
advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.LPVOID),
    ctypes.POINTER(wintypes.DWORD),
)
advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL

INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
GENERIC_READ = 0x80000000
FILE_APPEND_DATA = 0x00000004
FILE_SHARE_READ = 0x00000001
OPEN_EXISTING = 3
OPEN_ALWAYS = 4
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_TYPE_DISK = 0x0001
TOKEN_QUERY = 0x0008
TOKEN_USER = 1
OWNER_SECURITY_INFORMATION = 0x00000001
DACL_SECURITY_INFORMATION = 0x00000004
SE_FILE_OBJECT = 1
WAIT_OBJECT_0 = 0x00000000
WAIT_ABANDONED = 0x00000080
WAIT_TIMEOUT = 0x00000102


class BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", wintypes.DWORD),
        ("ftCreationTime", wintypes.FILETIME),
        ("ftLastAccessTime", wintypes.FILETIME),
        ("ftLastWriteTime", wintypes.FILETIME),
        ("dwVolumeSerialNumber", wintypes.DWORD),
        ("nFileSizeHigh", wintypes.DWORD),
        ("nFileSizeLow", wintypes.DWORD),
        ("nNumberOfLinks", wintypes.DWORD),
        ("nFileIndexHigh", wintypes.DWORD),
        ("nFileIndexLow", wintypes.DWORD),
    ]


class TOKEN_USER_VALUE(ctypes.Structure):
    _fields_ = [("Sid", wintypes.LPVOID), ("Attributes", wintypes.DWORD)]


class TOKEN_USER_BUFFER(ctypes.Structure):
    _fields_ = [("User", TOKEN_USER_VALUE)]


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


_local_mutex_guard = threading.Lock()
_local_mutexes: set[str] = set()


def _raise_last_error(code: str) -> None:
    error = ctypes.get_last_error()
    raise SecurityBoundaryError(f"{code}_{error}" if error else code)


def _close_handle(handle: int) -> None:
    if handle not in (0, None, INVALID_HANDLE_VALUE):
        kernel32.CloseHandle(wintypes.HANDLE(handle))


def _sid_bytes(sid: int) -> bytes:
    length = advapi32.GetLengthSid(wintypes.LPVOID(sid))
    if not length:
        _raise_last_error("SID_READ_FAILED")
    return ctypes.string_at(sid, length)


def _current_sid_bytes() -> bytes:
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)
    ):
        _raise_last_error("OPERATOR_TOKEN_OPEN_FAILED")
    try:
        required = wintypes.DWORD()
        advapi32.GetTokenInformation(
            token, TOKEN_USER, None, 0, ctypes.byref(required)
        )
        if not required.value:
            _raise_last_error("OPERATOR_SID_READ_FAILED")
        buffer = ctypes.create_string_buffer(required.value)
        if not advapi32.GetTokenInformation(
            token,
            TOKEN_USER,
            buffer,
            required.value,
            ctypes.byref(required),
        ):
            _raise_last_error("OPERATOR_SID_READ_FAILED")
        user = ctypes.cast(buffer, ctypes.POINTER(TOKEN_USER_BUFFER)).contents
        return _sid_bytes(user.User.Sid)
    finally:
        _close_handle(token.value)


def _current_sid_string() -> str:
    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)
    ):
        _raise_last_error("OPERATOR_TOKEN_OPEN_FAILED")
    try:
        required = wintypes.DWORD()
        advapi32.GetTokenInformation(
            token, TOKEN_USER, None, 0, ctypes.byref(required)
        )
        buffer = ctypes.create_string_buffer(required.value)
        if not required.value or not advapi32.GetTokenInformation(
            token,
            TOKEN_USER,
            buffer,
            required.value,
            ctypes.byref(required),
        ):
            _raise_last_error("OPERATOR_SID_READ_FAILED")
        user = ctypes.cast(buffer, ctypes.POINTER(TOKEN_USER_BUFFER)).contents
        return _sid_string(user.User.Sid)
    finally:
        _close_handle(token.value)


def _open_read_handle(path: Path) -> int:
    handle = kernel32.CreateFileW(
        str(path),
        GENERIC_READ,
        FILE_SHARE_READ,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        _raise_last_error("FILE_OPEN_FAILED")
    return int(handle)


def _open_directory_handle(path: Path) -> int:
    handle = kernel32.CreateFileW(
        str(path),
        GENERIC_READ,
        FILE_SHARE_READ,
        None,
        OPEN_EXISTING,
        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        _raise_last_error("DIRECTORY_OPEN_FAILED")
    return int(handle)


def _final_path(handle: int) -> str:
    required = kernel32.GetFinalPathNameByHandleW(handle, None, 0, 0)
    if not required:
        _raise_last_error("FINAL_PATH_READ_FAILED")
    buffer = ctypes.create_unicode_buffer(required + 1)
    written = kernel32.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not written or written >= len(buffer):
        _raise_last_error("FINAL_PATH_READ_FAILED")
    value = buffer.value
    return value[4:] if value.startswith("\\\\?\\") else value


def _sid_string(sid: int) -> str:
    value = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(value)):
        _raise_last_error("SID_READ_FAILED")
    try:
        return value.value
    finally:
        kernel32.LocalFree(value)


def _security_hashes(
    handle: int, *, require_current_owner: bool
) -> tuple[str, str, str]:
    owner = wintypes.LPVOID()
    dacl = wintypes.LPVOID()
    descriptor = wintypes.LPVOID()
    status = advapi32.GetSecurityInfo(
        handle,
        SE_FILE_OBJECT,
        OWNER_SECURITY_INFORMATION | DACL_SECURITY_INFORMATION,
        ctypes.byref(owner),
        None,
        ctypes.byref(dacl),
        None,
        ctypes.byref(descriptor),
    )
    if status:
        raise SecurityBoundaryError(f"SECURITY_DESCRIPTOR_READ_FAILED_{status}")
    try:
        owner_bytes = _sid_bytes(owner.value)
        if require_current_owner and owner_bytes != _current_sid_bytes():
            raise SecurityBoundaryError("FILE_OWNER_MISMATCH")
        descriptor_length = advapi32.GetSecurityDescriptorLength(descriptor)
        if not descriptor_length:
            _raise_last_error("SECURITY_DESCRIPTOR_READ_FAILED")
        descriptor_bytes = ctypes.string_at(descriptor, descriptor_length)
        if not dacl.value:
            raise SecurityBoundaryError("FILE_DACL_MISSING")
        # ACL size is stored in the fixed header at bytes 2..4.
        dacl_size = int.from_bytes(ctypes.string_at(dacl, 4)[2:4], "little")
        if dacl_size < 8:
            raise SecurityBoundaryError("FILE_DACL_INVALID")
        dacl_bytes = ctypes.string_at(dacl, dacl_size)
        _require_restrictive_dacl(dacl.value, dacl_bytes)
        return (
            hashlib.sha256(owner_bytes).hexdigest(),
            hashlib.sha256(descriptor_bytes).hexdigest(),
            hashlib.sha256(dacl_bytes).hexdigest(),
        )
    finally:
        kernel32.LocalFree(descriptor)


def _require_restrictive_dacl(dacl: int, raw: bytes) -> None:
    ace_count = int.from_bytes(raw[4:6], "little")
    broad_principals = {"S-1-1-0", "S-1-5-11", "S-1-5-32-545"}
    write_mask = (
        0x00000002
        | 0x00000004
        | 0x00000010
        | 0x00000100
        | 0x00010000
        | 0x00040000
        | 0x00080000
        | 0x10000000
        | 0x40000000
    )
    for index in range(ace_count):
        ace = wintypes.LPVOID()
        if not advapi32.GetAce(dacl, index, ctypes.byref(ace)):
            _raise_last_error("FILE_DACL_INVALID")
        header = ctypes.string_at(ace, 8)
        ace_type = header[0]
        ace_size = int.from_bytes(header[2:4], "little")
        if ace_size < 8:
            raise SecurityBoundaryError("FILE_DACL_INVALID")
        if ace_type != 0:  # only ACCESS_ALLOWED_ACE has a fixed SID offset
            continue
        mask = int.from_bytes(header[4:8], "little")
        if mask & write_mask and _sid_string(ace.value + 8) in broad_principals:
            raise SecurityBoundaryError("FILE_DACL_TOO_BROAD")


def _duplicate_for_python(handle: int) -> BinaryIO:
    duplicate = wintypes.HANDLE()
    current = kernel32.GetCurrentProcess()
    if not kernel32.DuplicateHandle(
        current,
        handle,
        current,
        ctypes.byref(duplicate),
        0,
        False,
        2,
    ):
        _raise_last_error("FILE_HANDLE_DUPLICATION_FAILED")
    try:
        descriptor = msvcrt.open_osfhandle(duplicate.value, os.O_RDONLY)
    except BaseException:
        _close_handle(duplicate.value)
        raise
    return os.fdopen(descriptor, "rb", closefd=True)


def _snapshot(handle: int, *, require_current_owner: bool = True) -> BoundFileSnapshot:
    information = BY_HANDLE_FILE_INFORMATION()
    if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(information)):
        _raise_last_error("FILE_INFORMATION_READ_FAILED")
    if kernel32.GetFileType(handle) != FILE_TYPE_DISK:
        raise SecurityBoundaryError("NON_DISK_PATH_REJECTED")
    reparse = bool(information.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
    if reparse:
        raise SecurityBoundaryError("REPARSE_POINT_REJECTED")
    if not kernel32.SetFilePointerEx(handle, 0, None, 0):
        _raise_last_error("FILE_SEEK_FAILED")
    with _duplicate_for_python(handle) as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if not kernel32.SetFilePointerEx(handle, 0, None, 0):
        _raise_last_error("FILE_SEEK_FAILED")
    owner_hash, descriptor_hash, dacl_hash = _security_hashes(
        handle, require_current_owner=require_current_owner
    )
    canonical = _final_path(handle).casefold().encode("utf-8")
    return BoundFileSnapshot(
        path_sha256=hashlib.sha256(canonical).hexdigest(),
        volume_serial=information.dwVolumeSerialNumber,
        file_id=(information.nFileIndexHigh << 32) | information.nFileIndexLow,
        size=(information.nFileSizeHigh << 32) | information.nFileSizeLow,
        sha256=digest,
        owner_sid_sha256=owner_hash,
        security_descriptor_sha256=descriptor_hash,
        dacl_sha256=dacl_hash,
        reparse_point=False,
    )


class WindowsRunLock:
    def __init__(
        self, handle: int, name: str, status: str, target_binding: str
    ) -> None:
        self._handle = handle
        self._name = name
        self.status = status
        self.mutex_name_sha256 = hashlib.sha256(name.encode("utf-8")).hexdigest()
        self.journal_sha256 = hashlib.sha256(
            target_binding.encode("ascii")
        ).hexdigest()

    def close(self) -> None:
        handle, self._handle = self._handle, 0
        if handle:
            kernel32.ReleaseMutex(handle)
            _close_handle(handle)
            with _local_mutex_guard:
                _local_mutexes.discard(self._name)

    def __enter__(self) -> "WindowsRunLock":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()


class WindowsActivationSecurityBackend:
    def capabilities(self) -> SecurityCapabilities:
        return SecurityCapabilities(
            handle_bound_files=True,
            private_owner_acl=True,
            reparse_protection=True,
            durable_atomic_writes=True,
            durable_append=True,
            exclusive_run_lock=True,
            abandoned_lock_detection=True,
            suspended_process_launch=True,
            job_object_containment=True,
            process_image_attestation=True,
        )

    def current_operator_binding(self) -> OperatorBinding:
        return OperatorBinding(hashlib.sha256(_current_sid_bytes()).hexdigest())

    def inspect_private_path(
        self, path: Path, purpose: str
    ) -> BoundFileSnapshot:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        handle = _open_read_handle(candidate)
        try:
            return _snapshot(
                handle,
                require_current_owner=purpose not in {
                    "process-image",
                    "test-executable",
                    "toolchain-executable",
                },
            )
        finally:
            _close_handle(handle)

    def inspect_open_file_descriptor(
        self, descriptor: int, purpose: str
    ) -> BoundFileSnapshot:
        del purpose
        handle = msvcrt.get_osfhandle(descriptor)
        if handle == INVALID_HANDLE_VALUE:
            raise SecurityBoundaryError("FILE_HANDLE_INVALID")
        return _snapshot(int(handle), require_current_owner=True)

    def validate_private_directory(self, path: Path) -> str:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        handle = _open_directory_handle(candidate)
        try:
            information = BY_HANDLE_FILE_INFORMATION()
            if not kernel32.GetFileInformationByHandle(
                handle, ctypes.byref(information)
            ):
                _raise_last_error("DIRECTORY_INFORMATION_READ_FAILED")
            if not information.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY:
                raise SecurityBoundaryError("DIRECTORY_REQUIRED")
            if information.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
                raise SecurityBoundaryError("REPARSE_POINT_REJECTED")
            _security_hashes(handle, require_current_owner=True)
            return hashlib.sha256(
                _final_path(handle).casefold().encode("utf-8")
            ).hexdigest()
        finally:
            _close_handle(handle)

    @contextmanager
    def open_bound_read(
        self, path: Path, expected_binding: BoundFileSnapshot
    ) -> Iterator[BinaryIO]:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        handle = _open_read_handle(candidate)
        try:
            if _snapshot(handle, require_current_owner=False) != expected_binding:
                raise SecurityBoundaryError("FILE_BINDING_MISMATCH")
            with _duplicate_for_python(handle) as stream:
                yield stream
        finally:
            _close_handle(handle)

    def atomic_write(self, path: Path, payload: bytes) -> BoundFileSnapshot:
        target = Path(path)
        if not target.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            return self.inspect_private_path(target, purpose="atomic-write")
        finally:
            if temporary.exists():
                temporary.unlink()

    def append_and_flush(self, path: Path, payload: bytes) -> BoundFileSnapshot:
        target = Path(path)
        if not target.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        with target.open("ab") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        return self.inspect_private_path(target, purpose="append")

    def flush_directory(self, path: Path) -> None:
        handle = _open_directory_handle(Path(path))
        try:
            if not kernel32.FlushFileBuffers(handle):
                error = ctypes.get_last_error()
                # Some Windows filesystems reject directory flush even when
                # every file handle was durably flushed. Reject all errors
                # except the documented invalid-function response.
                if error != 1:
                    _raise_last_error("DIRECTORY_FLUSH_FAILED")
        finally:
            _close_handle(handle)

    def acquire_run_lock(self, target_binding: str) -> WindowsRunLock:
        if len(target_binding) != 64 or any(
            character not in "0123456789abcdef" for character in target_binding
        ):
            raise SecurityBoundaryError("RUN_LOCK_BINDING_INVALID")
        name = "Local\\NaC-Activation-" + hashlib.sha256(
            target_binding.encode("ascii")
        ).hexdigest()
        with _local_mutex_guard:
            if name in _local_mutexes:
                raise SecurityBoundaryError("RUN_LOCK_HELD")
            _local_mutexes.add(name)
        descriptor = wintypes.LPVOID()
        descriptor_size = wintypes.DWORD()
        sddl = f"D:P(A;;GA;;;{_current_sid_string()})(A;;GA;;;SY)(A;;GA;;;BA)"
        if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), ctypes.byref(descriptor_size)
        ):
            with _local_mutex_guard:
                _local_mutexes.discard(name)
            _raise_last_error("RUN_LOCK_SECURITY_FAILED")
        attributes = SECURITY_ATTRIBUTES(
            ctypes.sizeof(SECURITY_ATTRIBUTES), descriptor, False
        )
        try:
            handle = kernel32.CreateMutexW(ctypes.byref(attributes), False, name)
        finally:
            kernel32.LocalFree(descriptor)
        if not handle:
            with _local_mutex_guard:
                _local_mutexes.discard(name)
            _raise_last_error("RUN_LOCK_CREATE_FAILED")
        status = kernel32.WaitForSingleObject(handle, 0)
        if status == WAIT_TIMEOUT:
            _close_handle(handle)
            with _local_mutex_guard:
                _local_mutexes.discard(name)
            raise SecurityBoundaryError("RUN_LOCK_HELD")
        if status not in (WAIT_OBJECT_0, WAIT_ABANDONED):
            _close_handle(handle)
            with _local_mutex_guard:
                _local_mutexes.discard(name)
            raise SecurityBoundaryError("RUN_LOCK_ACQUIRE_FAILED")
        return WindowsRunLock(
            int(handle),
            name,
            "abandoned" if status == WAIT_ABANDONED else "normal",
            target_binding,
        )

    def launch_attested_process(self, spec: ProcessSpec) -> ProcessResult:
        from .azure_live_commands_win import launch_attested_process

        return launch_attested_process(spec)

    def inspect_process_image(self, process_handle: int) -> str:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(
            process_handle, 0, buffer, ctypes.byref(size)
        ):
            _raise_last_error("PROCESS_IMAGE_READ_FAILED")
        return self.inspect_private_path(
            Path(buffer.value), purpose="process-image"
        ).sha256


__all__ = ["WindowsActivationSecurityBackend", "WindowsRunLock"]
