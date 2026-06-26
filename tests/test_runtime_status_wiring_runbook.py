from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DE_DOC = REPO_ROOT / "docs" / "de" / "architecture" / "runtime-status-wiring-runbook.md"
EN_DOC = REPO_ROOT / "docs" / "en" / "architecture" / "runtime-status-wiring-runbook.md"
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "runtime-status-wiring-runbook.contract.json"
CONTRACT_README = REPO_ROOT / "workflows" / "contracts" / "README.md"


class RuntimeStatusWiringRunbookTests(unittest.TestCase):
    def test_contract_defines_safe_runtime_status_wiring_boundary(self) -> None:
        self.assertTrue(CONTRACT.is_file(), CONTRACT)
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], "nac.workflow-contract/v0.1")
        self.assertEqual(contract["contract_id"], "workflow.runtime_status_wiring_runbook")
        self.assertEqual(contract["status"], "owner_free_contract_first")
        self.assertEqual(contract["runtime_store"], "atp_adapter_future_slice")
        self.assertEqual(contract["current_store"], "in_memory_demo_adapter")
        self.assertEqual(
            contract["route"],
            "/workspace/immobilienkaufvertrag",
        )
        seam = contract["atp_metadata_seam_v0"]
        self.assertEqual(seam["source_env"], "NAC_FIRST_MATTER_RUNTIME_SOURCE")
        self.assertEqual(
            seam["accepted_source_values"],
            ["atp", "atp-json", "atp_metadata", "atp-runtime-metadata"],
        )
        self.assertEqual(seam["object_key_env"], "NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY")
        self.assertEqual(seam["default_object_key"], "DEMO-PROCESS-IMMOBILIENKAUF-01")
        self.assertEqual(seam["payload_column_env"], "NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN")
        self.assertEqual(seam["table_env"], "NAC_FIRST_MATTER_RUNTIME_TABLE")
        self.assertEqual(seam["default_table"], "nac_process_instances")
        self.assertEqual(seam["key_column_env"], "NAC_FIRST_MATTER_RUNTIME_KEY_COLUMN")
        self.assertEqual(seam["default_key_column"], "process_instance_id")
        self.assertIn("nac_process_instances", seam["allowed_tables"])
        self.assertEqual(seam["sql_identifier_policy"], "allowlisted_table_key_and_payload_columns_only")
        self.assertFalse(seam["packaged_fallback_when_atp_enabled"])
        self.assertTrue(seam["requires_existing_atp_secret_reference"])
        self.assertTrue(seam["wallet_references_reused_only"])
        self.assertFalse(seam["plaintext_password_env_allowed"])
        self.assertFalse(seam["database_migration_required"])
        self.assertFalse(seam["oci_apply_required"])
        self.assertFalse(seam["secrets_or_wallet_change_required"])

        guardrails = contract["guardrails"]
        for key in (
            "mandate_data_allowed",
            "productive_xnp_action_allowed",
            "secrets_allowed",
            "oci_apply_allowed",
            "browser_identifiers_allowed",
            "provider_details_allowed",
        ):
            self.assertFalse(guardrails[key], key)
        self.assertTrue(guardrails["fail_closed_required"])
        self.assertTrue(guardrails["append_only_process_events_required"])
        self.assertTrue(guardrails["graph_projection_derived_from_events"])

    def test_runbooks_explain_current_and_future_wiring_without_sensitive_output(self) -> None:
        for path in (DE_DOC, EN_DOC):
            self.assertTrue(path.is_file(), path)
            content = path.read_text(encoding="utf-8")
            normalized = content.lower()

            for required in (
                "notariat8",
                "RuntimeStoreAdapter",
                "InMemoryRuntimeStore",
                "ATP",
                "process_events",
                "graph projection",
                "/workspace",
                "/workspace/immobilienkaufvertrag",
                "Immobilienkaufvertrag",
                "XNP/SNP",
                "fail-closed",
                "NAC_FIRST_MATTER_RUNTIME_TABLE",
                "NAC_FIRST_MATTER_RUNTIME_KEY_COLUMN",
                "NAC_ATP_PASSWORD_SECRET_OCID",
                "DEMO-PROCESS-IMMOBILIENKAUF-01",
                "nac_process_instances",
                "process_instance_id",
                "no mandate data",
                "no OCI Apply",
            ):
                self.assertIn(required, content, f"{required} missing in {path}")

            for forbidden in (
                "client_secret",
                "private_key",
                "session_id",
                "process_instance_id in browser",
                "tenant_id in browser",
                "matter_id in browser",
                "provider details in browser",
                "productive xnp action allowed",
            ):
                self.assertNotIn(forbidden, normalized, f"{forbidden} leaked in {path}")

    def test_contract_readme_lists_runtime_status_wiring_runbook(self) -> None:
        content = CONTRACT_README.read_text(encoding="utf-8")

        self.assertIn("runtime-status-wiring-runbook.contract.json", content)
        self.assertIn("Runtime-Status", content)


if __name__ == "__main__":
    unittest.main()
