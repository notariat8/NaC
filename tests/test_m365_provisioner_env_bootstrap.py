from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.provisioner_env_bootstrap import build_provisioner_env_bootstrap  # noqa: E402


class M365ProvisionerEnvBootstrapTests(unittest.TestCase):
    def test_builds_overlay_from_dedicated_provisioning_app_without_serializing_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            certificate_path = tmp_path / "provisioner.cert.pem"
            private_key_path = tmp_path / "provisioner.key.pem"
            certificate_path.touch()
            private_key_path.touch()

            bootstrap = build_provisioner_env_bootstrap(
                _privileged_apply_state(),
                certificate_path=certificate_path,
                private_key_path=private_key_path,
                env={},
                now_utc="2026-07-10T13:30:00Z",
            )

        self.assertEqual(bootstrap.readiness["status"], "PASSED")
        self.assertEqual(
            bootstrap.env_overlay,
            {
                "M365_TENANT_ID": "tenant-guid",
                "M365_PROVISIONER_CLIENT_ID": "provisioner-client-guid",
                "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH": str(certificate_path),
                "M365_PROVISIONER_CLIENT_KEY_PATH": str(private_key_path),
            },
        )
        summary = bootstrap.readiness["summary"]
        self.assertTrue(summary["dedicated_provisioning_app_resolved"])
        self.assertTrue(summary["explicit_client_matches_provisioning_app"])
        self.assertFalse(summary["tenant_id_emitted"])
        self.assertFalse(summary["client_id_emitted"])
        self.assertFalse(summary["credential_files_read"])
        serialized = json.dumps(bootstrap.readiness)
        self.assertNotIn("tenant-guid", serialized)
        self.assertNotIn("provisioner-client-guid", serialized)

    def test_blocks_explicit_cli_app_client_id_before_token_acquisition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            certificate_path = tmp_path / "provisioner.cert.pem"
            private_key_path = tmp_path / "provisioner.key.pem"
            certificate_path.touch()
            private_key_path.touch()

            bootstrap = build_provisioner_env_bootstrap(
                _privileged_apply_state(),
                certificate_path=certificate_path,
                private_key_path=private_key_path,
                env={
                    "M365_TENANT_ID": "tenant-guid",
                    "M365_PROVISIONER_CLIENT_ID": "cli-admin-client-guid",
                    "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH": str(certificate_path),
                    "M365_PROVISIONER_CLIENT_KEY_PATH": str(private_key_path),
                },
                now_utc="2026-07-10T13:30:00Z",
            )

        self.assertEqual(bootstrap.readiness["status"], "BLOCKED")
        self.assertFalse(bootstrap.readiness["summary"]["explicit_client_matches_provisioning_app"])
        self.assertEqual(bootstrap.env_overlay, {})
        self.assertIn(
            "Explicit client ID is not the dedicated provisioning application.",
            bootstrap.readiness["errors"],
        )

    def test_blocks_missing_certificate_files_without_reading_credentials(self) -> None:
        bootstrap = build_provisioner_env_bootstrap(
            _privileged_apply_state(),
            certificate_path=Path("/missing/provisioner.cert.pem"),
            private_key_path=Path("/missing/provisioner.key.pem"),
            env={},
            now_utc="2026-07-10T13:30:00Z",
        )

        self.assertEqual(bootstrap.readiness["status"], "BLOCKED")
        self.assertFalse(bootstrap.readiness["summary"]["certificate_file_exists"])
        self.assertFalse(bootstrap.readiness["summary"]["private_key_file_exists"])
        self.assertFalse(bootstrap.readiness["summary"]["credential_files_read"])

    def test_blocks_missing_privileged_apply_state(self) -> None:
        bootstrap = build_provisioner_env_bootstrap(
            {},
            certificate_path=None,
            private_key_path=None,
            env={},
            now_utc="2026-07-10T13:30:00Z",
        )

        self.assertEqual(bootstrap.readiness["status"], "BLOCKED")
        self.assertFalse(bootstrap.readiness["summary"]["privileged_apply_state_attached"])
        self.assertEqual(bootstrap.env_overlay, {})


def _privileged_apply_state() -> dict:
    return {
        "status": "PASSED",
        "tenantId": "tenant-guid",
        "applications": {
            "m365_provisioning_app": {
                "displayName": "NaC M365 Provisioning",
                "clientId": "provisioner-client-guid",
            },
            "m365_runtime_app": {
                "displayName": "NaC M365 Runtime",
                "clientId": "runtime-client-guid",
            },
        },
    }


if __name__ == "__main__":
    unittest.main()
