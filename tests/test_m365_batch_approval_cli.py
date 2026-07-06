from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class M365BatchApprovalCliTests(unittest.TestCase):
    def test_batch_approval_renders_merge_text_without_writes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-pr",
                "#383,385",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_github_writes"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertEqual(payload["result"]["merge"]["prs"], ["#383", "#385"])
        self.assertIn("Freigabe: PRs #383, #385 mergen", payload["result"]["merge"]["approval_text"])

    def test_batch_approval_renders_live_smoke_text_without_writes(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--batch-mode",
                "live-smoke",
                "--workspace-id",
                "notary_team_01",
                "--synthetic-case-id",
                "NAC-SMOKE-WRITE-READ-20260706T123000Z",
                "--correlation-id",
                "batch-corr-1",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["owner_gates"], ["m365_tenant_write_and_delete"])
        live_smoke = payload["result"]["live_smoke"]
        self.assertIn("synthetischer Testakte", live_smoke["approval_text"])
        self.assertIn("mcp-positive-write-read-smoke", live_smoke["commands"][0])
        self.assertIn("mcp-smoke-cleanup", live_smoke["commands"][1])

    def test_batch_approval_requires_prs_for_merge_mode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "batch-approval",
                "m365",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("--batch-pr", payload["errors"][0])


if __name__ == "__main__":
    unittest.main()
