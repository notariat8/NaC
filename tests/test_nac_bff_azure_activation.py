from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
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
    ENTRA_API_CONTRACT,
    FUNCTION_APP,
    MATTER_ID,
    M365_CLI_OWNER_UPN,
    PROVISIONER_CLIENT_ID,
    REQUESTED_ACCESS_TOKEN_VERSION,
    SITE_ID,
    SUBSCRIPTION_ID,
    TENANT_ID,
    WORKSPACE_ID,
    _activation_contract_valid,
    _function_package_binding,
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
        self.assertEqual(
            first["bindings"]["provisioner_client_id"], PROVISIONER_CLIENT_ID
        )
        self.assertEqual(
            first["bindings"]["m365_cli_owner_upn"], M365_CLI_OWNER_UPN
        )
        self.assertEqual(first["bindings"]["entra_api_contract"], ENTRA_API_CONTRACT)
        self.assertEqual(
            first["bindings"]["entra_api_contract"]["requested_access_token_version"],
            REQUESTED_ACCESS_TOKEN_VERSION,
        )
        self.assertTrue(
            first["bindings"]["entra_api_contract"]["readback_required_before_azure_deploy"]
        )
        self.assertEqual(len(first["steps"]), 12)
        self.assertTrue(first["gate_results"]["activation_contract_valid"])
        bindings = {
            binding["path"]: binding for binding in first["artifact_bindings"]
        }
        self.assertIn("generated:nac-bff-function.zip", bindings)
        self.assertIn("generated:spfx-source-manifest", bindings)
        for path in (
            "src/nac_bff/azure_activation_approval.py",
            "src/nac_bff/azure_activation_attestations.py",
            "src/nac_bff/azure_activation_owner_gate.py",
            "src/nac_bff/azure_activation_provisioner_bootstrap.py",
            "src/nac_m365_graph/provisioner_env_bootstrap.py",
        ):
            self.assertIn(path, bindings)
            self.assertRegex(bindings[path]["sha256"], r"^[0-9a-f]{64}$")
        spfx_manifest = bindings["generated:spfx-source-manifest"]
        self.assertEqual(spfx_manifest["source"], "git_tracked_files_only")
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
            "entra_api_contract_readback_redacted",
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

    def test_provisioner_bootstrap_source_drift_changes_activation_hash(
        self,
    ) -> None:
        baseline = build_azure_bff_activation_plan(REPO_ROOT)
        original_read_bytes = Path.read_bytes
        for relative in (
            "src/nac_bff/azure_activation_provisioner_bootstrap.py",
            "src/nac_m365_graph/provisioner_env_bootstrap.py",
        ):
            target = (REPO_ROOT / relative).resolve()

            def drifted_read_bytes(path):
                raw = original_read_bytes(path)
                return raw + b"\n# simulated source drift\n" if path.resolve() == target else raw

            with self.subTest(relative=relative), patch.object(
                Path, "read_bytes", drifted_read_bytes
            ):
                changed = build_azure_bff_activation_plan(REPO_ROOT)
            self.assertNotEqual(
                changed["activation_hash"], baseline["activation_hash"]
            )

    def test_spfx_source_manifest_is_stable_before_and_after_build_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "spfx/nac-bpmn-viewer"
            source = package / "src/client.ts"
            source.parent.mkdir(parents=True)
            source.write_text("export const value = 1;\n", encoding="utf-8")
            (package / "package.json").write_text("{}\n", encoding="utf-8")
            (package / ".gitignore").write_text(
                "node_modules\nlib\nlib-dts\nlib-esm\n.heft\n"
                "coverage\nsharepoint\ntemp\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "add", "spfx/nac-bpmn-viewer"], cwd=root, check=True)

            before, before_error = _spfx_source_manifest_binding(root)
            for relative in (
                "node_modules/dependency/index.js",
                "lib/client.js",
                "lib-dts/client.d.ts",
                "lib-esm/client.js",
                ".heft/build-cache.json",
                "coverage/index.json",
                "sharepoint/solution/nac-bpmn-viewer.sppkg",
                "temp/build.json",
            ):
                generated = package / relative
                generated.parent.mkdir(parents=True, exist_ok=True)
                generated.write_text("generated\n", encoding="utf-8")
            after_build, after_build_error = _spfx_source_manifest_binding(root)
            source.write_text("export const value = 2;\n", encoding="utf-8")
            source_change, source_error = _spfx_source_manifest_binding(root)

        self.assertIsNone(before_error)
        self.assertIsNone(after_build_error)
        self.assertIsNone(source_error)
        assert before is not None
        assert after_build is not None
        assert source_change is not None
        self.assertEqual(before["source"], "git_tracked_files_only")
        self.assertEqual(before["sha256"], after_build["sha256"])
        self.assertNotEqual(before["sha256"], source_change["sha256"])
        self.assertEqual(
            {entry["path"] for entry in before["entries"]},
            {
                "spfx/nac-bpmn-viewer/.gitignore",
                "spfx/nac-bpmn-viewer/package.json",
                "spfx/nac-bpmn-viewer/src/client.ts",
            },
        )

    def test_package_binding_never_executes_manipulated_top_level_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builder = root / "deploy/runtime/azure/nac-bff/build_package.py"
            builder.parent.mkdir(parents=True)
            marker = root / "top-level-code-executed"
            source = (
                (REPO_ROOT / "deploy/runtime/azure/nac-bff/build_package.py")
                .read_text(encoding="utf-8")
                + f"\nPath({str(marker)!r}).write_text('executed')\n"
            )
            builder.write_text(source, encoding="utf-8")
            digest = hashlib.sha256(source.encode("utf-8")).hexdigest()

            with patch(
                "nac_bff.azure_activation._PACKAGE_BUILDER_SHA256", digest
            ):
                binding, error = _function_package_binding(root)

        self.assertIsNone(binding)
        self.assertEqual(error, "generated:nac-bff-function.zip")
        self.assertFalse(marker.exists())

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

            contract = json.loads(
                (
                    REPO_ROOT
                    / "workflows/contracts/m365-azure-bff-activation-plan.contract.json"
                ).read_text(encoding="utf-8")
            )
            contract["bindings"]["entra_api_contract"][
                "requested_access_token_version"
            ] = 1
            target.write_text(json.dumps(contract), encoding="utf-8")
            self.assertFalse(_activation_contract_valid(root))

    def test_plan_builder_does_not_access_environment_network_or_subprocess(self) -> None:
        secret = "must-not-appear"
        with (
            patch.dict(os.environ, {"AZURE_CLIENT_SECRET": secret}),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS access")),
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("HTTP access")),
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
