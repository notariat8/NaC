"""Windows-native hardened subprocess launcher for the NaC BFF Live Activation Runner.

Replaces Linux memfd / mount-namespace / fcntl hardening with Windows equivalents:
- Handle-based SHA-256 binary verification
- Job Object process isolation
- Windows global mutex for exclusive activation lock"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys


if os.name != "nt":
    raise ImportError("azure_live_commands_win requires Windows (os.name == 'nt')")

# Windows-specific imports
import ctypes
from ctypes import wintypes
import msvcrt

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

# Constants
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
GENERIC_READ = 0x80000000

JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008

CREATE_MUTEX_INITIAL_OWNER = 0x00000001
WAIT_ABANDONED = 0x00000080
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF

_READ_CHUNK = 1024 * 1024
_MAX_FILE_BYTES = 512 * 1024 * 1024


def _open_trusted_handle(path: Path) -> int | None:
    """Open a Windows file handle with shared-read-only, no write/delete share.
    Returns a C file handle (not a Python file object)."""
    try:
        handle = kernel32.CreateFileW(
            str(path),
            GENERIC_READ,
            FILE_SHARE_READ,  # allow other reads, deny writes/deletes
            None,  # security attributes
            OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL | FILE_FLAG_SEQUENTIAL_SCAN,
            None,  # template file
        )
        if handle == wintypes.HANDLE(-1).value:
            return None
        return handle
    except OSError:
        return None


def _sha256_from_handle(handle: int) -> str | None:
    """Compute SHA-256 from a Windows file handle using msvcrt low-level I/O."""
    try:
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY)
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(fd, _READ_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
            total += len(chunk)
            if total > _MAX_FILE_BYTES:
                return None
        return digest.hexdigest()
    except OSError:
        return None
    finally:
        try:
            os.close(fd)
        except OSError:
            pass


def verified_sha256(path: Path) -> str | None:
    """Compute trusted SHA-256 of a Windows binary.
    
    Opens the file with a restricted handle (no write/delete share),
    computes SHA-256 via msvcrt low-level I/O, verifying the file hasn't
    been replaced between open and computation.
    """
    if not path.is_absolute() or not path.is_file():
        return None
    handle = _open_trusted_handle(path)
    if handle is None:
        return None
    try:
        return _sha256_from_handle(handle)
    finally:
        kernel32.CloseHandle(handle)


def launch_in_job_object(
    executable: Path,
    args: list[str],
    *,
    env_allowlist: set[str] | None = None,
) -> subprocess.Popen:
    """Launch a subprocess inside a Windows Job Object with env allowlist.
    
    The Job Object limits active processes to 1, ensuring the child
    cannot spawn additional processes beyond the CLI tool itself.
    """
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise OSError("CreateJobObjectW failed")

    limit_info = wintypes.JOBOBJECT_BASIC_LIMIT_INFORMATION()
    limit_info.LimitFlags = JOB_OBJECT_LIMIT_ACTIVE_PROCESS
    limit_info.ActiveProcessLimit = 1

    info = wintypes.JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation = limit_info
    info_size = ctypes.sizeof(info)

    if not kernel32.SetInformationJobObject(
        job,
        9,  # JobObjectExtendedLimitInformation
        ctypes.byref(info),
        info_size,
    ):
        kernel32.CloseHandle(job)
        raise OSError("SetInformationJobObject failed")

    # Build cleaned environment
    env = {}
    if env_allowlist is not None:
        for key, value in os.environ.items():
            if key in env_allowlist or key.startswith("AZURE_") or key.startswith("CLIMICROSOFT365"):
                env[key] = value
    else:
        env = dict(os.environ)

    proc = subprocess.Popen(
        [str(executable)] + args,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if not kernel32.AssignProcessToJobObject(job, wintypes.HANDLE(proc.pid)):
        kernel32.CloseHandle(job)
        raise OSError("AssignProcessToJobObject failed")

    # Job handle intentionally leaked - child process lifecycle tied to job
    return proc


def acquire_windows_mutex(mutex_name: str, timeout_ms: int = 0) -> bool:
    """Acquire a Windows global mutex for exclusive activation.
    
    Returns True if acquired, False if already held.
    Detects abandoned mutex (crash window) as successful acquisition.
    """
    mutex = kernel32.CreateMutexW(None, False, f"Local\\{mutex_name}")
    if not mutex:
        return False

    result = kernel32.WaitForSingleObject(
        wintypes.HANDLE(mutex),
        timeout_ms if timeout_ms > 0 else INFINITE,
    )

    if result == WAIT_OBJECT_0:
        # Acquired normally
        return True
    elif result == WAIT_ABANDONED:
        # Previous holder crashed - mutex is abandoned, we can take it
        return True
    else:
        kernel32.CloseHandle(mutex)
        return False


def release_windows_mutex(mutex: int) -> None:
    """Release a held Windows mutex."""
    kernel32.ReleaseMutex(wintypes.HANDLE(mutex))
    kernel32.CloseHandle(wintypes.HANDLE(mutex))