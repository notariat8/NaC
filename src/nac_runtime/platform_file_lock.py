from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


def lock_exclusive(descriptor: int, *, nonblocking: bool) -> None:
    if os.name == "nt":
        _lock_windows(descriptor, nonblocking=nonblocking)
        return
    if os.name == "posix":
        import fcntl

        operation = fcntl.LOCK_EX
        if nonblocking:
            operation |= fcntl.LOCK_NB
        fcntl.flock(descriptor, operation)
        return
    raise OSError("PLATFORM_FILE_LOCK_UNAVAILABLE")


def unlock(descriptor: int) -> None:
    if os.name == "nt":
        _unlock_windows(descriptor)
        return
    if os.name == "posix":
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_UN)
        return
    raise OSError("PLATFORM_FILE_LOCK_UNAVAILABLE")


if os.name == "nt":
    import msvcrt

    class _OVERLAPPED(ctypes.Structure):
        _fields_ = (
            ("Internal", ctypes.c_size_t),
            ("InternalHigh", ctypes.c_size_t),
            ("Offset", wintypes.DWORD),
            ("OffsetHigh", wintypes.DWORD),
            ("hEvent", wintypes.HANDLE),
        )

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.LockFileEx.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_OVERLAPPED),
    )
    _kernel32.LockFileEx.restype = wintypes.BOOL
    _kernel32.UnlockFileEx.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.POINTER(_OVERLAPPED),
    )
    _kernel32.UnlockFileEx.restype = wintypes.BOOL


def _lock_windows(descriptor: int, *, nonblocking: bool) -> None:
    handle = msvcrt.get_osfhandle(descriptor)
    flags = 0x00000002 | (0x00000001 if nonblocking else 0)
    overlapped = _OVERLAPPED()
    if not _kernel32.LockFileEx(
        handle,
        flags,
        0,
        0xFFFFFFFF,
        0xFFFFFFFF,
        ctypes.byref(overlapped),
    ):
        error = ctypes.get_last_error()
        if error in {32, 33, 158}:
            raise BlockingIOError(error, "FILE_LOCK_HELD")
        raise OSError(error, "FILE_LOCK_ACQUIRE_FAILED")


def _unlock_windows(descriptor: int) -> None:
    handle = msvcrt.get_osfhandle(descriptor)
    overlapped = _OVERLAPPED()
    if not _kernel32.UnlockFileEx(
        handle,
        0,
        0xFFFFFFFF,
        0xFFFFFFFF,
        ctypes.byref(overlapped),
    ):
        error = ctypes.get_last_error()
        raise OSError(error, "FILE_LOCK_RELEASE_FAILED")


__all__ = ["lock_exclusive", "unlock"]
