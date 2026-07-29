from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeLiveWriteReadinessContractTests(unittest.TestCase):
    def test_contract_pair_and_validator(self) -> None:
        contract = json.loads(
            (
                ROOT
                / "workflows/contracts/"
                "business-case-type-live-write-readiness-s4e.contract.json"
            ).read_text(encoding="utf-8")
        )
        verification = json.loads(
            (
                ROOT
                / "workflows/verification-contracts/"
                "business-case-type-live-write-readiness-s4e.verification.json"
            ).read_text(encoding="utf-8")
        )

        self.assertEqual(contract["status"], "BLOCKED")
        self.assertEqual(
            contract["acceptanceIdsExact"],
            [f"AC-S4E-{index:02d}" for index in range(1, 8)],
        )
        self.assertFalse(
            contract["identityBoundary"]["provisioningAppExecutesBusinessWrites"]
        )
        self.assertEqual(
            verification["passCondition"]["currentStatusExact"], "BLOCKED"
        )
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/validate_business_case_type_live_write_readiness.py",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
