from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeProductionAdaptersCliTests(unittest.TestCase):
    def test_json_status_is_partial_and_offline(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "m365",
                "teams-sharepoint",
                "business-case-type-production-adapters",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual("S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE", payload["status"])
        self.assertFalse(payload["central_truth_claimed"])
        self.assertFalse(payload["live_write_authorized"])
        self.assertEqual(0, payload["summary"]["graph_calls"])
        self.assertEqual(0, payload["summary"]["tenant_writes"])
        self.assertIn(
            "production_identity_inspection_readback",
            payload["remaining_blockers"],
        )

    def test_text_output_does_not_claim_live_readiness(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "m365",
                "teams-sharepoint",
                "business-case-type-production-adapters",
                "--format",
                "text",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE", completed.stdout)
        self.assertIn("Live write authorized: false", completed.stdout)
        self.assertNotIn("LIVE_READY", completed.stdout)


if __name__ == "__main__":
    unittest.main()
