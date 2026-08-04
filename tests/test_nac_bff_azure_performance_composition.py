from __future__ import annotations

import inspect
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
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


def _coordination_resources() -> dict[str, str]:
    base = "/subscriptions/s/resourceGroups/rg"
    storage = f"{base}/providers/Microsoft.Storage/storageAccounts/stcoord"
    container = (
        f"{storage}/blobServices/default/containers/nac-bff-performance-leases"
    )
    return {
        "coordination_storage_account_resource_id": storage,
        "lease_container_resource_id": container,
        "broker_lease_data_role_definition_id": (
            f"{base}/providers/Microsoft.Authorization/roleDefinitions/broker"
        ),
        "broker_lease_role_assignment_id": (
            f"{container}/providers/Microsoft.Authorization/roleAssignments/broker"
        ),
    }


class _TraceReadback:
    def __init__(self, trace: list[str], *, name_available: bool = True) -> None:
        self.trace = trace
        self.name_available = name_available
        self.verification_capability = object()

    def check_storage_account_name_availability(self, **_kwargs: object) -> object:
        self.trace.append("provider:name-probe")
        return {"payload": {"name_available": self.name_available}}

    def execute_read(self, *, observation_kind: str, **_kwargs: object) -> object:
        self.trace.append(f"provider:get:{observation_kind}")
        return {"kind": observation_kind}

    def read_management_group_ancestry(self, **_kwargs: object) -> object:
        self.trace.append("provider:get:subscription-ancestry")
        return {"payload": {"management_group_relationships": []}}

    def read_effective_rbac(self, *, principal_id: str, **_kwargs: object) -> object:
        self.trace.append(f"provider:get:effective-rbac:{principal_id}")
        return {"principal_id": principal_id}


class _TraceReceiptStore:
    def __init__(
        self,
        trace: list[str],
        *,
        status: str,
        name_available: bool = True,
    ) -> None:
        self.trace = trace
        self.status = status
        self.name_available = name_available
        self.original = {"schema_version": "original"}

    def load(self) -> dict[str, object]:
        self.trace.append("receipt:load")
        result: dict[str, object] = {"status": self.status}
        if self.status in {"NAME_ONLY", "COMPLETE"}:
            result["original_name_receipt"] = self.original
        return result

    def persist_original_name_available(self, _value: object) -> None:
        self.trace.append("receipt:create:original-name")

    def require_current_name_available(self, _value: object) -> None:
        self.trace.append("receipt:validate:current-name")
        if not self.name_available:
            raise ValueError("COORDINATION_STORAGE_NAME_UNAVAILABLE")

    def persist_successful_deployment(self, _value: object, **_kwargs: object) -> None:
        self.trace.append("receipt:create:successful-deployment")

    def reconcile_successful_deployment(self, _value: object) -> dict[str, object]:
        self.trace.append("receipt:validate:successful-deployment")
        return {"coordination_resources": _coordination_resources()}


def _trace_infrastructure_path(
    status: str, *, name_available: bool = True
) -> list[str]:
    trace: list[str] = []
    readback = _TraceReadback(trace, name_available=name_available)
    store = _TraceReceiptStore(
        trace, status=status, name_available=name_available
    )
    resources = _coordination_resources()
    coordination = SimpleNamespace(
        **resources,
        deployment_receipt_sha256="1" * 64,
        outputs_sha256="2" * 64,
    )

    def worm_deploy(_authority: object) -> object:
        trace.append("provider:create:worm-deployment")
        return object()

    def worm_readback(_authority: object, _receipt: object) -> object:
        trace.append("provider:get:worm-baseline-readback")
        return object()

    def coordination_deploy(_authority: object, _readback: object) -> object:
        trace.append("provider:create:coordination-deployment")
        return coordination

    parameters = {
        "tenantId": "tenant",
        "subscriptionId": "s",
        "resourceGroupName": "rg",
        "storageAccountName": "stcoord",
        "bffStorageAccountResourceId": "bff",
        "wormStorageAccountResourceId": "worm",
        "brokerPrincipalId": "broker",
        "brokerCallerServicePrincipalId": "caller",
        "brokerFunctionAppResourceId": "function",
        "brokerFunctionPackageSha256": "b" * 64,
        "brokerTicketVerificationCertificateSha256": "c" * 64,
        "brokerOutboundIpAddresses": ["203.0.113.10"],
        "targetBindingSha256": "a" * 64,
        "location": "location",
        "tags": {},
    }
    with (
        patch.object(
            composition,
            "UnlockedWormBaselineDeploymentPort",
            return_value=SimpleNamespace(deploy=worm_deploy),
        ),
        patch.object(
            composition,
            "UnlockedWormBaselineReadbackPort",
            return_value=SimpleNamespace(
                verify_exact_unlocked_baseline=worm_readback
            ),
        ),
        patch.object(
            composition,
            "PerformanceCoordinationDeploymentPort",
            return_value=SimpleNamespace(deploy=coordination_deploy),
        ),
    ):
        prepared, name, deployment, _complete_restart = composition._prepare_performance_infrastructure(
            readback=readback,
            receipt_store=store,
            deployment_authority=object(),
            executor=object(),
            deployment_id="deployment",
            infrastructure_parameters=parameters,
        )
    composition._infrastructure_verification_arguments(
        readback=readback,
        name_readback=name,
        deployment_readback=deployment,
        coordination=prepared,
        infrastructure_parameters=parameters,
    )
    return trace


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
                "immutable_infrastructure_restart_receipts",
                "performance_coordination_safety_readback",
                "provisioner_performance_lease_app_role",
                "broker_function_settings_activation",
                "owner_bound_bff_app_token",
                "short_lived_signed_broker_ticket",
                "full_lifecycle_process_fence",
                "brokered_dedicated_blob_lease",
                "server_side_atomic_blob_lease_state_machine",
                "azure_monitor_observation",
                "bounded_500_get_runner",
                "restartable_final_evidence",
            ],
        )
        self.assertEqual(result["summary"]["network_calls"], 0)
        self.assertEqual(result["summary"]["azure_calls"], 0)
        self.assertEqual(result["summary"]["tenant_writes"], 0)
        self.assertEqual(result["summary"]["credential_reads"], 0)

    def test_fresh_path_persists_both_receipts_around_deployment(self) -> None:
        trace = _trace_infrastructure_path("EMPTY")

        self.assertEqual(
            trace[:9],
            [
                "receipt:load",
                "provider:name-probe",
                "receipt:create:original-name",
                "provider:create:worm-deployment",
                "provider:get:worm-baseline-readback",
                "provider:create:coordination-deployment",
                "provider:get:coordination-deployment-receipt",
                "receipt:create:successful-deployment",
                "provider:get:subscription-ancestry",
            ],
        )

    def test_complete_restart_is_read_only_and_uses_no_name_probe(self) -> None:
        trace = _trace_infrastructure_path("COMPLETE")

        self.assertEqual(
            trace[:4],
            [
                "receipt:load",
                "provider:get:coordination-deployment-receipt",
                "receipt:validate:successful-deployment",
                "provider:get:subscription-ancestry",
            ],
        )
        self.assertNotIn("provider:name-probe", trace)
        self.assertFalse(any(item.startswith("provider:create:") for item in trace))
        self.assertIn("provider:get:coordination-storage-account-configuration", trace)
        self.assertIn("provider:get:effective-rbac:broker", trace)
        self.assertIn("provider:get:effective-rbac:caller", trace)

    def test_complete_restart_precedes_and_selects_read_only_runtime_activation(self) -> None:
        source = inspect.getsource(
            composition.run_azure_performance_acceptance_live.__wrapped__
        )
        self.assertLess(
            source.index("_prepare_performance_infrastructure("),
            source.index("_performance_lease_app_role_state("),
        )
        self.assertIn("read_only=complete_restart", source)
        self.assertIn("settings_port.verify_current(broker_settings)", source)
        self.assertIn("if complete_restart", source)

    def test_name_only_restart_requires_new_available_probe_before_create(self) -> None:
        trace = _trace_infrastructure_path("NAME_ONLY")
        self.assertEqual(
            trace[:5],
            [
                "receipt:load",
                "provider:name-probe",
                "receipt:validate:current-name",
                "provider:create:worm-deployment",
                "provider:get:worm-baseline-readback",
            ],
        )

    def test_name_only_unavailable_blocks_without_deployment_create(self) -> None:
        trace: list[str] = []
        readback = _TraceReadback(trace, name_available=False)
        store = _TraceReceiptStore(
            trace, status="NAME_ONLY", name_available=False
        )
        with self.assertRaisesRegex(
            ValueError, "^COORDINATION_STORAGE_NAME_UNAVAILABLE$"
        ):
            composition._prepare_performance_infrastructure(
                readback=readback,
                receipt_store=store,
                deployment_authority=object(),
                executor=object(),
                deployment_id="deployment",
                infrastructure_parameters={
                    "subscriptionId": "s",
                    "storageAccountName": "stcoord",
                },
            )
        self.assertEqual(
            trace,
            [
                "receipt:load",
                "provider:name-probe",
                "receipt:validate:current-name",
            ],
        )

    def test_missing_reconciliation_deployment_blocks_without_fallback(self) -> None:
        trace: list[str] = []
        readback = _TraceReadback(trace)

        def missing(**_kwargs: object) -> object:
            trace.append("provider:get:coordination-deployment-receipt")
            raise ValueError("DEPLOYMENT_MISSING")

        readback.execute_read = missing  # type: ignore[method-assign]
        store = _TraceReceiptStore(trace, status="COMPLETE")
        with self.assertRaisesRegex(ValueError, "^DEPLOYMENT_MISSING$"):
            composition._prepare_performance_infrastructure(
                readback=readback,
                receipt_store=store,
                deployment_authority=object(),
                executor=object(),
                deployment_id="deployment",
                infrastructure_parameters={},
            )
        self.assertEqual(
            trace,
            ["receipt:load", "provider:get:coordination-deployment-receipt"],
        )

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

    def test_performance_lease_role_uses_only_bound_certificate_graph_client(
        self,
    ) -> None:
        identity = {
            "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
            "client_id": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
            "service_principal_id": "11111111-2222-4333-8444-555555555555",
        }
        token_provider = object()
        expected = {
            "status": "present",
            "assignment_count": 1,
            "application_role": "Performance.Lease",
        }
        with (
            patch.object(
                composition,
                "_bound_provisioner_token_provider",
                return_value=token_provider,
            ) as provider,
            patch.object(
                composition,
                "ensure_provisioner_performance_lease",
                return_value=expected,
            ) as ensure,
        ):
            result = composition._ensure_performance_lease_app_role(
                identity=identity,
                certificate_path=Path("/tmp/provisioner.cert.pem"),
                private_key_path=Path("/tmp/provisioner.key.pem"),
                expected_certificate_sha256="a" * 64,
            )

        self.assertEqual(result, expected)
        environment = provider.call_args.args[0]
        self.assertEqual(
            set(environment),
            {
                "M365_TENANT_ID",
                "M365_PROVISIONER_CLIENT_ID",
                "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
                "M365_PROVISIONER_CLIENT_KEY_PATH",
            },
        )
        self.assertNotIn("M365_GRAPH_ACCESS_TOKEN", environment)
        graph = ensure.call_args.args[0]
        self.assertIs(graph.token_provider, token_provider)

    def test_complete_restart_inspects_role_without_graph_mutation(self) -> None:
        identity = {
            "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
            "client_id": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
            "service_principal_id": "11111111-2222-4333-8444-555555555555",
        }
        expected = {
            "status": "present",
            "assignment_count": 1,
            "application_role": "Performance.Lease",
        }
        with (
            patch.object(
                composition,
                "_bound_provisioner_token_provider",
                return_value=object(),
            ),
            patch.object(
                composition,
                "inspect_provisioner_performance_lease",
                return_value=expected,
            ) as inspect_role,
            patch.object(
                composition,
                "ensure_provisioner_performance_lease",
                side_effect=AssertionError("mutating ensure must not run"),
            ),
        ):
            result = composition._performance_lease_app_role_state(
                identity=identity,
                certificate_path=Path("/tmp/provisioner.cert.pem"),
                private_key_path=Path("/tmp/provisioner.key.pem"),
                expected_certificate_sha256="a" * 64,
                read_only=True,
            )

        self.assertEqual(result, expected)
        inspect_role.assert_called_once()

    def test_performance_lease_role_requires_exact_positive_readback(self) -> None:
        identity = {
            "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
            "client_id": "04b07795-8ddb-461a-bbee-02f9e1bf7b46",
            "service_principal_id": "11111111-2222-4333-8444-555555555555",
        }
        with (
            patch.object(
                composition,
                "_bound_provisioner_token_provider",
                return_value=object(),
            ),
            patch.object(
                composition,
                "ensure_provisioner_performance_lease",
                return_value={"status": "present", "assignment_count": 0},
            ),
        ):
            with self.assertRaisesRegex(
                ValueError,
                "^PERFORMANCE_LEASE_APP_ROLE_READBACK_MISMATCH$",
            ):
                composition._ensure_performance_lease_app_role(
                    identity=identity,
                    certificate_path=Path("/tmp/provisioner.cert.pem"),
                    private_key_path=Path("/tmp/provisioner.key.pem"),
                    expected_certificate_sha256="a" * 64,
                )

    def test_missing_existing_method_adds_its_port_to_blockers(self) -> None:
        with patch.object(
            composition.BrokeredAzureBlobLeaseAdapter, "acquire", None
        ):
            result = validate_azure_performance_composition_readiness()

        self.assertIn("brokered_dedicated_blob_lease", result["missing_ports"])
        port = next(
            item
            for item in result["ports"]
            if item["id"] == "brokered_dedicated_blob_lease"
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
