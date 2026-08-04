from __future__ import annotations

from datetime import UTC, datetime, timedelta
from contextlib import AbstractContextManager
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from typing import Any, Callable, Mapping, Protocol, Sequence
from uuid import UUID

from .azure_activation import WORKSPACE_ID
from .azure_performance_acceptance import (
    BoundPerformanceAuthorizationVerifier,
    MEASUREMENT_MODE,
    TENANT_WIDE_SHAREPOINT_CAPACITY_CLAIM,
    TOTAL_REQUEST_LIMIT,
    MeasurementAttestation,
    RuntimeSafetyObservation,
    _MAX_EXECUTION_UNITS_GB_SECONDS,
    _validate_redacted_evidence,
    build_performance_acceptance_plan,
    measurement_policy_sha256,
)
from .azure_performance_authorization import (
    SecurePerformancePathError,
    VerifiedLiveActionCapability,
    VerifiedPerformanceAuthority,
    _open_root_anchored_private_parent,
)
from .azure_performance_lease import AzureBlobLeaseAdapter, AzureBlobLeaseReceipt
from .azure_performance_monitor import (
    INGESTION_LAG_SECONDS,
    AzurePerformanceMonitorAdapter,
    AzurePerformanceObservation,
)


TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
MAXIMUM_DISPATCHES_PER_MINUTE = 6
PROJECTED_EXECUTION_UNITS_GB_SECONDS = 30_000.0
_UNSETTLED_DISPATCH_RESERVE = (
    MAXIMUM_DISPATCHES_PER_MINUTE * INGESTION_LAG_SECONDS // 60
)
_MAX_FINAL_SETTLEMENT_WAIT_SECONDS = INGESTION_LAG_SECONDS + 60
_MAX_EVIDENCE_BYTES = 4 * 1024 * 1024
_PREFLIGHT_CHAIN_SCHEMA = "nac.m365-bff-performance-preflight-evidence/v1"
_ZERO_SHA256 = "0" * 64


class PerformanceRunPort(Protocol):
    def run(self, **kwargs: Any) -> Mapping[str, Any]: ...


class FinalEvidencePort(Protocol):
    def load_final_evidence(self) -> Mapping[str, Any] | None: ...

    def assert_incomplete_final_evidence_recoverable(self) -> None: ...

    def load_terminal_measurement(self) -> Mapping[str, Any] | None: ...

    def write_terminal_measurement(self, terminal: Mapping[str, Any]) -> None: ...

    def clear_terminal_measurement(self) -> None: ...

    def load_pending_finalization(self) -> Mapping[str, Any] | None: ...

    def write_pending_finalization(self, pending: Mapping[str, Any]) -> None: ...

    def write_final_evidence(self, evidence: Mapping[str, Any]) -> None: ...

    def clear_pending_finalization(self) -> None: ...


class AzurePerformanceRuntimeAdapter:
    """Compose the fixed Monitor read and dedicated Blob lease boundaries."""

    def __init__(
        self,
        *,
        monitor: AzurePerformanceMonitorAdapter,
        lease: AzureBlobLeaseAdapter,
        lease_id: UUID,
        monitor_window_anchor_utc: datetime,
        clock: Callable[[], datetime] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        if not isinstance(monitor, AzurePerformanceMonitorAdapter):
            raise TypeError("monitor")
        if not isinstance(lease, AzureBlobLeaseAdapter):
            raise TypeError("lease")
        if type(lease_id) is not UUID:
            raise TypeError("lease_id")
        if (
            not isinstance(monitor_window_anchor_utc, datetime)
            or monitor_window_anchor_utc.tzinfo is None
            or monitor_window_anchor_utc.utcoffset() is None
            or monitor_window_anchor_utc.second != 0
            or monitor_window_anchor_utc.microsecond != 0
        ):
            raise TypeError("monitor_window_anchor_utc")
        if clock is not None and not callable(clock):
            raise TypeError("clock")
        if sleeper is not None and not callable(sleeper):
            raise TypeError("sleeper")
        self._monitor = monitor
        self._lease = lease
        self._lease_id = lease_id
        self._monitor_window_anchor_utc = monitor_window_anchor_utc.astimezone(UTC)
        self._monitor_window_anchor_sha256 = _sha256_text(
            _timestamp(self._monitor_window_anchor_utc)
        )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._sleeper = sleeper or time.sleep

    def acquire(
        self, capability: VerifiedLiveActionCapability
    ) -> AzureBlobLeaseReceipt:
        return self._lease.acquire(
            self._lease_id, live_action_capability=capability
        )

    def release(
        self, capability: VerifiedLiveActionCapability
    ) -> AzureBlobLeaseReceipt:
        return self._lease.release(
            self._lease_id, live_action_capability=capability
        )

    def execution_fence(
        self, capability: VerifiedLiveActionCapability | None = None
    ) -> AbstractContextManager[None]:
        return self._lease.execution_fence(
            live_action_capability=capability
        )

    @property
    def target_binding_sha256(self) -> str:
        return self._lease.target_binding_sha256

    @property
    def lease_binding_sha256(self) -> str:
        return self._lease.lease_binding_sha256

    @property
    def infrastructure_safety_evidence_sha256(self) -> str:
        return self._lease.infrastructure_safety_evidence_sha256

    @property
    def lease_acquisition_safety_evidence_sha256(self) -> str:
        return self._lease.lease_acquisition_safety_evidence_sha256

    @property
    def monitor_window_anchor_sha256(self) -> str:
        return self._monitor_window_anchor_sha256

    def completion_bindings(
        self,
        release_receipt: AzureBlobLeaseReceipt,
        final_measurement_attestation: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(release_receipt, AzureBlobLeaseReceipt):
            raise ValueError("PERFORMANCE_LEASE_RELEASE_EVIDENCE_INVALID")
        attestation = _validate_final_measurement_attestation(
            final_measurement_attestation,
            expected_monitor_window_anchor_sha256=(
                self._monitor_window_anchor_sha256
            ),
            expected_target_binding_sha256=release_receipt.target_binding_sha256,
        )
        payload = {
            "lease_binding_sha256": release_receipt.lease_binding_sha256,
            "target_binding_sha256": release_receipt.target_binding_sha256,
            "lease_release_lifecycle_state": release_receipt.lifecycle_state,
            "lease_release_lifecycle_state_sha256": (
                _sha256_text(release_receipt.lifecycle_state)
            ),
            "lease_release_state_evidence_sha256": (
                release_receipt.lifecycle_state_sha256
            ),
            "monitor_binding_sha256": attestation["monitor_binding_sha256"],
            "monitor_evidence_sha256": attestation["monitor_evidence_sha256"],
            "monitor_window_anchor_sha256": self._monitor_window_anchor_sha256,
            "final_measurement_attestation_sha256": attestation[
                "attestation_sha256"
            ],
            "final_measurement_attestation": attestation,
            "final_measurement_summary_sha256": _sha256_json(attestation),
            "final_observed_execution_units_gb_seconds": attestation[
                "azure_execution_units_gb_seconds"
            ],
            "final_projected_execution_units_gb_seconds": attestation[
                "projected_execution_units_gb_seconds"
            ],
            "final_execution_units_below_cap": attestation[
                "execution_units_below_cap"
            ],
            "final_telemetry_cap_reached": attestation[
                "telemetry_cap_reached"
            ],
        }
        if (
            release_receipt.lifecycle_state != "RELEASED"
            or release_receipt.target_binding_sha256
            != attestation["target_binding_sha256"]
            or release_receipt.lease_binding_sha256
            != attestation["lease_binding_sha256"]
            or any(
                not _is_sha256(payload[key])
                for key in (
                    "lease_binding_sha256",
                    "target_binding_sha256",
                    "lease_release_lifecycle_state_sha256",
                    "lease_release_state_evidence_sha256",
                    "monitor_binding_sha256",
                    "monitor_evidence_sha256",
                    "monitor_window_anchor_sha256",
                    "final_measurement_attestation_sha256",
                    "final_measurement_summary_sha256",
                )
            )
        ):
            raise ValueError("PERFORMANCE_COMPLETION_BINDING_INVALID")
        return payload

    def get_validated_final_attestation(
        self,
        measurement_finished_at_utc: str,
        *,
        measurement_outcome: str = "PASSED",
        minimum_on_demand_execution_count: int = TOTAL_REQUEST_LIMIT,
        live_action_capability: VerifiedLiveActionCapability,
    ) -> dict[str, Any]:
        if (
            measurement_outcome not in {"PASSED", "FAILED"}
            or type(minimum_on_demand_execution_count) is not int
            or minimum_on_demand_execution_count < 0
            or minimum_on_demand_execution_count > TOTAL_REQUEST_LIMIT
            or (
                measurement_outcome == "PASSED"
                and minimum_on_demand_execution_count != TOTAL_REQUEST_LIMIT
            )
        ):
            raise ValueError("PERFORMANCE_FINAL_MEASUREMENT_ATTESTATION_INVALID")
        finished_at = _parse_timestamp(measurement_finished_at_utc)
        self._wait_for_final_settlement(finished_at)
        receipt, observation, observed_at, window_start, window_end = (
            self._observe_bound_state(
                minimum_window_end_utc=finished_at,
                live_action_capability=live_action_capability,
            )
        )
        attestation = self._measurement_attestation(
            receipt, observation, observed_at
        ).validate(now=observed_at)
        measurement_attestation_sha256 = attestation.pop("attestation_sha256")
        attestation["projected_execution_units_gb_seconds"] = 0.0
        attestation["execution_units_below_cap"] = (
            float(attestation["azure_execution_units_gb_seconds"])
            <= _MAX_EXECUTION_UNITS_GB_SECONDS
        )
        result = {
            **attestation,
            "status": measurement_outcome,
            "minimum_on_demand_execution_count": (
                minimum_on_demand_execution_count
            ),
            "on_demand_execution_count": _exact_int(
                observation.on_demand_execution_count
            ),
            "measurement_attestation_sha256": measurement_attestation_sha256,
            "target_binding_sha256": receipt.target_binding_sha256,
            "measurement_finished_at_utc": _timestamp(finished_at),
            "monitor_window_start_utc": _timestamp(window_start),
            "monitor_window_end_utc": _timestamp(window_end),
            "monitor_observed_at_utc": _timestamp(observed_at),
            "monitor_settlement_delay_seconds": int(
                (observed_at - window_end).total_seconds()
            ),
        }
        result["attestation_sha256"] = _sha256_json(result)
        return _validate_final_measurement_attestation(
            result,
            expected_monitor_window_anchor_sha256=(
                self._monitor_window_anchor_sha256
            ),
            expected_target_binding_sha256=receipt.target_binding_sha256,
            expected_measurement_finished_at_utc=_timestamp(finished_at),
            expected_measurement_outcome=measurement_outcome,
            expected_minimum_on_demand_execution_count=(
                minimum_on_demand_execution_count
            ),
        )

    def _wait_for_final_settlement(self, finished_at: datetime) -> None:
        window_end = finished_at.astimezone(UTC).replace(second=0, microsecond=0)
        if window_end < finished_at.astimezone(UTC):
            window_end += timedelta(minutes=1)
        ready_at = window_end + timedelta(seconds=INGESTION_LAG_SECONDS)
        delay = (ready_at - self._validated_now()).total_seconds()
        if delay > _MAX_FINAL_SETTLEMENT_WAIT_SECONDS:
            raise ValueError("PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED")
        if delay > 0:
            self._sleeper(delay)

    def get_attestation(
        self,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> MeasurementAttestation:
        receipt, observation, observed_at, _, _ = self._observe_bound_state(
            live_action_capability=live_action_capability
        )
        return self._measurement_attestation(receipt, observation, observed_at)

    def _measurement_attestation(
        self,
        receipt: AzureBlobLeaseReceipt,
        observation: AzurePerformanceObservation,
        observed_at: datetime,
    ) -> MeasurementAttestation:
        return MeasurementAttestation(
            measurement_mode=MEASUREMENT_MODE,
            tenant_wide_sharepoint_capacity_claim=(
                TENANT_WIDE_SHAREPOINT_CAPACITY_CLAIM
            ),
            maximum_dispatches_per_minute=MAXIMUM_DISPATCHES_PER_MINUTE,
            planned_dispatch_count=TOTAL_REQUEST_LIMIT,
            always_ready_units=_exact_int(observation.always_ready_units),
            projected_execution_units_gb_seconds=(
                PROJECTED_EXECUTION_UNITS_GB_SECONDS
            ),
            observed_execution_units_gb_seconds=float(
                observation.observed_execution_units_gb_seconds
            ),
            telemetry_cap_reached=False,
            measurement_policy_sha256=measurement_policy_sha256(),
            monitor_binding_sha256=observation.monitor_binding_sha256,
            monitor_evidence_sha256=observation.monitor_evidence_sha256,
            monitor_window_anchor_sha256=self._monitor_window_anchor_sha256,
            lease_binding_sha256=receipt.lease_binding_sha256,
            observed_at_utc=_timestamp(observed_at),
            tenant_binding_sha256=_sha256_text(TENANT_ID),
            workspace_binding_sha256=_sha256_text(WORKSPACE_ID),
        )

    def observe(
        self,
        dispatch_attempt_count: int,
        measurement_attestation_sha256: str,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> RuntimeSafetyObservation:
        if type(dispatch_attempt_count) is not int or dispatch_attempt_count < 0:
            raise ValueError("PERFORMANCE_RUNTIME_OBSERVATION_INVALID")
        if not _is_sha256(measurement_attestation_sha256):
            raise ValueError("PERFORMANCE_RUNTIME_OBSERVATION_INVALID")
        receipt, observation, observed_at, _, _ = self._observe_bound_state(
            live_action_capability=live_action_capability
        )
        return RuntimeSafetyObservation(
            observed_execution_units_gb_seconds=float(
                observation.observed_execution_units_gb_seconds
            ),
            projected_remaining_execution_units_gb_seconds=(
                PROJECTED_EXECUTION_UNITS_GB_SECONDS
                * min(
                    TOTAL_REQUEST_LIMIT,
                    max(TOTAL_REQUEST_LIMIT - dispatch_attempt_count, 0)
                    + min(dispatch_attempt_count, _UNSETTLED_DISPATCH_RESERVE),
                )
                / TOTAL_REQUEST_LIMIT
            ),
            always_ready_units=_exact_int(observation.always_ready_units),
            telemetry_cap_reached=False,
            monitor_binding_sha256=observation.monitor_binding_sha256,
            monitor_evidence_sha256=observation.monitor_evidence_sha256,
            monitor_window_anchor_sha256=self._monitor_window_anchor_sha256,
            lease_binding_sha256=receipt.lease_binding_sha256,
            measurement_attestation_sha256=measurement_attestation_sha256,
            observed_at_utc=_timestamp(observed_at),
        )

    def _observe_bound_state(
        self,
        *,
        minimum_window_end_utc: datetime | None = None,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> tuple[
        AzureBlobLeaseReceipt,
        AzurePerformanceObservation,
        datetime,
        datetime,
        datetime,
    ]:
        receipt = self._lease.assert_held(
            self._lease_id,
            live_action_capability=live_action_capability,
        )
        current = self._validated_now()
        end = (
            current.astimezone(UTC) - timedelta(seconds=INGESTION_LAG_SECONDS)
        ).replace(second=0, microsecond=0)
        start = self._monitor_window_anchor_utc
        if (
            end <= start
            or (
                minimum_window_end_utc is not None
                and end < minimum_window_end_utc.astimezone(UTC)
            )
        ):
            raise ValueError("PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED")
        observation = self._monitor.observe(
            start,
            end,
            live_action_capability=live_action_capability,
            target_binding_sha256=self.target_binding_sha256,
        )
        return receipt, observation, current.astimezone(UTC), start, end

    def _validated_now(self) -> datetime:
        current = self._clock()
        if (
            not isinstance(current, datetime)
            or current.tzinfo is None
            or current.utcoffset() is None
        ):
            raise ValueError("PERFORMANCE_RUNTIME_CLOCK_INVALID")
        return current.astimezone(UTC)


class LeaseBoundPerformanceAcceptance:
    """Expose a run result only after the dedicated remote lease is released."""

    def __init__(
        self,
        *,
        runtime: AzurePerformanceRuntimeAdapter,
        runner: PerformanceRunPort,
        execution_bindings: Mapping[str, str],
        authorization_verifier: BoundPerformanceAuthorizationVerifier,
        final_evidence_store: FinalEvidencePort,
    ) -> None:
        if not isinstance(runtime, AzurePerformanceRuntimeAdapter):
            raise TypeError("runtime")
        if not callable(getattr(runner, "run", None)):
            raise TypeError("runner")
        if type(authorization_verifier) is not BoundPerformanceAuthorizationVerifier:
            raise TypeError("authorization_verifier")
        required_store_methods = (
            "load_final_evidence",
            "assert_incomplete_final_evidence_recoverable",
            "load_terminal_measurement",
            "write_terminal_measurement",
            "clear_terminal_measurement",
            "load_pending_finalization",
            "write_pending_finalization",
            "write_final_evidence",
            "clear_pending_finalization",
        )
        if any(
            not callable(getattr(final_evidence_store, method, None))
            for method in required_store_methods
        ):
            raise TypeError("final_evidence_store")
        self._runtime = runtime
        self._runner = runner
        self._execution_bindings = _validate_execution_bindings(execution_bindings)
        if (
            runtime.monitor_window_anchor_sha256
            != self._execution_bindings["monitor_window_anchor_sha256"]
        ):
            raise ValueError("PERFORMANCE_MONITOR_WINDOW_ANCHOR_BINDING_MISMATCH")
        if (
            runtime.target_binding_sha256
            != self._execution_bindings["target_binding_sha256"]
        ):
            raise ValueError("PERFORMANCE_TARGET_BINDING_MISMATCH")
        if (
            runtime.lease_binding_sha256
            != self._execution_bindings["lease_binding_sha256"]
        ):
            raise ValueError("PERFORMANCE_LEASE_ACQUISITION_BINDING_MISMATCH")
        self._authorization_verifier = authorization_verifier
        self._final_evidence_store = final_evidence_store

    def run(self, **kwargs: Any) -> Mapping[str, Any]:
        with self._runtime.execution_fence():
            authority = self._verify_current_preflight(kwargs)
            return self._run_fenced(authority, **kwargs)

    def _run_fenced(
        self,
        authority: VerifiedPerformanceAuthority,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        capability = authority.capability
        current_bindings = dict(authority.execution_bindings)
        completed = self._final_evidence_store.load_final_evidence()
        if completed is not None:
            self._assert_final_evidence_bound_to_authority(
                completed, current_bindings
            )
            self._clear_matching_committed_pending_finalization(completed)
            return completed
        self._final_evidence_store.assert_incomplete_final_evidence_recoverable()
        pending = self._final_evidence_store.load_pending_finalization()
        if pending is not None:
            recovered = self._recover_checkpoint_preflight(
                pending,
                digest_field="pending_finalization_sha256",
                validator=_validate_pending_finalization,
                current=current_bindings,
            )
            self._final_evidence_store.write_pending_finalization(recovered)
            return self._finalize_pending(recovered, capability)
        terminal = self._final_evidence_store.load_terminal_measurement()
        if terminal is not None:
            recovered = self._recover_checkpoint_preflight(
                terminal,
                digest_field="terminal_measurement_sha256",
                validator=_validate_terminal_measurement,
                current=current_bindings,
            )
            self._final_evidence_store.write_terminal_measurement(recovered)
            return self._complete_terminal_measurement(recovered, capability)
        if current_bindings != self._execution_bindings:
            raise ValueError("PERFORMANCE_OWNER_PREFLIGHT_INVALID")
        acquired_receipt = self._runtime.acquire(capability)
        try:
            _validate_lease_receipt(
                acquired_receipt,
                expected_target_binding_sha256=self._execution_bindings[
                    "target_binding_sha256"
                ],
                expected_lifecycle_state="HELD",
            )
        except ValueError:
            self._runtime.release(capability)
            raise
        try:
            evidence = self._runner.run(
                **kwargs,
                _live_action_capability=capability,
            )
        except Exception:
            recover = getattr(self._runner, "recover_terminal_evidence", None)
            if not callable(recover):
                raise
            try:
                evidence = recover(**kwargs)
            except Exception:
                raise
            if evidence is None:
                raise
        if not isinstance(evidence, Mapping):
            self._runtime.release(capability)
            raise ValueError("PERFORMANCE_EVIDENCE_INVALID")
        try:
            _validate_redacted_evidence(evidence)
        except Exception:
            self._runtime.release(capability)
            raise
        if evidence.get("owner_approval_body_sha256") != self._execution_bindings[
            "owner_approval_body_sha256"
        ]:
            self._runtime.release(capability)
            raise ValueError("PERFORMANCE_OWNER_EVIDENCE_BINDING_MISMATCH")
        terminal = _build_terminal_measurement(
            evidence=evidence,
            execution_bindings=self._execution_bindings,
            preflight_evidence_chain=_initial_preflight_evidence_chain(
                self._execution_bindings
            ),
        )
        self._final_evidence_store.write_terminal_measurement(terminal)
        return self._complete_terminal_measurement(terminal, capability)

    def _verify_current_preflight(
        self, run_arguments: Mapping[str, Any]
    ) -> VerifiedPerformanceAuthority:
        try:
            authority = (
                self._authorization_verifier.verify_owner_and_infrastructure_before_lease(
                    approval_reference=str(
                        run_arguments.get("approval_reference", "")
                    ),
                    contract_sha256=self._execution_bindings[
                        "contract_sha256"
                    ],
                    activation_hash=self._execution_bindings[
                        "expected_activation_hash"
                    ],
                    correlation_id=str(run_arguments.get("correlation_id", "")),
                    lease_binding_sha256=self._runtime.lease_binding_sha256,
                    lease_acquisition_safety_evidence_sha256=(
                        self._runtime.lease_acquisition_safety_evidence_sha256
                    ),
                )
            )
            if type(authority) is not VerifiedPerformanceAuthority:
                raise TypeError
            current = _validate_execution_bindings(authority.execution_bindings)
        except (TypeError, ValueError):
            raise ValueError("PERFORMANCE_OWNER_PREFLIGHT_INVALID") from None
        if (
            current["infrastructure_safety_evidence_sha256"]
            != self._runtime.infrastructure_safety_evidence_sha256
        ):
            raise ValueError("PERFORMANCE_OWNER_PREFLIGHT_INVALID")
        return authority

    def _assert_final_evidence_bound_to_authority(
        self,
        completed: Mapping[str, Any],
        current: Mapping[str, str],
    ) -> None:
        final_bindings = completed.get("execution_bindings")
        if not _stable_execution_bindings_match(
            final_bindings, self._execution_bindings
        ) or not _stable_execution_bindings_match(final_bindings, current):
            raise ValueError("PERFORMANCE_FINAL_EVIDENCE_BINDING_MISMATCH")

    def _clear_matching_committed_pending_finalization(
        self, completed: Mapping[str, Any]
    ) -> None:
        pending = self._final_evidence_store.load_pending_finalization()
        if pending is None:
            return
        validated = _validate_pending_finalization(pending)
        completion = completed.get("completion_bindings")
        if not isinstance(completion, Mapping) or (
            validated["measurement_evidence"]
            != completed.get("measurement_evidence")
            or validated["measurement_evidence_sha256"]
            != completed.get("measurement_evidence_sha256")
            or validated["execution_bindings"]
            != completed.get("execution_bindings")
            or validated["preflight_evidence_chain"]
            != completed.get("preflight_evidence_chain")
            or validated["final_measurement_attestation"]
            != completion.get("final_measurement_attestation")
            or validated["final_measurement_summary_sha256"]
            != completion.get("final_measurement_summary_sha256")
        ):
            raise ValueError("PERFORMANCE_PENDING_FINALIZATION_COMMIT_MISMATCH")
        self._final_evidence_store.clear_pending_finalization()
        if self._final_evidence_store.load_pending_finalization() is not None:
            raise ValueError("PERFORMANCE_PENDING_FINALIZATION_CLEANUP_UNPROVEN")

    def _recover_checkpoint_preflight(
        self,
        checkpoint: Mapping[str, Any],
        *,
        digest_field: str,
        validator: Callable[[Mapping[str, Any]], dict[str, Any]],
        current: Mapping[str, str],
    ) -> dict[str, Any]:
        validated = validator(checkpoint)
        initial = validated["execution_bindings"]
        if not _stable_execution_bindings_match(initial, self._execution_bindings):
            raise ValueError("PERFORMANCE_RECOVERY_BINDING_MISMATCH")
        if not _stable_execution_bindings_match(initial, current):
            raise ValueError("PERFORMANCE_RECOVERY_BINDING_MISMATCH")
        recovered = {
            key: value for key, value in validated.items() if key != digest_field
        }
        recovered["preflight_evidence_chain"] = _append_preflight_evidence(
            validated["preflight_evidence_chain"], current
        )
        recovered[digest_field] = _sha256_json(recovered)
        return validator(recovered)

    def _complete_terminal_measurement(
        self,
        terminal: Mapping[str, Any],
        capability: VerifiedLiveActionCapability,
    ) -> Mapping[str, Any]:
        validated = _validate_terminal_measurement(terminal)
        if not _stable_execution_bindings_match(
            validated["execution_bindings"], self._execution_bindings
        ):
            raise ValueError("PERFORMANCE_TERMINAL_MEASUREMENT_BINDING_MISMATCH")
        evidence = validated["measurement_evidence"]
        measurement_outcome = evidence.get("status")
        minimum_on_demand_execution_count = (
            TOTAL_REQUEST_LIMIT
            if measurement_outcome == "PASSED"
            else evidence.get("completed_network_dispatch_count")
        )
        final_attestation = self._runtime.get_validated_final_attestation(
            evidence.get("finished_at_utc"),
            measurement_outcome=measurement_outcome,
            minimum_on_demand_execution_count=minimum_on_demand_execution_count,
            live_action_capability=capability,
        )
        pending = _build_pending_finalization(
            evidence=evidence,
            execution_bindings=validated["execution_bindings"],
            final_measurement_attestation=final_attestation,
            preflight_evidence_chain=validated["preflight_evidence_chain"],
        )
        try:
            self._final_evidence_store.write_pending_finalization(pending)
        except Exception:
            raise
        self._final_evidence_store.clear_terminal_measurement()
        return self._finalize_pending(pending, capability)

    def _finalize_pending(
        self,
        pending: Mapping[str, Any],
        capability: VerifiedLiveActionCapability,
    ) -> Mapping[str, Any]:
        validated = _validate_pending_finalization(pending)
        if not _stable_execution_bindings_match(
            validated["execution_bindings"], self._execution_bindings
        ):
            raise ValueError("PERFORMANCE_PENDING_FINALIZATION_BINDING_MISMATCH")
        initial_bindings = validated["execution_bindings"]
        release_receipt = self._runtime.release(capability)
        _validate_lease_receipt(
            release_receipt,
            expected_target_binding_sha256=initial_bindings[
                "target_binding_sha256"
            ],
            expected_lifecycle_state="RELEASED",
        )
        completion = self._runtime.completion_bindings(
            release_receipt,
            validated["final_measurement_attestation"],
        )
        evidence = validated["measurement_evidence"]
        final = {
            "schema_version": "nac.m365-bff-performance-final-evidence/v1",
            "status": evidence.get("status"),
            "measurement_evidence": dict(evidence),
            "measurement_evidence_sha256": validated[
                "measurement_evidence_sha256"
            ],
            "execution_bindings": dict(initial_bindings),
            "preflight_evidence_chain": validated["preflight_evidence_chain"],
            "completion_bindings": completion,
            "lease_release_verified": True,
            "tenant_wide_sharepoint_baseline_claim": "NOT_CLAIMED",
            "tenant_wide_sharepoint_request_allowance_claim": "NOT_CLAIMED",
            "tenant_wide_sharepoint_resource_unit_allowance_claim": (
                "NOT_CLAIMED"
            ),
            "monetary_cost_claim": "NOT_CLAIMED",
        }
        final["final_evidence_sha256"] = _sha256_json(final)
        self._final_evidence_store.write_final_evidence(final)
        self._final_evidence_store.clear_pending_finalization()
        self._final_evidence_store.clear_terminal_measurement()
        return final


class PerformanceFinalEvidenceStore:
    """Persist final evidence with a manifest committed after both artifacts."""

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or path.name in {"", ".", ".."}:
            raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID")
        self._path = Path(os.path.abspath(path.expanduser()))
        suffix = ".redacted.json"
        pending_name = (
            f"{self._path.name[:-len(suffix)]}.pending-finalization{suffix}"
            if self._path.name.endswith(suffix)
            else f"{self._path.name}.pending-finalization.redacted.json"
        )
        self._pending_path = self._path.with_name(pending_name)
        terminal_name = (
            f"{self._path.name[:-len(suffix)]}.terminal-measurement{suffix}"
            if self._path.name.endswith(suffix)
            else f"{self._path.name}.terminal-measurement.redacted.json"
        )
        self._terminal_path = self._path.with_name(terminal_name)
        markdown_name = (
            f"{self._path.name[:-len(suffix)]}.redacted.md"
            if self._path.name.endswith(suffix)
            else f"{self._path.name}.redacted.md"
        )
        self._markdown_path = self._path.with_name(markdown_name)
        manifest_name = (
            f"{self._path.name[:-len(suffix)]}.completion-manifest{suffix}"
            if self._path.name.endswith(suffix)
            else f"{self._path.name}.completion-manifest.redacted.json"
        )
        self._manifest_path = self._path.with_name(manifest_name)

    @property
    def pending_path(self) -> Path:
        return self._pending_path

    @property
    def terminal_path(self) -> Path:
        return self._terminal_path

    @property
    def markdown_path(self) -> Path:
        return self._markdown_path

    @property
    def manifest_path(self) -> Path:
        return self._manifest_path

    @property
    def incomplete_final_evidence(self) -> bool:
        directory = _open_private_parent_directory(self._path, create=False)
        if directory is None:
            return False
        try:
            return not _private_entry_exists_at(
                directory, self._manifest_path.name
            ) and any(
                _private_entry_exists_at(directory, path.name)
                for path in (self._path, self._markdown_path)
            )
        finally:
            os.close(directory)

    def load_final_evidence(self) -> Mapping[str, Any] | None:
        directory = _open_private_parent_directory(self._path, create=False)
        if directory is None:
            return None
        try:
            manifest = _read_private_json_at(
                directory,
                self._manifest_path.name,
                error_code="PERFORMANCE_FINAL_EVIDENCE_INVALID",
            )
            if manifest is None:
                return None
            validated_manifest = _validate_completion_manifest(manifest)
            json_encoded = _read_private_bytes_at(
                directory,
                self._path.name,
                error_code="PERFORMANCE_FINAL_EVIDENCE_INVALID",
            )
            markdown_encoded = _read_private_bytes_at(
                directory,
                self._markdown_path.name,
                error_code="PERFORMANCE_FINAL_EVIDENCE_INVALID",
            )
            if json_encoded is None or markdown_encoded is None:
                raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
            if (
                _sha256_bytes(json_encoded)
                != validated_manifest["final_evidence_json_sha256"]
                or _sha256_bytes(markdown_encoded)
                != validated_manifest["final_evidence_markdown_sha256"]
            ):
                raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
            final = _decode_canonical_json(
                json_encoded,
                error_code="PERFORMANCE_FINAL_EVIDENCE_INVALID",
            )
            validated = _validate_final_evidence(final)
            if (
                validated["final_evidence_sha256"]
                != validated_manifest["final_evidence_sha256"]
            ):
                raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
            try:
                rendered = _render_final_markdown(validated).encode("ascii")
            except UnicodeEncodeError:
                raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
            if markdown_encoded != rendered:
                raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
            return validated
        finally:
            os.close(directory)

    def assert_incomplete_final_evidence_recoverable(self) -> None:
        if not self.incomplete_final_evidence:
            return
        if self.load_pending_finalization() is not None:
            return
        if self.load_terminal_measurement() is not None:
            return
        raise ValueError("PERFORMANCE_INCOMPLETE_FINAL_EVIDENCE_UNRECOVERABLE")

    def load_terminal_measurement(self) -> Mapping[str, Any] | None:
        terminal = _read_private_json(
            self._terminal_path,
            error_code="PERFORMANCE_TERMINAL_MEASUREMENT_INVALID",
        )
        if terminal is None:
            return None
        return _validate_terminal_measurement(terminal)

    def write_terminal_measurement(self, terminal: Mapping[str, Any]) -> None:
        validated = _validate_terminal_measurement(terminal)
        _atomic_private_json_write(self._terminal_path, validated)

    def clear_terminal_measurement(self) -> None:
        _remove_private_file(self._terminal_path)

    def load_pending_finalization(self) -> Mapping[str, Any] | None:
        pending = _read_private_json(
            self._pending_path,
            error_code="PERFORMANCE_PENDING_FINALIZATION_INVALID",
        )
        if pending is None:
            return None
        return _validate_pending_finalization(pending)

    def write_pending_finalization(self, pending: Mapping[str, Any]) -> None:
        validated = _validate_pending_finalization(pending)
        _atomic_private_json_write(self._pending_path, validated)

    def write_final_evidence(self, evidence: Mapping[str, Any]) -> None:
        validated = _validate_final_evidence(evidence)
        json_encoded = _encode_canonical_json(validated)
        markdown = _render_final_markdown(validated)
        try:
            markdown_encoded = markdown.encode("ascii")
        except UnicodeEncodeError:
            raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
        manifest = {
            "schema_version": (
                "nac.m365-bff-performance-completion-manifest/v1"
            ),
            "final_evidence_json_sha256": _sha256_bytes(json_encoded),
            "final_evidence_markdown_sha256": _sha256_bytes(markdown_encoded),
            "final_evidence_sha256": validated["final_evidence_sha256"],
        }
        manifest["completion_manifest_sha256"] = _sha256_json(manifest)
        directory = _open_private_parent_directory(self._path, create=True)
        if directory is None:
            raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID")
        try:
            _remove_private_file_at(directory, self._manifest_path.name)
            _atomic_private_write_at(directory, self._path.name, json_encoded)
            _atomic_private_write_at(
                directory, self._markdown_path.name, markdown_encoded
            )
            _atomic_private_write_at(
                directory,
                self._manifest_path.name,
                _encode_canonical_json(_validate_completion_manifest(manifest)),
            )
        finally:
            os.close(directory)

    def clear_pending_finalization(self) -> None:
        _remove_private_file(self._pending_path)


def _build_pending_finalization(
    *,
    evidence: Mapping[str, Any],
    execution_bindings: Mapping[str, str],
    final_measurement_attestation: Mapping[str, Any],
    preflight_evidence_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    chain = (
        _initial_preflight_evidence_chain(execution_bindings)
        if preflight_evidence_chain is None
        else _validate_preflight_evidence_chain(
            preflight_evidence_chain, execution_bindings
        )
    )
    payload = {
        "schema_version": "nac.m365-bff-performance-pending-finalization/v1",
        "measurement_evidence": dict(evidence),
        "measurement_evidence_sha256": _sha256_json(evidence),
        "execution_bindings": dict(execution_bindings),
        "preflight_evidence_chain": chain,
        "final_measurement_attestation": dict(final_measurement_attestation),
        "final_measurement_summary_sha256": _sha256_json(
            final_measurement_attestation
        ),
    }
    payload["pending_finalization_sha256"] = _sha256_json(payload)
    return _validate_pending_finalization(payload)


def _build_terminal_measurement(
    *,
    evidence: Mapping[str, Any],
    execution_bindings: Mapping[str, str],
    preflight_evidence_chain: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    chain = (
        _initial_preflight_evidence_chain(execution_bindings)
        if preflight_evidence_chain is None
        else _validate_preflight_evidence_chain(
            preflight_evidence_chain, execution_bindings
        )
    )
    payload = {
        "schema_version": "nac.m365-bff-performance-terminal-measurement/v1",
        "measurement_evidence": dict(evidence),
        "measurement_evidence_sha256": _sha256_json(evidence),
        "execution_bindings": dict(execution_bindings),
        "preflight_evidence_chain": chain,
    }
    payload["terminal_measurement_sha256"] = _sha256_json(payload)
    return _validate_terminal_measurement(payload)


def _validate_terminal_measurement(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("PERFORMANCE_TERMINAL_MEASUREMENT_INVALID")
    result = dict(value)
    digest = result.pop("terminal_measurement_sha256", None)
    required = {
        "schema_version",
        "measurement_evidence",
        "measurement_evidence_sha256",
        "execution_bindings",
        "preflight_evidence_chain",
    }
    try:
        execution_bindings = _validate_execution_bindings(
            result.get("execution_bindings")
        )
        evidence = result.get("measurement_evidence")
        _validate_redacted_evidence(evidence)
        chain = _validate_preflight_evidence_chain(
            result.get("preflight_evidence_chain"), execution_bindings
        )
    except (TypeError, ValueError):
        raise ValueError("PERFORMANCE_TERMINAL_MEASUREMENT_INVALID") from None
    if (
        set(result) != required
        or result.get("schema_version")
        != "nac.m365-bff-performance-terminal-measurement/v1"
        or result.get("measurement_evidence_sha256") != _sha256_json(evidence)
        or digest != _sha256_json(result)
    ):
        raise ValueError("PERFORMANCE_TERMINAL_MEASUREMENT_INVALID")
    try:
        _validate_measurement_execution_bindings(evidence, execution_bindings)
    except ValueError:
        raise ValueError("PERFORMANCE_TERMINAL_MEASUREMENT_INVALID") from None
    return {
        **result,
        "execution_bindings": execution_bindings,
        "measurement_evidence": dict(evidence),
        "preflight_evidence_chain": chain,
        "terminal_measurement_sha256": digest,
    }


def _validate_pending_finalization(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("PERFORMANCE_PENDING_FINALIZATION_INVALID")
    result = dict(value)
    digest = result.pop("pending_finalization_sha256", None)
    required = {
        "schema_version",
        "measurement_evidence",
        "measurement_evidence_sha256",
        "execution_bindings",
        "preflight_evidence_chain",
        "final_measurement_attestation",
        "final_measurement_summary_sha256",
    }
    try:
        execution_bindings = _validate_execution_bindings(
            result.get("execution_bindings")
        )
        evidence = result.get("measurement_evidence")
        _validate_redacted_evidence(evidence)
        chain = _validate_preflight_evidence_chain(
            result.get("preflight_evidence_chain"), execution_bindings
        )
        attestation = _validate_final_measurement_attestation(
            result.get("final_measurement_attestation"),
            expected_monitor_window_anchor_sha256=execution_bindings[
                "monitor_window_anchor_sha256"
            ],
            expected_target_binding_sha256=execution_bindings[
                "target_binding_sha256"
            ],
            expected_measurement_finished_at_utc=evidence.get(
                "finished_at_utc"
            ),
            expected_measurement_outcome=evidence.get("status"),
            expected_minimum_on_demand_execution_count=(
                TOTAL_REQUEST_LIMIT
                if evidence.get("status") == "PASSED"
                else evidence.get("completed_network_dispatch_count")
            ),
        )
    except (TypeError, ValueError):
        raise ValueError("PERFORMANCE_PENDING_FINALIZATION_INVALID") from None
    if (
        set(result) != required
        or result.get("schema_version")
        != "nac.m365-bff-performance-pending-finalization/v1"
        or result.get("measurement_evidence_sha256") != _sha256_json(evidence)
        or result.get("final_measurement_summary_sha256")
        != _sha256_json(attestation)
        or digest != _sha256_json(result)
    ):
        raise ValueError("PERFORMANCE_PENDING_FINALIZATION_INVALID")
    try:
        _validate_measurement_execution_bindings(evidence, execution_bindings)
        if (
            evidence["measurement_preflight"]["lease_binding_sha256"]
            != attestation["lease_binding_sha256"]
        ):
            raise ValueError
    except (KeyError, TypeError, ValueError):
        raise ValueError("PERFORMANCE_PENDING_FINALIZATION_INVALID") from None
    return {
        **result,
        "execution_bindings": execution_bindings,
        "measurement_evidence": dict(evidence),
        "preflight_evidence_chain": chain,
        "final_measurement_attestation": attestation,
        "pending_finalization_sha256": digest,
    }


def _validate_final_measurement_attestation(
    value: Mapping[str, Any],
    *,
    expected_monitor_window_anchor_sha256: str,
    expected_target_binding_sha256: str,
    expected_measurement_finished_at_utc: str | None = None,
    expected_measurement_outcome: str | None = None,
    expected_minimum_on_demand_execution_count: int | None = None,
) -> dict[str, Any]:
    required = {
        "status",
        "measurement_mode",
        "tenant_wide_sharepoint_capacity_claim",
        "maximum_dispatches_per_minute",
        "planned_dispatch_count",
        "endpoint_request_budget_fraction_used",
        "tenant_resource_unit_capacity_claim",
        "always_ready_units",
        "on_demand_execution_count",
        "minimum_on_demand_execution_count",
        "azure_execution_units_gb_seconds",
        "projected_execution_units_gb_seconds",
        "execution_units_below_cap",
        "telemetry_cap_reached",
        "measurement_policy_sha256",
        "monitor_binding_sha256",
        "monitor_evidence_sha256",
        "monitor_window_anchor_sha256",
        "lease_binding_sha256",
        "measurement_attestation_sha256",
        "target_binding_sha256",
        "measurement_finished_at_utc",
        "monitor_window_start_utc",
        "monitor_window_end_utc",
        "monitor_observed_at_utc",
        "monitor_settlement_delay_seconds",
    }
    if not isinstance(value, Mapping):
        raise ValueError("PERFORMANCE_FINAL_MEASUREMENT_ATTESTATION_INVALID")
    result = dict(value)
    digest = result.pop("attestation_sha256", None)
    numeric = (
        result.get("azure_execution_units_gb_seconds"),
        result.get("projected_execution_units_gb_seconds"),
    )
    try:
        finished_at = _parse_timestamp(
            result.get("measurement_finished_at_utc")
        )
        window_start = _parse_timestamp(result.get("monitor_window_start_utc"))
        window_end = _parse_timestamp(result.get("monitor_window_end_utc"))
        observed_at = _parse_timestamp(result.get("monitor_observed_at_utc"))
    except (TypeError, ValueError):
        raise ValueError("PERFORMANCE_FINAL_MEASUREMENT_ATTESTATION_INVALID") from None
    settlement_seconds = (observed_at - window_end).total_seconds()
    if (
        set(result) != required
        or result.get("status") not in {"PASSED", "FAILED"}
        or (
            expected_measurement_outcome is not None
            and result.get("status") != expected_measurement_outcome
        )
        or result.get("measurement_mode") != MEASUREMENT_MODE
        or result.get("tenant_wide_sharepoint_capacity_claim")
        != TENANT_WIDE_SHAREPOINT_CAPACITY_CLAIM
        or result.get("tenant_resource_unit_capacity_claim")
        != TENANT_WIDE_SHAREPOINT_CAPACITY_CLAIM
        or result.get("maximum_dispatches_per_minute")
        != MAXIMUM_DISPATCHES_PER_MINUTE
        or result.get("planned_dispatch_count") != TOTAL_REQUEST_LIMIT
        or result.get("endpoint_request_budget_fraction_used") != 1.0
        or result.get("projected_execution_units_gb_seconds") != 0.0
        or result.get("always_ready_units") != 0
        or type(result.get("on_demand_execution_count")) is not int
        or type(result.get("minimum_on_demand_execution_count")) is not int
        or result.get("minimum_on_demand_execution_count") < 0
        or result.get("minimum_on_demand_execution_count") > TOTAL_REQUEST_LIMIT
        or (
            result.get("status") == "PASSED"
            and result.get("minimum_on_demand_execution_count")
            != TOTAL_REQUEST_LIMIT
        )
        or result.get("on_demand_execution_count")
        < result.get("minimum_on_demand_execution_count")
        or (
            expected_minimum_on_demand_execution_count is not None
            and result.get("minimum_on_demand_execution_count")
            != expected_minimum_on_demand_execution_count
        )
        or result.get("execution_units_below_cap") is not True
        or result.get("telemetry_cap_reached") is not False
        or result.get("measurement_policy_sha256") != measurement_policy_sha256()
        or result.get("monitor_window_anchor_sha256")
        != expected_monitor_window_anchor_sha256
        or result.get("target_binding_sha256")
        != expected_target_binding_sha256
        or (
            expected_measurement_finished_at_utc is not None
            and result.get("measurement_finished_at_utc")
            != expected_measurement_finished_at_utc
        )
        or _sha256_text(result["monitor_window_start_utc"])
        != expected_monitor_window_anchor_sha256
        or window_start.second != 0
        or window_start.microsecond != 0
        or window_end.second != 0
        or window_end.microsecond != 0
        or not window_start < window_end
        or window_end < finished_at
        or settlement_seconds < INGESTION_LAG_SECONDS
        or type(result.get("monitor_settlement_delay_seconds")) is not int
        or result.get("monitor_settlement_delay_seconds")
        != int(settlement_seconds)
        or digest != _sha256_json(result)
        or any(
            not _is_sha256(result.get(key))
            for key in required
            if key.endswith("sha256")
        )
        or any(
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not 0 <= float(item) <= _MAX_EXECUTION_UNITS_GB_SECONDS
            for item in numeric
        )
        or sum(float(item) for item in numeric)
        > _MAX_EXECUTION_UNITS_GB_SECONDS
    ):
        raise ValueError("PERFORMANCE_FINAL_MEASUREMENT_ATTESTATION_INVALID")
    return {**result, "attestation_sha256": digest}


def _validate_completion_bindings(
    value: Mapping[str, Any],
    *,
    execution_bindings: Mapping[str, str],
    measurement_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "lease_binding_sha256",
        "target_binding_sha256",
        "lease_release_lifecycle_state",
        "lease_release_lifecycle_state_sha256",
        "lease_release_state_evidence_sha256",
        "monitor_binding_sha256",
        "monitor_evidence_sha256",
        "monitor_window_anchor_sha256",
        "final_measurement_attestation_sha256",
        "final_measurement_attestation",
        "final_measurement_summary_sha256",
        "final_observed_execution_units_gb_seconds",
        "final_projected_execution_units_gb_seconds",
        "final_execution_units_below_cap",
        "final_telemetry_cap_reached",
    }
    if not isinstance(value, Mapping):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    result = dict(value)
    measurement_outcome = measurement_evidence.get("status")
    minimum_on_demand_execution_count = (
        TOTAL_REQUEST_LIMIT
        if measurement_outcome == "PASSED"
        else measurement_evidence.get("completed_network_dispatch_count")
    )
    try:
        attestation = _validate_final_measurement_attestation(
            result.get("final_measurement_attestation"),
            expected_monitor_window_anchor_sha256=execution_bindings[
                "monitor_window_anchor_sha256"
            ],
            expected_target_binding_sha256=execution_bindings[
                "target_binding_sha256"
            ],
            expected_measurement_finished_at_utc=measurement_evidence.get(
                "finished_at_utc"
            ),
            expected_measurement_outcome=measurement_outcome,
            expected_minimum_on_demand_execution_count=(
                minimum_on_demand_execution_count
            ),
        )
    except (TypeError, ValueError):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
    numeric = (
        result.get("final_observed_execution_units_gb_seconds"),
        result.get("final_projected_execution_units_gb_seconds"),
    )
    if (
        set(result) != required
        or result.get("monitor_window_anchor_sha256")
        != execution_bindings["monitor_window_anchor_sha256"]
        or result.get("target_binding_sha256")
        != execution_bindings["target_binding_sha256"]
        or result.get("target_binding_sha256")
        != attestation["target_binding_sha256"]
        or result.get("lease_release_lifecycle_state") != "RELEASED"
        or result.get("lease_release_lifecycle_state_sha256")
        != _sha256_text("RELEASED")
        or result.get("final_execution_units_below_cap") is not True
        or result.get("final_telemetry_cap_reached") is not False
        or result.get("lease_binding_sha256")
        != attestation["lease_binding_sha256"]
        or result.get("monitor_binding_sha256")
        != attestation["monitor_binding_sha256"]
        or result.get("monitor_evidence_sha256")
        != attestation["monitor_evidence_sha256"]
        or result.get("final_measurement_attestation_sha256")
        != attestation["attestation_sha256"]
        or result.get("final_measurement_summary_sha256")
        != _sha256_json(attestation)
        or result.get("final_observed_execution_units_gb_seconds")
        != attestation["azure_execution_units_gb_seconds"]
        or result.get("final_projected_execution_units_gb_seconds")
        != attestation["projected_execution_units_gb_seconds"]
        or result.get("final_execution_units_below_cap")
        != attestation["execution_units_below_cap"]
        or result.get("final_telemetry_cap_reached")
        != attestation["telemetry_cap_reached"]
        or any(
            not _is_sha256(result.get(key))
            for key in required
            if key.endswith("sha256")
        )
        or any(
            not isinstance(item, (int, float))
            or isinstance(item, bool)
            or not 0 <= float(item) <= _MAX_EXECUTION_UNITS_GB_SECONDS
            for item in numeric
        )
        or sum(float(item) for item in numeric)
        > _MAX_EXECUTION_UNITS_GB_SECONDS
    ):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    return result


def _validate_final_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(evidence, Mapping):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    result = dict(evidence)
    digest = result.pop("final_evidence_sha256", None)
    required = {
        "schema_version",
        "status",
        "measurement_evidence",
        "measurement_evidence_sha256",
        "execution_bindings",
        "preflight_evidence_chain",
        "completion_bindings",
        "lease_release_verified",
        "tenant_wide_sharepoint_baseline_claim",
        "tenant_wide_sharepoint_request_allowance_claim",
        "tenant_wide_sharepoint_resource_unit_allowance_claim",
        "monetary_cost_claim",
    }
    try:
        nested = result.get("measurement_evidence")
        _validate_redacted_evidence(nested)
        execution_bindings = _validate_execution_bindings(
            result.get("execution_bindings")
        )
        chain = _validate_preflight_evidence_chain(
            result.get("preflight_evidence_chain"), execution_bindings
        )
        completion = _validate_completion_bindings(
            result.get("completion_bindings"),
            execution_bindings=execution_bindings,
            measurement_evidence=nested,
        )
    except (TypeError, ValueError):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
    if (
        set(result) != required
        or result.get("schema_version")
        != "nac.m365-bff-performance-final-evidence/v1"
        or result.get("status") not in {"PASSED", "FAILED"}
        or result.get("status") != nested.get("status")
        or result.get("lease_release_verified") is not True
        or result.get("tenant_wide_sharepoint_baseline_claim") != "NOT_CLAIMED"
        or result.get("tenant_wide_sharepoint_request_allowance_claim")
        != "NOT_CLAIMED"
        or result.get("tenant_wide_sharepoint_resource_unit_allowance_claim")
        != "NOT_CLAIMED"
        or result.get("monetary_cost_claim") != "NOT_CLAIMED"
        or result.get("measurement_evidence_sha256") != _sha256_json(nested)
        or digest != _sha256_json(result)
        or completion["lease_binding_sha256"]
        != nested.get("measurement_preflight", {}).get("lease_binding_sha256")
        or completion["target_binding_sha256"]
        != execution_bindings["target_binding_sha256"]
    ):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    try:
        _validate_measurement_execution_bindings(nested, execution_bindings)
    except ValueError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
    return {
        **result,
        "preflight_evidence_chain": chain,
        "final_evidence_sha256": digest,
    }


def _validate_completion_manifest(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    result = dict(value)
    digest = result.pop("completion_manifest_sha256", None)
    required = {
        "schema_version",
        "final_evidence_json_sha256",
        "final_evidence_markdown_sha256",
        "final_evidence_sha256",
    }
    if (
        set(result) != required
        or result.get("schema_version")
        != "nac.m365-bff-performance-completion-manifest/v1"
        or digest != _sha256_json(result)
        or not _is_sha256(digest)
        or any(
            not _is_sha256(result.get(key))
            for key in required
            if key.endswith("sha256")
        )
    ):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    return {**result, "completion_manifest_sha256": digest}


def _read_private_json(
    path: Path,
    *,
    error_code: str = "PERFORMANCE_PENDING_FINALIZATION_INVALID",
) -> dict[str, Any] | None:
    encoded = _read_private_bytes(path, error_code=error_code)
    if encoded is None:
        return None
    return _decode_canonical_json(encoded, error_code=error_code)


def _read_private_json_at(
    directory: int,
    name: str,
    *,
    error_code: str,
) -> dict[str, Any] | None:
    encoded = _read_private_bytes_at(directory, name, error_code=error_code)
    if encoded is None:
        return None
    return _decode_canonical_json(encoded, error_code=error_code)


def _read_private_bytes(path: Path, *, error_code: str) -> bytes | None:
    directory = _open_private_parent_directory(path, create=False)
    if directory is None:
        return None
    try:
        return _read_private_bytes_at(directory, path.name, error_code=error_code)
    finally:
        os.close(directory)


def _read_private_bytes_at(
    directory: int,
    name: str,
    *,
    error_code: str,
) -> bytes | None:
    try:
        descriptor = os.open(
            name,
            os.O_RDONLY
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0),
            dir_fd=directory,
        )
    except FileNotFoundError:
        return None
    except OSError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID") from None
    try:
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_size > _MAX_EVIDENCE_BYTES
        ):
            raise ValueError
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            return stream.read()
    except (OSError, ValueError):
        raise ValueError(error_code) from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _decode_canonical_json(encoded: bytes, *, error_code: str) -> dict[str, Any]:
    try:
        raw = encoded.decode("ascii")
        value = json.loads(raw)
        if not isinstance(value, dict) or encoded != _encode_canonical_json(value):
            raise ValueError
        return value
    except (UnicodeError, ValueError, json.JSONDecodeError):
        raise ValueError(error_code) from None


def _encode_canonical_json(value: Mapping[str, Any]) -> bytes:
    try:
        encoded = (_canonical_json(dict(value)) + "\n").encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError):
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
    if len(encoded) > _MAX_EVIDENCE_BYTES:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    return encoded


def _atomic_private_json_write(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_private_write(path, _encode_canonical_json(value))


def _atomic_private_text_write(path: Path, value: str) -> None:
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID") from None
    if len(encoded) > _MAX_EVIDENCE_BYTES:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_INVALID")
    _atomic_private_write(path, encoded)


def _atomic_private_write(path: Path, encoded: bytes) -> None:
    directory = _open_private_parent_directory(path, create=True)
    if directory is None:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID")
    try:
        _atomic_private_write_at(directory, path.name, encoded)
    finally:
        os.close(directory)


def _atomic_private_write_at(directory: int, name: str, encoded: bytes) -> None:
    temporary = f".{name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    descriptor = -1
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=directory,
        )
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or metadata.st_nlink != 1
        ):
            raise OSError
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(
            temporary,
            name,
            src_dir_fd=directory,
            dst_dir_fd=directory,
        )
        os.fsync(directory)
    except OSError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=directory)
        except FileNotFoundError:
            pass
        except OSError:
            raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID") from None


def _remove_private_file(path: Path) -> None:
    directory = _open_private_parent_directory(path, create=False)
    if directory is None:
        return
    try:
        _remove_private_file_at(directory, path.name)
    finally:
        os.close(directory)


def _remove_private_file_at(directory: int, name: str) -> None:
    try:
        os.unlink(name, dir_fd=directory)
        os.fsync(directory)
    except FileNotFoundError:
        return
    except OSError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID") from None


def _private_entry_exists_at(directory: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID") from None


def _render_final_markdown(evidence: Mapping[str, Any]) -> str:
    validated = _validate_final_evidence(evidence)
    measurement = validated["measurement_evidence"]
    completion = validated["completion_bindings"]
    lines = [
        "# M365 BFF Performance Acceptance Evidence",
        "",
        f"- Status: `{validated['status']}`",
        "- Measurement mode: `endpoint_scoped_conservative_measurement`",
        "- Tenant-wide SharePoint baseline: `NOT_CLAIMED`",
        "- Tenant-wide SharePoint request allowance: `NOT_CLAIMED`",
        "- Tenant-wide SharePoint resource-unit allowance: `NOT_CLAIMED`",
        "- Monetary cost: `NOT_CLAIMED`",
        f"- Target dispatches: `{measurement['global_dispatch_count']}`",
        (
            "- Completed network dispatches: "
            f"`{measurement['completed_network_dispatch_count']}`"
        ),
        f"- Lease released: `{str(validated['lease_release_verified']).lower()}`",
        f"- Lease lifecycle state: `{completion['lease_release_lifecycle_state']}`",
        f"- Final evidence SHA-256: `{validated['final_evidence_sha256']}`",
        f"- Monitor evidence SHA-256: `{completion['monitor_evidence_sha256']}`",
        "- Monitor window anchor SHA-256: "
        f"`{completion['monitor_window_anchor_sha256']}`",
        f"- Lease binding SHA-256: `{completion['lease_binding_sha256']}`",
        f"- Target binding SHA-256: `{completion['target_binding_sha256']}`",
        (
            "- Verified preflight evidence count: "
            f"`{len(validated['preflight_evidence_chain'])}`"
        ),
        "",
        "This artifact contains redacted aggregate evidence only.",
        "",
    ]
    return "\n".join(lines)


def _open_private_parent_directory(path: Path, *, create: bool) -> int | None:
    try:
        return _open_root_anchored_private_parent(path, create=create)
    except SecurePerformancePathError:
        raise ValueError("PERFORMANCE_FINAL_EVIDENCE_PATH_INVALID") from None


def _exact_int(value: object) -> int:
    try:
        converted = int(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("PERFORMANCE_RUNTIME_OBSERVATION_INVALID") from None
    if value != converted:
        raise ValueError("PERFORMANCE_RUNTIME_OBSERVATION_INVALID")
    return converted


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("PERFORMANCE_TIMESTAMP_INVALID")
    try:
        parsed = datetime.fromisoformat(f"{value[:-1]}+00:00")
    except ValueError:
        raise ValueError("PERFORMANCE_TIMESTAMP_INVALID") from None
    if parsed.tzinfo is None or _timestamp(parsed) != value:
        raise ValueError("PERFORMANCE_TIMESTAMP_INVALID")
    return parsed.astimezone(UTC)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: object) -> str:
    return _sha256_text(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _validate_execution_bindings(value: Mapping[str, str]) -> dict[str, str]:
    required = _owner_execution_binding_keys() | {
        "infrastructure_safety_evidence_sha256",
        "lease_acquisition_safety_evidence_sha256",
        "lease_binding_sha256",
    }
    result = _validate_digest_bindings(value, required)
    _validate_approved_plan_bindings(result)
    return result


def _validate_owner_preflight_bindings(
    value: Mapping[str, str],
) -> dict[str, str]:
    required = _owner_execution_binding_keys() | {
        "infrastructure_safety_evidence_sha256"
    }
    result = _validate_digest_bindings(value, required)
    _validate_approved_plan_bindings(result)
    return result


def _validate_owner_execution_bindings(
    value: Mapping[str, str],
) -> dict[str, str]:
    result = _validate_digest_bindings(value, _owner_execution_binding_keys())
    _validate_approved_plan_bindings(result)
    return result


def _owner_execution_binding_keys() -> set[str]:
    return {
        "approved_commit_sha",
        "approved_tree_sha",
        "toolchain_attestations_sha256",
        "contract_sha256",
        "expected_activation_hash",
        "phase_plan_sha256",
        "measurement_policy_sha256",
        "monitor_policy_sha256",
        "lease_policy_sha256",
        "infrastructure_binding_sha256",
        "infrastructure_parameters_sha256",
        "infrastructure_source_sha256",
        "lease_bootstrap_policy_sha256",
        "infrastructure_safety_policy_sha256",
        "worm_baseline_binding_sha256",
        "worm_baseline_compiled_arm_sha256",
        "worm_baseline_parameters_sha256",
        "worm_baseline_source_sha256",
        "deployment_sequence_sha256",
        "owner_approval_body_sha256",
        "monitor_window_anchor_sha256",
        "target_binding_sha256",
    }


def _stable_execution_bindings(value: Mapping[str, str]) -> dict[str, str]:
    validated = _validate_execution_bindings(value)
    return {
        key: validated[key]
        for key in sorted(_owner_execution_binding_keys() | {"lease_binding_sha256"})
    }


def _stable_execution_bindings_match(
    left: Mapping[str, str], right: Mapping[str, str]
) -> bool:
    try:
        return _stable_execution_bindings(left) == _stable_execution_bindings(right)
    except (TypeError, ValueError):
        return False


def _initial_preflight_evidence_chain(
    execution_bindings: Mapping[str, str],
) -> list[dict[str, Any]]:
    validated = _validate_execution_bindings(execution_bindings)
    return [
        _build_preflight_evidence_entry(
            sequence=0,
            reason="INITIAL",
            previous_sha256=_ZERO_SHA256,
            execution_bindings=validated,
        )
    ]


def _append_preflight_evidence(
    chain: Sequence[Mapping[str, Any]],
    current_execution_bindings: Mapping[str, str],
) -> list[dict[str, Any]]:
    current = _validate_execution_bindings(current_execution_bindings)
    validated = _validate_preflight_evidence_chain(chain, current, stable_only=True)
    return [
        *validated,
        _build_preflight_evidence_entry(
            sequence=len(validated),
            reason="RECOVERY",
            previous_sha256=validated[-1]["preflight_evidence_sha256"],
            execution_bindings=current,
        ),
    ]


def _build_preflight_evidence_entry(
    *,
    sequence: int,
    reason: str,
    previous_sha256: str,
    execution_bindings: Mapping[str, str],
) -> dict[str, Any]:
    payload = {
        "schema_version": _PREFLIGHT_CHAIN_SCHEMA,
        "sequence": sequence,
        "reason": reason,
        "stable_execution_bindings_sha256": _sha256_json(
            _stable_execution_bindings(execution_bindings)
        ),
        "infrastructure_safety_evidence_sha256": execution_bindings[
            "infrastructure_safety_evidence_sha256"
        ],
        "lease_acquisition_safety_evidence_sha256": execution_bindings[
            "lease_acquisition_safety_evidence_sha256"
        ],
        "previous_preflight_evidence_sha256": previous_sha256,
    }
    payload["preflight_evidence_sha256"] = _sha256_json(payload)
    return payload


def _validate_preflight_evidence_chain(
    value: Sequence[Mapping[str, Any]],
    execution_bindings: Mapping[str, str],
    *,
    stable_only: bool = False,
) -> list[dict[str, Any]]:
    if (
        not isinstance(value, list)
        or not value
        or len(value) > 64
    ):
        raise ValueError("PERFORMANCE_PREFLIGHT_EVIDENCE_CHAIN_INVALID")
    bindings = _validate_execution_bindings(execution_bindings)
    stable_sha256 = _sha256_json(_stable_execution_bindings(bindings))
    required = {
        "schema_version",
        "sequence",
        "reason",
        "stable_execution_bindings_sha256",
        "infrastructure_safety_evidence_sha256",
        "lease_acquisition_safety_evidence_sha256",
        "previous_preflight_evidence_sha256",
        "preflight_evidence_sha256",
    }
    previous = _ZERO_SHA256
    result: list[dict[str, Any]] = []
    for sequence, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) != required:
            raise ValueError("PERFORMANCE_PREFLIGHT_EVIDENCE_CHAIN_INVALID")
        entry = dict(item)
        digest = entry.pop("preflight_evidence_sha256", None)
        if (
            entry.get("schema_version") != _PREFLIGHT_CHAIN_SCHEMA
            or entry.get("sequence") != sequence
            or entry.get("reason") != ("INITIAL" if sequence == 0 else "RECOVERY")
            or entry.get("stable_execution_bindings_sha256") != stable_sha256
            or entry.get("previous_preflight_evidence_sha256") != previous
            or any(
                not _is_sha256(entry.get(key))
                for key in (
                    "infrastructure_safety_evidence_sha256",
                    "lease_acquisition_safety_evidence_sha256",
                    "previous_preflight_evidence_sha256",
                )
            )
            or digest != _sha256_json(entry)
        ):
            raise ValueError("PERFORMANCE_PREFLIGHT_EVIDENCE_CHAIN_INVALID")
        if sequence == 0 and not stable_only and (
            entry["infrastructure_safety_evidence_sha256"]
            != bindings["infrastructure_safety_evidence_sha256"]
            or entry["lease_acquisition_safety_evidence_sha256"]
            != bindings["lease_acquisition_safety_evidence_sha256"]
        ):
            raise ValueError("PERFORMANCE_PREFLIGHT_EVIDENCE_CHAIN_INVALID")
        validated_entry = {**entry, "preflight_evidence_sha256": digest}
        result.append(validated_entry)
        previous = digest
    return result


def _validate_measurement_execution_bindings(
    evidence: Mapping[str, Any], execution_bindings: Mapping[str, str]
) -> None:
    capacity = evidence.get("measurement_preflight")
    if not isinstance(capacity, Mapping):
        raise ValueError("PERFORMANCE_EXECUTION_BINDINGS_INVALID")
    plan = _validate_approved_plan_bindings(execution_bindings)
    if (
        evidence.get("plan_sha256") != plan["plan_sha256"]
        or evidence.get("contract_sha256")
        != execution_bindings["contract_sha256"]
        or evidence.get("activation_hash")
        != execution_bindings["expected_activation_hash"]
        or evidence.get("phase_plan_sha256")
        != execution_bindings["phase_plan_sha256"]
        or evidence.get("owner_approval_body_sha256")
        != execution_bindings["owner_approval_body_sha256"]
        or evidence.get("target_binding_sha256")
        != execution_bindings["target_binding_sha256"]
        or capacity.get("measurement_policy_sha256")
        != execution_bindings["measurement_policy_sha256"]
        or capacity.get("monitor_window_anchor_sha256")
        != execution_bindings["monitor_window_anchor_sha256"]
        or capacity.get("lease_binding_sha256")
        != execution_bindings["lease_binding_sha256"]
    ):
        raise ValueError("PERFORMANCE_EXECUTION_BINDINGS_INVALID")


def _validate_approved_plan_bindings(
    execution_bindings: Mapping[str, str],
) -> dict[str, Any]:
    plan = build_performance_acceptance_plan(
        execution_bindings["expected_activation_hash"],
        execution_bindings["contract_sha256"],
    )
    infrastructure_binding_sha256 = _sha256_json(
        {
            "infrastructure_parameters_sha256": execution_bindings[
                "infrastructure_parameters_sha256"
            ],
            "infrastructure_source_sha256": execution_bindings[
                "infrastructure_source_sha256"
            ],
            "lease_bootstrap_policy_sha256": execution_bindings[
                "lease_bootstrap_policy_sha256"
            ],
            "infrastructure_safety_policy_sha256": execution_bindings[
                "infrastructure_safety_policy_sha256"
            ],
        }
    )
    if (
        execution_bindings["infrastructure_binding_sha256"]
        != infrastructure_binding_sha256
        or any(
            execution_bindings[key] != plan[key]
            for key in (
                "target_binding_sha256",
                "phase_plan_sha256",
                "measurement_policy_sha256",
                "monitor_policy_sha256",
                "lease_policy_sha256",
            )
        )
    ):
        raise ValueError("PERFORMANCE_EXECUTION_BINDINGS_INVALID")
    return plan


def _validate_digest_bindings(
    value: Mapping[str, str], required: set[str]
) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError("PERFORMANCE_EXECUTION_BINDINGS_INVALID")
    result = dict(value)
    for key, item in result.items():
        valid = (
            isinstance(item, str)
            and (
                len(item) == 40
                if key in {"approved_commit_sha", "approved_tree_sha"}
                else _is_sha256(item)
            )
            and all(character in "0123456789abcdef" for character in item)
        )
        if not valid:
            raise ValueError("PERFORMANCE_EXECUTION_BINDINGS_INVALID")
    return {key: result[key] for key in sorted(result)}


def _validate_lease_receipt(
    receipt: AzureBlobLeaseReceipt,
    *,
    expected_target_binding_sha256: str,
    expected_lifecycle_state: str,
) -> None:
    if (
        not isinstance(receipt, AzureBlobLeaseReceipt)
        or receipt.target_binding_sha256 != expected_target_binding_sha256
        or receipt.lifecycle_state != expected_lifecycle_state
    ):
        raise ValueError("PERFORMANCE_LEASE_RECEIPT_BINDING_INVALID")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
