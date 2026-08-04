from __future__ import annotations

import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import nac_bff.azure_performance_composition as composition
from nac_bff.azure_performance_composition import (
    BLOCKED_STATUS,
    validate_azure_performance_composition_readiness,
)


EXPECTED_MISSING_PORTS: list[str] = []


class AzurePerformanceCompositionReadinessTests(unittest.TestCase):
    def test_current_stack_has_all_production_ports_without_live_authority(self) -> None:
        result = validate_azure_performance_composition_readiness()

        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["ready"])
        self.assertEqual(result["missing_ports"], EXPECTED_MISSING_PORTS)
        self.assertTrue(result["production_composition_constructed"])
        self.assertFalse(result["owner_approval_verified"])
        self.assertFalse(result["live_actions_authorized"])

    def test_all_ports_are_reported_without_claiming_live_authority(self) -> None:
        result = validate_azure_performance_composition_readiness()
        ports = {item["id"]: item for item in result["ports"]}

        self.assertEqual(
            {port_id for port_id, item in ports.items() if item["status"] == "READY"},
            set(ports),
        )
        self.assertTrue(
            ports["combined_owner_approval_verification"]["owner_bound"]
        )
        self.assertEqual(
            ports["bounded_500_get_runner"]["maximum_network_gets"], 500
        )
        self.assertEqual(
            ports["bounded_500_get_runner"]["maximum_concurrency"], 1
        )
        self.assertEqual(
            ports["bounded_500_get_runner"]["maximum_dispatches_per_minute"],
            6,
        )

    def test_required_sequence_is_fail_closed_and_ordered(self) -> None:
        result = validate_azure_performance_composition_readiness()

        self.assertEqual(
            [item["id"] for item in result["ports"]],
            [
                "combined_owner_approval_verification",
                "owner_bound_infrastructure_deployment_authority",
                "unlocked_worm_baseline_deployment",
                "unlocked_worm_baseline_exact_readback",
                "performance_coordination_deployment",
                "performance_coordination_safety_readback",
                "lease_blob_bootstrap",
                "durable_bootstrap_lease_binding_handoff",
                "attested_azure_storage_token_provider",
                "dedicated_blob_lease",
                "azure_monitor_observation",
                "bounded_500_get_runner",
                "restartable_final_evidence",
            ],
        )
        self.assertEqual(result["summary"]["network_calls"], 0)
        self.assertEqual(result["summary"]["azure_calls"], 0)
        self.assertEqual(result["summary"]["tenant_writes"], 0)
        self.assertEqual(result["summary"]["credential_reads"], 0)

    def test_validator_performs_no_io_or_environment_access(self) -> None:
        with (
            patch("builtins.open", side_effect=AssertionError("file read")),
            patch("os.getenv", side_effect=AssertionError("environment read")),
            patch.object(socket, "socket", side_effect=AssertionError("socket")),
            patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("subprocess"),
            ),
        ):
            result = validate_azure_performance_composition_readiness()

        self.assertEqual(result["status"], "READY")
        self.assertTrue(result["offline_only"])

    def test_live_entrypoint_rejects_closed_gate_before_any_io(self) -> None:
        with (
            patch("builtins.open", side_effect=AssertionError("file read")),
            patch("os.getenv", side_effect=AssertionError("environment read")),
            patch.object(socket, "socket", side_effect=AssertionError("socket")),
            patch.object(subprocess, "run", side_effect=AssertionError("subprocess")),
        ):
            with self.assertRaisesRegex(
                ValueError, "^PERFORMANCE_ACCEPTANCE_OWNER_GATE_CLOSED$"
            ):
                composition.run_azure_performance_acceptance_live(
                    repo_root=ROOT,
                    owner_approved=False,
                    execute_live_acceptance=False,
                    approval_reference="issuecomment-1",
                    expected_activation_hash="1" * 64,
                    correlation_id="offline-gate-test",
                    monitor_window_anchor_utc="2026-08-03T00:00:00Z",
                    toolchain_attestations={},
                    infrastructure_parameters={},
                    worm_baseline_parameters={},
                    provisioner_state_path=ROOT / "not-read.json",
                    provisioner_certificate_path=ROOT / "not-read.pem",
                    provisioner_private_key_path=ROOT / "not-read.key",
                )

    def test_missing_existing_method_adds_its_port_to_blockers(self) -> None:
        with patch.object(composition.AzureBlobLeaseAdapter, "acquire", None):
            result = validate_azure_performance_composition_readiness()

        self.assertIn("dedicated_blob_lease", result["missing_ports"])
        port = next(
            item for item in result["ports"] if item["id"] == "dedicated_blob_lease"
        )
        self.assertEqual(port["status"], "MISSING")
        self.assertIsNone(port["provider"])

    def test_result_is_fresh_redacted_data_and_accepts_no_injected_ports(self) -> None:
        first = validate_azure_performance_composition_readiness()
        first["missing_ports"].clear()
        first["ports"][0]["status"] = "TAMPERED"
        second = validate_azure_performance_composition_readiness()

        self.assertEqual(second["missing_ports"], [])
        self.assertEqual(second["ports"][0]["status"], "READY")
        self.assertEqual(
            list(
                inspect.signature(
                    validate_azure_performance_composition_readiness
                ).parameters
            ),
            [],
        )
        encoded = json.dumps(second, sort_keys=True).casefold()
        for forbidden in (
            "access_token",
            "authorization: bearer",
            "client_secret",
            "private_key",
            "issuecomment-",
        ):
            self.assertNotIn(forbidden, encoded)

    def test_public_exports_contain_no_test_capability_or_unsafe_factory(self) -> None:
        self.assertEqual(
            composition.__all__,
            [
                "BLOCKED_STATUS",
                "SCHEMA_VERSION",
                "run_azure_performance_acceptance_live",
                "validate_azure_performance_composition_readiness",
            ],
        )
        self.assertFalse(
            any(
                "test" in name.casefold() or "capability" in name.casefold()
                for name in composition.__all__
            )
        )


if __name__ == "__main__":
    unittest.main()
