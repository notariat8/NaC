from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeLiveWriteReadinessCliTests(unittest.TestCase):
    def test_cli_reports_current_blockers_without_live_access(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "m365",
                "teams-sharepoint",
                "business-case-type-live-write-readiness",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 2, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["live_write_authorized"])
        self.assertEqual(result["summary"]["tenant_writes"], 0)


if __name__ == "__main__":
    unittest.main()
