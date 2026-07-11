from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class VerificationContractsDomainPilotTests(unittest.TestCase):
    def test_decision_index_lists_matter_access_adrs(self) -> None:
        payload = _read_json("agent-context/decision-index.json")

        self.assertEqual(payload["schema_version"], "nac.agent-decision-index/v0.1")
        decision_ids = {item["id"] for item in payload["decisions"]}
        self.assertGreaterEqual(
            decision_ids,
            {
                "ADR-M365-MATTER-ACCESS-001",
                "ADR-M365-MATTER-ACCESS-002",
                "ADR-M365-MATTER-ACCESS-003",
            },
        )
        for item in (entry for entry in payload["decisions"] if entry["domain"] == "m365_matter_access_delegation"):
            self.assertEqual(item["status"], "accepted")
            self.assertEqual(item["domain"], "m365_matter_access_delegation")
            self.assertIn(
                "workflows/verification-contracts/m365-matter-access-delegation.verification.json",
                item["verification_contracts"],
            )

    def test_invariant_index_lists_critical_matter_access_guardrails(self) -> None:
        payload = _read_json("agent-context/invariant-index.json")

        self.assertEqual(payload["schema_version"], "nac.agent-invariant-index/v0.1")
        invariant_ids = {item["id"] for item in payload["invariants"]}
        self.assertGreaterEqual(
            invariant_ids,
            {
                "invariant.m365_matter_access.no_blanket_visibility",
                "invariant.m365_matter_access.timeboxed_deputy_access",
                "invariant.m365_matter_access.reason_approver_audit_required",
                "invariant.m365_graph.rest_only_no_legacy_sdk",
                "invariant.m365_matter_access.owner_gate_before_live_write",
                "invariant.m365_evidence.redacted_only_no_matter_payloads",
            },
        )
        for item in (entry for entry in payload["invariants"] if entry["domain"] == "m365_matter_access_delegation"):
            self.assertEqual(item["severity"], "critical")
            self.assertIn("scripts/validate_verification_contracts_domain_pilot.py", item["enforced_by"])

    def test_matter_access_verification_contract_binds_domain_evidence(self) -> None:
        payload = _read_json("workflows/verification-contracts/m365-matter-access-delegation.verification.json")

        self.assertEqual(payload["schema_version"], "nac.verification-contract/v0.1")
        self.assertEqual(payload["domain_contract_id"], "m365.matter_access_delegation")
        self.assertEqual(payload["thresholds"]["required_matter_access_release_gate_artifacts"], 4)
        self.assertEqual(payload["thresholds"]["max_live_apply_steps_without_owner_gate"], 0)
        self.assertTrue(payload["pass_condition"]["all_required_invariants_indexed"])
        self.assertTrue(payload["pass_condition"]["matter_access_artifacts_attached_to_release_gate"])
        self.assertIn("matter_access_apply_request_plan", payload["required_evidence"])
        self.assertIn("matter_access_apply_policy_enforcement", payload["required_evidence"])
        self.assertIn("matter_access_apply_policy_smoke", payload["required_evidence"])
        self.assertIn("negative_apply_policy_smoke", payload["required_evidence"])
        self.assertEqual(payload["failure_behavior"]["owner_gate_missing"], "block_live_apply")

    def test_agent_context_routes_domain_indexes_and_verification_contract(self) -> None:
        payload = _read_json("agent-context/index.json")

        self.assertIn(
            "workflows/verification-contracts/m365-matter-access-delegation.verification.json",
            payload["verification_contracts"],
        )
        categories = {
            category["id"]: category["paths"]
            for layer in payload["layers"]
            for category in layer.get("categories", [])
        }
        self.assertIn("agent-context/decision-index.json", categories["history"])
        self.assertIn("agent-context/invariant-index.json", categories["guardrails"])


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
