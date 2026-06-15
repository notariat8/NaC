from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli.cli import main  # noqa: E402


def run_cli(*argv: str) -> tuple[int, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            rc = main(["--repo-root", str(REPO_ROOT), *argv])
        except SystemExit as exc:
            rc = int(exc.code or 0)
    return rc, stdout.getvalue() + stderr.getvalue()


class CodexTimeLedgerCliTests(unittest.TestCase):
    def test_time_ledger_add_writes_jsonl_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "codex-time-ledger.jsonl"

            rc, output = run_cli(
                "time-ledger",
                "add",
                "--log",
                str(log_path),
                "--session-id",
                "2026-06-15-nac",
                "--task",
                "NaC observability",
                "--phase",
                "unit-tests",
                "--category",
                "local_cpu",
                "--started-at",
                "2026-06-15T10:00:00Z",
                "--ended-at",
                "2026-06-15T10:00:05Z",
                "--command",
                "python -m unittest tests/test_codex_time_ledger.py",
                "--notes",
                "synthetic command timing",
                "--format",
                "json",
            )

            self.assertEqual(rc, 0, output)
            payload = json.loads(output)
            self.assertEqual(payload["schema_version"], "nac.codex-time-ledger/v0.1")
            self.assertEqual(payload["duration_ms"], 5000)
            self.assertEqual(payload["category"], "local_cpu")
            self.assertTrue(log_path.exists())

            lines = log_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            entry = json.loads(lines[0])
            self.assertEqual(entry["session_id"], "2026-06-15-nac")
            self.assertEqual(entry["phase"], "unit-tests")
            self.assertEqual(entry["command"], "python -m unittest tests/test_codex_time_ledger.py")

    def test_time_ledger_summary_groups_duration_by_category_and_phase(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "codex-time-ledger.jsonl"
            entries = [
                {
                    "schema_version": "nac.codex-time-ledger/v0.1",
                    "session_id": "2026-06-15-nac",
                    "task": "NaC observability",
                    "phase": "context-read",
                    "category": "local_io",
                    "actor": "codex",
                    "started_at": "2026-06-15T10:00:00Z",
                    "ended_at": "2026-06-15T10:00:03Z",
                    "duration_ms": 3000,
                    "outcome": "completed",
                },
                {
                    "schema_version": "nac.codex-time-ledger/v0.1",
                    "session_id": "2026-06-15-nac",
                    "task": "NaC observability",
                    "phase": "tests",
                    "category": "local_cpu",
                    "actor": "codex",
                    "started_at": "2026-06-15T10:00:03Z",
                    "ended_at": "2026-06-15T10:00:08Z",
                    "duration_ms": 5000,
                    "outcome": "completed",
                },
                {
                    "schema_version": "nac.codex-time-ledger/v0.1",
                    "session_id": "2026-06-15-nac",
                    "task": "NaC observability",
                    "phase": "approval",
                    "category": "approval_wait",
                    "actor": "user",
                    "started_at": "2026-06-15T10:00:08Z",
                    "ended_at": "2026-06-15T10:00:10Z",
                    "duration_ms": 2000,
                    "outcome": "completed",
                },
            ]
            log_path.write_text(
                "\n".join(json.dumps(entry, sort_keys=True) for entry in entries) + "\n",
                encoding="utf-8",
            )

            rc, output = run_cli(
                "time-ledger",
                "summary",
                "--log",
                str(log_path),
                "--format",
                "json",
            )

            self.assertEqual(rc, 0, output)
            payload = json.loads(output)
            self.assertEqual(payload["schema_version"], "nac.codex-time-ledger-summary/v0.1")
            self.assertEqual(payload["total_duration_ms"], 10000)
            self.assertEqual(payload["entries"], 3)
            self.assertEqual(payload["by_category"]["local_io"]["duration_ms"], 3000)
            self.assertEqual(payload["by_category"]["local_cpu"]["duration_ms"], 5000)
            self.assertEqual(payload["by_category"]["approval_wait"]["duration_ms"], 2000)
            self.assertEqual(payload["by_phase"]["tests"]["duration_ms"], 5000)
            self.assertAlmostEqual(payload["by_category"]["local_cpu"]["share"], 0.5)

    def test_time_ledger_run_times_child_command_and_returns_child_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "codex-time-ledger.jsonl"

            rc, output = run_cli(
                "time-ledger",
                "run",
                "--log",
                str(log_path),
                "--session-id",
                "2026-06-15-nac",
                "--task",
                "NaC observability",
                "--phase",
                "tiny-command",
                "--category",
                "local_cpu",
                "--format",
                "json",
                "--",
                sys.executable,
                "-c",
                "pass",
            )

            self.assertEqual(rc, 0, output)
            payload = json.loads(output)
            self.assertEqual(payload["child_return_code"], 0)
            self.assertEqual(payload["outcome"], "completed")
            self.assertGreaterEqual(payload["duration_ms"], 0)

            entry = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(entry["phase"], "tiny-command")
            self.assertEqual(entry["category"], "local_cpu")
            self.assertEqual(entry["exit_code"], 0)


if __name__ == "__main__":
    unittest.main()
