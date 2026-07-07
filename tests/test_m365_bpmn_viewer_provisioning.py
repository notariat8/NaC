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
        library_columns = {
            column["name"]
            for library in config["sharepoint"]["document_libraries"]
            for column in library["columns"]
        }
        self.assertIn("BpmnDriveItemId", library_columns)
        self.assertIn("BpmnContentMode", library_columns)
        self.assertIn("BpmnXmlMimeType", library_columns)
        list_columns = {
            column["name"]
            for list_def in config["sharepoint"]["lists"]
            for column in list_def["columns"]
        }
        self.assertIn("BpmnContentMode", list_columns)

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
