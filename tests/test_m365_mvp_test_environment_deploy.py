from __future__ import annotations

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
    BPMN_XML,
    DEADLINE,
    MATTER_ID,
    MATTER_STATUS,
    TASKS,
    WORKSPACE_ID,
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


PASSED_ROLE_CHECKS = [
    {"scenario": "assigned", "expected": "ALLOW", "actual": "ALLOW", "passed": True},
    {"scenario": "deputy", "expected": "ALLOW", "actual": "ALLOW", "passed": True},
    {"scenario": "deny", "expected": "DENY", "actual": "DENY", "passed": True},
]
_DEFAULT_RUNNER = object()


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

    def test_policy_evidence_is_data_driven_and_live_entra_bff_is_deferred(self) -> None:
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
        self.assertEqual(evidence["liveEntraBffActivation"], "DEFERRED")
        self.assertEqual(
            evidence["deferredReason"],
            "requires_new_delegated_scope_and_public_https_endpoint",
        )

    def test_ui_graph_smoke_and_bff_share_the_canonical_synthetic_fixture(self) -> None:
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
            },
        )
        self.assertEqual(workspace["tasks"], [dict(task) for task in TASKS])
        self.assertEqual(fixture["model"]["process_key"], BPMN_PROCESS_KEY)
        self.assertEqual(fixture["model"]["content"], BPMN_XML)
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
        sample_source = (
            spfx_root / "src/webparts/nacBpmnViewer/fixtures/sampleBpmn.ts"
        ).read_text(encoding="utf-8")
        self.assertEqual(sample_source.split(chr(96), 2)[1], BPMN_XML)
        ui_fixture = (
            spfx_root / "src/webparts/nacBpmnViewer/fixtures/syntheticWorkspace.ts"
        ).read_text(encoding="utf-8")
        bff_client = (
            spfx_root / "src/webparts/nacBpmnViewer/services/NacBffClient.ts"
        ).read_text(encoding="utf-8")
        for value in (WORKSPACE_ID, BPMN_PROCESS_KEY, BPMN_SHA256):
            self.assertIn(value, ui_fixture)
        for value in (
            MATTER_ID,
            MATTER_STATUS,
            DEADLINE,
            *(str(task[key]) for task in TASKS for key in ("task_id", "title", "step_code", "status")),
        ):
            self.assertNotIn(value, ui_fixture)
        for value in (
            WORKSPACE_ID,
            MATTER_ID,
            BPMN_PROCESS_KEY,
            BPMN_SHA256,
            "api://funktion8.de/nac-bff",
            "Matter.Read",
            "https://func-nac-bff-test-funktion8.azurewebsites.net",
        ):
            self.assertIn(value, bff_client)

    def test_writer_creates_redacted_json_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out" / "evidence.json"
            write_mvp_test_environment_deploy_artifact({"status": "PASSED"}, output)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "PASSED")

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_runner_uses_explicit_binary_home_node_path_and_shell_false(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "m365-bin" / "m365"
            home = root / "m365-home"
            node_bin = root / "node-bin"
            binary.parent.mkdir()
            home.mkdir()
            node_bin.mkdir()
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            (node_bin / "node").write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o700)
            (node_bin / "node").chmod(0o700)
            run.return_value = subprocess.CompletedProcess([str(binary), "status"], 0, "{}", "")

            runner = M365CliCommandRunner(
                binary=binary,
                home=home,
                node_bin=node_bin,
                environ={
                    "PATH": "/usr/bin",
                    "LANG": "de_DE.UTF-8",
                    "M365_RUNTIME_CLIENT_SECRET": "runtime-secret",
                    "M365_RUNTIME_CERTIFICATE_PATH": "/secret/runtime.pem",
                    "M365_PROVISIONER_PRIVATE_KEY": "provisioner-key",
                    "M365_PROVISIONER_ACCESS_TOKEN": "provisioner-token",
                    "AZURE_CLIENT_SECRET": "azure-secret",
                    "GRAPH_ACCESS_TOKEN": "graph-token",
                },
            )
            result = runner.run(("m365", "status", "--output", "json"))

        self.assertEqual(result.returncode, 0)
        call = run.call_args
        self.assertEqual(call.args[0][0], str(binary.resolve()))
        self.assertEqual(call.args[0][1:], ["status", "--output", "json"])
        self.assertFalse(call.kwargs["shell"])
        self.assertEqual(call.kwargs["env"]["HOME"], str(home.resolve()))
        self.assertEqual(call.kwargs["env"]["PATH"].split(os.pathsep)[0], str(node_bin.resolve()))
        self.assertEqual(call.kwargs["env"]["LANG"], "de_DE.UTF-8")
        for forbidden in (
            "M365_RUNTIME_CLIENT_SECRET",
            "M365_RUNTIME_CERTIFICATE_PATH",
            "M365_PROVISIONER_PRIVATE_KEY",
            "M365_PROVISIONER_ACCESS_TOKEN",
            "AZURE_CLIENT_SECRET",
            "GRAPH_ACCESS_TOKEN",
        ):
            self.assertNotIn(forbidden, call.kwargs["env"])

    @patch("nac_m365_graph.mvp_test_environment_deploy.subprocess.run")
    def test_m365_readiness_requires_authenticated_expected_tenant_session(self, run) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "m365"
            binary.write_text("#!/bin/sh\n", encoding="utf-8")
            binary.chmod(0o700)
            runner = M365CliCommandRunner(binary=binary, environ={"PATH": "/usr/bin"})

            run.return_value = subprocess.CompletedProcess(
                [str(binary), "status"],
                0,
                json.dumps(
                    {
                        "connectedAs": "ofunk@funktion8.de",
                        "appTenant": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
                        "cloudType": "Public",
                    }
                ),
                "",
            )
            self.assertTrue(runner.check_readiness())

            run.return_value = subprocess.CompletedProcess(
                [str(binary), "status"],
                0,
                json.dumps(
                    {
                        "connectedAs": "ofunk@funktion8.de",
                        "appTenant": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
                        "cloudType": "USGov",
                    }
                ),
                "",
            )
            self.assertFalse(runner.check_readiness())

            run.return_value = subprocess.CompletedProcess(
                [str(binary), "status"],
                0,
                json.dumps(
                    {
                        "connectedAs": "",
                        "appTenant": "00000000-0000-0000-0000-000000000000",
                        "cloudType": "Public",
                    }
                ),
                "",
            )
            self.assertFalse(runner.check_readiness())

    def test_m365_runner_rejects_unavailable_explicit_binary(self) -> None:
        with self.assertRaisesRegex(M365CliReadinessError, "unavailable"):
            M365CliCommandRunner(
                binary="/missing/nac-m365",
                environ={"PATH": ""},
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
