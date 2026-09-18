from __future__ import annotations

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import io
import msvcrt
import os
from pathlib import Path
import secrets
import threading
from typing import BinaryIO, Iterator

from .activation_security_backend import (
    BoundFileSnapshot,
    OperatorBinding,
    PrivateFileMetadata,
    ProcessResult,
    ProcessSpec,
    SecureDirectoryBinding,
    SecurityBoundaryError,
    SecurityCapabilities,
)


if os.name != "nt":  # pragma: no cover - module is selected only on Windows
    raise ImportError("Windows activation security backend requires Windows")


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

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
kernel32.SetFileInformationByHandle.argtypes = (
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
)
kernel32.SetFileInformationByHandle.restype = wintypes.BOOL
kernel32.WriteFile.argtypes = (
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.LPVOID,
)
kernel32.WriteFile.restype = wintypes.BOOL
kernel32.GetFileAttributesW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetFileAttributesW.restype = wintypes.DWORD
kernel32.GetVolumePathNameW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    wintypes.DWORD,
)
kernel32.GetVolumePathNameW.restype = wintypes.BOOL
kernel32.GetDriveTypeW.argtypes = (wintypes.LPCWSTR,)
kernel32.GetDriveTypeW.restype = wintypes.UINT
kernel32.GetVolumeInformationW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(wintypes.DWORD),
    wintypes.LPWSTR,
    wintypes.DWORD,
)
kernel32.GetVolumeInformationW.restype = wintypes.BOOL
kernel32.CreateDirectoryW.argtypes = (wintypes.LPCWSTR, wintypes.LPVOID)
kernel32.CreateDirectoryW.restype = wintypes.BOOL
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
GENERIC_WRITE = 0x40000000
FILE_APPEND_DATA = 0x00000004
FILE_READ_ATTRIBUTES = 0x00000080
READ_CONTROL = 0x00020000
DELETE = 0x00010000
FILE_ADD_SUBDIRECTORY = 0x00000004
FILE_TRAVERSE = 0x00000020
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
CREATE_NEW = 1
OPEN_ALWAYS = 4
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_ATTRIBUTE_DIRECTORY = 0x00000010
FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
FILE_TYPE_DISK = 0x0001
INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
DRIVE_FIXED = 3
TOKEN_QUERY = 0x0008
TOKEN_USER = 1
OWNER_SECURITY_INFORMATION = 0x00000001
DACL_SECURITY_INFORMATION = 0x00000004
SE_FILE_OBJECT = 1
WAIT_OBJECT_0 = 0x00000000
WAIT_ABANDONED = 0x00000080
WAIT_TIMEOUT = 0x00000102

_RESERVED_DEVICE_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


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


class FILE_DISPOSITION_INFO(ctypes.Structure):
    _fields_ = [("DeleteFile", wintypes.BOOL)]


class FILE_RENAME_INFO(ctypes.Structure):
    _fields_ = [
        ("ReplaceIfExists", wintypes.BOOL),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
        ("FileName", wintypes.WCHAR * 1),
    ]


class FILE_RENAME_INFO_EX(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("RootDirectory", wintypes.HANDLE),
        ("FileNameLength", wintypes.DWORD),
        ("FileName", wintypes.WCHAR * 1),
    ]


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.USHORT),
        ("MaximumLength", wintypes.USHORT),
        ("Buffer", wintypes.LPWSTR),
    ]


class OBJECT_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Length", wintypes.ULONG),
        ("RootDirectory", wintypes.HANDLE),
        ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
        ("Attributes", wintypes.ULONG),
        ("SecurityDescriptor", wintypes.LPVOID),
        ("SecurityQualityOfService", wintypes.LPVOID),
    ]


class IO_STATUS_BLOCK(ctypes.Structure):
    _fields_ = [("Status", ctypes.c_ssize_t), ("Information", ctypes.c_size_t)]


ntdll.NtCreateFile.argtypes = (
    ctypes.POINTER(wintypes.HANDLE),
    wintypes.DWORD,
    ctypes.POINTER(OBJECT_ATTRIBUTES),
    ctypes.POINTER(IO_STATUS_BLOCK),
    ctypes.POINTER(ctypes.c_longlong),
    wintypes.ULONG,
    wintypes.ULONG,
    wintypes.ULONG,
    wintypes.ULONG,
    wintypes.LPVOID,
    wintypes.ULONG,
)
ntdll.NtCreateFile.restype = ctypes.c_long
ntdll.RtlNtStatusToDosError.argtypes = (ctypes.c_long,)
ntdll.RtlNtStatusToDosError.restype = wintypes.ULONG
ntdll.NtSetInformationFile.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(IO_STATUS_BLOCK),
    wintypes.LPVOID,
    wintypes.ULONG,
    wintypes.ULONG,
)
ntdll.NtSetInformationFile.restype = ctypes.c_long

FILE_OPEN = 1
FILE_CREATE = 2
FILE_NON_DIRECTORY_FILE = 0x00000040
FILE_DIRECTORY_FILE = 0x00000001
FILE_SYNCHRONOUS_IO_NONALERT = 0x00000020
FILE_OPEN_REPARSE_POINT_OPTION = 0x00200000
SYNCHRONIZE = 0x00100000
OBJ_CASE_INSENSITIVE = 0x00000040


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


def _volume_root(path: Path) -> str:
    buffer = ctypes.create_unicode_buffer(32768)
    if not kernel32.GetVolumePathNameW(str(path), buffer, len(buffer)):
        _raise_last_error("VOLUME_PATH_READ_FAILED")
    return buffer.value


def _drive_type(path: Path) -> int:
    return int(kernel32.GetDriveTypeW(_volume_root(path)))


def _validate_supported_local_path(path: Path) -> None:
    candidate = Path(os.path.abspath(path))
    if _drive_type(candidate) != DRIVE_FIXED:
        raise SecurityBoundaryError("LOCAL_FIXED_VOLUME_REQUIRED")
    filesystem = ctypes.create_unicode_buffer(64)
    if not kernel32.GetVolumeInformationW(
        _volume_root(candidate),
        None,
        0,
        None,
        None,
        None,
        filesystem,
        len(filesystem),
    ):
        _raise_last_error("FILESYSTEM_READ_FAILED")
    if filesystem.value.upper() != "NTFS":
        raise SecurityBoundaryError("SUPPORTED_LOCAL_FILESYSTEM_REQUIRED")
    current = Path(candidate.anchor)
    for component in candidate.parts[1:]:
        current /= component
        attributes = kernel32.GetFileAttributesW(str(current))
        if attributes == INVALID_FILE_ATTRIBUTES:
            _raise_last_error("PATH_COMPONENT_READ_FAILED")
        if attributes & FILE_ATTRIBUTE_REPARSE_POINT:
            raise SecurityBoundaryError("REPARSE_POINT_REJECTED")


def _validate_child_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or name in {"", ".", ".."}
        or name[-1:] in {" ", "."}
        or any(character in name for character in ("/", "\\", ":", "\0", "*", "?"))
        or Path(name).name != name
    ):
        raise SecurityBoundaryError("SECURE_CHILD_NAME_INVALID")
    stem = name.split(".", 1)[0].upper()
    if stem in _RESERVED_DEVICE_NAMES:
        raise SecurityBoundaryError("SECURE_CHILD_NAME_INVALID")
    return name


@contextmanager
def _private_security_attributes(*, directory: bool) -> Iterator[SECURITY_ATTRIBUTES]:
    descriptor = wintypes.LPVOID()
    descriptor_size = wintypes.DWORD()
    inheritance = "OICI" if directory else ""
    sid = _current_sid_string()
    sddl = (
        "D:P"
        f"(A;{inheritance};GA;;;{sid})"
        f"(A;{inheritance};GA;;;SY)"
        f"(A;{inheritance};GA;;;BA)"
    )
    if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, 1, ctypes.byref(descriptor), ctypes.byref(descriptor_size)
    ):
        _raise_last_error("PRIVATE_SECURITY_DESCRIPTOR_CREATE_FAILED")
    try:
        yield SECURITY_ATTRIBUTES(
            ctypes.sizeof(SECURITY_ATTRIBUTES), descriptor, False
        )
    finally:
        kernel32.LocalFree(descriptor)


def _open_relative_child(
    directory_handle: int,
    name: str,
    *,
    desired_access: int,
    share_access: int,
    create: bool,
) -> int | None:
    child = _validate_child_name(name)
    name_buffer = ctypes.create_unicode_buffer(child)
    unicode_name = UNICODE_STRING(
        len(child.encode("utf-16-le")),
        len(child.encode("utf-16-le")) + 2,
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    handle = wintypes.HANDLE()
    status_block = IO_STATUS_BLOCK()
    security_descriptor = wintypes.LPVOID()
    security_size = wintypes.DWORD()
    if create:
        sid = _current_sid_string()
        sddl = f"D:P(A;;GA;;;{sid})(A;;GA;;;SY)(A;;GA;;;BA)"
        if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl,
            1,
            ctypes.byref(security_descriptor),
            ctypes.byref(security_size),
        ):
            _raise_last_error("PRIVATE_SECURITY_DESCRIPTOR_CREATE_FAILED")
    attributes = OBJECT_ATTRIBUTES(
        ctypes.sizeof(OBJECT_ATTRIBUTES),
        wintypes.HANDLE(directory_handle),
        ctypes.pointer(unicode_name),
        OBJ_CASE_INSENSITIVE,
        security_descriptor,
        None,
    )
    try:
        status = ntdll.NtCreateFile(
            ctypes.byref(handle),
            desired_access | SYNCHRONIZE,
            ctypes.byref(attributes),
            ctypes.byref(status_block),
            None,
            FILE_ATTRIBUTE_NORMAL,
            share_access,
            FILE_CREATE if create else FILE_OPEN,
            FILE_NON_DIRECTORY_FILE
            | FILE_SYNCHRONOUS_IO_NONALERT
            | FILE_OPEN_REPARSE_POINT_OPTION,
            None,
            0,
        )
    finally:
        if security_descriptor:
            kernel32.LocalFree(security_descriptor)
    if status < 0:
        error = int(ntdll.RtlNtStatusToDosError(status))
        if not create and error in {2, 3}:
            return None
        raise SecurityBoundaryError(
            f"RELATIVE_FILE_OPEN_FAILED_{error}"
            if error
            else "RELATIVE_FILE_OPEN_FAILED"
        )
    return int(handle.value)


def _open_relative_directory(
    parent_handle: int,
    name: str,
    *,
    desired_access: int,
    share_access: int,
    create: bool,
) -> int:
    component = _validate_child_name(name)
    name_buffer = ctypes.create_unicode_buffer(component)
    encoded_length = len(component.encode("utf-16-le"))
    unicode_name = UNICODE_STRING(
        encoded_length,
        encoded_length + 2,
        ctypes.cast(name_buffer, wintypes.LPWSTR),
    )
    descriptor = wintypes.LPVOID()
    descriptor_size = wintypes.DWORD()
    if create:
        sid = _current_sid_string()
        sddl = (
            "D:P"
            f"(A;OICI;GA;;;{sid})"
            "(A;OICI;GA;;;SY)(A;OICI;GA;;;BA)"
        )
        if not advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), ctypes.byref(descriptor_size)
        ):
            _raise_last_error("PRIVATE_SECURITY_DESCRIPTOR_CREATE_FAILED")
    attributes = OBJECT_ATTRIBUTES(
        ctypes.sizeof(OBJECT_ATTRIBUTES),
        wintypes.HANDLE(parent_handle),
        ctypes.pointer(unicode_name),
        OBJ_CASE_INSENSITIVE,
        descriptor,
        None,
    )
    handle = wintypes.HANDLE()
    io_status = IO_STATUS_BLOCK()
    try:
        status = ntdll.NtCreateFile(
            ctypes.byref(handle),
            desired_access | SYNCHRONIZE,
            ctypes.byref(attributes),
            ctypes.byref(io_status),
            None,
            FILE_ATTRIBUTE_NORMAL,
            share_access,
            FILE_CREATE if create else FILE_OPEN,
            FILE_DIRECTORY_FILE | FILE_SYNCHRONOUS_IO_NONALERT | FILE_OPEN_REPARSE_POINT_OPTION,
            None,
            0,
        )
    finally:
        if descriptor:
            kernel32.LocalFree(descriptor)
    if status < 0:
        error = int(ntdll.RtlNtStatusToDosError(status))
        raise SecurityBoundaryError(f"DIRECTORY_OPEN_FAILED_{error}")
    return int(handle.value)


def _normalized_final_path(value: str) -> str:
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    if value.startswith("\\\\?\\"):
        return value[4:]
    return value


def _require_requested_path_binding(handle: int, path: Path) -> None:
    requested = os.path.normcase(os.path.abspath(path))
    final = os.path.normcase(_normalized_final_path(_final_path(handle)))
    if requested != final:
        raise SecurityBoundaryError("FINAL_PATH_BINDING_MISMATCH")


def _open_directory_handle(path: Path) -> int:
    handle = kernel32.CreateFileW(
        str(path),
        GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
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
    return _normalized_final_path(buffer.value)


def _sid_string(sid: int) -> str:
    value = wintypes.LPWSTR()
    if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(value)):
        _raise_last_error("SID_READ_FAILED")
    try:
        return value.value
    finally:
        kernel32.LocalFree(value)


def _security_hashes(
    handle: int,
    *,
    require_current_owner: bool,
    require_restrictive_dacl: bool = True,
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
        if require_restrictive_dacl:
            _require_restrictive_dacl(
                dacl.value,
                dacl_bytes,
                owner_sid=_sid_string(owner.value),
            )
        return (
            hashlib.sha256(owner_bytes).hexdigest(),
            hashlib.sha256(descriptor_bytes).hexdigest(),
            hashlib.sha256(dacl_bytes).hexdigest(),
        )
    finally:
        kernel32.LocalFree(descriptor)


def _require_restrictive_dacl(
    dacl: int,
    raw: bytes,
    *,
    owner_sid: str,
) -> None:
    ace_count = int.from_bytes(raw[4:6], "little")
    writable_principals = {
        _current_sid_string(),
        "S-1-3-0",  # CREATOR_OWNER, resolves to the creating principal
        "S-1-3-4",  # OWNER_RIGHTS, scoped to the bound owner
        "S-1-5-18",  # LOCAL_SYSTEM
        "S-1-5-32-544",  # BUILTIN\\Administrators
        owner_sid,
    }
    write_mask = (
        0x00000002
        | 0x00000004
        | 0x00000010
        | 0x00000040
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
        ace_flags = header[1]
        ace_size = int.from_bytes(header[2:4], "little")
        if ace_size < 8:
            raise SecurityBoundaryError("FILE_DACL_INVALID")
        if ace_type in {4, 5, 9, 11}:
            raise SecurityBoundaryError("FILE_DACL_UNSUPPORTED_ALLOW_ACE")
        if ace_type != 0:  # only ACCESS_ALLOWED_ACE has a fixed SID offset
            continue
        mask = int.from_bytes(header[4:8], "little")
        principal = _sid_string(ace.value + 8)
        if principal == "S-1-3-0" and (
            not ace_flags & 0x08 or not ace_flags & 0x03
        ):
            raise SecurityBoundaryError("FILE_DACL_TOO_BROAD")
        if (
            mask & write_mask
            and principal not in writable_principals
        ):
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


def _snapshot(
    handle: int,
    *,
    require_current_owner: bool = True,
    require_restrictive_dacl: bool = True,
    require_single_link: bool = True,
) -> BoundFileSnapshot:
    information = BY_HANDLE_FILE_INFORMATION()
    if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(information)):
        _raise_last_error("FILE_INFORMATION_READ_FAILED")
    if kernel32.GetFileType(handle) != FILE_TYPE_DISK:
        raise SecurityBoundaryError("NON_DISK_PATH_REJECTED")
    reparse = bool(information.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
    if reparse:
        raise SecurityBoundaryError("REPARSE_POINT_REJECTED")
    if information.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY:
        raise SecurityBoundaryError("REGULAR_FILE_REQUIRED")
    if require_single_link and information.nNumberOfLinks != 1:
        raise SecurityBoundaryError("FILE_LINK_COUNT_INVALID")
    if not kernel32.SetFilePointerEx(handle, 0, None, 0):
        _raise_last_error("FILE_SEEK_FAILED")
    with _duplicate_for_python(handle) as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if not kernel32.SetFilePointerEx(handle, 0, None, 0):
        _raise_last_error("FILE_SEEK_FAILED")
    owner_hash, descriptor_hash, dacl_hash = _security_hashes(
        handle,
        require_current_owner=require_current_owner,
        require_restrictive_dacl=require_restrictive_dacl,
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


def _metadata_snapshot(
    handle: int, *, require_current_owner: bool = True
) -> PrivateFileMetadata:
    information = BY_HANDLE_FILE_INFORMATION()
    if not kernel32.GetFileInformationByHandle(handle, ctypes.byref(information)):
        _raise_last_error("FILE_INFORMATION_READ_FAILED")
    if kernel32.GetFileType(handle) != FILE_TYPE_DISK:
        raise SecurityBoundaryError("NON_DISK_PATH_REJECTED")
    reparse = bool(information.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT)
    if reparse:
        raise SecurityBoundaryError("REPARSE_POINT_REJECTED")
    if information.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY:
        raise SecurityBoundaryError("REGULAR_FILE_REQUIRED")
    if information.nNumberOfLinks != 1:
        raise SecurityBoundaryError("FILE_LINK_COUNT_INVALID")
    owner_hash, descriptor_hash, dacl_hash = _security_hashes(
        handle, require_current_owner=require_current_owner
    )
    canonical = _final_path(handle).casefold().encode("utf-8")
    return PrivateFileMetadata(
        path_sha256=hashlib.sha256(canonical).hexdigest(),
        volume_serial=information.dwVolumeSerialNumber,
        file_id=(information.nFileIndexHigh << 32) | information.nFileIndexLow,
        size=(information.nFileSizeHigh << 32) | information.nFileSizeLow,
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


class WindowsSecureDirectorySession:
    """Retain every verified path component for one protected operation."""

    def __init__(
        self,
        backend: "WindowsActivationSecurityBackend",
        path: Path,
        handles: list[int],
        binding: SecureDirectoryBinding,
    ) -> None:
        self._backend = backend
        self.path = path
        self._handles = handles
        self.binding = binding

    def __enter__(self) -> "WindowsSecureDirectorySession":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        handles, self._handles = self._handles, []
        for handle in reversed(handles):
            _close_handle(handle)

    def _require_open(self) -> None:
        if not self._handles:
            raise SecurityBoundaryError("SECURE_DIRECTORY_SESSION_CLOSED")

    def _require_directory_path(self) -> None:
        self._require_open()
        _require_requested_path_binding(self._handles[-1], self.path)

    def canonical_child_path(self, name: str) -> Path:
        self._require_directory_path()
        return self.path / _validate_child_name(name)

    def open_secure_child_directory(
        self, name: str, *, create: bool
    ) -> "WindowsSecureDirectorySession":
        """Open one child relative to this retained, verified directory handle."""

        target = self.canonical_child_path(name)
        try:
            handle = _open_relative_directory(
                self._handles[-1],
                name,
                desired_access=(
                    FILE_READ_ATTRIBUTES | READ_CONTROL | GENERIC_WRITE
                ),
                share_access=FILE_SHARE_READ | FILE_SHARE_WRITE,
                create=False,
            )
        except SecurityBoundaryError as error:
            if error.code.endswith("_267"):
                raise SecurityBoundaryError("DIRECTORY_REQUIRED") from None
            if not create or not error.code.endswith(("_2", "_3")):
                raise
            handle = _open_relative_directory(
                self._handles[-1],
                name,
                desired_access=(
                    FILE_READ_ATTRIBUTES | READ_CONTROL | GENERIC_WRITE
                ),
                share_access=FILE_SHARE_READ | FILE_SHARE_WRITE,
                create=True,
            )
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
            _require_requested_path_binding(handle, target)
            owner, descriptor, dacl = _security_hashes(
                handle,
                require_current_owner=True,
                require_restrictive_dacl=True,
            )
            if int(information.dwVolumeSerialNumber) != self.binding.volume_serial:
                raise SecurityBoundaryError("SECURE_DIRECTORY_VOLUME_MISMATCH")
            binding = SecureDirectoryBinding(
                path_sha256=hashlib.sha256(
                    _final_path(handle).casefold().encode("utf-8")
                ).hexdigest(),
                volume_serial=int(information.dwVolumeSerialNumber),
                file_id=(int(information.nFileIndexHigh) << 32)
                | int(information.nFileIndexLow),
                owner_sid_sha256=owner,
                security_descriptor_sha256=descriptor,
                dacl_sha256=dacl,
            )
            child = WindowsSecureDirectorySession(
                self._backend, target, [handle], binding
            )
            handle = 0
            return child
        finally:
            _close_handle(handle)

    def inspect_optional_child(
        self, name: str, purpose: str
    ) -> BoundFileSnapshot | None:
        target = self.canonical_child_path(name)
        handle = _open_relative_child(
            self._handles[-1],
            name,
            desired_access=GENERIC_READ,
            share_access=FILE_SHARE_READ,
            create=False,
        )
        if handle is None:
            return None
        try:
            _require_requested_path_binding(handle, target)
            system_toolchain = purpose in {
                "process-image",
                "toolchain-executable",
            }
            snapshot = _snapshot(
                handle,
                require_current_owner=purpose not in {
                    "process-image",
                    "test-executable",
                    "toolchain-executable",
                },
                require_restrictive_dacl=True,
                require_single_link=not system_toolchain,
            )
            if snapshot.volume_serial != self.binding.volume_serial:
                raise SecurityBoundaryError("SECURE_CHILD_VOLUME_MISMATCH")
            return snapshot
        finally:
            _close_handle(handle)

    def read_bounded(self, name: str, maximum_bytes: int) -> bytes | None:
        if type(maximum_bytes) is not int or maximum_bytes < 0:
            raise SecurityBoundaryError("SECURE_READ_LIMIT_INVALID")
        descriptor = self.open_regular_descriptor(name, create=False)
        if descriptor < 0:
            return None
        try:
            metadata = os.fstat(descriptor)
            if metadata.st_size > maximum_bytes:
                raise SecurityBoundaryError("SECURE_READ_LIMIT_EXCEEDED")
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                payload = stream.read(maximum_bytes + 1)
            if len(payload) > maximum_bytes:
                raise SecurityBoundaryError("SECURE_READ_LIMIT_EXCEEDED")
            return payload
        finally:
            if descriptor >= 0:
                os.close(descriptor)

    def open_regular_descriptor(self, name: str, *, create: bool) -> int:
        target = self.canonical_child_path(name)
        handle = _open_relative_child(
            self._handles[-1],
            name,
            desired_access=GENERIC_READ | GENERIC_WRITE,
            share_access=FILE_SHARE_READ,
            create=False,
        )
        if handle is None:
            if not create:
                return -1
            handle = _open_relative_child(
                self._handles[-1],
                name,
                desired_access=GENERIC_READ | GENERIC_WRITE,
                share_access=FILE_SHARE_READ,
                create=True,
            )
            assert handle is not None
        integer_handle = handle
        try:
            _require_requested_path_binding(integer_handle, target)
            snapshot = _snapshot(integer_handle, require_current_owner=True)
            if snapshot.volume_serial != self.binding.volume_serial:
                raise SecurityBoundaryError("SECURE_CHILD_VOLUME_MISMATCH")
            descriptor = msvcrt.open_osfhandle(integer_handle, os.O_RDWR)
            integer_handle = 0
            return descriptor
        finally:
            _close_handle(integer_handle)

    def atomic_write(self, name: str, payload: bytes) -> BoundFileSnapshot:
        target = self.canonical_child_path(name)
        temporary_name = _validate_child_name(
            f".{name}.{secrets.token_hex(16)}.tmp"
        )
        handle = INVALID_HANDLE_VALUE
        published = False
        try:
            handle = _open_relative_child(
                self._handles[-1],
                temporary_name,
                desired_access=GENERIC_READ | GENERIC_WRITE | DELETE,
                share_access=FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                create=True,
            )
            assert handle is not None
            integer_handle = handle
            offset = 0
            while offset < len(payload):
                chunk = payload[offset : offset + 1024 * 1024]
                buffer = ctypes.create_string_buffer(chunk)
                written = wintypes.DWORD()
                if not kernel32.WriteFile(
                    integer_handle,
                    buffer,
                    len(chunk),
                    ctypes.byref(written),
                    None,
                ):
                    _raise_last_error("FILE_WRITE_FAILED")
                if written.value != len(chunk):
                    raise SecurityBoundaryError("FILE_WRITE_INCOMPLETE")
                offset += written.value
            if not kernel32.FlushFileBuffers(integer_handle):
                _raise_last_error("FILE_FLUSH_FAILED")
            if not kernel32.SetFilePointerEx(integer_handle, 0, None, 0):
                _raise_last_error("FILE_SEEK_FAILED")
            temporary_binding = _snapshot(
                integer_handle, require_current_owner=True
            )
            if temporary_binding.volume_serial != self.binding.volume_serial:
                raise SecurityBoundaryError("SECURE_CHILD_VOLUME_MISMATCH")

            encoded_name = name.encode("utf-16-le")
            size = FILE_RENAME_INFO.FileName.offset + len(encoded_name)
            rename_buffer = ctypes.create_string_buffer(size)
            rename = ctypes.cast(
                rename_buffer, ctypes.POINTER(FILE_RENAME_INFO)
            ).contents
            rename.ReplaceIfExists = True
            rename.RootDirectory = wintypes.HANDLE(self._handles[-1])
            rename.FileNameLength = len(encoded_name)
            ctypes.memmove(
                ctypes.addressof(rename_buffer) + FILE_RENAME_INFO.FileName.offset,
                encoded_name,
                len(encoded_name),
            )
            rename_io = IO_STATUS_BLOCK()
            rename_status = ntdll.NtSetInformationFile(
                integer_handle,
                ctypes.byref(rename_io),
                rename_buffer,
                size,
                10,
            )
            if rename_status < 0:
                error = int(ntdll.RtlNtStatusToDosError(rename_status))
                raise SecurityBoundaryError(
                    f"FILE_ATOMIC_RENAME_FAILED_{error}"
                )
            published = True
            self.flush()
            _require_requested_path_binding(integer_handle, target)
            result = _snapshot(integer_handle, require_current_owner=True)
            if result.volume_serial != self.binding.volume_serial:
                raise SecurityBoundaryError("SECURE_CHILD_VOLUME_MISMATCH")
            return result
        finally:
            if handle not in (INVALID_HANDLE_VALUE, None, 0):
                if not published:
                    disposition = FILE_DISPOSITION_INFO(True)
                    kernel32.SetFileInformationByHandle(
                        handle,
                        4,
                        ctypes.byref(disposition),
                        ctypes.sizeof(disposition),
                    )
                _close_handle(int(handle))

    def create_exclusive(self, name: str, payload: bytes) -> BoundFileSnapshot:
        target = self.canonical_child_path(name)
        try:
            handle = _open_relative_child(
                self._handles[-1],
                name,
                desired_access=GENERIC_READ | GENERIC_WRITE | DELETE,
                share_access=FILE_SHARE_READ,
                create=True,
            )
        except SecurityBoundaryError as exc:
            if exc.code.endswith(("_80", "_183")):
                raise SecurityBoundaryError("SECURE_CHILD_ALREADY_EXISTS") from None
            raise
        assert handle is not None
        try:
            offset = 0
            while offset < len(payload):
                chunk = payload[offset : offset + 1024 * 1024]
                buffer = ctypes.create_string_buffer(chunk)
                written = wintypes.DWORD()
                if not kernel32.WriteFile(
                    handle,
                    buffer,
                    len(chunk),
                    ctypes.byref(written),
                    None,
                ):
                    _raise_last_error("FILE_WRITE_FAILED")
                if written.value != len(chunk):
                    raise SecurityBoundaryError("FILE_WRITE_INCOMPLETE")
                offset += written.value
            if not kernel32.FlushFileBuffers(handle):
                _raise_last_error("FILE_FLUSH_FAILED")
            _require_requested_path_binding(handle, target)
            result = _snapshot(handle, require_current_owner=True)
            if result.volume_serial != self.binding.volume_serial:
                raise SecurityBoundaryError("SECURE_CHILD_VOLUME_MISMATCH")
            self.flush()
            return result
        except BaseException:
            disposition = FILE_DISPOSITION_INFO(True)
            kernel32.SetFileInformationByHandle(
                handle,
                4,
                ctypes.byref(disposition),
                ctypes.sizeof(disposition),
            )
            raise
        finally:
            _close_handle(handle)

    def append_and_flush(
        self, name: str, payload: bytes
    ) -> BoundFileSnapshot:
        descriptor = self.open_regular_descriptor(name, create=True)
        try:
            os.lseek(descriptor, 0, os.SEEK_END)
            os.write(descriptor, payload)
            os.fsync(descriptor)
            result = _snapshot(
                int(msvcrt.get_osfhandle(descriptor)),
                require_current_owner=True,
            )
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return result

    def delete_child(self, name: str) -> bool:
        target = self.canonical_child_path(name)
        expected = self.inspect_optional_child(name, "secure-delete")
        if expected is None:
            return False
        handle = _open_relative_child(
            self._handles[-1],
            name,
            desired_access=GENERIC_READ | DELETE | FILE_READ_ATTRIBUTES | READ_CONTROL,
            share_access=FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            create=False,
        )
        if handle is None:
            return False
        try:
            _require_requested_path_binding(int(handle), target)
            if _snapshot(int(handle), require_current_owner=True) != expected:
                raise SecurityBoundaryError("FILE_BINDING_MISMATCH")
            disposition = FILE_DISPOSITION_INFO(True)
            if not kernel32.SetFileInformationByHandle(
                handle,
                4,
                ctypes.byref(disposition),
                ctypes.sizeof(disposition),
            ):
                _raise_last_error("FILE_DELETE_FAILED")
        finally:
            _close_handle(int(handle))
        self.flush()
        return True

    def flush(self) -> None:
        self._require_open()
        if not kernel32.FlushFileBuffers(self._handles[-1]):
            error = ctypes.get_last_error()
            if error != 1:
                _raise_last_error("DIRECTORY_FLUSH_FAILED")


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
        require_owner = purpose not in {
            "process-image",
            "test-executable",
            "toolchain-executable",
        }
        with self.open_secure_directory(
            candidate.parent,
            create=False,
            require_current_owner=require_owner,
            require_restrictive_dacl=require_owner,
        ) as session:
            result = session.inspect_optional_child(candidate.name, purpose)
            if result is None:
                raise SecurityBoundaryError("FILE_OPEN_FAILED_2")
            return result

    def inspect_open_file_descriptor(
        self, descriptor: int, purpose: str
    ) -> BoundFileSnapshot:
        del purpose
        handle = msvcrt.get_osfhandle(descriptor)
        if handle == INVALID_HANDLE_VALUE:
            raise SecurityBoundaryError("FILE_HANDLE_INVALID")
        return _snapshot(int(handle), require_current_owner=True)

    def inspect_open_file_metadata(
        self, descriptor: int, purpose: str
    ) -> PrivateFileMetadata:
        del purpose
        handle = msvcrt.get_osfhandle(descriptor)
        if handle == INVALID_HANDLE_VALUE:
            raise SecurityBoundaryError("FILE_HANDLE_INVALID")
        return _metadata_snapshot(int(handle), require_current_owner=True)

    def inspect_private_metadata(
        self, path: Path, purpose: str
    ) -> PrivateFileMetadata:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        require_owner = purpose not in {
            "process-image",
            "test-executable",
            "toolchain-executable",
        }
        with self.open_secure_directory(
            candidate.parent,
            create=False,
            require_current_owner=require_owner,
        ) as session:
            handle = _open_relative_child(
                session._handles[-1],
                candidate.name,
                desired_access=GENERIC_READ,
                share_access=FILE_SHARE_READ,
                create=False,
            )
            if handle is None:
                raise SecurityBoundaryError("FILE_OPEN_FAILED_2")
            try:
                _require_requested_path_binding(handle, candidate)
                return _metadata_snapshot(
                    handle, require_current_owner=require_owner
                )
            finally:
                _close_handle(handle)

    def validate_private_directory(self, path: Path) -> str:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        with self.open_secure_directory(candidate, create=False) as session:
            return session.binding.path_sha256

    def open_secure_directory(
        self,
        path: Path,
        *,
        create: bool,
        require_current_owner: bool = True,
        require_restrictive_dacl: bool = True,
    ) -> WindowsSecureDirectorySession:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        candidate = Path(os.path.abspath(candidate))
        if candidate.drive.startswith("\\") or str(candidate).startswith(
            ("\\\\.\\", "\\\\?\\")
        ):
            raise SecurityBoundaryError("LOCAL_FIXED_VOLUME_REQUIRED")
        if _drive_type(candidate) != DRIVE_FIXED:
            raise SecurityBoundaryError("LOCAL_FIXED_VOLUME_REQUIRED")
        filesystem = ctypes.create_unicode_buffer(64)
        root = _volume_root(candidate)
        if not kernel32.GetVolumeInformationW(
            root, None, 0, None, None, None, filesystem, len(filesystem)
        ):
            _raise_last_error("FILESYSTEM_READ_FAILED")
        if filesystem.value.upper() != "NTFS":
            raise SecurityBoundaryError("SUPPORTED_LOCAL_FILESYSTEM_REQUIRED")

        handles: list[int] = []
        current = Path(candidate.anchor)
        final_index = len(candidate.parts) - 1
        try:
            for index, component in enumerate((candidate.anchor, *candidate.parts[1:])):
                if index:
                    _validate_child_name(component)
                    current /= component
                path_attributes = kernel32.GetFileAttributesW(str(current))
                if (
                    path_attributes != INVALID_FILE_ATTRIBUTES
                    and path_attributes & FILE_ATTRIBUTE_REPARSE_POINT
                ):
                    raise SecurityBoundaryError("REPARSE_POINT_REJECTED")
                create_child_access = (
                    FILE_ADD_SUBDIRECTORY
                    if create and index == final_index - 1
                    else 0
                )
                traversal_access = FILE_TRAVERSE if index < final_index else 0
                desired_access = (
                    FILE_READ_ATTRIBUTES | traversal_access | create_child_access
                ) | (
                    READ_CONTROL
                    | (GENERIC_WRITE if require_current_owner else 0)
                    if index == final_index
                    else 0
                )
                share_access = FILE_SHARE_READ | FILE_SHARE_WRITE | (
                    FILE_SHARE_DELETE
                    if index == 0 or not require_current_owner
                    else 0
                )
                if index == 0:
                    handle = kernel32.CreateFileW(
                        str(current), desired_access, share_access, None,
                        OPEN_EXISTING,
                        FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT,
                        None,
                    )
                    if handle == INVALID_HANDLE_VALUE:
                        _raise_last_error("DIRECTORY_OPEN_FAILED")
                    integer_handle = int(handle)
                else:
                    try:
                        integer_handle = _open_relative_directory(
                            handles[-1], component,
                            desired_access=desired_access,
                            share_access=share_access,
                            create=False,
                        )
                    except SecurityBoundaryError as error:
                        if not create or not error.code.endswith(("_2", "_3")):
                            raise
                        integer_handle = _open_relative_directory(
                            handles[-1], component,
                            desired_access=desired_access,
                            share_access=share_access,
                            create=True,
                        )
                handles.append(integer_handle)
                information = BY_HANDLE_FILE_INFORMATION()
                if not kernel32.GetFileInformationByHandle(
                    integer_handle, ctypes.byref(information)
                ):
                    _raise_last_error("DIRECTORY_INFORMATION_READ_FAILED")
                if not information.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY:
                    raise SecurityBoundaryError("DIRECTORY_REQUIRED")
                if information.dwFileAttributes & FILE_ATTRIBUTE_REPARSE_POINT:
                    raise SecurityBoundaryError("REPARSE_POINT_REJECTED")
                _require_requested_path_binding(integer_handle, current)
                if len(handles) > 1:
                    root_information = BY_HANDLE_FILE_INFORMATION()
                    if not kernel32.GetFileInformationByHandle(
                        handles[0], ctypes.byref(root_information)
                    ):
                        _raise_last_error("DIRECTORY_INFORMATION_READ_FAILED")
                    if (
                        information.dwVolumeSerialNumber
                        != root_information.dwVolumeSerialNumber
                    ):
                        raise SecurityBoundaryError("SECURE_DIRECTORY_VOLUME_MISMATCH")
            owner, descriptor, dacl = _security_hashes(
                handles[-1],
                require_current_owner=require_current_owner,
                require_restrictive_dacl=require_restrictive_dacl,
            )
            final_information = BY_HANDLE_FILE_INFORMATION()
            if not kernel32.GetFileInformationByHandle(
                handles[-1], ctypes.byref(final_information)
            ):
                _raise_last_error("DIRECTORY_INFORMATION_READ_FAILED")
            binding = SecureDirectoryBinding(
                path_sha256=hashlib.sha256(
                    _final_path(handles[-1]).casefold().encode("utf-8")
                ).hexdigest(),
                volume_serial=int(final_information.dwVolumeSerialNumber),
                file_id=(int(final_information.nFileIndexHigh) << 32)
                | int(final_information.nFileIndexLow),
                owner_sid_sha256=owner,
                security_descriptor_sha256=descriptor,
                dacl_sha256=dacl,
            )
            return WindowsSecureDirectorySession(
                self, candidate, handles, binding
            )
        except Exception:
            for handle in reversed(handles):
                _close_handle(handle)
            raise

    @contextmanager
    def open_bound_read(
        self, path: Path, expected_binding: BoundFileSnapshot
    ) -> Iterator[BinaryIO]:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        session = self.open_secure_directory(
            candidate.parent,
            create=False,
            require_current_owner=False,
        )
        descriptor = -1
        try:
            handle = _open_relative_child(
                session._handles[-1],
                candidate.name,
                desired_access=GENERIC_READ,
                share_access=FILE_SHARE_READ,
                create=False,
            )
            if handle is None:
                raise SecurityBoundaryError("FILE_OPEN_FAILED_2")
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
            actual = _snapshot(
                int(msvcrt.get_osfhandle(descriptor)),
                require_current_owner=False,
            )
            if actual != expected_binding:
                raise SecurityBoundaryError("FILE_BINDING_MISMATCH")
            session.close()
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                yield stream
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            session.close()

    def inspect_bound_input_path(
        self, path: Path, purpose: str
    ) -> BoundFileSnapshot:
        del purpose
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        with self.open_secure_directory(
            candidate.parent,
            create=False,
            require_current_owner=False,
            require_restrictive_dacl=False,
        ) as session:
            if session.binding.owner_sid_sha256 != self.current_operator_binding().sid_sha256:
                raise SecurityBoundaryError("FILE_OWNER_MISMATCH")
            handle = _open_relative_child(
                session._handles[-1],
                candidate.name,
                desired_access=GENERIC_READ,
                share_access=FILE_SHARE_READ,
                create=False,
            )
            if handle is None:
                raise SecurityBoundaryError("FILE_OPEN_FAILED_2")
            try:
                _require_requested_path_binding(handle, candidate)
                return _snapshot(
                    handle,
                    require_current_owner=True,
                    require_restrictive_dacl=False,
                )
            finally:
                _close_handle(handle)

    @contextmanager
    def open_bound_input_read(
        self, path: Path, expected_binding: BoundFileSnapshot
    ) -> Iterator[BinaryIO]:
        candidate = Path(path)
        if not candidate.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        session = self.open_secure_directory(
            candidate.parent,
            create=False,
            require_current_owner=False,
            require_restrictive_dacl=False,
        )
        descriptor = -1
        try:
            if session.binding.owner_sid_sha256 != self.current_operator_binding().sid_sha256:
                raise SecurityBoundaryError("FILE_OWNER_MISMATCH")
            handle = _open_relative_child(
                session._handles[-1],
                candidate.name,
                desired_access=GENERIC_READ,
                share_access=FILE_SHARE_READ,
                create=False,
            )
            if handle is None:
                raise SecurityBoundaryError("FILE_OPEN_FAILED_2")
            descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
            actual = _snapshot(
                int(msvcrt.get_osfhandle(descriptor)),
                require_current_owner=True,
                require_restrictive_dacl=False,
            )
            if actual != expected_binding:
                raise SecurityBoundaryError("FILE_BINDING_MISMATCH")
            session.close()
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                yield stream
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            session.close()

    def atomic_write(self, path: Path, payload: bytes) -> BoundFileSnapshot:
        target = Path(path)
        if not target.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        with self.open_secure_directory(target.parent, create=True) as session:
            return session.atomic_write(target.name, payload)

    def append_and_flush(self, path: Path, payload: bytes) -> BoundFileSnapshot:
        target = Path(path)
        if not target.is_absolute():
            raise SecurityBoundaryError("PATH_NOT_ABSOLUTE")
        with self.open_secure_directory(target.parent, create=True) as session:
            return session.append_and_flush(target.name, payload)

    def flush_directory(self, path: Path) -> None:
        with self.open_secure_directory(Path(path), create=False) as session:
            session.flush()

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
