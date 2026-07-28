from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BusinessCaseTypeImmutableEvidenceContractTests(unittest.TestCase):
    def test_domain_and_verification_contracts_share_acceptance_ids(self) -> None:
        domain = json.loads(
            (ROOT / "workflows/contracts/business-case-type-immutable-evidence-s6.contract.json").read_text(
                encoding="utf-8"
            )
        )
        verification = json.loads(
            (ROOT / "workflows/verification-contracts/business-case-type-immutable-evidence-s6.verification.json").read_text(
                encoding="utf-8"
            )
        )
        acceptance_ids = [f"AC-S6-{index:02d}" for index in range(1, 9)]

        self.assertEqual(
            [item["id"] for item in domain["acceptance_criteria"]], acceptance_ids
        )
        self.assertEqual(verification["acceptance_ids"], acceptance_ids)
        self.assertEqual(domain["status"], "S6_OFFLINE_FOUNDATION")
        self.assertEqual(
            domain["slice"]["live_status_exact"], "BLOCKED_PENDING_S7_APPROVAL"
        )

    def test_central_contract_commands_register_s6_validator(self) -> None:
        cli_text = (ROOT / "src/nac_cli/cli.py").read_text(encoding="utf-8")
        self.assertIn(
            "Business Case Type Immutable Evidence S6",
            cli_text,
        )
        self.assertGreaterEqual(
            cli_text.count("validate_business_case_type_immutable_evidence.py"),
            2,
        )


    def test_standalone_validator_passes(self) -> None:
        path = ROOT / "scripts/validate_business_case_type_immutable_evidence.py"
        spec = importlib.util.spec_from_file_location("validate_s6", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
