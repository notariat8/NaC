from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nac_mvp_test_environment import (
    BPMN_PROCESS_KEY,
    BPMN_SHA256,
    BPMN_SOURCE_PATH,
    DEADLINE,
    KG_SCHEMA_VERSION,
    MATTER_ID,
    MATTER_STATUS,
    TASKS,
    WORKSPACE_ID,
    WORKFLOW_VERSION,
)

from nac_m365_graph import mvp_test_environment_smoke as smoke_contract
from nac_m365_graph.mvp_test_environment_deploy import (
    M365CliCommandRunner,
    M365CliReadinessError,
    DeploymentPlanError,
    SYNTHETIC_ACCESS_DECISION_SOURCE,
    run_mvp_test_environment_deploy,
    synthetic_access_decision_fixture,
    write_mvp_test_environment_deploy_artifact,
)
from nac_m365_graph.privileged_change import DEFAULT_PROVISIONED_STATE
from nac_m365_graph.node_runtime_integrity import build_node_runtime_manifest
from nac_bff.bpmn_asset import (
    CANONICAL_BPMN_MODEL_KEY,
    CANONICAL_BPMN_SHA256,
)


PASSED_ROLE_CHECKS = [
    {"scenario": "assigned", "expected": "ALLOW", "actual": "ALLOW", "passed": True},
    {"scenario": "deputy", "expected": "ALLOW", "actual": "ALLOW", "passed": True},
    {"scenario": "deny", "expected": "DENY", "actual": "DENY", "passed": True},
]
_DEFAULT_RUNNER = object()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_user_toolchain(root: Path) -> tuple[Path, Path, str, str]:
    binary = root / "m365-runtime" / "dist" / "index.js"
    node_bin = root / "node-bin"
    binary.parent.mkdir(parents=True)
    node_bin.mkdir()
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    node = node_bin / "node"
    node.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(0o700)
    node.chmod(0o700)
    bundle_digest = build_node_runtime_manifest(binary.parent.parent).digest
    return binary, node_bin, bundle_digest, _file_sha256(node)


class MvpTestEnvironmentDeployTests(unittest.TestCase):
    def test_owner_gate_and_workspace_scope_block_before_plan(self) -> None:
        with patch(
            "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan"
        ) as build:
            owner_blocked = self._run(owner_approved=False)
            workspace_blocked = self._run(workspace_id="notary_team_02")

        self.assertEqual(owner_blocked["error"]["code"], "OWNER_GATE_CLOSED")
        self.assertEqual(workspace_blocked["error"]["code"], "WORKSPACE_SCOPE_REJECTED")
        build.assert_not_called()

    def test_missing_package_hash_blocks_before_plan(self) -> None:
        with patch(
            "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan"
        ) as build:
            result = self._run(expected_hash=None)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["error"]["code"], "PACKAGE_HASH_BINDING_REQUIRED")
        build.assert_not_called()

    def test_wrong_package_hash_fails_before_deployment(self) -> None:
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                side_effect=ValueError("SHA256 mismatch"),
            ) as build,
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment"
            ) as deploy,
        ):
            result = self._run(expected_hash="0" * 64)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["controlPlane"]["error"]["code"], "DEPLOYMENT_PLAN_INVALID")
        build.assert_called_once()
        deploy.assert_not_called()

    def test_deployment_failure_stops_before_graph_smoke(self) -> None:
        plan = _Plan("a" * 64)
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment",
                return_value={"status": "FAILED", "commands_executed": 2, "steps": []},
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_mvp_test_environment_smoke_from_paths"
            ) as smoke,
        ):
            result = self._run()

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "CONTROL_PLANE_DEPLOYMENT_FAILED")
        self.assertEqual(result["syntheticDataSmoke"]["status"], "NOT_RUN")
        smoke.assert_not_called()

    def test_success_composes_hash_bound_deployment_and_cleaning_smoke(self) -> None:
        plan = _Plan("b" * 64)
        smoke_result = {
            "status": "PASSED",
            "summary": {"cleanupVerified": True},
            "cleanup": {"finallyExecuted": True, "verifiedAbsentCount": 3},
            "roleChecks": PASSED_ROLE_CHECKS,
        }
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ) as build,
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment",
                return_value={
                    "status": "PASSED",
                    "commands_executed": 11,
                    "classifications": {"publish_page": "update"},
                    "steps": [{"name": "publish_page", "status": "PASSED"}],
                },
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_mvp_test_environment_smoke_from_paths",
                return_value=smoke_result,
            ) as smoke,
        ):
            result = self._run(expected_hash="b" * 64, include_teams=True)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["controlPlane"]["packageSha256"], "b" * 64)
        self.assertTrue(result["controlPlane"]["teamsIncluded"])
        self.assertEqual(
            result["accessDecisionVerification"]["source"],
            SYNTHETIC_ACCESS_DECISION_SOURCE,
        )
        self.assertFalse(result["accessDecisionVerification"]["liveBffDecision"])
        self.assertEqual(result["accessDecisionVerification"]["status"], "PASSED")
        self.assertEqual(result["accessDecisionVerification"]["checks"], PASSED_ROLE_CHECKS)
        self.assertNotIn("notary_team_01", json.dumps(result))
        build.assert_called_once()
        self.assertEqual(build.call_args.kwargs["expected_package_sha256"], "b" * 64)
        smoke.assert_called_once()
        self.assertIs(smoke.call_args.args[1], synthetic_access_decision_fixture)

    def test_passed_smoke_without_role_evidence_fails_closed(self) -> None:
        plan = _Plan("e" * 64)
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment",
                return_value={"status": "PASSED", "commands_executed": 1},
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_mvp_test_environment_smoke_from_paths",
                return_value={"status": "PASSED"},
            ),
        ):
            result = self._run(expected_hash="e" * 64)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "ACCESS_DECISION_EVIDENCE_FAILED")
        self.assertEqual(result["accessDecisionVerification"]["status"], "FAILED")

    def test_failed_smoke_remains_redacted_and_reports_cleanup_result(self) -> None:
        plan = _Plan("c" * 64)
        smoke_result = {
            "status": "FAILED",
            "error": {"code": "WRITE_FAILED"},
            "cleanup": {"finallyExecuted": True, "verifiedAbsentCount": 1},
        }
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment",
                return_value={"status": "PASSED", "commands_executed": 1},
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_mvp_test_environment_smoke_from_paths",
                return_value=smoke_result,
            ),
        ):
            result = self._run()

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "SYNTHETIC_DATA_SMOKE_FAILED")
        self.assertTrue(result["syntheticDataSmoke"]["cleanup"]["finallyExecuted"])

    def test_orchestrator_defaults_bind_contract_state_and_bpmn_fixture(self) -> None:
        plan = _Plan("d" * 64)
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment",
                return_value={"status": "PASSED", "commands_executed": 1},
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_mvp_test_environment_smoke_from_paths",
                return_value={"status": "PASSED", "roleChecks": PASSED_ROLE_CHECKS},
            ) as smoke,
        ):
            result = run_mvp_test_environment_deploy(
                object(),
                repo_root=Path("/repo"),
                workspace_id="notary_team_01",
                owner_approved=True,
                expected_package_sha256="d" * 64,
                command_runner=_ReadyRunner(),
            )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(smoke.call_args.kwargs["workspace_id"], "notary_team_01")
        self.assertTrue(smoke.call_args.kwargs["contract_path"].name.endswith(".json"))
        self.assertTrue(smoke.call_args.kwargs["provisioned_state_path"].name.endswith(".json"))
        self.assertEqual(smoke.call_args.kwargs["fixture_path"].name, "synthetic-bpmn.fixture.json")

    def test_policy_evidence_is_data_driven_and_live_entra_bff_is_pending(self) -> None:
        base = {
            "workspace_id": WORKSPACE_ID,
            "case_id": MATTER_ID,
            "purpose": "m365_mvp_test_environment_smoke",
        }
        assigned = synthetic_access_decision_fixture(
            {**base, "scenario": "deny", "actor_id": "nac-synthetic-assigned"}
        )
        deputy = synthetic_access_decision_fixture(
            {**base, "scenario": "deny", "actor_id": "nac-synthetic-deputy"}
        )
        denied = synthetic_access_decision_fixture(
            {**base, "scenario": "assigned", "actor_id": "nac-synthetic-unassigned"}
        )

        self.assertEqual((assigned["decision"], assigned["code"]), ("ALLOW", "ALLOW_ASSIGNED_USER"))
        self.assertEqual((deputy["decision"], deputy["code"]), ("ALLOW", "ALLOW_ACTIVE_DEPUTY_GRANT"))
        self.assertEqual((denied["decision"], denied["code"]), ("DENY", "DENY_NO_ASSIGNMENT_OR_DEPUTY_GRANT"))

        blocked = self._run(owner_approved=False)
        evidence = blocked["accessDecisionVerification"]
        self.assertEqual(evidence["source"], SYNTHETIC_ACCESS_DECISION_SOURCE)
        self.assertTrue(evidence["failClosed"])
        self.assertFalse(evidence["liveBffDecision"])
        self.assertEqual(
            evidence["liveEntraBffActivation"],
            "FINAL_LIVE_RUN_PENDING",
        )
        self.assertEqual(
            evidence["pendingReason"],
            "provisioned_endpoint_and_scope_require_current_main_live_verification",
        )

    def test_ui_graph_smoke_and_bff_bind_their_declared_bpmn_sources(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "tests/fixtures/m365/mvp-test-environment/synthetic-bpmn.fixture.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        workspace = fixture["workspace"]
        self.assertEqual(workspace["workspace_id"], WORKSPACE_ID)
        self.assertEqual(
            workspace["matter"],
            {
                "matter_id": MATTER_ID,
                "business_case_type_id": "immobilienkaufvertrag",
                "status": MATTER_STATUS,
                "deadline": DEADLINE,
                "workflow_version": WORKFLOW_VERSION,
                "kg_version": KG_SCHEMA_VERSION,
            },
        )
        self.assertEqual(workspace["tasks"], [dict(task) for task in TASKS])
        self.assertEqual(fixture["model"]["process_key"], BPMN_PROCESS_KEY)
        self.assertEqual(fixture["model"]["source_path"], BPMN_SOURCE_PATH)
        self.assertEqual(fixture["model"]["content_sha256"], BPMN_SHA256)

        self.assertEqual(smoke_contract.SYNTHETIC_CASE_ID, MATTER_ID)
        self.assertEqual(smoke_contract.SYNTHETIC_TASK_IDS, tuple(task["task_id"] for task in TASKS))
        self.assertEqual(smoke_contract.SYNTHETIC_DEADLINE_DUE_DATE, DEADLINE)
        self.assertEqual(
            smoke_contract._task_arguments(),
            [
                {
                    "task_id": task["task_id"],
                    "case_id": MATTER_ID,
                    "bpmn_step_code": task["step_code"],
                    "status": task["status"],
                    "requires_notary_approval": task["requires_notary_approval"],
                    **({"due_date": task["due_at"]} if task["due_at"] else {}),
                }
                for task in TASKS
            ],
        )

        spfx_root = Path(__file__).resolve().parents[1] / "spfx/nac-bpmn-viewer"
        canonical_bpmn = (
            Path(__file__).resolve().parents[1] / "bpmn/immobilienkaufvertrag.bpmn"
        ).read_bytes()
        self.assertEqual(hashlib.sha256(canonical_bpmn).hexdigest(), CANONICAL_BPMN_SHA256)
        self.assertEqual(BPMN_PROCESS_KEY, CANONICAL_BPMN_MODEL_KEY)
        self.assertEqual(BPMN_SHA256, CANONICAL_BPMN_SHA256)
        bff_client = (
            spfx_root / "src/webparts/nacBpmnViewer/services/NacBffClient.ts"
        ).read_text(encoding="utf-8")
        for value in (
            WORKSPACE_ID,
            MATTER_ID,
            CANONICAL_BPMN_MODEL_KEY,
            CANONICAL_BPMN_SHA256,
            "api://funktion8.de/nac-bff",
            "Matter.Read",
            "https://func-nac-bff-test-funktion8.azurewebsites.net",
        ):
            self.assertIn(value, bff_client)
        self.assertNotIn("NAC_SYN_MATTER_001", bff_client)

    def test_writer_creates_redacted_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out" / "evidence.json"
            write_mvp_test_environment_deploy_artifact({"status": "PASSED"}, output)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PASSED")

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_uses_pinned_tools_minimal_env_timeout_and_shell_false(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            home = root / "m365-home"
            home.mkdir()
            run.return_value = subprocess.CompletedProcess([str(binary), "status"], 0, "{}", "")

            runner = M365CliCommandRunner(
                binary=binary,
                home=home,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                timeout_seconds=17,
                environ={
                    "PATH": "/untrusted/path",
                    "LANG": "de_DE.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "TZ": "UTC",
                    "NODE_OPTIONS": "--require=/tmp/payload.js",
                    "NODE_EXTRA_CA_CERTS": "/tmp/rogue-ca.pem",
                    "HTTP_PROXY": "http://attacker.invalid",
                    "HTTPS_PROXY": "http://attacker.invalid",
                    "NO_PROXY": "*",
                    "http_proxy": "http://attacker.invalid",
                    "M365_RUNTIME_CLIENT_SECRET": "runtime-secret",
                    "M365_PROVISIONER_PRIVATE_KEY": "provisioner-key",
                    "AZURE_CLIENT_SECRET": "azure-secret",
                    "GRAPH_ACCESS_TOKEN": "graph-token",
                },
            )
            result = runner.run(("m365", "status", "--output", "json"))

        self.assertEqual(result.returncode, 0)
        call = run.call_args
        process_argv = call.args[0]
        self.assertRegex(process_argv[0], r"^/proc/self/fd/[0-9]+$")
        self.assertEqual(
            process_argv[1:3], ["--preserve-symlinks", "--require"]
        )
        self.assertEqual(
            process_argv[-4:],
            [str(binary), "status", "--output", "json"],
        )
        self.assertFalse(call.kwargs["shell"])
        self.assertEqual(call.kwargs["cwd"], binary.parent)
        self.assertEqual(call.kwargs["timeout"], 17.0)
        self.assertEqual(len(call.kwargs["pass_fds"]), 4)
        environment = call.kwargs["env"]
        self.assertRegex(
            environment["NAC_NODE_RUNTIME_MANIFEST"],
            r"^/proc/self/fd/[0-9]+$",
        )
        self.assertEqual(
            {
                key: value
                for key, value in environment.items()
                if key not in {
                    "NAC_NODE_RUNTIME_MANIFEST",
                    "NAC_NODE_RUNTIME_PRELOADER",
                    "NAC_NODE_RUNTIME_ESM_LOADER",
                }
            },
            {
                "HOME": str(home),
                "LANG": "de_DE.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": os.pathsep.join(("/usr/bin", "/bin")),
                "TZ": "UTC",
                "CLIMICROSOFT365_NOUPDATE": "1",
                "NODE": process_argv[0],
            },
        )
        self.assertEqual(
            environment["NAC_NODE_RUNTIME_PRELOADER"], process_argv[3]
        )
        self.assertEqual(
            environment["NAC_NODE_RUNTIME_ESM_LOADER"], process_argv[5]
        )

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_reattests_cli_immediately_before_subprocess(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            binary.write_text("#!/bin/sh\n# replaced\n", encoding="utf-8")
            binary.chmod(0o700)

            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_CLI_RUNTIME_BUNDLE_MISMATCH$",
            ):
                runner.run(("m365", "status", "--output", "json"))

        run.assert_not_called()

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_reattests_node_immediately_before_subprocess(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            node = node_bin / "node"
            node.write_text("#!/bin/sh\n# replaced\n", encoding="utf-8")
            node.chmod(0o700)

            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_NODE_BINARY_SHA256_MISMATCH$",
            ):
                runner.run(("m365", "status", "--output", "json"))

        run.assert_not_called()

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_blocks_destructive_unknown_and_free_arguments(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            blocked = (
                ("m365", "spo", "app", "remove", "--id", "13074f16-12e3-4237-9a20-000000000001"),
                ("m365", "status", "free", "--output", "json"),
                (
                    "m365",
                    "request",
                    "--url",
                    "https://graph.microsoft.com/v1.0/me?$select=id",
                    "--resource",
                    "https://graph.microsoft.com",
                    "--method",
                    "delete",
                    "--output",
                    "json",
                ),
                (
                    "m365",
                    "spo",
                    "app",
                    "list",
                    "--appCatalogScope",
                    "tenant",
                    "--output",
                    "json",
                    "free",
                ),
            )
            for command in blocked:
                with self.subTest(command=command), self.assertRaisesRegex(
                    M365CliReadinessError,
                    "^M365_CLI_COMMAND_NOT_ALLOWLISTED$",
                ):
                    runner.run(command)

        run.assert_not_called()

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_allows_every_real_bff_and_spfx_command_schema(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            solution = root / "run" / "spfx" / "nac-bpmn-viewer" / "sharepoint" / "solution"
            solution.mkdir(parents=True)
            sppkg = str(solution / "nac-bpmn-viewer.sppkg")
            teams_zip = str(solution / "nac-bpmn-viewer.zip")
            identifier = "13074f16-12e3-4237-9a20-000000000001"
            site = "https://funktion8.sharepoint.com/sites/NaC-Notar-01"
            team = "124f1b11-207d-4307-bfd1-ac0fd73aa90a"
            page = "NaC-Testumgebung.aspx"
            graph_catalog = (
                "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/"
                f"{identifier}?$expand=appDefinitions"
            )
            graph_installed = (
                f"https://graph.microsoft.com/v1.0/teams/{team}/installedApps?"
                "$filter=teamsApp/externalId%20eq%20'"
                f"{identifier}'&$expand=teamsApp"
            )
            commands = [
                ("m365", "status", "--output", "json"),
                ("m365", "spo", "serviceprincipal", "grant", "list", "--output", "json"),
                ("m365", "spo", "serviceprincipal", "permissionrequest", "list", "--output", "json"),
                ("m365", "spo", "serviceprincipal", "permissionrequest", "approve", "--id", identifier, "--output", "none"),
                ("m365", "spo", "app", "list", "--appCatalogScope", "tenant", "--output", "json"),
                ("m365", "spo", "app", "get", "--name", "nac-bpmn-viewer.sppkg", "--appCatalogScope", "tenant", "--output", "json"),
                ("m365", "spo", "app", "add", "--filePath", sppkg, "--appCatalogScope", "tenant", "--output", "none"),
                ("m365", "spo", "app", "add", "--filePath", sppkg, "--appCatalogScope", "tenant", "--overwrite", "--output", "none"),
                ("m365", "spo", "app", "deploy", "--id", identifier, "--appCatalogScope", "tenant", "--output", "none"),
                ("m365", "spo", "app", "instance", "list", "--siteUrl", site, "--output", "json"),
                ("m365", "spo", "app", "install", "--id", identifier, "--siteUrl", site, "--appCatalogScope", "tenant", "--output", "none"),
                ("m365", "spo", "app", "upgrade", "--id", identifier, "--siteUrl", site, "--appCatalogScope", "tenant", "--output", "none"),
                ("m365", "spo", "page", "list", "--webUrl", site, "--output", "json"),
                ("m365", "spo", "page", "get", "--name", page, "--webUrl", site, "--output", "json"),
                ("m365", "spo", "page", "set", "--name", page, "--webUrl", site, "--layoutType", "Article", "--title", "NaC-Testumgebung", "--output", "none"),
                ("m365", "spo", "page", "add", "--name", page, "--webUrl", site, "--layoutType", "Article", "--title", "NaC-Testumgebung", "--output", "none"),
                ("m365", "spo", "page", "set", "--name", page, "--webUrl", site, "--content", '[{"controlType":0,"pageSettingsSlice":{"isDefaultDescription":true,"isDefaultThumbnail":true}}]', "--output", "none"),
                ("m365", "spo", "page", "clientsidewebpart", "add", "--webUrl", site, "--pageName", page, "--webPartId", "3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21", "--output", "none"),
                ("m365", "spo", "page", "set", "--name", page, "--webUrl", site, "--publish", "--output", "none"),
                ("m365", "spo", "app", "teamspackage", "download", "--appName", "nac-bpmn-viewer.sppkg", "--fileName", teams_zip, "--output", "none"),
                ("m365", "teams", "app", "list", "--distributionMethod", "organization", "--output", "json"),
                ("m365", "teams", "app", "publish", "--filePath", teams_zip, "--output", "json"),
                ("m365", "teams", "app", "update", "--id", identifier, "--filePath", teams_zip, "--output", "none"),
                ("m365", "teams", "app", "install", "--id", identifier, "--teamId", team, "--output", "none"),
                ("m365", "request", "--url", graph_catalog, "--method", "get", "--output", "json"),
                ("m365", "request", "--url", graph_installed, "--method", "get", "--output", "json"),
                ("m365", "request", "--url", "https://graph.microsoft.com/v1.0/me?$select=id", "--resource", "https://graph.microsoft.com", "--method", "get", "--output", "json"),
                ("m365", "request", "--url", "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001?purpose=view_synthetic_matter_workspace", "--resource", "api://funktion8.de/nac-bff", "--method", "get", "--output", "json"),
                ("m365", "request", "--url", "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/foreign_workspace/matters/NAC-SYN-MATTER-001?purpose=view_synthetic_matter_workspace", "--resource", "api://funktion8.de/nac-bff", "--method", "get", "--output", "json"),
                ("m365", "request", "--url", "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-FOREIGN?purpose=view_synthetic_matter_workspace", "--resource", "api://funktion8.de/nac-bff", "--method", "get", "--output", "json"),
                ("m365", "request", "--url", "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001?purpose=foreign", "--resource", "api://funktion8.de/nac-bff", "--method", "get", "--output", "json"),
                ("m365", "request", "--url", "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001?purpose=view_synthetic_matter_workspace&site_id=foreign", "--resource", "api://funktion8.de/nac-bff", "--method", "get", "--output", "json"),
            ]
            run.return_value = subprocess.CompletedProcess([], 0, "{}", "")
            for command in commands:
                with self.subTest(command=command):
                    self.assertEqual(runner.run(command).returncode, 0)

        self.assertEqual(run.call_count, len(commands))

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_readiness_binds_exact_user_app_tenant_and_public_cloud(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )

            canonical = {
                "connectedAs": "ofunk@funktion8.de",
                "appId": "c86dded6-9723-4b8d-91f2-e0fd70e25839",
                "appTenant": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
                "cloudType": "Public",
            }
            run.return_value = subprocess.CompletedProcess(
                [str(binary), "status"],
                0,
                json.dumps(canonical),
                "",
            )
            self.assertTrue(runner.check_readiness())

            for field, wrong_value in (
                ("connectedAs", "other@funktion8.de"),
                ("appId", "00000000-0000-0000-0000-000000000000"),
                ("appTenant", "00000000-0000-0000-0000-000000000000"),
                ("cloudType", "USGov"),
            ):
                payload = {**canonical, field: wrong_value}
                run.return_value = subprocess.CompletedProcess(
                    [str(binary), "status"],
                    0,
                    json.dumps(payload),
                    "",
                )
                with self.subTest(field=field):
                    self.assertFalse(runner.check_readiness())

    def test_m365_runner_rejects_path_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path_binary = root / "path-bin" / "m365"
            path_binary.parent.mkdir()
            path_binary.write_text("#!/bin/sh\n", encoding="utf-8")
            path_binary.chmod(0o700)
            with (
                patch.object(M365CliCommandRunner, "_LOCAL_BINARY", root / "missing"),
                self.assertRaisesRegex(
                    M365CliReadinessError,
                    "^M365_CLI_BINARY_UNAVAILABLE$",
                ),
            ):
                M365CliCommandRunner(environ={"PATH": str(path_binary.parent)})

    def test_m365_runner_rejects_world_writable_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "m365-runtime/dist/index.js"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o777)
            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_CLI_BINARY_MODE_UNSAFE$",
            ):
                M365CliCommandRunner(
                    binary=binary,
                    expected_binary_sha256=_file_sha256(binary),
                    environ={},
                )

    def test_m365_runner_rejects_binary_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "m365-real"
            target.write_text("#!/bin/sh\n", encoding="utf-8")
            target.chmod(0o700)
            binary = root / "m365"
            binary.symlink_to(target)
            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_CLI_BINARY_SYMLINK_REJECTED$",
            ):
                M365CliCommandRunner(
                    binary=binary,
                    expected_binary_sha256=_file_sha256(target),
                    environ={},
                )

    def test_m365_runner_requires_and_verifies_user_owned_binary_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "m365-runtime/dist/index.js"
            binary.parent.mkdir(parents=True)
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o700)
            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_CLI_BINARY_SHA256_INVALID$",
            ):
                M365CliCommandRunner(binary=binary, environ={})
            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_CLI_RUNTIME_BUNDLE_MISMATCH$",
            ):
                M365CliCommandRunner(
                    binary=binary,
                    expected_binary_sha256="0" * 64,
                    environ={},
                )

    def test_m365_runner_requires_hash_for_user_owned_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, _ = _write_user_toolchain(root)
            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_NODE_BINARY_SHA256_REQUIRED$",
            ):
                M365CliCommandRunner(
                    binary=binary,
                    node_bin=node_bin,
                    expected_binary_sha256=binary_sha256,
                    environ={},
                )

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_timeout_is_bounded_and_redacted(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                timeout_seconds=0.5,
                environ={},
            )
            run.side_effect = subprocess.TimeoutExpired(
                cmd=[str(binary), "status"],
                timeout=0.5,
                output="secret-output",
                stderr="secret-error",
            )
            with self.assertRaisesRegex(
                M365CliReadinessError,
                "^M365_CLI_COMMAND_TIMEOUT$",
            ) as captured:
                runner.run(("m365", "status", "--output", "json"))

        self.assertIsNone(captured.exception.__cause__)
        self.assertNotIn("secret", str(captured.exception))
        self.assertEqual(run.call_args.kwargs["timeout"], 0.5)

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_redacts_nonzero_process_output(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            run.return_value = subprocess.CompletedProcess(
                [str(binary), "status"],
                1,
                "access-token-value",
                "tenant secret detail",
            )
            result = runner.run(("m365", "status", "--output", "json"))

        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "M365_CLI_COMMAND_FAILED")

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_normalizes_only_exact_allowlisted_bff_403(self, run) -> None:
        base_url = (
            "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/"
            "notary_team_01/matters/NAC-SYN-MATTER-001"
            "?purpose=view_synthetic_matter_workspace"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            run.return_value = subprocess.CompletedProcess(
                [str(binary), "request"],
                1,
                "",
                "Error: Request failed with status code 403",
            )
            urls = (
                base_url,
                base_url.replace(
                    "/workspaces/notary_team_01/",
                    "/workspaces/foreign_workspace/",
                ),
                base_url.replace(
                    "/matters/NAC-SYN-MATTER-001",
                    "/matters/NAC-SYN-MATTER-FOREIGN",
                ),
                base_url.replace(
                    "purpose=view_synthetic_matter_workspace",
                    "purpose=foreign",
                ),
                f"{base_url}&site_id=foreign",
            )
            for url in urls:
                with self.subTest(url=url):
                    result = runner.run(
                        (
                            "m365",
                            "request",
                            "--url",
                            url,
                            "--resource",
                            "api://funktion8.de/nac-bff",
                            "--method",
                            "get",
                            "--output",
                            "json",
                        )
                    )
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stderr, "")
                    self.assertEqual(
                        json.loads(result.stdout),
                        {"status": 403, "error": {"code": "ACCESS_DENIED"}},
                    )

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_rejects_ambiguous_or_body_injected_403(self, run) -> None:
        base_url = (
            "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/"
            "notary_team_01/matters/NAC-SYN-MATTER-001"
            "?purpose=view_synthetic_matter_workspace"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            run.return_value = subprocess.CompletedProcess(
                [str(binary), "request"],
                1,
                "untrusted body says Request failed with status code 403",
                "Request failed with status code 500",
            )
            result = runner.run(
                (
                    "m365",
                    "request",
                    "--url",
                    base_url,
                    "--resource",
                    "api://funktion8.de/nac-bff",
                    "--method",
                    "get",
                    "--output",
                    "json",
                )
            )
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "M365_CLI_COMMAND_FAILED")

    def test_m365_runner_rejects_unavailable_explicit_binary(self) -> None:
        with self.assertRaisesRegex(
            M365CliReadinessError,
            "^M365_CLI_BINARY_UNAVAILABLE$",
        ):
            M365CliCommandRunner(
                binary="/missing/nac-m365",
                environ={},
            )

    def test_modified_state_is_rejected_before_plan_readiness_or_any_write(self) -> None:
        canonical = json.loads(DEFAULT_PROVISIONED_STATE.read_text(encoding="utf-8"))
        for workspace in canonical["workspaces"]:
            if workspace.get("id") == WORKSPACE_ID:
                workspace["site_id"] = "funktion8.sharepoint.com,foreign,site"
        with tempfile.TemporaryDirectory() as tmp:
            modified_state = Path(tmp) / "state.json"
            modified_state.write_text(json.dumps(canonical), encoding="utf-8")
            runner = _ReadyRunner()
            with (
                patch(
                    "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan"
                ) as build,
                patch(
                    "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment"
                ) as deploy,
            ):
                result = self._run(
                    command_runner=runner,
                    provisioned_state_path=modified_state,
                )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["error"]["code"], "MVP_INPUT_BINDING_INVALID")
        self.assertEqual(result["inputBinding"]["status"], "FAILED")
        self.assertEqual(runner.readiness_checks, 0)
        build.assert_not_called()
        deploy.assert_not_called()

    def test_plan_resource_drift_is_rejected_before_readiness_or_write(self) -> None:
        plan = _Plan("a" * 64)
        plan.team_id = "foreign-team"
        runner = _ReadyRunner()
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment"
            ) as deploy,
        ):
            result = self._run(command_runner=runner)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["controlPlane"]["error"]["code"],
            "DEPLOYMENT_PLAN_INVALID",
        )
        self.assertEqual(runner.readiness_checks, 0)
        deploy.assert_not_called()

    def test_injected_runner_must_pass_readiness_before_deployment(self) -> None:
        plan = _Plan("a" * 64)
        runner = _ReadyRunner(ready=False)
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment"
            ) as deploy,
        ):
            result = self._run(command_runner=runner)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["controlPlane"]["error"]["code"],
            "M365_CLI_SESSION_NOT_READY",
        )
        self.assertEqual(runner.readiness_checks, 1)
        deploy.assert_not_called()

    def test_runner_without_readiness_contract_fails_closed(self) -> None:
        plan = _Plan("a" * 64)
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment"
            ) as deploy,
        ):
            result = self._run(command_runner=object())

        self.assertEqual(
            result["controlPlane"]["error"]["code"],
            "M365_CLI_SESSION_NOT_READY",
        )
        deploy.assert_not_called()

    def test_script_delegates_cli_runner_creation_to_checked_orchestrator(self) -> None:
        script = (
            Path(__file__).resolve().parents[1]
            / "scripts/provision_teams_sharepoint_graph.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("M365CliCommandRunner", script)

    def test_missing_sppkg_reports_precise_readiness_error_before_cli(self) -> None:
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                side_effect=DeploymentPlanError(
                    "SPFx package is missing at spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg"
                ),
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.M365CliCommandRunner"
            ) as runner,
        ):
            result = self._run(command_runner=None)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["controlPlane"]["error"]["code"], "SPFX_PACKAGE_NOT_BUILT")
        runner.assert_not_called()

    def test_unavailable_default_cli_session_stops_before_deployment(self) -> None:
        plan = _Plan("a" * 64)
        with (
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.build_spfx_site_deployment_plan",
                return_value=plan,
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.M365CliCommandRunner",
                side_effect=M365CliReadinessError("missing"),
            ),
            patch(
                "nac_m365_graph.mvp_test_environment_deploy.run_spfx_site_deployment"
            ) as deploy,
        ):
            result = self._run(command_runner=None)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["controlPlane"]["error"]["code"], "M365_CLI_SESSION_NOT_READY")
        deploy.assert_not_called()

    def _run(
        self,
        *,
        workspace_id: str = "notary_team_01",
        owner_approved: bool = True,
        expected_hash: str | None = "a" * 64,
        include_teams: bool = False,
        command_runner: object | None = _DEFAULT_RUNNER,
        provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    ) -> dict:
        return run_mvp_test_environment_deploy(
            object(),
            repo_root=Path("/repo"),
            workspace_id=workspace_id,
            owner_approved=owner_approved,
            expected_package_sha256=expected_hash,
            include_teams=include_teams,
            provisioned_state_path=provisioned_state_path,
            command_runner=(
                _ReadyRunner()
                if command_runner is _DEFAULT_RUNNER
                else command_runner
            ),
        )


    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_bound_artifact_uses_sealed_descriptor(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary, node_bin, binary_sha256, node_sha256 = _write_user_toolchain(root)
            package = (
                root / "spfx/nac-bpmn-viewer/sharepoint/solution/nac-bpmn-viewer.sppkg"
            )
            package.parent.mkdir(parents=True)
            package.write_bytes(b"approved-package")
            package_sha256 = hashlib.sha256(package.read_bytes()).hexdigest()
            observed: dict[str, object] = {}
            def inspect_provider_path(argv, **kwargs):
                provider_path = argv[argv.index("--filePath") + 1]
                observed["basename"] = Path(provider_path).name
                observed["payload"] = Path(os.path.realpath(provider_path)).read_bytes()
                return subprocess.CompletedProcess([], 0, "", "")
            run.side_effect = inspect_provider_path
            runner = M365CliCommandRunner(
                binary=binary,
                node_bin=node_bin,
                expected_binary_sha256=binary_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            result = runner.run_bound(
                (
                    "m365", "spo", "app", "add", "--filePath", str(package),
                    "--appCatalogScope", "tenant", "--output", "none",
                ),
                {str(package): (package, package_sha256)},
            )

        self.assertEqual(result.returncode, 0)
        provider_argv = run.call_args.args[0]
        self.assertNotIn(str(package), provider_argv)
        file_path = provider_argv[provider_argv.index("--filePath") + 1]
        self.assertRegex(file_path, r"^/proc/self/fd/[0-9]+/nac-bpmn-viewer[.]sppkg$")
        self.assertEqual(len(run.call_args.kwargs["pass_fds"]), 5)
        self.assertEqual(observed, {"basename": "nac-bpmn-viewer.sppkg", "payload": b"approved-package"})


class _Plan:
    def __init__(self, package_sha256: str) -> None:
        self.package_sha256 = package_sha256
        self.workspace_id = WORKSPACE_ID
        self.site_url = "https://funktion8.sharepoint.com/sites/NaC-Notar-01"
        self.team_id = "124f1b11-207d-4307-bfd1-ac0fd73aa90a"


class _ReadyRunner:
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready
        self.readiness_checks = 0

    def check_readiness(self) -> bool:
        self.readiness_checks += 1
        return self.ready

    def run(self, argv: object) -> object:
        raise AssertionError(f"unexpected command: {argv}")


if __name__ == "__main__":
    unittest.main()
