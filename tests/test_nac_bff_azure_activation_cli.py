from __future__ import annotations

import io
import json
import os
import sys
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402


HASH = "a" * 64
BODY_HASH = "b" * 64
COMMIT = "c" * 40
TREE = "d" * 40
AZURE_TOOLCHAIN_HASH = "1" * 64
M365_CLI_HASH = "2" * 64
M365_NODE_HASH = "3" * 64
BUILD_PYTHON_HASH = "8" * 64
BUILD_NODE_HASH = "4" * 64
BUILD_NPM_HASH = "5" * 64
GH_CLI_HASH = "6" * 64
PROVISIONER_CERTIFICATE_HASH = "7" * 64
PROVISIONER_BOOTSTRAP_BINDING_HASH = "9" * 64
APPROVAL_REFERENCE = "https://github.com/notariat8/NaC/issues/632#issuecomment-123456"
PROVISIONER_STATE = Path("/tmp/privileged-apply-result.json")
PROVISIONER_CERTIFICATE = Path("/tmp/provisioner.cert.pem")
PROVISIONER_PRIVATE_KEY = Path("/tmp/provisioner.key.pem")


@dataclass(frozen=True)
class _FakeRequest:
    expected_activation_hash: str
    owner_approval_reference: str
    approval_body_sha256: str
    approved_commit: str
    approved_tree: str
    azure_cli_toolchain_sha256: str
    m365_cli_sha256: str
    m365_node_sha256: str
    build_python_sha256: str
    build_node_sha256: str
    build_npm_cli_sha256: str
    gh_cli_sha256: str
    provisioner_certificate_sha256: str
    provisioner_bootstrap_binding_sha256: str
    reason: str
    correlation_id: str
    owner_approved: bool
    execute_live_activation: bool
    resume: bool = False


class AzureBffLiveActivationCliTests(unittest.TestCase):
    def _argv(self, *extra: str) -> list[str]:
        return [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "bff-azure-activate-live",
            "--owner-approved",
            "--execute-live-activation",
            "--expected-activation-hash",
            HASH,
            "--approval-reference",
            APPROVAL_REFERENCE,
            "--approval-body-sha256",
            BODY_HASH,
            "--approved-commit",
            COMMIT,
            "--approved-tree",
            TREE,
            "--azure-cli-toolchain-sha256",
            AZURE_TOOLCHAIN_HASH,
            "--m365-cli-sha256",
            M365_CLI_HASH,
            "--m365-node-sha256",
            M365_NODE_HASH,
            "--build-python-sha256",
            BUILD_PYTHON_HASH,
            "--build-node-sha256",
            BUILD_NODE_HASH,
            "--build-npm-cli-sha256",
            BUILD_NPM_HASH,
            "--gh-cli-sha256",
            GH_CLI_HASH,
            "--provisioner-certificate-sha256",
            PROVISIONER_CERTIFICATE_HASH,
            "--provisioner-bootstrap-binding-sha256",
            PROVISIONER_BOOTSTRAP_BINDING_HASH,
            "--provisioner-state",
            str(PROVISIONER_STATE),
            "--provisioner-certificate-path",
            str(PROVISIONER_CERTIFICATE),
            "--provisioner-private-key-path",
            str(PROVISIONER_PRIVATE_KEY),
            "--reason",
            "Owner approved the exact activation target.",
            "--correlation-id",
            "nac-bff-live-20260714",
            *extra,
        ]

    def _fake_modules(self, *, status: str = "PASSED") -> tuple[dict[str, types.ModuleType], Mock, Mock]:
        factory = Mock(return_value=object())
        run = Mock(return_value={"status": status, "step_results": []})

        composition = types.ModuleType("nac_bff.azure_activation_composition")
        composition.build_live_activation_execution_port = factory
        runner = types.ModuleType("nac_bff.azure_activation_runner")
        runner.DEFAULT_OUTPUT_ROOT = Path("out/default")
        runner.LiveActivationRequest = _FakeRequest
        runner.run_azure_bff_live_activation = run
        bootstrap = types.ModuleType("nac_bff.azure_activation_provisioner_bootstrap")
        bootstrap.build_activation_provisioner_bootstrap = Mock(
            return_value=types.SimpleNamespace(
                env_overlay={"M365_TENANT_ID": "bound-tenant"},
                binding_sha256=PROVISIONER_BOOTSTRAP_BINDING_HASH,
                readiness={"status": "PASSED"},
            )
        )
        return {
            "nac_bff.azure_activation_composition": composition,
            "nac_bff.azure_activation_provisioner_bootstrap": bootstrap,
            "nac_bff.azure_activation_runner": runner,
        }, factory, run

    def test_parser_requires_every_owner_binding_argument_except_gate_flags(self) -> None:
        required_options = (
            "--expected-activation-hash",
            "--approval-reference",
            "--approval-body-sha256",
            "--approved-commit",
            "--approved-tree",
            "--azure-cli-toolchain-sha256",
            "--m365-cli-sha256",
            "--m365-node-sha256",
            "--build-python-sha256",
            "--build-node-sha256",
            "--build-npm-cli-sha256",
            "--gh-cli-sha256",
            "--provisioner-certificate-sha256",
            "--provisioner-bootstrap-binding-sha256",
            "--provisioner-state",
            "--provisioner-certificate-path",
            "--provisioner-private-key-path",
            "--reason",
            "--correlation-id",
        )
        argv = self._argv()
        for option in required_options:
            with self.subTest(option=option):
                candidate = list(argv)
                index = candidate.index(option)
                del candidate[index : index + 2]
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    nac_cli.main(candidate)
                self.assertEqual(raised.exception.code, 2)

    def test_closed_gate_stops_before_lazy_factory_import(self) -> None:
        argv = self._argv()
        argv.remove("--execute-live-activation")
        composition = types.ModuleType("nac_bff.azure_activation_composition")
        composition.build_live_activation_execution_port = Mock(
            side_effect=AssertionError("factory must remain unreachable")
        )
        stdout = io.StringIO()
        with (
            patch.dict(sys.modules, {"nac_bff.azure_activation_composition": composition}),
            redirect_stdout(stdout),
        ):
            rc = nac_cli.main(argv)
        self.assertEqual(rc, 2)
        self.assertEqual(
            stdout.getvalue(),
            "STATUS: BLOCKED\nERROR: OWNER_GATE_CLOSED\n",
        )
        composition.build_live_activation_execution_port.assert_not_called()

    def test_each_missing_gate_flag_returns_redacted_json_without_traceback(self) -> None:
        for flag in ("--owner-approved", "--execute-live-activation"):
            with self.subTest(flag=flag):
                argv = self._argv("--format", "json")
                argv.remove(flag)
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    rc = nac_cli.main(argv)
                self.assertEqual(rc, 2)
                self.assertEqual(stderr.getvalue(), "")
                self.assertEqual(
                    json.loads(stdout.getvalue()),
                    {
                        "schema_version": "nac.m365-azure-bff-live-activation-cli/v1",
                        "status": "BLOCKED",
                        "error": {"code": "OWNER_GATE_CLOSED"},
                        "writes_started": False,
                    },
                )

    def test_closed_gate_precedes_missing_binding_argument_validation(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        argv = [
            "m365",
            "teams-sharepoint",
            "bff-azure-activate-live",
            "--format",
            "json",
        ]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            rc = nac_cli.main(argv)
        self.assertEqual(rc, 2)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            json.loads(stdout.getvalue())["error"]["code"],
            "OWNER_GATE_CLOSED",
        )

    def test_factory_and_execution_errors_are_redacted_without_traceback(self) -> None:
        cases = (
            ("factory", "LIVE_ACTIVATION_FACTORY_FAILED"),
            ("execution", "LIVE_ACTIVATION_EXECUTION_FAILED"),
        )
        for phase, expected_code in cases:
            with self.subTest(phase=phase):
                modules, factory, run = self._fake_modules()
                secret = "provider-secret-must-not-escape"
                (factory if phase == "factory" else run).side_effect = RuntimeError(secret)
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch.dict(sys.modules, modules),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    rc = nac_cli.main(self._argv("--format", "json"))
                self.assertEqual(rc, 2)
                self.assertEqual(stderr.getvalue(), "")
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["error"]["code"], expected_code)
                self.assertFalse(payload["writes_started"])
                self.assertNotIn(secret, stdout.getvalue())

    def test_bootstrap_block_or_exception_stops_before_factory_and_write(self) -> None:
        cases = (
            ("blocked", "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED"),
            ("exception", "PROVISIONER_ENV_BOOTSTRAP_FAILED"),
        )
        for phase, expected_code in cases:
            with self.subTest(phase=phase):
                modules, factory, run = self._fake_modules()
                bootstrap = modules[
                    "nac_bff.azure_activation_provisioner_bootstrap"
                ].build_activation_provisioner_bootstrap
                if phase == "blocked":
                    bootstrap.return_value = types.SimpleNamespace(
                        env_overlay={},
                        readiness={
                            "status": "BLOCKED",
                            "error_code": expected_code,
                            "private_path": "/secret/key.pem",
                        },
                    )
                else:
                    bootstrap.side_effect = RuntimeError(
                        "private-value-must-not-escape"
                    )
                stdout = io.StringIO()
                stderr = io.StringIO()
                with (
                    patch.dict(sys.modules, modules),
                    redirect_stdout(stdout),
                    redirect_stderr(stderr),
                ):
                    rc = nac_cli.main(self._argv("--format", "json"))

                self.assertEqual(rc, 2)
                self.assertEqual(stderr.getvalue(), "")
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["error"]["code"], expected_code)
                self.assertFalse(payload["writes_started"])
                self.assertNotIn("secret", stdout.getvalue())
                self.assertNotIn("private-value", stdout.getvalue())
                factory.assert_not_called()
                run.assert_not_called()

    def test_bootstrap_binding_mismatch_stops_before_factory_and_write(self) -> None:
        modules, factory, run = self._fake_modules()
        bootstrap = modules[
            "nac_bff.azure_activation_provisioner_bootstrap"
        ].build_activation_provisioner_bootstrap
        bootstrap.return_value = types.SimpleNamespace(
            env_overlay={"M365_TENANT_ID": "bound-tenant"},
            binding_sha256="0" * 64,
            readiness={"status": "PASSED"},
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.dict(sys.modules, modules),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            rc = nac_cli.main(self._argv("--format", "json"))

        self.assertEqual(rc, 2)
        self.assertEqual(stderr.getvalue(), "")
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            payload["error"]["code"],
            "PROVISIONER_BOOTSTRAP_BINDING_MISMATCH",
        )
        self.assertFalse(payload["writes_started"])
        factory.assert_not_called()
        run.assert_not_called()

    def test_invalid_repo_config_is_redacted_without_traceback(self) -> None:
        modules, factory, _run = self._fake_modules()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.dict(sys.modules, modules),
            patch.object(
                nac_cli,
                "resolve_repo_root",
                side_effect=ValueError("config-secret-must-not-escape"),
            ),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            rc = nac_cli.main(self._argv("--format", "json"))
        self.assertEqual(rc, 2)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            json.loads(stdout.getvalue())["error"]["code"],
            "LIVE_ACTIVATION_CONFIG_INVALID",
        )
        self.assertNotIn("config-secret", stdout.getvalue())
        factory.assert_not_called()

    def test_arguments_are_forwarded_after_both_gates(self) -> None:
        modules, factory, run = self._fake_modules()
        stdout = io.StringIO()
        original_env = {"EXISTING_RUNTIME_VALUE": "preserved"}
        with (
            patch.dict(sys.modules, modules),
            patch.dict(os.environ, original_env, clear=True),
            redirect_stdout(stdout),
        ):
            rc = nac_cli.main(self._argv("--format", "json"))
            self.assertEqual(dict(os.environ), original_env)

        self.assertEqual(rc, 0)
        request = factory.call_args.args[1]
        factory.assert_called_once_with(
            REPO_ROOT,
            request,
            environ={
                "EXISTING_RUNTIME_VALUE": "preserved",
                "M365_TENANT_ID": "bound-tenant",
            },
        )
        bootstrap = modules[
            "nac_bff.azure_activation_provisioner_bootstrap"
        ].build_activation_provisioner_bootstrap
        bootstrap.assert_called_once_with(
            PROVISIONER_STATE,
            PROVISIONER_CERTIFICATE,
            PROVISIONER_PRIVATE_KEY,
            env=os.environ,
        )
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["repo_root"], REPO_ROOT)
        self.assertEqual(kwargs["output_root"], Path("out/default"))
        self.assertIs(kwargs["execution_port"], factory.return_value)
        self.assertEqual(
            kwargs["request"],
            _FakeRequest(
                expected_activation_hash=HASH,
                owner_approval_reference=APPROVAL_REFERENCE,
                approval_body_sha256=BODY_HASH,
                approved_commit=COMMIT,
                approved_tree=TREE,
                azure_cli_toolchain_sha256=AZURE_TOOLCHAIN_HASH,
                m365_cli_sha256=M365_CLI_HASH,
                m365_node_sha256=M365_NODE_HASH,
                build_python_sha256=BUILD_PYTHON_HASH,
                build_node_sha256=BUILD_NODE_HASH,
                build_npm_cli_sha256=BUILD_NPM_HASH,
                gh_cli_sha256=GH_CLI_HASH,
                provisioner_certificate_sha256=PROVISIONER_CERTIFICATE_HASH,
                provisioner_bootstrap_binding_sha256=(
                    PROVISIONER_BOOTSTRAP_BINDING_HASH
                ),
                reason="Owner approved the exact activation target.",
                correlation_id="nac-bff-live-20260714",
                owner_approved=True,
                execute_live_activation=True,
                resume=False,
            ),
        )
        self.assertEqual(json.loads(stdout.getvalue())["status"], "PASSED")

    def test_resume_and_output_root_are_not_exposed(self) -> None:
        for option, value in (("--resume", None), ("--output-root", "/tmp/other")):
            with self.subTest(option=option):
                argv = self._argv(option, *([] if value is None else [value]))
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    nac_cli.main(argv)
                self.assertEqual(raised.exception.code, 2)

    def test_return_code_is_zero_only_for_passed(self) -> None:
        for status, expected_rc in (("PASSED", 0), ("BLOCKED", 2), ("FAILED_PARTIAL", 2)):
            with self.subTest(status=status):
                modules, _factory, _run = self._fake_modules(status=status)
                stdout = io.StringIO()
                with patch.dict(sys.modules, modules), redirect_stdout(stdout):
                    rc = nac_cli.main(self._argv("--format", "text"))
                self.assertEqual(rc, expected_rc)
                self.assertEqual(stdout.getvalue(), f"STATUS: {status}\n")

    def test_json_output_exposes_exact_contract_summary_keys(self) -> None:
        modules, _factory, run = self._fake_modules()
        summary = {
            "required_step_count": 12,
            "passed_step_count": 12,
            "failed_step_count": 0,
            "duplicate_count": 0,
            "broader_permission_count": 0,
            "automatic_rollback_count": 0,
            "automatic_deletion_count": 0,
            "writes_started": True,
            "ledger_hash_chain_valid": True,
            "prebuilt_inputs_verified": True,
            "healthz_before_auth_passed": True,
            "authenticated_read_passed": True,
            "readyz_after_authenticated_read_passed": True,
            "synthetic_state_restored": True,
            "assigned_access_passed": True,
            "deputy_access_passed": True,
            "denied_access_passed": True,
            "tampered_access_passed": True,
            "resume_enabled": False,
        }
        run.return_value = {
            "status": "PASSED",
            "toolchain_attestations_sha256": "8" * 64,
            "step_results": [],
            "summary": {**summary, "provider_secret": "drop-me"},
        }
        stdout = io.StringIO()
        with patch.dict(sys.modules, modules), redirect_stdout(stdout):
            rc = nac_cli.main(self._argv("--format", "json"))

        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["summary"], summary)
        self.assertEqual(payload["toolchain_attestations_sha256"], "8" * 64)

    def test_json_output_drops_unexpected_provider_fields(self) -> None:
        modules, _factory, run = self._fake_modules()
        run.return_value = {
            "schema_version": "nac.m365-azure-bff-live-activation-evidence/v1",
            "status": "PASSED",
            "step_results": [{"id": "azure_preflight", "status": "PASSED", "token": "secret"}],
            "provider_output": "secret",
        }
        stdout = io.StringIO()
        with patch.dict(sys.modules, modules), redirect_stdout(stdout):
            rc = nac_cli.main(self._argv("--format", "json"))

        self.assertEqual(rc, 0)
        payload = json.loads(stdout.getvalue())
        self.assertNotIn("provider_output", payload)
        self.assertNotIn("token", payload["step_results"][0])


class AzureBffLiveActivationRecoveryCliTests(unittest.TestCase):
    def _argv(self, *extra: str) -> list[str]:
        return [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "bff-azure-activation-recovery",
            "--owner-approved",
            "--expected-activation-hash",
            HASH,
            "--approval-reference",
            APPROVAL_REFERENCE,
            "--approval-body-sha256",
            BODY_HASH,
            "--approved-commit",
            COMMIT,
            "--approved-tree",
            TREE,
            "--azure-cli-toolchain-sha256",
            AZURE_TOOLCHAIN_HASH,
            "--m365-cli-sha256",
            M365_CLI_HASH,
            "--m365-node-sha256",
            M365_NODE_HASH,
            "--build-python-sha256",
            BUILD_PYTHON_HASH,
            "--build-node-sha256",
            BUILD_NODE_HASH,
            "--build-npm-cli-sha256",
            BUILD_NPM_HASH,
            "--gh-cli-sha256",
            GH_CLI_HASH,
            "--provisioner-certificate-sha256",
            PROVISIONER_CERTIFICATE_HASH,
            "--provisioner-bootstrap-binding-sha256",
            PROVISIONER_BOOTSTRAP_BINDING_HASH,
            "--reason",
            "Owner approved finalization recovery inspection.",
            "--correlation-id",
            "nac-bff-recovery-20260715",
            *extra,
        ]

    def _fake_runner(self, *, code: str) -> tuple[types.ModuleType, Mock]:
        reconcile = Mock(
            return_value={
                "status": "FAILED_PARTIAL",
                "writes_started": True,
                "error": {"code": code, "provider_detail": "drop-me"},
                "recovery": {
                    "lock_held": code != "FINALIZATION_LOCK_RECONCILED",
                    "committed_artifacts_valid": False,
                    "resume_enabled": False,
                    "state_sha256": "8" * 64,
                    "ledger_head_sha256": "9" * 64,
                    "reconcile_marker_sha256": "0" * 64,
                    "private_path": "/tmp/drop-me",
                },
            }
        )
        runner = types.ModuleType("nac_bff.azure_activation_runner")
        runner.LiveActivationRequest = _FakeRequest
        runner.reconcile_azure_bff_live_activation_lock = reconcile
        return runner, reconcile

    def test_closed_gate_stops_before_recovery_import(self) -> None:
        argv = self._argv("--format", "json")
        argv.remove("--owner-approved")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            rc = nac_cli.main(argv)
        self.assertEqual(rc, 2)
        self.assertEqual(json.loads(stdout.getvalue())["error"]["code"], "OWNER_GATE_CLOSED")

    def test_read_only_inspection_forwards_bound_request_without_unlock(self) -> None:
        runner, reconcile = self._fake_runner(code="FINALIZATION_RECOVERY_REQUIRED")
        stdout = io.StringIO()
        with patch.dict(sys.modules, {"nac_bff.azure_activation_runner": runner}), redirect_stdout(stdout):
            rc = nac_cli.main(self._argv("--format", "json"))
        self.assertEqual(rc, 0)
        kwargs = reconcile.call_args.kwargs
        self.assertEqual(kwargs["repo_root"], REPO_ROOT)
        self.assertFalse(kwargs["confirm_unlock"])
        self.assertEqual(kwargs["request"].expected_activation_hash, HASH)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["recovery"]["lock_held"])
        self.assertNotIn("private_path", payload["recovery"])
        self.assertEqual(payload["error"], {"code": "FINALIZATION_RECOVERY_REQUIRED"})

    def test_confirm_unlock_is_forwarded_and_redacted(self) -> None:
        runner, reconcile = self._fake_runner(code="FINALIZATION_LOCK_RECONCILED")
        stdout = io.StringIO()
        with patch.dict(sys.modules, {"nac_bff.azure_activation_runner": runner}), redirect_stdout(stdout):
            rc = nac_cli.main(self._argv("--confirm-unlock", "--format", "json"))
        self.assertEqual(rc, 0)
        self.assertTrue(reconcile.call_args.kwargs["confirm_unlock"])
        payload = json.loads(stdout.getvalue())
        self.assertFalse(payload["recovery"]["lock_held"])
        self.assertEqual(payload["recovery"]["reconcile_marker_sha256"], "0" * 64)

    def test_recovery_error_is_redacted_without_traceback(self) -> None:
        runner, reconcile = self._fake_runner(code="FINALIZATION_RECOVERY_REQUIRED")
        reconcile.side_effect = RuntimeError("secret-provider-detail")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with (
            patch.dict(sys.modules, {"nac_bff.azure_activation_runner": runner}),
            redirect_stdout(stdout),
            redirect_stderr(stderr),
        ):
            rc = nac_cli.main(self._argv("--format", "json"))
        self.assertEqual(rc, 2)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(
            json.loads(stdout.getvalue())["error"]["code"],
            "FINALIZATION_RECOVERY_RUNTIME_UNAVAILABLE",
        )
        self.assertNotIn("secret-provider-detail", stdout.getvalue())

    def test_recovery_does_not_expose_resume_or_output_root(self) -> None:
        for option, value in (("--resume", None), ("--output-root", "/tmp/other")):
            with self.subTest(option=option):
                argv = self._argv(option, *([] if value is None else [value]))
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
                    nac_cli.main(argv)
                self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
