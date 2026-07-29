from __future__ import annotations

import os
import sqlite3
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_runtime.immutable_evidence import (  # noqa: E402
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    ZERO_HASH,
    EvidenceRecord,
    ImmutableEvidenceError,
    actor_ref,
    build_event,
    correlation_ref,
    typed_identifier_registry,
    verify_chain,
)
from nac_runtime.sqlite_evidence_staging_outbox import (  # noqa: E402
    SqliteEvidenceStagingOutbox,
)


TENANT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_OBJECT_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_OBJECT_ID = "55555555-5555-4555-8555-555555555555"
ACTOR_KEY = b"actor-key-for-immutable-evidence"
PRINCIPAL_KEY = b"stable-principal-binding-key-0001"
CORRELATION_ID = correlation_ref(
    tenant_id=TENANT_ID,
    source_object_id=SOURCE_OBJECT_ID,
    key_version=3,
    key=ACTOR_KEY,
)
ACTOR_REF = actor_ref(
    tenant_id=TENANT_ID,
    actor_object_id=ACTOR_OBJECT_ID,
    key_version=3,
    key=ACTOR_KEY,
    principal_key=PRINCIPAL_KEY,
)
CATALOG_VERSION = next(iter(REGISTERED_CATALOG_VERSIONS))
IDENTIFIER_REGISTRY = typed_identifier_registry(
    business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
    catalog_versions=REGISTERED_CATALOG_VERSIONS,
)


def _event(
    phase: str,
    *,
    sequence: int,
    previous_event_sha256: str,
    **overrides: Any,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "correlation_id": CORRELATION_ID,
        "phase": phase,
        "sequence": sequence,
        "previous_event_sha256": previous_event_sha256,
        "actor_ref_value": ACTOR_REF,
        "tool_id": "tool-nac-cli",
        "role_id": "role-migration-operator",
        "action": "schema_apply",
        "business_case_type_id": "immobilienkaufvertrag",
        "catalog_version": CATALOG_VERSION,
        "identifier_registry": IDENTIFIER_REGISTRY,
        "manifest_sha256": "a" * 64,
        "etag_hmac_key": ACTOR_KEY,
        "etag_hmac_key_version": 1,
        "occurred_at": "2026-07-29T12:00:00Z",
    }
    if phase in {"outcome", "readback"}:
        values["result_code"] = "confirmed"
        values["etags"] = {"matter": "synthetic-state-etag"}
    values.update(overrides)
    return build_event(**values)


def _append(
    outbox: SqliteEvidenceStagingOutbox,
    phase: str,
    **overrides: Any,
) -> EvidenceRecord:
    records = outbox.records(CORRELATION_ID)
    return outbox.append(
        _event(
            phase,
            sequence=len(records) + 1,
            previous_event_sha256=(
                records[-1].event_sha256 if records else ZERO_HASH
            ),
            **overrides,
        )
    )


class SqliteEvidenceStagingOutboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name).resolve()
        self.database_path = self.directory / "evidence-staging.sqlite3"
        self.outbox = SqliteEvidenceStagingOutbox(self.database_path)

    def test_records_survive_restarts_and_preserve_sequence_and_hash_chain(
        self,
    ) -> None:
        intent = _append(self.outbox, "intent")

        restarted = SqliteEvidenceStagingOutbox(self.database_path)
        outcome = _append(restarted, "outcome")

        restarted_again = SqliteEvidenceStagingOutbox(self.database_path)
        readback = _append(restarted_again, "readback")
        records = restarted_again.records(CORRELATION_ID)
        status = verify_chain(records)

        self.assertEqual([record.event["sequence"] for record in records], [1, 2, 3])
        self.assertEqual(
            [record.event["phase"] for record in records],
            ["intent", "outcome", "readback"],
        )
        self.assertEqual(outcome.event["previous_event_sha256"], intent.event_sha256)
        self.assertEqual(
            readback.event["previous_event_sha256"], outcome.event_sha256
        )
        self.assertEqual(status["head_sha256"], readback.event_sha256)
        self.assertTrue(status["complete"])

    def test_returned_records_are_copies_not_mutable_database_state(self) -> None:
        appended = _append(self.outbox, "intent")
        appended.event["tool_id"] = "mutated-return-value"
        first_read = self.outbox.records(CORRELATION_ID)
        first_read[0].event["tool_id"] = "mutated-read-value"

        restarted = SqliteEvidenceStagingOutbox(self.database_path)
        persisted = restarted.records(CORRELATION_ID)

        self.assertEqual(persisted[0].event["tool_id"], "tool-nac-cli")

    def test_sequence_and_previous_hash_drift_are_rejected_atomically(
        self,
    ) -> None:
        intent = _append(self.outbox, "intent")
        invalid_events = (
            _event(
                "outcome",
                sequence=3,
                previous_event_sha256=intent.event_sha256,
            ),
            _event(
                "outcome",
                sequence=2,
                previous_event_sha256="f" * 64,
            ),
        )

        for event in invalid_events:
            with self.subTest(
                sequence=event["sequence"],
                previous=event["previous_event_sha256"],
            ):
                with self.assertRaises(ImmutableEvidenceError):
                    self.outbox.append(event)
                self.assertEqual(
                    len(self.outbox.records(CORRELATION_ID)),
                    1,
                )

        restarted = SqliteEvidenceStagingOutbox(self.database_path)
        self.assertEqual(restarted.records(CORRELATION_ID), (intent,))

    def test_invalid_phase_transition_is_rejected_without_partial_insert(
        self,
    ) -> None:
        intent = _append(self.outbox, "intent")
        readback_without_outcome = _event(
            "readback",
            sequence=2,
            previous_event_sha256=intent.event_sha256,
        )

        with self.assertRaises(ImmutableEvidenceError):
            self.outbox.append(readback_without_outcome)

        self.assertEqual(self.outbox.records(CORRELATION_ID), (intent,))

    def test_duplicate_event_is_rejected_and_original_survives_restart(
        self,
    ) -> None:
        event = _event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
        )
        original = self.outbox.append(event)

        with self.assertRaises(ImmutableEvidenceError):
            self.outbox.append(event)

        restarted = SqliteEvidenceStagingOutbox(self.database_path)
        self.assertEqual(restarted.records(CORRELATION_ID), (original,))

    def test_event_mutated_after_build_is_rejected_before_database_write(
        self,
    ) -> None:
        event = _event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
        )
        event["tool_id"] = "tampered-after-build"

        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            r"^event changed after build_event$",
        ):
            self.outbox.append(event)

        self.assertEqual(self.outbox.records(CORRELATION_ID), ())

    def test_persisted_payload_tamper_is_detected_on_read_and_after_restart(
        self,
    ) -> None:
        _append(self.outbox, "intent")
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                UPDATE evidence_staging_outbox
                SET event_json = ?
                WHERE correlation_id = ? AND sequence = 1
                """,
                (b"{}", CORRELATION_ID),
            )

        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            r"^event hash is invalid$",
        ):
            self.outbox.records(CORRELATION_ID)
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            r"^event hash is invalid$",
        ):
            SqliteEvidenceStagingOutbox(self.database_path)

    def test_persisted_routing_column_tamper_is_detected_globally(
        self,
    ) -> None:
        record = _append(self.outbox, "intent")
        mutations = (
            ("correlation_id", "tampered-correlation", CORRELATION_ID),
            ("sequence", 7, 1),
            ("previous_event_sha256", "f" * 64, ZERO_HASH),
        )
        for column, tampered, original in mutations:
            with self.subTest(column=column):
                with sqlite3.connect(self.database_path) as connection:
                    connection.execute(
                        f"UPDATE evidence_staging_outbox SET {column} = ?",
                        (tampered,),
                    )
                for correlation_id in (CORRELATION_ID, "tampered-correlation"):
                    with self.assertRaisesRegex(
                        ImmutableEvidenceError,
                        r"^staged evidence routing is invalid$",
                    ):
                        self.outbox.records(correlation_id)
                with self.assertRaisesRegex(
                    ImmutableEvidenceError,
                    r"^staged evidence routing is invalid$",
                ):
                    SqliteEvidenceStagingOutbox(self.database_path)
                with sqlite3.connect(self.database_path) as connection:
                    connection.execute(
                        f"UPDATE evidence_staging_outbox SET {column} = ?",
                        (original,),
                    )
                self.assertEqual(
                    self.outbox.records(CORRELATION_ID),
                    (record,),
                )

    def test_database_schema_failure_is_stable_and_does_not_leak_path(
        self,
    ) -> None:
        sensitive_path = str(self.database_path)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute("DROP TABLE evidence_staging_outbox")

        with self.assertRaises(ImmutableEvidenceError) as captured:
            self.outbox.records(CORRELATION_ID)

        self.assertEqual(
            str(captured.exception),
            "local evidence staging outbox is unavailable",
        )
        self.assertNotIn(sensitive_path, str(captured.exception))

    def test_database_file_is_created_owner_only(self) -> None:
        metadata = self.database_path.stat()

        self.assertTrue(stat.S_ISREG(metadata.st_mode))
        self.assertEqual(stat.S_IMODE(metadata.st_mode), 0o600)
        self.assertEqual(metadata.st_uid, os.getuid())

    def test_database_with_non_exact_permissions_is_rejected(
        self,
    ) -> None:
        for mode in (0o640, 0o700, 0o400):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.database_path, mode)
                with self.assertRaisesRegex(
                    ImmutableEvidenceError,
                    r"^local evidence staging outbox is unavailable$",
                ):
                    self.outbox.records(CORRELATION_ID)
                os.chmod(self.database_path, 0o600)
        self.addCleanup(os.chmod, self.database_path, 0o600)

    def test_symlink_database_is_rejected(self) -> None:
        symlink_path = self.directory / "symlink.sqlite3"
        symlink_path.symlink_to(self.database_path)

        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            r"^local evidence staging outbox is unavailable$",
        ):
            SqliteEvidenceStagingOutbox(symlink_path)

    def test_group_writable_parent_directory_is_rejected(self) -> None:
        insecure_parent = self.directory / "insecure"
        insecure_parent.mkdir(mode=0o700)
        insecure_database = insecure_parent / "staging.sqlite3"
        os.chmod(insecure_parent, 0o770)
        self.addCleanup(os.chmod, insecure_parent, 0o700)

        with self.assertRaisesRegex(
            ValueError,
            r"^database_parent_invalid$",
        ):
            SqliteEvidenceStagingOutbox(insecure_database)

    def test_parent_directory_requires_exact_owner_only_mode(self) -> None:
        insecure_parent = self.directory / "readable-by-group"
        insecure_parent.mkdir(mode=0o700)
        insecure_database = insecure_parent / "staging.sqlite3"
        os.chmod(insecure_parent, 0o750)
        self.addCleanup(os.chmod, insecure_parent, 0o700)

        with self.assertRaisesRegex(ValueError, r"^database_parent_invalid$"):
            SqliteEvidenceStagingOutbox(insecure_database)

    def test_capabilities_and_public_api_cannot_complete_promote_or_cleanup(
        self,
    ) -> None:
        self.assertEqual(
            self.outbox.capabilities(),
            {
                "central_truth": False,
                "promotion": False,
                "central_acknowledgement": False,
                "mutation_completion": False,
                "cleanup": False,
            },
        )
        public_methods = {
            name
            for name in dir(SqliteEvidenceStagingOutbox)
            if not name.startswith("_")
            and callable(getattr(SqliteEvidenceStagingOutbox, name))
        }
        self.assertEqual(public_methods, {"append", "capabilities", "records"})
        self.assertTrue(
            {
                "complete",
                "acknowledge",
                "promote",
                "cleanup",
                "delete",
                "truncate",
            }.isdisjoint(public_methods)
        )


if __name__ == "__main__":
    unittest.main()
