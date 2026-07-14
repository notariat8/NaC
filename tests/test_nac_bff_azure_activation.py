from __future__ import annotations

import json
import os
import socket
import tempfile
import unittest
import urllib.request
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from nac_bff.azure_activation import (
    API_APP_URI,
    API_CLIENT_ID_BINDING,
    DELEGATED_SCOPE,
    FUNCTION_APP,
    MATTER_ID,
    SITE_ID,
    SUBSCRIPTION_ID,
    TENANT_ID,
    WORKSPACE_ID,
    _activation_contract_valid,
    _spfx_source_manifest_binding,
    build_azure_bff_activation_plan,
)
from nac_cli.cli import main as nac_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class AzureBffActivationPlanTests(unittest.TestCase):
    def test_current_repository_produces_hash_bound_ready_plan(self) -> None:
        first = build_azure_bff_activation_plan(REPO_ROOT)
        second = build_azure_bff_activation_plan(REPO_ROOT)

        self.assertEqual(first["status"], "READY")
        self.assertEqual(first["activation_hash"], second["activation_hash"])
        self.assertRegex(first["activation_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["bindings"]["subscription_id"], SUBSCRIPTION_ID)
        self.assertEqual(first["bindings"]["tenant_id"], TENANT_ID)
        self.assertEqual(first["bindings"]["workspace_id"], WORKSPACE_ID)
        self.assertEqual(first["bindings"]["matter_id"], MATTER_ID)
        self.assertEqual(first["bindings"]["site_id"], SITE_ID)
        self.assertEqual(first["bindings"]["function_app"], FUNCTION_APP)
        self.assertEqual(first["bindings"]["api_app_uri"], API_APP_URI)
        self.assertEqual(
            first["bindings"]["api_client_id_binding"],
            API_CLIENT_ID_BINDING,
        )
        self.assertTrue(
            first["bindings"]["api_client_id_binding"]["bind_before_azure_deploy"]
        )
        self.assertEqual(first["bindings"]["delegated_scope"], DELEGATED_SCOPE)
        self.assertEqual(len(first["steps"]), 12)
        self.assertTrue(first["gate_results"]["activation_contract_valid"])
        bindings = {
            binding["path"]: binding for binding in first["artifact_bindings"]
        }
        self.assertIn("generated:nac-bff-function.zip", bindings)
        self.assertIn("generated:spfx-source-manifest", bindings)
        spfx_manifest = bindings["generated:spfx-source-manifest"]
        self.assertGreater(spfx_manifest["file_count"], 10)
        spfx_paths = {entry["path"] for entry in spfx_manifest["entries"]}
        self.assertIn(
            "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/fixtures/sampleBpmn.ts",
            spfx_paths,
        )
        self.assertIn(
            "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.test.ts",
            spfx_paths,
        )
        self.assertIn(
            "entra_api_client_id_binding_redacted",
            first["required_evidence"],
        )
        self.assertIn(
            "spfx_source_manifest_and_package_sha256_redacted",
            first["required_evidence"],
        )
        self.assertTrue(all(step["stop_on_error"] for step in first["steps"]))
        self.assertEqual(first["boundaries"]["live_actions_executed"], 0)
        self.assertFalse(first["boundaries"]["production_data_allowed"])
        self.assertFalse(first["boundaries"]["other_workspaces_allowed"])
        self.assertFalse(first["boundaries"]["credential_changes_allowed"])

    def test_spfx_source_manifest_changes_only_for_package_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "spfx/nac-bpmn-viewer"
            source = package / "src/client.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export const value = 1;\n", encoding="utf-8")
            (package / "package.json").write_text("{}\n", encoding="utf-8")
            generated = package / "node_modules/dependency/index.js"
            generated.parent.mkdir(parents=True)
            generated.write_text("ignored-v1\n", encoding="utf-8")

            first, first_error = _spfx_source_manifest_binding(root)
            generated.write_text("ignored-v2\n", encoding="utf-8")
            generated_change, generated_error = _spfx_source_manifest_binding(root)
            source.write_text("export const value = 2;\n", encoding="utf-8")
            source_change, source_error = _spfx_source_manifest_binding(root)

        self.assertIsNone(first_error)
        self.assertIsNone(generated_error)
        self.assertIsNone(source_error)
        self.assertIsNotNone(first)
        self.assertIsNotNone(generated_change)
        self.assertIsNotNone(source_change)
        assert first is not None
        assert generated_change is not None
        assert source_change is not None
        self.assertEqual(first["sha256"], generated_change["sha256"])
        self.assertNotEqual(first["sha256"], source_change["sha256"])
        self.assertEqual(
            {entry["path"] for entry in first["entries"]},
            {
                "spfx/nac-bpmn-viewer/package.json",
                "spfx/nac-bpmn-viewer/src/client.ts",
            },
        )

    def test_activation_contract_rejects_wrong_site_or_client_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = (
                root
                / "workflows/contracts/m365-azure-bff-activation-plan.contract.json"
            )
            target.parent.mkdir(parents=True)
            contract = json.loads(
                (
                    REPO_ROOT
                    / "workflows/contracts/m365-azure-bff-activation-plan.contract.json"
                ).read_text(encoding="utf-8")
            )
            target.write_text(json.dumps(contract), encoding="utf-8")
            self.assertTrue(_activation_contract_valid(root))

            contract["bindings"]["site_id"] = "different-site"
            target.write_text(json.dumps(contract), encoding="utf-8")
            self.assertFalse(_activation_contract_valid(root))

            contract["bindings"]["site_id"] = SITE_ID
            del contract["bindings"]["api_client_id_binding"]["must_be_uuid"]
            target.write_text(json.dumps(contract), encoding="utf-8")
            self.assertFalse(_activation_contract_valid(root))

    def test_plan_builder_does_not_access_environment_network_or_subprocess(self) -> None:
        secret = "must-not-appear"
        with (
            patch.dict(os.environ, {"AZURE_CLIENT_SECRET": secret}),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS access")),
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("HTTP access")),
            patch("subprocess.run", side_effect=AssertionError("subprocess access")),
        ):
            plan = build_azure_bff_activation_plan(REPO_ROOT)

        self.assertEqual(plan["status"], "READY")
        self.assertNotIn(secret, json.dumps(plan))

    def test_cli_emits_ready_json_plan(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            return_code = nac_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "bff-azure-activation-plan",
                    "--format",
                    "json",
                ]
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["bindings"]["workspace_id"], WORKSPACE_ID)


if __name__ == "__main__":
    unittest.main()
