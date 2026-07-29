from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeProductionCompositionCliTests(unittest.TestCase):
    def test_cli_reports_verified_offline_edge_and_live_block(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime_root = Path(directory) / "runtime"
            runtime_root.mkdir(mode=0o700)
            os.chmod(runtime_root, 0o700)
            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-production-composition",
                    "--s4g-runtime-root",
                    str(runtime_root),
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
        self.assertEqual(
            result["status"],
            "S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE",
        )
        self.assertEqual(
            result["live_status"],
            "BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION",
        )
        self.assertFalse(result["runtime_factory_constructed"])
        self.assertEqual(result["summary"]["tenant_writes"], 0)

    def test_cli_requires_explicit_runtime_root(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "m365",
                "teams-sharepoint",
                "business-case-type-production-composition",
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
        self.assertNotIn("access_token", completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
