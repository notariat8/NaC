from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.spfx_bpmn_viewer_skeleton import (  # noqa: E402
    APPROVED_WORKSPACE_ID,
    DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE,
    DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
    REQUIRED_DOM_MARKERS,
    SPFX_GENERATED_PATHS,
    _iter_spfx_source_files,
    build_spfx_bpmn_viewer_skeleton_result,
    evaluate_spfx_bpmn_viewer_process_selection,
    load_spfx_bpmn_viewer_render_fixture,
    load_spfx_bpmn_viewer_skeleton,
    validate_spfx_bpmn_viewer_skeleton,
)


SPFX_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer"


class M365SpfxBpmnViewerSkeletonTests(unittest.TestCase):
    def test_package_contract_validates_site_scoped_bff_read_mode(self) -> None:
        skeleton = load_spfx_bpmn_viewer_skeleton(DEFAULT_SPFX_BPMN_VIEWER_SKELETON)
        fixture = load_spfx_bpmn_viewer_render_fixture(DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE)

        self.assertEqual(validate_spfx_bpmn_viewer_skeleton(skeleton, render_fixture=fixture), [])
        self.assertEqual(skeleton["schema_version"], "nac.m365-spfx-bpmn-viewer-skeleton/v0.3")
        self.assertEqual(skeleton["status"], "bff_read_site_scoped_package")
        self.assertEqual(skeleton["spfx"]["framework_version"], "1.23.2")
        self.assertEqual(skeleton["spfx"]["build_tool"], "Heft")
        self.assertEqual(skeleton["spfx"]["approved_workspace_id"], APPROVED_WORKSPACE_ID)
        self.assertTrue(skeleton["spfx"]["package_lock_required"])
        self.assertTrue(skeleton["spfx"]["package_solution_enabled_now"])
        self.assertTrue(skeleton["spfx"]["site_scoped_package"])
        self.assertTrue(skeleton["spfx"]["app_catalog_deploy_owner_approved"])
        self.assertFalse(skeleton["spfx"]["tenant_wide_deploy_allowed_now"])
        self.assertFalse(skeleton["spfx"]["graph_permissions_requested"])
        self.assertFalse(skeleton["spfx"]["direct_graph_access_allowed"])
        self.assertTrue(skeleton["spfx"]["aad_http_client_allowed"])
        self.assertTrue(skeleton["spfx"]["bpmn_asset_sha256_verified_in_browser"])
        self.assertTrue(skeleton["spfx"]["bff_dto_exact_shape_required"])
        self.assertEqual(
            skeleton["package_contract"]["bff_client_test"],
            "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.test.ts",
        )
        self.assertEqual(
            skeleton["package_contract"]["component_runtime_test"],
            "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacBpmnViewer.test.tsx",
        )
        self.assertEqual(skeleton["spfx"]["delegated_api_resource"], "api://funktion8.de/nac-bff")
        self.assertEqual(skeleton["spfx"]["delegated_api_scope"], "Matter.Read")
        self.assertFalse(skeleton["spfx"]["sharepoint_writes_allowed"])
        self.assertFalse(skeleton["spfx"]["contains_real_matter_data"])

    def test_package_sources_are_pinned_and_graph_free(self) -> None:
        package = json.loads((SPFX_ROOT / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((SPFX_ROOT / "package-lock.json").read_text(encoding="utf-8"))
        solution = json.loads((SPFX_ROOT / "config/package-solution.json").read_text(encoding="utf-8"))
        generator_config = json.loads((SPFX_ROOT / ".yo-rc.json").read_text(encoding="utf-8"))[
            "@microsoft/generator-sharepoint"
        ]
        manifest = json.loads(
            (SPFX_ROOT / "src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.manifest.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(lock["lockfileVersion"], 3)
        self.assertEqual(lock["packages"][""]["dependencies"], package["dependencies"])
        self.assertEqual(lock["packages"][""]["devDependencies"], package["devDependencies"])
        self.assertIn("heft test --clean --production", package["scripts"]["build"])
        self.assertIn("heft package-solution --production", package["scripts"]["build"])
        all_dependencies = {**package["dependencies"], **package["devDependencies"]}
        spfx_versions = {
            version for name, version in all_dependencies.items() if name.startswith("@microsoft/sp")
        }
        self.assertEqual(spfx_versions, {"1.23.2"})
        self.assertFalse(generator_config["skipFeatureDeployment"])
        self.assertEqual(
            generator_config["solutionShortDescription"],
            "Synthetic read-only NaC workspace for Teams and SharePoint",
        )
        self.assertFalse(solution["solution"]["skipFeatureDeployment"])
        self.assertEqual(
            solution["solution"]["webApiPermissionRequests"],
            [{"resource": "NaC M365 BFF", "scope": "Matter.Read"}],
        )
        self.assertIn("SharePointWebPart", manifest["supportedHosts"])
        self.assertIn("TeamsTab", manifest["supportedHosts"])

        scanned = {path.relative_to(SPFX_ROOT).as_posix() for path in _iter_spfx_source_files(SPFX_ROOT)}
        for generated in SPFX_GENERATED_PATHS:
            self.assertFalse(any(path == generated or path.startswith(f"{generated}/") for path in scanned))

    def test_current_ui_uses_only_the_delegated_bff_and_hash_bound_bpmn(self) -> None:
        component = (
            SPFX_ROOT / "src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx"
        ).read_text(encoding="utf-8")
        webpart = (
            SPFX_ROOT / "src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts"
        ).read_text(encoding="utf-8")
        fixture = (
            SPFX_ROOT / "src/webparts/nacBpmnViewer/fixtures/syntheticWorkspace.ts"
        ).read_text(encoding="utf-8")
        bff_client = (
            SPFX_ROOT / "src/webparts/nacBpmnViewer/services/NacBffClient.ts"
        ).read_text(encoding="utf-8")
        bff_client_test = (
            SPFX_ROOT / "src/webparts/nacBpmnViewer/services/NacBffClient.test.ts"
        ).read_text(encoding="utf-8")
        component_test = (
            SPFX_ROOT / "src/webparts/nacBpmnViewer/components/NacBpmnViewer.test.tsx"
        ).read_text(encoding="utf-8")

        for marker in REQUIRED_DOM_MARKERS.values():
            self.assertIn(marker, component)
        self.assertIn("Workspace nicht freigegeben.", component)
        self.assertIn("Vorgangsdaten sind derzeit nicht verfügbar.", component)
        self.assertIn("loadNacBffWorkspace(this.context.aadHttpClientFactory, signal)", webpart)
        self.assertIn("source: 'package_bpmn_fixture'", fixture)
        self.assertIn("containsMatterData: false", fixture)
        self.assertIn("bpmnXml: sampleApprovedBpmnXml", fixture)
        self.assertNotIn("NAC-SYN-TASK-001", fixture)
        self.assertNotIn("deadlineLabel", fixture)

        self.assertIn("AadHttpClientFactory", bff_client)
        self.assertIn("api://funktion8.de/nac-bff", bff_client)
        self.assertIn("Matter.Read", bff_client)
        self.assertIn("func-nac-bff-test-funktion8.azurewebsites.net", bff_client)
        self.assertIn("MAX_RESPONSE_BYTES", bff_client)
        self.assertIn("isWorkspace", bff_client)
        self.assertIn("hasExactKeys", bff_client)
        self.assertIn("verifyBpmnAsset", bff_client)
        self.assertIn("crypto.subtle.digest", bff_client)
        self.assertIn("verifyBpmnAsset", component)
        self.assertIn("rejects extra %s fields", bff_client_test)
        self.assertIn("cryptographically binds packaged BPMN XML", bff_client_test)
        self.assertIn("fails closed and destroys the viewer when BPMN import fails", component_test)
        self.assertIn("aborts an outstanding BFF request when the component unmounts", component_test)

        combined = "\n".join(path.read_text(encoding="utf-8") for path in _iter_spfx_source_files(SPFX_ROOT))
        self.assertIn("AadHttpClient", combined)
        for marker in (
            "MSGraphClient",
            "graph.microsoft.com",
            "@microsoft/microsoft-graph-client",
            "bpmn-js/lib/Modeler",
            "saveXML",
        ):
            self.assertNotIn(marker, combined)

    def test_contract_rejects_tenant_wide_or_graph_enabled_variants(self) -> None:
        skeleton = load_spfx_bpmn_viewer_skeleton()
        invalid = copy.deepcopy(skeleton)
        invalid["deployment_scope"]["tenant_wide"] = True
        invalid["spfx"]["graph_permissions_requested"] = True
        invalid["render_contract"]["writes_allowed"] = True

        errors = validate_spfx_bpmn_viewer_skeleton(invalid)

        self.assertTrue(any("tenant-wide" in error for error in errors))
        self.assertTrue(any("graph_permissions_requested" in error for error in errors))
        self.assertTrue(any("writes_allowed" in error for error in errors))

    def test_package_result_exposes_one_delegated_bff_request_plan(self) -> None:
        result = build_spfx_bpmn_viewer_skeleton_result(load_spfx_bpmn_viewer_skeleton())

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["approved_workspace_id"], APPROVED_WORKSPACE_ID)
        self.assertEqual(result["summary"]["request_plan_count"], 1)
        self.assertTrue(result["summary"]["package_solution_enabled_now"])
        self.assertTrue(result["summary"]["app_catalog_deploy_owner_approved"])
        self.assertTrue(result["summary"]["site_scoped_install_allowed_now"])
        self.assertFalse(result["summary"]["tenant_wide_deploy_allowed_now"])
        self.assertFalse(result["summary"]["executes_graph_requests_now"])
        self.assertEqual(len(result["requestPlans"]), 1)
        self.assertEqual(result["requestPlans"][0]["resource"], "api://funktion8.de/nac-bff")
        self.assertEqual(result["requestPlans"][0]["scope"], "Matter.Read")
        self.assertEqual(result["renderContract"]["domMarkers"], REQUIRED_DOM_MARKERS)
        self.assertFalse(result["guardrails"]["graph_permissions_requested"])
        self.assertTrue(result["guardrails"]["aad_http_client_allowed"])
        self.assertFalse(result["guardrails"]["sharepoint_writes_allowed"])

    def test_fixture_process_selection_remains_local_and_read_only(self) -> None:
        fixture = load_spfx_bpmn_viewer_render_fixture()
        result = evaluate_spfx_bpmn_viewer_process_selection(
            fixture["process_register_rows"],
            fixture["bpmn_models"],
            workspace_id=fixture["workspace_id"],
            process_id=fixture["component_props"]["processId"],
            bpmn_model_id=fixture["component_props"]["bpmnModelId"],
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertFalse(result["summary"]["executesGraphRequestsNow"])
        self.assertFalse(result["summary"]["readsSharePointFileContentNow"])
        self.assertFalse(result["guardrails"]["writesBpmnXml"])
        self.assertFalse(result["guardrails"]["startsWorkflow"])

    def test_central_cli_exposes_package_contract(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "spfx-bpmn-viewer-skeleton",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["spfx_version"], "1.23.2")
        self.assertEqual(payload["summary"]["request_plan_count"], 1)
        self.assertTrue(payload["guardrails"]["package_lock_required"])
        self.assertTrue(payload["guardrails"]["app_catalog_deploy_owner_approved"])
        self.assertFalse(payload["guardrails"]["tenant_wide_deploy_allowed_now"])
        self.assertFalse(payload["guardrails"]["executes_graph_requests_now"])
        self.assertTrue(payload["guardrails"]["aad_http_client_allowed"])


if __name__ == "__main__":
    unittest.main()
