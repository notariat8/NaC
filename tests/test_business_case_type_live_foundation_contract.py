from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = REPO_ROOT / "workflows/contracts/business-case-type-live-foundation.contract.json"
VERIFICATION_PATH = (
    REPO_ROOT
    / "workflows/verification-contracts/business-case-type-live-foundation.verification.json"
)


class BusinessCaseTypeLiveFoundationContractTests(unittest.TestCase):
    def test_contracts_cover_exact_issue_acceptance_boundary(self) -> None:
        domain = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
        verification = json.loads(VERIFICATION_PATH.read_text(encoding="utf-8"))
        acceptance_ids = [f"AC-678-{number:02d}" for number in range(1, 9)]

        self.assertEqual(
            [item["id"] for item in domain["acceptance_criteria"]], acceptance_ids
        )
        self.assertEqual(verification["acceptance_ids"], acceptance_ids)
        self.assertEqual(domain["scope"]["workspace_id_exact"], "notary_team_01")
        self.assertFalse(domain["scope"]["other_workspaces_allowed"])
        self.assertFalse(domain["scope"]["migration_allowed"])
        self.assertFalse(domain["scope"]["deletes_allowed"])
        self.assertFalse(domain["scope"]["rollbacks_allowed"])
        self.assertEqual(domain["graph_boundary"]["allowed_methods"], ["GET", "POST"])
        self.assertEqual(domain["graph_boundary"]["forbidden_methods"], ["PATCH", "DELETE"])
        self.assertEqual(
            domain["graph_boundary"]["application_permission"], "Sites.FullControl.All"
        )
        self.assertEqual(
            domain["graph_boundary"]["provisioner_binding"]["application_display_name_exact"],
            "NaC M365 Provisioning",
        )
        self.assertFalse(
            domain["graph_boundary"]["provisioner_binding"]["permission_change_required"]
        )
        self.assertFalse(
            domain["graph_boundary"]["provisioner_binding"]["permission_mutation_allowed"]
        )
        self.assertEqual(domain["registry_contract"]["canonical_row_count_exact"], 20)
        self.assertEqual(domain["registry_contract"]["alias_row_count_exact"], 0)
        self.assertEqual(verification["thresholds"]["second_run_mutations"], 0)
        self.assertEqual(verification["thresholds"]["allowed_test_graph_calls"], 0)

    def test_quality_gate_declares_live_foundation_validator(self) -> None:
        quality_gate = (REPO_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
        self.assertIn("validate_business_case_type_live_foundation.py", quality_gate)


if __name__ == "__main__":
    unittest.main()
