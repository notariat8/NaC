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

from nac_m365_graph.mcp_runtime import load_mcp_contract  # noqa: E402
from nac_m365_graph.spfx_bpmn_viewer_skeleton import (  # noqa: E402
    DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE,
    DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
    build_spfx_bpmn_viewer_skeleton_result,
    evaluate_spfx_bpmn_viewer_render_case,
    load_spfx_bpmn_viewer_render_fixture,
    load_spfx_bpmn_viewer_skeleton,
    validate_spfx_bpmn_viewer_skeleton,
)


SPFX_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer"
REQUIRED_RENDER_STATES = {
    "approved_renderable",
    "approval_missing_or_review_required",
    "viewer_disabled",
    "contains_matter_data",
    "invalid_mime_or_hash_missing",
}
REQUIRED_DOM_MARKERS = {
    "data-nac-render-state",
    "data-nac-content-source",
    "data-nac-metadata-overlay",
}


class M365SpfxBpmnViewerSkeletonTests(unittest.TestCase):
    def test_skeleton_validates_source_only_guardrails(self) -> None:
        skeleton = load_spfx_bpmn_viewer_skeleton(DEFAULT_SPFX_BPMN_VIEWER_SKELETON)
        fixture = load_spfx_bpmn_viewer_render_fixture(DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE)

        self.assertEqual(
            validate_spfx_bpmn_viewer_skeleton(
                skeleton,
                render_fixture=fixture,
                mcp_contract=load_mcp_contract(),
            ),
            [],
        )
        self.assertTrue(skeleton["spfx"]["source_skeleton_included_now"])
        self.assertFalse(skeleton["spfx"]["actual_spfx_package_included_now"])
        self.assertFalse(skeleton["spfx"]["app_catalog_deploy_allowed_now"])
        self.assertFalse(skeleton["spfx"]["tenant_wide_deploy_allowed_now"])
        self.assertFalse(skeleton["graph_content_read_boundary"]["live_content_read_enabled_now"])
        self.assertIn(
            "NacDataClass in Template,Demo,Reference",
            skeleton["graph_content_read_boundary"]["required_metadata_gates"],
        )
        self.assertEqual(fixture["approved_bpmn_model"]["bpmnContentMode"], "ApprovedCopy")
        self.assertEqual(fixture["approved_bpmn_model"]["bpmnXmlMimeType"], "application/xml")
        self.assertEqual(fixture["render_contract"]["request_plan_count"], 3)
        self.assertFalse(fixture["render_contract"]["liveTenantAccess"])
        self.assertFalse(fixture["render_contract"]["appCatalogDeploy"])
        self.assertEqual(set(fixture["render_contract"]["dom_markers"].values()), REQUIRED_DOM_MARKERS)

    def test_render_fixture_covers_all_offline_states(self) -> None:
        fixture = load_spfx_bpmn_viewer_render_fixture(DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE)
        cases = fixture["render_cases"]

        self.assertEqual({case["name"] for case in cases}, REQUIRED_RENDER_STATES)
        for case in cases:
            decision = evaluate_spfx_bpmn_viewer_render_case(case["bpmn_model"])
            self.assertEqual(decision, case["expected_render_state"])
            self.assertEqual(decision["renderState"], case["name"])
            self.assertFalse(decision["liveTenantAccess"])
            self.assertFalse(decision["appCatalogDeploy"])
            self.assertEqual(decision["metadataOverlay"], "redacted_metadata_only")
        approved = next(case for case in cases if case["name"] == "approved_renderable")
        blocked = [case for case in cases if case["name"] != "approved_renderable"]
        self.assertTrue(approved["expected_render_state"]["renderAllowed"])
        self.assertTrue(all(not case["expected_render_state"]["renderAllowed"] for case in blocked))

    def test_render_fixture_redacted_overlay_contains_no_sensitive_payload(self) -> None:
        fixture = load_spfx_bpmn_viewer_render_fixture(DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE)
        forbidden = (
            "NAC-FIXTURE-CASE",
            "/sites/",
            "/drives/",
            "/lists/",
            "fields/",
            "token",
            "secret",
            "Akteninhalt",
            "Mandatswert",
        )

        for case in fixture["render_cases"]:
            overlay_json = json.dumps(case["redacted_overlay"], sort_keys=True)
            self.assertEqual(case["redacted_overlay"]["case_context"], "redacted")
            self.assertEqual(case["redacted_overlay"]["data_boundary"], "metadata_only")
            for marker in forbidden:
                self.assertNotIn(marker, overlay_json)

    def test_spfx_source_contains_viewer_only_skeleton_without_build_artifacts(self) -> None:
        self.assertTrue((SPFX_ROOT / "package.json").is_file())
        self.assertTrue((SPFX_ROOT / "config" / "package-solution.json").is_file())
        self.assertTrue((SPFX_ROOT / "src" / "webparts" / "nacBpmnViewer" / "NacBpmnViewerWebPart.ts").is_file())
        self.assertTrue(
            (SPFX_ROOT / "src" / "webparts" / "nacBpmnViewer" / "components" / "NacBpmnViewer.tsx").is_file()
        )
        for blocked in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "node_modules", "sharepoint/solution"):
            self.assertFalse((SPFX_ROOT / blocked).exists(), blocked)

        component = (SPFX_ROOT / "src" / "webparts" / "nacBpmnViewer" / "components" / "NacBpmnViewer.tsx").read_text(
            encoding="utf-8"
        )
        self.assertIn("bpmn-js/lib/Viewer", component)
        self.assertNotIn("Model" + "er", component)
        self.assertNotIn("save" + "XML", component)
        for marker in REQUIRED_DOM_MARKERS:
            self.assertIn(marker, component)
        self.assertIn("metadata_only_no_private_payload_or_credentials", component)
        self.assertNotIn("data-case-id", component)

    def test_skeleton_result_returns_mcp_request_plans_without_live_access(self) -> None:
        result = build_spfx_bpmn_viewer_skeleton_result(load_spfx_bpmn_viewer_skeleton())

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["request_plan_count"], 3)
        self.assertFalse(result["summary"]["app_catalog_deploy_allowed_now"])
        self.assertFalse(result["summary"]["live_tenant_apply_allowed_now"])
        self.assertFalse(result["summary"]["live_content_read_enabled_now"])
        self.assertEqual(result["renderContract"]["request_plan_count"], 3)
        self.assertFalse(result["renderContract"]["liveTenantAccess"])
        self.assertFalse(result["renderContract"]["appCatalogDeploy"])
        self.assertEqual(set(result["renderContract"]["domMarkers"].values()), REQUIRED_DOM_MARKERS)
        self.assertEqual({case["name"] for case in result["renderContract"]["cases"]}, REQUIRED_RENDER_STATES)
        self.assertEqual(result["renderContract"]["componentProps"]["caseId"], "redacted")
        self.assertEqual(
            {plan["tool"] for plan in result["requestPlans"]},
            {"bpmn_model_get", "process_register_list", "bpmn_viewer_overlay_get"},
        )
        for plan in result["requestPlans"]:
            self.assertEqual(plan["method"], "GET")
            self.assertIsNone(plan["payload"])
            self.assertFalse(plan["reads_files"])
            self.assertFalse(plan["writes_items"])

    def test_central_cli_exposes_spfx_bpmn_viewer_skeleton(self) -> None:
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
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["request_plan_count"], 3)
        self.assertEqual(payload["renderContract"]["request_plan_count"], 3)
        self.assertFalse(payload["renderContract"]["liveTenantAccess"])
        self.assertFalse(payload["renderContract"]["appCatalogDeploy"])
        self.assertEqual(set(payload["renderContract"]["domMarkers"].values()), REQUIRED_DOM_MARKERS)
        self.assertEqual({case["name"] for case in payload["renderContract"]["cases"]}, REQUIRED_RENDER_STATES)
        self.assertEqual(payload["renderContract"]["componentProps"]["caseId"], "redacted")
        self.assertFalse(payload["guardrails"]["app_catalog_deploy_allowed_now"])
        self.assertFalse(payload["guardrails"]["tenant_wide_deploy_allowed_now"])
        self.assertTrue(payload["guardrails"]["mcp_tools_request_plan_only_now"])


if __name__ == "__main__":
    unittest.main()
