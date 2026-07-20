from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli.cli import main  # noqa: E402


class BusinessCaseTypeLiveFoundationCliTests(unittest.TestCase):
    def test_plan_command_emits_offline_plan(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-live-foundation-plan",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])

    def test_apply_command_only_validates_owner_gate(self) -> None:
        plan_output = io.StringIO()
        with redirect_stdout(plan_output):
            main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-live-foundation-plan",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                ]
            )
        plan_sha256 = json.loads(plan_output.getvalue())["plan_sha256"]
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-live-foundation-apply",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--expected-plan-sha256",
                    plan_sha256,
                    "--approval-reference",
                    "owner-ref",
                    "--reason",
                    "approved additive foundation",
                    "--owner-approved",
                    "--execute-live-foundation",
                    "--format",
                    "json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "READY_FOR_INJECTED_RUNNER")
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])
        self.assertFalse(payload["summary"]["live_execution_composed"])
        self.assertNotIn("owner-ref", output.getvalue())
        self.assertNotIn("approved additive foundation", output.getvalue())

    def test_plan_rejects_other_workspace(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-live-foundation-plan",
                    "--repo-root",
                    str(REPO_ROOT),
                    "--workspace-id",
                    "notary_team_02",
                    "--format",
                    "json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 2)
        self.assertEqual(payload["error_code"], "WORKSPACE_SCOPE_MISMATCH")


if __name__ == "__main__":
    unittest.main()
