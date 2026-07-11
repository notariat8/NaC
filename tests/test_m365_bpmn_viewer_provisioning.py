from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.bpmn_viewer_provisioning import (  # noqa: E402
    DEFAULT_BPMN_VIEWER_PROVISIONING,
    PROCESS_ROW_BPMN_FIELDS,
    build_bpmn_viewer_provisioning_plan,
    load_bpmn_viewer_provisioning_config,
    summarize_bpmn_viewer_provisioning_plan,
    validate_bpmn_viewer_provisioning_config,
)
from nac_m365_graph.schema import load_schema  # noqa: E402


class M365BpmnViewerProvisioningTests(unittest.TestCase):
    def test_optional_config_validates_without_changing_required_mvp_schema(self) -> None:
        config = load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
        schema = load_schema()

        self.assertEqual(validate_bpmn_viewer_provisioning_config(config), [])
        self.assertNotIn(
            "Prozessregister",
            {item["display_name"] for item in schema["sharepoint"]["lists"]},
        )
        self.assertNotIn(
            "BPMN Models",
            {item["display_name"] for item in schema["sharepoint"]["document_libraries"]},
        )
        self.assertFalse(config["live_apply"]["implemented"])
        self.assertFalse(config["live_apply"]["mutates_tenant_now"])
        self.assertTrue(config["live_apply"]["owner_gate_required_before_future_apply"])
        library = next(
            item
            for item in config["sharepoint"]["document_libraries"]
            if item["display_name"] == "BPMN Models"
        )
        library_columns = {column["name"]: column for column in library["columns"]}
        self.assertTrue(PROCESS_ROW_BPMN_FIELDS <= set(library_columns))
        self.assertTrue(all(library_columns[name]["required"] for name in PROCESS_ROW_BPMN_FIELDS))
        process_register = next(
            item
            for item in config["sharepoint"]["lists"]
            if item["display_name"] == "Prozessregister"
        )
        process_columns = {column["name"]: column for column in process_register["columns"]}
        process_key = process_columns["ProcessKey"]
        self.assertTrue(process_key["enforce_unique_values"])
        self.assertIn("ProcessKey", process_register["indexed_columns"])
        self.assertTrue(PROCESS_ROW_BPMN_FIELDS <= set(process_columns))
        self.assertTrue(all(not process_columns[name]["required"] for name in PROCESS_ROW_BPMN_FIELDS))
        self.assertIn("BpmnXmlMimeType", library_columns)

    def test_rejects_nonunique_or_unindexed_process_key(self) -> None:
        config = load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
        process_register = config["sharepoint"]["lists"][0]
        process_key = next(
            column
            for column in process_register["columns"]
            if column["name"] == "ProcessKey"
        )
        process_key.pop("enforce_unique_values")
        errors = validate_bpmn_viewer_provisioning_config(config)
        self.assertIn("bpmn viewer provisioning Prozessregister ProcessKey must enforce unique values", errors)

        unindexed = load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
        unindexed_register = unindexed["sharepoint"]["lists"][0]
        unindexed_register["indexed_columns"].remove("ProcessKey")
        errors = validate_bpmn_viewer_provisioning_config(unindexed)
        self.assertIn("bpmn viewer provisioning Prozessregister ProcessKey must be indexed", errors)

    def test_rejects_nonnullable_process_register_bpmn_links(self) -> None:
        config = load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
        process_register = config["sharepoint"]["lists"][0]
        model_id = next(
            column
            for column in process_register["columns"]
            if column["name"] == "NacBpmnModelId"
        )
        model_id["required"] = True

        errors = validate_bpmn_viewer_provisioning_config(config)

        self.assertIn(
            "bpmn viewer provisioning Prozessregister column NacBpmnModelId must be nullable",
            errors,
        )

    def test_rejects_nullable_bpmn_models_metadata(self) -> None:
        config = load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
        library = config["sharepoint"]["document_libraries"][0]
        model_id = next(
            column
            for column in library["columns"]
            if column["name"] == "NacBpmnModelId"
        )
        model_id["required"] = False

        errors = validate_bpmn_viewer_provisioning_config(config)

        self.assertIn(
            "bpmn viewer provisioning BPMN Models column NacBpmnModelId must be required",
            errors,
        )

    def test_plan_is_owner_gated_optional_sharepoint_surface_only(self) -> None:
        config = load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
        operations = build_bpmn_viewer_provisioning_plan(config)
        summary = summarize_bpmn_viewer_provisioning_plan(operations)

        self.assertEqual(summary["operation_count"], 68)
        self.assertEqual(summary["owner_gated_operations"], 68)
        self.assertFalse(summary["mutates_tenant_now"])
        self.assertFalse(summary["live_apply_implemented"])
        self.assertEqual(
            set(summary["by_action"]),
            {
                "ensure_optional_bpmn_viewer_document_library",
                "ensure_optional_bpmn_viewer_library_column",
                "ensure_optional_bpmn_viewer_list",
                "ensure_optional_bpmn_viewer_column",
            },
        )
        self.assertTrue(all(operation.owner_gate_required for operation in operations))
        self.assertTrue(all(operation.graph_method == "POST" for operation in operations))
        process_key_operations = [
            operation
            for operation in operations
            if operation.target == "Prozessregister.ProcessKey"
        ]
        self.assertEqual(len(process_key_operations), 2)
        for operation in process_key_operations:
            self.assertTrue(operation.payload["enforceUniqueValues"])
            self.assertTrue(operation.payload["indexed"])

    def test_central_cli_exposes_bpmn_viewer_plan_without_live_apply(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "bpmn-viewer-plan",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["operation_count"], 68)
        self.assertFalse(payload["guardrails"]["mutates_tenant_now"])
        self.assertFalse(payload["guardrails"]["live_apply_implemented"])
        self.assertTrue(payload["guardrails"]["owner_gate_required_before_future_apply"])
        self.assertTrue(payload["guardrails"]["mcp_tools_request_plan_only"])


if __name__ == "__main__":
    unittest.main()
