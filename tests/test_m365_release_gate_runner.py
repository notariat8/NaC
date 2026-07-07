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
            _write_release_gate_output_args(command)
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
            runtime_env_bootstrap_output = tmp_path / "runtime-env-bootstrap.redacted.json"
            retention_dir = tmp_path / "release-gate-run"
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
                        "--runtime-env-bootstrap-output",
                        str(runtime_env_bootstrap_output),
                        "--release-gate-run-artifact-dir",
                        str(retention_dir),
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
        inventory_arg_index = calls[5].index("--release-gate-inventory-artifact") + 1
        self.assertTrue(calls[5][inventory_arg_index].endswith("mcp-inventory-smoke.redacted.json"))
        self.assertIn("--release-gate-runtime-certificate-expiry-artifact", calls[5])
        self.assertIn("--release-gate-runtime-env-bootstrap-artifact", calls[5])
        bootstrap_arg_index = calls[5].index("--release-gate-runtime-env-bootstrap-artifact") + 1
        self.assertEqual(calls[5][bootstrap_arg_index], str(runtime_env_bootstrap_output))
        self.assertEqual(payload["summary"]["correlation_id"], "runner-corr")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_artifact"], str(runtime_env_bootstrap_output))
        self.assertEqual(payload["summary"]["release_gate_run_artifact_dir"], str(retention_dir))
        self.assertTrue(payload["summary"]["release_gate_retention_index"].endswith("release-gate-retention-index.redacted.json"))

    def test_release_gate_run_pins_missing_inventory_artifact_when_not_explicitly_attached(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            step = command[command.index("teams-sharepoint") + 1]
            _write_release_gate_output_args(command)
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
            runtime_env_bootstrap_output = tmp_path / "runtime-env-bootstrap.redacted.json"
            retention_dir = tmp_path / "release-gate-run"
            certificate_path.touch()
            private_key_path.touch()
            with patch.object(cli.subprocess, "run", side_effect=fake_run):
                payload, return_code = _invoke_release_gate_run(
                    [
                        "--owner-approved",
                        "--runtime-certificate-path",
                        str(certificate_path),
                        "--runtime-private-key-path",
                        str(private_key_path),
                        "--runtime-env-bootstrap-output",
                        str(runtime_env_bootstrap_output),
                        "--release-gate-run-artifact-dir",
                        str(retention_dir),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        evidence_call = calls[5]
        self.assertIn("--release-gate-inventory-artifact", evidence_call)
        inventory_arg_index = evidence_call.index("--release-gate-inventory-artifact") + 1
        self.assertTrue(evidence_call[inventory_arg_index].endswith("mcp-inventory-smoke.not-attached.redacted.json"))

    def test_release_gate_run_writes_retention_index_with_run_artifact_copies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runtime_state = tmp_path / "runtime-state.json"
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            runtime_env_bootstrap_output = tmp_path / "runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_output = tmp_path / "runtime-certificate-expiry-monitor.redacted.json"
            runtime_smoke_output = tmp_path / "runtime-smoke.redacted.json"
            runtime_metadata_output = tmp_path / "runtime-metadata.redacted.json"
            mcp_suite_output = tmp_path / "mcp-smoke-suite.redacted.json"
            mcp_leftover_output = tmp_path / "mcp-smoke-leftover-cleanup.redacted.json"
            evidence_output = tmp_path / "release-gate-evidence.redacted.md"
            evidence_json_output = tmp_path / "release-gate-evidence.redacted.json"
            artifact_index_output = tmp_path / "release-gate-artifact-index.redacted.json"
            retention_dir = tmp_path / "retained"
            runtime_state.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            certificate_path.touch()
            private_key_path.touch()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                step = command[command.index("teams-sharepoint") + 1]
                _write_output_arg(command, "--runtime-certificate-expiry-output", {"status": "PASSED", "step": step})
                _write_output_arg(command, "--runtime-smoke-output", {"status": "PASSED", "step": step})
                _write_output_arg(command, "--runtime-metadata-output", {"status": "PASSED", "step": step})
                _write_output_arg(command, "--mcp-suite-output", {"status": "PASSED", "step": step})
                _write_output_arg(command, "--mcp-leftover-output", {"status": "PASSED", "step": step})
                if "--release-gate-evidence-output" in command:
                    evidence_output.write_text("# redacted evidence\n", encoding="utf-8")
                    evidence_json_output.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")
                    artifact_index_output.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")
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
                        "--mcp-smoke-correlation-id",
                        "retention-corr",
                        "--runtime-smoke-state",
                        str(runtime_state),
                        "--runtime-certificate-path",
                        str(certificate_path),
                        "--runtime-private-key-path",
                        str(private_key_path),
                        "--runtime-env-bootstrap-output",
                        str(runtime_env_bootstrap_output),
                        "--runtime-certificate-expiry-output",
                        str(runtime_certificate_expiry_output),
                        "--runtime-smoke-output",
                        str(runtime_smoke_output),
                        "--runtime-metadata-output",
                        str(runtime_metadata_output),
                        "--mcp-suite-output",
                        str(mcp_suite_output),
                        "--mcp-leftover-output",
                        str(mcp_leftover_output),
                        "--release-gate-evidence-output",
                        str(evidence_output),
                        "--release-gate-evidence-json-output",
                        str(evidence_json_output),
                        "--release-gate-artifact-index-output",
                        str(artifact_index_output),
                        "--release-gate-run-artifact-dir",
                        str(retention_dir),
                        "--format",
                        "json",
                    ]
                )

            retention_index = json.loads((retention_dir / "release-gate-retention-index.redacted.json").read_text())
            retained_evidence_json = json.loads((retention_dir / "release-gate-evidence.redacted.json").read_text())
            retained_artifact_index = json.loads((retention_dir / "release-gate-artifact-index.redacted.json").read_text())
            retained_report = (retention_dir / "release-gate-evidence.redacted.md").read_text()
            retained_bootstrap_exists = (retention_dir / "runtime-env-bootstrap.redacted.json").exists()
            retained_evidence_json_exists = (retention_dir / "release-gate-evidence.redacted.json").exists()

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["release_gate_run_artifact_dir"], str(retention_dir))
        self.assertEqual(payload["summary"]["release_gate_retention_index"], str(retention_dir / "release-gate-retention-index.redacted.json"))
        self.assertEqual(retention_index["schema_version"], "nac.m365-release-gate-retention-index/v0.1")
        self.assertEqual(retention_index["correlation_id"], "retention-corr")
        self.assertFalse(retention_index["privacy"]["storesTokensOrSecrets"])
        self.assertEqual(
            retained_evidence_json["summary"]["release_gate_retention_index_path"],
            str(retention_dir / "release-gate-retention-index.redacted.json"),
        )
        self.assertEqual(retained_evidence_json["summary"]["retained_artifact_count"], 9)
        self.assertTrue(retained_evidence_json["summary"]["retention_index_attached"])
        self.assertEqual(
            retained_artifact_index["retention"]["retention_index_path"],
            str(retention_dir / "release-gate-retention-index.redacted.json"),
        )
        self.assertTrue(retained_artifact_index["retention"]["attached"])
        self.assertIn("## Artifact Retention", retained_report)
        self.assertIn("release-gate-retention-index.redacted.json", retained_report)
        artifacts = {artifact["id"]: artifact for artifact in retention_index["artifacts"]}
        self.assertEqual(artifacts["runtime_env_bootstrap"]["status"], "COPIED")
        self.assertEqual(len(artifacts["runtime_env_bootstrap"]["artifact_sha256"]), 64)
        self.assertEqual(artifacts["mcp_inventory_smoke"]["status"], "NOT_ATTACHED")
        self.assertEqual(artifacts["mcp_inventory_smoke"]["artifact_sha256"], None)
        self.assertTrue(retained_bootstrap_exists)
        self.assertTrue(retained_evidence_json_exists)

    def test_release_gate_run_bootstraps_runtime_env_for_live_steps(self) -> None:
        calls: list[tuple[str, dict[str, str] | None]] = []
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            runtime_state = tmp_path / "runtime-state.json"
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            runtime_env_bootstrap_output = tmp_path / "runtime-env-bootstrap.redacted.json"
            retention_dir = tmp_path / "release-gate-run"
            runtime_state.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            certificate_path.touch()
            private_key_path.touch()

            def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                step = command[command.index("teams-sharepoint") + 1]
                calls.append((step, kwargs.get("env")))  # type: ignore[arg-type]
                _write_release_gate_output_args(command)
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
                        "--runtime-env-bootstrap-output",
                        str(runtime_env_bootstrap_output),
                        "--release-gate-run-artifact-dir",
                        str(retention_dir),
                        "--format",
                        "json",
                    ]
                )
                bootstrap_artifact = json.loads(runtime_env_bootstrap_output.read_text(encoding="utf-8"))

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_status"], "PASSED")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_artifact"], str(runtime_env_bootstrap_output))
        self.assertEqual(bootstrap_artifact["status"], "PASSED")
        self.assertEqual(bootstrap_artifact["summary"]["artifact_path"], str(runtime_env_bootstrap_output))
        self.assertFalse(bootstrap_artifact["summary"]["tenant_id_emitted"])
        self.assertFalse(bootstrap_artifact["summary"]["client_id_emitted"])
        self.assertFalse(bootstrap_artifact["summary"]["credential_files_read"])
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
            runtime_env_bootstrap_output = tmp_path / "runtime-env-bootstrap.redacted.json"
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
                        "--runtime-env-bootstrap-output",
                        str(runtime_env_bootstrap_output),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(return_code, 2)
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["summary"]["failed_step"], "runtime_env_bootstrap")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_status"], "REVIEW_REQUIRED")
        self.assertEqual(payload["summary"]["runtime_env_bootstrap_artifact"], str(runtime_env_bootstrap_output))
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
            runtime_env_bootstrap_output = tmp_path / "runtime-env-bootstrap.redacted.json"
            retention_dir = tmp_path / "release-gate-run"
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
                        "--runtime-env-bootstrap-output",
                        str(runtime_env_bootstrap_output),
                        "--release-gate-run-artifact-dir",
                        str(retention_dir),
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

    def test_release_gate_retention_list_reads_local_run_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            retention_root = tmp_path / "release-gates"
            run_dir = retention_root / "corr-b"
            run_dir.mkdir(parents=True)
            (run_dir / "release-gate-retention-index.redacted.json").write_text(
                json.dumps(
                    {
                        "schema_version": "nac.m365-release-gate-retention-index/v0.1",
                        "status": "PASSED",
                        "workspace_id": "notary_team_01",
                        "correlation_id": "corr-b",
                        "artifact_dir": str(run_dir),
                        "copied_artifact_count": 2,
                        "artifacts": [
                            {"id": "runtime_smoke", "status": "COPIED"},
                            {"id": "mcp_inventory_smoke", "status": "NOT_ATTACHED"},
                        ],
                        "privacy": {"storesTokensOrSecrets": False},
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "release-gate-evidence.redacted.json").write_text(
                json.dumps(
                    {
                        "schema_version": "nac.m365-release-gate-evidence/v0.1",
                        "status": "PASSED",
                        "generated_at": "2026-07-07T12:07:57Z",
                    }
                ),
                encoding="utf-8",
            )

            payload, return_code = _invoke_retention_list(
                [
                    "--release-gate-retention-root",
                    str(retention_root),
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["run_count"], 1)
        self.assertEqual(payload["summary"]["invalid_run_count"], 0)
        self.assertFalse(payload["summary"]["graph_requests_executed"])
        self.assertEqual(payload["runs"][0]["correlation_id"], "corr-b")
        self.assertEqual(payload["runs"][0]["timestamp"], "2026-07-07T12:07:57Z")
        self.assertEqual(payload["runs"][0]["copied_artifact_count"], 2)
        self.assertEqual(payload["runs"][0]["not_attached_artifact_count"], 1)
        self.assertTrue(payload["runs"][0]["retention_index_path"].endswith("release-gate-retention-index.redacted.json"))
        self.assertFalse(payload["runs"][0]["privacy"]["storesTokensOrSecrets"])

    def test_release_gate_retention_list_allows_empty_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload, return_code = _invoke_retention_list(
                [
                    "--release-gate-retention-root",
                    str(Path(tmp) / "missing-release-gates"),
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["run_count"], 0)
        self.assertEqual(payload["runs"], [])

    def test_release_gate_retention_compare_reports_differences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            retention_root = Path(tmp) / "release-gates"
            _write_retention_run(
                retention_root / "corr-left",
                correlation_id="corr-left",
                generated_at="2026-07-07T12:00:00Z",
                copied_artifact_count=1,
                artifacts=[
                    {"id": "runtime_smoke", "status": "COPIED", "artifact_sha256": "aaa"},
                    {"id": "mcp_inventory_smoke", "status": "NOT_ATTACHED", "artifact_sha256": None},
                    {"id": "runtime_metadata", "status": "COPIED", "artifact_sha256": "bbb"},
                ],
            )
            _write_retention_run(
                retention_root / "corr-right",
                correlation_id="corr-right",
                generated_at="2026-07-07T12:30:00Z",
                copied_artifact_count=3,
                artifacts=[
                    {"id": "runtime_smoke", "status": "COPIED", "artifact_sha256": "changed"},
                    {"id": "mcp_inventory_smoke", "status": "COPIED", "artifact_sha256": "inventory"},
                    {"id": "mcp_smoke_suite", "status": "COPIED", "artifact_sha256": "suite"},
                ],
            )

            payload, return_code = _invoke_retention_compare(
                [
                    "--release-gate-retention-root",
                    str(retention_root),
                    "--release-gate-compare-left",
                    "corr-left",
                    "--release-gate-compare-right",
                    "corr-right",
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(payload["summary"]["differences_found"])
        self.assertEqual(payload["summary"]["left_correlation_id"], "corr-left")
        self.assertEqual(payload["summary"]["right_correlation_id"], "corr-right")
        self.assertFalse(payload["summary"]["graph_requests_executed"])
        self.assertGreater(payload["summary"]["difference_count"], 0)
        self.assertIn(
            {"field": "copied_artifact_count", "left": 1, "right": 3},
            payload["comparison"]["fields"],
        )
        self.assertEqual(payload["comparison"]["artifacts"]["added_in_right"], ["mcp_smoke_suite"])
        self.assertEqual(payload["comparison"]["artifacts"]["removed_in_right"], ["runtime_metadata"])
        self.assertEqual(
            {artifact["id"] for artifact in payload["comparison"]["artifacts"]["changed"]},
            {"mcp_inventory_smoke", "runtime_smoke"},
        )
        self.assertEqual(payload["comparison"]["missing_attachments"]["resolved_in_right"], ["mcp_inventory_smoke"])
        self.assertEqual(payload["comparison"]["missing_attachments"]["newly_missing_in_right"], [])
        self.assertFalse(payload["comparison"]["privacy"]["storesTokensOrSecrets"])

    def test_release_gate_retention_compare_blocks_without_references(self) -> None:
        payload, return_code = _invoke_retention_compare(["--format", "json"])

        self.assertEqual(return_code, 2)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("left release gate reference is required", payload["errors"][0])

    def test_release_gate_retention_compare_artifact_writes_redacted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            retention_root = tmp_path / "release-gates"
            report_path = tmp_path / "compare" / "compare.redacted.md"
            json_path = tmp_path / "compare" / "compare.redacted.json"
            _write_retention_run(
                retention_root / "corr-left",
                correlation_id="corr-left",
                generated_at="2026-07-07T12:00:00Z",
                copied_artifact_count=1,
                artifacts=[
                    {"id": "runtime_smoke", "status": "COPIED", "artifact_sha256": "aaa"},
                    {"id": "mcp_inventory_smoke", "status": "NOT_ATTACHED", "artifact_sha256": None},
                ],
            )
            _write_retention_run(
                retention_root / "corr-right",
                correlation_id="corr-right",
                generated_at="2026-07-07T12:30:00Z",
                copied_artifact_count=2,
                artifacts=[
                    {"id": "runtime_smoke", "status": "COPIED", "artifact_sha256": "changed"},
                    {"id": "mcp_inventory_smoke", "status": "COPIED", "artifact_sha256": "inventory"},
                ],
            )

            payload, return_code = _invoke_retention_compare_artifact(
                [
                    "--release-gate-retention-root",
                    str(retention_root),
                    "--release-gate-compare-left",
                    "corr-left",
                    "--release-gate-compare-right",
                    "corr-right",
                    "--release-gate-compare-output",
                    str(report_path),
                    "--release-gate-compare-json-output",
                    str(json_path),
                    "--format",
                    "json",
                ]
            )
            report = report_path.read_text(encoding="utf-8")
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["schema_version"], "nac.m365-release-gate-retention-compare-artifact/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["report_path"], str(report_path))
        self.assertEqual(payload["summary"]["json_path"], str(json_path))
        self.assertFalse(payload["summary"]["graph_requests_executed"])
        self.assertFalse(payload["summary"]["reads_sharepoint_file_content"])
        self.assertTrue(report.startswith("# M365 Release Gate Retention Compare"))
        self.assertIn("Left correlation ID: corr-left", report)
        self.assertIn("Resolved in right: mcp_inventory_smoke", report)
        self.assertEqual(json_payload["summary"]["left_correlation_id"], "corr-left")
        self.assertEqual(json_payload["summary"]["right_correlation_id"], "corr-right")
        self.assertFalse(json_payload["comparison"]["privacy"]["storesTokensOrSecrets"])

    def test_release_gate_retention_compare_index_lists_and_filters_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            compare_root = Path(tmp) / "comparisons"
            _write_compare_artifact(
                compare_root / "left-a__right-a",
                left_correlation_id="left-a",
                right_correlation_id="right-a",
                status="PASSED",
                generated_at="2026-07-07T12:00:00Z",
                difference_count=3,
            )
            _write_compare_artifact(
                compare_root / "left-b__right-b",
                left_correlation_id="left-b",
                right_correlation_id="right-b",
                status="FAILED",
                generated_at="2026-07-07T13:00:00Z",
                difference_count=7,
            )

            payload, return_code = _invoke_retention_compare_index(
                [
                    "--release-gate-compare-index-root",
                    str(compare_root),
                    "--format",
                    "json",
                ]
            )
            left_filtered, left_return_code = _invoke_retention_compare_index(
                [
                    "--release-gate-compare-index-root",
                    str(compare_root),
                    "--release-gate-compare-left",
                    "left-a",
                    "--format",
                    "json",
                ]
            )
            query_filtered, query_return_code = _invoke_retention_compare_index(
                [
                    "--release-gate-compare-index-root",
                    str(compare_root),
                    "--release-gate-compare-query",
                    "left-b__right-b",
                    "--release-gate-compare-status",
                    "FAILED",
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["comparison_count"], 2)
        self.assertEqual(payload["summary"]["invalid_artifact_count"], 0)
        self.assertFalse(payload["summary"]["graph_requests_executed"])
        self.assertEqual(payload["comparisons"][0]["left_correlation_id"], "left-b")
        self.assertEqual(payload["comparisons"][0]["status"], "FAILED")
        self.assertEqual(payload["comparisons"][0]["difference_count"], 7)
        self.assertTrue(payload["comparisons"][0]["report_path"].endswith("release-gate-retention-compare.redacted.md"))
        self.assertFalse(payload["comparisons"][0]["privacy"]["storesTokensOrSecrets"])
        self.assertEqual(left_return_code, 0)
        self.assertEqual(left_filtered["summary"]["comparison_count"], 1)
        self.assertEqual(left_filtered["comparisons"][0]["right_correlation_id"], "right-a")
        self.assertEqual(query_return_code, 0)
        self.assertEqual(query_filtered["summary"]["comparison_count"], 1)
        self.assertEqual(query_filtered["comparisons"][0]["left_correlation_id"], "left-b")

    def test_release_gate_retention_compare_index_allows_empty_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload, return_code = _invoke_retention_compare_index(
                [
                    "--release-gate-compare-index-root",
                    str(Path(tmp) / "missing-comparisons"),
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["comparison_count"], 0)
        self.assertEqual(payload["comparisons"], [])

    def test_release_gate_retention_compare_index_artifact_writes_redacted_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            compare_root = tmp_path / "comparisons"
            report_path = tmp_path / "index" / "compare-index.redacted.md"
            json_path = tmp_path / "index" / "compare-index.redacted.json"
            _write_compare_artifact(
                compare_root / "left-a__right-a",
                left_correlation_id="left-a",
                right_correlation_id="right-a",
                status="PASSED",
                generated_at="2026-07-07T12:00:00Z",
                difference_count=3,
            )
            _write_compare_artifact(
                compare_root / "left-b__right-b",
                left_correlation_id="left-b",
                right_correlation_id="right-b",
                status="FAILED",
                generated_at="2026-07-07T13:00:00Z",
                difference_count=7,
            )

            payload, return_code = _invoke_retention_compare_index_artifact(
                [
                    "--release-gate-compare-index-root",
                    str(compare_root),
                    "--release-gate-compare-query",
                    "left-b__right-b",
                    "--release-gate-compare-status",
                    "FAILED",
                    "--release-gate-compare-index-output",
                    str(report_path),
                    "--release-gate-compare-index-json-output",
                    str(json_path),
                    "--format",
                    "json",
                ]
            )
            report = report_path.read_text(encoding="utf-8")
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["schema_version"], "nac.m365-release-gate-retention-compare-index-artifact/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["comparison_count"], 1)
        self.assertEqual(payload["summary"]["status_filter"], "FAILED")
        self.assertEqual(payload["summary"]["report_path"], str(report_path))
        self.assertEqual(payload["summary"]["json_path"], str(json_path))
        self.assertFalse(payload["summary"]["graph_requests_executed"])
        self.assertFalse(payload["summary"]["reads_sharepoint_file_content"])
        self.assertTrue(report.startswith("# M365 Release Gate Retention Compare Index"))
        self.assertIn("Comparison count: 1", report)
        self.assertIn("| 2026-07-07T13:00:00Z | left-b | right-b | FAILED | 7 |", report)
        self.assertEqual(json_payload["summary"]["query"], "left-b__right-b")
        self.assertEqual(json_payload["comparisons"][0]["left_correlation_id"], "left-b")
        self.assertFalse(json_payload["comparisons"][0]["privacy"]["storesTokensOrSecrets"])

    def test_release_gate_retention_compare_index_artifact_blocks_invalid_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            compare_root = Path(tmp) / "comparisons"
            invalid_dir = compare_root / "broken"
            invalid_dir.mkdir(parents=True)
            (invalid_dir / "release-gate-retention-compare.redacted.json").write_text("{", encoding="utf-8")

            payload, return_code = _invoke_retention_compare_index_artifact(
                [
                    "--release-gate-compare-index-root",
                    str(compare_root),
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(return_code, 2)
        self.assertEqual(payload["schema_version"], "nac.m365-release-gate-retention-compare-index-artifact/v0.1")
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["summary"]["invalid_artifact_count"], 1)
        self.assertEqual(payload["comparisons"], [])
        self.assertTrue(payload["errors"])


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


def _invoke_retention_list(extra_args: list[str]) -> tuple[dict, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "release-gate-retention-list",
            *extra_args,
        ]
    )
    output = StringIO()
    with redirect_stdout(output):
        return_code = args.func(args)
    return json.loads(output.getvalue()), return_code


def _invoke_retention_compare(extra_args: list[str]) -> tuple[dict, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "release-gate-retention-compare",
            *extra_args,
        ]
    )
    output = StringIO()
    with redirect_stdout(output):
        return_code = args.func(args)
    return json.loads(output.getvalue()), return_code


def _invoke_retention_compare_artifact(extra_args: list[str]) -> tuple[dict, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "release-gate-retention-compare-artifact",
            *extra_args,
        ]
    )
    output = StringIO()
    with redirect_stdout(output):
        return_code = args.func(args)
    return json.loads(output.getvalue()), return_code


def _invoke_retention_compare_index(extra_args: list[str]) -> tuple[dict, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "release-gate-retention-compare-index",
            *extra_args,
        ]
    )
    output = StringIO()
    with redirect_stdout(output):
        return_code = args.func(args)
    return json.loads(output.getvalue()), return_code


def _invoke_retention_compare_index_artifact(extra_args: list[str]) -> tuple[dict, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "--repo-root",
            str(REPO_ROOT),
            "m365",
            "teams-sharepoint",
            "release-gate-retention-compare-index-artifact",
            *extra_args,
        ]
    )
    output = StringIO()
    with redirect_stdout(output):
        return_code = args.func(args)
    return json.loads(output.getvalue()), return_code


def _write_retention_run(
    run_dir: Path,
    *,
    correlation_id: str,
    generated_at: str,
    copied_artifact_count: int,
    artifacts: list[dict],
) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "release-gate-retention-index.redacted.json").write_text(
        json.dumps(
            {
                "schema_version": "nac.m365-release-gate-retention-index/v0.1",
                "status": "PASSED",
                "workspace_id": "notary_team_01",
                "correlation_id": correlation_id,
                "artifact_dir": str(run_dir),
                "copied_artifact_count": copied_artifact_count,
                "artifacts": artifacts,
                "privacy": {"storesTokensOrSecrets": False},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "release-gate-evidence.redacted.json").write_text(
        json.dumps(
            {
                "schema_version": "nac.m365-release-gate-evidence/v0.1",
                "status": "PASSED",
                "generated_at": generated_at,
            }
        ),
        encoding="utf-8",
    )


def _write_compare_artifact(
    artifact_dir: Path,
    *,
    left_correlation_id: str,
    right_correlation_id: str,
    status: str,
    generated_at: str,
    difference_count: int,
) -> None:
    artifact_dir.mkdir(parents=True)
    report_path = artifact_dir / "release-gate-retention-compare.redacted.md"
    json_path = artifact_dir / "release-gate-retention-compare.redacted.json"
    report_path.write_text("# M365 Release Gate Retention Compare\n", encoding="utf-8")
    json_path.write_text(
        json.dumps(
            {
                "schema_version": "nac.m365-release-gate-retention-compare-artifact/v0.1",
                "status": status,
                "generated_at": generated_at,
                "summary": {
                    "left_correlation_id": left_correlation_id,
                    "right_correlation_id": right_correlation_id,
                    "differences_found": difference_count > 0,
                    "difference_count": difference_count,
                    "artifact_difference_count": difference_count,
                    "missing_attachment_difference_count": 0,
                    "artifact_directory": str(artifact_dir),
                    "report_path": str(report_path),
                    "json_path": str(json_path),
                    "graph_requests_executed": False,
                    "tenant_writes_executed": False,
                    "tenant_deletes_executed": False,
                    "stores_tokens_or_secrets": False,
                    "reads_sharepoint_file_content": False,
                },
                "comparison": {
                    "privacy": {"storesTokensOrSecrets": False},
                },
            }
        ),
        encoding="utf-8",
    )


def _write_output_arg(command: list[str], option: str, payload: dict) -> None:
    if option not in command:
        return
    output_path = Path(command[command.index(option) + 1])
    output_path.write_text(json.dumps(payload), encoding="utf-8")


def _write_release_gate_output_args(command: list[str]) -> None:
    if "--release-gate-evidence-output" in command:
        output_path = Path(command[command.index("--release-gate-evidence-output") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("# redacted evidence\n", encoding="utf-8")
    if "--release-gate-evidence-json-output" in command:
        output_path = Path(command[command.index("--release-gate-evidence-json-output") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "schema_version": "nac.m365-release-gate-evidence/v0.1",
                    "status": "PASSED",
                    "generated_at": "2026-07-07T11:48:00Z",
                    "summary": {},
                    "steps": [],
                    "errors": [],
                    "privacy": {"storesTokensOrSecrets": False},
                }
            ),
            encoding="utf-8",
        )
    if "--release-gate-artifact-index-output" in command:
        output_path = Path(command[command.index("--release-gate-artifact-index-output") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"status": "PASSED"}), encoding="utf-8")


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
