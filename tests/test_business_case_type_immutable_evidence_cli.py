from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeImmutableEvidenceCliTests(unittest.TestCase):
    def test_central_nac_cli_exposes_redacted_offline_dry_run(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "kg",
                "business-case-type-evidence-dry-run",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(output["status"], "S6_OFFLINE_FOUNDATION")
        self.assertEqual(output["live_status"], "BLOCKED_PENDING_S7_APPROVAL")
        for field in (
            "network_calls",
            "provider_calls",
            "tenant_calls",
            "tenant_writes",
            "credential_reads",
            "live_mutations",
        ):
            self.assertEqual(output[field], 0)
        self.assertFalse(output["production_worm_claim"])


if __name__ == "__main__":
    unittest.main()
