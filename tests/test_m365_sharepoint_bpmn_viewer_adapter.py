from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from scripts.validate_m365_sharepoint_bpmn_viewer_adapter import _validate_contract


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "m365-sharepoint-bpmn-viewer-adapter.contract.json"


class M365SharePointBpmnViewerAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_defines_packageable_viewer_only_spfx(self) -> None:
        self.assertEqual(self.contract["schema_version"], "nac.m365-sharepoint-bpmn-viewer-adapter/v0.4")
        self.assertEqual(self.contract["status"], "bff_read_site_scoped_package_ready_activation_deferred")
        spfx = self.contract["spfx_surface"]
        self.assertEqual(spfx["delivery"], "SharePoint Framework Web Part")
        self.assertEqual(spfx["framework_version"], "1.23.2")
        self.assertEqual(spfx["build_tool"], "Heft")
        self.assertEqual(spfx["library"], "bpmn-js")
        self.assertEqual(spfx["bpmn_js_mode"], "viewer_only")
        self.assertTrue(spfx["package_lock_required"])
        self.assertTrue(spfx["reproducible_build_required"])
        self.assertTrue(spfx["package_solution_enabled_now"])
        self.assertTrue(spfx["site_scoped"])
        self.assertFalse(spfx["tenant_wide"])
        self.assertFalse(spfx["modeler_enabled"])
        self.assertFalse(spfx["workflow_execution_allowed"])
        self.assertFalse(spfx["writes_sharepoint_or_bpmn"])
        self.assertIn("TeamsTab", spfx["supported_hosts"])

    def test_deployment_is_owner_approved_only_for_notary_team_01(self) -> None:
        deployment = self.contract["deployment_scope"]
        self.assertEqual(deployment["approval"], "deferred_until_bff_activation")
        self.assertTrue(deployment["activation_gate_required"])
        self.assertEqual(deployment["approved_workspace_ids"], ["notary_team_01"])
        self.assertFalse(deployment["app_catalog_upload_allowed_now"])
        self.assertFalse(deployment["site_scoped_install_allowed_now"])
        self.assertFalse(deployment["tenant_wide_deploy_allowed_now"])
        self.assertFalse(deployment["other_workspace_deploy_allowed_now"])

        invalid = copy.deepcopy(self.contract)
        invalid["deployment_scope"]["approved_workspace_ids"].append("other_workspace")
        errors = _validate_contract(invalid, {}, {}, {}, {})
        self.assertIn(
            "deployment_scope.approved_workspace_ids must contain only notary_team_01",
            errors,
        )

    def test_packaging_requires_lockfile_and_excludes_generated_trees(self) -> None:
        packaging = self.contract["packaging_contract"]
        self.assertEqual(packaging["package_lock"], "spfx/nac-bpmn-viewer/package-lock.json")
        self.assertEqual(packaging["install_command"], "npm ci")
        self.assertEqual(packaging["build_command"], "npm run build")
        self.assertEqual(packaging["package_output"], "sharepoint/solution/nac-bpmn-viewer.sppkg")
        self.assertEqual(
            set(packaging["generated_paths_ignored_untracked"]),
            {
                "node_modules",
                "lib",
                "lib-commonjs",
                "dist",
                "temp",
                "sharepoint/solution",
                "release",
                "jest-output",
            },
        )
        self.assertTrue(packaging["generated_paths_excluded_from_recursive_source_scans"])
        self.assertTrue(packaging["bpmn_asset_sha256_verified_in_browser"])
        self.assertTrue(packaging["bff_dto_exact_shape_required"])
        self.assertEqual(
            packaging["bff_client_test"],
            "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.test.ts",
        )
        self.assertEqual(
            packaging["component_runtime_test"],
            "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacBpmnViewer.test.tsx",
        )

    def test_contract_allows_only_the_delegated_bff_permission_path(self) -> None:
        boundary = self.contract["graph_free_boundary"]
        self.assertFalse(boundary["graph_permissions_requested"])
        self.assertFalse(boundary["direct_graph_access_allowed"])
        self.assertFalse(boundary["ms_graph_client_allowed"])
        self.assertFalse(boundary["graph_sdk_allowed"])
        self.assertTrue(boundary["aad_http_client_allowed"])
        self.assertTrue(boundary["web_api_permission_requests_allowed"])
        self.assertEqual(boundary["delegated_api_resource"], "api://funktion8.de/nac-bff")
        self.assertEqual(boundary["delegated_scope"], "Matter.Read")

        invalid = copy.deepcopy(self.contract)
        invalid["graph_free_boundary"]["delegated_scope"] = "Matter.Write"
        errors = _validate_contract(invalid, {}, {}, {}, {})
        self.assertIn("graph_free_boundary.delegated_scope must be Matter.Read", errors)

    def test_contract_uses_bff_redacted_synthetic_data_and_package_bpmn(self) -> None:
        synthetic = self.contract["synthetic_data_boundary"]
        self.assertEqual(synthetic["workspace_id"], "notary_team_01")
        self.assertEqual(synthetic["source"], "nac_bff_redacted_dto")
        self.assertFalse(synthetic["browser_reads_sharepoint_content"])
        self.assertTrue(synthetic["bff_reads_sharepoint_metadata"])
        self.assertTrue(synthetic["synthetic_data_only"])
        self.assertFalse(synthetic["contains_real_matter_data"])
        self.assertFalse(synthetic["reads_sharepoint_content"])
        self.assertFalse(synthetic["reads_matter_document_content"])
        self.assertFalse(synthetic["writes_allowed"])

        render = self.contract["package_render_contract"]
        self.assertEqual(render["request_plan_count"], 1)
        self.assertTrue(render["viewer_only"])
        self.assertFalse(render["liveTenantAccess"])
        self.assertEqual(
            render["dom_markers"],
            {
                "component": 'data-nac-component="test-workspace"',
                "synthetic_data": "Synthetische Testdaten",
                "no_matter_data": "Keine Mandatsdaten",
            },
        )
        self.assertTrue(all(value is False for value in render["privacy_guards"].values()))

    def test_blocked_operations_cover_writes_real_data_and_network_clients(self) -> None:
        blocked = set(self.contract["blocked_operations"])
        for operation in {
            "tenant_wide_deploy",
            "deploy_other_workspace",
            "microsoft_graph_permission_request",
            "direct_graph_request",
            "ms_graph_client",
            "aad_http_client_non_bff_resource",
            "additional_delegated_scope",
            "graph_sdk",
            "legacy_sharepoint_api",
            "pnp",
            "write_bpmn_xml",
            "execute_workflow",
            "write_sharepoint_data",
            "read_matter_document_content",
            "store_real_matter_data",
        }:
            self.assertIn(operation, blocked)

    def test_runtime_readiness_matches_package_mode(self) -> None:
        readiness = self.contract["runtime_readiness"]
        self.assertEqual(readiness["status"], "bff_read_site_scoped_package_ready_activation_deferred")
        self.assertEqual(
            readiness["redacted_artifact_kind"],
            "redacted_bff_read_site_scoped_readiness_json",
        )
        self.assertTrue(readiness["spfx_package_allowed_now"])
        self.assertFalse(readiness["app_catalog_upload_allowed_now"])
        self.assertFalse(readiness["site_scoped_install_allowed_now"])
        self.assertFalse(readiness["tenant_wide_deploy_allowed_now"])
        self.assertFalse(readiness["graph_access_allowed"])
        self.assertTrue(readiness["aad_http_client_allowed"])
        self.assertEqual(readiness["delegated_scope"], "Matter.Read")
        self.assertFalse(readiness["writes_allowed"])

    def test_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
