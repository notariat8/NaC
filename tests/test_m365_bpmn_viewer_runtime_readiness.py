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

from nac_m365_graph.spfx_bpmn_viewer_runtime_readiness import (  # noqa: E402
    DEFAULT_BPMN_VIEWER_RUNTIME_READINESS,
    build_bpmn_viewer_runtime_readiness_result,
    load_bpmn_viewer_runtime_readiness,
    validate_bpmn_viewer_runtime_readiness,
)


SPFX_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer"


class M365BpmnViewerRuntimeReadinessTests(unittest.TestCase):
    def test_runtime_readiness_artifact_validates_offline_guardrails(self) -> None:
        readiness = load_bpmn_viewer_runtime_readiness(DEFAULT_BPMN_VIEWER_RUNTIME_READINESS)

        self.assertEqual(validate_bpmn_viewer_runtime_readiness(readiness), [])
        self.assertEqual(readiness["status"], "offline_runtime_readiness_no_live_deploy")
        self.assertFalse(readiness["spfx_packaging_boundary"]["npm_install_allowed_now"])
        self.assertFalse(readiness["spfx_packaging_boundary"]["package_solution_allowed_now"])
        self.assertFalse(readiness["app_catalog_deploy_gate"]["app_catalog_upload_allowed_now"])
        self.assertFalse(readiness["graph_bpmn_content_read_gate"]["live_content_read_enabled_now"])
        self.assertTrue(readiness["app_catalog_deploy_gate"]["requires_owner_gate"])
        self.assertIn(
            "NacDataClass in Template,Demo,Reference",
            readiness["graph_bpmn_content_read_gate"]["required_metadata_gates"],
        )

    def test_runtime_readiness_result_is_passed_but_not_deployable(self) -> None:
        result = build_bpmn_viewer_runtime_readiness_result(load_bpmn_viewer_runtime_readiness())

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["readiness_gate_count"], 3)
        self.assertFalse(result["summary"]["live_deploy_allowed_now"])
        self.assertFalse(result["summary"]["live_content_read_enabled_now"])
        self.assertFalse(result["summary"]["app_catalog_upload_allowed_now"])
        self.assertEqual(
            {gate["id"] for gate in result["readinessGates"]},
            {
                "spfx_packaging_boundary",
                "app_catalog_deploy_gate",
                "graph_bpmn_content_read_gate",
            },
        )
        for gate in result["readinessGates"]:
            self.assertEqual(gate["status"], "BLOCKED_UNTIL_OWNER_GATE")
            self.assertFalse(gate["allowed_now"])
        self.assertTrue(result["guardrails"]["graph_rest_only"])
        self.assertFalse(result["guardrails"]["graph_sdk_allowed"])
        self.assertFalse(result["guardrails"]["workflow_execution_allowed"])

    def test_spfx_runtime_readiness_keeps_source_tree_package_free(self) -> None:
        for blocked in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "node_modules", "sharepoint/solution"):
            self.assertFalse((SPFX_ROOT / blocked).exists(), blocked)
        self.assertEqual(list(SPFX_ROOT.rglob("*.sppkg")), [])

        package = json.loads((SPFX_ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(set(package["scripts"]), {"validate:skeleton"})
        for flag in (
            "npmInstallRequiredNow",
            "buildRequiredNow",
            "appCatalogDeployAllowedNow",
            "tenantApplyAllowedNow",
            "executesGraphRequestsNow",
        ):
            self.assertFalse(package["nacSkeleton"][flag])

        package_solution = json.loads((SPFX_ROOT / "config" / "package-solution.json").read_text(encoding="utf-8"))
        self.assertFalse(package_solution["nacGuardrails"]["packageSolutionEnabledNow"])
        self.assertFalse(package_solution["nacGuardrails"]["appCatalogDeployAllowedNow"])
        self.assertFalse(package_solution["nacGuardrails"]["tenantApplyAllowedNow"])
        self.assertNotIn("webApiPermissionRequests", package_solution["solution"])

    def test_central_cli_exposes_bpmn_viewer_runtime_readiness(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "bpmn-viewer-runtime-readiness",
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
        self.assertFalse(payload["guardrails"]["app_catalog_upload_allowed_now"])
        self.assertFalse(payload["guardrails"]["live_content_read_enabled_now"])
        self.assertFalse(payload["guardrails"]["package_solution_allowed_now"])


if __name__ == "__main__":
    unittest.main()
