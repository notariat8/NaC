from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeLiveWriteBoundaryContractTests(unittest.TestCase):
    def test_contract_pair_and_validator(self) -> None:
        contract = json.loads(
            (
                ROOT
                / "workflows/contracts/"
                "business-case-type-live-write-boundary-s4d.contract.json"
            ).read_text(encoding="utf-8")
        )
        verification = json.loads(
            (
                ROOT
                / "workflows/verification-contracts/"
                "business-case-type-live-write-boundary-s4d.verification.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(contract["status"], "S4D_READY_OFFLINE")
        self.assertEqual(
            contract["acceptanceIdsExact"],
            [f"AC-S4D-{index:02d}" for index in range(1, 9)],
        )
        self.assertEqual(
            verification["passCondition"]["statusExact"],
            "S4D_READY_OFFLINE",
        )
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/validate_business_case_type_live_write_boundary.py",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

