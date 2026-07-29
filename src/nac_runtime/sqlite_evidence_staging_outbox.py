from __future__ import annotations

import ctypes
import hashlib
import json
import os
import sqlite3
import stat
from pathlib import Path
from typing import Any, Mapping

from .immutable_evidence import (
    EvidenceRecord,
    ImmutableEvidenceError,
    _EVIDENCE_EVENT_FACTORY_TOKEN,
    _VerifiedEvidenceEvent,
    canonical_json_bytes,
    verify_chain,
)


_APPLICATION_ID = 0x4E414346
_USER_VERSION = 1
_MAX_DATABASE_BYTES = 8 * 1024 * 1024
_LOCAL_FILESYSTEM_MAGICS = frozenset(
    {
        0x01021994,  # tmpfs
        0x58465342,  # XFS
        0x794C7630,  # overlayfs
        0x858458F6,  # ramfs
        0x9123683E,  # Btrfs
        0xEF53,  # ext2/ext3/ext4
    }
)
_DDL = """
CREATE TABLE evidence_staging_outbox (
    correlation_id TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    event_sha256 TEXT NOT NULL UNIQUE CHECK (length(event_sha256) = 64),
    previous_event_sha256 TEXT NOT NULL CHECK (length(previous_event_sha256) = 64),
    event_json BLOB NOT NULL CHECK (length(event_json) BETWEEN 2 AND 1048576),
    PRIMARY KEY (correlation_id, sequence)
) WITHOUT ROWID
""".strip()


class SqliteEvidenceStagingOutbox:
    """Restart-safe local staging only; it cannot acknowledge or close a mutation."""

    def __init__(self, database_path: Path) -> None:
        if not isinstance(database_path, Path) or not database_path.is_absolute():
            raise ValueError("database_path_must_be_absolute")
        self._database_path = database_path
        self._validate_parent()
        self._initialize()

    def append(self, event: Mapping[str, Any]) -> EvidenceRecord:
        if (
            type(event) is not _VerifiedEvidenceEvent
            or event._factory_token is not _EVIDENCE_EVENT_FACTORY_TOKEN
        ):
            raise ImmutableEvidenceError("event must be created by build_event")
        payload = canonical_json_bytes(event)
        if hashlib.sha256(payload).hexdigest() != event._payload_sha256:
            raise ImmutableEvidenceError("event changed after build_event")
        candidate = EvidenceRecord(
            event=json.loads(payload.decode("ascii")),
            event_sha256=hashlib.sha256(payload).hexdigest(),
        )
        correlation_id = candidate.event.get("correlation_id")
        if not isinstance(correlation_id, str):
            raise ImmutableEvidenceError("correlation_id is invalid")

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = self._load_records(connection, correlation_id)
            verify_chain((*existing, candidate))
            connection.execute(
                """
                INSERT INTO evidence_staging_outbox (
                    correlation_id,
                    sequence,
                    event_sha256,
                    previous_event_sha256,
                    event_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    correlation_id,
                    candidate.event["sequence"],
                    candidate.event_sha256,
                    candidate.event["previous_event_sha256"],
                    payload,
                ),
            )
            self._validate_database_size(connection)
            connection.execute("COMMIT")
            return _copy_record(candidate)
        except ImmutableEvidenceError:
            _rollback(connection)
            raise
        except sqlite3.IntegrityError:
            _rollback(connection)
            raise ImmutableEvidenceError("duplicate event is not allowed") from None
        except Exception:
            _rollback(connection)
            raise ImmutableEvidenceError(
                "local evidence staging outbox is unavailable"
            ) from None
        finally:
            _close(connection)

    def records(self, correlation_id: str) -> tuple[EvidenceRecord, ...]:
        if not isinstance(correlation_id, str) or not correlation_id:
            raise ImmutableEvidenceError("correlation_id is invalid")
        connection = self._connect()
        try:
            records = self._load_records(connection, correlation_id)
            return tuple(_copy_record(record) for record in records)
        except ImmutableEvidenceError:
            raise
        except Exception:
            raise ImmutableEvidenceError(
                "local evidence staging outbox is unavailable"
            ) from None
        finally:
            _close(connection)

    def capabilities(self) -> dict[str, bool]:
        return {
            "central_truth": False,
            "promotion": False,
            "central_acknowledgement": False,
            "mutation_completion": False,
            "cleanup": False,
        }

    def _initialize(self) -> None:
        self._ensure_file()
        connection = self._connect(initialize=True)
        _close(connection)

    def _connect(self, *, initialize: bool = False) -> sqlite3.Connection:
        self._validate_file()
        try:
            connection = sqlite3.connect(
                self._database_path,
                timeout=0.0,
                isolation_level=None,
            )
            self._configure(connection)
            self._initialize_or_validate_schema(connection, initialize=initialize)
            self._validate_database_size(connection)
            if connection.execute("PRAGMA integrity_check(1)").fetchone() != ("ok",):
                raise RuntimeError("integrity_check_failed")
            return connection
        except Exception:
            try:
                connection.close()
            except (UnboundLocalError, sqlite3.Error):
                pass
            raise ImmutableEvidenceError(
                "local evidence staging outbox is unavailable"
            ) from None

    def _configure(self, connection: sqlite3.Connection) -> None:
        if hasattr(connection, "setlimit"):
            connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
            connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 16)
            connection.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 1)
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1024 * 1024)
            connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 64 * 1024)
        connection.execute("PRAGMA busy_timeout = 0")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA foreign_keys = ON")
        journal_mode = connection.execute("PRAGMA journal_mode = DELETE").fetchone()
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA mmap_size = 0")
        if journal_mode != ("delete",):
            raise RuntimeError("journal_mode_invalid")
        page_size = connection.execute("PRAGMA page_size").fetchone()
        if page_size is None or type(page_size[0]) is not int or page_size[0] <= 0:
            raise RuntimeError("page_size_invalid")
        max_pages = _MAX_DATABASE_BYTES // page_size[0]
        if connection.execute(f"PRAGMA max_page_count = {max_pages}").fetchone() != (
            max_pages,
        ):
            raise RuntimeError("max_page_count_invalid")

    def _initialize_or_validate_schema(
        self, connection: sqlite3.Connection, *, initialize: bool
    ) -> None:
        objects = connection.execute(
            """
            SELECT name, type, sql
            FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        application_id = connection.execute("PRAGMA application_id").fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()
        if initialize and not objects and application_id == (0,) and user_version == (0,):
            try:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(_DDL)
                connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
                connection.execute(f"PRAGMA user_version = {_USER_VERSION}")
                connection.execute("COMMIT")
            except Exception:
                _rollback(connection)
                raise
            objects = connection.execute(
                """
                SELECT name, type, sql
                FROM sqlite_schema
                WHERE name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
            application_id = connection.execute("PRAGMA application_id").fetchone()
            user_version = connection.execute("PRAGMA user_version").fetchone()
        if (
            objects != [("evidence_staging_outbox", "table", _DDL)]
            or application_id != (_APPLICATION_ID,)
            or user_version != (_USER_VERSION,)
            or connection.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise RuntimeError("schema_invalid")

    def _load_records(
        self, connection: sqlite3.Connection, correlation_id: str
    ) -> tuple[EvidenceRecord, ...]:
        rows = connection.execute(
            """
            SELECT event_json, event_sha256
            FROM evidence_staging_outbox
            WHERE correlation_id = ?
            ORDER BY sequence
            """,
            (correlation_id,),
        ).fetchall()
        records: list[EvidenceRecord] = []
        for payload, event_sha256 in rows:
            if type(payload) is not bytes or type(event_sha256) is not str:
                raise ImmutableEvidenceError("staged evidence record is invalid")
            try:
                event = json.loads(payload.decode("ascii"))
            except Exception:
                raise ImmutableEvidenceError("staged evidence record is invalid") from None
            records.append(EvidenceRecord(event=event, event_sha256=event_sha256))
        result = tuple(records)
        if result:
            verify_chain(result)
        return result

    def _validate_parent(self) -> None:
        parent = self._database_path.parent
        try:
            metadata = parent.lstat()
            local_filesystem = _is_explicitly_local_filesystem(parent)
        except OSError:
            raise ValueError("database_parent_invalid") from None
        if (
            os.name != "posix"
            or not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o700
            or not local_filesystem
        ):
            raise ValueError("database_parent_invalid")

    def _ensure_file(self) -> None:
        if self._database_path.exists() or self._database_path.is_symlink():
            self._validate_file()
            return
        try:
            descriptor = os.open(
                self._database_path,
                os.O_CREAT
                | os.O_EXCL
                | os.O_WRONLY
                | getattr(os, "O_CLOEXEC", 0)
                | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            _fsync_directory(self._database_path.parent)
        except OSError:
            raise ImmutableEvidenceError(
                "local evidence staging outbox is unavailable"
            ) from None

    def _validate_file(self) -> None:
        try:
            metadata = self._database_path.lstat()
        except OSError:
            raise ImmutableEvidenceError(
                "local evidence staging outbox is unavailable"
            ) from None
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ImmutableEvidenceError(
                "local evidence staging outbox is unavailable"
            )

    def _validate_database_size(self, connection: sqlite3.Connection) -> None:
        page_count = connection.execute("PRAGMA page_count").fetchone()
        page_size = connection.execute("PRAGMA page_size").fetchone()
        if (
            page_count is None
            or page_size is None
            or type(page_count[0]) is not int
            or type(page_size[0]) is not int
            or page_count[0] * page_size[0] > _MAX_DATABASE_BYTES
            or self._database_path.stat().st_size > _MAX_DATABASE_BYTES
        ):
            raise RuntimeError("database_size_invalid")


def _copy_record(record: EvidenceRecord) -> EvidenceRecord:
    return EvidenceRecord(
        event=json.loads(canonical_json_bytes(record.event).decode("ascii")),
        event_sha256=record.event_sha256,
    )


def _rollback(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _close(connection: sqlite3.Connection) -> None:
    try:
        connection.close()
    except sqlite3.Error:
        pass


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _is_explicitly_local_filesystem(path: Path) -> bool:
    if (
        os.name != "posix"
        or not hasattr(os, "uname")
        or os.uname().sysname != "Linux"
    ):
        return False
    filesystem = (ctypes.c_long * 32)()
    libc = ctypes.CDLL(None, use_errno=True)
    statfs = libc.statfs
    statfs.argtypes = (ctypes.c_char_p, ctypes.c_void_p)
    statfs.restype = ctypes.c_int
    if statfs(os.fsencode(path), ctypes.byref(filesystem)) != 0:
        raise OSError("statfs_failed")
    return filesystem[0] & 0xFFFFFFFF in _LOCAL_FILESYSTEM_MAGICS
