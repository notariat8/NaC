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

from nac_m365_graph.spfx_bpmn_viewer_runtime_readiness import (  # noqa: E402
    DEFAULT_BPMN_VIEWER_RUNTIME_READINESS,
    build_bpmn_viewer_runtime_readiness_result,
    load_bpmn_viewer_runtime_readiness,
    validate_bpmn_viewer_runtime_readiness,
)


SPFX_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer"


class M365BpmnViewerRuntimeReadinessTests(unittest.TestCase):
    def test_runtime_readiness_validates_package_and_site_scope(self) -> None:
        readiness = load_bpmn_viewer_runtime_readiness(DEFAULT_BPMN_VIEWER_RUNTIME_READINESS)

        self.assertEqual(validate_bpmn_viewer_runtime_readiness(readiness), [])
        self.assertEqual(readiness["status"], "bff_read_site_scoped_runtime_ready")
        packaging = readiness["spfx_packaging_boundary"]
        self.assertTrue(packaging["package_lock_required"])
        self.assertTrue(packaging["npm_ci_allowed_now"])
        self.assertTrue(packaging["build_allowed_now"])
        self.assertTrue(packaging["package_solution_allowed_now"])
        self.assertTrue(packaging["generated_outputs_excluded_from_source_scans"])
        self.assertEqual(packaging["reproducible_commands"], ["npm ci", "npm run build"])

        deployment = readiness["app_catalog_deployment"]
        self.assertEqual(deployment["approval"], "owner_approved")
        self.assertEqual(deployment["approved_workspace_id"], "notary_team_01")
        self.assertTrue(deployment["site_scoped"])
        self.assertFalse(deployment["tenant_wide"])

    def test_runtime_result_allows_only_bff_read_and_blocks_graph_and_writes(self) -> None:
        result = build_bpmn_viewer_runtime_readiness_result(load_bpmn_viewer_runtime_readiness())

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["readiness_gate_count"], 3)
        self.assertTrue(result["summary"]["package_build_allowed_now"])
        self.assertTrue(result["summary"]["package_solution_allowed_now"])
        self.assertTrue(result["summary"]["app_catalog_deploy_owner_approved"])
        self.assertTrue(result["summary"]["site_scoped_install_allowed_now"])
        self.assertFalse(result["summary"]["tenant_wide_deploy_allowed_now"])
        self.assertFalse(result["summary"]["graph_access_allowed"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in result["readinessGates"]},
            {
                "spfx_packaging_boundary": "READY",
                "app_catalog_deployment": "OWNER_APPROVED",
                "synthetic_data_boundary": "ENFORCED",
            },
        )
        guardrails = result["guardrails"]
        self.assertFalse(guardrails["graph_permissions_requested"])
        self.assertFalse(guardrails["direct_graph_access_allowed"])
        self.assertFalse(guardrails["ms_graph_client_allowed"])
        self.assertTrue(guardrails["aad_http_client_allowed"])
        self.assertEqual(guardrails["delegated_api_resource"], "api://funktion8.de/nac-bff")
        self.assertEqual(guardrails["delegated_scope"], "Matter.Read")
        self.assertFalse(guardrails["legacy_sharepoint_api_allowed"])
        self.assertFalse(guardrails["sharepoint_writes_allowed"])
        self.assertFalse(guardrails["workflow_execution_allowed"])
        self.assertFalse(guardrails["real_matter_data_allowed"])

    def test_runtime_rejects_broader_deployment_or_network_data_mode(self) -> None:
        readiness = load_bpmn_viewer_runtime_readiness()
        invalid = copy.deepcopy(readiness)
        invalid["app_catalog_deployment"]["tenant_wide"] = True
        invalid["synthetic_data_boundary"]["graph_access_allowed"] = True
        invalid["synthetic_data_boundary"]["writes_allowed"] = True

        errors = validate_bpmn_viewer_runtime_readiness(invalid)

        self.assertTrue(any("tenant_wide" in error for error in errors))
        self.assertTrue(any("graph_access_allowed" in error for error in errors))
        self.assertTrue(any("writes_allowed" in error for error in errors))

    def test_package_lock_and_site_scoped_solution_are_present(self) -> None:
        self.assertTrue((SPFX_ROOT / "package-lock.json").is_file())
        package = json.loads((SPFX_ROOT / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((SPFX_ROOT / "package-lock.json").read_text(encoding="utf-8"))
        solution = json.loads((SPFX_ROOT / "config/package-solution.json").read_text(encoding="utf-8"))

        self.assertEqual(lock["packages"][""]["name"], package["name"])
        self.assertEqual(lock["packages"][""]["version"], package["version"])
        self.assertFalse(solution["solution"]["skipFeatureDeployment"])
        self.assertEqual(
            solution["solution"]["webApiPermissionRequests"],
            [{"resource": "NaC M365 BFF", "scope": "Matter.Read"}],
        )

        tracked = subprocess.run(
            ["git", "ls-files", "--", "spfx/nac-bpmn-viewer"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        for generated in ("node_modules", "lib", "dist", "temp", "sharepoint/solution"):
            prefix = f"spfx/nac-bpmn-viewer/{generated}"
            self.assertFalse(any(path == prefix or path.startswith(f"{prefix}/") for path in tracked))

    def test_central_cli_exposes_runtime_readiness(self) -> None:
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
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(payload["guardrails"]["package_solution_allowed_now"])
        self.assertTrue(payload["guardrails"]["app_catalog_deploy_owner_approved"])
        self.assertTrue(payload["guardrails"]["site_scoped_install_allowed_now"])
        self.assertFalse(payload["guardrails"]["tenant_wide_deploy_allowed_now"])
        self.assertFalse(payload["guardrails"]["direct_graph_access_allowed"])


if __name__ == "__main__":
    unittest.main()
