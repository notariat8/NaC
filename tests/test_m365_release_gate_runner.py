from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli  # noqa: E402


class M365ReleaseGateRunnerTests(unittest.TestCase):
    def test_release_gate_run_blocks_without_owner_approval(self) -> None:
        payload, return_code = _invoke_release_gate_run(
            [
                "--format",
                "json",
            ]
        )

        self.assertEqual(return_code, 2)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("requires --owner-approved", payload["errors"][0])

    def test_release_gate_run_executes_fixed_sequence(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            step = command[command.index("teams-sharepoint") + 1]
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"status": "PASSED", "step": step}),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            certificate_path.touch()
            private_key_path.touch()
            with patch.object(cli.subprocess, "run", side_effect=fake_run):
                payload, return_code = _invoke_release_gate_run(
                    [
                        "--owner-approved",
                        "--mcp-smoke-workspace-id",
                        "notary_team_01",
                        "--mcp-smoke-correlation-id",
                        "runner-corr",
                        "--release-gate-inventory-artifact",
                        "out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json",
                        "--runtime-certificate-path",
                        str(certificate_path),
                        "--runtime-private-key-path",
                        str(private_key_path),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(
            [step["step"] for step in payload["steps"]],
            [
                "runtime_certificate_expiry",
                "runtime_smoke",
                "runtime_metadata",
                "mcp_smoke_suite",
                "mcp_leftover_dry_run",
                "release_gate_evidence",
            ],
        )
        invoked_steps = [call[call.index("teams-sharepoint") + 1] for call in calls]
        self.assertEqual(
            invoked_steps,
            [
                "runtime-certificate-expiry-monitor",
                "runtime-smoke",
                "runtime-metadata",
                "mcp-smoke-suite",
                "mcp-smoke-leftover-cleanup",
                "release-gate-evidence",
            ],
        )
        self.assertIn("--runtime-certificate-expiry-output", calls[0])
        self.assertIn("--mcp-suite-cleanup", calls[3])
        self.assertIn("--mcp-leftover-dry-run", calls[4])
        self.assertIn("--release-gate-require-runtime-artifacts", calls[5])
        self.assertIn("--release-gate-inventory-artifact", calls[5])
        self.assertIn("--release-gate-runtime-certificate-expiry-artifact", calls[5])
        self.assertEqual(payload["summary"]["correlation_id"], "runner-corr")

    def test_release_gate_run_bootstraps_runtime_env_for_live_steps(self) -> None:
        calls: list[tuple[str, dict[str, str] | None]] = []
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runtime_state = tmp_path / "runtime-state.json"
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            runtime_state.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            certificate_path.touch()
            private_key_path.touch()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                step = command[command.index("teams-sharepoint") + 1]
                calls.append((step, kwargs.get("env")))  # type: ignore[arg-type]
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps({"status": "PASSED", "step": step}),
                    stderr="",
                )

            with patch.object(cli.subprocess, "run", side_effect=fake_run), patch.dict(cli.os.environ, {}, clear=True):
                payload, return_code = _invoke_release_gate_run(
                    [
                        "--owner-approved",
                        "--runtime-smoke-state",
                        str(runtime_state),
                        "--runtime-certificate-path",
                        str(certificate_path),
                        "--runtime-private-key-path",
                        str(private_key_path),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_status"], "PASSED")
        self.assertEqual(
            payload["summary"]["runtime_env_overlay_variable_names"],
            [
                "M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
                "M365_RUNTIME_CLIENT_ID",
                "M365_RUNTIME_CLIENT_KEY_PATH",
                "M365_TENANT_ID",
            ],
        )
        env_by_step = dict(calls)
        self.assertIsNone(env_by_step["runtime-certificate-expiry-monitor"])
        self.assertIsNone(env_by_step["release-gate-evidence"])
        for step in (
            "runtime-smoke",
            "runtime-metadata",
            "mcp-smoke-suite",
            "mcp-smoke-leftover-cleanup",
        ):
            env = env_by_step[step]
            self.assertIsNotNone(env)
            assert env is not None
            self.assertEqual(env["M365_TENANT_ID"], "tenant-guid")
            self.assertEqual(env["M365_RUNTIME_CLIENT_ID"], "runtime-client-guid")
            self.assertEqual(env["M365_RUNTIME_CLIENT_CERTIFICATE_PATH"], str(certificate_path))
            self.assertEqual(env["M365_RUNTIME_CLIENT_KEY_PATH"], str(private_key_path))

    def test_release_gate_run_blocks_before_live_steps_when_runtime_env_needs_review(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"status": "PASSED"}), stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runtime_state = tmp_path / "runtime-state.json"
            runtime_state.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            with patch.object(cli.subprocess, "run", side_effect=fake_run):
                payload, return_code = _invoke_release_gate_run(
                    [
                        "--owner-approved",
                        "--runtime-smoke-state",
                        str(runtime_state),
                        "--runtime-certificate-path",
                        str(tmp_path / "missing.cert.pem"),
                        "--runtime-private-key-path",
                        str(tmp_path / "missing.key.pem"),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(return_code, 2)
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["summary"]["failed_step"], "runtime_env_bootstrap")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_status"], "REVIEW_REQUIRED")
        self.assertEqual(payload["steps"], [])
        self.assertEqual(calls, [])

    def test_release_gate_run_stops_on_failed_step(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            step = command[command.index("teams-sharepoint") + 1]
            if step == "runtime-metadata":
                return subprocess.CompletedProcess(
                    command,
                    1,
                    stdout=json.dumps({"status": "FAILED", "errors": ["metadata failed"]}),
                    stderr="",
                )
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"status": "PASSED"}), stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            certificate_path.touch()
            private_key_path.touch()
            with patch.object(cli.subprocess, "run", side_effect=fake_run):
                payload, return_code = _invoke_release_gate_run(
                    [
                        "--owner-approved",
                        "--mcp-smoke-correlation-id",
                        "runner-corr",
                        "--runtime-certificate-path",
                        str(certificate_path),
                        "--runtime-private-key-path",
                        str(private_key_path),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(return_code, 1)
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["summary"]["failed_step"], "runtime_metadata")
        self.assertEqual(payload["summary"]["steps_completed"], 2)
        self.assertEqual(payload["errors"], ["metadata failed"])
        self.assertEqual(len(calls), 3)


def _invoke_release_gate_run(extra_args: list[str]) -> tuple[dict, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "release-gate-run",
            *extra_args,
        ]
    )
    output = StringIO()
    with redirect_stdout(output):
        return_code = args.func(args)
    return json.loads(output.getvalue()), return_code


def _runtime_state() -> dict:
    return {
        "state_version": "nac.m365-runtime-smoke/v0.1",
        "tenant": {"tenant_id": "tenant-guid"},
        "runtime_application": {
            "client_id": "runtime-client-guid",
            "authentication_mode": "client_credentials_with_certificate",
        },
    }


if __name__ == "__main__":
    unittest.main()
