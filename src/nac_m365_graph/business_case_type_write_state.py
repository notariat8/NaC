from __future__ import annotations

import ctypes
import os
import re
import sqlite3
import stat
from pathlib import Path
from typing import Any, Mapping

from notary_kg.business_case_type_mutation import canonical_hash

from .business_case_type_write_edge import MutationPersistenceState


_SCHEMA_VERSION = "nac.business-case-type-write-evidence-hook/v0.1"
_APPLICATION_ID = 0x4E414353
_USER_VERSION = 1
_MAX_DATABASE_BYTES = 16 * 1024 * 1024
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_OPERATIONS = frozenset(
    {
        "business_case_type_backfill",
        "case_create",
        "case_status_update",
        "task_create",
        "task_update",
    }
)
_BASE_FIELDS = frozenset(
    {
        "schema_version",
        "mutation_id",
        "execution_key",
        "operation",
        "target_binding_hash",
        "plan_sha256",
        "authorization_run_identity",
        "result_code",
    }
)
_OPTIONAL_BASE_FIELDS = frozenset({"s5_operation_hash"})
_PHASE_FIELDS = {
    "intent": frozenset(
        {
            "intent_generation",
            "expected_intent_generation",
            "prior_authorization_run_identity",
        }
    ),
    "outcome": frozenset({"intent_generation"}),
    "reconciliation": frozenset({"intent_generation"}),
    "readback": frozenset(
        {
            "http_status",
            "intent_generation",
            "close_intent",
            "completion_state",
        }
    ),
}
_OPTIONAL_PHASE_FIELDS = {
    "intent": frozenset(),
    "outcome": frozenset({"http_status"}),
    "reconciliation": frozenset(),
    "readback": frozenset(),
}
_RESULT_CODES = {
    "intent": frozenset({"planned"}),
    "outcome": frozenset(
        {
            "confirmed",
            "create_conflict",
            "deduplicated",
            "failed",
            "precondition_failed",
            "retryable_rejected",
            "write_state_uncertain",
        }
    ),
    "reconciliation": frozenset(
        {
            "create_conflict_evidence_incomplete",
            "create_conflict_readback_uncertain",
            "dedupe_collection_ambiguous",
            "dedupe_evidence_incomplete",
            "dedupe_fresh_readback_uncertain",
            "negative_evidence_incomplete",
            "negative_readback_uncertain",
            "precondition_evidence_incomplete",
            "precondition_readback_uncertain",
            "provider_5xx",
            "readback_evidence_incomplete",
            "readback_not_verified",
            "retryable_response_evidence_incomplete",
            "retryable_response_readback_uncertain",
            "transport_result_unknown",
            "write_completion_uncertain",
        }
    ),
    "readback": frozenset(
        {"not_verified", "verified_applied", "verified_not_applied"}
    ),
}
_EVENT_TABLES = {
    "intent": "intent_events",
    "outcome": "outcome_events",
    "reconciliation": "reconciliation_events",
    "readback": "readback_events",
}
_EVENT_COLUMNS = (
    "schema_version",
    "mutation_id",
    "execution_key",
    "operation",
    "target_binding_hash",
    "plan_sha256",
    "authorization_run_identity",
    "result_code",
    "s5_operation_hash",
    "http_status",
    "intent_generation",
    "expected_intent_generation",
    "prior_authorization_run_identity",
    "close_intent",
    "completion_state",
)
_STATE_COLUMNS = (
    "execution_key",
    "reconciliation_state",
    "intent_state",
    "intent_generation",
    "closed_generation",
    "authorization_run_identity",
    "mutation_id",
    "operation",
    "target_binding_hash",
    "plan_sha256",
    "s5_operation_hash",
)
_NETWORK_FILESYSTEM_MAGICS = frozenset(
    {
        0x0000BD00,  # Lustre
        0x00006969,  # NFS
        0x01021997,  # 9P
        0x01161970,  # GFS2
        0x00C36400,  # Ceph
        0x47504653,  # GPFS
        0x517B,  # SMB
        0x5346414F,  # AFS
        0x564C,  # NCP
        0x65735546,  # FUSE (remote/local cannot be distinguished safely)
        0x73757245,  # Coda
        0x7461636F,  # OCFS2
        0xFF534D42,  # CIFS
    }
)

_STATE_DDL = """
CREATE TABLE mutation_state (
    execution_key TEXT NOT NULL PRIMARY KEY,
    reconciliation_state TEXT NOT NULL
        CHECK (reconciliation_state IN ('clear', 'required')),
    intent_state TEXT NOT NULL
        CHECK (intent_state IN ('open', 'retryable', 'closed')),
    intent_generation INTEGER NOT NULL
        CHECK (intent_generation > 0 AND intent_generation < 9223372036854775807),
    closed_generation INTEGER NOT NULL
        CHECK (closed_generation >= 0 AND closed_generation <= intent_generation),
    authorization_run_identity TEXT NOT NULL
        CHECK (length(authorization_run_identity) = 64),
    mutation_id TEXT NOT NULL CHECK (length(mutation_id) = 64),
    operation TEXT NOT NULL,
    target_binding_hash TEXT NOT NULL CHECK (length(target_binding_hash) = 64),
    plan_sha256 TEXT NOT NULL CHECK (length(plan_sha256) = 64),
    s5_operation_hash TEXT
        CHECK (s5_operation_hash IS NULL OR length(s5_operation_hash) = 64),
    CHECK (
        (intent_state = 'open' AND intent_generation = closed_generation + 1)
        OR
        (
            intent_state IN ('retryable', 'closed')
            AND intent_generation = closed_generation
        )
    ),
    CHECK (reconciliation_state = 'clear' OR intent_state = 'open')
) WITHOUT ROWID
""".strip()


def _event_ddl(table: str) -> str:
    return f"""
CREATE TABLE {table} (
    schema_version TEXT NOT NULL,
    mutation_id TEXT NOT NULL CHECK (length(mutation_id) = 64),
    execution_key TEXT NOT NULL,
    operation TEXT NOT NULL,
    target_binding_hash TEXT NOT NULL CHECK (length(target_binding_hash) = 64),
    plan_sha256 TEXT NOT NULL CHECK (length(plan_sha256) = 64),
    authorization_run_identity TEXT NOT NULL
        CHECK (length(authorization_run_identity) = 64),
    result_code TEXT NOT NULL,
    s5_operation_hash TEXT
        CHECK (s5_operation_hash IS NULL OR length(s5_operation_hash) = 64),
    http_status INTEGER,
    intent_generation INTEGER NOT NULL CHECK (intent_generation > 0),
    expected_intent_generation INTEGER,
    prior_authorization_run_identity TEXT,
    close_intent INTEGER CHECK (close_intent IS NULL OR close_intent IN (0, 1)),
    completion_state TEXT,
    PRIMARY KEY (execution_key, intent_generation),
    FOREIGN KEY (execution_key) REFERENCES mutation_state(execution_key)
) WITHOUT ROWID
""".strip()


_EXPECTED_DDL = {"mutation_state": _STATE_DDL}
_EXPECTED_DDL.update(
    {table: _event_ddl(table) for table in _EVENT_TABLES.values()}
)


class _Unavailable(RuntimeError):
    pass


class SqliteMutationEvidenceHook:
    """Local single-host process-restart state for the S4b evidence port."""

    def __init__(self, database_path: Path) -> None:
        if not isinstance(database_path, Path) or not database_path.is_absolute():
            raise ValueError("database_path must be an absolute pathlib.Path")
        self._database_path = database_path
        try:
            connection = self._connect()
            self._close(connection)
        except Exception:
            return

    def persistence_state(
        self, execution_key: str
    ) -> MutationPersistenceState:
        if not _is_hash(execution_key):
            return _unavailable_state()
        try:
            connection = self._connect()
            try:
                row = connection.execute(
                    """
                    SELECT reconciliation_state, intent_state,
                           intent_generation, closed_generation,
                           authorization_run_identity
                    FROM mutation_state
                    WHERE execution_key = ?
                    """,
                    (execution_key,),
                ).fetchone()
            finally:
                self._close(connection)
        except Exception:
            return _unavailable_state()
        if row is None:
            return MutationPersistenceState("clear", "absent", 0, 0, None)
        if not _valid_state_row(row):
            return _unavailable_state()
        return MutationPersistenceState(
            reconciliation_state=row[0],
            intent_state=row[1],
            intent_generation=row[2],
            closed_generation=row[3],
            authorization_run_identity=row[4],
        )

    def intent(self, evidence: Mapping[str, Any]) -> bool:
        record = _validated_evidence("intent", evidence)
        if record is None:
            return False
        return self._transaction(
            lambda connection: self._intent(connection, record)
        )

    def outcome(self, evidence: Mapping[str, Any]) -> bool:
        record = _validated_evidence("outcome", evidence)
        if record is None:
            return False
        return self._transaction(
            lambda connection: self._event_only(
                connection, "outcome", record, reconciliation_state="clear"
            )
        )

    def readback(self, evidence: Mapping[str, Any]) -> bool:
        record = _validated_evidence("readback", evidence)
        if record is None:
            return False
        return self._transaction(
            lambda connection: self._readback(connection, record)
        )

    def reconciliation_required(self, evidence: Mapping[str, Any]) -> bool:
        record = _validated_evidence("reconciliation", evidence)
        if record is None:
            return False
        return self._transaction(
            lambda connection: self._require_reconciliation(
                connection, record
            )
        )

    def _connect(self) -> sqlite3.Connection:
        self._ensure_storage()
        try:
            connection = sqlite3.connect(
                self._database_path,
                timeout=0.0,
                isolation_level=None,
            )
        except sqlite3.Error as exc:
            raise _Unavailable from exc
        try:
            self._configure(connection)
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("ROLLBACK")
            self._initialize_or_validate_schema(connection)
            self._validate_database_size(connection)
            check = connection.execute("PRAGMA integrity_check(1)").fetchone()
            if check != ("ok",):
                raise _Unavailable
            return connection
        except Exception:
            try:
                connection.close()
            except sqlite3.Error:
                pass
            raise

    def _configure(self, connection: sqlite3.Connection) -> None:
        if hasattr(connection, "setlimit"):
            connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
            connection.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 32)
            connection.setlimit(sqlite3.SQLITE_LIMIT_COMPOUND_SELECT, 1)
            connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1024 * 1024)
            connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 64 * 1024)
        connection.execute("PRAGMA busy_timeout = 0")
        connection.execute("PRAGMA trusted_schema = OFF")
        connection.execute("PRAGMA foreign_keys = ON")
        journal_mode = connection.execute(
            "PRAGMA journal_mode = DELETE"
        ).fetchone()
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA mmap_size = 0")
        if (
            journal_mode != ("delete",)
            or connection.execute("PRAGMA busy_timeout").fetchone() != (0,)
            or connection.execute("PRAGMA trusted_schema").fetchone() != (0,)
            or connection.execute("PRAGMA foreign_keys").fetchone() != (1,)
            or connection.execute("PRAGMA synchronous").fetchone() != (2,)
        ):
            raise _Unavailable
        page_size = connection.execute("PRAGMA page_size").fetchone()
        if (
            page_size is None
            or type(page_size[0]) is not int
            or page_size[0] <= 0
            or page_size[0] > _MAX_DATABASE_BYTES
        ):
            raise _Unavailable
        maximum_pages = _MAX_DATABASE_BYTES // page_size[0]
        configured = connection.execute(
            f"PRAGMA max_page_count = {maximum_pages}"
        ).fetchone()
        if configured is None or configured[0] != maximum_pages:
            raise _Unavailable

    def _initialize_or_validate_schema(
        self, connection: sqlite3.Connection
    ) -> None:
        objects = connection.execute(
            """
            SELECT name, type, sql
            FROM sqlite_schema
            WHERE name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        application_id = connection.execute(
            "PRAGMA application_id"
        ).fetchone()
        user_version = connection.execute("PRAGMA user_version").fetchone()
        if (
            not objects
            and application_id == (0,)
            and user_version == (0,)
        ):
            try:
                connection.execute("BEGIN IMMEDIATE")
                for ddl in _EXPECTED_DDL.values():
                    connection.execute(ddl)
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
            application_id = connection.execute(
                "PRAGMA application_id"
            ).fetchone()
            user_version = connection.execute("PRAGMA user_version").fetchone()
        actual = {
            name: sql
            for name, object_type, sql in objects
            if object_type == "table" and type(sql) is str
        }
        if (
            len(actual) != len(objects)
            or set(actual) != set(_EXPECTED_DDL)
            or application_id != (_APPLICATION_ID,)
            or user_version != (_USER_VERSION,)
        ):
            raise _Unavailable
        for table, expected_sql in _EXPECTED_DDL.items():
            if _normalize_sql(actual[table]) != _normalize_sql(expected_sql):
                raise _Unavailable
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        if foreign_keys:
            raise _Unavailable

    def _validate_database_size(
        self, connection: sqlite3.Connection
    ) -> None:
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
            raise _Unavailable

    def _transaction(self, mutation: Any) -> bool:
        try:
            connection = self._connect()
            accepted = False
            try:
                connection.execute("BEGIN IMMEDIATE")
                self._initialize_or_validate_schema(connection)
                self._validate_database_size(connection)
                accepted = mutation(connection)
                if not accepted:
                    _rollback(connection)
                    return False
                self._validate_database_size(connection)
                connection.execute("COMMIT")
            except Exception:
                _rollback(connection)
                return False
            finally:
                self._close(connection)
            return accepted
        except Exception:
            return False

    def _intent(
        self, connection: sqlite3.Connection, evidence: dict[str, Any]
    ) -> bool:
        key = evidence["execution_key"]
        expected = evidence["expected_intent_generation"]
        generation = evidence["intent_generation"]
        run_identity = evidence["authorization_run_identity"]
        prior_identity = evidence["prior_authorization_run_identity"]
        if generation != expected + 1:
            return False
        row = self._state_row(connection, key)
        bindings = _state_bindings(evidence)
        if row is None:
            if expected != 0 or prior_identity is not None:
                return False
            connection.execute(
                f"""
                INSERT INTO mutation_state ({", ".join(_STATE_COLUMNS)})
                VALUES ({", ".join("?" for _ in _STATE_COLUMNS)})
                """,
                (
                    key,
                    "clear",
                    "open",
                    generation,
                    0,
                    run_identity,
                    *bindings,
                ),
            )
        else:
            if (
                row[1] != "clear"
                or row[2] != "retryable"
                or row[3] != expected
                or row[4] != expected
                or row[5] != prior_identity
                or run_identity == prior_identity
                or not _same_retry_bindings(row, evidence)
            ):
                return False
            cursor = connection.execute(
                """
                UPDATE mutation_state
                SET intent_state = 'open',
                    intent_generation = ?,
                    authorization_run_identity = ?,
                    plan_sha256 = ?,
                    s5_operation_hash = ?
                WHERE execution_key = ?
                  AND reconciliation_state = 'clear'
                  AND intent_state = 'retryable'
                  AND intent_generation = ?
                  AND closed_generation = ?
                  AND authorization_run_identity = ?
                """,
                (
                    generation,
                    run_identity,
                    evidence["plan_sha256"],
                    evidence.get("s5_operation_hash"),
                    key,
                    expected,
                    expected,
                    prior_identity,
                ),
            )
            if cursor.rowcount != 1:
                return False
        return self._insert_event(connection, "intent", evidence)

    def _event_only(
        self,
        connection: sqlite3.Connection,
        phase: str,
        evidence: dict[str, Any],
        *,
        reconciliation_state: str,
    ) -> bool:
        row = self._state_row(connection, evidence["execution_key"])
        if not _matches_open_state(
            row, evidence, reconciliation_state=reconciliation_state
        ):
            return False
        return self._insert_event(connection, phase, evidence)

    def _require_reconciliation(
        self, connection: sqlite3.Connection, evidence: dict[str, Any]
    ) -> bool:
        row = self._state_row(connection, evidence["execution_key"])
        if not _matches_open_state(row, evidence, reconciliation_state="clear"):
            return False
        cursor = connection.execute(
            """
            UPDATE mutation_state
            SET reconciliation_state = 'required'
            WHERE execution_key = ?
              AND reconciliation_state = 'clear'
              AND intent_state = 'open'
              AND intent_generation = ?
              AND authorization_run_identity = ?
            """,
            (
                evidence["execution_key"],
                evidence["intent_generation"],
                evidence["authorization_run_identity"],
            ),
        )
        return cursor.rowcount == 1 and self._insert_event(
            connection, "reconciliation", evidence
        )

    def _readback(
        self, connection: sqlite3.Connection, evidence: dict[str, Any]
    ) -> bool:
        row = self._state_row(connection, evidence["execution_key"])
        close_intent = evidence["close_intent"]
        if close_intent:
            if not _matches_open_state(
                row, evidence, reconciliation_state="clear"
            ):
                return False
            next_state = (
                "retryable"
                if evidence["completion_state"] == "retryable"
                else "closed"
            )
            cursor = connection.execute(
                """
                UPDATE mutation_state
                SET reconciliation_state = 'clear',
                    intent_state = ?,
                    closed_generation = intent_generation
                WHERE execution_key = ?
                  AND reconciliation_state = 'clear'
                  AND intent_state = 'open'
                  AND intent_generation = ?
                  AND authorization_run_identity = ?
                """,
                (
                    next_state,
                    evidence["execution_key"],
                    evidence["intent_generation"],
                    evidence["authorization_run_identity"],
                ),
            )
            if cursor.rowcount != 1:
                return False
        else:
            if (
                evidence["completion_state"] != "terminal"
                or not _matches_open_state(
                    row, evidence, reconciliation_state="required"
                )
            ):
                return False
        return self._insert_event(connection, "readback", evidence)

    def _state_row(
        self, connection: sqlite3.Connection, execution_key: str
    ) -> tuple[Any, ...] | None:
        return connection.execute(
            f"""
            SELECT {", ".join(_STATE_COLUMNS)}
            FROM mutation_state
            WHERE execution_key = ?
            """,
            (execution_key,),
        ).fetchone()

    def _insert_event(
        self,
        connection: sqlite3.Connection,
        phase: str,
        evidence: dict[str, Any],
    ) -> bool:
        table = _EVENT_TABLES[phase]
        values = tuple(
            int(value) if name == "close_intent" and value is not None else value
            for name in _EVENT_COLUMNS
            for value in (evidence.get(name),)
        )
        connection.execute(
            f"""
            INSERT INTO {table} ({", ".join(_EVENT_COLUMNS)})
            VALUES ({", ".join("?" for _ in _EVENT_COLUMNS)})
            """,
            values,
        )
        return True

    def _ensure_storage(self) -> None:
        if os.name != "posix":
            raise _Unavailable
        parent = self._database_path.parent
        created_parent = False
        try:
            parent_stat = parent.lstat()
        except FileNotFoundError:
            try:
                os.mkdir(parent, 0o700)
                created_parent = True
            except FileExistsError:
                pass
            parent_stat = parent.lstat()
        _require_directory(parent_stat)
        if _is_network_filesystem(parent):
            raise _Unavailable
        if created_parent:
            _fsync_directory(parent.parent)
        created_database = False
        try:
            database_stat = self._database_path.lstat()
        except FileNotFoundError:
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            flags |= getattr(os, "O_CLOEXEC", 0)
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                descriptor = os.open(self._database_path, flags, 0o600)
            except FileExistsError:
                database_stat = self._database_path.lstat()
            else:
                try:
                    database_stat = os.fstat(descriptor)
                    _require_database(database_stat)
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
                created_database = True
        _require_database(database_stat)
        if created_database:
            _fsync_directory(parent)
        self._validate_sidecars(allow_journal=True)

    def _validate_sidecars(self, *, allow_journal: bool) -> None:
        for suffix in ("-wal", "-shm"):
            if os.path.lexists(f"{self._database_path}{suffix}"):
                raise _Unavailable
        journal = Path(f"{self._database_path}-journal")
        if os.path.lexists(journal):
            journal_stat = journal.lstat()
            if not allow_journal:
                raise _Unavailable
            _require_database(journal_stat)

    def _close(self, connection: sqlite3.Connection) -> None:
        try:
            connection.close()
        except sqlite3.Error as exc:
            raise _Unavailable from exc
        self._ensure_storage()
        self._validate_sidecars(allow_journal=False)


def _validated_evidence(
    phase: str, evidence: Mapping[str, Any]
) -> dict[str, Any] | None:
    try:
        if not isinstance(evidence, Mapping):
            return None
        record = dict(evidence)
    except Exception:
        return None
    required = _BASE_FIELDS | _PHASE_FIELDS[phase]
    optional = _OPTIONAL_BASE_FIELDS | _OPTIONAL_PHASE_FIELDS[phase]
    if not required <= set(record) <= required | optional:
        return None
    if (
        type(record["schema_version"]) is not str
        or record["schema_version"] != _SCHEMA_VERSION
        or type(record["operation"]) is not str
        or record["operation"] not in _OPERATIONS
        or type(record["result_code"]) is not str
        or record["result_code"] not in _RESULT_CODES[phase]
        or not all(
            _is_hash(record[name])
            for name in (
                "mutation_id",
                "execution_key",
                "target_binding_hash",
                "plan_sha256",
                "authorization_run_identity",
            )
        )
        or record["execution_key"]
        != canonical_hash(
            {
                "target_binding_hash": record["target_binding_hash"],
                "mutation_id": record["mutation_id"],
            }
        )
        or (
            "s5_operation_hash" in record
            and not _is_hash(record["s5_operation_hash"])
        )
        or not _is_generation(record["intent_generation"], minimum=1)
    ):
        return None
    if phase == "intent":
        prior = record["prior_authorization_run_identity"]
        if (
            not _is_generation(
                record["expected_intent_generation"], minimum=0
            )
            or (prior is not None and not _is_hash(prior))
        ):
            return None
    if "http_status" in record and (
        type(record["http_status"]) is not int
        or not 0 <= record["http_status"] <= 599
    ):
        return None
    if phase == "readback" and (
        type(record["close_intent"]) is not bool
        or type(record["completion_state"]) is not str
        or record["completion_state"] not in {"terminal", "retryable"}
        or (
            record["close_intent"]
            and record["result_code"] == "not_verified"
        )
        or (
            record["completion_state"] == "retryable"
            and record["result_code"] != "verified_not_applied"
        )
        or (
            not record["close_intent"]
            and record["completion_state"] != "terminal"
        )
    ):
        return None
    return record


def _matches_open_state(
    row: tuple[Any, ...] | None,
    evidence: Mapping[str, Any],
    *,
    reconciliation_state: str,
) -> bool:
    return bool(
        row is not None
        and row[1] == reconciliation_state
        and row[2] == "open"
        and row[3] == evidence["intent_generation"]
        and row[4] < row[3]
        and row[5] == evidence["authorization_run_identity"]
        and row[6] == evidence["mutation_id"]
        and row[7] == evidence["operation"]
        and row[8] == evidence["target_binding_hash"]
        and row[9] == evidence["plan_sha256"]
        and row[10] == evidence.get("s5_operation_hash")
    )


def _same_retry_bindings(
    row: tuple[Any, ...], evidence: Mapping[str, Any]
) -> bool:
    return bool(
        row[6] == evidence["mutation_id"]
        and row[7] == evidence["operation"]
        and row[8] == evidence["target_binding_hash"]
        and row[10] == evidence.get("s5_operation_hash")
    )


def _state_bindings(evidence: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        evidence["mutation_id"],
        evidence["operation"],
        evidence["target_binding_hash"],
        evidence["plan_sha256"],
        evidence.get("s5_operation_hash"),
    )


def _valid_state_row(row: tuple[Any, ...]) -> bool:
    reconciliation, intent, generation, closed, identity = row
    return bool(
        reconciliation in {"clear", "required"}
        and intent in {"open", "retryable", "closed"}
        and _is_generation(generation, minimum=1)
        and _is_generation(closed, minimum=0)
        and closed <= generation
        and _is_hash(identity)
        and (
            (intent == "open" and generation == closed + 1)
            or (intent in {"retryable", "closed"} and generation == closed)
        )
        and (reconciliation == "clear" or intent == "open")
    )


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _is_generation(value: Any, *, minimum: int) -> bool:
    return type(value) is int and minimum <= value < 2**63 - 1


def _unavailable_state() -> MutationPersistenceState:
    return MutationPersistenceState("unavailable", "unavailable", 0, 0, None)


def _normalize_sql(value: str) -> str:
    return " ".join(value.rstrip(";").split()).lower()


def _rollback(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("ROLLBACK")
    except sqlite3.Error:
        pass


def _require_directory(metadata: os.stat_result) -> None:
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise _Unavailable


def _require_database(metadata: os.stat_result) -> None:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_size > _MAX_DATABASE_BYTES
    ):
        raise _Unavailable


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _is_network_filesystem(path: Path) -> bool:
    if os.uname().sysname != "Linux":
        return True
    filesystem = (ctypes.c_long * 32)()
    libc = ctypes.CDLL(None, use_errno=True)
    statfs = libc.statfs
    statfs.argtypes = (ctypes.c_char_p, ctypes.c_void_p)
    statfs.restype = ctypes.c_int
    encoded_path = os.fsencode(path)
    if statfs(encoded_path, ctypes.byref(filesystem)) != 0:
        raise _Unavailable
    return filesystem[0] & 0xFFFFFFFF in _NETWORK_FILESYSTEM_MAGICS
