from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeLiveWriteBoundaryCliTests(unittest.TestCase):
    def test_cli_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-live-write-smoke",
                    "--database-path",
                    str(Path(directory) / "state.sqlite"),
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
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "S4D_READY_OFFLINE")
        self.assertEqual(result["summary"]["tenant_writes"], 0)

    def test_cli_requires_absolute_database_path(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "m365",
                "teams-sharepoint",
                "business-case-type-live-write-smoke",
                "--database-path",
                "relative.sqlite",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertNotIn("access_token", completed.stderr)
