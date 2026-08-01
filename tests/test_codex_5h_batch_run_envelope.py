from __future__ import annotations

import json
import subprocess
import sys
import unittest
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_agent_ops.batch_run_envelope import (
    build_batch_run_envelope_template,
    batch_run_envelope_status,
    format_batch_run_envelope_status,
    load_batch_run_envelope,
    validate_batch_run_envelope,
)


FIXTURE = REPO_ROOT / "tests/fixtures/agent-ops/codex-5h-batch-run-envelope.valid.json"


class Codex5hBatchRunEnvelopeTests(unittest.TestCase):
    def test_valid_fixture_passes(self) -> None:
        payload = load_batch_run_envelope(FIXTURE)

        self.assertEqual(validate_batch_run_envelope(payload), [])
        status = batch_run_envelope_status(payload)
        self.assertEqual(status["status"], "PASSED")
        self.assertEqual(status["summary"]["lane_count"], 2)
        self.assertFalse(status["summary"]["executes_live_tenant_actions"])
        self.assertFalse(status["summary"]["stores_tokens_or_secrets"])

    def test_template_passes_validation(self) -> None:
        payload = build_batch_run_envelope_template(
            session_id="test-batch",
            objective="Prepare independent offline slices.",
            time_budget_hours=5,
        )

        self.assertEqual(validate_batch_run_envelope(payload), [])
        self.assertIn("Status: `PASSED`", format_batch_run_envelope_status(batch_run_envelope_status(payload)))

    def test_rejects_duplicate_write_scope(self) -> None:
        payload = _fixture()
        payload["lanes"][1]["write_scope"] = payload["lanes"][0]["write_scope"][:]

        errors = validate_batch_run_envelope(payload)

        self.assertTrue(any("used by both" in error for error in errors))

    def test_rejects_writable_lane_without_worktree(self) -> None:
        payload = _fixture()
        payload["lanes"][0]["worktree_required"] = False
        payload["lanes"][0]["worktree_path"] = ""

        errors = validate_batch_run_envelope(payload)

        self.assertIn("matter-access-decision-replay with write_scope must set worktree_required=true", errors)
        self.assertIn("matter-access-decision-replay with write_scope must set worktree_path", errors)

    def test_rejects_missing_subagent_plan_for_parallel_review_questions(self) -> None:
        payload = _fixture()
        payload["subagent_review"]["independent_review_questions_count"] = 3
        payload["subagent_review"]["subagent_plan"] = []
        payload["subagent_review"]["no_split_reason"] = None

        errors = validate_batch_run_envelope(payload)

        self.assertIn("two or more independent review questions require subagent_plan or no_split_reason", errors)

    def test_rejects_subagent_without_context_isolation(self) -> None:
        payload = _fixture()
        plan = payload["subagent_review"]["subagent_plan"][0]
        plan["fork_context"] = True
        plan["prompt_context"] = ["task", "paths"]
        plan["close_completed_immediately"] = False

        errors = validate_batch_run_envelope(payload)

        self.assertTrue(any("fork_context must be false" in error for error in errors))
        self.assertTrue(any("prompt_context must contain" in error for error in errors))
        self.assertTrue(any("close_completed_immediately must be true" in error for error in errors))

    def test_rejects_single_subagent_below_threshold_and_without_isolation(self) -> None:
        payload = _fixture()
        payload["subagent_review"]["independent_review_questions_count"] = 1
        payload["subagent_review"]["subagent_plan"] = [
            {"id": "single", "role": "single reviewer", "read_only": True}
        ]

        errors = validate_batch_run_envelope(payload)

        self.assertIn(
            "subagent_plan requires at least two independent review questions", errors
        )
        self.assertTrue(any("fork_context must be false" in error for error in errors))
        self.assertTrue(any("prompt_context must contain" in error for error in errors))
        self.assertTrue(any("close_completed_immediately must be true" in error for error in errors))

    def test_rejects_red_command_and_yellow_without_owner_gate(self) -> None:
        payload = _fixture()
        payload["command_risk_matrix"].append(
            {"risk": "RED", "command": "rm -rf out", "decision": "block"}
        )
        payload["command_risk_matrix"].append(
            {"risk": "YELLOW", "command": "gh pr merge", "decision": "allow"}
        )

        errors = validate_batch_run_envelope(payload)

        self.assertTrue(any("RED command is prohibited" in error for error in errors))
        self.assertTrue(any("YELLOW command requires owner_gate" in error for error in errors))

    def test_validator_script_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_codex_5h_batch_run_envelope.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


def _fixture() -> dict[str, object]:
    return deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
