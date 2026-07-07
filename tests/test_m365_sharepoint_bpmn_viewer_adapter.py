from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "m365-sharepoint-bpmn-viewer-adapter.contract.json"


class M365SharePointBpmnViewerAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_keeps_sharepoint_viewer_only(self) -> None:
        spfx = self.contract["spfx_surface"]
        self.assertEqual(spfx["delivery"], "SharePoint Framework Web Part")
        self.assertEqual(spfx["library"], "bpmn-js")
        self.assertEqual(spfx["bpmn_js_mode"], "viewer_only")
        self.assertTrue(spfx["included_in_nac_repo_now"])
        self.assertEqual(spfx["package_root"], "spfx/nac-bpmn-viewer")
        self.assertEqual(spfx["status"], "offline_source_only")
        self.assertFalse(spfx["app_catalog_deploy_allowed_now"])
        self.assertFalse(spfx["tenant_apply_allowed_now"])
        self.assertFalse(spfx["executes_graph_requests_now"])
        self.assertFalse(spfx["modeler_enabled"])
        self.assertFalse(spfx["workflow_execution_allowed"])
        self.assertFalse(spfx["requires_custom_script"])

    def test_contract_keeps_graph_rest_boundary(self) -> None:
        graph = self.contract["graph_policy"]
        self.assertTrue(graph["graph_rest_only"])
        self.assertTrue(graph["raw_http_required"])
        self.assertFalse(graph["legacy_sharepoint_api_allowed"])
        self.assertFalse(graph["csom_allowed"])
        self.assertFalse(graph["pnp_allowed"])
        self.assertFalse(graph["graph_sdk_allowed"])
        self.assertIn(
            "GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/content",
            graph["allowed_endpoint_patterns"],
        )

    def test_contract_blocks_modeler_execution_and_matter_payloads(self) -> None:
        blocked = set(self.contract["blocked_operations"])
        for operation in {
            "write_bpmn_xml",
            "save_bpmn_model",
            "execute_workflow",
            "start_process_instance",
            "mutate_sharepoint_schema",
            "read_matter_document_content",
            "read_matter_payload",
            "store_mandate_data",
        }:
            self.assertIn(operation, blocked)
        self.assertTrue(self.contract["sharepoint_surface"]["approved_bpmn_xml_content_read_allowed"])
        self.assertFalse(self.contract["sharepoint_surface"]["matter_document_content_reads_allowed"])

    def test_contract_links_optional_provisioning_plan_without_live_apply(self) -> None:
        optional_plan = self.contract["optional_provisioning_plan"]

        self.assertEqual(
            optional_plan["artifact"],
            "deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json",
        )
        self.assertEqual(optional_plan["command"], "nac m365 teams-sharepoint bpmn-viewer-plan --format json")
        self.assertEqual(optional_plan["status"], "optional_plan_only_no_live_apply")
        self.assertFalse(optional_plan["adds_to_required_mvp_schema_now"])
        self.assertFalse(optional_plan["live_apply_implemented"])
        self.assertFalse(optional_plan["mutates_tenant_now"])
        self.assertTrue(optional_plan["owner_gate_required_before_future_apply"])
        self.assertEqual(optional_plan["planned_document_libraries"], ["BPMN Models"])
        self.assertEqual(optional_plan["planned_lists"], ["Prozessregister"])

    def test_contract_links_offline_spfx_skeleton_without_deploy(self) -> None:
        skeleton = self.contract["offline_spfx_skeleton"]

        self.assertEqual(
            skeleton["artifact"],
            "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
        )
        self.assertEqual(skeleton["package_root"], "spfx/nac-bpmn-viewer")
        self.assertEqual(skeleton["command"], "nac m365 teams-sharepoint spfx-bpmn-viewer-skeleton --format json")
        self.assertEqual(skeleton["status"], "offline_skeleton_no_package_deploy")
        self.assertTrue(skeleton["source_skeleton_included_now"])
        self.assertFalse(skeleton["actual_spfx_package_included_now"])
        self.assertFalse(skeleton["package_solution_enabled_now"])
        self.assertFalse(skeleton["app_catalog_deploy_allowed_now"])
        self.assertFalse(skeleton["tenant_apply_allowed_now"])
        self.assertFalse(skeleton["executes_graph_requests_now"])

    def test_contract_keeps_bpmn_mcp_tools_planning_only(self) -> None:
        mcp = self.contract["mcp_boundary"]

        self.assertEqual(
            set(mcp["request_plan_tools_enabled_now"]),
            {"bpmn_model_get", "process_register_list", "bpmn_viewer_overlay_get"},
        )
        self.assertEqual(set(mcp["owner_gated_live_read_tools_enabled_now"]), {"case_get", "document_list"})
        self.assertTrue(mcp["tools_read_only"])
        self.assertTrue(mcp["tools_must_not_return_matter_document_content"])

    def test_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
