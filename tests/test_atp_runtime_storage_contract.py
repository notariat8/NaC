from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "atp-runtime-storage.contract.json"


class AtpRuntimeStorageContractTests(unittest.TestCase):
    def test_runtime_storage_contract_defines_anchors_payloads_and_graph_projection(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "nac.atp-runtime-storage/v0.1")
        self.assertEqual(payload["contract_id"], "runtime.atp_storage")
        self.assertEqual(payload["status"], "contract_first_no_schema_apply")
        self.assertEqual(payload["runtime_data_plane"], "oracle_atp")

        self.assertEqual(
            payload["source_of_truth"]["git"],
            ["code", "iac", "governance", "bpmn_templates", "synthetic_demo_data"],
        )
        self.assertEqual(
            payload["source_of_truth"]["atp"],
            [
                "tenants",
                "user_bindings",
                "sessions",
                "matters",
                "process_instances",
                "process_events",
                "audit_metadata",
            ],
        )

        anchor_ids = {anchor["id"] for anchor in payload["transactional_anchors"]}
        self.assertGreaterEqual(
            anchor_ids,
            {
                "tenants",
                "user_bindings",
                "sessions",
                "matters",
                "process_templates",
                "process_instances",
                "process_events",
                "audit_events",
            },
        )

        for anchor in payload["transactional_anchors"]:
            self.assertIn("safe_metadata_only", anchor["allowed_data_classes"])
            self.assertNotIn("raw_mandate_content", anchor["allowed_data_classes"])

        json_policy = payload["json_payload_policy"]
        self.assertTrue(json_policy["schema_version_required"])
        self.assertTrue(json_policy["payload_type_required"])
        self.assertTrue(json_policy["redaction_class_required"])
        self.assertFalse(json_policy["raw_mandate_content_allowed_before_separate_gate"])

        graph_projection = payload["graph_projection"]
        self.assertEqual(graph_projection["status"], "projection_contract_only")
        self.assertIn("ProcessInstance", graph_projection["node_types"])
        self.assertIn("ExternalSystem", graph_projection["node_types"])
        self.assertIn("critical_path_of", graph_projection["edge_types"])
        self.assertIn("sent_to", graph_projection["edge_types"])
        self.assertIn("received_from", graph_projection["edge_types"])

        anchor_schema = payload["anchor_schema"]
        self.assertEqual(anchor_schema["status"], "artifact_only_no_apply")
        self.assertEqual(anchor_schema["artifact"], "deploy/database/atp-runtime-anchor-schema.sql")
        self.assertTrue(anchor_schema["guardrails"]["idempotent_create_only"])
        self.assertFalse(anchor_schema["guardrails"]["drop_or_truncate_allowed"])
        self.assertFalse(anchor_schema["guardrails"]["raw_mandate_payload_columns_allowed"])

        table_names = {table["name"] for table in anchor_schema["tables"]}
        self.assertGreaterEqual(
            table_names,
            {
                "nac_tenants",
                "nac_user_bindings",
                "nac_matters",
                "nac_process_templates",
                "nac_process_instances",
                "nac_process_events",
                "nac_audit_events",
            },
        )

    def test_runtime_storage_contract_preserves_guardrails(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        guardrails = payload["guardrails"]

        self.assertFalse(guardrails["productive_schema_apply_approved"])
        self.assertFalse(guardrails["productive_graph_activation_approved"])
        self.assertFalse(guardrails["raw_mandate_data_in_git_allowed"])
        self.assertFalse(guardrails["secrets_in_git_allowed"])
        self.assertFalse(guardrails["oci_apply_approved"])
        self.assertTrue(guardrails["protected_pr_required"])

        forbidden = json.dumps(payload, ensure_ascii=False).lower()
        self.assertNotIn("sql-only", forbidden)
        self.assertNotIn("productive mandate payload", forbidden)


if __name__ == "__main__":
    unittest.main()
