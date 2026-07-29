from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nac_m365_graph.business_case_type_live_write_readiness import (
    BLOCKED_STATUS,
    READY_STATUS,
    build_business_case_type_live_write_readiness,
    current_business_case_type_live_write_readiness,
    synthetic_ready_input,
)


class BusinessCaseTypeLiveWriteReadinessTests(unittest.TestCase):
    def test_current_repository_state_is_blocked_without_side_effects(self) -> None:
        result = current_business_case_type_live_write_readiness()

        self.assertEqual(result["status"], BLOCKED_STATUS)
        self.assertFalse(result["live_write_authorized"])
        self.assertFalse(result["provisioning_app_executes_business_writes"])
        self.assertIn("write_token_adapter_bound", result["blockers"])
        self.assertEqual(result["summary"]["tenant_writes"], 0)
        self.assertEqual(result["summary"]["external_credential_store_reads"], 0)

    def test_complete_synthetic_shape_is_offline_ready_only(self) -> None:
        result = build_business_case_type_live_write_readiness(
            synthetic_ready_input()
        )

        self.assertEqual(result["status"], READY_STATUS)
        self.assertEqual(result["blockers"], [])
        self.assertFalse(result["live_write_authorized"])
        self.assertEqual(result["summary"]["graph_calls"], 0)

    def test_principal_reuse_is_blocked(self) -> None:
        ready = synthetic_ready_input()
        result = build_business_case_type_live_write_readiness(
            replace(
                ready,
                write_principal_sha256=ready.provisioning_principal_sha256,
            )
        )

        self.assertEqual(result["status"], BLOCKED_STATUS)
        self.assertIn("principals_pairwise_distinct", result["blockers"])

    def test_business_write_route_cannot_use_provisioning_principal(self) -> None:
        ready = synthetic_ready_input()
        result = build_business_case_type_live_write_readiness(
            replace(
                ready,
                business_write_executor_principal_sha256=(
                    ready.provisioning_principal_sha256
                ),
            )
        )

        self.assertEqual(result["status"], BLOCKED_STATUS)
        self.assertIn("business_write_route_exact", result["blockers"])
        self.assertTrue(result["provisioning_app_executes_business_writes"])

    def test_broader_permission_or_role_is_blocked(self) -> None:
        result = build_business_case_type_live_write_readiness(
            replace(
                synthetic_ready_input(),
                write_graph_permissions=("Sites.FullControl.All",),
                write_site_roles=("fullcontrol",),
            )
        )

        self.assertIn("write_permission_exact", result["blockers"])
        self.assertIn("write_site_role_exact", result["blockers"])

    def test_unlocked_worm_and_missing_durable_ports_are_blocked(self) -> None:
        result = build_business_case_type_live_write_readiness(
            replace(
                synthetic_ready_input(),
                worm_policy_locked=False,
                durable_outbox_adapter_sha256=None,
                reconciliation_store_adapter_sha256=None,
            )
        )

        self.assertIn("worm_policy_locked", result["blockers"])
        self.assertIn("durable_outbox_adapter_bound", result["blockers"])
        self.assertIn("reconciliation_store_adapter_bound", result["blockers"])

    def test_output_contains_no_binding_hashes_or_secrets(self) -> None:
        result = build_business_case_type_live_write_readiness(
            replace(
                synthetic_ready_input(),
                workspace_id="client-secret-value",
                graph_http_adapter_sha256="/tmp/private-key.pem",
            )
        )
        encoded = json.dumps(result, sort_keys=True)

        self.assertNotIn("1" * 64, encoded)
        self.assertNotIn("client-secret-value", encoded)
        self.assertNotIn("/tmp/private-key.pem", encoded)
        self.assertNotIn("private_key", encoded)
        self.assertNotIn("access_token", encoded)

    def test_current_snapshot_performs_no_io_or_environment_reads(self) -> None:
        with (
            patch("builtins.open", side_effect=AssertionError("file read")),
            patch("os.getenv", side_effect=AssertionError("environment read")),
            patch.object(socket, "socket", side_effect=AssertionError("socket")),
            patch(
                "urllib.request.urlopen",
                side_effect=AssertionError("http request"),
            ),
        ):
            result = current_business_case_type_live_write_readiness()

        self.assertEqual(result["status"], BLOCKED_STATUS)
        self.assertFalse(result["live_state_inspected"])


if __name__ == "__main__":
    unittest.main()
