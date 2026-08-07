from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import base64
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
from types import MappingProxyType, SimpleNamespace

from nac_bff.azure_performance_acceptance import (
    BoundPerformanceAuthorizationVerifier,
    MeasurementAttestation,
    FixedBffPerformanceTransport,
    FixedTransportBindingVerifier,
    LatencyMetrics,
    M365DelegatedTokenProvider,
    PerformanceAcceptanceRunner,
    PerformanceArtifactStore,
    PerformanceExecutionAuthorization,
    PerformanceSample,
    PhaseSpec,
    RuntimeSafetyObservation,
    TOTAL_REQUEST_LIMIT,
    build_owner_comment,
    build_performance_acceptance_plan,
    verify_activation_success,
    verify_performance_execution_authorization,
)
from nac_bff import azure_activation_runner
from nac_bff import azure_performance_acceptance as performance
from nac_bff import azure_performance_authorization as live_authorization
from nac_bff.azure_performance_authorization import (
    BLOB_LEASE_ACQUIRE,
    TARGET_GET,
    VerifiedInfrastructureSafetySource,
    VerifiedLiveActionCapability,
)
from nac_bff.azure_performance_infrastructure_safety import (
    AzurePerformanceInfrastructureSafetyVerification,
)
from nac_bff.azure_activation_composition import GitHubApprovalVerifier
from nac_m365_graph.mvp_test_environment_deploy import (
    M365CliReadinessError,
    _validate_m365_command,
)
from nac_cli.cli import main as cli_main


SHA256 = "a" * 64
CONTRACT_SHA256 = "f" * 64
APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/735#issuecomment-1"
)
CORRELATION_ID = "nac-bff-performance-20260802"
BROKER_PRINCIPAL_ID = "11111111-2222-4333-8444-555555555555"
MONITOR_WINDOW_ANCHOR = "2026-08-02T00:00:00Z"
MONITOR_WINDOW_ANCHOR_SHA256 = hashlib.sha256(
    MONITOR_WINDOW_ANCHOR.encode("utf-8")
).hexdigest()
INFRASTRUCTURE_APPROVAL = {
    "approved_commit_sha": "1" * 40,
    "approved_tree_sha": "2" * 40,
    "toolchain_attestations_sha256": "3" * 64,
    "infrastructure_binding_sha256": "4" * 64,
    "infrastructure_parameters_sha256": "5" * 64,
    "infrastructure_source_sha256": "6" * 64,
    "lease_bootstrap_policy_sha256": "7" * 64,
    "infrastructure_safety_policy_sha256": "8" * 64,
    "worm_baseline_binding_sha256": "9" * 64,
    "worm_baseline_compiled_arm_sha256": "a" * 64,
    "worm_baseline_parameters_sha256": "b" * 64,
    "worm_baseline_source_sha256": "c" * 64,
    "deployment_sequence_sha256": "d" * 64,
}
INFRASTRUCTURE_PARAMETERS = {
    "location": "germanywestcentral",
    "storageAccountName": "stnacperflease001",
    "bffStorageAccountResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/"
        "storageAccounts/stnacbfftest001"
    ),
    "wormStorageAccountResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/"
        "storageAccounts/stnacwormtest001"
    ),
    "brokerCallerServicePrincipalId": (
        "66666666-7777-4888-8999-aaaaaaaaaaaa"
    ),
    "brokerFunctionAppResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/sites/"
        "func-nac-bff-test"
    ),
    "brokerVirtualNetworkResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Network/"
        "virtualNetworks/vnet-nac-bff-test"
    ),
    "brokerFunctionIntegrationSubnetResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Network/"
        "virtualNetworks/vnet-nac-bff-test/subnets/snet-flex-integration"
    ),
    "brokerPrivateEndpointSubnetResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Network/"
        "virtualNetworks/vnet-nac-bff-test/subnets/snet-private-endpoints"
    ),
    "brokerFunctionPackageSha256": "e" * 64,
    "brokerTicketVerificationCertificateSha256": "f" * 64,
    "targetBindingSha256": "0" * 64,
    "tenantId": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
    "subscriptionId": "37cd9645-6cb9-4278-88ee-e80377cd951c",
    "resourceGroupName": "rg-nac-bff-test",
    "deploymentMode": "Incremental",
    "tags": {
        "owner": "notariat8",
        "purpose": "endpoint-scoped-conservative-measurement",
    },
}
WORM_BASELINE_PARAMETERS = {
    "location": "germanywestcentral",
    "tenantId": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
    "subscriptionId": "37cd9645-6cb9-4278-88ee-e80377cd951c",
    "resourceGroupName": "rg-nac-bff-test",
    "deploymentMode": "Incremental",
    "storageAccountName": "stnacwormtest001",
    "containerName": "nac-worm-tenant",
    "encryptionScopeName": "nac-worm-tenant",
    "tags": {"owner": "notariat8", "purpose": "unlocked-worm-baseline"},
}


def _transport_capability(transport: FixedBffPerformanceTransport, uses: int = 8):
    return _test_live_action_capability(
        target_binding_sha256=transport.target_binding_sha256,
        action_bindings={
            TARGET_GET: (transport.target_binding_sha256, uses),
        },
    )


def _test_live_action_capability(
    *,
    target_binding_sha256: str,
    action_bindings: dict[str, tuple[str, int]],
) -> VerifiedLiveActionCapability:
    """Construct test-only authority without exposing a production mint API."""

    capability = object.__new__(VerifiedLiveActionCapability)
    nonce = secrets.token_hex(32)
    capability._nonce = nonce
    state = live_authorization._CapabilityState(
        capability=capability,
        target_binding_sha256=target_binding_sha256,
        action_bindings=MappingProxyType(
            {action: binding for action, (binding, _uses) in action_bindings.items()}
        ),
        remaining_uses={
            action: uses for action, (_binding, uses) in action_bindings.items()
        },
        usage_ledger=None,
    )
    with live_authorization._CAPABILITY_LOCK:
        live_authorization._CAPABILITY_STATES[nonce] = state
    return capability


def _bound_safety_evidence(target_binding_sha256: str) -> dict[str, object]:
    parameters = INFRASTRUCTURE_PARAMETERS
    return {
        "status": "SAFE",
        "owner_binding_sha256": "9" * 64,
        "target_binding_sha256": target_binding_sha256,
        "infrastructure_safety_policy_sha256": "8" * 64,
        "infrastructure_safety_evidence_sha256": "d" * 64,
        "tenant_id": parameters["tenantId"],
        "subscription_id": parameters["subscriptionId"],
        "resource_group_name": parameters["resourceGroupName"],
        "location": parameters["location"],
        "coordination_storage_account_name": parameters["storageAccountName"],
        "coordination_storage_account_resource_id": (
            f"/subscriptions/{parameters['subscriptionId']}/resourceGroups/"
            f"{parameters['resourceGroupName']}/providers/Microsoft.Storage/"
            f"storageAccounts/{parameters['storageAccountName']}"
        ),
        "bff_storage_account_resource_id": parameters[
            "bffStorageAccountResourceId"
        ],
        "worm_storage_account_resource_id": parameters[
            "wormStorageAccountResourceId"
        ],
        "broker_principal_id": BROKER_PRINCIPAL_ID,
        "broker_caller_service_principal_id": parameters[
            "brokerCallerServicePrincipalId"
        ],
        "broker_function_app_resource_id": parameters[
            "brokerFunctionAppResourceId"
        ],
        "broker_function_package_sha256": parameters[
            "brokerFunctionPackageSha256"
        ],
        "broker_ticket_verification_certificate_sha256": parameters[
            "brokerTicketVerificationCertificateSha256"
        ],
        "tags_sha256": performance._sha256_json(parameters["tags"]),
        "broker_private_network_boundary_sha256": performance._sha256_json(
            {
                "virtualNetworkResourceId": parameters[
                    "brokerVirtualNetworkResourceId"
                ],
                "functionIntegrationSubnetResourceId": parameters[
                    "brokerFunctionIntegrationSubnetResourceId"
                ],
                "privateEndpointSubnetResourceId": parameters[
                    "brokerPrivateEndpointSubnetResourceId"
                ],
            }
        ),
        "toolchain_attestations_sha256": INFRASTRUCTURE_APPROVAL[
            "toolchain_attestations_sha256"
        ],
    }


def _test_safety_verification(
    evidence: dict[str, object],
) -> AzurePerformanceInfrastructureSafetyVerification:
    verification = dict.__new__(AzurePerformanceInfrastructureSafetyVerification)
    dict.__init__(verification, evidence)
    return verification


def _test_bound_verifier(**values) -> BoundPerformanceAuthorizationVerifier:
    values.pop("infrastructure_safety_readback", None)
    source = object.__new__(VerifiedInfrastructureSafetySource)
    return BoundPerformanceAuthorizationVerifier(
        **values,
        infrastructure_safety_source=source,
    )


class _Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds

    def now(self) -> datetime:
        return datetime(2026, 8, 2, tzinfo=UTC)


class _AdvancingClock(_Clock):
    def now(self) -> datetime:
        return datetime(2026, 8, 2, tzinfo=UTC) + timedelta(seconds=self.value)


class _Transport:
    def __init__(self, samples: list[PerformanceSample]) -> None:
        self.samples = list(samples)
        self.calls = 0

    @property
    def target_binding_sha256(self) -> str:
        return build_performance_acceptance_plan("0" * 64, "0" * 64)[
            "target_binding_sha256"
        ]

    def request(self, *, transport_boundary=None) -> PerformanceSample:
        self.calls += 1
        sample = self.samples.pop(0)
        if sample.network_dispatched and transport_boundary is not None:
            transport_boundary()
        return sample


class _RecordingTransport(_Transport):
    def __init__(
        self, samples: list[PerformanceSample], clock: _AdvancingClock
    ) -> None:
        super().__init__(samples)
        self.clock = clock
        self.dispatch_times: list[float] = []

    def request(self, *, transport_boundary=None) -> PerformanceSample:
        self.dispatch_times.append(self.clock.value)
        return super().request(transport_boundary=transport_boundary)


class _Monitor:
    def __init__(self) -> None:
        self.attempts: list[int] = []

    def observe(
        self, dispatch_attempt_count: int, measurement_attestation_sha256: str
    ) -> RuntimeSafetyObservation:
        self.attempts.append(dispatch_attempt_count)
        return RuntimeSafetyObservation(
            observed_execution_units_gb_seconds=1000.0,
            projected_remaining_execution_units_gb_seconds=(
                30_000.0
                * min(
                    TOTAL_REQUEST_LIMIT,
                    max(TOTAL_REQUEST_LIMIT - dispatch_attempt_count, 0)
                    + min(dispatch_attempt_count, 30),
                )
                / TOTAL_REQUEST_LIMIT
            ),
            always_ready_units=0,
            telemetry_cap_reached=False,
            monitor_binding_sha256="d" * 64,
            monitor_evidence_sha256="f" * 64,
            monitor_window_anchor_sha256=MONITOR_WINDOW_ANCHOR_SHA256,
            lease_binding_sha256="e" * 64,
            measurement_attestation_sha256=measurement_attestation_sha256,
            observed_at_utc="2026-08-02T00:00:00Z",
        )


class _CheckpointStore:
    def __init__(self, on_write=None) -> None:
        self.state = None
        self.on_write = on_write

    def write_state(self, state) -> None:
        snapshot = json.loads(json.dumps(state))
        if self.on_write is not None:
            self.on_write(snapshot)
        self.state = snapshot

    def load_state(self):
        return json.loads(json.dumps(self.state)) if self.state is not None else None

    def state_sha256(self):
        if self.state is None:
            return None
        return hashlib.sha256(
            json.dumps(
                self.state,
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()


class _ApprovalVerifier:
    def __init__(self, *, status: str = "VERIFIED") -> None:
        self.status = status

    def verify_performance_owner_comment(self, **values):
        return {
            "status": self.status,
            "owner_login": "ofunk",
            "immutable": True,
            "reference": values["reference"],
            "body_sha256": values["expected_body_sha256"],
        }


def _github_approval_verifier() -> GitHubApprovalVerifier:
    return object.__new__(GitHubApprovalVerifier)


class _AuthorizationVerifier:
    def verify(self, **values):
        return _authorization(
            values["activation_hash"], values["measurement_preflight_sha256"]
        )


class _MeasurementProvider:
    def get_attestation(self):
        return _capacity()


class _TransportVerifier:
    def verify(self, transport, expected_sha256):
        if transport.target_binding_sha256 != expected_sha256:
            raise ValueError("PERFORMANCE_TARGET_BINDING_MISMATCH")


def _capacity() -> MeasurementAttestation:
    return MeasurementAttestation(
        measurement_mode="endpoint_scoped_conservative_measurement",
        tenant_wide_sharepoint_capacity_claim="NOT_CLAIMED",
        maximum_dispatches_per_minute=6,
        planned_dispatch_count=500,
        always_ready_units=0,
        projected_execution_units_gb_seconds=30_000.0,
        observed_execution_units_gb_seconds=0.0,
        telemetry_cap_reached=False,
        measurement_policy_sha256=performance.measurement_policy_sha256(),
        monitor_binding_sha256="d" * 64,
        monitor_evidence_sha256="f" * 64,
        monitor_window_anchor_sha256=MONITOR_WINDOW_ANCHOR_SHA256,
        lease_binding_sha256="e" * 64,
        observed_at_utc="2026-08-02T00:00:00Z",
        tenant_binding_sha256=hashlib.sha256(
            b"870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
        ).hexdigest(),
        workspace_binding_sha256=hashlib.sha256(b"notary_team_01").hexdigest(),
    )


def _authorization(
    activation_hash: str,
    capacity_sha256: str,
) -> PerformanceExecutionAuthorization:
    plan = build_performance_acceptance_plan(activation_hash, CONTRACT_SHA256)
    authorization = object.__new__(PerformanceExecutionAuthorization)
    values = {
        "status": "VERIFIED",
        "owner_login": "ofunk",
        "owner_approval_reference_sha256": "7" * 64,
        "owner_approval_body_sha256": "9" * 64,
        "action": performance.OWNER_ACTION,
        "correlation_id": "nac-bff-performance-20260802",
        "contract_sha256": CONTRACT_SHA256,
        "activation_hash": activation_hash,
        "activation_receipt_sha256": "4" * 64,
        "activation_evidence_sha256": "5" * 64,
        "target_binding_sha256": plan["target_binding_sha256"],
        "measurement_preflight_sha256": capacity_sha256,
        "phase_plan_sha256": plan["phase_plan_sha256"],
        "monitor_window_anchor_sha256": MONITOR_WINDOW_ANCHOR_SHA256,
        "interruption_terminalization_status": (
            "VERIFIED_BY_COMMITTED_ACTIVATION_RECEIPT"
        ),
    }
    for name, value in values.items():
        object.__setattr__(authorization, name, value)
    object.__setattr__(
        authorization, "_seal", performance._EXECUTION_AUTHORIZATION_SEAL
    )
    performance._ISSUED_EXECUTION_AUTHORIZATIONS[id(authorization)] = authorization
    return authorization


def _bindings() -> tuple[str, str, str]:
    activation_hash = "b" * 64
    plan_sha256 = build_performance_acceptance_plan(
        activation_hash,
        CONTRACT_SHA256,
    )["plan_sha256"]
    capacity_sha256 = _capacity().validate(
        now=datetime(2026, 8, 2, tzinfo=UTC)
    )["attestation_sha256"]
    return activation_hash, plan_sha256, capacity_sha256


def _phase(identifier: str, requests: int) -> PhaseSpec:
    return PhaseSpec(
        identifier,
        "paced",
        requests,
        1,
        0.01,
        1,
        100.0,
        0.0,
        0.5,
        100,
        100,
        100,
    )


def _jwt(*, audience: str, algorithm: str = "none") -> str:
    encode = lambda value: base64.urlsafe_b64encode(  # noqa: E731
        json.dumps(value, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    return ".".join(
        (
            encode({"alg": algorithm, "typ": "JWT"}),
            encode(
                {
                    "aud": audience,
                    "exp": 1000,
                    "scp": "Matter.Read",
                    "tid": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
                }
            ),
            "signature",
        )
    )


_DUMMY_M365_TOKEN = _jwt(
    audience="api://funktion8.de/nac-bff",
    algorithm="RS256",
)


def _attested_m365_token(token: str = _DUMMY_M365_TOKEN):
    return performance._issue_attested_m365_access_token(
        token,
        resource="api://funktion8.de/nac-bff",
        scopes=frozenset({"Matter.Read"}),
    )


class AzurePerformanceAcceptanceTests(unittest.TestCase):
    def test_bound_verifier_rejects_caller_fabricated_readback_source(self) -> None:
        with self.assertRaisesRegex(TypeError, "infrastructure_safety_source"):
            BoundPerformanceAuthorizationVerifier(
                repo_root=Path("."),
                approval_verifier=_ApprovalVerifier(),
                infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                toolchain_attestations={},
                infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
                worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
                infrastructure_safety_source=lambda: _bound_safety_evidence(
                    "0" * 64
                ),
            )

    def test_plan_is_exactly_bounded_and_deterministic(self) -> None:
        first = build_performance_acceptance_plan(SHA256, CONTRACT_SHA256)
        second = build_performance_acceptance_plan(SHA256, CONTRACT_SHA256)

        self.assertEqual(first, second)
        self.assertEqual(TOTAL_REQUEST_LIMIT, 500)
        self.assertEqual(first["budgets"]["total_request_limit"], 500)
        self.assertEqual(first["budgets"]["maximum_client_concurrency"], 1)
        self.assertEqual(
            first["measurement_envelope"]["maximum_dispatches_per_minute"], 6
        )
        self.assertTrue(first["measurement_envelope"]["no_client_retries"])
        self.assertEqual(
            first["tenant_wide_sharepoint_capacity_claim"], "NOT_CLAIMED"
        )
        self.assertEqual(
            {
                name: first[name]
                for name in performance.NOT_CLAIMED_ACCEPTANCE_FIELDS
            },
            performance.NOT_CLAIMED_ACCEPTANCE_FIELDS,
        )
        self.assertEqual(
            first["offline_adapters"]["azure_monitor"]["status"],
            "IMPLEMENTED_OFFLINE",
        )
        self.assertEqual(
            first["offline_adapters"]["azure_blob_lease_broker"]["status"],
            "IMPLEMENTED_OFFLINE",
        )
        lease_policy = first["offline_adapters"]["azure_blob_lease_broker"][
            "policy"
        ]
        self.assertTrue(
            lease_policy["same_ticket_retry_reuses_persisted_private_lease_id"]
        )
        self.assertTrue(
            lease_policy[
                "fresh_same_run_ticket_may_reconcile_persisted_intent"
            ]
        )
        self.assertTrue(first["live_preconditions"]["exclusive_remote_lease_required"])
        self.assertNotIn("notary_team_01", json.dumps(first))

    def test_owner_comment_binds_single_batch_without_identifiers(self) -> None:
        result = build_owner_comment(
            CONTRACT_SHA256,
            SHA256,
            "nac-bff-performance-20260802",
            INFRASTRUCTURE_APPROVAL,
            MONITOR_WINDOW_ANCHOR,
        )

        self.assertIn(
            performance.OWNER_ACTION,
            result["body"],
        )
        self.assertIn('"total_request_limit":500', result["body"])
        self.assertIn('"abort_on_throttle_signal":true', result["body"])
        self.assertIn('"monitor_policy_sha256":', result["body"])
        self.assertIn('"lease_policy_sha256":', result["body"])
        self.assertIn(f'"contract_sha256":"{CONTRACT_SHA256}"', result["body"])
        self.assertIn('"correlation_id":"nac-bff-performance-20260802"', result["body"])
        self.assertNotIn("870c862b", result["body"])
        self.assertIn('"notary_team_01_only":true', result["body"])
        for name in performance.NOT_CLAIMED_ACCEPTANCE_FIELDS:
            self.assertIn(f'"{name}":"NOT_CLAIMED"', result["body"])
        self.assertEqual(len(result["body_sha256"]), 64)

    def test_measurement_preflight_fails_closed(self) -> None:
        self.assertEqual(
            _capacity().validate(now=datetime(2026, 8, 2, tzinfo=UTC))["status"],
            "PASSED",
        )
        blocked = replace(_capacity(), maximum_dispatches_per_minute=7)
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_MEASUREMENT_PREFLIGHT_BLOCKED"):
            blocked.validate(now=datetime(2026, 8, 2, tzinfo=UTC))

        with self.assertRaisesRegex(ValueError, "PERFORMANCE_MEASUREMENT_PREFLIGHT_BLOCKED"):
            replace(
                _capacity(),
                tenant_wide_sharepoint_capacity_claim="CLAIMED",
            ).validate(now=datetime(2026, 8, 2, tzinfo=UTC))
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_MEASUREMENT_PREFLIGHT_BLOCKED"):
            replace(
                _capacity(),
                projected_execution_units_gb_seconds=29_999.0,
            ).validate(now=datetime(2026, 8, 2, tzinfo=UTC))
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_MEASUREMENT_PREFLIGHT_BLOCKED"):
            replace(
                _capacity(),
                monitor_evidence_sha256=performance.measurement_policy_sha256(),
            ).validate(now=datetime(2026, 8, 2, tzinfo=UTC))

    def test_refreshed_measurement_cannot_lower_projected_execution_budget(self) -> None:
        approved = _capacity().validate(
            now=datetime(2026, 8, 2, tzinfo=UTC)
        )
        downgraded = {**approved, "projected_execution_units_gb_seconds": 29_999.0}
        self.assertFalse(performance._same_measurement_policy(approved, downgraded))

    def test_runner_journals_attempts_and_classifies_epoch_change(self) -> None:
        clock = _Clock()
        monitor = _Monitor()
        phases = (_phase("cold_epoch_baseline", 1), _phase("cold_epoch_candidate", 1))
        transport = _Transport(
            [
                PerformanceSample(200, 10, True, instance_epoch_sha256="1" * 64),
                PerformanceSample(200, 10, True, instance_epoch_sha256="2" * 64),
            ]
        )
        states: list[dict[str, object]] = []
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            clock=clock,
            phases=phases,
            checkpoint_store=_CheckpointStore(
                lambda state: states.append(json.loads(json.dumps(state)))
            ),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            safety_monitor=monitor,
        )

        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["total_request_count"], 2)
        self.assertEqual(result["summary"]["cold_start_classification"], "VERIFIED")
        self.assertEqual(result["cold_start_classification"], "VERIFIED")
        self.assertEqual(monitor.attempts, [0, 1, 1, 2])
        self.assertEqual(result["global_dispatch_count"], 2)
        self.assertEqual(result["global_dispatch_ceiling"], 500)
        self.assertEqual(result["phase_aggregate_metrics"], result["phases"])
        self.assertTrue(result["server_instance_or_start_epoch_changed"])
        self.assertIsNone(result["abort_reason_code"])
        self.assertEqual(result["endpoint_request_budget_fraction_used"], 1.0)
        self.assertEqual(
            result["tenant_resource_unit_capacity_claim"], "NOT_CLAIMED"
        )
        self.assertTrue(
            any(
                state.get("current_phase", {}).get("reserved_attempt_count") == 1
                and state.get("current_phase", {}).get("completed_attempt_count") == 0
                for state in states
                if isinstance(state.get("current_phase"), dict)
            )
        )

    def test_cold_start_is_inconclusive_without_epoch_change(self) -> None:
        phases = (_phase("cold_epoch_baseline", 1), _phase("cold_epoch_candidate", 1))
        runner = PerformanceAcceptanceRunner(
            transport=_Transport(
                [
                    PerformanceSample(200, 10, True, instance_epoch_sha256="1" * 64),
                    PerformanceSample(200, 10, True, instance_epoch_sha256="1" * 64),
                ]
            ),
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["cold_start_classification"], "INCONCLUSIVE")
        self.assertFalse(result["server_instance_or_start_epoch_changed"])

    def test_predispatch_transport_failure_records_zero_network_dispatches(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport(
            [
                PerformanceSample(
                    0,
                    0,
                    False,
                    "TOKEN_ACQUISITION_FAILED",
                    True,
                    network_dispatched=False,
                )
            ]
        )
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            clock=_Clock(),
            phases=phases,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["global_dispatch_count"], 1)
        self.assertEqual(result["completed_network_dispatch_count"], 0)

    def test_inflight_attempt_is_not_replayed_after_crash(self) -> None:
        phase = _phase("load", 2)
        phases = (phase,)
        captured: dict[str, object] = {}

        def crash_after_reservation(state):
            nonlocal captured
            captured = json.loads(json.dumps(state))
            current = captured.get("current_phase")
            if (
                isinstance(current, dict)
                and current.get("reserved_attempt_count") == 1
                and current.get("completed_attempt_count") == 0
            ):
                raise RuntimeError("simulated crash")

        first_transport = _Transport([PerformanceSample(200, 10, True)])
        first = PerformanceAcceptanceRunner(
            transport=first_transport,
            clock=_Clock(),
            phases=(phase,),
            checkpoint_store=_CheckpointStore(crash_after_reservation),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(RuntimeError, "simulated crash"):
                first.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )
        self.assertEqual(first_transport.calls, 0)

        second_transport = _Transport([PerformanceSample(200, 10, True)])
        second_store = _CheckpointStore()
        second_store.state = captured

        class _UnavailableAuthorization:
            def verify(self, **_values):
                raise AssertionError("authorization must not run during terminalization")

        class _UnavailableCapacity:
            def get_attestation(self):
                raise AssertionError("capacity must not run during terminalization")

        class _UnavailableMonitor:
            def observe(self, *_values):
                raise AssertionError("monitor must not run during terminalization")

        second = PerformanceAcceptanceRunner(
            transport=second_transport,
            clock=_Clock(),
            phases=(phase,),
            checkpoint_store=second_store,
            authorization_verifier=_UnavailableAuthorization(),
            measurement_provider=_UnavailableCapacity(),
            transport_verifier=_TransportVerifier(),
            safety_monitor=_UnavailableMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            result = second.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(second_transport.calls, 0)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"], "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN"
        )
        self.assertEqual(result["summary"]["total_request_count"], 1)
        self.assertEqual(result["summary"]["total_error_count"], 1)
        self.assertEqual(result["completed_network_dispatch_count"], 0)

    def test_transport_boundary_is_durable_before_http_outcome(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        store = _CheckpointStore()

        class _CrashAfterBoundary(_Transport):
            def request(self, *, transport_boundary=None):
                self.calls += 1
                assert transport_boundary is not None
                transport_boundary()
                raise RuntimeError("simulated crash after dispatch boundary")

        first_transport = _CrashAfterBoundary([])
        first = PerformanceAcceptanceRunner(
            transport=first_transport,
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(
                RuntimeError, "simulated crash after dispatch boundary"
            ):
                first.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )

        current = store.state["current_phase"]
        self.assertTrue(current["transport_boundary_crossed"])
        self.assertEqual(store.state["completed_network_dispatch_count"], 1)

        resumed_transport = _Transport([PerformanceSample(200, 10, True)])
        resumed = PerformanceAcceptanceRunner(
            transport=resumed_transport,
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            evidence = resumed.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(evidence["completed_network_dispatch_count"], 1)
        self.assertEqual(
            evidence["abort_reason_code"], "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN"
        )
        self.assertEqual(resumed_transport.calls, 0)

    def test_clean_checkpoint_exception_is_durably_terminalized(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        store = _CheckpointStore()
        runner = PerformanceAcceptanceRunner(
            transport=_Transport([]),
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            state = runner._restore_or_create_state(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                owner_approval_body_sha256="9" * 64,
                approved_measurement_preflight_sha256=capacity_sha256,
                monitor_window_anchor_sha256=MONITOR_WINDOW_ANCHOR_SHA256,
                resume_state=None,
            )
            state["measurement_preflight"] = _capacity().validate(
                now=datetime(2026, 8, 2, tzinfo=UTC)
            )
            state["current_phase"] = runner._new_phase_state(phase)
            store.state = state

            evidence = runner.recover_terminal_evidence(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(evidence["abort_reason_code"], "PERFORMANCE_RUNNER_EXCEPTION")
        self.assertEqual(evidence["global_dispatch_count"], 0)
        self.assertEqual(evidence["completed_network_dispatch_count"], 0)
        self.assertEqual(store.state["status"], "FAILED")
        performance._validate_redacted_evidence(evidence)

    def test_clean_all_phases_complete_checkpoint_resumes_to_passed(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        store = _CheckpointStore()
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
            store.state["status"] = "RUNNING"
            store.state["finished_at_utc"] = None

            evidence = runner.recover_terminal_evidence(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(store.state["status"], "PASSED")
        self.assertEqual(transport.calls, 1)

    def test_resume_honors_persisted_dispatch_deadline_without_catchup(self) -> None:
        phase = replace(_phase("load", 2), interval_seconds=10.0, duration_seconds=30.0)
        phases = (phase,)
        captured: dict[str, object] = {}

        def crash_after_first_completion(state):
            nonlocal captured
            current = state.get("current_phase")
            if (
                isinstance(current, dict)
                and current.get("completed_attempt_count") == 1
                and current.get("next_dispatch_not_before_utc") is not None
            ):
                captured = json.loads(json.dumps(state))
                raise RuntimeError("crash before pacing sleep")

        first = PerformanceAcceptanceRunner(
            transport=_Transport([PerformanceSample(200, 10, True)]),
            checkpoint_store=_CheckpointStore(crash_after_first_completion),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_AdvancingClock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(RuntimeError, "crash before pacing sleep"):
                first.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )

        resumed_clock = _AdvancingClock()
        store = _CheckpointStore()
        store.state = captured
        resumed = PerformanceAcceptanceRunner(
            transport=_Transport([PerformanceSample(200, 10, True)]),
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=resumed_clock,
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            result = resumed.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(result["status"], "PASSED")
        self.assertGreaterEqual(resumed_clock.value, 10.0)

    def test_global_rolling_limit_paces_seventh_dispatch_across_phase_boundary(
        self,
    ) -> None:
        first = replace(
            _phase("first", 6), interval_seconds=10.0, duration_seconds=70.0
        )
        second = replace(_phase("second", 1), duration_seconds=70.0)
        phases = (first, second)
        clock = _AdvancingClock()
        transport = _RecordingTransport(
            [PerformanceSample(200, 10, True) for _ in range(7)], clock
        )
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=clock,
            phases=phases,
            safety_monitor=_Monitor(),
        )

        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(
            transport.dispatch_times,
            [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        )

    def test_resume_preserves_global_rolling_limit_across_phase_boundary(self) -> None:
        first = replace(
            _phase("first", 6), interval_seconds=10.0, duration_seconds=70.0
        )
        second = replace(_phase("second", 1), duration_seconds=70.0)
        phases = (first, second)
        captured: dict[str, object] = {}

        def crash_after_first_phase(state):
            nonlocal captured
            if state.get("completed_phase_ids") == ["first"]:
                captured = json.loads(json.dumps(state))
                raise RuntimeError("crash at phase boundary")

        first_clock = _AdvancingClock()
        first_runner = PerformanceAcceptanceRunner(
            transport=_RecordingTransport(
                [PerformanceSample(200, 10, True) for _ in range(6)], first_clock
            ),
            checkpoint_store=_CheckpointStore(crash_after_first_phase),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=first_clock,
            phases=phases,
            safety_monitor=_Monitor(),
        )

        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(RuntimeError, "crash at phase boundary"):
                first_runner.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )

        self.assertEqual(
            captured["global_next_dispatch_not_before_utc"],
            "2026-08-02T00:01:00Z",
        )
        resumed_clock = _AdvancingClock()
        resumed_clock.value = 50.0
        resumed_transport = _RecordingTransport(
            [PerformanceSample(200, 10, True)], resumed_clock
        )
        resumed_store = _CheckpointStore()
        resumed_store.state = captured
        resumed_runner = PerformanceAcceptanceRunner(
            transport=resumed_transport,
            checkpoint_store=resumed_store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=resumed_clock,
            phases=phases,
            safety_monitor=_Monitor(),
        )

        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            result = resumed_runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(resumed_transport.dispatch_times, [60.0])

    def test_runner_rejects_plan_and_capacity_binding_mismatches(self) -> None:
        activation_hash, plan_sha256, capacity_sha256 = _bindings()
        runner = PerformanceAcceptanceRunner(
            transport=_Transport([]),
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            safety_monitor=_Monitor(),
        )

        with self.assertRaisesRegex(ValueError, "PERFORMANCE_PLAN_BINDING_MISMATCH"):
            runner.run(
                plan_sha256="d" * 64,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        with self.assertRaisesRegex(
            ValueError, "PERFORMANCE_MEASUREMENT_PREFLIGHT_MISMATCH"
        ):
            runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256="e" * 64,
            )

    def test_latency_metrics_boundary(self) -> None:
        metrics = LatencyMetrics()
        for latency in (10, 20, 30, 40, 50):
            metrics.record(PerformanceSample(200, latency, True))
        self.assertEqual(metrics.summary()["latency_ms"]["p95"], 50)

    def test_runner_aborts_immediately_on_transport_or_latency_failure(self) -> None:
        phase = _phase("load", 2)
        phases = (phase,)
        for sample, failure_code in (
            (
                PerformanceSample(0, 10, False, "TRANSPORT_ERROR", True),
                "TRANSPORT_ERROR",
            ),
            (
                PerformanceSample(200, 101, True),
                "PERFORMANCE_REQUEST_LATENCY_EXCEEDED",
            ),
        ):
            with self.subTest(failure_code=failure_code):
                transport = _Transport(
                    [sample, PerformanceSample(200, 10, True)]
                )
                runner = PerformanceAcceptanceRunner(
                    transport=transport,
                    checkpoint_store=_CheckpointStore(),
                    authorization_verifier=_AuthorizationVerifier(),
                    measurement_provider=_MeasurementProvider(),
                    transport_verifier=_TransportVerifier(),
                    clock=_Clock(),
                    phases=phases,
                    safety_monitor=_Monitor(),
                )
                with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
                    activation_hash, plan_sha256, capacity_sha256 = _bindings()
                    result = runner.run(
                        plan_sha256=plan_sha256,
                        contract_sha256=CONTRACT_SHA256,
                        activation_hash=activation_hash,
                        approval_reference=APPROVAL_REFERENCE,
                        correlation_id=CORRELATION_ID,
                        expected_measurement_preflight_sha256=capacity_sha256,
                    )
                self.assertEqual(result["status"], "FAILED")
                self.assertEqual(result["phases"][0]["failure_code"], failure_code)
                self.assertEqual(transport.calls, 1)

    def test_fatal_checkpoint_is_terminalized_without_redispatch_after_crash(self) -> None:
        phase = _phase("load", 2)
        phases = (phase,)
        captured: dict[str, object] = {}

        def crash_after_fatal_checkpoint(state):
            nonlocal captured
            current = state.get("current_phase")
            if isinstance(current, dict) and current.get("fatal_code") == "HTTP_429":
                captured = json.loads(json.dumps(state))
                raise RuntimeError("simulated crash after fatal checkpoint")

        first_transport = _Transport(
            [PerformanceSample(429, 10, True, "HTTP_429", True)]
        )
        first = PerformanceAcceptanceRunner(
            transport=first_transport,
            checkpoint_store=_CheckpointStore(crash_after_fatal_checkpoint),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(
                RuntimeError, "simulated crash after fatal checkpoint"
            ):
                first.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )
        self.assertEqual(first_transport.calls, 1)

        resumed_store = _CheckpointStore()
        resumed_store.state = captured
        resumed_transport = _Transport([PerformanceSample(200, 10, True)])
        resumed = PerformanceAcceptanceRunner(
            transport=resumed_transport,
            checkpoint_store=resumed_store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            result = resumed.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["abort_reason_code"], "HTTP_429")
        self.assertEqual(resumed_transport.calls, 0)

    def test_terminal_failed_checkpoint_rebuilds_evidence_without_reacquire(
        self,
    ) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        captured: dict[str, object] = {}

        def crash_after_terminal_failure(state):
            nonlocal captured
            if state.get("status") == "FAILED" and state.get("current_phase") is None:
                captured = json.loads(json.dumps(state))
                raise RuntimeError("simulated crash after terminal failure")

        first_transport = _Transport(
            [PerformanceSample(429, 10, False, "HTTP_429", True)]
        )
        first = PerformanceAcceptanceRunner(
            transport=first_transport,
            checkpoint_store=_CheckpointStore(crash_after_terminal_failure),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(
                RuntimeError, "simulated crash after terminal failure"
            ):
                first.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )
        self.assertEqual(first_transport.calls, 1)

        class _UnavailableAuthorization:
            def verify(self, **_values):
                raise AssertionError("authorization must not be reacquired")

        class _UnavailableCapacity:
            def get_attestation(self):
                raise AssertionError("measurement must not be reacquired")

        resumed_store = _CheckpointStore()
        resumed_store.state = captured
        resumed_transport = _Transport([PerformanceSample(200, 10, True)])
        resumed = PerformanceAcceptanceRunner(
            transport=resumed_transport,
            checkpoint_store=resumed_store,
            authorization_verifier=_UnavailableAuthorization(),
            measurement_provider=_UnavailableCapacity(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            evidence = resumed.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(evidence["abort_reason_code"], "HTTP_429")
        self.assertEqual(evidence["summary"]["total_request_count"], 1)
        self.assertEqual(resumed_transport.calls, 0)
        with tempfile.TemporaryDirectory() as directory:
            artifact_store = PerformanceArtifactStore(
                Path(directory), plan_sha256
            )
            artifact_store.write_state(captured)
            artifact_store.write_evidence(evidence)
            persisted = json.loads(
                artifact_store.evidence_path.read_text(encoding="utf-8")
            )
        self.assertEqual(persisted["status"], "FAILED")
        self.assertEqual(persisted["phases"][0]["failure_code"], "HTTP_429")

    def test_measurement_attestation_is_refreshed_and_stale_evidence_blocks_dispatch(
        self,
    ) -> None:
        phase = replace(_phase("load", 1), idle_before_seconds=86_401.0)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_AdvancingClock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"], "PERFORMANCE_MEASUREMENT_PREFLIGHT_BLOCKED"
        )
        self.assertEqual(transport.calls, 0)

    def test_global_dispatch_ceiling_blocks_before_request_501(self) -> None:
        phase = _phase("load", 2)
        phases = (phase,)
        transport = _Transport(
            [
                PerformanceSample(200, 10, True),
                PerformanceSample(200, 10, True),
            ]
        )
        monitor = _Monitor()
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=monitor,
        )
        state = {
            "phase_results": [{"request_count": 500}],
            "journal_head_sha256": "0" * 64,
            "journal_event_count": 0,
            "measurement_preflight": _capacity().validate(
                now=datetime(2026, 8, 2, tzinfo=UTC)
            ),
            "runtime_safety": None,
            "monitor_window_anchor_sha256": MONITOR_WINDOW_ANCHOR_SHA256,
            "global_next_dispatch_not_before_utc": None,
        }
        with self.assertRaisesRegex(
            ValueError, "PERFORMANCE_REQUEST_CEILING_REACHED"
        ):
            runner._reserve_dispatch(
                runner._new_phase_state(phase), LatencyMetrics(), state
            )
        self.assertEqual(transport.calls, 0)
        self.assertEqual(monitor.attempts, [])

    def test_artifact_store_writes_only_redacted_aggregate(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        checkpoint = _CheckpointStore()
        runner = PerformanceAcceptanceRunner(
            transport=_Transport(
                [PerformanceSample(429, 10, False, "HTTP_429", True)]
            ),
            checkpoint_store=checkpoint,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            evidence = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), plan_sha256)
            store.write_state(checkpoint.state)
            store.write_evidence(evidence)
            raw = store.evidence_path.read_text(encoding="utf-8")
            self.assertNotIn("Bearer", raw)
            self.assertNotIn("https://", raw)
            self.assertEqual(store.evidence_path.stat().st_mode & 0o077, 0)
            malicious = {**evidence, "url": "https://example.invalid/Bearer secret"}
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_REDACTION_INVALID"
            ):
                store.write_evidence(malicious)
            embedded_jwt = {
                **evidence,
                "started_at_utc": (
                    "prefix eyJhbGciOiJub25lIn0.eyJzdWIiOiJzZWNyZXQifQ.signature suffix"
                ),
            }
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_REDACTION_INVALID"
            ):
                store.write_evidence(embedded_jwt)
            contradictory = json.loads(json.dumps(evidence))
            contradictory["global_dispatch_count"] = 0
            contradictory["summary"]["total_request_count"] = 0
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_REDACTION_INVALID"
            ):
                store.write_evidence(contradictory)
            forged_binding = {**evidence, "activation_hash": "c" * 64}
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_STATE_BINDING_INVALID"
            ):
                store.write_evidence(forged_binding)
            conflated_sources = json.loads(json.dumps(evidence))
            conflated_sources["measurement_preflight"][
                "monitor_evidence_sha256"
            ] = conflated_sources["measurement_preflight"][
                "measurement_policy_sha256"
            ]
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_(?:REDACTION|STATE_BINDING)_INVALID"
            ):
                store.write_evidence(conflated_sources)

    def test_checkpoint_store_detects_state_digest_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "RUNNING"})
            self.assertEqual(store.load_state(), {"status": "RUNNING"})
            commit = json.loads(store.state_commit_path.read_text(encoding="utf-8"))
            store._state_slots[commit["slot"]].write_text(
                '{"status":"PASSED"}\n', encoding="utf-8"
            )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID"
            ):
                store.load_state()

    def test_checkpoint_reader_rejects_symlinked_authoritative_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "RUNNING"})
            commit = json.loads(store.state_commit_path.read_text(encoding="utf-8"))
            slot = store._state_slots[commit["slot"]]
            foreign = store.run_dir / "foreign-state.json"
            foreign.write_text('{"status":"RUNNING"}\n', encoding="utf-8")
            foreign.chmod(0o600)
            slot.unlink()
            slot.symlink_to(foreign)
            with self.assertRaisesRegex(ValueError, "PERFORMANCE_STATE_INVALID"):
                store.load_state()

    def test_checkpoint_store_rejects_symlink_in_any_ancestor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external"
            external.mkdir(mode=0o700)
            linked = root / "linked"
            linked.symlink_to(external, target_is_directory=True)
            store = PerformanceArtifactStore(linked / "nested", SHA256)

            with self.assertRaisesRegex(ValueError, "PERFORMANCE_STATE_INVALID"):
                store.write_state({"status": "RUNNING"})

            self.assertEqual(list(external.iterdir()), [])

    def test_checkpoint_store_rejects_unsafe_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "RUNNING"})
            store.run_dir.chmod(0o755)
            try:
                with self.assertRaisesRegex(ValueError, "PERFORMANCE_STATE_INVALID"):
                    store.load_state()
                with self.assertRaisesRegex(ValueError, "PERFORMANCE_STATE_INVALID"):
                    store.write_state({"status": "FAILED"})
            finally:
                store.run_dir.chmod(0o700)

    def test_checkpoint_commit_pointer_survives_mirror_write_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "FIRST"})
            original = performance._atomic_json_write

            def interrupt_mirror(path, value):
                if path == store.state_path:
                    raise OSError("simulated mirror interruption")
                return original(path, value)

            with patch.object(
                performance, "_atomic_json_write", side_effect=interrupt_mirror
            ):
                with self.assertRaisesRegex(OSError, "mirror interruption"):
                    store.write_state({"status": "SECOND"})
            self.assertEqual(store.load_state(), {"status": "SECOND"})

    def test_checkpoint_orphan_slot_does_not_replace_committed_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "FIRST"})
            original = performance._atomic_json_write

            def interrupt_commit(path, value):
                if path == store.state_commit_path:
                    raise OSError("simulated commit interruption")
                return original(path, value)

            with patch.object(
                performance, "_atomic_json_write", side_effect=interrupt_commit
            ):
                with self.assertRaisesRegex(OSError, "commit interruption"):
                    store.write_state({"status": "SECOND"})
            self.assertEqual(store.load_state(), {"status": "FIRST"})

    def test_checkpoint_slot_interruption_keeps_previous_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "FIRST"})
            original = performance._atomic_json_write

            def interrupt_slot(path, value):
                if path in store._state_slots.values():
                    raise OSError("simulated slot interruption")
                return original(path, value)

            with patch.object(
                performance, "_atomic_json_write", side_effect=interrupt_slot
            ):
                with self.assertRaisesRegex(OSError, "slot interruption"):
                    store.write_state({"status": "SECOND"})
            self.assertEqual(store.load_state(), {"status": "FIRST"})

    def test_checkpoint_digest_mirror_interruption_keeps_new_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), SHA256)
            store.write_state({"status": "FIRST"})
            original = performance._atomic_text_write

            def interrupt_digest(path, value):
                if path == store.state_digest_path:
                    raise OSError("simulated digest interruption")
                return original(path, value)

            with patch.object(
                performance, "_atomic_text_write", side_effect=interrupt_digest
            ):
                with self.assertRaisesRegex(OSError, "digest interruption"):
                    store.write_state({"status": "SECOND"})
            self.assertEqual(store.load_state(), {"status": "SECOND"})

    def test_passed_evidence_requires_the_exact_500_request_phase_plan(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        checkpoint = _CheckpointStore()
        runner = PerformanceAcceptanceRunner(
            transport=_Transport([PerformanceSample(200, 10, True)]),
            checkpoint_store=checkpoint,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            evidence = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(evidence["status"], "PASSED")
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), plan_sha256)
            store.write_state(checkpoint.state)
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_REDACTION_INVALID"
            ):
                store.write_evidence(evidence)

    def test_canonical_passed_phase_rejects_false_latency_idle_and_duration(self) -> None:
        cold = performance.PHASES[1]
        aggregate = {
            "mode": cold.mode,
            "error_rate": 0.0,
            "idle_elapsed_seconds": cold.idle_before_seconds,
            "active_elapsed_seconds": 0.5,
            "latency_ms": {"p50": 1, "p95": 1, "p99": 1, "max": 1},
        }
        self.assertTrue(
            performance._canonical_passed_phase_matches(cold, aggregate)
        )
        self.assertFalse(
            performance._canonical_passed_phase_matches(
                cold, {**aggregate, "idle_elapsed_seconds": 0.0}
            )
        )
        self.assertFalse(
            performance._canonical_passed_phase_matches(
                cold,
                {
                    **aggregate,
                    "latency_ms": {
                        "p50": 1,
                        "p95": cold.max_p95_ms + 1,
                        "p99": 1,
                        "max": 1,
                    },
                },
            )
        )
        load = performance.PHASES[3]
        self.assertFalse(
            performance._canonical_passed_phase_matches(
                load,
                {
                    **aggregate,
                    "idle_elapsed_seconds": 0.0,
                    "active_elapsed_seconds": load.duration_seconds + 1.0,
                },
            )
        )

    def test_artifact_store_rejects_checkpoint_consistent_false_passed_metrics(
        self,
    ) -> None:
        activation_hash, plan_sha256, capacity_sha256 = _bindings()
        plan = build_performance_acceptance_plan(
            activation_hash, CONTRACT_SHA256
        )
        capacity = _capacity().validate(
            now=datetime(2026, 8, 2, tzinfo=UTC)
        )
        runtime_safety = replace(
            _Monitor().observe(500, capacity["attestation_sha256"]),
            projected_remaining_execution_units_gb_seconds=1_800.0,
        ).validate(now=datetime(2026, 8, 2, tzinfo=UTC))
        phases = []
        for index, spec in enumerate(performance.PHASES):
            phases.append(
                {
                    "phase_id": spec.phase_id,
                    "mode": spec.mode,
                    "request_limit": spec.request_limit,
                    "idle_elapsed_seconds": spec.idle_before_seconds,
                    "active_elapsed_seconds": spec.duration_seconds,
                    "checkpoint_count": spec.request_limit * 2,
                    "reserved_attempt_count": spec.request_limit,
                    "completed_attempt_count": spec.request_limit,
                    "instance_epoch_sha256": (
                        f"{index + 1}" * 64 if index < 2 else None
                    ),
                    "request_count": spec.request_limit,
                    "error_count": 0,
                    "error_rate": 0.0,
                    "latency_ms": {"p50": 1, "p95": 1, "p99": 1, "max": 1},
                    "status_counts": {"200": spec.request_limit},
                    "error_codes": {},
                    "status": "PASSED",
                }
            )
        state = {
            "schema_version": performance.STATE_SCHEMA_VERSION,
            "status": "PASSED",
            "plan_sha256": plan_sha256,
            "contract_sha256": CONTRACT_SHA256,
            "activation_hash": activation_hash,
            "owner_approval_body_sha256": "9" * 64,
            "approved_measurement_preflight_sha256": capacity_sha256,
            "target_binding_sha256": plan["target_binding_sha256"],
            "phase_plan_sha256": plan["phase_plan_sha256"],
            "started_at_utc": "2026-08-02T00:00:00Z",
            "finished_at_utc": "2026-08-03T00:00:00Z",
            "completed_phase_ids": [spec.phase_id for spec in performance.PHASES],
            "current_phase": None,
            "phase_results": phases,
            "measurement_preflight": capacity,
            "runtime_safety": runtime_safety,
            "completed_network_dispatch_count": 500,
            "journal_head_sha256": "8" * 64,
            "journal_event_count": 1_000,
        }
        runner = PerformanceAcceptanceRunner(
            transport=_Transport([]),
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            safety_monitor=_Monitor(),
        )
        evidence = runner._evidence(state, idempotent=False)
        self.assertEqual(
            evidence["projected_remaining_execution_units_gb_seconds"],
            0.0,
        )
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceArtifactStore(Path(directory), plan_sha256)
            store.write_state(state)
            store.write_evidence(evidence)

            forged_state = json.loads(json.dumps(state))
            forged_state["phase_results"][2]["latency_ms"]["p95"] = 999_999
            forged_evidence = runner._evidence(forged_state, idempotent=False)
            store.write_state(forged_state)
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_REDACTION_INVALID"
            ):
                store.write_evidence(forged_evidence)
    def test_owner_and_activation_are_verified_before_authorization(self) -> None:
        approval_verifier = _github_approval_verifier()
        with (
            patch(
                "nac_bff.azure_performance_acceptance._sha256_file",
                return_value=CONTRACT_SHA256,
            ),
            patch(
                "nac_bff.azure_performance_acceptance.verify_activation_success",
                return_value={
                    "status": "VERIFIED",
                    "activation_hash": "b" * 64,
                    "receipt_sha256": "4" * 64,
                    "evidence_sha256": "5" * 64,
                    "activated_function_base_url_sha256": hashlib.sha256(
                        b"https://func-nac-bff-test-funktion8.azurewebsites.net"
                    ).hexdigest(),
                    "activated_workspace_id_sha256": hashlib.sha256(
                        b"notary_team_01"
                    ).hexdigest(),
                    "activated_matter_id_sha256": hashlib.sha256(
                        b"NAC-SYN-MATTER-001"
                    ).hexdigest(),
                },
            ),
            patch(
                "nac_bff.azure_performance_owner_gate."
                "measure_performance_infrastructure_approval",
                return_value={
                    "contract_sha256": CONTRACT_SHA256,
                    "infrastructure_approval": INFRASTRUCTURE_APPROVAL,
                },
            ),
            patch.object(
                GitHubApprovalVerifier,
                "verify_performance_owner_comment",
                side_effect=lambda **values: _ApprovalVerifier().verify_performance_owner_comment(
                    **values
                ),
            ),
        ):
            authorization = verify_performance_execution_authorization(
                repo_root=Path("."),
                approval_verifier=approval_verifier,
                approval_reference=(
                    "https://github.com/notariat8/NaC/issues/735#issuecomment-1"
                ),
                contract_sha256=CONTRACT_SHA256,
                activation_hash="b" * 64,
                measurement_preflight_sha256="c" * 64,
                correlation_id="nac-bff-performance-20260802",
                infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                toolchain_attestations={},
                infrastructure_parameters={},
                worm_baseline_parameters={},
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_OWNER_VERIFIER_INVALID"
            ):
                verify_performance_execution_authorization(
                    repo_root=Path("."),
                    approval_verifier=_ApprovalVerifier(),
                    approval_reference=APPROVAL_REFERENCE,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash="b" * 64,
                    measurement_preflight_sha256="c" * 64,
                    correlation_id=CORRELATION_ID,
                    infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                    toolchain_attestations={},
                    infrastructure_parameters={},
                    worm_baseline_parameters={},
                    monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
                )
        self.assertEqual(authorization.status, "VERIFIED")
        with patch(
            "nac_bff.azure_performance_acceptance._sha256_file",
            return_value=CONTRACT_SHA256,
        ), patch(
            "nac_bff.azure_performance_owner_gate."
            "measure_performance_infrastructure_approval",
            return_value={
                "contract_sha256": CONTRACT_SHA256,
                "infrastructure_approval": INFRASTRUCTURE_APPROVAL,
            },
        ), patch.object(
            GitHubApprovalVerifier,
            "verify_performance_owner_comment",
            side_effect=lambda **values: _ApprovalVerifier(
                status="FAILED"
            ).verify_performance_owner_comment(**values),
        ):
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_OWNER_APPROVAL_INVALID"
            ):
                    verify_performance_execution_authorization(
                        repo_root=Path("."),
                        approval_verifier=approval_verifier,
                    approval_reference=(
                        "https://github.com/notariat8/NaC/issues/735#issuecomment-1"
                    ),
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash="b" * 64,
                    measurement_preflight_sha256="c" * 64,
                    correlation_id="nac-bff-performance-20260802",
                    infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                    toolchain_attestations={},
                    infrastructure_parameters={},
                    worm_baseline_parameters={},
                    monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
                )

    def test_bound_preflight_adds_verified_infrastructure_evidence_before_lease(
        self,
    ) -> None:
        verifier = _test_bound_verifier(
            repo_root=Path("."),
            approval_verifier=_ApprovalVerifier(),
            infrastructure_approval=INFRASTRUCTURE_APPROVAL,
            toolchain_attestations={},
            infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
            worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
            monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            infrastructure_safety_readback=lambda: {"sealed": "readback-input"},
        )
        authorization = _authorization("b" * 64, "0" * 64)
        safety = _test_safety_verification({
            "status": "SAFE",
            "owner_binding_sha256": authorization.owner_approval_body_sha256,
            "target_binding_sha256": authorization.target_binding_sha256,
            "infrastructure_safety_policy_sha256": "8" * 64,
            "infrastructure_safety_evidence_sha256": "d" * 64,
            "tenant_id": INFRASTRUCTURE_PARAMETERS["tenantId"],
            "subscription_id": INFRASTRUCTURE_PARAMETERS["subscriptionId"],
            "resource_group_name": INFRASTRUCTURE_PARAMETERS[
                "resourceGroupName"
            ],
            "location": INFRASTRUCTURE_PARAMETERS["location"],
            "coordination_storage_account_name": INFRASTRUCTURE_PARAMETERS[
                "storageAccountName"
            ],
            "coordination_storage_account_resource_id": (
                f"/subscriptions/{INFRASTRUCTURE_PARAMETERS['subscriptionId']}/"
                f"resourceGroups/{INFRASTRUCTURE_PARAMETERS['resourceGroupName']}/"
                "providers/Microsoft.Storage/storageAccounts/"
                f"{INFRASTRUCTURE_PARAMETERS['storageAccountName']}"
            ),
            "bff_storage_account_resource_id": INFRASTRUCTURE_PARAMETERS[
                "bffStorageAccountResourceId"
            ],
            "worm_storage_account_resource_id": INFRASTRUCTURE_PARAMETERS[
                "wormStorageAccountResourceId"
            ],
            "broker_principal_id": BROKER_PRINCIPAL_ID,
            "broker_caller_service_principal_id": INFRASTRUCTURE_PARAMETERS[
                "brokerCallerServicePrincipalId"
            ],
            "broker_function_app_resource_id": INFRASTRUCTURE_PARAMETERS[
                "brokerFunctionAppResourceId"
            ],
            "broker_function_package_sha256": INFRASTRUCTURE_PARAMETERS[
                "brokerFunctionPackageSha256"
            ],
            "broker_ticket_verification_certificate_sha256": (
                INFRASTRUCTURE_PARAMETERS[
                    "brokerTicketVerificationCertificateSha256"
                ]
            ),
            "tags_sha256": performance._sha256_json(
                INFRASTRUCTURE_PARAMETERS["tags"]
            ),
            "broker_private_network_boundary_sha256": performance._sha256_json(
                {
                    "virtualNetworkResourceId": INFRASTRUCTURE_PARAMETERS[
                        "brokerVirtualNetworkResourceId"
                    ],
                    "functionIntegrationSubnetResourceId": INFRASTRUCTURE_PARAMETERS[
                        "brokerFunctionIntegrationSubnetResourceId"
                    ],
                    "privateEndpointSubnetResourceId": INFRASTRUCTURE_PARAMETERS[
                        "brokerPrivateEndpointSubnetResourceId"
                    ],
                }
            ),
            "toolchain_attestations_sha256": INFRASTRUCTURE_APPROVAL[
                "toolchain_attestations_sha256"
            ],
        })
        with (
            patch.object(verifier, "verify", return_value=authorization),
            patch.object(
                VerifiedInfrastructureSafetySource,
                "_verify",
                return_value=safety,
            ),
            patch(
                "nac_bff.azure_performance_authorization."
                "validate_infrastructure_safety_evidence",
                return_value=safety,
            ),
            patch(
                "nac_bff.azure_performance_owner_gate."
                "measure_performance_infrastructure_approval",
                return_value={
                    "contract_sha256": CONTRACT_SHA256,
                    "infrastructure_approval": INFRASTRUCTURE_APPROVAL,
                },
            ),
        ):
            result = verifier.verify_owner_and_infrastructure_before_lease(
                approval_reference=APPROVAL_REFERENCE,
                contract_sha256=CONTRACT_SHA256,
                activation_hash="b" * 64,
                correlation_id=CORRELATION_ID,
                lease_binding_sha256="e" * 64,
                lease_acquisition_safety_evidence_sha256="a" * 64,
            )

        bindings = dict(result.execution_bindings)
        self.assertEqual(
            bindings["infrastructure_safety_evidence_sha256"], "d" * 64
        )
        plan = build_performance_acceptance_plan("b" * 64, CONTRACT_SHA256)
        self.assertEqual(
            set(bindings),
            {
                *INFRASTRUCTURE_APPROVAL,
                "contract_sha256",
                "expected_activation_hash",
                "phase_plan_sha256",
                "measurement_policy_sha256",
                "monitor_policy_sha256",
                "lease_policy_sha256",
                "lease_broker_policy_sha256",
                "monitor_window_anchor_sha256",
                "owner_approval_body_sha256",
                "target_binding_sha256",
                "infrastructure_safety_evidence_sha256",
                "lease_binding_sha256",
                "lease_acquisition_safety_evidence_sha256",
            },
        )
        for key in (
            "phase_plan_sha256",
            "measurement_policy_sha256",
            "monitor_policy_sha256",
            "lease_policy_sha256",
            "lease_broker_policy_sha256",
            "target_binding_sha256",
        ):
            self.assertEqual(bindings[key], plan[key])
        self.assertEqual(bindings["lease_binding_sha256"], "e" * 64)
        self.assertEqual(
            bindings["lease_acquisition_safety_evidence_sha256"], "a" * 64
        )

    def test_bound_bootstrap_authority_rejects_all_cross_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            verifier = _test_bound_verifier(
                repo_root=root,
                approval_verifier=_ApprovalVerifier(),
                infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                toolchain_attestations={},
                infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
                worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
                infrastructure_safety_readback=lambda: {"sealed": "readback-input"},
            )
            authorization = _authorization("b" * 64, "0" * 64)
            safety = _test_safety_verification(
                _bound_safety_evidence(authorization.target_binding_sha256)
            )
            bootstrap_binding_sha256 = "e" * 64
            with (
                patch.object(verifier, "verify", return_value=authorization),
                patch.object(
                    VerifiedInfrastructureSafetySource,
                    "_verify",
                    return_value=safety,
                ),
                patch(
                    "nac_bff.azure_performance_authorization."
                    "validate_infrastructure_safety_evidence",
                    return_value=safety,
                ),
                patch(
                    "nac_bff.azure_performance_owner_gate."
                    "measure_performance_infrastructure_approval",
                    return_value={
                        "contract_sha256": CONTRACT_SHA256,
                        "infrastructure_approval": INFRASTRUCTURE_APPROVAL,
                    },
                ),
            ):
                authority = verifier.verify_owner_and_infrastructure_before_bootstrap(
                    approval_reference=APPROVAL_REFERENCE,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash="b" * 64,
                    correlation_id=CORRELATION_ID,
                    bootstrap_binding_sha256=bootstrap_binding_sha256,
                )

            live_authorization._authorize_live_action(
                authority.capability,
                action=live_authorization.BLOB_BOOTSTRAP,
                target_binding_sha256=authorization.target_binding_sha256,
                binding_sha256=bootstrap_binding_sha256,
                consume=False,
            )
            plan = build_performance_acceptance_plan("b" * 64, CONTRACT_SHA256)
            for action, binding in (
                (live_authorization.TARGET_GET, authorization.target_binding_sha256),
                (live_authorization.MONITOR_READ, plan["monitor_policy_sha256"]),
                (live_authorization.BLOB_LEASE_ACQUIRE, bootstrap_binding_sha256),
                (live_authorization.BLOB_LEASE_ASSERT_HELD, bootstrap_binding_sha256),
                (live_authorization.BLOB_LEASE_RELEASE, bootstrap_binding_sha256),
            ):
                with self.subTest(action=action), self.assertRaisesRegex(
                    ValueError,
                    "^PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH$",
                ):
                    live_authorization._authorize_live_action(
                        authority.capability,
                        action=action,
                        target_binding_sha256=authorization.target_binding_sha256,
                        binding_sha256=binding,
                        consume=True,
                    )
            self.assertFalse(
                (root / live_authorization.AUTHORIZATION_USAGE_ROOT).exists()
            )

    def test_bound_preflight_rejects_safety_evidence_for_another_target(self) -> None:
        verifier = _test_bound_verifier(
            repo_root=Path("."),
            approval_verifier=_ApprovalVerifier(),
            infrastructure_approval=INFRASTRUCTURE_APPROVAL,
            toolchain_attestations={},
            infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
            worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
            monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            infrastructure_safety_readback=lambda: {"sealed": "readback-input"},
        )
        authorization = _authorization("b" * 64, "0" * 64)
        safety = {
            "status": "SAFE",
            "target_binding_sha256": "0" * 64,
            "infrastructure_safety_policy_sha256": "8" * 64,
            "infrastructure_safety_evidence_sha256": "d" * 64,
        }
        with (
            patch.object(verifier, "verify", return_value=authorization),
            patch.object(
                VerifiedInfrastructureSafetySource,
                "_verify",
                return_value=safety,
            ),
            self.assertRaisesRegex(
                ValueError, "PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID"
            ),
        ):
            verifier.verify_owner_and_infrastructure_before_lease(
                approval_reference=APPROVAL_REFERENCE,
                contract_sha256=CONTRACT_SHA256,
                activation_hash="b" * 64,
                correlation_id=CORRELATION_ID,
                lease_binding_sha256="e" * 64,
                lease_acquisition_safety_evidence_sha256="a" * 64,
            )

    def test_bound_preflight_rejects_safety_evidence_for_other_resources(self) -> None:
        verifier = _test_bound_verifier(
            repo_root=Path("."),
            approval_verifier=_ApprovalVerifier(),
            infrastructure_approval=INFRASTRUCTURE_APPROVAL,
            toolchain_attestations={},
            infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
            worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
            monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            infrastructure_safety_readback=lambda: {"sealed": "readback-input"},
        )
        authorization = _authorization("b" * 64, "0" * 64)
        safety = _bound_safety_evidence(authorization.target_binding_sha256)
        safety["subscription_id"] = "99999999-6cb9-4278-88ee-e80377cd951c"
        with (
            patch.object(verifier, "verify", return_value=authorization),
            patch.object(
                VerifiedInfrastructureSafetySource,
                "_verify",
                return_value=safety,
            ),
            self.assertRaisesRegex(
                ValueError, "PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID"
            ),
        ):
            verifier.verify_owner_and_infrastructure_before_lease(
                approval_reference=APPROVAL_REFERENCE,
                contract_sha256=CONTRACT_SHA256,
                activation_hash="b" * 64,
                correlation_id=CORRELATION_ID,
                lease_binding_sha256="e" * 64,
                lease_acquisition_safety_evidence_sha256="a" * 64,
            )

    def test_bound_preflight_rejects_foreign_owner_bound_safety_evidence(self) -> None:
        verifier = _test_bound_verifier(
            repo_root=Path("."),
            approval_verifier=_ApprovalVerifier(),
            infrastructure_approval=INFRASTRUCTURE_APPROVAL,
            toolchain_attestations={},
            infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
            worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
            monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            infrastructure_safety_readback=lambda: {"sealed": "readback-input"},
        )
        authorization = _authorization("b" * 64, "0" * 64)
        safety = _bound_safety_evidence(authorization.target_binding_sha256)
        safety["owner_binding_sha256"] = "f" * 64
        with (
            patch.object(verifier, "verify", return_value=authorization),
            patch.object(
                VerifiedInfrastructureSafetySource,
                "_verify",
                return_value=safety,
            ),
            self.assertRaisesRegex(
                ValueError, "PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID"
            ),
        ):
            verifier.verify_owner_and_infrastructure_before_lease(
                approval_reference=APPROVAL_REFERENCE,
                contract_sha256=CONTRACT_SHA256,
                activation_hash="b" * 64,
                correlation_id=CORRELATION_ID,
                lease_binding_sha256="e" * 64,
                lease_acquisition_safety_evidence_sha256="a" * 64,
            )

    def test_bound_preflight_remeasures_after_slow_readback(self) -> None:
        verifier = _test_bound_verifier(
            repo_root=Path("."),
            approval_verifier=_ApprovalVerifier(),
            infrastructure_approval=INFRASTRUCTURE_APPROVAL,
            toolchain_attestations={},
            infrastructure_parameters=INFRASTRUCTURE_PARAMETERS,
            worm_baseline_parameters=WORM_BASELINE_PARAMETERS,
            monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            infrastructure_safety_readback=lambda: {"sealed": "readback-input"},
        )
        authorization = _authorization("b" * 64, "0" * 64)
        safety = _bound_safety_evidence(authorization.target_binding_sha256)
        drifted = {
            **INFRASTRUCTURE_APPROVAL,
            "approved_tree_sha": "a" * 40,
        }
        with (
            patch.object(verifier, "verify", return_value=authorization),
            patch.object(
                VerifiedInfrastructureSafetySource,
                "_verify",
                return_value=safety,
            ),
            patch(
                "nac_bff.azure_performance_owner_gate."
                "measure_performance_infrastructure_approval",
                return_value={
                    "contract_sha256": CONTRACT_SHA256,
                    "infrastructure_approval": drifted,
                },
            ),
            self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EXECUTION_BINDING_MISMATCH"
            ),
        ):
            verifier.verify_owner_and_infrastructure_before_lease(
                approval_reference=APPROVAL_REFERENCE,
                contract_sha256=CONTRACT_SHA256,
                activation_hash="b" * 64,
                correlation_id=CORRELATION_ID,
                lease_binding_sha256="e" * 64,
                lease_acquisition_safety_evidence_sha256="a" * 64,
            )

    def test_authorization_remeasures_tree_after_immutable_comment_verification(
        self,
    ) -> None:
        drifted_approval = {
            **INFRASTRUCTURE_APPROVAL,
            "approved_tree_sha": "a" * 40,
        }

        approval = _github_approval_verifier()
        approval_calls = 0

        def verify_owner(**values):
            nonlocal approval_calls
            approval_calls += 1
            return _ApprovalVerifier().verify_performance_owner_comment(**values)

        with (
            patch(
                "nac_bff.azure_performance_acceptance._sha256_file",
                return_value=CONTRACT_SHA256,
            ),
            patch(
                "nac_bff.azure_performance_owner_gate."
                "measure_performance_infrastructure_approval",
                side_effect=(
                    {
                        "contract_sha256": CONTRACT_SHA256,
                        "infrastructure_approval": INFRASTRUCTURE_APPROVAL,
                    },
                    {
                        "contract_sha256": CONTRACT_SHA256,
                        "infrastructure_approval": drifted_approval,
                    },
                ),
            ) as measure,
            patch(
                "nac_bff.azure_performance_acceptance.verify_activation_success"
            ) as activation,
            patch.object(
                GitHubApprovalVerifier,
                "verify_performance_owner_comment",
                side_effect=verify_owner,
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EXECUTION_BINDING_MISMATCH"
            ):
                verify_performance_execution_authorization(
                    repo_root=Path("."),
                    approval_verifier=approval,
                    approval_reference=APPROVAL_REFERENCE,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash="b" * 64,
                    measurement_preflight_sha256="c" * 64,
                    correlation_id=CORRELATION_ID,
                    infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                    toolchain_attestations={},
                    infrastructure_parameters={},
                    worm_baseline_parameters={},
                    monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
                )
        self.assertEqual(approval_calls, 1)
        self.assertEqual(measure.call_count, 2)
        activation.assert_not_called()

    def test_authorization_rejects_activation_for_another_fixed_target(self) -> None:
        approval = _github_approval_verifier()
        with (
            patch(
                "nac_bff.azure_performance_acceptance._sha256_file",
                return_value=CONTRACT_SHA256,
            ),
            patch(
                "nac_bff.azure_performance_acceptance.verify_activation_success",
                return_value={
                "status": "VERIFIED",
                "activation_hash": "b" * 64,
                "receipt_sha256": "4" * 64,
                "evidence_sha256": "5" * 64,
                "activated_function_base_url_sha256": "6" * 64,
                "activated_workspace_id_sha256": hashlib.sha256(
                    b"notary_team_01"
                ).hexdigest(),
                "activated_matter_id_sha256": hashlib.sha256(
                    b"NAC-SYN-MATTER-001"
                ).hexdigest(),
                },
            ),
            patch(
                "nac_bff.azure_performance_owner_gate."
                "measure_performance_infrastructure_approval",
                return_value={
                    "contract_sha256": CONTRACT_SHA256,
                    "infrastructure_approval": INFRASTRUCTURE_APPROVAL,
                },
            ),
            patch.object(
                GitHubApprovalVerifier,
                "verify_performance_owner_comment",
                side_effect=lambda **values: _ApprovalVerifier().verify_performance_owner_comment(
                    **values
                ),
            ),
        ):
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_ACTIVATION_TARGET_MISMATCH"
            ):
                verify_performance_execution_authorization(
                    repo_root=Path("."),
                    approval_verifier=approval,
                    approval_reference=APPROVAL_REFERENCE,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash="b" * 64,
                    measurement_preflight_sha256="c" * 64,
                    correlation_id=CORRELATION_ID,
                    infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                    toolchain_attestations={},
                    infrastructure_parameters={},
                    worm_baseline_parameters={},
                    monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
                )

    def test_authorization_rejects_non_repository_contract_digest(self) -> None:
        with self.assertRaisesRegex(
            ValueError, "PERFORMANCE_CONTRACT_BINDING_MISMATCH"
        ):
            verify_performance_execution_authorization(
                repo_root=Path("."),
                approval_verifier=_ApprovalVerifier(),
                approval_reference=APPROVAL_REFERENCE,
                contract_sha256="0" * 64,
                activation_hash="b" * 64,
                measurement_preflight_sha256="c" * 64,
                correlation_id=CORRELATION_ID,
                infrastructure_approval=INFRASTRUCTURE_APPROVAL,
                toolchain_attestations={},
                infrastructure_parameters={},
                worm_baseline_parameters={},
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

    def test_activation_receipt_must_bind_actual_committed_artifacts(self) -> None:
        activation_hash = "b" * 64
        receipt = {
            "schema_version": azure_activation_runner.SUCCESS_RECEIPT_SCHEMA_VERSION,
            "status": "COMMITTED",
            "activation_hash": activation_hash,
            "approval_body_sha256": "1" * 64,
            "approval_reference_sha256": "2" * 64,
            "approved_commit_sha": "3" * 40,
            "approved_tree_sha": "4" * 40,
            "provisioner_bootstrap_binding_sha256": "5" * 64,
            "toolchain_attestations_sha256": "6" * 64,
            "target_binding_sha256": "7" * 64,
            "evidence_sha256": "8" * 64,
            "final_commit_marker_sha256": "9" * 64,
            "final_state_sha256": "a" * 64,
        }
        receipt["receipt_sha256"] = azure_activation_runner._sha256_json(receipt)
        evidence = {
            "status": "PASSED",
            "activation_hash": activation_hash,
            "approval_reference_sha256": receipt["approval_reference_sha256"],
            "approved_commit_sha": receipt["approved_commit_sha"],
            "approved_tree_sha": receipt["approved_tree_sha"],
            "provisioner_bootstrap_binding_sha256": receipt[
                "provisioner_bootstrap_binding_sha256"
            ],
            "toolchain_attestations_sha256": receipt[
                "toolchain_attestations_sha256"
            ],
            "target_binding_sha256": receipt["target_binding_sha256"],
            "ledger_head_sha256": "c" * 64,
            "summary": {
                "passed_step_count": 12,
                "required_step_count": 12,
                "failed_step_count": 0,
                "synthetic_state_restored": True,
                "assigned_access_passed": True,
                "deputy_access_passed": True,
                "denied_access_passed": True,
            },
        }
        state = {
            "status": "PASSED",
            "activation_hash": activation_hash,
            "target_binding_sha256": receipt["target_binding_sha256"],
            "ledger_head_sha256": evidence["ledger_head_sha256"],
        }

        def read_artifact(path):
            if path.name == "activation.success-receipt.redacted.json":
                return receipt
            if path.name == "activation.redacted.json":
                return evidence
            if path.name == "resume-state.redacted.json":
                return state
            return None

        def artifact_sha(path):
            return {
                "activation.redacted.json": "f" * 64,
                "activation.commit.redacted.json": "9" * 64,
                "resume-state.redacted.json": "a" * 64,
            }.get(path.name)

        with tempfile.TemporaryDirectory() as directory, patch.object(
            azure_activation_runner,
            "_read_secure_canonical_json",
            side_effect=read_artifact,
        ), patch.object(
            azure_activation_runner, "_artifact_sha256", side_effect=artifact_sha
        ), patch.object(
            azure_activation_runner, "_validate_evidence"
        ), patch.object(
            azure_activation_runner, "_final_commit_marker_matches", return_value=True
        ), patch.object(
            azure_activation_runner, "_terminal_chain_is_valid", return_value=True
        ):
            with self.assertRaisesRegex(
                ValueError, "ACTIVATION_SUCCESS_RECEIPT_INVALID"
            ):
                verify_activation_success(Path(directory), activation_hash)

    def test_github_verifier_accepts_only_immutable_issue_733_comment(self) -> None:
        reference = "https://github.com/notariat8/NaC/issues/735#issuecomment-1"
        expected = build_owner_comment(
            CONTRACT_SHA256,
            "b" * 64,
            "nac-bff-performance-20260802",
            INFRASTRUCTURE_APPROVAL,
            MONITOR_WINDOW_ANCHOR,
        )
        verifier = object.__new__(GitHubApprovalVerifier)
        verifier._binary = Path("/usr/bin/true")
        verifier._env = {}
        comment = {
            "html_url": reference,
            "created_at": "2026-08-02T00:00:00Z",
            "updated_at": "2026-08-02T00:00:00Z",
            "body": expected["body"],
            "author_association": "OWNER",
            "user": {"login": "ofunk"},
        }
        with patch.object(verifier, "_gh_json", return_value=comment):
            result = verifier.verify_performance_owner_comment(
                reference=reference,
                expected_body=expected["body"],
                expected_body_sha256=expected["body_sha256"],
            )
            rejected = verifier.verify_performance_owner_comment(
                reference=(
                    "https://github.com/notariat8/NaC/issues/717#issuecomment-1"
                ),
                expected_body=expected["body"],
                expected_body_sha256=expected["body_sha256"],
            )
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(rejected["status"], "FAILED")

    def test_runner_requires_checkpoint_authorization_and_target_binding(self) -> None:
        with self.assertRaises(TypeError):
            PerformanceAcceptanceRunner(  # type: ignore[call-arg]
                transport=_Transport([]), safety_monitor=_Monitor()
            )
        activation_hash, plan_sha256, capacity_sha256 = _bindings()
        class _BadTransport(_Transport):
            @property
            def target_binding_sha256(self) -> str:
                return "0" * 64

        bad_transport = _BadTransport([])
        runner = PerformanceAcceptanceRunner(
            transport=bad_transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            safety_monitor=_Monitor(),
        )
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_TARGET_BINDING_MISMATCH"):
            runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        class _RejectingAuthorizationVerifier:
            def verify(self, **_values):
                raise ValueError("PERFORMANCE_OWNER_APPROVAL_INVALID")

        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_RejectingAuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            safety_monitor=_Monitor(),
        )
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_OWNER_APPROVAL_INVALID"):
            runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(transport.calls, 0)

    def test_fixed_transport_binding_requires_production_transport_type(self) -> None:
        verifier = FixedTransportBindingVerifier()
        transport = FixedBffPerformanceTransport(
            SimpleNamespace(get_token=_attested_m365_token)
        )
        verifier.verify(transport, transport.target_binding_sha256)
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_TARGET_BINDING_MISMATCH"):
            verifier.verify(_Transport([]), transport.target_binding_sha256)
        with self.assertRaisesRegex(TypeError, "opener"):
            FixedBffPerformanceTransport(
                SimpleNamespace(get_token=_attested_m365_token),
                opener=SimpleNamespace(),
            )

    def test_fixed_transport_rejects_endpoint_drift_before_token_or_request(self) -> None:
        calls = {"token": 0, "request": 0}

        def token():
            calls["token"] += 1
            return _attested_m365_token()

        def request(*_args, **_kwargs):
            calls["request"] += 1
            raise AssertionError("network must not run after target drift")

        transport = FixedBffPerformanceTransport(SimpleNamespace(get_token=token))
        original_binding = transport.target_binding_sha256
        capability = _transport_capability(transport)
        transport._opener = SimpleNamespace(open=request)
        transport._endpoint = f"{transport._endpoint}&drift=true"

        sample = transport.request(
            live_action_capability=capability
        )

        self.assertEqual(sample.error_code, "TARGET_BINDING_MISMATCH")
        self.assertTrue(sample.fatal)
        self.assertEqual(calls, {"token": 0, "request": 0})
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_TARGET_BINDING_MISMATCH"):
            _ = transport.target_binding_sha256
        stable = FixedBffPerformanceTransport(SimpleNamespace(get_token=token))
        with patch.object(performance, "_ENDPOINT", "https://example.invalid"):
            self.assertEqual(stable.target_binding_sha256, original_binding)

    def test_fixed_transport_requires_verified_capability_before_token_or_request(
        self,
    ) -> None:
        calls = {"token": 0, "request": 0}

        def token():
            calls["token"] += 1
            return _attested_m365_token()

        def request(*_args, **_kwargs):
            calls["request"] += 1
            raise AssertionError("network must not run")

        transport = FixedBffPerformanceTransport(SimpleNamespace(get_token=token))
        transport._opener = SimpleNamespace(open=request)

        with self.assertRaisesRegex(ValueError, "PERFORMANCE_LIVE_CAPABILITY_REQUIRED"):
            transport.request()

        self.assertEqual(calls, {"token": 0, "request": 0})

    def test_target_get_consumption_failure_precedes_token_state_and_network(
        self,
    ) -> None:
        calls = {"token": 0, "state": 0, "network": 0}

        def token():
            calls["token"] += 1
            return _attested_m365_token()

        transport = FixedBffPerformanceTransport(SimpleNamespace(get_token=token))
        transport._opener = SimpleNamespace(
            open=lambda *_args, **_kwargs: calls.__setitem__("network", 1)
        )

        def authorize(_capability, *, consume, **_kwargs):
            if consume:
                raise ValueError("PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED")

        with patch.object(performance, "_authorize_live_action", side_effect=authorize):
            with self.assertRaisesRegex(
                ValueError,
                "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED",
            ):
                transport.request(
                    live_action_capability=object(),  # type: ignore[arg-type]
                    transport_boundary=lambda: calls.__setitem__("state", 1),
                )

        self.assertEqual(calls, {"token": 0, "state": 0, "network": 0})

    def test_fixed_transport_rejects_wrong_action_target_and_replay(self) -> None:
        token_calls = 0

        def token():
            nonlocal token_calls
            token_calls += 1
            return _attested_m365_token()

        def http_error(request, **_kwargs):
            raise performance.urllib.error.HTTPError(
                request.full_url, 500, "failure", {}, None
            )

        transport = FixedBffPerformanceTransport(SimpleNamespace(get_token=token))
        transport._opener = SimpleNamespace(open=http_error)
        wrong_action = _test_live_action_capability(
            target_binding_sha256=transport.target_binding_sha256,
            action_bindings={
                BLOB_LEASE_ACQUIRE: (transport.target_binding_sha256, 1),
            },
        )
        wrong_target = _test_live_action_capability(
            target_binding_sha256="0" * 64,
            action_bindings={TARGET_GET: (transport.target_binding_sha256, 1)},
        )

        for capability in (wrong_action, wrong_target):
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH"
            ):
                transport.request(live_action_capability=capability)
        self.assertEqual(token_calls, 0)

        one_use = _transport_capability(transport, uses=1)
        self.assertEqual(
            transport.request(live_action_capability=one_use).status_code, 500
        )
        with self.assertRaisesRegex(
            ValueError, "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
        ):
            transport.request(live_action_capability=one_use)
        self.assertEqual(token_calls, 1)

    def test_runner_reverifies_target_before_every_dispatch(self) -> None:
        class _DriftingVerifier(_TransportVerifier):
            def __init__(self) -> None:
                self.calls = 0

            def verify(self, transport, expected_sha256):
                self.calls += 1
                if self.calls == 2:
                    raise ValueError("PERFORMANCE_TARGET_BINDING_MISMATCH")
                super().verify(transport, expected_sha256)

        phase = replace(_phase("load", 2), duration_seconds=30.0)
        phases = (phase,)
        transport = _Transport(
            [PerformanceSample(200, 10, True), PerformanceSample(200, 10, True)]
        )
        verifier = _DriftingVerifier()
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=verifier,
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            evidence = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(
            evidence["abort_reason_code"], "PERFORMANCE_TARGET_BINDING_MISMATCH"
        )
        self.assertEqual(transport.calls, 0)
        self.assertEqual(verifier.calls, 2)
        self.assertEqual(evidence["global_dispatch_count"], 1)
        self.assertEqual(evidence["completed_network_dispatch_count"], 0)
        self.assertEqual(
            evidence["phases"][0]["reserved_attempt_count"],
            evidence["phases"][0]["completed_attempt_count"],
        )
        performance._validate_redacted_evidence(evidence)

    def test_corrupt_passed_resume_state_is_rejected_before_network(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        store = _CheckpointStore()
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            state = runner._restore_or_create_state(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                owner_approval_body_sha256="9" * 64,
                approved_measurement_preflight_sha256=capacity_sha256,
                monitor_window_anchor_sha256=MONITOR_WINDOW_ANCHOR_SHA256,
                resume_state=None,
            )
            state["status"] = "PASSED"
            state["finished_at_utc"] = "2026-08-02T00:00:00Z"
            store.state = state
            with self.assertRaisesRegex(ValueError, "PERFORMANCE_STATE_INVALID"):
                runner.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )
        self.assertEqual(transport.calls, 0)

    def test_persisted_passed_state_must_still_meet_phase_thresholds(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        store = _CheckpointStore()
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
            store.state["phase_results"][0]["latency_ms"]["p95"] = 9999
            with self.assertRaisesRegex(ValueError, "PERFORMANCE_STATE_INVALID"):
                runner.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )
        self.assertEqual(transport.calls, 1)

    def test_idle_resume_repeats_full_idle_observation(self) -> None:
        phase = PhaseSpec(
            "cold_epoch_candidate",
            "paced",
            1,
            1,
            0.01,
            1,
            20.0,
            10.0,
            0.0,
            100,
            100,
            100,
        )
        phases = (phase,)
        store = _CheckpointStore()
        clock = _Clock()
        runner = PerformanceAcceptanceRunner(
            transport=_Transport([PerformanceSample(200, 10, True)]),
            checkpoint_store=store,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=clock,
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            state = runner._restore_or_create_state(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                owner_approval_body_sha256="9" * 64,
                approved_measurement_preflight_sha256=capacity_sha256,
                monitor_window_anchor_sha256=MONITOR_WINDOW_ANCHOR_SHA256,
                resume_state=None,
            )
            state["measurement_preflight"] = _capacity().validate(now=clock.now())
            state["current_phase"] = runner._new_phase_state(phase)
            state["current_phase"]["idle_elapsed_seconds"] = 5.0
            store.state = state
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "PASSED")
        self.assertGreaterEqual(clock.value, 10.0)

    def test_runtime_monitor_failure_blocks_before_transport(self) -> None:
        class _BadMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                result = super().observe(
                    dispatch_attempt_count, measurement_attestation_sha256
                )
                return RuntimeSafetyObservation(
                    observed_execution_units_gb_seconds=(
                        result.observed_execution_units_gb_seconds
                    ),
                    always_ready_units=1,
                    telemetry_cap_reached=False,
                    monitor_evidence_sha256=result.monitor_evidence_sha256,
                    lease_binding_sha256=result.lease_binding_sha256,
                    measurement_attestation_sha256=(
                        result.measurement_attestation_sha256
                    ),
                    observed_at_utc=result.observed_at_utc,
                )

        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_BadMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"], "PERFORMANCE_RUNTIME_SAFETY_BLOCKED"
        )
        self.assertEqual(transport.calls, 0)

    def test_runtime_monitor_must_hold_the_bound_remote_lease(self) -> None:
        class _ConflatedMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                result = super().observe(
                    dispatch_attempt_count, measurement_attestation_sha256
                )
                return replace(result, lease_binding_sha256="d" * 64)

        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_ConflatedMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"], "PERFORMANCE_RUNTIME_SAFETY_BLOCKED"
        )
        self.assertEqual(transport.calls, 0)

    def test_runtime_execution_unit_cap_blocks_before_transport(self) -> None:
        class _OverCapMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                result = super().observe(
                    dispatch_attempt_count, measurement_attestation_sha256
                )
                return replace(
                    result,
                    observed_execution_units_gb_seconds=120_000.01,
                )

        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_OverCapMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"], "PERFORMANCE_RUNTIME_SAFETY_BLOCKED"
        )
        self.assertEqual(transport.calls, 0)

    def test_runtime_execution_unit_budget_includes_remaining_dispatches(self) -> None:
        class _ExhaustedMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                return replace(
                    super().observe(
                        dispatch_attempt_count, measurement_attestation_sha256
                    ),
                    observed_execution_units_gb_seconds=119_500.0,
                )

        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        checkpoint = _CheckpointStore()
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=checkpoint,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_ExhaustedMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"],
            "PERFORMANCE_EXECUTION_UNIT_BUDGET_EXHAUSTED",
        )
        self.assertEqual(
            result["projected_remaining_execution_units_gb_seconds"],
            30_000.0,
        )
        self.assertEqual(
            checkpoint.state["runtime_safety"][
                "projected_remaining_execution_units_gb_seconds"
            ],
            30_000.0,
        )
        self.assertEqual(transport.calls, 0)

    def test_runtime_safety_persists_exact_projection_for_each_cap_decision(
        self,
    ) -> None:
        projections: list[float] = []

        def capture_projection(state):
            runtime_safety = state.get("runtime_safety")
            if isinstance(runtime_safety, dict):
                projections.append(
                    runtime_safety[
                        "projected_remaining_execution_units_gb_seconds"
                    ]
                )

        phase = replace(_phase("load", 32), duration_seconds=400.0)
        phases = (phase,)
        checkpoint = _CheckpointStore(capture_projection)
        runner = PerformanceAcceptanceRunner(
            transport=_Transport(
                [PerformanceSample(200, 10, True) for _ in range(32)]
            ),
            checkpoint_store=checkpoint,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            evidence = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertIn(29_940.0, projections)
        self.assertEqual(projections[-1], 29_880.0)
        self.assertEqual(
            checkpoint.state["runtime_safety"][
                "projected_remaining_execution_units_gb_seconds"
            ],
            29_880.0,
        )
        self.assertEqual(
            evidence["projected_remaining_execution_units_gb_seconds"],
            29_880.0,
        )
        self.assertNotEqual(
            evidence["projected_remaining_execution_units_gb_seconds"],
            evidence["measurement_preflight"][
                "projected_execution_units_gb_seconds"
            ],
        )

    def test_runtime_safety_rejects_full_run_projection_for_remaining_cap(
        self,
    ) -> None:
        class _IncorrectProjectionMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                return replace(
                    super().observe(
                        dispatch_attempt_count, measurement_attestation_sha256
                    ),
                    projected_remaining_execution_units_gb_seconds=29_940.0,
                )

        phase = _phase("load", 1)
        phases = (phase,)
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_IncorrectProjectionMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            evidence = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(
            evidence["abort_reason_code"],
            "PERFORMANCE_RUNTIME_SAFETY_BLOCKED",
        )
        self.assertEqual(transport.calls, 0)

    def test_pending_safety_check_is_restart_terminal_without_dispatch(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        captured: dict[str, object] = {}

        def crash_after_pending_marker(state):
            nonlocal captured
            current = state.get("current_phase")
            if isinstance(current, dict) and current.get("safety_check_pending"):
                captured = json.loads(json.dumps(state))
                raise RuntimeError("simulated crash after safety marker")

        first_transport = _Transport([PerformanceSample(200, 10, True)])
        first = PerformanceAcceptanceRunner(
            transport=first_transport,
            checkpoint_store=_CheckpointStore(crash_after_pending_marker),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            with self.assertRaisesRegex(
                RuntimeError, "simulated crash after safety marker"
            ):
                first.run(
                    plan_sha256=plan_sha256,
                    contract_sha256=CONTRACT_SHA256,
                    activation_hash=activation_hash,
                    approval_reference=APPROVAL_REFERENCE,
                    correlation_id=CORRELATION_ID,
                    expected_measurement_preflight_sha256=capacity_sha256,
                )
        self.assertEqual(first_transport.calls, 0)

        resumed_store = _CheckpointStore()
        resumed_store.state = captured
        resumed_transport = _Transport([PerformanceSample(200, 10, True)])
        class _UnavailableAuthorization:
            def verify(self, **_values):
                raise AssertionError("authorization must not run during terminalization")

        class _UnavailableCapacity:
            def get_attestation(self):
                raise AssertionError("capacity must not run during terminalization")

        resumed = PerformanceAcceptanceRunner(
            transport=resumed_transport,
            checkpoint_store=resumed_store,
            authorization_verifier=_UnavailableAuthorization(),
            measurement_provider=_UnavailableCapacity(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            result = resumed.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"],
            "PREDISPATCH_SAFETY_OUTCOME_UNKNOWN",
        )
        self.assertEqual(resumed_transport.calls, 0)

    def test_fixed_transport_enforces_connect_and_total_request_deadlines(self) -> None:
        transport = FixedBffPerformanceTransport(
            SimpleNamespace(get_token=_attested_m365_token)
        )
        observed: dict[str, float] = {}

        def deadline(_request, *, timeout):
            observed["connect_timeout"] = timeout
            raise performance._RequestDeadlineExceeded()

        transport._opener = SimpleNamespace(open=deadline)
        with (
            patch.object(performance.signal, "getitimer", return_value=(0.0, 0.0)),
            patch.object(performance.signal, "getsignal", return_value=object()),
            patch.object(performance.signal, "signal"),
            patch.object(performance.signal, "setitimer") as setitimer,
        ):
            sample = transport.request(
                live_action_capability=_transport_capability(transport)
            )
        self.assertEqual(observed["connect_timeout"], 10.0)
        self.assertEqual(sample.error_code, "REQUEST_DEADLINE_EXCEEDED")
        self.assertTrue(sample.fatal)
        self.assertEqual(setitimer.call_args_list[0].args[1], 30.0)
        self.assertEqual(setitimer.call_args_list[-1].args[1], 0.0)
        with self.assertRaisesRegex(TypeError, "timeout_seconds"):
            FixedBffPerformanceTransport(
                SimpleNamespace(get_token=_attested_m365_token),
                timeout_seconds=1.0,
            )

    def test_fixed_transport_real_alarm_and_redirect_rejection(self) -> None:
        transport = FixedBffPerformanceTransport(
            SimpleNamespace(get_token=_attested_m365_token)
        )

        def block_past_deadline(_request, *, timeout):
            self.assertEqual(timeout, 10.0)
            performance.time.sleep(1.0)

        transport._opener = SimpleNamespace(open=block_past_deadline)
        with patch.object(performance, "_REQUEST_TIMEOUT_SECONDS", 0.01):
            sample = transport.request(
                live_action_capability=_transport_capability(transport)
            )
        self.assertEqual(sample.error_code, "REQUEST_DEADLINE_EXCEEDED")
        self.assertTrue(sample.fatal)

        self.assertIsNone(
            performance._NoRedirect().redirect_request(
                None, None, 302, "Found", {}, "https://example.invalid"
            )
        )

        def redirect(request, *, timeout):
            raise performance.urllib.error.HTTPError(
                request.full_url,
                302,
                "Found",
                {"Location": "https://example.invalid"},
                None,
            )

        transport._opener = SimpleNamespace(open=redirect)
        redirected = transport.request(
            live_action_capability=_transport_capability(transport)
        )
        self.assertTrue(redirected.fatal)
        self.assertEqual(
            redirected.error_code, "AUTHORIZATION_OR_TARGET_FAILURE"
        )

    def test_fixed_transport_rechecks_endpoint_after_token_acquisition(self) -> None:
        transport = FixedBffPerformanceTransport(SimpleNamespace())
        opened: list[str] = []

        def mutate_endpoint():
            transport._endpoint = "https://example.invalid/token-sink"
            return _attested_m365_token()

        transport._token_provider = SimpleNamespace(get_token=mutate_endpoint)
        transport._opener = SimpleNamespace(
            open=lambda request, **_kwargs: opened.append(request.full_url)
        )

        sample = transport.request(
            live_action_capability=_transport_capability(transport)
        )

        self.assertEqual(sample.error_code, "TARGET_BINDING_MISMATCH")
        self.assertTrue(sample.fatal)
        self.assertEqual(opened, [])

    def test_stable_authorization_failure_code_is_valid_redacted_evidence(self) -> None:
        self.assertFalse(
            performance._contains_sensitive_string(
                "AUTHORIZATION_OR_TARGET_FAILURE"
            )
        )
        self.assertTrue(
            performance._contains_sensitive_string(
                "Authorization: Basic synthetic-secret"
            )
        )

    def test_post_dispatch_monitor_failure_is_terminalized(self) -> None:
        class _PostDispatchFailureMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                result = super().observe(
                    dispatch_attempt_count, measurement_attestation_sha256
                )
                if len(self.attempts) == 1:
                    return result
                return replace(result, telemetry_cap_reached=True)

        phase = _phase("load", 1)
        phases = (phase,)
        checkpoint = _CheckpointStore()
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=checkpoint,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_PostDispatchFailureMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            result = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertEqual(transport.calls, 1)
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["abort_reason_code"], "PERFORMANCE_RUNTIME_SAFETY_BLOCKED"
        )
        self.assertEqual(checkpoint.state["status"], "FAILED")

    def test_passed_readback_checkpoints_refreshed_measurement_before_evidence(self) -> None:
        class _NoonClock(_Clock):
            def now(self):
                return datetime(2026, 8, 2, 12, 0, tzinfo=UTC)

        class _RotatingCapacityProvider:
            def __init__(self):
                self.calls = 0

            def get_attestation(self):
                observed = datetime(2026, 8, 2, tzinfo=UTC) + timedelta(
                    seconds=self.calls
                )
                self.calls += 1
                return replace(
                    _capacity(),
                    observed_at_utc=observed.isoformat().replace("+00:00", "Z"),
                )

        class _NoonMonitor(_Monitor):
            def observe(self, dispatch_attempt_count, measurement_attestation_sha256):
                return replace(
                    super().observe(
                        dispatch_attempt_count, measurement_attestation_sha256
                    ),
                    observed_at_utc="2026-08-02T12:00:00Z",
                )

        phase = _phase("load", 1)
        phases = (phase,)
        checkpoint = _CheckpointStore()
        provider = _RotatingCapacityProvider()
        transport = _Transport([PerformanceSample(200, 10, True)])
        runner = PerformanceAcceptanceRunner(
            transport=transport,
            checkpoint_store=checkpoint,
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=provider,
            transport_verifier=_TransportVerifier(),
            clock=_NoonClock(),
            phases=phases,
            safety_monitor=_NoonMonitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            first = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
            self.assertEqual(first["status"], "PASSED", first)
            second = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertTrue(second["idempotent_readback"])
        self.assertEqual(second["final_checkpoint_sha256"], checkpoint.state_sha256())
        self.assertEqual(transport.calls, 1)

    def test_nested_secret_shaped_error_is_redacted_before_evidence(self) -> None:
        phase = _phase("load", 1)
        phases = (phase,)
        secret = _jwt(audience="synthetic-redaction-test")
        runner = PerformanceAcceptanceRunner(
            transport=_Transport(
                [PerformanceSample(500, 10, False, secret, True)]
            ),
            checkpoint_store=_CheckpointStore(),
            authorization_verifier=_AuthorizationVerifier(),
            measurement_provider=_MeasurementProvider(),
            transport_verifier=_TransportVerifier(),
            clock=_Clock(),
            phases=phases,
            safety_monitor=_Monitor(),
        )
        with patch("nac_bff.azure_performance_acceptance.PHASES", phases):
            activation_hash, plan_sha256, capacity_sha256 = _bindings()
            evidence = runner.run(
                plan_sha256=plan_sha256,
                contract_sha256=CONTRACT_SHA256,
                activation_hash=activation_hash,
                approval_reference=APPROVAL_REFERENCE,
                correlation_id=CORRELATION_ID,
                expected_measurement_preflight_sha256=capacity_sha256,
            )
        self.assertNotIn(secret, json.dumps(evidence))
        self.assertEqual(
            evidence["abort_reason_code"], "UNSAFE_ERROR_CODE_REDACTED"
        )

    def test_m365_allowlist_accepts_only_exact_token_command(self) -> None:
        command = (
            "m365",
            "util",
            "accesstoken",
            "get",
            "--resource",
            "api://funktion8.de/nac-bff",
            "--new",
            "--output",
            "json",
        )
        _validate_m365_command(command)
        with self.assertRaises(M365CliReadinessError):
            _validate_m365_command((*command, "--verbose"))

    def test_delegated_token_must_target_exact_bff_audience(self) -> None:
        class _Runner:
            def __init__(self, token: str) -> None:
                self.token = token

            def run(self, _command):
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps({"accessToken": self.token}),
                )

        invalid = M365DelegatedTokenProvider(
            _Runner(_jwt(audience="api://wrong")), clock=lambda: 0.0
        )
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_TOKEN_BINDING_INVALID"):
            invalid.get_token()

        class _Attestor:
            def attest(self, token, *, resource, required_scopes):
                self.assertions = (resource, required_scopes)
                return performance._issue_attested_m365_access_token(
                    token,
                    resource=resource,
                    scopes=required_scopes,
                )

        valid = M365DelegatedTokenProvider(
            _Runner(_DUMMY_M365_TOKEN),
            clock=lambda: 0.0,
            token_attestor=_Attestor(),
        )
        result = valid.get_token()
        self.assertIsInstance(result, performance.AttestedM365AccessToken)
        self.assertEqual(result.token, _DUMMY_M365_TOKEN)
        with self.assertRaises(AttributeError):
            result.token = _jwt(audience="api://wrong")

    def test_fixed_transport_rejects_unattested_token_result_after_consumption(
        self,
    ) -> None:
        transport = FixedBffPerformanceTransport(
            SimpleNamespace(get_token=lambda: _DUMMY_M365_TOKEN)
        )
        opened: list[object] = []
        transport._opener = SimpleNamespace(
            open=lambda *args, **kwargs: opened.append((args, kwargs))
        )

        sample = transport.request(
            live_action_capability=_transport_capability(transport)
        )

        self.assertEqual(sample.error_code, "TOKEN_ACQUISITION_FAILED")
        self.assertTrue(sample.fatal)
        self.assertEqual(opened, [])

    def test_cli_emits_offline_plan_without_network(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = cli_main(
                [
                    "m365",
                    "teams-sharepoint",
                    "bff-performance-acceptance-plan",
                    "--expected-activation-hash",
                    SHA256,
                    "--format",
                    "json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(status, 0)
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["budgets"]["total_request_limit"], 500)

    def test_cli_rejects_invalid_binding_before_network(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            status = cli_main(
                [
                    "m365",
                    "teams-sharepoint",
                    "bff-performance-acceptance-plan",
                    "--expected-activation-hash",
                    "invalid",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(status, 2)
        self.assertEqual(
            json.loads(output.getvalue())["error"]["code"],
            "PERFORMANCE_PLAN_BINDING_INVALID",
        )


if __name__ == "__main__":
    unittest.main()
