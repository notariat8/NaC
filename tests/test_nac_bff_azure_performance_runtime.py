from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

from nac_bff import azure_performance_acceptance as performance
from nac_bff import azure_performance_runtime as performance_runtime
from nac_bff.azure_performance_acceptance import MeasurementAttestation
from nac_bff.azure_performance_acceptance import BoundPerformanceAuthorizationVerifier
from nac_bff.azure_performance_authorization import (
    VerifiedLiveActionCapability,
    VerifiedPerformanceAuthority,
)
from nac_bff.azure_performance_lease import (
    AzureBlobLeaseAdapter,
    AzureBlobLeaseReceipt,
)
from nac_bff.azure_performance_monitor import (
    AzurePerformanceMonitorAdapter,
    AzurePerformanceObservation,
)
from nac_bff.azure_performance_runtime import (
    AzurePerformanceRuntimeAdapter,
    LeaseBoundPerformanceAcceptance,
    PerformanceFinalEvidenceStore,
)


LEASE_ID = UUID("12345678-1234-4abc-8def-1234567890ab")
START = datetime(2026, 8, 3, 11, 0, tzinfo=UTC)
END = datetime(2026, 8, 3, 11, 15, tzinfo=UTC)
NOW = datetime(2026, 8, 3, 12, 5, tzinfo=UTC)
SETTLED_END = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
ANCHOR_SHA256 = __import__("hashlib").sha256(
    b"2026-08-03T11:00:00Z"
).hexdigest()
CONTRACT_SHA256 = "a" * 64
ACTIVATION_HASH = "b" * 64
APPROVED_PLAN = performance.build_performance_acceptance_plan(
    ACTIVATION_HASH, CONTRACT_SHA256
)
TARGET_BINDING_SHA256 = APPROVED_PLAN["target_binding_sha256"]
INFRASTRUCTURE_PARAMETERS_SHA256 = "5" * 64
INFRASTRUCTURE_SOURCE_SHA256 = "6" * 64
LEASE_BOOTSTRAP_POLICY_SHA256 = "7" * 64
INFRASTRUCTURE_SAFETY_POLICY_SHA256 = "9" * 64
INFRASTRUCTURE_BINDING_SHA256 = performance._sha256_json(
    {
        "infrastructure_parameters_sha256": INFRASTRUCTURE_PARAMETERS_SHA256,
        "infrastructure_source_sha256": INFRASTRUCTURE_SOURCE_SHA256,
        "lease_bootstrap_policy_sha256": LEASE_BOOTSTRAP_POLICY_SHA256,
        "infrastructure_safety_policy_sha256": (
            INFRASTRUCTURE_SAFETY_POLICY_SHA256
        ),
    }
)
EXECUTION_BINDINGS = {
    "approved_commit_sha": "1" * 40,
    "approved_tree_sha": "2" * 40,
    "toolchain_attestations_sha256": "3" * 64,
    "contract_sha256": CONTRACT_SHA256,
    "expected_activation_hash": ACTIVATION_HASH,
    "phase_plan_sha256": APPROVED_PLAN["phase_plan_sha256"],
    "measurement_policy_sha256": APPROVED_PLAN["measurement_policy_sha256"],
    "monitor_policy_sha256": APPROVED_PLAN["monitor_policy_sha256"],
    "lease_policy_sha256": APPROVED_PLAN["lease_policy_sha256"],
    "infrastructure_binding_sha256": INFRASTRUCTURE_BINDING_SHA256,
    "infrastructure_parameters_sha256": INFRASTRUCTURE_PARAMETERS_SHA256,
    "infrastructure_source_sha256": INFRASTRUCTURE_SOURCE_SHA256,
    "lease_bootstrap_policy_sha256": LEASE_BOOTSTRAP_POLICY_SHA256,
    "infrastructure_safety_policy_sha256": (
        INFRASTRUCTURE_SAFETY_POLICY_SHA256
    ),
    "worm_baseline_binding_sha256": "4" * 64,
    "worm_baseline_compiled_arm_sha256": "5" * 64,
    "worm_baseline_parameters_sha256": "6" * 64,
    "worm_baseline_source_sha256": "7" * 64,
    "deployment_sequence_sha256": "9" * 64,
    "infrastructure_safety_evidence_sha256": "a" * 64,
    "lease_acquisition_safety_evidence_sha256": "b" * 64,
    "lease_binding_sha256": "e" * 64,
    "owner_approval_body_sha256": "8" * 64,
    "monitor_window_anchor_sha256": ANCHOR_SHA256,
    "target_binding_sha256": TARGET_BINDING_SHA256,
}


def _verified_execution_bindings() -> dict[str, str]:
    return _owner_preflight_for(EXECUTION_BINDINGS)


def _owner_preflight_for(bindings: dict[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in bindings.items()
        if key
        not in {
            "lease_acquisition_safety_evidence_sha256",
            "lease_binding_sha256",
        }
    }


def _test_authorization_verifier(source=_verified_execution_bindings):
    def issue(**values):
        owner = source() if callable(source) else source
        bindings = {
            **owner,
            "lease_binding_sha256": values["lease_binding_sha256"],
            "lease_acquisition_safety_evidence_sha256": values[
                "lease_acquisition_safety_evidence_sha256"
            ],
        }
        capability = object.__new__(VerifiedLiveActionCapability)
        capability._nonce = "runtime-test-capability"
        authority = object.__new__(VerifiedPerformanceAuthority)
        authority._bindings = bindings
        authority._capability = capability
        return authority

    verifier = object.__new__(BoundPerformanceAuthorizationVerifier)
    verifier.verify_owner_and_infrastructure_before_lease = issue
    return verifier


def _test_capability():
    authority = _test_authorization_verifier()
    return authority.verify_owner_and_infrastructure_before_lease(
        approval_reference="test",
        contract_sha256=CONTRACT_SHA256,
        activation_hash=ACTIVATION_HASH,
        correlation_id="test",
        lease_binding_sha256=EXECUTION_BINDINGS["lease_binding_sha256"],
        lease_acquisition_safety_evidence_sha256=EXECUTION_BINDINGS[
            "lease_acquisition_safety_evidence_sha256"
        ],
    ).capability


def _receipt(
    lifecycle_state: str = "HELD",
    *,
    target_binding_sha256: str = TARGET_BINDING_SHA256,
    lease_binding_sha256: str = "e" * 64,
) -> AzureBlobLeaseReceipt:
    return AzureBlobLeaseReceipt(
        lease_binding_sha256=lease_binding_sha256,
        target_binding_sha256=target_binding_sha256,
        lease_id_sha256="2" * 64,
        read_identity_binding_sha256="3" * 64,
        write_identity_binding_sha256="4" * 64,
        lifecycle_state=lifecycle_state,
        lifecycle_state_sha256="5" * 64,
    )


def _observation(
    on_demand_execution_count: int = 500,
) -> AzurePerformanceObservation:
    names = (
        "OnDemandFunctionExecutionUnits",
        "OnDemandFunctionExecutionCount",
        "AlwaysReadyFunctionExecutionUnits",
        "AlwaysReadyUnits",
        "AlwaysReadyFunctionExecutionCount",
    )
    return AzurePerformanceObservation(
        requested_timespan="2026-08-03T11:00:00Z/2026-08-03T11:15:00Z",
        returned_timespan="2026-08-03T11:00:00Z/2026-08-03T11:15:00Z",
        on_demand_execution_units=Decimal("1024000"),
        on_demand_execution_count=Decimal(on_demand_execution_count),
        always_ready_execution_units=Decimal("0"),
        always_ready_units=Decimal("0"),
        always_ready_execution_count=Decimal("0"),
        observed_execution_units_gb_seconds=Decimal("1"),
        series_counts={name: 1 for name in names},
        data_point_counts={name: 1 for name in names},
        monitor_binding_sha256="d" * 64,
        monitor_evidence_sha256="f" * 64,
    )


def _measurement_attestation_summary() -> dict:
    return MeasurementAttestation(
        measurement_mode=performance.MEASUREMENT_MODE,
        tenant_wide_sharepoint_capacity_claim="NOT_CLAIMED",
        maximum_dispatches_per_minute=6,
        planned_dispatch_count=500,
        always_ready_units=0,
        projected_execution_units_gb_seconds=30_000.0,
        observed_execution_units_gb_seconds=1.0,
        telemetry_cap_reached=False,
        measurement_policy_sha256=performance.measurement_policy_sha256(),
        monitor_binding_sha256="d" * 64,
        monitor_evidence_sha256="f" * 64,
        monitor_window_anchor_sha256=ANCHOR_SHA256,
        lease_binding_sha256="e" * 64,
        observed_at_utc="2026-08-03T12:05:00Z",
        tenant_binding_sha256=__import__("hashlib").sha256(
            b"870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
        ).hexdigest(),
        workspace_binding_sha256=__import__("hashlib").sha256(
            b"notary_team_01"
        ).hexdigest(),
    ).validate(now=NOW)


def _final_attestation_summary() -> dict:
    summary = _measurement_attestation_summary()
    measurement_attestation_sha256 = summary.pop("attestation_sha256")
    summary["projected_execution_units_gb_seconds"] = 0.0
    result = {
        **summary,
        "minimum_on_demand_execution_count": 500,
        "on_demand_execution_count": 500,
        "measurement_attestation_sha256": measurement_attestation_sha256,
        "target_binding_sha256": TARGET_BINDING_SHA256,
        "measurement_finished_at_utc": "2026-08-03T12:00:00Z",
        "monitor_window_start_utc": "2026-08-03T11:00:00Z",
        "monitor_window_end_utc": "2026-08-03T12:00:00Z",
        "monitor_observed_at_utc": "2026-08-03T12:05:00Z",
        "monitor_settlement_delay_seconds": 300,
    }
    result["attestation_sha256"] = performance._sha256_json(result)
    return result


def _measurement_evidence() -> dict:
    capacity = _measurement_attestation_summary()
    phases = []
    for index, spec in enumerate(performance.PHASES):
        phases.append(
            {
                "phase_id": spec.phase_id,
                "mode": spec.mode,
                "request_limit": spec.request_limit,
                "idle_elapsed_seconds": spec.idle_before_seconds,
                "active_elapsed_seconds": 0.0,
                "checkpoint_count": spec.request_limit * 2,
                "reserved_attempt_count": spec.request_limit,
                "completed_attempt_count": spec.request_limit,
                "instance_epoch_sha256": str(index + 1) * 64,
                "request_count": spec.request_limit,
                "error_count": 0,
                "error_rate": 0.0,
                "latency_ms": {"p50": 10, "p95": 10, "p99": 10, "max": 10},
                "status_counts": {"200": spec.request_limit},
                "error_codes": {},
                "status": "PASSED",
            }
        )
    total_requests = sum(item["request_count"] for item in phases)
    return {
        "schema_version": performance.EVIDENCE_SCHEMA_VERSION,
        "contract_id": performance.CONTRACT_ID,
        "status": "PASSED",
        "final_acceptance_scope": "MEASUREMENT_ONLY_LEASE_RELEASE_PENDING",
        "plan_sha256": APPROVED_PLAN["plan_sha256"],
        "contract_sha256": CONTRACT_SHA256,
        "activation_hash": ACTIVATION_HASH,
        "owner_approval_body_sha256": "8" * 64,
        "approved_measurement_preflight_sha256": capacity["attestation_sha256"],
        "started_at_utc": "2026-08-03T11:00:00Z",
        "finished_at_utc": "2026-08-03T12:00:00Z",
        "idempotent_readback": False,
        "summary": {
            "phase_count": len(phases),
            "passed_phase_count": len(phases),
            "total_request_count": total_requests,
            "total_error_count": 0,
            "request_limit": total_requests,
            "journal_event_count": total_requests * 2,
            "journal_head_sha256": "c" * 64,
            "cold_start_classification": "VERIFIED",
            "instance_epoch_changed": True,
        },
        "measurement_preflight": capacity,
        "measurement_preflight_sha256": capacity["attestation_sha256"],
        "target_binding_sha256": TARGET_BINDING_SHA256,
        "phase_plan_sha256": APPROVED_PLAN["phase_plan_sha256"],
        "global_dispatch_count": total_requests,
        "completed_network_dispatch_count": total_requests,
        "global_dispatch_ceiling": 500,
        "endpoint_request_budget_fraction_used": 1.0,
        "tenant_resource_unit_capacity_claim": "NOT_CLAIMED",
        "azure_execution_units_gb_seconds": 1.0,
        "projected_remaining_execution_units_gb_seconds": 0.0,
        "always_ready_units": 0,
        "phase_aggregate_metrics": phases,
        "cold_start_classification": "VERIFIED",
        "server_instance_or_start_epoch_changed": True,
        "abort_reason_code": None,
        "phases": phases,
        "boundaries": {
            "workspace_id_sha256": "3" * 64,
            "matter_id_sha256": "4" * 64,
            "endpoint_sha256": "5" * 64,
            "raw_token_count": 0,
            "raw_response_body_count": 0,
            "tenant_write_count": 0,
            "infrastructure_restart_count": 0,
            "credential_change_count": 0,
            "permission_change_count": 0,
            "automatic_rollback_count": 0,
            "automatic_deletion_count": 0,
        },
        "redaction": {
            "aggregated_metrics_only": True,
            "contains_tokens": False,
            "contains_response_bodies": False,
            "contains_urls": False,
            "contains_tenant_or_user_ids": False,
            "contains_correlation_ids": False,
        },
        "final_checkpoint_sha256": "6" * 64,
    }


def _failed_measurement_evidence() -> dict:
    evidence = _measurement_evidence()
    phase = dict(evidence["phases"][0])
    phase.update(
        {
            "checkpoint_count": 2,
            "reserved_attempt_count": 1,
            "completed_attempt_count": 1,
            "request_count": 1,
            "error_count": 1,
            "error_rate": 1.0,
            "status_counts": {"401": 1},
            "error_codes": {"AUTHORIZATION_OR_TARGET_FAILURE": 1},
            "failure_code": "AUTHORIZATION_OR_TARGET_FAILURE",
            "status": "FAILED",
        }
    )
    evidence.update(
        {
            "status": "FAILED",
            "summary": {
                **evidence["summary"],
                "phase_count": 1,
                "passed_phase_count": 0,
                "total_request_count": 1,
                "total_error_count": 1,
                "request_limit": 500,
                "journal_event_count": 2,
            },
            "global_dispatch_count": 1,
            "completed_network_dispatch_count": 1,
            "phase_aggregate_metrics": [phase],
            "abort_reason_code": "AUTHORIZATION_OR_TARGET_FAILURE",
            "phases": [phase],
        }
    )
    return evidence


def _predispatch_failed_measurement_evidence() -> dict:
    evidence = _failed_measurement_evidence()
    phase = evidence["phases"][0]
    phase["status_counts"] = {"transport": 1}
    phase["error_codes"] = {"TOKEN_ACQUISITION_FAILED": 1}
    phase["failure_code"] = "TOKEN_ACQUISITION_FAILED"
    evidence["phase_aggregate_metrics"] = [phase]
    evidence["completed_network_dispatch_count"] = 0
    evidence["abort_reason_code"] = "TOKEN_ACQUISITION_FAILED"
    return evidence


def _measurement_evidence_for_lease(lease_binding_sha256: str) -> dict:
    evidence = _measurement_evidence()
    preflight = evidence["measurement_preflight"]
    preflight["lease_binding_sha256"] = lease_binding_sha256
    preflight.pop("attestation_sha256")
    preflight["attestation_sha256"] = performance._sha256_json(preflight)
    evidence["approved_measurement_preflight_sha256"] = preflight[
        "attestation_sha256"
    ]
    evidence["measurement_preflight_sha256"] = preflight["attestation_sha256"]
    return evidence


def _public_verifier_execution_bindings() -> tuple[dict, dict, dict[str, str]]:
    from nac_bff.azure_performance_infrastructure_safety import (
        validate_infrastructure_safety_evidence,
    )
    from nac_bff import azure_performance_infrastructure_safety as safety_module
    from nac_bff.azure_performance_lease import (
        AzureBlobLeaseBinding,
        build_lease_acquisition_safety_evidence,
    )
    from tests import test_nac_bff_azure_performance_infrastructure_safety as fixture

    fixture.TARGET_BINDING = TARGET_BINDING_SHA256
    with tempfile.TemporaryDirectory() as ledger_directory, patch.object(
        safety_module,
        "_READBACK_REPLAY_LEDGER_DIRECTORY",
        Path(ledger_directory) / "ledger",
    ), patch.object(
        safety_module,
        "_trusted_now",
        return_value=fixture.VERIFY_AT,
    ):
        infrastructure = validate_infrastructure_safety_evidence(
            fixture._issue_evidence()
        )
    binding = AzureBlobLeaseBinding(
        account_name=infrastructure["coordination_storage_account_name"],
        bff_account_name=infrastructure["bff_storage_account_resource_id"].rsplit(
            "/", 1
        )[-1],
        worm_account_name=infrastructure[
            "worm_storage_account_resource_id"
        ].rsplit("/", 1)[-1],
        coordination_storage_account_resource_id=infrastructure[
            "coordination_storage_account_resource_id"
        ],
        owner_approval_body_sha256=EXECUTION_BINDINGS[
            "owner_approval_body_sha256"
        ],
        token_subject=infrastructure["provisioner_principal_id"],
        token_tenant_id=infrastructure["tenant_id"],
        target_binding_sha256=TARGET_BINDING_SHA256,
        expected_etag='"nac-restart-test-etag"',
        read_identity_binding_sha256="3" * 64,
        write_identity_binding_sha256="4" * 64,
    )
    with patch.object(
        safety_module, "_trusted_now", return_value=fixture.VERIFY_AT
    ):
        acquisition = build_lease_acquisition_safety_evidence(
            binding=binding,
            infrastructure_safety_evidence=infrastructure,
        )
    bindings = {
        **EXECUTION_BINDINGS,
        "toolchain_attestations_sha256": infrastructure[
            "toolchain_attestations_sha256"
        ],
        "infrastructure_safety_policy_sha256": infrastructure[
            "infrastructure_safety_policy_sha256"
        ],
        "infrastructure_safety_evidence_sha256": infrastructure[
            "infrastructure_safety_evidence_sha256"
        ],
        "lease_acquisition_safety_evidence_sha256": acquisition[
            "lease_acquisition_safety_evidence_sha256"
        ],
        "lease_binding_sha256": acquisition["lease_binding_sha256"],
    }
    bindings["infrastructure_binding_sha256"] = performance._sha256_json(
        {
            "infrastructure_parameters_sha256": bindings[
                "infrastructure_parameters_sha256"
            ],
            "infrastructure_source_sha256": bindings[
                "infrastructure_source_sha256"
            ],
            "lease_bootstrap_policy_sha256": bindings[
                "lease_bootstrap_policy_sha256"
            ],
            "infrastructure_safety_policy_sha256": bindings[
                "infrastructure_safety_policy_sha256"
            ],
        }
    )
    return infrastructure, acquisition, bindings


def _run_public_verifier_restart_stage(stage: str, evidence_path: str) -> dict:
    infrastructure, acquisition, bindings = _public_verifier_execution_bindings()
    lease = _Lease(
        infrastructure_safety_evidence_sha256=bindings[
            "infrastructure_safety_evidence_sha256"
        ],
        lease_acquisition_safety_evidence_sha256=bindings[
            "lease_acquisition_safety_evidence_sha256"
        ],
        lease_binding_sha256=bindings["lease_binding_sha256"],
    )
    clock = (
        (lambda: datetime(2026, 8, 3, 12, 4, 59, tzinfo=UTC))
        if stage == "initial"
        else (lambda: NOW)
    )
    runtime = AzurePerformanceRuntimeAdapter(
        monitor=_Monitor(),
        lease=lease,
        lease_id=LEASE_ID,
        monitor_window_anchor_utc=START,
        clock=clock,
        sleeper=lambda _seconds: None,
    )

    class _PublicEvidenceRunner(_Runner):
        def run(self, **_kwargs):
            self.calls += 1
            if stage != "initial":
                raise AssertionError("measurement runner replayed")
            return _measurement_evidence_for_lease(
                bindings["lease_binding_sha256"]
            )

    orchestrator = LeaseBoundPerformanceAcceptance(
        runtime=runtime,
        runner=_PublicEvidenceRunner(),
        execution_bindings=bindings,
        authorization_verifier=_test_authorization_verifier(
            lambda: _owner_preflight_for(bindings)
        ),
        final_evidence_store=PerformanceFinalEvidenceStore(Path(evidence_path)),
    )
    if stage == "initial":
        try:
            orchestrator.run()
        except ValueError as exc:
            if str(exc) != "PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED":
                raise
        terminal = PerformanceFinalEvidenceStore(
            Path(evidence_path)
        ).load_terminal_measurement()
        if terminal is None:
            raise AssertionError("terminal checkpoint not persisted")
        chain = terminal["preflight_evidence_chain"]
    else:
        final = orchestrator.run()
        chain = final["preflight_evidence_chain"]
    return {
        "infrastructure_safety_evidence_sha256": infrastructure[
            "infrastructure_safety_evidence_sha256"
        ],
        "lease_acquisition_safety_evidence_sha256": acquisition[
            "lease_acquisition_safety_evidence_sha256"
        ],
        "preflight_evidence_chain": chain,
    }


def _final_evidence() -> dict:
    evidence = _measurement_evidence()
    attestation = _final_attestation_summary()
    completion = {
        "lease_binding_sha256": "e" * 64,
        "target_binding_sha256": TARGET_BINDING_SHA256,
        "lease_release_lifecycle_state": "RELEASED",
        "lease_release_lifecycle_state_sha256": performance._sha256_text(
            "RELEASED"
        ),
        "lease_release_state_evidence_sha256": "5" * 64,
        "monitor_binding_sha256": "d" * 64,
        "monitor_evidence_sha256": "f" * 64,
        "monitor_window_anchor_sha256": ANCHOR_SHA256,
        "final_measurement_attestation_sha256": attestation[
            "attestation_sha256"
        ],
        "final_measurement_attestation": attestation,
        "final_measurement_summary_sha256": performance._sha256_json(attestation),
        "final_observed_execution_units_gb_seconds": 1.0,
        "final_projected_execution_units_gb_seconds": 0.0,
        "final_execution_units_below_cap": True,
        "final_telemetry_cap_reached": False,
    }
    final = {
        "schema_version": "nac.m365-bff-performance-final-evidence/v1",
        "status": "PASSED",
        "measurement_evidence": evidence,
        "measurement_evidence_sha256": performance._sha256_json(evidence),
        "execution_bindings": EXECUTION_BINDINGS,
        "preflight_evidence_chain": (
            performance_runtime._initial_preflight_evidence_chain(
                EXECUTION_BINDINGS
            )
        ),
        "completion_bindings": completion,
        "lease_release_verified": True,
        "tenant_wide_sharepoint_baseline_claim": "NOT_CLAIMED",
        "tenant_wide_sharepoint_request_allowance_claim": "NOT_CLAIMED",
        "tenant_wide_sharepoint_resource_unit_allowance_claim": "NOT_CLAIMED",
        "monetary_cost_claim": "NOT_CLAIMED",
    }
    final["final_evidence_sha256"] = performance._sha256_json(final)
    return final


def _final_evidence_with_owner_binding(owner_binding_sha256: str) -> dict:
    final = _final_evidence()
    execution_bindings = {
        **final["execution_bindings"],
        "owner_approval_body_sha256": owner_binding_sha256,
    }
    measurement_evidence = {
        **final["measurement_evidence"],
        "owner_approval_body_sha256": owner_binding_sha256,
    }
    final["measurement_evidence"] = measurement_evidence
    final["measurement_evidence_sha256"] = performance._sha256_json(
        measurement_evidence
    )
    final["execution_bindings"] = execution_bindings
    final["preflight_evidence_chain"] = (
        performance_runtime._initial_preflight_evidence_chain(
            execution_bindings
        )
    )
    final.pop("final_evidence_sha256")
    final["final_evidence_sha256"] = performance._sha256_json(final)
    return final


def _failed_final_evidence() -> dict:
    final = _final_evidence()
    nested = _failed_measurement_evidence()
    attestation = dict(final["completion_bindings"]["final_measurement_attestation"])
    attestation["status"] = "FAILED"
    attestation["minimum_on_demand_execution_count"] = 1
    attestation.pop("attestation_sha256")
    attestation["attestation_sha256"] = performance._sha256_json(attestation)
    completion = final["completion_bindings"]
    completion["final_measurement_attestation"] = attestation
    completion["final_measurement_attestation_sha256"] = attestation[
        "attestation_sha256"
    ]
    completion["final_measurement_summary_sha256"] = performance._sha256_json(
        attestation
    )
    final["status"] = "FAILED"
    final["measurement_evidence"] = nested
    final["measurement_evidence_sha256"] = performance._sha256_json(nested)
    final.pop("final_evidence_sha256")
    final["final_evidence_sha256"] = performance._sha256_json(final)
    return final


class _Lease(AzureBlobLeaseAdapter):
    def __init__(
        self,
        *,
        target_binding_sha256: str = TARGET_BINDING_SHA256,
        infrastructure_safety_evidence_sha256: str = "a" * 64,
        lease_acquisition_safety_evidence_sha256: str = "b" * 64,
        lease_binding_sha256: str = "e" * 64,
    ) -> None:
        self.calls: list[str] = []
        self.capabilities: list[object] = []
        self._target_binding_sha256 = target_binding_sha256
        self._infrastructure_safety_evidence_sha256 = (
            infrastructure_safety_evidence_sha256
        )
        self._lease_acquisition_safety_evidence_sha256 = (
            lease_acquisition_safety_evidence_sha256
        )
        self._lease_binding_sha256 = lease_binding_sha256

    @property
    def target_binding_sha256(self):
        return self._target_binding_sha256

    @property
    def lease_binding_sha256(self):
        return self._lease_binding_sha256

    @property
    def infrastructure_safety_evidence_sha256(self):
        return self._infrastructure_safety_evidence_sha256

    @property
    def lease_acquisition_safety_evidence_sha256(self):
        return self._lease_acquisition_safety_evidence_sha256

    @contextmanager
    def execution_fence(self, live_action_capability=None):
        if live_action_capability is not None:
            self.capabilities.append(live_action_capability)
        yield

    def acquire(self, lease_id, live_action_capability=None):
        self.capabilities.append(live_action_capability)
        self.calls.append(f"acquire:{lease_id}")
        return _receipt(
            target_binding_sha256=self._target_binding_sha256,
            lease_binding_sha256=self._lease_binding_sha256,
        )

    def assert_held(self, lease_id, live_action_capability=None):
        self.capabilities.append(live_action_capability)
        self.calls.append(f"assert:{lease_id}")
        return _receipt(
            target_binding_sha256=self._target_binding_sha256,
            lease_binding_sha256=self._lease_binding_sha256,
        )

    def release(self, lease_id, live_action_capability=None):
        self.capabilities.append(live_action_capability)
        self.calls.append(f"release:{lease_id}")
        return _receipt(
            "RELEASED",
            target_binding_sha256=self._target_binding_sha256,
            lease_binding_sha256=self._lease_binding_sha256,
        )


class _Monitor(AzurePerformanceMonitorAdapter):
    def __init__(self, *, on_demand_execution_count: int = 500) -> None:
        self.calls: list[tuple[datetime, datetime]] = []
        self.capabilities: list[object] = []
        self.target_bindings: list[str] = []
        self._on_demand_execution_count = on_demand_execution_count

    def observe(
        self,
        start,
        end,
        *,
        live_action_capability=None,
        target_binding_sha256=None,
    ):
        self.calls.append((start, end))
        self.capabilities.append(live_action_capability)
        self.target_bindings.append(target_binding_sha256)
        return _observation(self._on_demand_execution_count)


class _Runner:
    def __init__(self, *, failure: Exception | None = None) -> None:
        self.failure = failure
        self.calls = 0
        self.capability = None

    def run(self, **kwargs):
        self.calls += 1
        self.capability = kwargs.get("_live_action_capability")
        if self.failure is not None:
            raise self.failure
        return _measurement_evidence()


class _FailingFinalStore(PerformanceFinalEvidenceStore):
    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.fail_once = True

    def write_final_evidence(self, evidence):
        if self.fail_once:
            self.fail_once = False
            raise RuntimeError("simulated final persistence crash")
        return super().write_final_evidence(evidence)


class _PostManifestCrashStore(PerformanceFinalEvidenceStore):
    def clear_pending_finalization(self):
        if self.manifest_path.is_file():
            raise RuntimeError("simulated post-manifest crash")
        return super().clear_pending_finalization()


class _ObservedFinalStore(PerformanceFinalEvidenceStore):
    def __init__(self, path: Path, events: list[str]) -> None:
        super().__init__(path)
        self._events = events

    def load_final_evidence(self):
        self._events.append("load-final")
        return super().load_final_evidence()


class AzurePerformanceRuntimeTests(unittest.TestCase):
    def adapter(
        self, *, clock=lambda: NOW, sleeper=None, lease=None, monitor=None
    ):
        monitor = monitor or _Monitor()
        lease = lease or _Lease()
        adapter = AzurePerformanceRuntimeAdapter(
            monitor=monitor,
            lease=lease,
            lease_id=LEASE_ID,
            monitor_window_anchor_utc=START,
            clock=clock,
            sleeper=sleeper,
        )
        return adapter, monitor, lease

    def test_attestation_composes_lease_and_monitor_without_capacity_claim(self):
        adapter, monitor, lease = self.adapter()
        capability = _test_capability()
        summary = adapter.get_attestation(capability).validate(now=NOW)

        self.assertEqual(lease.calls, [f"assert:{LEASE_ID}"])
        self.assertEqual(monitor.calls, [(START, SETTLED_END)])
        self.assertEqual(monitor.capabilities, [capability])
        self.assertEqual(monitor.target_bindings, [TARGET_BINDING_SHA256])
        self.assertEqual(summary["planned_dispatch_count"], 500)
        self.assertEqual(
            summary["tenant_wide_sharepoint_capacity_claim"], "NOT_CLAIMED"
        )
        self.assertEqual(summary["azure_execution_units_gb_seconds"], 1.0)
        self.assertEqual(summary["lease_binding_sha256"], "e" * 64)
        self.assertEqual(summary["monitor_evidence_sha256"], "f" * 64)

    def test_runtime_observation_is_bound_to_attestation_and_held_lease(self):
        adapter, monitor, lease = self.adapter()
        capability = _test_capability()
        observation = adapter.observe(7, "a" * 64, capability)
        summary = observation.validate(now=NOW)

        self.assertEqual(lease.calls, [f"assert:{LEASE_ID}"])
        self.assertEqual(monitor.capabilities, [capability])
        self.assertEqual(monitor.target_bindings, [TARGET_BINDING_SHA256])
        self.assertEqual(summary["measurement_attestation_sha256"], "a" * 64)
        self.assertEqual(summary["lease_binding_sha256"], "e" * 64)

    def test_acquire_and_release_are_explicit_not_implicit(self):
        adapter, _, lease = self.adapter()
        capability = _test_capability()
        adapter.acquire(capability)
        adapter.release(capability)
        self.assertEqual(
            lease.calls,
            [f"acquire:{LEASE_ID}", f"release:{LEASE_ID}"],
        )

    def test_invalid_runtime_inputs_fail_before_monitor_read(self):
        adapter, monitor, lease = self.adapter()
        for attempt, digest in ((-1, "a" * 64), (1, "not-a-sha")):
            with self.subTest(attempt=attempt, digest=digest):
                with self.assertRaisesRegex(
                    ValueError, "PERFORMANCE_RUNTIME_OBSERVATION_INVALID"
                ):
                    adapter.observe(attempt, digest)
        self.assertEqual(monitor.calls, [])
        self.assertEqual(lease.calls, [])

    def test_invalid_clock_fails_after_bound_read(self):
        adapter, _, _ = self.adapter(clock=lambda: datetime(2026, 8, 3, 12, 0))
        with self.assertRaisesRegex(ValueError, "PERFORMANCE_RUNTIME_CLOCK_INVALID"):
            adapter.get_attestation()

    def test_orchestrator_returns_passed_only_after_release(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner()
        with tempfile.TemporaryDirectory() as directory:
            evidence_path = Path(directory) / "final.redacted.json"
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(evidence_path),
            )

            result = orchestrator.run(binding="a" * 64)
            self.assertTrue(evidence_path.is_file())
            self.assertTrue(
                PerformanceFinalEvidenceStore(evidence_path).markdown_path.is_file()
            )
            self.assertTrue(
                PerformanceFinalEvidenceStore(evidence_path).manifest_path.is_file()
            )

        self.assertEqual(result["status"], "PASSED")
        self.assertTrue(result["lease_release_verified"])
        self.assertEqual(result["execution_bindings"], EXECUTION_BINDINGS)
        self.assertEqual(
            result["execution_bindings"]["infrastructure_binding_sha256"],
            INFRASTRUCTURE_BINDING_SHA256,
        )
        self.assertEqual(
            result["completion_bindings"]["lease_release_lifecycle_state_sha256"],
            performance._sha256_text("RELEASED"),
        )
        self.assertEqual(
            result["completion_bindings"]["lease_release_lifecycle_state"],
            "RELEASED",
        )
        self.assertEqual(
            result["completion_bindings"]["target_binding_sha256"],
            EXECUTION_BINDINGS["target_binding_sha256"],
        )
        self.assertEqual(len(result["preflight_evidence_chain"]), 1)
        self.assertEqual(
            result["preflight_evidence_chain"][0][
                "infrastructure_safety_evidence_sha256"
            ],
            EXECUTION_BINDINGS["infrastructure_safety_evidence_sha256"],
        )
        self.assertEqual(
            result["preflight_evidence_chain"][0][
                "lease_acquisition_safety_evidence_sha256"
            ],
            EXECUTION_BINDINGS[
                "lease_acquisition_safety_evidence_sha256"
            ],
        )
        final_attestation = result["completion_bindings"][
            "final_measurement_attestation"
        ]
        self.assertEqual(
            final_attestation["measurement_finished_at_utc"],
            "2026-08-03T12:00:00Z",
        )
        self.assertEqual(
            final_attestation["monitor_window_end_utc"],
            "2026-08-03T12:00:00Z",
        )
        self.assertEqual(final_attestation["monitor_settlement_delay_seconds"], 300)
        self.assertEqual(final_attestation["on_demand_execution_count"], 500)
        self.assertEqual(runner.calls, 1)
        self.assertIsNotNone(runner.capability)
        self.assertTrue(lease.capabilities)
        self.assertTrue(
            all(capability is runner.capability for capability in lease.capabilities)
        )
        self.assertTrue(monitor.capabilities)
        self.assertTrue(
            all(
                capability is runner.capability
                for capability in monitor.capabilities
            )
        )
        self.assertEqual(
            monitor.target_bindings,
            [TARGET_BINDING_SHA256] * len(monitor.capabilities),
        )
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_orchestrator_rejects_arbitrary_preflight_callable(self):
        adapter, _, lease = self.adapter()
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            TypeError, "authorization_verifier"
        ):
            LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_Runner(),
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=lambda **_values: EXECUTION_BINDINGS,
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            )
        self.assertEqual(lease.calls, [])

    def test_orchestrator_releases_after_runner_failure_without_retry_is_forbidden(
        self,
    ):
        adapter, _, lease = self.adapter()
        runner = _Runner(failure=RuntimeError("runner stopped"))
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            )

            with self.assertRaisesRegex(RuntimeError, "runner stopped"):
                orchestrator.run(binding="a" * 64)

        self.assertEqual(runner.calls, 1)
        self.assertEqual(
            lease.calls,
            [f"acquire:{LEASE_ID}"],
        )

    def test_early_failed_measurement_finalizes_and_releases_lease(self):
        adapter, monitor, lease = self.adapter(
            monitor=_Monitor(on_demand_execution_count=1)
        )

        class _FailedRunner(_Runner):
            def run(self, **_kwargs):
                self.calls += 1
                return _failed_measurement_evidence()

        runner = _FailedRunner()
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceFinalEvidenceStore(
                Path(directory) / "final.redacted.json"
            )
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=store,
            )

            result = orchestrator.run(binding="a" * 64)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["completion_bindings"]["final_measurement_attestation"][
                "minimum_on_demand_execution_count"
            ],
            1,
        )
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )
        self.assertEqual(monitor.calls, [(START, SETTLED_END)])

    def test_pre_http_failed_measurement_uses_zero_monitor_floor(self):
        adapter, monitor, lease = self.adapter(
            monitor=_Monitor(on_demand_execution_count=0)
        )

        class _FailedRunner(_Runner):
            def run(self, **_kwargs):
                self.calls += 1
                return _predispatch_failed_measurement_evidence()

        with tempfile.TemporaryDirectory() as directory:
            result = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_FailedRunner(),
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            ).run(binding="a" * 64)

        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(
            result["completion_bindings"]["final_measurement_attestation"][
                "minimum_on_demand_execution_count"
            ],
            0,
        )
        self.assertEqual(monitor.calls, [(START, SETTLED_END)])
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_orchestrator_recovers_terminal_checkpoint_before_release(self):
        class _RecoveringRunner(_Runner):
            def __init__(self):
                super().__init__(failure=RuntimeError("terminal checkpoint written"))
                self.recovery_calls = 0

            def recover_terminal_evidence(self, **kwargs):
                self.recovery_calls += 1
                return _measurement_evidence()

        adapter, _, lease = self.adapter()
        runner = _RecoveringRunner()
        with tempfile.TemporaryDirectory() as directory:
            result = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            ).run(binding="a" * 64)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(runner.calls, 1)
        self.assertEqual(runner.recovery_calls, 1)
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_owner_preflight_blocks_before_any_lease_or_monitor_network(self):
        adapter, monitor, lease = self.adapter()
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_Runner(),
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(lambda: {
                    **EXECUTION_BINDINGS,
                    "owner_approval_body_sha256": "0" * 64,
                }),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_OWNER_PREFLIGHT_INVALID"
            ):
                orchestrator.run(binding="a" * 64)
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_process_fence_blocks_before_owner_or_infrastructure_preflight(self):
        adapter, monitor, lease = self.adapter()
        owner_calls = 0

        def owner_preflight():
            nonlocal owner_calls
            owner_calls += 1
            return _verified_execution_bindings()

        @contextmanager
        def occupied_fence(*_args, **_kwargs):
            raise ValueError("AZURE_BLOB_LEASE_PROCESS_BUSY")
            yield

        lease.execution_fence = occupied_fence
        runner = _Runner()
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    owner_preflight
                ),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            )
            with self.assertRaisesRegex(
                ValueError, "AZURE_BLOB_LEASE_PROCESS_BUSY"
            ):
                orchestrator.run(binding="a" * 64)

        self.assertEqual(owner_calls, 0)
        self.assertEqual(runner.calls, 0)
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_owner_preflight_rejects_each_unverified_execution_binding(self):
        verified_preflight = _verified_execution_bindings()
        for field, value in verified_preflight.items():
            with self.subTest(field=field):
                adapter, monitor, lease = self.adapter()
                drifted = {
                    **verified_preflight,
                    field: ("0" if value[0] != "0" else "f") + value[1:],
                }
                with tempfile.TemporaryDirectory() as directory:
                    orchestrator = LeaseBoundPerformanceAcceptance(
                        runtime=adapter,
                        runner=_Runner(),
                        execution_bindings=EXECUTION_BINDINGS,
                        authorization_verifier=_test_authorization_verifier(
                            lambda drifted=drifted: drifted
                        ),
                        final_evidence_store=PerformanceFinalEvidenceStore(
                            Path(directory) / "final.redacted.json"
                        ),
                    )
                    with self.assertRaisesRegex(
                        ValueError, "PERFORMANCE_OWNER_PREFLIGHT_INVALID"
                    ):
                        orchestrator.run(binding="a" * 64)
                self.assertEqual(lease.calls, [])
                self.assertEqual(monitor.calls, [])

    def test_recovery_accepts_only_rotated_current_safety_receipt_hashes(self):
        initial = dict(EXECUTION_BINDINGS)
        current = {
            **initial,
            "infrastructure_safety_evidence_sha256": "c" * 64,
            "lease_acquisition_safety_evidence_sha256": "d" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            store = PerformanceFinalEvidenceStore(path)
            store.write_terminal_measurement(
                performance_runtime._build_terminal_measurement(
                    evidence=_measurement_evidence(),
                    execution_bindings=initial,
                )
            )
            lease = _Lease(
                infrastructure_safety_evidence_sha256=current[
                    "infrastructure_safety_evidence_sha256"
                ],
                lease_acquisition_safety_evidence_sha256=current[
                    "lease_acquisition_safety_evidence_sha256"
                ],
            )
            adapter, _, _ = self.adapter(lease=lease)

            result = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_Runner(failure=AssertionError("runner replayed")),
                execution_bindings=current,
                authorization_verifier=_test_authorization_verifier(
                    lambda: _owner_preflight_for(current)
                ),
                final_evidence_store=store,
            ).run()

        chain = result["preflight_evidence_chain"]
        self.assertEqual(len(chain), 2)
        self.assertEqual(
            chain[0]["infrastructure_safety_evidence_sha256"],
            initial["infrastructure_safety_evidence_sha256"],
        )
        self.assertEqual(
            chain[1]["infrastructure_safety_evidence_sha256"],
            current["infrastructure_safety_evidence_sha256"],
        )
        self.assertEqual(
            chain[1]["previous_preflight_evidence_sha256"],
            chain[0]["preflight_evidence_sha256"],
        )
        self.assertEqual(result["execution_bindings"], initial)
        self.assertEqual(lease.calls, [f"assert:{LEASE_ID}", f"release:{LEASE_ID}"])

    def test_recovery_rejects_foreign_stable_binding_before_release(self):
        foreign = {
            **EXECUTION_BINDINGS,
            "owner_approval_body_sha256": "f" * 64,
            "infrastructure_safety_evidence_sha256": "c" * 64,
            "lease_acquisition_safety_evidence_sha256": "d" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceFinalEvidenceStore(
                Path(directory) / "final.redacted.json"
            )
            store.write_terminal_measurement(
                performance_runtime._build_terminal_measurement(
                    evidence=_measurement_evidence(),
                    execution_bindings=EXECUTION_BINDINGS,
                )
            )
            lease = _Lease(
                infrastructure_safety_evidence_sha256=foreign[
                    "infrastructure_safety_evidence_sha256"
                ],
                lease_acquisition_safety_evidence_sha256=foreign[
                    "lease_acquisition_safety_evidence_sha256"
                ],
            )
            adapter, monitor, _ = self.adapter(lease=lease)
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_Runner(failure=AssertionError("runner replayed")),
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    lambda: _owner_preflight_for(foreign)
                ),
                final_evidence_store=store,
            )

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_RECOVERY_BINDING_MISMATCH"
            ):
                orchestrator.run()

        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_recovery_rejects_stale_reattestation_before_release(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PerformanceFinalEvidenceStore(
                Path(directory) / "final.redacted.json"
            )
            store.write_terminal_measurement(
                performance_runtime._build_terminal_measurement(
                    evidence=_measurement_evidence(),
                    execution_bindings=EXECUTION_BINDINGS,
                )
            )
            adapter, monitor, lease = self.adapter()

            def stale_preflight():
                raise ValueError("INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID")

            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_Runner(failure=AssertionError("runner replayed")),
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    stale_preflight
                ),
                final_evidence_store=store,
            )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_OWNER_PREFLIGHT_INVALID"
            ):
                orchestrator.run()

        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_two_process_restart_reattests_public_verifier_evidence(self):
        code = (
            "import json,sys; "
            "from tests.test_nac_bff_azure_performance_runtime import "
            "_run_public_verifier_restart_stage as run; "
            "print(json.dumps(run(sys.argv[1], sys.argv[2]), sort_keys=True))"
        )
        environment = {**os.environ, "PYTHONPATH": "src"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            initial = subprocess.run(
                [sys.executable, "-c", code, "initial", str(path)],
                check=True,
                capture_output=True,
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                text=True,
            )
            initial_result = json.loads(initial.stdout)
            terminal_path = PerformanceFinalEvidenceStore(path).terminal_path
            old = datetime.now(UTC).timestamp() - 301
            os.utime(terminal_path, (old, old))
            self.assertGreater(
                datetime.now(UTC).timestamp() - terminal_path.stat().st_mtime,
                300,
            )

            recovered = subprocess.run(
                [sys.executable, "-c", code, "recovery", str(path)],
                check=True,
                capture_output=True,
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                text=True,
            )
            recovered_result = json.loads(recovered.stdout)

        chain = recovered_result["preflight_evidence_chain"]
        self.assertEqual(len(initial_result["preflight_evidence_chain"]), 1)
        self.assertEqual(len(chain), 2)
        self.assertEqual(
            chain[0]["infrastructure_safety_evidence_sha256"],
            initial_result["infrastructure_safety_evidence_sha256"],
        )
        self.assertEqual(
            chain[1]["infrastructure_safety_evidence_sha256"],
            recovered_result["infrastructure_safety_evidence_sha256"],
        )
        self.assertNotEqual(
            chain[0]["infrastructure_safety_evidence_sha256"],
            chain[1]["infrastructure_safety_evidence_sha256"],
        )
        self.assertNotEqual(
            chain[0]["lease_acquisition_safety_evidence_sha256"],
            chain[1]["lease_acquisition_safety_evidence_sha256"],
        )

    def test_terminal_checkpoint_rejects_each_execution_binding_mismatch(self):
        for field, value in EXECUTION_BINDINGS.items():
            with (
                self.subTest(field=field),
                tempfile.TemporaryDirectory() as directory,
            ):
                terminal = performance_runtime._build_terminal_measurement(
                    evidence=_measurement_evidence(),
                    execution_bindings=EXECUTION_BINDINGS,
                )
                terminal["execution_bindings"][field] = (
                    ("0" if value[0] != "0" else "f") + value[1:]
                )
                terminal.pop("terminal_measurement_sha256")
                terminal["terminal_measurement_sha256"] = performance._sha256_json(
                    terminal
                )
                path = Path(directory) / "final.redacted.json"
                store = PerformanceFinalEvidenceStore(path)
                performance_runtime._atomic_private_json_write(
                    store.terminal_path, terminal
                )
                adapter, monitor, lease = self.adapter()
                orchestrator = LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=_Runner(),
                    execution_bindings=EXECUTION_BINDINGS,
                    authorization_verifier=_test_authorization_verifier(),
                    final_evidence_store=store,
                )

                with self.assertRaises(ValueError):
                    orchestrator.run(binding="a" * 64)

                self.assertEqual(lease.calls, [])
                self.assertEqual(monitor.calls, [])

    def test_final_evidence_rejects_each_execution_binding_mismatch(self):
        for field, value in EXECUTION_BINDINGS.items():
            with (
                self.subTest(field=field),
                tempfile.TemporaryDirectory() as directory,
            ):
                final = _final_evidence()
                final["execution_bindings"] = dict(final["execution_bindings"])
                final["execution_bindings"][field] = (
                    ("0" if value[0] != "0" else "f") + value[1:]
                )
                final.pop("final_evidence_sha256")
                final["final_evidence_sha256"] = performance._sha256_json(final)
                store = PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                )
                try:
                    store.write_final_evidence(final)
                except ValueError:
                    continue
                adapter, monitor, lease = self.adapter()
                orchestrator = LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=_Runner(),
                    execution_bindings=EXECUTION_BINDINGS,
                    authorization_verifier=_test_authorization_verifier(),
                    final_evidence_store=store,
                )

                with self.assertRaisesRegex(
                    ValueError, "PERFORMANCE_FINAL_EVIDENCE_BINDING_MISMATCH"
                ):
                    orchestrator.run(binding="a" * 64)

                self.assertEqual(lease.calls, [])
                self.assertEqual(monitor.calls, [])

    def test_final_monitor_window_must_cover_finished_at_before_release(self):
        current = {"value": datetime(2026, 8, 3, 12, 4, 59, tzinfo=UTC)}
        adapter, monitor, lease = self.adapter(
            clock=lambda: current["value"],
            sleeper=lambda _: None,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            runner = _Runner()
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(path),
            )

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED"
            ):
                orchestrator.run(binding="a" * 64)

            self.assertFalse(path.exists())
            self.assertFalse(
                PerformanceFinalEvidenceStore(path).pending_path.exists()
            )
            self.assertTrue(
                PerformanceFinalEvidenceStore(path).terminal_path.exists()
            )
            self.assertEqual(runner.calls, 1)
            self.assertEqual(monitor.calls, [])
            self.assertEqual(
                lease.calls,
                [
                    f"acquire:{LEASE_ID}",
                    f"assert:{LEASE_ID}",
                ],
            )

            current["value"] = datetime(2026, 8, 3, 12, 5, tzinfo=UTC)
            result = orchestrator.run(binding="a" * 64)

            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(runner.calls, 1)
            self.assertFalse(
                PerformanceFinalEvidenceStore(path).terminal_path.exists()
            )
        self.assertEqual(monitor.calls, [(START, SETTLED_END)])
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_completed_final_evidence_readback_reverifies_without_runtime_action(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner()
        owner_calls = 0

        def owner_preflight():
            nonlocal owner_calls
            owner_calls += 1
            return _verified_execution_bindings()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    owner_preflight
                ),
                final_evidence_store=PerformanceFinalEvidenceStore(path),
            )

            first = orchestrator.run(binding="a" * 64)
            runtime_activity_after_first = (
                list(lease.calls),
                list(lease.capabilities),
                list(monitor.calls),
            )
            second = orchestrator.run(binding="a" * 64)

        self.assertEqual(second, first)
        self.assertEqual(runner.calls, 1)
        self.assertEqual(owner_calls, 2)
        self.assertEqual(
            (lease.calls, lease.capabilities, monitor.calls),
            runtime_activity_after_first,
        )

    def test_completed_final_evidence_rejects_unavailable_preflight_before_read(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner(failure=AssertionError("runner replayed"))
        for failure in (
            "OWNER_APPROVAL_UNAVAILABLE",
            "INFRASTRUCTURE_SAFETY_EVIDENCE_INVALID",
        ):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as directory,
            ):
                events: list[str] = []

                def unavailable_preflight(failure=failure):
                    events.append("verify")
                    raise ValueError(failure)

                path = Path(directory) / "final.redacted.json"
                PerformanceFinalEvidenceStore(path).write_final_evidence(
                    _final_evidence()
                )
                orchestrator = LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=runner,
                    execution_bindings=EXECUTION_BINDINGS,
                    authorization_verifier=_test_authorization_verifier(
                        unavailable_preflight
                    ),
                    final_evidence_store=_ObservedFinalStore(path, events),
                )

                with self.assertRaisesRegex(
                    ValueError, "PERFORMANCE_OWNER_PREFLIGHT_INVALID"
                ):
                    orchestrator.run(binding="a" * 64)

                self.assertEqual(events, ["verify"])
        self.assertEqual(runner.calls, 0)
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_completed_final_evidence_is_bound_to_fresh_owner_authority(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner(failure=AssertionError("runner replayed"))
        events: list[str] = []
        forged = _final_evidence_with_owner_binding("f" * 64)

        def current_preflight():
            events.append("verify")
            return _verified_execution_bindings()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            PerformanceFinalEvidenceStore(path).write_final_evidence(forged)
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=forged["execution_bindings"],
                authorization_verifier=_test_authorization_verifier(
                    current_preflight
                ),
                final_evidence_store=_ObservedFinalStore(path, events),
            )

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_FINAL_EVIDENCE_BINDING_MISMATCH"
            ):
                orchestrator.run(binding="a" * 64)

        self.assertEqual(events, ["verify", "load-final"])
        self.assertEqual(runner.calls, 0)
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_completed_final_evidence_rejects_changed_current_safety_before_read(self):
        events: list[str] = []
        changed_lease = _Lease(
            infrastructure_safety_evidence_sha256="c" * 64
        )
        adapter, monitor, lease = self.adapter(lease=changed_lease)
        runner = _Runner(failure=AssertionError("runner replayed"))

        def stale_safety_preflight():
            events.append("verify")
            return _verified_execution_bindings()

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            PerformanceFinalEvidenceStore(path).write_final_evidence(
                _final_evidence()
            )
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    stale_safety_preflight
                ),
                final_evidence_store=_ObservedFinalStore(path, events),
            )

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_OWNER_PREFLIGHT_INVALID"
            ):
                orchestrator.run(binding="a" * 64)

        self.assertEqual(events, ["verify"])
        self.assertEqual(runner.calls, 0)
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_final_monitor_waits_until_the_measurement_window_is_settled(self):
        current = {"value": datetime(2026, 8, 3, 12, 4, 59, tzinfo=UTC)}
        sleeps: list[float] = []

        def sleeper(seconds: float) -> None:
            sleeps.append(seconds)
            current["value"] += timedelta(seconds=seconds)

        adapter, monitor, lease = self.adapter(
            clock=lambda: current["value"], sleeper=sleeper
        )
        capability = _test_capability()
        attestation = adapter.get_validated_final_attestation(
            "2026-08-03T12:00:00Z",
            live_action_capability=capability,
        )

        self.assertEqual(sleeps, [1.0])
        self.assertEqual(monitor.calls, [(START, SETTLED_END)])
        self.assertEqual(monitor.capabilities, [capability])
        self.assertEqual(monitor.target_bindings, [TARGET_BINDING_SHA256])
        self.assertEqual(attestation["monitor_settlement_delay_seconds"], 300)
        self.assertEqual(attestation["on_demand_execution_count"], 500)
        self.assertEqual(attestation["projected_execution_units_gb_seconds"], 0.0)
        self.assertEqual(lease.calls, [f"assert:{LEASE_ID}"])

    def test_finalization_blocks_when_monitor_dispatch_count_is_below_limit(self):
        for dispatch_count in (0, 499):
            with self.subTest(dispatch_count=dispatch_count):
                monitor = _Monitor(
                    on_demand_execution_count=dispatch_count
                )
                adapter, _, lease = self.adapter(monitor=monitor)
                runner = _Runner()
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "final.redacted.json"
                    store = PerformanceFinalEvidenceStore(path)
                    orchestrator = LeaseBoundPerformanceAcceptance(
                        runtime=adapter,
                        runner=runner,
                        execution_bindings=EXECUTION_BINDINGS,
                        authorization_verifier=_test_authorization_verifier(),
                        final_evidence_store=store,
                    )

                    with self.assertRaisesRegex(
                        ValueError,
                        "PERFORMANCE_FINAL_MEASUREMENT_ATTESTATION_INVALID",
                    ):
                        orchestrator.run(binding="a" * 64)

                    self.assertTrue(store.terminal_path.is_file())
                    self.assertFalse(store.pending_path.exists())
                    self.assertFalse(path.exists())
                    self.assertFalse(store.markdown_path.exists())
                    self.assertFalse(store.manifest_path.exists())
                    self.assertEqual(runner.calls, 1)
                    self.assertEqual(monitor.calls, [(START, SETTLED_END)])
                    self.assertEqual(
                        lease.calls,
                        [f"acquire:{LEASE_ID}", f"assert:{LEASE_ID}"],
                    )

    def test_owner_target_binding_drift_blocks_before_network(self):
        adapter, monitor, lease = self.adapter(
            lease=_Lease(target_binding_sha256="0" * 64)
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_TARGET_BINDING_MISMATCH"
            ):
                LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=_Runner(),
                    execution_bindings=EXECUTION_BINDINGS,
                    authorization_verifier=_test_authorization_verifier(),
                    final_evidence_store=PerformanceFinalEvidenceStore(
                        Path(directory) / "final.redacted.json"
                    ),
                )
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_completion_rejects_held_lease_receipt_even_with_valid_digest(self):
        adapter, _, _ = self.adapter()
        with self.assertRaisesRegex(
            ValueError, "PERFORMANCE_COMPLETION_BINDING_INVALID"
        ):
            adapter.completion_bindings(
                _receipt("HELD"), _final_attestation_summary()
            )

    def test_final_evidence_rejects_non_released_exact_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            evidence = _final_evidence()
            completion = evidence["completion_bindings"]
            completion["lease_release_lifecycle_state"] = "HELD"
            completion["lease_release_lifecycle_state_sha256"] = (
                performance._sha256_text("HELD")
            )
            evidence.pop("final_evidence_sha256")
            evidence["final_evidence_sha256"] = performance._sha256_json(evidence)

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
            ):
                PerformanceFinalEvidenceStore(path).write_final_evidence(evidence)

            self.assertFalse(path.exists())

    def test_final_evidence_rejects_tampered_preflight_evidence_chain(self):
        evidence = _final_evidence()
        evidence["preflight_evidence_chain"][0][
            "infrastructure_safety_evidence_sha256"
        ] = "0" * 64
        evidence.pop("final_evidence_sha256")
        evidence["final_evidence_sha256"] = performance._sha256_json(evidence)

        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
        ):
            PerformanceFinalEvidenceStore(
                Path(directory) / "final.redacted.json"
            ).write_final_evidence(evidence)

    def test_final_evidence_rejects_window_that_ends_before_measurement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            evidence = _final_evidence()
            completion = evidence["completion_bindings"]
            attestation = completion["final_measurement_attestation"]
            attestation["monitor_window_end_utc"] = "2026-08-03T11:59:00Z"
            attestation["monitor_settlement_delay_seconds"] = 360
            attestation.pop("attestation_sha256")
            attestation["attestation_sha256"] = performance._sha256_json(
                attestation
            )
            completion["final_measurement_attestation_sha256"] = attestation[
                "attestation_sha256"
            ]
            completion["final_measurement_summary_sha256"] = (
                performance._sha256_json(attestation)
            )
            evidence.pop("final_evidence_sha256")
            evidence["final_evidence_sha256"] = performance._sha256_json(evidence)

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
            ):
                PerformanceFinalEvidenceStore(path).write_final_evidence(evidence)

            self.assertFalse(path.exists())

    def test_final_evidence_rejects_target_binding_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            evidence = _final_evidence()
            completion = evidence["completion_bindings"]
            attestation = completion["final_measurement_attestation"]
            attestation["target_binding_sha256"] = "0" * 64
            attestation.pop("attestation_sha256")
            attestation["attestation_sha256"] = performance._sha256_json(
                attestation
            )
            completion["target_binding_sha256"] = "0" * 64
            completion["final_measurement_attestation_sha256"] = attestation[
                "attestation_sha256"
            ]
            completion["final_measurement_summary_sha256"] = (
                performance._sha256_json(attestation)
            )
            evidence.pop("final_evidence_sha256")
            evidence["final_evidence_sha256"] = performance._sha256_json(evidence)

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
            ):
                PerformanceFinalEvidenceStore(path).write_final_evidence(evidence)

            self.assertFalse(path.exists())

    def test_final_evidence_cross_binds_failed_status_and_monitor_floor(self):
        for field, value in (
            ("status", "PASSED"),
            ("minimum_on_demand_execution_count", 0),
        ):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "final.redacted.json"
                    evidence = _failed_final_evidence()
                    completion = evidence["completion_bindings"]
                    attestation = completion["final_measurement_attestation"]
                    attestation[field] = value
                    if field == "status":
                        attestation["minimum_on_demand_execution_count"] = 500
                    attestation.pop("attestation_sha256")
                    attestation["attestation_sha256"] = performance._sha256_json(
                        attestation
                    )
                    completion["final_measurement_attestation_sha256"] = (
                        attestation["attestation_sha256"]
                    )
                    completion["final_measurement_summary_sha256"] = (
                        performance._sha256_json(attestation)
                    )
                    evidence.pop("final_evidence_sha256")
                    evidence["final_evidence_sha256"] = performance._sha256_json(
                        evidence
                    )

                    with self.assertRaisesRegex(
                        ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
                    ):
                        PerformanceFinalEvidenceStore(path).write_final_evidence(
                            evidence
                        )

                    self.assertFalse(path.exists())

    def test_monitor_anchor_drift_blocks_before_lease_or_monitor_network(self):
        adapter, monitor, lease = self.adapter()
        bindings = {**EXECUTION_BINDINGS, "monitor_window_anchor_sha256": "0" * 64}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_MONITOR_WINDOW_ANCHOR_BINDING_MISMATCH"
            ):
                LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=_Runner(),
                    execution_bindings=bindings,
                    authorization_verifier=_test_authorization_verifier(),
                    final_evidence_store=PerformanceFinalEvidenceStore(
                        Path(directory) / "final.redacted.json"
                    ),
                )
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_lease_acquisition_safety_bindings_block_before_network(self):
        class _DriftedLease(_Lease):
            @property
            def lease_binding_sha256(self):
                return "0" * 64

        adapter, monitor, lease = self.adapter(lease=_DriftedLease())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_LEASE_ACQUISITION_BINDING_MISMATCH"
            ):
                LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=_Runner(),
                    execution_bindings=EXECUTION_BINDINGS,
                    authorization_verifier=_test_authorization_verifier(),
                    final_evidence_store=PerformanceFinalEvidenceStore(
                        Path(directory) / "final.redacted.json"
                    ),
                )
        self.assertEqual(lease.calls, [])
        self.assertEqual(monitor.calls, [])

    def test_nested_measurement_evidence_uses_canonical_exact_schema_validator(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner()
        original_run = runner.run

        def invalid_run(**kwargs):
            evidence = original_run(**kwargs)
            evidence["raw_provider_payload"] = "redacted"
            return evidence

        runner.run = invalid_run
        with tempfile.TemporaryDirectory() as directory:
            orchestrator = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_EVIDENCE_REDACTION_INVALID"
            ):
                orchestrator.run(binding="a" * 64)

        self.assertEqual(monitor.calls, [])
        self.assertEqual(
            lease.calls,
            [f"acquire:{LEASE_ID}", f"release:{LEASE_ID}"],
        )

    def test_post_release_finalization_recovers_without_reacquire_or_monitor(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            failing_store = _FailingFinalStore(path)
            first = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=failing_store,
            )
            with self.assertRaisesRegex(
                RuntimeError, "simulated final persistence crash"
            ):
                first.run(binding="a" * 64)
            self.assertTrue(failing_store.pending_path.is_file())
            self.assertFalse(path.exists())

            resumed_adapter, resumed_monitor, _ = self.adapter(lease=lease)
            resumed_runner = _Runner(failure=AssertionError("runner replayed"))
            recovery_preflight_calls = 0

            def recovery_preflight():
                nonlocal recovery_preflight_calls
                recovery_preflight_calls += 1
                return _verified_execution_bindings()

            resumed = LeaseBoundPerformanceAcceptance(
                runtime=resumed_adapter,
                runner=resumed_runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    recovery_preflight
                ),
                final_evidence_store=PerformanceFinalEvidenceStore(path),
            )
            result = resumed.run(binding="a" * 64)

            self.assertTrue(path.is_file())
            self.assertFalse(failing_store.pending_path.exists())

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(runner.calls, 1)
        self.assertEqual(resumed_runner.calls, 0)
        self.assertEqual(recovery_preflight_calls, 1)
        self.assertEqual(len(result["preflight_evidence_chain"]), 2)
        self.assertEqual(len(monitor.calls), 1)
        self.assertEqual(resumed_monitor.calls, [])
        self.assertEqual(
            result["completion_bindings"]["lease_release_lifecycle_state"],
            "RELEASED",
        )
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_post_manifest_crash_reentry_clears_matching_pending_without_network(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            crashing_store = _PostManifestCrashStore(path)
            first = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=crashing_store,
            )
            with self.assertRaisesRegex(
                RuntimeError, "simulated post-manifest crash"
            ):
                first.run(binding="a" * 64)

            self.assertTrue(path.is_file())
            self.assertTrue(crashing_store.markdown_path.is_file())
            self.assertTrue(crashing_store.manifest_path.is_file())
            self.assertTrue(crashing_store.pending_path.is_file())

            resumed_adapter, resumed_monitor, _ = self.adapter(lease=lease)
            resumed_runner = _Runner(failure=AssertionError("runner replayed"))
            result = LeaseBoundPerformanceAcceptance(
                runtime=resumed_adapter,
                runner=resumed_runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(path),
            ).run(binding="a" * 64)

            self.assertEqual(result["status"], "PASSED")
            self.assertFalse(crashing_store.pending_path.exists())
            self.assertEqual(len(result["preflight_evidence_chain"]), 1)
            self.assertEqual(resumed_runner.calls, 0)

        self.assertEqual(runner.calls, 1)
        self.assertEqual(len(monitor.calls), 1)
        self.assertEqual(resumed_monitor.calls, [])
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_completed_reentry_fails_when_pending_cleanup_cannot_be_proven(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner(failure=AssertionError("runner invoked"))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            store = PerformanceFinalEvidenceStore(path)
            final = _final_evidence()
            pending = performance_runtime._build_pending_finalization(
                evidence=final["measurement_evidence"],
                execution_bindings=final["execution_bindings"],
                final_measurement_attestation=final["completion_bindings"][
                    "final_measurement_attestation"
                ],
                preflight_evidence_chain=final["preflight_evidence_chain"],
            )
            store.write_final_evidence(final)
            store.write_pending_finalization(pending)

            with patch.object(
                store, "clear_pending_finalization", return_value=None
            ), self.assertRaisesRegex(
                ValueError, "PERFORMANCE_PENDING_FINALIZATION_CLEANUP_UNPROVEN"
            ):
                LeaseBoundPerformanceAcceptance(
                    runtime=adapter,
                    runner=runner,
                    execution_bindings=EXECUTION_BINDINGS,
                    authorization_verifier=_test_authorization_verifier(),
                    final_evidence_store=store,
                ).run(binding="a" * 64)

            self.assertTrue(store.pending_path.is_file())

        self.assertEqual(runner.calls, 0)
        self.assertEqual(monitor.calls, [])
        self.assertEqual(lease.calls, [])

    def test_crash_between_json_and_markdown_recovers_from_pending_checkpoint(self):
        adapter, monitor, lease = self.adapter()
        runner = _Runner()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            store = PerformanceFinalEvidenceStore(path)
            first = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=store,
            )
            atomic_write = performance_runtime._atomic_private_write_at

            def crash_before_markdown(directory_fd, name, encoded):
                if name == store.markdown_path.name:
                    raise RuntimeError("crash between final artifacts")
                return atomic_write(directory_fd, name, encoded)

            with patch.object(
                performance_runtime,
                "_atomic_private_write_at",
                side_effect=crash_before_markdown,
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "crash between final artifacts"
                ):
                    first.run(binding="a" * 64)

            self.assertTrue(path.is_file())
            self.assertFalse(store.markdown_path.exists())
            self.assertFalse(store.manifest_path.exists())
            self.assertTrue(store.pending_path.is_file())
            self.assertTrue(store.incomplete_final_evidence)
            self.assertIsNone(store.load_final_evidence())
            store.assert_incomplete_final_evidence_recoverable()

            resumed_adapter, resumed_monitor, _ = self.adapter(lease=lease)
            resumed_runner = _Runner(failure=AssertionError("runner replayed"))
            recovery_preflight_calls = 0

            def recovery_preflight():
                nonlocal recovery_preflight_calls
                recovery_preflight_calls += 1
                return _verified_execution_bindings()

            result = LeaseBoundPerformanceAcceptance(
                runtime=resumed_adapter,
                runner=resumed_runner,
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(
                    recovery_preflight
                ),
                final_evidence_store=PerformanceFinalEvidenceStore(path),
            ).run(binding="a" * 64)

            self.assertEqual(result["status"], "PASSED")
            self.assertTrue(store.manifest_path.is_file())
            self.assertFalse(store.pending_path.exists())
            self.assertFalse(store.incomplete_final_evidence)
            self.assertEqual(resumed_runner.calls, 0)
            self.assertEqual(recovery_preflight_calls, 1)
            self.assertEqual(len(result["preflight_evidence_chain"]), 2)

        self.assertEqual(len(monitor.calls), 1)
        self.assertEqual(resumed_monitor.calls, [])
        self.assertEqual(
            lease.calls,
            [
                f"acquire:{LEASE_ID}",
                f"assert:{LEASE_ID}",
                f"release:{LEASE_ID}",
                f"release:{LEASE_ID}",
            ],
        )

    def test_final_evidence_store_writes_atomically_after_release(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence" / "final.redacted.json"
            evidence = _final_evidence()

            PerformanceFinalEvidenceStore(path).write_final_evidence(evidence)

            self.assertEqual(json.loads(path.read_text(encoding="ascii")), evidence)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            markdown_path = PerformanceFinalEvidenceStore(path).markdown_path
            markdown = markdown_path.read_text(encoding="ascii")
            self.assertIn("Status: `PASSED`", markdown)
            self.assertIn("Tenant-wide SharePoint baseline: `NOT_CLAIMED`", markdown)
            self.assertIn(
                "Tenant-wide SharePoint request allowance: `NOT_CLAIMED`",
                markdown,
            )
            self.assertIn(
                "Tenant-wide SharePoint resource-unit allowance: `NOT_CLAIMED`",
                markdown,
            )
            self.assertIn("Monetary cost: `NOT_CLAIMED`", markdown)
            self.assertIn("Lease lifecycle state: `RELEASED`", markdown)
            self.assertNotIn("NAC-SYN-MATTER-001", markdown)
            self.assertEqual(stat.S_IMODE(markdown_path.stat().st_mode), 0o600)
            manifest_path = PerformanceFinalEvidenceStore(path).manifest_path
            manifest = json.loads(manifest_path.read_text(encoding="ascii"))
            self.assertEqual(
                manifest["final_evidence_sha256"],
                evidence["final_evidence_sha256"],
            )
            self.assertEqual(stat.S_IMODE(manifest_path.stat().st_mode), 0o600)
            self.assertEqual(list(path.parent.glob(".*.tmp")), [])

    def test_final_evidence_requires_every_not_claimed_position(self):
        fields = (
            "tenant_wide_sharepoint_baseline_claim",
            "tenant_wide_sharepoint_request_allowance_claim",
            "tenant_wide_sharepoint_resource_unit_allowance_claim",
            "monetary_cost_claim",
        )
        for field in fields:
            with self.subTest(field=field):
                evidence = _final_evidence()
                evidence[field] = "CLAIMED"
                evidence["final_evidence_sha256"] = performance._sha256_json(
                    {
                        key: value
                        for key, value in evidence.items()
                        if key != "final_evidence_sha256"
                    }
                )
                with self.assertRaisesRegex(
                    ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
                ):
                    performance_runtime._validate_final_evidence(evidence)

    def test_final_and_pending_writes_stay_on_validated_parent_descriptor(self):
        pending = performance_runtime._build_pending_finalization(
            evidence=_measurement_evidence(),
            execution_bindings=EXECUTION_BINDINGS,
            final_measurement_attestation=_final_attestation_summary(),
        )
        for artifact in ("final", "pending"):
            with (
                self.subTest(artifact=artifact),
                tempfile.TemporaryDirectory() as root,
            ):
                base = Path(root)
                parent = base / "evidence"
                moved_parent = base / "validated-parent"
                external = base / "external"
                parent.mkdir(mode=0o700)
                external.mkdir(mode=0o700)
                store = PerformanceFinalEvidenceStore(
                    parent / "final.redacted.json"
                )
                real_replace = os.replace
                swapped = False

                def swap_parent_before_replace(
                    source,
                    destination,
                    *,
                    src_dir_fd=None,
                    dst_dir_fd=None,
                ):
                    nonlocal swapped
                    if not swapped:
                        swapped = True
                        os.rename(parent, moved_parent)
                        os.symlink(external, parent, target_is_directory=True)
                    return real_replace(
                        source,
                        destination,
                        src_dir_fd=src_dir_fd,
                        dst_dir_fd=dst_dir_fd,
                    )

                with patch.object(
                    performance_runtime.os,
                    "replace",
                    side_effect=swap_parent_before_replace,
                ):
                    if artifact == "final":
                        store.write_final_evidence(_final_evidence())
                        expected_name = "final.redacted.json"
                    else:
                        store.write_pending_finalization(pending)
                        expected_name = store.pending_path.name

                self.assertTrue((moved_parent / expected_name).is_file())
                self.assertEqual(list(external.iterdir()), [])

    def test_final_and_pending_reads_stay_on_validated_parent_descriptor(self):
        pending = performance_runtime._build_pending_finalization(
            evidence=_measurement_evidence(),
            execution_bindings=EXECUTION_BINDINGS,
            final_measurement_attestation=_final_attestation_summary(),
        )
        for artifact in ("final", "pending"):
            with (
                self.subTest(artifact=artifact),
                tempfile.TemporaryDirectory() as root,
            ):
                base = Path(root)
                parent = base / "evidence"
                moved_parent = base / "validated-parent"
                external = base / "external"
                parent.mkdir(mode=0o700)
                external.mkdir(mode=0o700)
                store = PerformanceFinalEvidenceStore(
                    parent / "final.redacted.json"
                )
                if artifact == "final":
                    expected = _final_evidence()
                    store.write_final_evidence(expected)
                    load = store.load_final_evidence
                else:
                    expected = pending
                    store.write_pending_finalization(expected)
                    load = store.load_pending_finalization
                real_read = performance_runtime._read_private_bytes_at
                swapped = False

                def swap_parent_after_first_read(
                    directory_fd, name, *, error_code
                ):
                    nonlocal swapped
                    result = real_read(directory_fd, name, error_code=error_code)
                    if not swapped:
                        swapped = True
                        os.rename(parent, moved_parent)
                        os.symlink(external, parent, target_is_directory=True)
                    return result

                with patch.object(
                    performance_runtime,
                    "_read_private_bytes_at",
                    side_effect=swap_parent_after_first_read,
                ):
                    self.assertEqual(load(), expected)

                self.assertEqual(list(external.iterdir()), [])

    def test_symlink_in_any_ancestor_blocks_final_and_pending_evidence(self):
        pending = performance_runtime._build_pending_finalization(
            evidence=_measurement_evidence(),
            execution_bindings=EXECUTION_BINDINGS,
            final_measurement_attestation=_final_attestation_summary(),
        )
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            external = base / "external"
            external.mkdir(mode=0o700)
            linked = base / "linked"
            os.symlink(external, linked, target_is_directory=True)
            parent = linked / "nested" / "evidence"
            store = PerformanceFinalEvidenceStore(parent / "final.redacted.json")

            for artifact, write in (
                ("final", lambda: store.write_final_evidence(_final_evidence())),
                ("pending", lambda: store.write_pending_finalization(pending)),
            ):
                with self.subTest(artifact=artifact), self.assertRaisesRegex(
                    ValueError, "PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID"
                ):
                    write()

            self.assertEqual(list(external.iterdir()), [])

    def test_symlinked_final_and_pending_artifacts_are_never_followed(self):
        pending = performance_runtime._build_pending_finalization(
            evidence=_measurement_evidence(),
            execution_bindings=EXECUTION_BINDINGS,
            final_measurement_attestation=_final_attestation_summary(),
        )
        for artifact in ("manifest", "pending"):
            with (
                self.subTest(artifact=artifact),
                tempfile.TemporaryDirectory() as root,
            ):
                path = Path(root) / "final.redacted.json"
                store = PerformanceFinalEvidenceStore(path)
                if artifact == "manifest":
                    store.write_final_evidence(_final_evidence())
                    target = store.manifest_path
                    load = store.load_final_evidence
                else:
                    store.write_pending_finalization(pending)
                    target = store.pending_path
                    load = store.load_pending_finalization
                external = Path(root) / f"external-{artifact}"
                target.rename(external)
                target.symlink_to(external)

                with self.assertRaisesRegex(
                    ValueError, "PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID"
                ):
                    load()

    def test_final_evidence_is_incomplete_without_completion_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            store = PerformanceFinalEvidenceStore(path)
            store.write_final_evidence(_final_evidence())
            store.manifest_path.unlink()

            self.assertIsNone(store.load_final_evidence())
            self.assertTrue(store.incomplete_final_evidence)
            with self.assertRaisesRegex(
                ValueError,
                "PERFORMANCE_INCOMPLETE_FINAL_EVIDENCE_UNRECOVERABLE",
            ):
                store.assert_incomplete_final_evidence_recoverable()

    def test_completion_manifest_fails_closed_for_missing_or_tampered_artifacts(self):
        for artifact, mutation in (
            ("json", "missing"),
            ("markdown", "missing"),
            ("json", "tampered"),
            ("markdown", "tampered"),
        ):
            with self.subTest(artifact=artifact, mutation=mutation):
                with tempfile.TemporaryDirectory() as directory:
                    path = Path(directory) / "final.redacted.json"
                    store = PerformanceFinalEvidenceStore(path)
                    store.write_final_evidence(_final_evidence())
                    artifact_path = (
                        path if artifact == "json" else store.markdown_path
                    )
                    if mutation == "missing":
                        artifact_path.unlink()
                    else:
                        artifact_path.write_bytes(
                            artifact_path.read_bytes() + b"tampered\n"
                        )

                    with self.assertRaisesRegex(
                        ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
                    ):
                        store.load_final_evidence()

    def test_completion_manifest_requires_exact_rendered_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            store = PerformanceFinalEvidenceStore(path)
            store.write_final_evidence(_final_evidence())
            changed = store.markdown_path.read_text(encoding="ascii").replace(
                "Status: `PASSED`", "Status: `FAILED`"
            )
            store.markdown_path.write_text(changed, encoding="ascii")
            manifest = json.loads(
                store.manifest_path.read_text(encoding="ascii")
            )
            manifest["final_evidence_markdown_sha256"] = (
                performance_runtime._sha256_bytes(changed.encode("ascii"))
            )
            manifest.pop("completion_manifest_sha256")
            manifest["completion_manifest_sha256"] = performance._sha256_json(
                manifest
            )
            store.manifest_path.write_text(
                performance_runtime._canonical_json(manifest) + "\n",
                encoding="ascii",
            )

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
            ):
                store.load_final_evidence()

    def test_completion_manifest_requires_private_regular_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final.redacted.json"
            store = PerformanceFinalEvidenceStore(path)
            store.write_final_evidence(_final_evidence())
            store.markdown_path.chmod(0o640)

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_FINAL_EVIDENCE_INVALID"
            ):
                store.load_final_evidence()

    def test_final_evidence_persists_validated_monitor_cap_binding(self):
        adapter, _, _ = self.adapter()
        with tempfile.TemporaryDirectory() as directory:
            result = LeaseBoundPerformanceAcceptance(
                runtime=adapter,
                runner=_Runner(),
                execution_bindings=EXECUTION_BINDINGS,
                authorization_verifier=_test_authorization_verifier(),
                final_evidence_store=PerformanceFinalEvidenceStore(
                    Path(directory) / "final.redacted.json"
                ),
            ).run(binding="a" * 64)

        completion = result["completion_bindings"]
        self.assertEqual(completion["monitor_evidence_sha256"], "f" * 64)
        self.assertEqual(
            completion["final_measurement_attestation_sha256"],
            _final_attestation_summary()["attestation_sha256"],
        )
        self.assertEqual(
            completion["final_measurement_attestation"],
            _final_attestation_summary(),
        )
        self.assertTrue(completion["final_execution_units_below_cap"])
        self.assertFalse(completion["final_telemetry_cap_reached"])
        self.assertEqual(
            completion["final_observed_execution_units_gb_seconds"], 1.0
        )


if __name__ == "__main__":
    unittest.main()
