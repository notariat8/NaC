"""Native Windows process boundary for M365/Azure command adapters."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import msvcrt
import os
from pathlib import Path
import subprocess
import threading

from .activation_security_backend import (
    ProcessResult,
    ProcessSpec,
    SecurityBoundaryError,
)


if os.name != "nt":  # pragma: no cover - imported only by the Windows backend
    raise ImportError("Windows live command boundary requires Windows")


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CREATE_SUSPENDED = 0x00000004
CREATE_UNICODE_ENVIRONMENT = 0x00000400
CREATE_NO_WINDOW = 0x08000000
STARTF_USESTDHANDLES = 0x00000100
HANDLE_FLAG_INHERIT = 0x00000001
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
WAIT_OBJECT_0 = 0
WAIT_TIMEOUT = 258
INFINITE = 0xFFFFFFFF
STILL_ACTIVE = 259
SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000
TOKEN_ADJUST_DEFAULT = 0x0080
TOKEN_QUERY = 0x0008
TOKEN_INTEGRITY_LEVEL = 25
SECURITY_MANDATORY_LOW_RID = 0x00001000
SE_GROUP_INTEGRITY = 0x00000020


class SECURITY_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("nLength", wintypes.DWORD),
        ("lpSecurityDescriptor", wintypes.LPVOID),
        ("bInheritHandle", wintypes.BOOL),
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class SID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Sid", wintypes.LPVOID),
        ("Attributes", wintypes.DWORD),
    ]


class TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = [("Label", SID_AND_ATTRIBUTES)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_ulonglong)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION_VALUE(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


kernel32.CreatePipe.argtypes = (
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(wintypes.HANDLE),
    ctypes.POINTER(SECURITY_ATTRIBUTES),
    wintypes.DWORD,
)
kernel32.CreatePipe.restype = wintypes.BOOL
kernel32.SetHandleInformation.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.DWORD,
)
kernel32.SetHandleInformation.restype = wintypes.BOOL
kernel32.CreateProcessW.argtypes = (
    wintypes.LPCWSTR,
    wintypes.LPWSTR,
    wintypes.LPVOID,
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.DWORD,
    wintypes.LPVOID,
    wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW),
    ctypes.POINTER(PROCESS_INFORMATION),
)
kernel32.CreateProcessW.restype = wintypes.BOOL
kernel32.CreateJobObjectW.argtypes = (wintypes.LPVOID, wintypes.LPCWSTR)
kernel32.CreateJobObjectW.restype = wintypes.HANDLE
kernel32.SetInformationJobObject.argtypes = (
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
)
kernel32.SetInformationJobObject.restype = wintypes.BOOL
kernel32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
kernel32.ResumeThread.argtypes = (wintypes.HANDLE,)
kernel32.ResumeThread.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
kernel32.TerminateJobObject.restype = wintypes.BOOL
kernel32.GetExitCodeProcess.argtypes = (
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
)
kernel32.GetExitCodeProcess.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
)
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.SetErrorMode.argtypes = (wintypes.UINT,)
kernel32.SetErrorMode.restype = wintypes.UINT
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
advapi32.OpenProcessToken.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
)
advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.ConvertStringSidToSidW.argtypes = (
    wintypes.LPCWSTR,
    ctypes.POINTER(wintypes.LPVOID),
)
advapi32.ConvertStringSidToSidW.restype = wintypes.BOOL
advapi32.SetTokenInformation.argtypes = (
    wintypes.HANDLE,
    ctypes.c_int,
    wintypes.LPVOID,
    wintypes.DWORD,
)
advapi32.SetTokenInformation.restype = wintypes.BOOL
kernel32.LocalFree.argtypes = (wintypes.HLOCAL,)
kernel32.LocalFree.restype = wintypes.HLOCAL
advapi32.GetLengthSid.argtypes = (wintypes.LPVOID,)
advapi32.GetLengthSid.restype = wintypes.DWORD

_process_creation_error_mode_lock = threading.Lock()


def _close(handle: int | None) -> None:
    if handle:
        kernel32.CloseHandle(handle)


def _fail(code: str) -> None:
    error = ctypes.get_last_error()
    raise SecurityBoundaryError(f"{code}_{error}" if error else code)


def verified_sha256(path: Path) -> str:
    from .activation_security_windows import WindowsActivationSecurityBackend

    return WindowsActivationSecurityBackend().inspect_private_path(
        Path(path), purpose="process-image"
    ).sha256


def _environment_block(environment: dict[str, str]) -> ctypes.Array[ctypes.c_wchar]:
    forbidden_fragments = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    for key, value in environment.items():
        if not key or "=" in key or "\0" in key or "\0" in value:
            raise SecurityBoundaryError("PROCESS_ENVIRONMENT_INVALID")
        if any(fragment in key.upper() for fragment in forbidden_fragments):
            raise SecurityBoundaryError("PROCESS_ENVIRONMENT_SENSITIVE")
    encoded = "\0".join(
        f"{key}={environment[key]}"
        for key in sorted(environment, key=str.casefold)
    ) + "\0\0"
    return ctypes.create_unicode_buffer(encoded)


def _pipe() -> tuple[int, int]:
    read_handle = wintypes.HANDLE()
    write_handle = wintypes.HANDLE()
    attributes = SECURITY_ATTRIBUTES(
        ctypes.sizeof(SECURITY_ATTRIBUTES), None, True
    )
    if not kernel32.CreatePipe(
        ctypes.byref(read_handle),
        ctypes.byref(write_handle),
        ctypes.byref(attributes),
        0,
    ):
        _fail("PROCESS_PIPE_CREATE_FAILED")
    if not kernel32.SetHandleInformation(read_handle, HANDLE_FLAG_INHERIT, 0):
        _close(read_handle.value)
        _close(write_handle.value)
        _fail("PROCESS_PIPE_PROTECT_FAILED")
    return int(read_handle.value), int(write_handle.value)


def _reader(handle: int, limit: int, destination: list[bytes]) -> None:
    descriptor = msvcrt.open_osfhandle(handle, os.O_RDONLY)
    retained = bytearray()
    with os.fdopen(descriptor, "rb", closefd=True) as stream:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                break
            if len(retained) <= limit:
                retained.extend(chunk[: limit + 1 - len(retained)])
    destination.append(bytes(retained))


def _process_image_path(handle: int) -> Path:
    size = wintypes.DWORD(32768)
    buffer = ctypes.create_unicode_buffer(size.value)
    if not kernel32.QueryFullProcessImageNameW(
        handle, 0, buffer, ctypes.byref(size)
    ):
        _fail("PROCESS_IMAGE_READ_FAILED")
    return Path(buffer.value)


def _apply_low_integrity_write_guard(process_handle: int) -> None:
    """Deny writes to ordinary user-profile/cache objects before resume.

    Windows mandatory integrity control applies a no-write-up rule to objects
    carrying the normal medium integrity label.  Setting the suspended child
    to low integrity therefore lets an established CLI context be read while
    preventing token refresh, cache creation and configuration rewrites in the
    user's normal profile.  Child processes inherit the restricted token.
    """

    token = wintypes.HANDLE()
    sid = wintypes.LPVOID()
    if not advapi32.OpenProcessToken(
        process_handle,
        TOKEN_ADJUST_DEFAULT | TOKEN_QUERY,
        ctypes.byref(token),
    ):
        _fail("PROCESS_CREDENTIAL_GUARD_TOKEN_OPEN_FAILED")
    try:
        if not advapi32.ConvertStringSidToSidW(
            f"S-1-16-{SECURITY_MANDATORY_LOW_RID}", ctypes.byref(sid)
        ):
            _fail("PROCESS_CREDENTIAL_GUARD_SID_FAILED")
        label = TOKEN_MANDATORY_LABEL(
            SID_AND_ATTRIBUTES(sid, SE_GROUP_INTEGRITY)
        )
        sid_length = int(advapi32.GetLengthSid(sid))
        if sid_length <= 0:
            _fail("PROCESS_CREDENTIAL_GUARD_SID_FAILED")
        if not advapi32.SetTokenInformation(
            token,
            TOKEN_INTEGRITY_LEVEL,
            ctypes.byref(label),
            ctypes.sizeof(TOKEN_MANDATORY_LABEL) + sid_length,
        ):
            _fail("PROCESS_CREDENTIAL_GUARD_APPLY_FAILED")
    finally:
        if sid:
            kernel32.LocalFree(sid)
        _close(token.value)


def launch_attested_process(spec: ProcessSpec) -> ProcessResult:
    executable = Path(spec.executable)
    cwd = Path(spec.cwd)
    if not executable.is_absolute() or not cwd.is_absolute():
        raise SecurityBoundaryError("PROCESS_PATH_NOT_ABSOLUTE")
    if verified_sha256(executable) != spec.executable_sha256:
        raise SecurityBoundaryError("PROCESS_IMAGE_MISMATCH")
    if spec.maximum_output_bytes < 1 or spec.timeout_seconds <= 0:
        raise SecurityBoundaryError("PROCESS_LIMIT_INVALID")

    stdout_read, stdout_write = _pipe()
    try:
        stderr_read, stderr_write = _pipe()
    except BaseException:
        _close(stdout_read)
        _close(stdout_write)
        raise
    process = PROCESS_INFORMATION()
    job: int | None = None
    stdout_result: list[bytes] = []
    stderr_result: list[bytes] = []
    try:
        startup = STARTUPINFOW()
        startup.cb = ctypes.sizeof(STARTUPINFOW)
        startup.dwFlags = STARTF_USESTDHANDLES
        startup.hStdInput = None
        startup.hStdOutput = stdout_write
        startup.hStdError = stderr_write
        command = ctypes.create_unicode_buffer(
            subprocess.list2cmdline((str(executable), *spec.arguments))
        )
        environment = _environment_block(dict(spec.environment))
        # Windows loader failures otherwise escape the bounded adapter as a
        # modal GUI dialog.  Children inherit the process error mode at create
        # time, so serialize the short process-creation window and restore the
        # controller's prior mode immediately afterwards.
        with _process_creation_error_mode_lock:
            previous_error_mode = kernel32.SetErrorMode(
                SEM_FAILCRITICALERRORS
                | SEM_NOGPFAULTERRORBOX
                | SEM_NOOPENFILEERRORBOX
            )
            try:
                created = kernel32.CreateProcessW(
                    str(executable),
                    command,
                    None,
                    None,
                    True,
                    CREATE_SUSPENDED | CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW,
                    environment,
                    str(cwd),
                    ctypes.byref(startup),
                    ctypes.byref(process),
                )
            finally:
                kernel32.SetErrorMode(previous_error_mode)
        if not created:
            _fail("PROCESS_CREATE_FAILED")
        _close(stdout_write)
        stdout_write = 0
        _close(stderr_write)
        stderr_write = 0

        image_hash = verified_sha256(_process_image_path(process.hProcess))
        if image_hash != spec.executable_sha256:
            raise SecurityBoundaryError("PROCESS_IMAGE_MISMATCH")

        if spec.credential_write_guard:
            _apply_low_integrity_write_guard(process.hProcess)

        job = int(kernel32.CreateJobObjectW(None, None))
        if not job:
            _fail("PROCESS_JOB_CREATE_FAILED")
        limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION_VALUE()
        limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
            job,
            JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
            ctypes.byref(limits),
            ctypes.sizeof(limits),
        ):
            _fail("PROCESS_JOB_POLICY_FAILED")
        if not kernel32.AssignProcessToJobObject(job, process.hProcess):
            _fail("PROCESS_JOB_ASSIGN_FAILED")

        stdout_thread = threading.Thread(
            target=_reader,
            args=(stdout_read, spec.maximum_output_bytes, stdout_result),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=_reader,
            args=(stderr_read, spec.maximum_output_bytes, stderr_result),
            daemon=True,
        )
        stdout_thread.start()
        stderr_thread.start()
        stdout_read = 0
        stderr_read = 0
        if kernel32.ResumeThread(process.hThread) == 0xFFFFFFFF:
            _fail("PROCESS_RESUME_FAILED")
        wait_ms = min(int(spec.timeout_seconds * 1000), 0xFFFFFFFE)
        wait_status = kernel32.WaitForSingleObject(process.hProcess, wait_ms)
        if wait_status == WAIT_TIMEOUT:
            kernel32.TerminateJobObject(job, 1)
            kernel32.WaitForSingleObject(process.hProcess, INFINITE)
            raise SecurityBoundaryError("PROCESS_TIMEOUT")
        if wait_status != WAIT_OBJECT_0:
            _fail("PROCESS_WAIT_FAILED")
        exit_code = wintypes.DWORD(STILL_ACTIVE)
        if not kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(exit_code)):
            _fail("PROCESS_EXIT_READ_FAILED")
        stdout_thread.join(5)
        stderr_thread.join(5)
        if stdout_thread.is_alive() or stderr_thread.is_alive():
            raise SecurityBoundaryError("PROCESS_OUTPUT_DRAIN_FAILED")
        stdout = stdout_result[0] if stdout_result else b""
        stderr = stderr_result[0] if stderr_result else b""
        if len(stdout) > spec.maximum_output_bytes or len(stderr) > spec.maximum_output_bytes:
            raise SecurityBoundaryError("PROCESS_OUTPUT_LIMIT_EXCEEDED")
        if exit_code.value not in spec.allowed_exit_codes:
            raise SecurityBoundaryError("PROCESS_EXIT_CODE_REJECTED")
        return ProcessResult(
            exit_code=exit_code.value,
            stdout=stdout,
            stderr=stderr,
            image_sha256=image_hash,
            job_object_assigned=True,
        )
    finally:
        # On every exceptional path, closing the configured job terminates the
        # full process tree before process/thread handles are released.
        _close(job)
        _close(process.hThread)
        _close(process.hProcess)
        _close(stdout_read)
        _close(stdout_write)
        _close(stderr_read)
        _close(stderr_write)


def launch_in_job_object(*args: object, **kwargs: object) -> ProcessResult:
    if len(args) == 1 and isinstance(args[0], ProcessSpec) and not kwargs:
        return launch_attested_process(args[0])
    raise SecurityBoundaryError("PROCESS_SPEC_REQUIRED")


__all__ = ["launch_attested_process", "launch_in_job_object", "verified_sha256"]
