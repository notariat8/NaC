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
    load_spfx_bpmn_viewer_render_fixture,
    load_spfx_bpmn_viewer_skeleton,
    validate_spfx_bpmn_viewer_skeleton,
)


SPFX_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer"


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

    def test_skeleton_result_returns_mcp_request_plans_without_live_access(self) -> None:
        result = build_spfx_bpmn_viewer_skeleton_result(load_spfx_bpmn_viewer_skeleton())

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["request_plan_count"], 3)
        self.assertFalse(result["summary"]["app_catalog_deploy_allowed_now"])
        self.assertFalse(result["summary"]["live_tenant_apply_allowed_now"])
        self.assertFalse(result["summary"]["live_content_read_enabled_now"])
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
        self.assertFalse(payload["guardrails"]["app_catalog_deploy_allowed_now"])
        self.assertFalse(payload["guardrails"]["tenant_wide_deploy_allowed_now"])
        self.assertTrue(payload["guardrails"]["mcp_tools_request_plan_only_now"])


if __name__ == "__main__":
    unittest.main()
