from __future__ import annotations

import inspect
import sqlite3
import stat
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import nac_m365_graph.business_case_type_write_state as state_module
from nac_m365_graph.business_case_type_write_edge import (
    MutationPersistenceState,
)
from nac_m365_graph.business_case_type_write_state import (
    SqliteMutationEvidenceHook,
)
from notary_kg.business_case_type_mutation import canonical_hash


_HASHES = {
    "mutation_id": "1" * 64,
    "target_binding_hash": "3" * 64,
    "plan_sha256": "4" * 64,
    "authorization_run_identity": "5" * 64,
}
_HASHES["execution_key"] = canonical_hash(
    {
        "target_binding_hash": _HASHES["target_binding_hash"],
        "mutation_id": _HASHES["mutation_id"],
    }
)


def _evidence(**changes):
    value = {
        "schema_version": "nac.business-case-type-write-evidence-hook/v0.1",
        **_HASHES,
        "operation": "case_create",
        "result_code": "planned",
        "intent_generation": 1,
        "expected_intent_generation": 0,
        "prior_authorization_run_identity": None,
    }
    value.update(changes)
    return value


def _phase(evidence, result_code, **changes):
    value = {
        key: evidence[key]
        for key in (
            "schema_version",
            "mutation_id",
            "execution_key",
            "operation",
            "target_binding_hash",
            "plan_sha256",
            "authorization_run_identity",
        )
    }
    value.update(
        result_code=result_code,
        intent_generation=evidence["intent_generation"],
    )
    value.update(changes)
    return value


class SqliteMutationEvidenceHookTests(unittest.TestCase):
    def test_unknown_posix_filesystem_platform_fails_closed(self):
        with mock.patch.object(
            state_module.os,
            "uname",
            return_value=SimpleNamespace(sysname="Darwin"),
        ):
            self.assertTrue(
                state_module._is_network_filesystem(Path("/synthetic"))
            )

    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "state.sqlite3"
        self.hook = SqliteMutationEvidenceHook(self.database_path)

    def test_public_signatures_match_evidence_port(self):
        self.assertEqual(
            str(inspect.signature(SqliteMutationEvidenceHook)),
            "(database_path: 'Path') -> 'None'",
        )
        self.assertEqual(
            tuple(
                str(inspect.signature(getattr(SqliteMutationEvidenceHook, name)))
                for name in (
                    "persistence_state",
                    "intent",
                    "outcome",
                    "readback",
                    "reconciliation_required",
                )
            ),
            (
                "(self, execution_key: 'str') -> 'MutationPersistenceState'",
                "(self, evidence: 'Mapping[str, Any]') -> 'bool'",
                "(self, evidence: 'Mapping[str, Any]') -> 'bool'",
                "(self, evidence: 'Mapping[str, Any]') -> 'bool'",
                "(self, evidence: 'Mapping[str, Any]') -> 'bool'",
            ),
        )

    def test_initializes_restrictive_delete_full_database(self):
        self.assertEqual(
            stat.S_IMODE(self.database_path.parent.stat().st_mode), 0o700
        )
        self.assertEqual(stat.S_IMODE(self.database_path.stat().st_mode), 0o600)
        connection = sqlite3.connect(self.database_path)
        try:
            self.assertEqual(
                connection.execute("PRAGMA journal_mode").fetchone(), ("delete",)
            )
            self.assertEqual(
                connection.execute("PRAGMA synchronous").fetchone(), (2,)
            )
            self.assertLessEqual(self.database_path.stat().st_size, 16 * 1024 * 1024)
        finally:
            connection.close()
        self.assertFalse(Path(f"{self.database_path}-journal").exists())
        self.assertFalse(Path(f"{self.database_path}-wal").exists())
        self.assertFalse(Path(f"{self.database_path}-shm").exists())

    def test_complete_cas_matrix_and_duplicate_phases(self):
        first = _evidence()
        self.assertEqual(
            self.hook.persistence_state(first["execution_key"]),
            MutationPersistenceState("clear", "absent", 0, 0, None),
        )
        self.assertTrue(self.hook.intent(first))
        self.assertFalse(self.hook.intent(first))
        self.assertEqual(
            self.hook.persistence_state(first["execution_key"]),
            MutationPersistenceState("clear", "open", 1, 0, "5" * 64),
        )

        outcome = _phase(first, "confirmed", http_status=201)
        self.assertTrue(self.hook.outcome(outcome))
        self.assertFalse(self.hook.outcome(outcome))
        closing = _phase(
            first,
            "verified_applied",
            http_status=200,
            close_intent=True,
            completion_state="terminal",
        )
        self.assertTrue(self.hook.readback(closing))
        self.assertEqual(
            self.hook.persistence_state(first["execution_key"]),
            MutationPersistenceState("clear", "closed", 1, 1, "5" * 64),
        )
        self.assertFalse(self.hook.outcome(outcome))
        self.assertFalse(self.hook.readback(closing))

    def test_retry_requires_distinct_authorization_and_exact_prior_cas(self):
        first = _evidence()
        self.assertTrue(self.hook.intent(first))
        retryable = _phase(
            first,
            "verified_not_applied",
            http_status=200,
            close_intent=True,
            completion_state="retryable",
        )
        self.assertTrue(self.hook.readback(retryable))
        self.assertFalse(
            self.hook.intent(
                _evidence(
                    intent_generation=2,
                    expected_intent_generation=1,
                    prior_authorization_run_identity="5" * 64,
                )
            )
        )
        second = _evidence(
            plan_sha256="6" * 64,
            authorization_run_identity="7" * 64,
            intent_generation=2,
            expected_intent_generation=1,
            prior_authorization_run_identity="5" * 64,
        )
        self.assertTrue(self.hook.intent(second))
        self.assertEqual(
            self.hook.persistence_state(second["execution_key"]),
            MutationPersistenceState("clear", "open", 2, 1, "7" * 64),
        )

    def test_required_open_accepts_only_non_closing_readback(self):
        intent = _evidence()
        self.assertTrue(self.hook.intent(intent))
        required = _phase(intent, "write_completion_uncertain")
        self.assertTrue(self.hook.reconciliation_required(required))
        closing = _phase(
            intent,
            "verified_applied",
            http_status=200,
            close_intent=True,
            completion_state="terminal",
        )
        self.assertFalse(self.hook.readback(closing))
        non_closing = dict(closing, close_intent=False, result_code="not_verified")
        self.assertTrue(self.hook.readback(non_closing))
        self.assertFalse(self.hook.readback(non_closing))
        self.assertEqual(
            self.hook.persistence_state(intent["execution_key"]),
            MutationPersistenceState("required", "open", 1, 0, "5" * 64),
        )

    def test_readback_closure_requires_verified_result(self):
        intent = _evidence()
        self.assertTrue(self.hook.intent(intent))
        self.assertFalse(
            self.hook.readback(
                _phase(
                    intent,
                    "not_verified",
                    http_status=0,
                    close_intent=True,
                    completion_state="terminal",
                )
            )
        )
        self.assertEqual(
            self.hook.persistence_state(intent["execution_key"]).intent_state,
            "open",
        )

    def test_execution_key_must_bind_target_and_mutation_hashes(self):
        self.assertFalse(self.hook.intent(_evidence(execution_key="2" * 64)))

    def test_busy_corrupt_oversize_permissions_and_symlinks_fail_closed(self):
        intent = _evidence()
        lock = sqlite3.connect(self.database_path, timeout=0, isolation_level=None)
        lock.execute("BEGIN EXCLUSIVE")
        try:
            self.assertFalse(self.hook.intent(intent))
            self.assertEqual(
                self.hook.persistence_state(intent["execution_key"]).intent_state,
                "unavailable",
            )
        finally:
            lock.execute("ROLLBACK")
            lock.close()
        self.assertEqual(
            self.hook.persistence_state(intent["execution_key"]).intent_state,
            "absent",
        )

        cases = ("corrupt", "oversize", "mode", "symlink")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "state.sqlite3"
                if case == "corrupt":
                    path.write_bytes(b"not sqlite")
                    path.chmod(0o600)
                elif case == "oversize":
                    with path.open("wb") as stream:
                        stream.truncate(16 * 1024 * 1024 + 1)
                    path.chmod(0o600)
                elif case == "mode":
                    path.touch(mode=0o600)
                    path.chmod(0o644)
                else:
                    target = Path(directory) / "target"
                    target.touch(mode=0o600)
                    path.symlink_to(target)
                candidate = SqliteMutationEvidenceHook(path)
                self.assertEqual(
                    candidate.persistence_state("2" * 64).intent_state,
                    "unavailable",
                )
                self.assertFalse(candidate.intent(intent))

    def test_evidence_is_recursively_allowlisted_and_contains_no_raw_data(self):
        forbidden = {
            "request_body": {"fields": {"Mandant": "secret-value"}},
            "site_id": "site-raw",
            "headers": {"Authorization": "Bearer token-raw"},
            "url": "https://graph.microsoft.com/raw",
        }
        for name, value in forbidden.items():
            with self.subTest(name=name):
                self.assertFalse(self.hook.intent(_evidence(**{name: value})))
        content = self.database_path.read_bytes()
        for raw_value in (
            b"secret-value",
            b"site-raw",
            b"Bearer token-raw",
            b"https://graph.microsoft.com/raw",
        ):
            self.assertNotIn(raw_value, content)

    def test_two_connections_allow_only_one_first_intent(self):
        other = SqliteMutationEvidenceHook(self.database_path)
        intent = _evidence()
        self.assertTrue(self.hook.intent(intent))
        self.assertFalse(other.intent(intent))
        self.assertEqual(
            other.persistence_state(intent["execution_key"]),
            MutationPersistenceState("clear", "open", 1, 0, "5" * 64),
        )


if __name__ == "__main__":
    unittest.main()
