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
