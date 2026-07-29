from __future__ import annotations

import subprocess
import sys
import textwrap
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_write_edge import (
    MutationPersistenceState,
)
from nac_m365_graph.business_case_type_write_state import (
    SqliteMutationEvidenceHook,
)

try:
    from tests.test_business_case_type_graph_write_state_store import _evidence, _phase
except ImportError:
    from test_business_case_type_graph_write_state_store import _evidence, _phase


class SqliteMutationEvidenceCrashRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.database_path = Path(self.temporary_directory.name) / "state.sqlite3"

    def _restart(self):
        return SqliteMutationEvidenceHook(self.database_path)

    def test_intent_before_transport_blocks_replay_after_restart(self):
        hook = self._restart()
        intent = _evidence()
        self.assertTrue(hook.intent(intent))
        restarted = self._restart()
        self.assertEqual(
            restarted.persistence_state(intent["execution_key"]),
            MutationPersistenceState("clear", "open", 1, 0, "5" * 64),
        )
        self.assertFalse(restarted.intent(intent))

    def test_transport_before_outcome_remains_open_after_restart(self):
        hook = self._restart()
        intent = _evidence()
        self.assertTrue(hook.intent(intent))
        restarted = self._restart()
        self.assertFalse(
            restarted.reconciliation_required(
                _phase(intent, "transport_result_unknown", intent_generation=2)
            )
        )
        self.assertTrue(
            restarted.reconciliation_required(
                _phase(intent, "transport_result_unknown")
            )
        )
        self.assertEqual(
            self._restart().persistence_state(intent["execution_key"]),
            MutationPersistenceState("required", "open", 1, 0, "5" * 64),
        )

    def test_outcome_before_readback_remains_open_after_restart(self):
        hook = self._restart()
        intent = _evidence()
        self.assertTrue(hook.intent(intent))
        self.assertTrue(hook.outcome(_phase(intent, "confirmed", http_status=201)))
        restarted = self._restart()
        self.assertEqual(
            restarted.persistence_state(intent["execution_key"]).intent_state,
            "open",
        )
        self.assertFalse(restarted.intent(intent))

    def test_closure_before_acknowledgement_stays_terminal(self):
        hook = self._restart()
        intent = _evidence()
        self.assertTrue(hook.intent(intent))
        self.assertTrue(hook.outcome(_phase(intent, "confirmed", http_status=201)))
        closing = _phase(
            intent,
            "verified_applied",
            http_status=200,
            close_intent=True,
            completion_state="terminal",
        )
        self.assertTrue(hook.readback(closing))
        restarted = self._restart()
        self.assertEqual(
            restarted.persistence_state(intent["execution_key"]),
            MutationPersistenceState("clear", "closed", 1, 1, "5" * 64),
        )
        self.assertFalse(restarted.readback(closing))
        self.assertFalse(restarted.intent(intent))

    def test_process_kill_mid_transaction_rolls_back_partial_state(self):
        hook = self._restart()
        intent = _evidence()
        self.assertTrue(hook.intent(intent))
        script = textwrap.dedent(
            """
            import os
            import signal
            import sqlite3
            import sys

            connection = sqlite3.connect(sys.argv[1], isolation_level=None)
            connection.execute("PRAGMA journal_mode = DELETE")
            connection.execute("PRAGMA synchronous = FULL")
            connection.execute("PRAGMA cache_size = 1")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE mutation_state "
                "SET reconciliation_state = 'required'"
            )
            connection.execute("CREATE TABLE crash_fill (payload BLOB)")
            for _ in range(256):
                connection.execute(
                    "INSERT INTO crash_fill VALUES (randomblob(4096))"
                )
            os.kill(os.getpid(), signal.SIGKILL)
            """
        )

        crashed = subprocess.run(
            [sys.executable, "-c", script, str(self.database_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertLess(crashed.returncode, 0)
        restarted = self._restart()
        self.assertEqual(
            restarted.persistence_state(intent["execution_key"]),
            MutationPersistenceState("clear", "open", 1, 0, "5" * 64),
        )
        self.assertFalse(Path(f"{self.database_path}-journal").exists())

    def test_corrupt_restart_is_unavailable_and_never_recreated(self):
        self.database_path.write_bytes(b"\x00torn-state")
        self.database_path.chmod(0o600)
        restarted = self._restart()
        self.assertEqual(
            restarted.persistence_state("2" * 64),
            MutationPersistenceState("unavailable", "unavailable", 0, 0, None),
        )
        self.assertFalse(restarted.intent(_evidence()))
        self.assertEqual(self.database_path.read_bytes(), b"\x00torn-state")


if __name__ == "__main__":
    unittest.main()
