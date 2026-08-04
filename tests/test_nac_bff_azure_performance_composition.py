from __future__ import annotations

import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import nac_bff.azure_performance_composition as composition
from nac_bff.azure_performance_acceptance import OUTPUT_ROOT
from nac_bff.azure_performance_composition import (
    BLOCKED_STATUS,
    validate_azure_performance_composition_readiness,
)
from nac_bff.azure_performance_storage_ports import (
    AzurePerformanceStoragePortError,
    PerformanceExecutionFence,
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
                "full_lifecycle_process_fence",
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
                    runtime_state_path=ROOT / "not-read-runtime.json",
                    runtime_certificate_path=ROOT / "not-read-runtime.pem",
                    runtime_private_key_path=ROOT / "not-read-runtime.key",
                )

    def test_live_entrypoint_fences_full_lifecycle_before_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fence = PerformanceExecutionFence(
                root / OUTPUT_ROOT / ".composition-execution-fence.lock"
            )
            with (
                fence.hold(),
                patch.object(
                    composition,
                    "validate_azure_performance_composition_readiness",
                    side_effect=AssertionError("readiness must stay behind fence"),
                ),
            ):
                with self.assertRaisesRegex(
                    AzurePerformanceStoragePortError,
                    r"^AZURE_PERFORMANCE_EXECUTION_ALREADY_ACTIVE$",
                ):
                    composition.run_azure_performance_acceptance_live(
                        repo_root=root,
                        owner_approved=True,
                        execute_live_acceptance=True,
                        approval_reference="issuecomment-1",
                        expected_activation_hash="1" * 64,
                        correlation_id="offline-fence-test",
                        monitor_window_anchor_utc="2026-08-03T00:00:00Z",
                        toolchain_attestations={},
                        infrastructure_parameters={},
                        worm_baseline_parameters={},
                        provisioner_state_path=root / "not-read.json",
                        provisioner_certificate_path=root / "not-read.pem",
                        provisioner_private_key_path=root / "not-read.key",
                        runtime_state_path=root / "not-read-runtime.json",
                        runtime_certificate_path=root / "not-read-runtime.pem",
                        runtime_private_key_path=root / "not-read-runtime.key",
                    )

    def test_ready_composition_advances_without_measurement_readiness_field(self) -> None:
        contract_sha256 = "f" * 64
        measurement = {
            "contract_sha256": contract_sha256,
            "infrastructure_approval": {},
        }
        parameters = {"targetBindingSha256": "0" * 64}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(
                    composition,
                    "validate_azure_performance_composition_readiness",
                    return_value={"ready": True},
                ),
                patch(
                    "nac_bff.azure_performance_owner_gate."
                    "measure_performance_infrastructure_approval",
                    return_value=measurement,
                ) as measure,
            ):
                with self.assertRaisesRegex(
                    ValueError, "^PERFORMANCE_EXECUTION_BINDING_MISMATCH$"
                ):
                    composition.run_azure_performance_acceptance_live(
                        repo_root=root,
                        owner_approved=True,
                        execute_live_acceptance=True,
                        approval_reference="issuecomment-1",
                        expected_activation_hash="1" * 64,
                        correlation_id="offline-positive-route-test",
                        monitor_window_anchor_utc="2026-08-03T00:00:00Z",
                        toolchain_attestations={},
                        infrastructure_parameters=parameters,
                        worm_baseline_parameters={},
                        provisioner_state_path=root / "not-read.json",
                        provisioner_certificate_path=root / "not-read.pem",
                        provisioner_private_key_path=root / "not-read.key",
                        runtime_state_path=root / "not-read-runtime.json",
                        runtime_certificate_path=root / "not-read-runtime.pem",
                        runtime_private_key_path=root / "not-read-runtime.key",
                    )
        measure.assert_called_once()

    def test_application_identity_loader_binds_service_principal_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path = root / "runtime-state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "status": "PASSED",
                        "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
                        "applications": {
                            "m365_runtime_app": {
                                "display_name": "NaC M365 Runtime",
                                "client_id": "11111111-2222-4333-8444-555555555555",
                                "service_principal_id": (
                                    "66666666-7777-4888-8999-aaaaaaaaaaaa"
                                ),
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            identity = composition._load_application_identity(
                state_path,
                application_key="m365_runtime_app",
                expected_display_name="NaC M365 Runtime",
            )

        self.assertEqual(
            identity,
            {
                "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
                "client_id": "11111111-2222-4333-8444-555555555555",
                "service_principal_id": "66666666-7777-4888-8999-aaaaaaaaaaaa",
            },
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
