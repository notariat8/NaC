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
from nac_m365_graph.runtime_env_bootstrap import build_runtime_env_bootstrap  # noqa: E402


class M365RuntimeEnvBootstrapTests(unittest.TestCase):
    def test_builds_overlay_from_non_secret_state_without_serializing_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            certificate_path.touch()
            private_key_path.touch()

            bootstrap = build_runtime_env_bootstrap(
                _runtime_state(),
                certificate_path=certificate_path,
                private_key_path=private_key_path,
                env={},
                now_utc="2026-07-07T11:00:00Z",
            )

        self.assertEqual(bootstrap.readiness["status"], "PASSED")
        self.assertEqual(
            bootstrap.env_overlay,
            {
                "M365_TENANT_ID": "tenant-guid",
                "M365_RUNTIME_CLIENT_ID": "runtime-client-guid",
                "M365_RUNTIME_CLIENT_CERTIFICATE_PATH": str(certificate_path),
                "M365_RUNTIME_CLIENT_KEY_PATH": str(private_key_path),
            },
        )
        summary = bootstrap.readiness["summary"]
        self.assertEqual(summary["env_overlay_variable_count"], 4)
        self.assertTrue(summary["certificate_file_exists"])
        self.assertTrue(summary["private_key_file_exists"])
        self.assertFalse(summary["tenant_id_emitted"])
        self.assertFalse(summary["client_id_emitted"])
        self.assertFalse(summary["certificate_thumbprint_emitted"])
        self.assertFalse(summary["credential_files_read"])
        self.assertFalse(summary["secret_env_values_read"])
        self.assertFalse(summary["executes_graph_requests"])
        self.assertFalse(summary["executes_graph_writes"])
        serialized = json.dumps(bootstrap.readiness)
        self.assertNotIn("tenant-guid", serialized)
        self.assertNotIn("runtime-client-guid", serialized)
        self.assertNotIn("ABCDEF123456", serialized)

    def test_existing_runtime_token_mode_does_not_force_certificate_overlay(self) -> None:
        bootstrap = build_runtime_env_bootstrap(
            _runtime_state(),
            certificate_path=Path("/missing/runtime.cert.pem"),
            private_key_path=Path("/missing/runtime.key.pem"),
            env={"M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE": "/tmp/runtime-token"},
            now_utc="2026-07-07T11:00:00Z",
        )

        self.assertEqual(bootstrap.env_overlay, {})
        self.assertEqual(bootstrap.readiness["status"], "PASSED")
        self.assertEqual(bootstrap.readiness["summary"]["explicit_runtime_credential_mode"], "access_token")
        self.assertFalse(bootstrap.readiness["summary"]["certificate_file_exists"])
        self.assertFalse(bootstrap.readiness["summary"]["private_key_file_exists"])

    def test_partial_certificate_env_is_completed_from_state_and_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            certificate_path = tmp_path / "default-runtime.cert.pem"
            private_key_path = tmp_path / "default-runtime.key.pem"
            certificate_path.touch()
            private_key_path.touch()
            bootstrap = build_runtime_env_bootstrap(
                _runtime_state(),
                certificate_path=certificate_path,
                private_key_path=private_key_path,
                env={"M365_RUNTIME_CLIENT_CERTIFICATE_PATH": "/explicit/runtime.cert.pem"},
                now_utc="2026-07-07T11:00:00Z",
            )

        self.assertEqual(bootstrap.readiness["status"], "PASSED")
        self.assertEqual(bootstrap.readiness["summary"]["explicit_runtime_credential_mode"], "client_certificate")
        self.assertNotIn("M365_RUNTIME_CLIENT_CERTIFICATE_PATH", bootstrap.env_overlay)
        self.assertEqual(bootstrap.env_overlay["M365_TENANT_ID"], "tenant-guid")
        self.assertEqual(bootstrap.env_overlay["M365_RUNTIME_CLIENT_ID"], "runtime-client-guid")
        self.assertEqual(bootstrap.env_overlay["M365_RUNTIME_CLIENT_KEY_PATH"], str(private_key_path))

    def test_cli_writes_redacted_runtime_env_bootstrap_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_path = tmp_path / "runtime-state.json"
            output_path = tmp_path / "runtime-env-bootstrap.redacted.json"
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            state_path.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            certificate_path.touch()
            private_key_path.touch()

            parser = cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "runtime-env-bootstrap",
                    "--runtime-smoke-state",
                    str(state_path),
                    "--runtime-certificate-path",
                    str(certificate_path),
                    "--runtime-private-key-path",
                    str(private_key_path),
                    "--runtime-env-bootstrap-output",
                    str(output_path),
                    "--format",
                    "json",
                ]
            )
            stdout = StringIO()
            with redirect_stdout(stdout):
                return_code = args.func(args)

            payload = json.loads(stdout.getvalue())
            artifact = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(artifact["schema_version"], "nac.m365-runtime-env-bootstrap/v0.1")
        serialized = json.dumps(artifact)
        self.assertNotIn("tenant-guid", serialized)
        self.assertNotIn("runtime-client-guid", serialized)
        self.assertNotIn("ABCDEF123456", serialized)

    def test_matter_access_apply_smoke_child_receives_runtime_env_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_path = tmp_path / "runtime-state.json"
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            state_path.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            certificate_path.touch()
            private_key_path.touch()

            parser = cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "matter-access-apply-smoke",
                    "--owner-approved",
                    "--runtime-smoke-state",
                    str(state_path),
                    "--runtime-certificate-path",
                    str(certificate_path),
                    "--runtime-private-key-path",
                    str(private_key_path),
                    "--mcp-smoke-workspace-id",
                    "notary_team_01",
                    "--mcp-smoke-correlation-id",
                    "nac-test",
                    "--format",
                    "json",
                ]
            )
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps({"status": "PASSED"}) + "\n",
                stderr="",
            )
            with patch("nac_cli.cli.subprocess.run", return_value=completed) as run_mock:
                stdout = StringIO()
                with redirect_stdout(stdout):
                    return_code = args.func(args)

            child_env = run_mock.call_args.kwargs["env"]

        self.assertEqual(return_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "PASSED")
        self.assertEqual(child_env["M365_TENANT_ID"], "tenant-guid")
        self.assertEqual(child_env["M365_RUNTIME_CLIENT_ID"], "runtime-client-guid")
        self.assertEqual(child_env["M365_RUNTIME_CLIENT_CERTIFICATE_PATH"], str(certificate_path))
        self.assertEqual(child_env["M365_RUNTIME_CLIENT_KEY_PATH"], str(private_key_path))

    def test_matter_access_apply_smoke_child_preserves_explicit_runtime_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            state_path = tmp_path / "runtime-state.json"
            certificate_path = tmp_path / "runtime.cert.pem"
            private_key_path = tmp_path / "runtime.key.pem"
            state_path.write_text(json.dumps(_runtime_state()), encoding="utf-8")
            certificate_path.touch()
            private_key_path.touch()

            parser = cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "matter-access-apply-smoke",
                    "--owner-approved",
                    "--runtime-smoke-state",
                    str(state_path),
                    "--runtime-certificate-path",
                    str(certificate_path),
                    "--runtime-private-key-path",
                    str(private_key_path),
                    "--mcp-smoke-workspace-id",
                    "notary_team_01",
                    "--mcp-smoke-correlation-id",
                    "nac-test",
                    "--format",
                    "json",
                ]
            )
            explicit_env = {
                "M365_TENANT_ID": "explicit-tenant",
                "M365_RUNTIME_CLIENT_ID": "explicit-client",
                "M365_RUNTIME_CLIENT_CERTIFICATE_PATH": "/explicit/runtime.cert.pem",
                "M365_RUNTIME_CLIENT_KEY_PATH": "/explicit/runtime.key.pem",
            }
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps({"status": "PASSED"}) + "\n",
                stderr="",
            )
            with patch.dict(cli.os.environ, explicit_env, clear=True):
                with patch("nac_cli.cli.subprocess.run", return_value=completed) as run_mock:
                    stdout = StringIO()
                    with redirect_stdout(stdout):
                        return_code = args.func(args)

                child_env = run_mock.call_args.kwargs.get("env")

        self.assertEqual(return_code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "PASSED")
        self.assertIsNone(child_env)


def _runtime_state() -> dict:
    return {
        "state_version": "nac.m365-runtime-smoke/v0.1",
        "tenant": {
            "display_name": "f8",
            "tenant_id": "tenant-guid",
            "primary_domain": "example.invalid",
        },
        "runtime_application": {
            "display_name": "NaC M365 Runtime",
            "client_id": "runtime-client-guid",
            "certificate_thumbprint_sha1": "ABCDEF123456",
            "certificate_expires_at_utc": "2027-07-07T07:22:21Z",
            "authentication_mode": "client_credentials_with_certificate",
            "application_permissions": ["Sites.Selected"],
        },
    }


if __name__ == "__main__":
    unittest.main()
