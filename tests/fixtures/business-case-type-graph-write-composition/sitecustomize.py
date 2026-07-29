from __future__ import annotations

import os
import sys
from pathlib import Path


DATABASE_PATH = Path(os.environ["S4C_DATABASE_PATH"]).resolve()
REPOSITORY_ROOT = Path(os.environ["S4C_REPOSITORY_ROOT"]).resolve()
SOURCE_ROOT = REPOSITORY_ROOT / "src"
PYTHON_ROOT = Path(sys.base_prefix).resolve()
GUARD_PATH = Path(__file__).resolve()
ALLOWED_DATABASE_PATHS = {
    DATABASE_PATH,
    Path(f"{DATABASE_PATH}-journal"),
    Path(f"{DATABASE_PATH}-shm"),
    Path(f"{DATABASE_PATH}-wal"),
}
ALLOWED_DIRECTORY_PATHS = {
    DATABASE_PATH.parent,
    DATABASE_PATH.parent.parent,
}
ALLOWED_IMPORT_SUFFIXES = {".py", ".pyc", ".so"}


class _ForbiddenEnvironment(dict):
    def _blocked(self, *_args, **_kwargs):
        _deny("environment_access_blocked")

    __contains__ = _blocked
    __delitem__ = _blocked
    __eq__ = _blocked
    __format__ = _blocked
    __getitem__ = _blocked
    __iter__ = _blocked
    __len__ = _blocked
    __ne__ = _blocked
    __or__ = _blocked
    __reduce__ = _blocked
    __reduce_ex__ = _blocked
    __repr__ = _blocked
    __reversed__ = _blocked
    __ror__ = _blocked
    __setitem__ = _blocked
    __sizeof__ = _blocked
    __str__ = _blocked
    __ior__ = _blocked
    clear = _blocked
    copy = _blocked
    get = _blocked
    items = _blocked
    keys = _blocked
    pop = _blocked
    popitem = _blocked
    setdefault = _blocked
    update = _blocked
    values = _blocked


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _deny(reason: str) -> None:
    os.write(2, f"S4C_AUDIT_BLOCKED:{reason}\n".encode("utf-8"))
    raise RuntimeError(reason)


def _audit(event: str, args: tuple[object, ...]) -> None:
    if event.startswith("socket."):
        _deny("network_or_dns_access_blocked")
    if event == "sqlite3.connect":
        candidate = Path(os.fspath(args[0])).resolve()
        if candidate != DATABASE_PATH:
            _deny(f"foreign_sqlite_access_blocked:{candidate}")
        return
    if event != "open" or not args or isinstance(args[0], int):
        return
    candidate = Path(os.fspath(args[0])).resolve()
    if candidate in ALLOWED_DATABASE_PATHS:
        return
    flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
    if (
        candidate in ALLOWED_DIRECTORY_PATHS
        and flags & getattr(os, "O_DIRECTORY", 0)
    ):
        return
    if (
        candidate == GUARD_PATH
        or (
            candidate.suffix in ALLOWED_IMPORT_SUFFIXES
            and (
                _inside(candidate, SOURCE_ROOT)
                or _inside(candidate, PYTHON_ROOT)
            )
        )
    ):
        return
    _deny(f"external_file_access_blocked:{candidate}")


sys.addaudithook(_audit)
os.environ = _ForbiddenEnvironment()
os.environb = _ForbiddenEnvironment()
