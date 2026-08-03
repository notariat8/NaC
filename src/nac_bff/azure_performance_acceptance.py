from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import threading
import time
from typing import Any, Callable, Mapping, Protocol, Sequence
import urllib.error
import urllib.parse
import urllib.request

from nac_m365_graph.mvp_test_environment_deploy import M365CliCommandRunner

from .azure_activation import (
    API_APP_URI,
    FUNCTION_APP,
    MATTER_ID,
    WORKSPACE_ID,
    build_azure_bff_activation_plan,
)
from . import azure_activation_runner as activation_runner
from .test_environment import ALLOWED_MATTER_ID, ALLOWED_PURPOSE
from .workbench_projection import (
    WorkbenchProjectionError,
    validate_workbench_projection,
)


PLAN_SCHEMA_VERSION = "nac.m365-azure-bff-performance-acceptance-plan/v1"
STATE_SCHEMA_VERSION = "nac.m365-azure-bff-performance-acceptance-state/v1"
EVIDENCE_SCHEMA_VERSION = "nac.m365-azure-bff-performance-acceptance-evidence/v1"
CONTRACT_ID = "m365.bff_performance_acceptance"
PLAN_COMMAND = "nac m365 teams-sharepoint bff-performance-acceptance-plan"
LIVE_COMMAND = "nac m365 teams-sharepoint bff-performance-acceptance"
OWNER_ACTION = "EXECUTE_M365_BFF_PERFORMANCE_ACCEPTANCE"
REQUIRED_OWNER_LOGIN = "ofunk"
OUTPUT_ROOT = Path("out/m365/teams-sharepoint/bff-performance-acceptance")
CONTRACT_RELATIVE_PATH = Path(
    "workflows/contracts/m365-bff-performance-acceptance.contract.json"
)

_FUNCTION_HOST = f"{FUNCTION_APP}.azurewebsites.net"
_ENDPOINT = (
    f"https://{_FUNCTION_HOST}/v1/workspaces/{WORKSPACE_ID}/matters/"
    f"{ALLOWED_MATTER_ID}/workbench-snapshot?purpose={ALLOWED_PURPOSE}"
)
_MAX_RESPONSE_BYTES = 128 * 1024
_INSTANCE_EPOCH_HEADER = "x-nac-instance-epoch"
_EXPECTED_TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
_GLOBAL_REQUEST_LIMIT = 50_000
_MIN_TENANT_RU_PER_MINUTE = 1_250
_PROJECTED_RU_PER_REQUEST = 6
_MAX_CAPACITY_FRACTION = 0.5
_MAX_EXECUTION_UNITS_GB_SECONDS = 120_000.0
_CONNECT_TIMEOUT_SECONDS = 10.0
_REQUEST_TIMEOUT_SECONDS = 30.0
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_JWT_RE = re.compile(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")
_ERROR_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_OWNER_COMMENT_RE = re.compile(
    r"^https://github\.com/notariat8/NaC/issues/731#issuecomment-[1-9][0-9]*$"
)
_SAFE_HEADERS = {
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
}


@dataclass(frozen=True, slots=True)
class PhaseSpec:
    phase_id: str
    mode: str
    request_limit: int
    concurrency: int
    interval_seconds: float
    batch_size: int
    duration_seconds: float
    idle_before_seconds: float
    max_error_rate: float
    max_p95_ms: int
    max_p99_ms: int
    max_latency_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.phase_id,
            "mode": self.mode,
            "request_limit": self.request_limit,
            "concurrency": self.concurrency,
            "interval_seconds": self.interval_seconds,
            "batch_size": self.batch_size,
            "duration_seconds": self.duration_seconds,
            "idle_before_seconds": self.idle_before_seconds,
            "thresholds": {
                "max_error_rate": self.max_error_rate,
                "max_p95_ms": self.max_p95_ms,
                "max_p99_ms": self.max_p99_ms,
                "max_latency_ms": self.max_latency_ms,
            },
        }


PHASES = (
    PhaseSpec(
        "cold_epoch_baseline",
        "paced",
        1,
        1,
        1.0,
        1,
        1.0,
        0.0,
        0.0,
        20_000,
        20_000,
        20_000,
    ),
    PhaseSpec(
        "cold_epoch_candidate",
        "paced",
        1,
        1,
        1.0,
        1,
        1.0,
        1200.0,
        0.0,
        20_000,
        20_000,
        20_000,
    ),
    PhaseSpec(
        "capacity_bounded_volume",
        "paced",
        37_758,
        1,
        1.0,
        1,
        43_200.0,
        0.0,
        0.0,
        2000,
        5000,
        20_000,
    ),
    PhaseSpec(
        "sustained_2h",
        "paced",
        10_800,
        1,
        2.0 / 3.0,
        1,
        7200.0,
        0.0,
        0.0,
        2000,
        5000,
        20_000,
    ),
    PhaseSpec(
        "soak_24h",
        "paced",
        1440,
        1,
        60.0,
        1,
        86_400.0,
        0.0,
        0.0,
        1500,
        3000,
        20_000,
    ),
)
TOTAL_REQUEST_LIMIT = sum(phase.request_limit for phase in PHASES)
if TOTAL_REQUEST_LIMIT != _GLOBAL_REQUEST_LIMIT:  # pragma: no cover
    raise RuntimeError("BFF performance request allocation is invalid")


@dataclass(frozen=True, slots=True)
class PerformanceSample:
    status_code: int
    latency_ms: int
    valid_response: bool
    error_code: str | None = None
    fatal: bool = False
    instance_epoch_sha256: str | None = None


class PerformanceTransport(Protocol):
    @property
    def target_binding_sha256(self) -> str: ...

    def request(self) -> PerformanceSample: ...


class _PerformancePreDispatchAbort(ValueError):
    pass


class PerformanceSafetyMonitor(Protocol):
    def observe(
        self,
        dispatch_attempt_count: int,
        capacity_attestation_sha256: str,
    ) -> "RuntimeSafetyObservation": ...


class DurablePerformanceCheckpoint(Protocol):
    def load_state(self) -> dict[str, Any] | None: ...

    def write_state(self, state: Mapping[str, Any]) -> None: ...

    def state_sha256(self) -> str | None: ...


class CapacityAttestationProvider(Protocol):
    def get_attestation(self) -> "CapacityAttestation": ...


class TransportBindingVerifier(Protocol):
    def verify(self, transport: PerformanceTransport, expected_sha256: str) -> None: ...


class FixedTransportBindingVerifier:
    def verify(self, transport: PerformanceTransport, expected_sha256: str) -> None:
        if (
            type(transport) is not FixedBffPerformanceTransport
            or transport.target_binding_sha256 != expected_sha256
        ):
            raise ValueError("PERFORMANCE_TARGET_BINDING_MISMATCH")


@dataclass(frozen=True, slots=True)
class CapacityAttestation:
    sharepoint_tier_id: str
    request_allowance_window_seconds: int
    request_allowance_count: int
    resource_unit_allowance_window_seconds: int
    resource_unit_allowance_count: int
    baseline_request_count: int
    baseline_resource_units: int
    projected_request_count: int
    projected_resource_units: int
    always_ready_units: int
    projected_execution_units_gb_seconds: float
    observed_execution_units_gb_seconds: float
    telemetry_cap_reached: bool
    source_evidence_sha256: str
    monitor_evidence_sha256: str
    lease_evidence_sha256: str
    observed_at_utc: str
    tenant_binding_sha256: str
    workspace_binding_sha256: str

    def validate(self, *, now: datetime | None = None) -> dict[str, Any]:
        integer_values = (
            self.request_allowance_window_seconds,
            self.request_allowance_count,
            self.resource_unit_allowance_window_seconds,
            self.resource_unit_allowance_count,
            self.baseline_request_count,
            self.baseline_resource_units,
            self.projected_request_count,
            self.projected_resource_units,
            self.always_ready_units,
        )
        if any(type(value) is not int or value < 0 for value in integer_values):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
        if (
            not isinstance(self.sharepoint_tier_id, str)
            or re.fullmatch(r"[A-Z0-9_.-]{3,80}", self.sharepoint_tier_id) is None
        ):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
        _require_sha256(self.source_evidence_sha256, "source_evidence_sha256")
        _require_sha256(self.monitor_evidence_sha256, "monitor_evidence_sha256")
        _require_sha256(self.lease_evidence_sha256, "lease_evidence_sha256")
        observed = _parse_timestamp(self.observed_at_utc)
        current = now or datetime.now(UTC)
        age_seconds = (current.astimezone(UTC) - observed).total_seconds()
        request_fraction = (
            self.baseline_request_count + self.projected_request_count
        ) / max(1, self.request_allowance_count)
        resource_unit_fraction = (
            self.baseline_resource_units + self.projected_resource_units
        ) / max(1, self.resource_unit_allowance_count)
        projected_execution = float(self.projected_execution_units_gb_seconds)
        observed_execution = float(self.observed_execution_units_gb_seconds)
        valid = (
            self.request_allowance_window_seconds == 60
            and self.resource_unit_allowance_window_seconds == 60
            and self.request_allowance_count >= 200
            and self.resource_unit_allowance_count >= _MIN_TENANT_RU_PER_MINUTE
            and self.projected_request_count == 100
            and self.projected_resource_units >= (
                self.projected_request_count * _PROJECTED_RU_PER_REQUEST
            )
            and request_fraction <= _MAX_CAPACITY_FRACTION
            and resource_unit_fraction <= _MAX_CAPACITY_FRACTION
            and self.always_ready_units == 0
            and isinstance(self.projected_execution_units_gb_seconds, (int, float))
            and not isinstance(self.projected_execution_units_gb_seconds, bool)
            and isinstance(self.observed_execution_units_gb_seconds, (int, float))
            and not isinstance(self.observed_execution_units_gb_seconds, bool)
            and 0 <= projected_execution <= _MAX_EXECUTION_UNITS_GB_SECONDS
            and 0 <= observed_execution <= _MAX_EXECUTION_UNITS_GB_SECONDS
            and projected_execution + observed_execution
            <= _MAX_EXECUTION_UNITS_GB_SECONDS
            and self.telemetry_cap_reached is False
            and self.monitor_evidence_sha256 != self.source_evidence_sha256
            and -300 <= age_seconds <= 86_400
            and self.tenant_binding_sha256 == _sha256_text(_EXPECTED_TENANT_ID)
            and self.workspace_binding_sha256 == _sha256_text(WORKSPACE_ID)
        )
        if not valid:
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
        attestation = {
            field: getattr(self, field)
            for field in self.__dataclass_fields__
        }
        return {
            "status": "PASSED",
            "sharepoint_tier_id_sha256": _sha256_text(self.sharepoint_tier_id),
            "request_allowance_window_seconds": self.request_allowance_window_seconds,
            "resource_unit_allowance_window_seconds": self.resource_unit_allowance_window_seconds,
            "maximum_dispatches_per_minute": self.projected_request_count,
            "baseline_request_count": self.baseline_request_count,
            "baseline_resource_units": self.baseline_resource_units,
            "projected_request_count": self.projected_request_count,
            "projected_resource_units": self.projected_resource_units,
            "verified_request_allowance_fraction_used": round(request_fraction, 6),
            "verified_resource_unit_allowance_fraction_used": round(
                resource_unit_fraction, 6
            ),
            "projected_request_units_per_bff_request": _PROJECTED_RU_PER_REQUEST,
            "maximum_capacity_fraction": _MAX_CAPACITY_FRACTION,
            "always_ready_units": 0,
            "azure_execution_units_gb_seconds": observed_execution,
            "projected_execution_units_gb_seconds": projected_execution,
            "execution_units_below_cap": True,
            "telemetry_cap_reached": False,
            "source_evidence_sha256": self.source_evidence_sha256,
            "monitor_evidence_sha256": self.monitor_evidence_sha256,
            "lease_evidence_sha256": self.lease_evidence_sha256,
            "attestation_sha256": _sha256_json(attestation),
        }


@dataclass(frozen=True, slots=True)
class PerformanceExecutionAuthorization:
    status: str
    owner_login: str
    owner_approval_reference_sha256: str
    owner_approval_body_sha256: str
    action: str
    correlation_id: str
    contract_sha256: str
    activation_hash: str
    activation_receipt_sha256: str
    activation_evidence_sha256: str
    target_binding_sha256: str
    capacity_preflight_sha256: str
    phase_plan_sha256: str
    interruption_terminalization_status: str

    def validate(self, *, plan: Mapping[str, Any]) -> None:
        sha_fields = (
            self.owner_approval_reference_sha256,
            self.owner_approval_body_sha256,
            self.contract_sha256,
            self.activation_hash,
            self.activation_receipt_sha256,
            self.activation_evidence_sha256,
            self.target_binding_sha256,
            self.capacity_preflight_sha256,
            self.phase_plan_sha256,
        )
        if any(_SHA256_RE.fullmatch(value) is None for value in sha_fields) or (
            self.status != "VERIFIED"
            or self.owner_login != REQUIRED_OWNER_LOGIN
            or self.action != OWNER_ACTION
            or self.interruption_terminalization_status
            != "VERIFIED_BY_COMMITTED_ACTIVATION_RECEIPT"
            or self.contract_sha256 != plan.get("contract_sha256")
            or self.activation_hash != plan.get("expected_activation_hash")
            or self.target_binding_sha256 != plan.get("target_binding_sha256")
            or self.phase_plan_sha256 != plan.get("phase_plan_sha256")
        ):
            raise ValueError("PERFORMANCE_EXECUTION_AUTHORIZATION_INVALID")
        validate_correlation_id(self.correlation_id)


@dataclass(frozen=True, slots=True)
class RuntimeSafetyObservation:
    observed_execution_units_gb_seconds: float
    always_ready_units: int
    telemetry_cap_reached: bool
    monitor_evidence_sha256: str
    lease_evidence_sha256: str
    capacity_attestation_sha256: str
    observed_at_utc: str

    def validate(self, *, now: datetime) -> dict[str, Any]:
        _require_sha256(self.monitor_evidence_sha256, "monitor_evidence_sha256")
        _require_sha256(self.lease_evidence_sha256, "lease_evidence_sha256")
        _require_sha256(
            self.capacity_attestation_sha256, "capacity_attestation_sha256"
        )
        observed_at = _parse_timestamp(self.observed_at_utc)
        age = (now.astimezone(UTC) - observed_at).total_seconds()
        execution_units = self.observed_execution_units_gb_seconds
        if (
            not isinstance(execution_units, (int, float))
            or isinstance(execution_units, bool)
            or not 0 <= float(execution_units) <= _MAX_EXECUTION_UNITS_GB_SECONDS
            or type(self.always_ready_units) is not int
            or self.always_ready_units != 0
            or self.telemetry_cap_reached is not False
            or not -300 <= age <= 300
        ):
            raise ValueError("PERFORMANCE_RUNTIME_SAFETY_BLOCKED")
        return {
            "status": "PASSED",
            "observed_execution_units_gb_seconds": float(execution_units),
            "always_ready_units": 0,
            "telemetry_cap_reached": False,
            "monitor_evidence_sha256": self.monitor_evidence_sha256,
            "lease_evidence_sha256": self.lease_evidence_sha256,
            "capacity_attestation_sha256": self.capacity_attestation_sha256,
            "observed_at_utc_sha256": _sha256_text(self.observed_at_utc),
        }


class Clock(Protocol):
    def monotonic(self) -> float: ...

    def sleep(self, seconds: float) -> None: ...

    def now(self) -> datetime: ...


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def now(self) -> datetime:
        return datetime.now(UTC)


class LatencyMetrics:
    _BUCKET_MS = 10
    _MAX_BUCKET = 6000

    def __init__(self, payload: Mapping[str, Any] | None = None) -> None:
        self.request_count = 0
        self.error_count = 0
        self.max_latency_ms = 0
        self.status_counts: dict[str, int] = {}
        self.error_codes: dict[str, int] = {}
        self.histogram: dict[int, int] = {}
        if payload is not None:
            self._restore(payload)

    def record(self, sample: PerformanceSample) -> None:
        latency = max(0, min(int(sample.latency_ms), 60_000))
        self.request_count += 1
        self.max_latency_ms = max(self.max_latency_ms, latency)
        status_key = str(sample.status_code) if sample.status_code else "transport"
        self.status_counts[status_key] = self.status_counts.get(status_key, 0) + 1
        bucket = min(
            self._MAX_BUCKET,
            (latency + self._BUCKET_MS - 1) // self._BUCKET_MS,
        )
        self.histogram[bucket] = self.histogram.get(bucket, 0) + 1
        if not sample.valid_response or sample.status_code != 200:
            self.error_count += 1
            code = _safe_aggregate_error_code(sample.error_code)
            self.error_codes[code] = self.error_codes.get(code, 0) + 1

    def percentile_ms(self, percentile: float) -> int:
        if self.request_count == 0:
            return 0
        rank = max(1, int((self.request_count * percentile) + 0.999999))
        seen = 0
        for bucket, count in sorted(self.histogram.items()):
            seen += count
            if seen >= rank:
                return min(60_000, bucket * self._BUCKET_MS)
        return self.max_latency_ms

    def as_state(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "max_latency_ms": self.max_latency_ms,
            "status_counts": dict(sorted(self.status_counts.items())),
            "error_codes": dict(sorted(self.error_codes.items())),
            "histogram": {
                str(key): value for key, value in sorted(self.histogram.items())
            },
        }

    def summary(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": (
                self.error_count / self.request_count if self.request_count else 1.0
            ),
            "latency_ms": {
                "p50": self.percentile_ms(0.50),
                "p95": self.percentile_ms(0.95),
                "p99": self.percentile_ms(0.99),
                "max": self.max_latency_ms,
            },
            "status_counts": dict(sorted(self.status_counts.items())),
            "error_codes": dict(sorted(self.error_codes.items())),
        }

    def _restore(self, payload: Mapping[str, Any]) -> None:
        required = {
            "request_count",
            "error_count",
            "max_latency_ms",
            "status_counts",
            "error_codes",
            "histogram",
        }
        if set(payload) != required:
            raise ValueError("PERFORMANCE_STATE_INVALID")
        self.request_count = _nonnegative_int(payload["request_count"])
        self.error_count = _nonnegative_int(payload["error_count"])
        self.max_latency_ms = _nonnegative_int(payload["max_latency_ms"])
        self.status_counts = _count_mapping(payload["status_counts"])
        self.error_codes = _count_mapping(payload["error_codes"])
        histogram = _count_mapping(payload["histogram"])
        self.histogram = {int(key): value for key, value in histogram.items()}
        if (
            self.error_count > self.request_count
            or sum(self.status_counts.values()) != self.request_count
            or sum(self.histogram.values()) != self.request_count
            or any(key < 0 or key > self._MAX_BUCKET for key in self.histogram)
        ):
            raise ValueError("PERFORMANCE_STATE_INVALID")


def build_performance_acceptance_plan(
    expected_activation_hash: str,
    contract_sha256: str,
) -> dict[str, Any]:
    _require_sha256(expected_activation_hash, "expected_activation_hash")
    _require_sha256(contract_sha256, "contract_sha256")
    phase_plan = [phase.as_dict() for phase in PHASES]
    target_binding = {
        "scheme": "https",
        "host": _FUNCTION_HOST,
        "port": 443,
        "method": "GET",
        "path": (
            f"/v1/workspaces/{WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}/"
            "workbench-snapshot"
        ),
        "query": f"purpose={ALLOWED_PURPOSE}",
    }
    payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "command": f"{PLAN_COMMAND} --expected-activation-hash <sha256> --format json",
        "status": "READY",
        "mode": "offline_plan",
        "contract_sha256": contract_sha256,
        "expected_activation_hash": expected_activation_hash,
        "target_binding_sha256": _sha256_json(target_binding),
        "phase_plan_sha256": _sha256_json(phase_plan),
        "target": {
            "workspace_id_sha256": _sha256_text(WORKSPACE_ID),
            "matter_id_sha256": _sha256_text(ALLOWED_MATTER_ID),
            "endpoint_sha256": _sha256_text(_ENDPOINT),
            "https_only": True,
            "fixed_host": True,
            "read_only": True,
            "synthetic_only": True,
        },
        "phases": phase_plan,
        "budgets": {
            "total_request_limit": TOTAL_REQUEST_LIMIT,
            "maximum_client_concurrency": 1,
            "maximum_response_bytes": _MAX_RESPONSE_BYTES,
            "maximum_log_payload_bytes": 0,
            "infrastructure_restart_count": 0,
            "tenant_write_count": 0,
            "credential_change_count": 0,
            "permission_change_count": 0,
            "automatic_rollback_count": 0,
            "automatic_deletion_count": 0,
            "maximum_execution_units_gb_seconds": (
                _MAX_EXECUTION_UNITS_GB_SECONDS
            ),
        },
        "capacity_envelope": {
            "preflight_required": True,
            "authoritative_sharepoint_tier_required": True,
            "request_allowance_window_seconds": 60,
            "minimum_request_allowance_per_window": 200,
            "resource_unit_allowance_window_seconds": 60,
            "minimum_resource_unit_allowance_per_window": (
                _MIN_TENANT_RU_PER_MINUTE
            ),
            "source_and_lease_evidence_sha256_required": True,
            "projected_request_units_per_bff_request": (
                _PROJECTED_RU_PER_REQUEST
            ),
            "maximum_capacity_fraction": _MAX_CAPACITY_FRACTION,
            "maximum_dispatches_per_minute": 100,
            "abort_on_throttle_signal": True,
            "no_client_retries": True,
            "open_loop_no_catch_up_bursts": True,
        },
        "live_preconditions": {
            "successful_activation_receipt_required": True,
            "interrupted_activation_terminalization_required": True,
            "exclusive_remote_lease_required": True,
            "azure_meter_preflight_required": True,
            "always_ready_units_must_equal": 0,
            "telemetry_cap_not_reached_required": True,
        },
        "cold_start_interpretation": {
            "classification_without_epoch_change": "INCONCLUSIVE",
            "classification_with_epoch_change": "VERIFIED",
            "provider_cold_start_claimed": False,
            "idle_seconds": 1200,
            "infrastructure_restart_forbidden": True,
        },
        "evidence_boundary": {
            "raw_tokens": False,
            "raw_response_bodies": False,
            "raw_urls": False,
            "tenant_ids": False,
            "user_ids": False,
            "request_headers": False,
            "aggregated_metrics_only": True,
            "phase_state_resumable": True,
            "dispatch_reserved_before_network": True,
            "inflight_attempt_is_not_retried": True,
        },
    }
    plan_sha256 = _sha256_json(payload)
    return {**payload, "plan_sha256": plan_sha256}


def build_owner_comment(
    contract_sha256: str,
    expected_activation_hash: str,
    capacity_preflight_sha256: str,
    correlation_id: str,
) -> dict[str, str]:
    _require_sha256(contract_sha256, "contract_sha256")
    _require_sha256(capacity_preflight_sha256, "capacity_preflight_sha256")
    validate_correlation_id(correlation_id)
    plan = build_performance_acceptance_plan(
        expected_activation_hash,
        contract_sha256,
    )
    body = (
        "NAC_BFF_PERFORMANCE_ACCEPTANCE_APPROVAL\n"
        + _canonical_json(
            {
                "action": OWNER_ACTION,
                "contract_sha256": contract_sha256,
                "expected_activation_hash": expected_activation_hash,
                "target_binding_sha256": plan["target_binding_sha256"],
                "capacity_preflight_sha256": capacity_preflight_sha256,
                "phase_plan_sha256": plan["phase_plan_sha256"],
                "correlation_id": correlation_id,
                "phase_ids": [phase.phase_id for phase in PHASES],
                "total_request_limit": TOTAL_REQUEST_LIMIT,
                "maximum_dispatches_per_minute": 100,
                "maximum_execution_units_gb_seconds": (
                    _MAX_EXECUTION_UNITS_GB_SECONDS
                ),
                "required_owner_login": REQUIRED_OWNER_LOGIN,
                "notary_team_01_only": True,
                "synthetic_reads_only": True,
                "no_infrastructure_restart": True,
                "no_credential_or_permission_changes": True,
                "no_automatic_rollback_or_deletion": True,
                "capacity_and_meter_preflight_required": True,
                "exclusive_remote_lease_required": True,
                "abort_on_throttle_signal": True,
            }
        )
    )
    return {"body": body, "body_sha256": _sha256_text(body)}


def verify_activation_success(repo_root: Path, activation_hash: str) -> dict[str, Any]:
    _require_sha256(activation_hash, "activation_hash")
    run_dir = (repo_root / activation_runner.DEFAULT_OUTPUT_ROOT / activation_hash).resolve()
    expected_root = (repo_root / activation_runner.DEFAULT_OUTPUT_ROOT).resolve()
    if expected_root not in run_dir.parents:
        raise ValueError("ACTIVATION_SUCCESS_RECEIPT_INVALID")
    receipt_path = run_dir / "activation.success-receipt.redacted.json"
    evidence_path = run_dir / "activation.redacted.json"
    commit_marker_path = run_dir / "activation.commit.redacted.json"
    state_path = run_dir / "resume-state.redacted.json"
    receipt = activation_runner._read_secure_canonical_json(receipt_path)
    evidence = activation_runner._read_secure_canonical_json(evidence_path)
    state = activation_runner._read_secure_canonical_json(state_path)
    if (
        not isinstance(receipt, dict)
        or not isinstance(evidence, dict)
        or not isinstance(state, dict)
    ):
        raise ValueError("ACTIVATION_SUCCESS_RECEIPT_MISSING")
    try:
        activation_runner._validate_evidence(evidence)
    except activation_runner.ActivationStepError:
        raise ValueError("ACTIVATION_SUCCESS_RECEIPT_INVALID") from None
    expected_receipt_keys = {
        "schema_version",
        "status",
        "activation_hash",
        "approval_body_sha256",
        "approval_reference_sha256",
        "approved_commit_sha",
        "approved_tree_sha",
        "provisioner_bootstrap_binding_sha256",
        "toolchain_attestations_sha256",
        "target_binding_sha256",
        "evidence_sha256",
        "final_commit_marker_sha256",
        "final_state_sha256",
        "receipt_sha256",
    }
    artifact_hashes = {
        "evidence_sha256": activation_runner._artifact_sha256(evidence_path),
        "final_commit_marker_sha256": activation_runner._artifact_sha256(
            commit_marker_path
        ),
        "final_state_sha256": activation_runner._artifact_sha256(state_path),
    }
    receipt_evidence_bindings = {
        "activation_hash": "activation_hash",
        "approval_reference_sha256": "approval_reference_sha256",
        "approved_commit_sha": "approved_commit_sha",
        "approved_tree_sha": "approved_tree_sha",
        "provisioner_bootstrap_binding_sha256": (
            "provisioner_bootstrap_binding_sha256"
        ),
        "toolchain_attestations_sha256": "toolchain_attestations_sha256",
        "target_binding_sha256": "target_binding_sha256",
    }
    receipt_state_bindings = {
        "approval_body_sha256": "approval_body_sha256",
        "approval_reference_sha256": "approval_reference_sha256",
        "approved_commit_sha": "approved_commit_sha",
        "approved_tree_sha": "approved_tree_sha",
        "provisioner_bootstrap_binding_sha256": (
            "provisioner_bootstrap_binding_sha256"
        ),
        "toolchain_attestations_sha256": "toolchain_attestations_sha256",
        "target_binding_sha256": "target_binding_sha256",
    }
    receipt_without_digest = dict(receipt)
    receipt_digest = receipt_without_digest.pop("receipt_sha256", None)
    summary = evidence.get("summary")
    current_activation_plan = build_azure_bff_activation_plan(repo_root)
    current_activation_bindings = current_activation_plan.get("bindings")
    expected_function_base_url = f"https://{_FUNCTION_HOST}"
    expected_activation_target_sha256 = (
        activation_runner._binding_sha256_json(current_activation_bindings)
        if isinstance(current_activation_bindings, dict)
        else None
    )
    if (
        set(receipt) != expected_receipt_keys
        or receipt.get("schema_version")
        != activation_runner.SUCCESS_RECEIPT_SCHEMA_VERSION
        or receipt.get("status") != "COMMITTED"
        or receipt.get("activation_hash") != activation_hash
        or not isinstance(current_activation_bindings, dict)
        or current_activation_bindings.get("function_base_url")
        != expected_function_base_url
        or current_activation_bindings.get("workspace_id") != WORKSPACE_ID
        or current_activation_bindings.get("matter_id") != MATTER_ID
        or receipt.get("target_binding_sha256")
        != expected_activation_target_sha256
        or receipt_digest != activation_runner._sha256_json(receipt_without_digest)
        or any(value is None for value in artifact_hashes.values())
        or any(receipt.get(key) != value for key, value in artifact_hashes.items())
        or any(
            receipt.get(receipt_key) != evidence.get(evidence_key)
            for receipt_key, evidence_key in receipt_evidence_bindings.items()
        )
        or any(
            receipt.get(receipt_key) != state.get(state_key)
            for receipt_key, state_key in receipt_state_bindings.items()
        )
        or evidence.get("status") != "PASSED"
        or evidence.get("activation_hash") != activation_hash
        or state.get("status") != "PASSED"
        or state.get("activation_hash") != activation_hash
        or state.get("target_binding_sha256")
        != evidence.get("target_binding_sha256")
        or state.get("ledger_head_sha256") != evidence.get("ledger_head_sha256")
        or not activation_runner._final_commit_marker_matches(
            commit_marker_path, evidence
        )
        or not activation_runner._terminal_chain_is_valid(
            state, run_dir / "ledger"
        )
        or not isinstance(summary, dict)
        or summary.get("passed_step_count") != 12
        or summary.get("required_step_count") != 12
        or summary.get("failed_step_count") != 0
        or summary.get("synthetic_state_restored") is not True
        or summary.get("assigned_access_passed") is not True
        or summary.get("deputy_access_passed") is not True
        or summary.get("denied_access_passed") is not True
    ):
        raise ValueError("ACTIVATION_SUCCESS_RECEIPT_INVALID")
    return {
        "status": "VERIFIED",
        "activation_hash": activation_hash,
        "receipt_sha256": receipt_digest,
        "evidence_sha256": artifact_hashes["evidence_sha256"],
        "activated_function_base_url_sha256": _sha256_text(
            expected_function_base_url
        ),
        "activated_workspace_id_sha256": _sha256_text(WORKSPACE_ID),
        "activated_matter_id_sha256": _sha256_text(MATTER_ID),
    }


class ImmutableOwnerCommentVerifier(Protocol):
    def verify_performance_owner_comment(
        self,
        *,
        reference: str,
        expected_body: str,
        expected_body_sha256: str,
    ) -> dict[str, Any]: ...


class PerformanceAuthorizationVerifier(Protocol):
    def verify(
        self,
        *,
        approval_reference: str,
        contract_sha256: str,
        activation_hash: str,
        capacity_preflight_sha256: str,
        correlation_id: str,
    ) -> PerformanceExecutionAuthorization: ...


class BoundPerformanceAuthorizationVerifier:
    def __init__(
        self,
        *,
        repo_root: Path,
        approval_verifier: ImmutableOwnerCommentVerifier,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._approval_verifier = approval_verifier

    def verify(
        self,
        *,
        approval_reference: str,
        contract_sha256: str,
        activation_hash: str,
        capacity_preflight_sha256: str,
        correlation_id: str,
    ) -> PerformanceExecutionAuthorization:
        return verify_performance_execution_authorization(
            repo_root=self._repo_root,
            approval_verifier=self._approval_verifier,
            approval_reference=approval_reference,
            contract_sha256=contract_sha256,
            activation_hash=activation_hash,
            capacity_preflight_sha256=capacity_preflight_sha256,
            correlation_id=correlation_id,
        )


def verify_performance_execution_authorization(
    *,
    repo_root: Path,
    approval_verifier: ImmutableOwnerCommentVerifier,
    approval_reference: str,
    contract_sha256: str,
    activation_hash: str,
    capacity_preflight_sha256: str,
    correlation_id: str,
) -> PerformanceExecutionAuthorization:
    """Verify the immutable owner comment and committed activation receipt."""

    contract_path = (repo_root.resolve() / CONTRACT_RELATIVE_PATH).resolve()
    if (
        repo_root.resolve() not in contract_path.parents
        or not contract_path.is_file()
        or _sha256_file(contract_path) != contract_sha256
    ):
        raise ValueError("PERFORMANCE_CONTRACT_BINDING_MISMATCH")
    plan = build_performance_acceptance_plan(activation_hash, contract_sha256)
    expected = build_owner_comment(
        contract_sha256,
        activation_hash,
        capacity_preflight_sha256,
        correlation_id,
    )
    approval = approval_verifier.verify_performance_owner_comment(
        reference=approval_reference,
        expected_body=expected["body"],
        expected_body_sha256=expected["body_sha256"],
    )
    if (
        approval.get("status") != "VERIFIED"
        or approval.get("owner_login") != REQUIRED_OWNER_LOGIN
        or approval.get("immutable") is not True
        or approval.get("reference") != approval_reference
        or approval.get("body_sha256") != expected["body_sha256"]
    ):
        raise ValueError("PERFORMANCE_OWNER_APPROVAL_INVALID")
    activation = verify_activation_success(repo_root, activation_hash)
    if (
        activation.get("activated_function_base_url_sha256")
        != _sha256_text(f"https://{_FUNCTION_HOST}")
        or activation.get("activated_workspace_id_sha256")
        != _sha256_text(WORKSPACE_ID)
        or activation.get("activated_matter_id_sha256")
        != _sha256_text(ALLOWED_MATTER_ID)
    ):
        raise ValueError("PERFORMANCE_ACTIVATION_TARGET_MISMATCH")
    authorization = PerformanceExecutionAuthorization(
        status="VERIFIED",
        owner_login=REQUIRED_OWNER_LOGIN,
        owner_approval_reference_sha256=_sha256_text(approval_reference),
        owner_approval_body_sha256=expected["body_sha256"],
        action=OWNER_ACTION,
        correlation_id=correlation_id,
        contract_sha256=contract_sha256,
        activation_hash=activation_hash,
        activation_receipt_sha256=activation["receipt_sha256"],
        activation_evidence_sha256=activation["evidence_sha256"],
        target_binding_sha256=plan["target_binding_sha256"],
        capacity_preflight_sha256=capacity_preflight_sha256,
        phase_plan_sha256=plan["phase_plan_sha256"],
        interruption_terminalization_status=(
            "VERIFIED_BY_COMMITTED_ACTIVATION_RECEIPT"
        ),
    )
    authorization.validate(plan=plan)
    return authorization


class PerformanceAcceptanceRunner:
    def __init__(
        self,
        *,
        transport: PerformanceTransport,
        checkpoint_store: DurablePerformanceCheckpoint,
        authorization_verifier: PerformanceAuthorizationVerifier,
        capacity_provider: CapacityAttestationProvider,
        transport_verifier: TransportBindingVerifier,
        clock: Clock | None = None,
        phases: Sequence[PhaseSpec] = PHASES,
        safety_monitor: PerformanceSafetyMonitor | None = None,
    ) -> None:
        if not callable(getattr(checkpoint_store, "write_state", None)) or not callable(
            getattr(checkpoint_store, "load_state", None)
        ) or not callable(getattr(checkpoint_store, "state_sha256", None)):
            raise ValueError("PERFORMANCE_DURABLE_CHECKPOINT_REQUIRED")
        self._transport = transport
        self._clock = clock or SystemClock()
        self._phases = tuple(phases)
        self._checkpoint_store = checkpoint_store
        self._authorization_verifier = authorization_verifier
        self._capacity_provider = capacity_provider
        self._transport_verifier = transport_verifier
        self._safety_monitor = safety_monitor

    def run(
        self,
        *,
        plan_sha256: str,
        contract_sha256: str,
        activation_hash: str,
        approval_reference: str,
        correlation_id: str,
        expected_capacity_preflight_sha256: str,
    ) -> dict[str, Any]:
        _require_sha256(plan_sha256, "plan_sha256")
        _require_sha256(contract_sha256, "contract_sha256")
        _require_sha256(activation_hash, "activation_hash")
        _require_sha256(
            expected_capacity_preflight_sha256,
            "expected_capacity_preflight_sha256",
        )
        expected_plan = build_performance_acceptance_plan(
            activation_hash,
            contract_sha256,
        )
        if plan_sha256 != expected_plan["plan_sha256"]:
            raise ValueError("PERFORMANCE_PLAN_BINDING_MISMATCH")
        if tuple(self._phases) != tuple(PHASES):
            raise ValueError("PERFORMANCE_PHASE_PLAN_MISMATCH")
        resume_state = self._checkpoint_store.load_state()
        if resume_state is not None and self._checkpoint_store.state_sha256() != _sha256_json(
            resume_state
        ):
            raise ValueError("PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID")
        terminal_evidence = self._terminalize_interrupted_resume(
            resume_state=resume_state,
            plan_sha256=plan_sha256,
            contract_sha256=contract_sha256,
            activation_hash=activation_hash,
            expected_capacity_preflight_sha256=(
                expected_capacity_preflight_sha256
            ),
        )
        if terminal_evidence is not None:
            return terminal_evidence
        authorization = self._authorization_verifier.verify(
            approval_reference=approval_reference,
            contract_sha256=contract_sha256,
            activation_hash=activation_hash,
            capacity_preflight_sha256=expected_capacity_preflight_sha256,
            correlation_id=correlation_id,
        )
        authorization.validate(plan=expected_plan)
        if authorization.capacity_preflight_sha256 != expected_capacity_preflight_sha256:
            raise ValueError("PERFORMANCE_EXECUTION_AUTHORIZATION_INVALID")
        self._transport_verifier.verify(
            self._transport, expected_plan["target_binding_sha256"]
        )
        capacity_attestation = self._capacity_provider.get_attestation()
        if not isinstance(capacity_attestation, CapacityAttestation):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
        capacity_summary = capacity_attestation.validate(now=self._clock.now())
        if self._safety_monitor is None:
            raise ValueError("PERFORMANCE_SAFETY_MONITOR_REQUIRED")
        state = self._restore_or_create_state(
            plan_sha256=plan_sha256,
            contract_sha256=contract_sha256,
            activation_hash=activation_hash,
            owner_approval_body_sha256=authorization.owner_approval_body_sha256,
            approved_capacity_preflight_sha256=(
                expected_capacity_preflight_sha256
            ),
            resume_state=resume_state,
        )
        if (
            resume_state is None
            and capacity_summary["attestation_sha256"]
            != expected_capacity_preflight_sha256
        ):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_MISMATCH")
        if (
            resume_state is not None
            and state["current_phase"] is not None
            and state["current_phase"]["reserved_attempt_count"] == 0
            and state["current_phase"]["idle_elapsed_seconds"] > 0
        ):
            state["current_phase"]["idle_elapsed_seconds"] = 0.0
            self._write_checkpoint(state)
        existing_capacity = state.get("capacity_preflight")
        if existing_capacity is not None and not _same_capacity_policy(
            existing_capacity, capacity_summary
        ):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_MISMATCH")
        state["capacity_preflight"] = capacity_summary
        if state["status"] == "PASSED":
            self._observe_runtime_safety(
                state,
                sum(int(item["request_count"]) for item in state["phase_results"]),
            )
            self._write_checkpoint(state)
            return self._evidence(state, idempotent=True)
        for phase in self._phases:
            if phase.phase_id in state["completed_phase_ids"]:
                continue
            phase_state = state["current_phase"]
            if phase_state is None:
                phase_state = self._new_phase_state(phase)
                state["current_phase"] = phase_state
                self._write_checkpoint(state)
            if phase_state.get("phase_id") != phase.phase_id:
                raise ValueError("PERFORMANCE_STATE_INVALID")
            fatal_code = self._run_phase(phase, phase_state, state)
            summary = self._phase_summary(phase, phase_state)
            passed = fatal_code is None and self._phase_passed(phase, summary)
            if passed:
                try:
                    self._refresh_capacity(state)
                    self._observe_runtime_safety(
                        state,
                        sum(
                            int(item["request_count"])
                            for item in state["phase_results"]
                        )
                        + int(summary["request_count"]),
                    )
                except Exception as exc:
                    fatal_code = _safe_runtime_abort_code(exc)
                    phase_state["fatal_code"] = fatal_code
                    self._sync_metrics(phase_state, LatencyMetrics(phase_state["metrics"]), state)
                    summary = self._phase_summary(phase, phase_state)
                    passed = False
            summary["status"] = "PASSED" if passed else "FAILED"
            if not passed:
                summary["failure_code"] = (
                    fatal_code or "PERFORMANCE_THRESHOLD_EXCEEDED"
                )
            state["phase_results"].append(summary)
            state["current_phase"] = None
            if not passed:
                state["status"] = "FAILED"
                state["finished_at_utc"] = _timestamp(self._clock.now())
                self._write_checkpoint(state)
                return self._evidence(state, idempotent=False)
            state["completed_phase_ids"].append(phase.phase_id)
            self._write_checkpoint(state)
        state["status"] = "PASSED"
        state["finished_at_utc"] = _timestamp(self._clock.now())
        self._write_checkpoint(state)
        return self._evidence(state, idempotent=False)

    def _terminalize_interrupted_resume(
        self,
        *,
        resume_state: Mapping[str, Any] | None,
        plan_sha256: str,
        contract_sha256: str,
        activation_hash: str,
        expected_capacity_preflight_sha256: str,
    ) -> dict[str, Any] | None:
        if not isinstance(resume_state, Mapping):
            return None
        current = resume_state.get("current_phase")
        if not isinstance(current, Mapping):
            return None
        reserved = current.get("reserved_attempt_count")
        completed = current.get("completed_attempt_count")
        interrupted = current.get("safety_check_pending") is True or (
            type(reserved) is int
            and type(completed) is int
            and reserved == completed + 1
        )
        if not interrupted:
            return None
        owner_binding = resume_state.get("owner_approval_body_sha256")
        if not isinstance(owner_binding, str):
            raise ValueError("PERFORMANCE_STATE_INVALID")
        state = self._restore_or_create_state(
            plan_sha256=plan_sha256,
            contract_sha256=contract_sha256,
            activation_hash=activation_hash,
            owner_approval_body_sha256=owner_binding,
            approved_capacity_preflight_sha256=(
                expected_capacity_preflight_sha256
            ),
            resume_state=resume_state,
        )
        phase_index = len(state["completed_phase_ids"])
        if phase_index >= len(self._phases):
            raise ValueError("PERFORMANCE_STATE_INVALID")
        phase = self._phases[phase_index]
        phase_state = state["current_phase"]
        metrics = LatencyMetrics(phase_state["metrics"])
        self._reconcile_reserved_attempt(phase_state, metrics, state)
        fatal_code = phase_state.get("fatal_code")
        if not isinstance(fatal_code, str):
            raise ValueError("PERFORMANCE_STATE_INVALID")
        summary = self._phase_summary(phase, phase_state)
        summary["status"] = "FAILED"
        summary["failure_code"] = fatal_code
        state["phase_results"].append(summary)
        state["current_phase"] = None
        state["status"] = "FAILED"
        state["finished_at_utc"] = _timestamp(self._clock.now())
        self._write_checkpoint(state)
        return self._evidence(state, idempotent=False)

    def _run_phase(
        self,
        phase: PhaseSpec,
        phase_state: dict[str, Any],
        state: dict[str, Any],
    ) -> str | None:
        metrics = LatencyMetrics(phase_state["metrics"])
        self._reconcile_reserved_attempt(phase_state, metrics, state)
        if phase_state["fatal_code"] is not None:
            return phase_state["fatal_code"]
        idle_remaining = max(
            0.0,
            phase.idle_before_seconds - float(phase_state["idle_elapsed_seconds"]),
        )
        if idle_remaining:
            start = self._clock.monotonic()
            self._clock.sleep(idle_remaining)
            phase_state["idle_elapsed_seconds"] += max(
                0.0, self._clock.monotonic() - start
            )
            self._sync_metrics(phase_state, metrics, state)

        if phase.mode == "paced":
            return self._run_paced(phase, phase_state, metrics, state)
        return "PERFORMANCE_PHASE_INVALID"

    def _run_paced(
        self,
        phase: PhaseSpec,
        phase_state: dict[str, Any],
        metrics: LatencyMetrics,
        state: dict[str, Any],
    ) -> str | None:
        while metrics.request_count < phase.request_limit:
            if phase_state["active_elapsed_seconds"] >= phase.duration_seconds:
                break
            started = self._clock.monotonic()
            try:
                self._reserve_dispatch(phase_state, metrics, state)
            except _PerformancePreDispatchAbort as exc:
                fatal = str(exc)
                phase_state["fatal_code"] = fatal
                self._sync_metrics(phase_state, metrics, state)
                return fatal
            sample = self._transport.request()
            fatal = self._record_samples(metrics, (sample,))
            if sample.latency_ms > phase.max_latency_ms:
                fatal = "PERFORMANCE_REQUEST_LATENCY_EXCEEDED"
            if fatal is not None:
                phase_state["fatal_code"] = fatal
            phase_state["completed_attempt_count"] += 1
            self._append_journal_event(state, phase_state, "DISPATCH_COMPLETED")
            if sample.instance_epoch_sha256 is not None:
                phase_state["instance_epoch_sha256"] = sample.instance_epoch_sha256
            elapsed = max(0.0, self._clock.monotonic() - started)
            phase_state["active_elapsed_seconds"] += elapsed
            self._sync_metrics(phase_state, metrics, state)
            if fatal is not None:
                return fatal
            sleep_seconds = max(0.0, phase.interval_seconds - elapsed)
            if sleep_seconds:
                self._clock.sleep(sleep_seconds)
            phase_state["active_elapsed_seconds"] += max(
                0.0, self._clock.monotonic() - started - elapsed
            )
            self._sync_metrics(phase_state, metrics, state)
        if metrics.request_count != phase.request_limit:
            return "PERFORMANCE_PHASE_TARGET_NOT_MET"
        return None

    def _reserve_dispatch(
        self,
        phase_state: dict[str, Any],
        metrics: LatencyMetrics,
        state: dict[str, Any],
    ) -> None:
        total_attempts = sum(
            int(item.get("request_count", 0)) for item in state["phase_results"]
        ) + int(phase_state["reserved_attempt_count"])
        if total_attempts >= _GLOBAL_REQUEST_LIMIT:
            raise _PerformancePreDispatchAbort(
                "PERFORMANCE_REQUEST_CEILING_REACHED"
            )
        phase_state["safety_check_pending"] = True
        self._sync_metrics(phase_state, metrics, state)
        try:
            self._refresh_capacity(state)
            self._observe_runtime_safety(
                state,
                total_attempts + 1,
                projected_remaining_dispatch_count=(
                    _GLOBAL_REQUEST_LIMIT - total_attempts
                ),
            )
        except Exception as exc:
            raise _PerformancePreDispatchAbort(
                _safe_runtime_abort_code(exc)
            ) from None
        phase_state["reserved_attempt_count"] += 1
        phase_state["safety_check_pending"] = False
        self._append_journal_event(state, phase_state, "DISPATCH_RESERVED")
        self._sync_metrics(phase_state, metrics, state)

    def _observe_runtime_safety(
        self,
        state: dict[str, Any],
        dispatch_attempt_count: int,
        *,
        projected_remaining_dispatch_count: int | None = None,
    ) -> None:
        capacity = state.get("capacity_preflight")
        if not isinstance(capacity, dict):
            raise ValueError("PERFORMANCE_RUNTIME_SAFETY_BLOCKED")
        attestation_sha256 = capacity.get("attestation_sha256")
        observation = self._safety_monitor.observe(
            dispatch_attempt_count,
            attestation_sha256,
        )
        if not isinstance(observation, RuntimeSafetyObservation):
            raise ValueError("PERFORMANCE_RUNTIME_SAFETY_BLOCKED")
        summary = observation.validate(now=self._clock.now())
        if (
            summary["capacity_attestation_sha256"] != attestation_sha256
            or summary["monitor_evidence_sha256"]
            == capacity["source_evidence_sha256"]
            or summary["lease_evidence_sha256"]
            != capacity["lease_evidence_sha256"]
        ):
            raise ValueError("PERFORMANCE_RUNTIME_SAFETY_BLOCKED")
        remaining = (
            _GLOBAL_REQUEST_LIMIT - dispatch_attempt_count
            if projected_remaining_dispatch_count is None
            else projected_remaining_dispatch_count
        )
        if type(remaining) is not int or not 0 <= remaining <= _GLOBAL_REQUEST_LIMIT:
            raise ValueError("PERFORMANCE_RUNTIME_SAFETY_BLOCKED")
        projected_total = float(capacity["projected_execution_units_gb_seconds"])
        projected_remaining = projected_total * remaining / _GLOBAL_REQUEST_LIMIT
        observed = float(summary["observed_execution_units_gb_seconds"])
        if (
            remaining > 0
            and observed >= _MAX_EXECUTION_UNITS_GB_SECONDS
            or observed + projected_remaining > _MAX_EXECUTION_UNITS_GB_SECONDS
        ):
            raise ValueError("PERFORMANCE_EXECUTION_UNIT_BUDGET_EXHAUSTED")
        state["runtime_safety"] = summary

    def _refresh_capacity(self, state: dict[str, Any]) -> None:
        try:
            attestation = self._capacity_provider.get_attestation()
        except Exception:
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED") from None
        if not isinstance(attestation, CapacityAttestation):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
        refreshed = attestation.validate(now=self._clock.now())
        current = state.get("capacity_preflight")
        if current is not None and not _same_capacity_policy(current, refreshed):
            raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_MISMATCH")
        state["capacity_preflight"] = refreshed

    def _reconcile_reserved_attempt(
        self,
        phase_state: dict[str, Any],
        metrics: LatencyMetrics,
        state: dict[str, Any],
    ) -> None:
        if phase_state["safety_check_pending"]:
            phase_state["safety_check_pending"] = False
            phase_state["fatal_code"] = "PREDISPATCH_SAFETY_OUTCOME_UNKNOWN"
            self._sync_metrics(phase_state, metrics, state)
            return
        reserved = int(phase_state["reserved_attempt_count"])
        completed = int(phase_state["completed_attempt_count"])
        if reserved < completed or reserved - completed > 1:
            raise ValueError("PERFORMANCE_STATE_INVALID")
        if reserved == completed + 1:
            metrics.record(
                PerformanceSample(
                    0,
                    0,
                    False,
                    "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN",
                    False,
                )
            )
            phase_state["completed_attempt_count"] += 1
            phase_state["fatal_code"] = "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN"
            self._append_journal_event(
                state, phase_state, "INFLIGHT_OUTCOME_RECONCILED"
            )
            self._sync_metrics(phase_state, metrics, state)

    @staticmethod
    def _append_journal_event(
        state: dict[str, Any],
        phase_state: Mapping[str, Any],
        event_type: str,
    ) -> None:
        previous = state["journal_head_sha256"]
        state["journal_head_sha256"] = _sha256_json(
            {
                "previous_sha256": previous,
                "event_type": event_type,
                "phase_id": phase_state["phase_id"],
                "reserved_attempt_count": phase_state["reserved_attempt_count"],
                "completed_attempt_count": phase_state["completed_attempt_count"],
            }
        )
        state["journal_event_count"] += 1

    @staticmethod
    def _record_samples(
        metrics: LatencyMetrics, samples: Sequence[PerformanceSample]
    ) -> str | None:
        fatal: str | None = None
        for sample in samples:
            metrics.record(sample)
            if sample.fatal and fatal is None:
                fatal = _safe_aggregate_error_code(sample.error_code)
        return fatal

    def _sync_metrics(
        self,
        phase_state: dict[str, Any],
        metrics: LatencyMetrics,
        state: dict[str, Any],
    ) -> None:
        phase_state["metrics"] = metrics.as_state()
        phase_state["checkpoint_count"] += 1
        self._write_checkpoint(state)

    def _write_checkpoint(self, state: Mapping[str, Any]) -> None:
        snapshot = json.loads(_canonical_json(state))
        self._checkpoint_store.write_state(snapshot)
        if (
            self._checkpoint_store.load_state() != snapshot
            or self._checkpoint_store.state_sha256() != _sha256_json(snapshot)
        ):
            raise ValueError("PERFORMANCE_DURABLE_CHECKPOINT_FAILED")

    def _new_phase_state(self, phase: PhaseSpec) -> dict[str, Any]:
        return {
            "phase_id": phase.phase_id,
            "idle_elapsed_seconds": 0.0,
            "active_elapsed_seconds": 0.0,
            "checkpoint_count": 0,
            "safety_check_pending": False,
            "reserved_attempt_count": 0,
            "completed_attempt_count": 0,
            "instance_epoch_sha256": None,
            "fatal_code": None,
            "metrics": LatencyMetrics().as_state(),
        }

    def _restore_or_create_state(
        self,
        *,
        plan_sha256: str,
        contract_sha256: str,
        activation_hash: str,
        owner_approval_body_sha256: str,
        approved_capacity_preflight_sha256: str,
        resume_state: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if resume_state is None:
            return {
                "schema_version": STATE_SCHEMA_VERSION,
                "status": "RUNNING",
                "plan_sha256": plan_sha256,
                "contract_sha256": contract_sha256,
                "activation_hash": activation_hash,
                "owner_approval_body_sha256": owner_approval_body_sha256,
                "approved_capacity_preflight_sha256": (
                    approved_capacity_preflight_sha256
                ),
                "target_binding_sha256": build_performance_acceptance_plan(
                    activation_hash, contract_sha256
                )["target_binding_sha256"],
                "phase_plan_sha256": _sha256_json(
                    [phase.as_dict() for phase in self._phases]
                ),
                "started_at_utc": _timestamp(self._clock.now()),
                "finished_at_utc": None,
                "completed_phase_ids": [],
                "current_phase": None,
                "phase_results": [],
                "capacity_preflight": None,
                "runtime_safety": None,
                "journal_head_sha256": "0" * 64,
                "journal_event_count": 0,
            }
        state = json.loads(_canonical_json(resume_state))
        required = {
            "schema_version",
            "status",
            "plan_sha256",
            "contract_sha256",
            "activation_hash",
            "owner_approval_body_sha256",
            "approved_capacity_preflight_sha256",
            "target_binding_sha256",
            "phase_plan_sha256",
            "started_at_utc",
            "finished_at_utc",
            "completed_phase_ids",
            "current_phase",
            "phase_results",
            "capacity_preflight",
            "runtime_safety",
            "journal_head_sha256",
            "journal_event_count",
        }
        if (
            set(state) != required
            or state["schema_version"] != STATE_SCHEMA_VERSION
            or state["status"] not in {"RUNNING", "FAILED", "PASSED"}
            or state["plan_sha256"] != plan_sha256
            or state["contract_sha256"] != contract_sha256
            or state["activation_hash"] != activation_hash
            or state["owner_approval_body_sha256"]
            != owner_approval_body_sha256
            or state["approved_capacity_preflight_sha256"]
            != approved_capacity_preflight_sha256
            or state["target_binding_sha256"]
            != build_performance_acceptance_plan(
                activation_hash, contract_sha256
            )["target_binding_sha256"]
            or state["phase_plan_sha256"]
            != _sha256_json([phase.as_dict() for phase in self._phases])
            or _SHA256_RE.fullmatch(state["approved_capacity_preflight_sha256"])
            is None
            or not isinstance(state["completed_phase_ids"], list)
            or not isinstance(state["phase_results"], list)
            or not isinstance(state["journal_event_count"], int)
            or state["journal_event_count"] < 0
            or not isinstance(state["journal_head_sha256"], str)
            or _SHA256_RE.fullmatch(state["journal_head_sha256"]) is None
            or state["current_phase"] is not None
            and not isinstance(state["current_phase"], dict)
            or state["runtime_safety"] is not None
            and not isinstance(state["runtime_safety"], dict)
        ):
            raise ValueError("PERFORMANCE_STATE_INVALID")
        if state["status"] == "FAILED":
            raise ValueError("PERFORMANCE_FAILED_STATE_NOT_RESUMABLE")
        self._validate_state_semantics(state)
        return state

    def _validate_state_semantics(self, state: Mapping[str, Any]) -> None:
        try:
            _parse_timestamp(state["started_at_utc"])
            if state["finished_at_utc"] is not None:
                _parse_timestamp(state["finished_at_utc"])
        except (TypeError, ValueError):
            raise ValueError("PERFORMANCE_STATE_INVALID") from None

        phase_ids = [phase.phase_id for phase in self._phases]
        completed = state["completed_phase_ids"]
        results = state["phase_results"]
        if (
            any(not isinstance(value, str) for value in completed)
            or completed != phase_ids[: len(completed)]
            or len(results) != len(completed)
        ):
            raise ValueError("PERFORMANCE_STATE_INVALID")

        journal_events = 0
        for index, (phase, result) in enumerate(zip(self._phases, results)):
            self._validate_phase_result(phase, result)
            if result.get("status") != "PASSED" or completed[index] != phase.phase_id:
                raise ValueError("PERFORMANCE_STATE_INVALID")
            journal_events += int(result["reserved_attempt_count"]) + int(
                result["completed_attempt_count"]
            )

        current = state["current_phase"]
        if current is not None:
            if len(completed) >= len(self._phases):
                raise ValueError("PERFORMANCE_STATE_INVALID")
            self._validate_current_phase(self._phases[len(completed)], current)
            journal_events += int(current["reserved_attempt_count"]) + int(
                current["completed_attempt_count"]
            )

        if state["journal_event_count"] != journal_events:
            raise ValueError("PERFORMANCE_STATE_INVALID")
        runtime_safety = state["runtime_safety"]
        if runtime_safety is not None:
            _validate_runtime_safety_summary(
                runtime_safety,
                capacity=state["capacity_preflight"],
            )
        if state["status"] == "PASSED":
            if (
                completed != phase_ids
                or current is not None
                or state["finished_at_utc"] is None
                or runtime_safety is None
            ):
                raise ValueError("PERFORMANCE_STATE_INVALID")
        elif (
            state["status"] != "RUNNING"
            or state["finished_at_utc"] is not None
            or len(completed) == len(self._phases)
        ):
            raise ValueError("PERFORMANCE_STATE_INVALID")

        dispatches = sum(int(item["request_count"]) for item in results)
        if current is not None:
            dispatches += int(current["reserved_attempt_count"])
        if dispatches > _GLOBAL_REQUEST_LIMIT:
            raise ValueError("PERFORMANCE_STATE_INVALID")

    @staticmethod
    def _validate_phase_result(phase: PhaseSpec, result: Any) -> None:
        required = {
            "phase_id",
            "mode",
            "request_limit",
            "idle_elapsed_seconds",
            "active_elapsed_seconds",
            "checkpoint_count",
            "reserved_attempt_count",
            "completed_attempt_count",
            "instance_epoch_sha256",
            "request_count",
            "error_count",
            "error_rate",
            "latency_ms",
            "status_counts",
            "error_codes",
            "status",
        }
        if not isinstance(result, dict) or set(result) != required:
            raise ValueError("PERFORMANCE_STATE_INVALID")
        latency = result["latency_ms"]
        if (
            result["phase_id"] != phase.phase_id
            or result["mode"] != phase.mode
            or result["request_limit"] != phase.request_limit
            or result["request_count"] != phase.request_limit
            or result["reserved_attempt_count"] != phase.request_limit
            or result["completed_attempt_count"] != phase.request_limit
            or result["error_count"] != 0
            or result["error_rate"] != 0.0
            or not isinstance(latency, dict)
            or set(latency) != {"p50", "p95", "p99", "max"}
            or _count_mapping(result["status_counts"]).get("200")
            != phase.request_limit
            or _count_mapping(result["error_codes"])
            or _nonnegative_int(result["checkpoint_count"]) < phase.request_limit
            or not _valid_nonnegative_number(result["idle_elapsed_seconds"])
            or not _valid_nonnegative_number(result["active_elapsed_seconds"])
            or result["instance_epoch_sha256"] is not None
            and _SHA256_RE.fullmatch(result["instance_epoch_sha256"]) is None
            or any(_nonnegative_int(latency[key]) < 0 for key in latency)
            or not PerformanceAcceptanceRunner._phase_passed(phase, result)
        ):
            raise ValueError("PERFORMANCE_STATE_INVALID")

    @staticmethod
    def _validate_current_phase(phase: PhaseSpec, current: Any) -> None:
        required = {
            "phase_id",
            "idle_elapsed_seconds",
            "active_elapsed_seconds",
            "checkpoint_count",
            "safety_check_pending",
            "reserved_attempt_count",
            "completed_attempt_count",
            "instance_epoch_sha256",
            "fatal_code",
            "metrics",
        }
        if not isinstance(current, dict) or set(current) != required:
            raise ValueError("PERFORMANCE_STATE_INVALID")
        metrics = LatencyMetrics(current["metrics"])
        reserved = _nonnegative_int(current["reserved_attempt_count"])
        completed = _nonnegative_int(current["completed_attempt_count"])
        if (
            current["phase_id"] != phase.phase_id
            or type(current["safety_check_pending"]) is not bool
            or reserved > phase.request_limit
            or completed > reserved
            or reserved - completed > 1
            or metrics.request_count != completed
            or _nonnegative_int(current["checkpoint_count"]) < reserved
            or not _valid_nonnegative_number(current["idle_elapsed_seconds"])
            or not _valid_nonnegative_number(current["active_elapsed_seconds"])
            or current["instance_epoch_sha256"] is not None
            and _SHA256_RE.fullmatch(current["instance_epoch_sha256"]) is None
            or current["fatal_code"] is not None
            and (
                not isinstance(current["fatal_code"], str)
                or _ERROR_CODE_RE.fullmatch(current["fatal_code"]) is None
            )
        ):
            raise ValueError("PERFORMANCE_STATE_INVALID")

    def _phase_summary(
        self, phase: PhaseSpec, phase_state: Mapping[str, Any]
    ) -> dict[str, Any]:
        metrics = LatencyMetrics(phase_state["metrics"])
        return {
            "phase_id": phase.phase_id,
            "mode": phase.mode,
            "request_limit": phase.request_limit,
            "idle_elapsed_seconds": round(float(phase_state["idle_elapsed_seconds"]), 3),
            "active_elapsed_seconds": round(float(phase_state["active_elapsed_seconds"]), 3),
            "checkpoint_count": int(phase_state["checkpoint_count"]),
            "reserved_attempt_count": int(phase_state["reserved_attempt_count"]),
            "completed_attempt_count": int(phase_state["completed_attempt_count"]),
            "instance_epoch_sha256": phase_state["instance_epoch_sha256"],
            **metrics.summary(),
        }

    @staticmethod
    def _phase_passed(phase: PhaseSpec, summary: Mapping[str, Any]) -> bool:
        latency = summary.get("latency_ms")
        return (
            summary.get("request_count") == phase.request_limit
            and isinstance(latency, Mapping)
            and float(summary.get("error_rate", 1.0)) <= phase.max_error_rate
            and int(latency.get("p95", phase.max_p95_ms + 1)) <= phase.max_p95_ms
            and int(latency.get("p99", phase.max_p99_ms + 1)) <= phase.max_p99_ms
            and int(latency.get("max", phase.max_latency_ms + 1)) <= phase.max_latency_ms
            and float(summary.get("idle_elapsed_seconds", 0.0))
            >= phase.idle_before_seconds
        )

    def _evidence(self, state: Mapping[str, Any], *, idempotent: bool) -> dict[str, Any]:
        phase_results = list(state["phase_results"])
        total_requests = sum(int(item["request_count"]) for item in phase_results)
        total_errors = sum(int(item["error_count"]) for item in phase_results)
        epoch_values = {
            item.get("phase_id"): item.get("instance_epoch_sha256")
            for item in phase_results[:2]
        }
        epoch_changed = (
            len(epoch_values) == 2
            and all(isinstance(value, str) for value in epoch_values.values())
            and len(set(epoch_values.values())) == 2
        )
        capacity = state["capacity_preflight"]
        runtime_safety = state["runtime_safety"]
        if state["status"] == "PASSED" and not isinstance(runtime_safety, Mapping):
            raise ValueError("PERFORMANCE_RUNTIME_SAFETY_BLOCKED")
        abort_reason = next(
            (
                item.get("failure_code")
                for item in phase_results
                if item.get("status") == "FAILED"
            ),
            None,
        )
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "contract_id": CONTRACT_ID,
            "status": state["status"],
            "plan_sha256": state["plan_sha256"],
            "contract_sha256": state["contract_sha256"],
            "activation_hash": state["activation_hash"],
            "owner_approval_body_sha256": state["owner_approval_body_sha256"],
            "approved_capacity_preflight_sha256": state[
                "approved_capacity_preflight_sha256"
            ],
            "started_at_utc": state["started_at_utc"],
            "finished_at_utc": state["finished_at_utc"],
            "idempotent_readback": idempotent,
            "summary": {
                "phase_count": len(phase_results),
                "passed_phase_count": sum(
                    item.get("status") == "PASSED" for item in phase_results
                ),
                "total_request_count": total_requests,
                "total_error_count": total_errors,
                "request_limit": sum(phase.request_limit for phase in self._phases),
                "journal_event_count": state["journal_event_count"],
                "journal_head_sha256": state["journal_head_sha256"],
                "cold_start_classification": (
                    "VERIFIED" if epoch_changed else "INCONCLUSIVE"
                ),
                "instance_epoch_changed": epoch_changed,
            },
            "capacity_preflight": state["capacity_preflight"],
            "capacity_preflight_sha256": capacity["attestation_sha256"],
            "target_binding_sha256": state["target_binding_sha256"],
            "phase_plan_sha256": state["phase_plan_sha256"],
            "global_dispatch_count": total_requests,
            "global_dispatch_ceiling": _GLOBAL_REQUEST_LIMIT,
            "verified_request_allowance_fraction_used": capacity[
                "verified_request_allowance_fraction_used"
            ],
            "verified_resource_unit_allowance_fraction_used": capacity[
                "verified_resource_unit_allowance_fraction_used"
            ],
            "azure_execution_units_gb_seconds": (
                runtime_safety["observed_execution_units_gb_seconds"]
                if isinstance(runtime_safety, Mapping)
                else None
            ),
            "always_ready_units": (
                runtime_safety["always_ready_units"]
                if isinstance(runtime_safety, Mapping)
                else None
            ),
            "phase_aggregate_metrics": phase_results,
            "cold_start_classification": (
                "VERIFIED" if epoch_changed else "INCONCLUSIVE"
            ),
            "server_instance_or_start_epoch_changed": epoch_changed,
            "abort_reason_code": abort_reason,
            "phases": phase_results,
            "boundaries": {
                "workspace_id_sha256": _sha256_text(WORKSPACE_ID),
                "matter_id_sha256": _sha256_text(ALLOWED_MATTER_ID),
                "endpoint_sha256": _sha256_text(_ENDPOINT),
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
            "final_checkpoint_sha256": _sha256_json(state),
        }


class M365DelegatedTokenProvider:
    def __init__(
        self,
        runner: M365CliCommandRunner,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._runner = runner
        self._clock = clock or time.time
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            now = self._clock()
            if self._token is not None and self._expires_at - now >= 300:
                return self._token
            result = self._runner.run(
                (
                    "m365",
                    "util",
                    "accesstoken",
                    "get",
                    "--resource",
                    API_APP_URI,
                    "--new",
                    "--output",
                    "json",
                )
            )
            if result.returncode != 0:
                raise ValueError("PERFORMANCE_TOKEN_ACQUISITION_FAILED")
            token = _parse_token(result.stdout)
            claims = _jwt_claims(token)
            scopes = str(claims.get("scp", "")).split()
            expires_at = claims.get("exp")
            if (
                type(expires_at) is not int
                or expires_at - now < 300
                or "Matter.Read" not in scopes
                or claims.get("tid") != _EXPECTED_TENANT_ID
                or claims.get("aud") != API_APP_URI
            ):
                raise ValueError("PERFORMANCE_TOKEN_BINDING_INVALID")
            self._token = token
            self._expires_at = float(expires_at)
            return token


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class _RequestDeadlineExceeded(TimeoutError):
    pass


def _request_deadline_handler(_signum: int, _frame: Any) -> None:
    raise _RequestDeadlineExceeded("PERFORMANCE_REQUEST_DEADLINE_EXCEEDED")


class FixedBffPerformanceTransport:
    def __init__(
        self,
        token_provider: M365DelegatedTokenProvider,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        parsed = urllib.parse.urlsplit(_ENDPOINT)
        if (
            parsed.scheme != "https"
            or parsed.hostname != _FUNCTION_HOST
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise ValueError("PERFORMANCE_TARGET_INVALID")
        self._token_provider = token_provider
        self._clock = clock or time.perf_counter
        self._opener = urllib.request.build_opener(_NoRedirect())

    @property
    def target_binding_sha256(self) -> str:
        return build_performance_acceptance_plan("0" * 64, "0" * 64)[
            "target_binding_sha256"
        ]

    def request(self) -> PerformanceSample:
        try:
            token = self._token_provider.get_token()
        except Exception:
            return PerformanceSample(0, 0, False, "TOKEN_ACQUISITION_FAILED", True)
        request = urllib.request.Request(
            _ENDPOINT,
            method="GET",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "NaC-BFF-Performance-Acceptance/1",
            },
        )
        started = self._clock()
        if threading.current_thread() is not threading.main_thread():
            return PerformanceSample(
                0, 0, False, "TRANSPORT_DEADLINE_UNAVAILABLE", True
            )
        previous_handler = signal.getsignal(signal.SIGALRM)
        previous_timer = signal.getitimer(signal.ITIMER_REAL)
        if previous_timer != (0.0, 0.0):
            return PerformanceSample(
                0, 0, False, "TRANSPORT_DEADLINE_UNAVAILABLE", True
            )
        try:
            signal.signal(signal.SIGALRM, _request_deadline_handler)
            signal.setitimer(signal.ITIMER_REAL, _REQUEST_TIMEOUT_SECONDS)
            try:
                with self._opener.open(
                    request, timeout=_CONNECT_TIMEOUT_SECONDS
                ) as response:
                    status = int(response.status)
                    headers = {
                        key.lower(): value for key, value in response.headers.items()
                    }
                    payload = response.read(_MAX_RESPONSE_BYTES + 1)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0.0)
                signal.signal(signal.SIGALRM, previous_handler)
            latency_ms = max(0, int((self._clock() - started) * 1000))
        except _RequestDeadlineExceeded:
            latency_ms = max(0, int((self._clock() - started) * 1000))
            return PerformanceSample(
                0, latency_ms, False, "REQUEST_DEADLINE_EXCEEDED", True
            )
        except urllib.error.HTTPError as exc:
            latency_ms = max(0, int((self._clock() - started) * 1000))
            status = int(exc.code)
            fatal = status != 200
            code = (
                "UPSTREAM_THROTTLE_OR_UNAVAILABLE"
                if status in {429, 503}
                else "AUTHORIZATION_OR_TARGET_FAILURE"
                if status in {301, 302, 303, 307, 308, 401, 403, 404}
                else "HTTP_ERROR"
            )
            return PerformanceSample(status, latency_ms, False, code, fatal)
        except Exception:
            latency_ms = max(0, int((self._clock() - started) * 1000))
            return PerformanceSample(0, latency_ms, False, "TRANSPORT_ERROR", True)
        if status != 200:
            fatal = True
            return PerformanceSample(status, latency_ms, False, "HTTP_STATUS_INVALID", fatal)
        if len(payload) > _MAX_RESPONSE_BYTES:
            return PerformanceSample(status, latency_ms, False, "RESPONSE_TOO_LARGE", True)
        content_type = headers.get("content-type", "").lower()
        if headers.get("location") is not None:
            return PerformanceSample(status, latency_ms, False, "REDIRECT_SIGNAL", True)
        if content_type != "application/json; charset=utf-8" or any(
            headers.get(name, "").lower() != expected
            for name, expected in _SAFE_HEADERS.items()
        ):
            return PerformanceSample(status, latency_ms, False, "RESPONSE_HEADERS_INVALID", True)
        instance_epoch = headers.get(_INSTANCE_EPOCH_HEADER)
        if (
            not isinstance(instance_epoch, str)
            or re.fullmatch(r"[0-9a-f]{32}", instance_epoch) is None
        ):
            return PerformanceSample(status, latency_ms, False, "INSTANCE_EPOCH_MISSING", True)
        try:
            value = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return PerformanceSample(status, latency_ms, False, "RESPONSE_JSON_INVALID", True)
        if not _valid_workspace_response(value):
            return PerformanceSample(status, latency_ms, False, "RESPONSE_SCOPE_INVALID", True)
        return PerformanceSample(
            status,
            latency_ms,
            True,
            instance_epoch_sha256=_sha256_text(instance_epoch),
        )


class PerformanceArtifactStore:
    def __init__(self, repo_root: Path, plan_sha256: str) -> None:
        _require_sha256(plan_sha256, "plan_sha256")
        self.run_dir = (repo_root / OUTPUT_ROOT / plan_sha256).resolve()
        expected_root = (repo_root / OUTPUT_ROOT).resolve()
        if expected_root not in self.run_dir.parents:
            raise ValueError("PERFORMANCE_OUTPUT_PATH_INVALID")
        self.state_path = self.run_dir / "state.redacted.json"
        self.state_digest_path = self.run_dir / "state.redacted.sha256"
        self.state_commit_path = self.run_dir / "state.commit.redacted.json"
        self._state_slots = {
            "a": self.run_dir / "state.slot-a.redacted.json",
            "b": self.run_dir / "state.slot-b.redacted.json",
        }
        self.evidence_path = self.run_dir / "evidence.redacted.json"
        self.report_path = self.run_dir / "report.redacted.md"

    def load_state(self) -> dict[str, Any] | None:
        commit = _read_secure_json(self.state_commit_path)
        if commit is None:
            return None
        if (
            set(commit) != {"schema_version", "slot", "state_sha256"}
            or commit.get("schema_version") != "nac.performance-checkpoint-commit/v1"
            or commit.get("slot") not in self._state_slots
            or not isinstance(commit.get("state_sha256"), str)
            or _SHA256_RE.fullmatch(commit["state_sha256"]) is None
        ):
            raise ValueError("PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID")
        state = _read_secure_json(self._state_slots[commit["slot"]])
        if state is None or commit["state_sha256"] != _sha256_json(state):
            raise ValueError("PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID")
        return state

    def write_state(self, state: Mapping[str, Any]) -> None:
        current = _read_secure_json(self.state_commit_path)
        if current is not None and (
            not isinstance(current, dict)
            or current.get("slot") not in self._state_slots
        ):
            raise ValueError("PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID")
        slot = "b" if isinstance(current, dict) and current.get("slot") == "a" else "a"
        digest = _sha256_json(state)
        _atomic_json_write(self._state_slots[slot], state)
        _atomic_json_write(
            self.state_commit_path,
            {
                "schema_version": "nac.performance-checkpoint-commit/v1",
                "slot": slot,
                "state_sha256": digest,
            },
        )
        # These are human-readable mirrors; the commit pointer above is authoritative.
        _atomic_json_write(self.state_path, state)
        _atomic_text_write(self.state_digest_path, digest + "\n")

    def state_sha256(self) -> str | None:
        commit = _read_secure_json(self.state_commit_path)
        if commit is None:
            return None
        digest = commit.get("state_sha256")
        if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
            raise ValueError("PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID")
        return digest

    def write_evidence(self, evidence: Mapping[str, Any]) -> None:
        _validate_redacted_evidence(evidence)
        state = self.load_state()
        if (
            state is None
            or evidence.get("final_checkpoint_sha256") != self.state_sha256()
        ):
            raise ValueError("PERFORMANCE_EVIDENCE_STATE_BINDING_INVALID")
        _validate_evidence_state_binding(evidence, state)
        _atomic_json_write(self.evidence_path, evidence)
        report = _markdown_report(evidence)
        _atomic_text_write(self.report_path, report)


def validate_correlation_id(value: str) -> str:
    if not isinstance(value, str) or _CORRELATION_RE.fullmatch(value) is None:
        raise ValueError("PERFORMANCE_CORRELATION_ID_INVALID")
    return value


def _valid_workspace_response(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    try:
        validated = validate_workbench_projection(value)
    except WorkbenchProjectionError:
        return False
    return (
        validated["scope"]["workspaceId"] == WORKSPACE_ID
        and validated["scope"]["matterId"] == ALLOWED_MATTER_ID
        and validated["scope"]["purpose"] == ALLOWED_PURPOSE
        and validated["access"]["mode"] == "assigned"
    )


def _same_capacity_policy(
    previous: Mapping[str, Any], refreshed: Mapping[str, Any]
) -> bool:
    stable_keys = {
        "status",
        "sharepoint_tier_id_sha256",
        "request_allowance_window_seconds",
        "resource_unit_allowance_window_seconds",
        "maximum_dispatches_per_minute",
        "projected_request_count",
        "projected_resource_units",
        "projected_execution_units_gb_seconds",
        "projected_request_units_per_bff_request",
        "maximum_capacity_fraction",
        "always_ready_units",
    }
    return all(previous.get(key) == refreshed.get(key) for key in stable_keys)


def _validate_evidence_state_binding(
    evidence: Mapping[str, Any], state: Mapping[str, Any]
) -> None:
    phases = state.get("phase_results")
    capacity = state.get("capacity_preflight")
    runtime_safety = state.get("runtime_safety")
    if not isinstance(phases, list) or not isinstance(capacity, Mapping):
        raise ValueError("PERFORMANCE_EVIDENCE_STATE_BINDING_INVALID")
    total_requests = sum(int(item.get("request_count", 0)) for item in phases)
    total_errors = sum(int(item.get("error_count", 0)) for item in phases)
    epoch_values = [item.get("instance_epoch_sha256") for item in phases[:2]]
    epoch_changed = (
        len(epoch_values) == 2
        and all(isinstance(value, str) for value in epoch_values)
        and len(set(epoch_values)) == 2
    )
    abort_reason = next(
        (
            item.get("failure_code")
            for item in phases
            if item.get("status") == "FAILED"
        ),
        None,
    )
    expected_summary = {
        "phase_count": len(phases),
        "passed_phase_count": sum(
            item.get("status") == "PASSED" for item in phases
        ),
        "total_request_count": total_requests,
        "total_error_count": total_errors,
        "request_limit": sum(int(item.get("request_limit", 0)) for item in phases),
        "journal_event_count": state.get("journal_event_count"),
        "journal_head_sha256": state.get("journal_head_sha256"),
        "cold_start_classification": (
            "VERIFIED" if epoch_changed else "INCONCLUSIVE"
        ),
        "instance_epoch_changed": epoch_changed,
    }
    direct_bindings = {
        "status": state.get("status"),
        "plan_sha256": state.get("plan_sha256"),
        "contract_sha256": state.get("contract_sha256"),
        "activation_hash": state.get("activation_hash"),
        "owner_approval_body_sha256": state.get("owner_approval_body_sha256"),
        "approved_capacity_preflight_sha256": state.get(
            "approved_capacity_preflight_sha256"
        ),
        "started_at_utc": state.get("started_at_utc"),
        "finished_at_utc": state.get("finished_at_utc"),
        "summary": expected_summary,
        "capacity_preflight": capacity,
        "capacity_preflight_sha256": capacity.get("attestation_sha256"),
        "target_binding_sha256": state.get("target_binding_sha256"),
        "phase_plan_sha256": state.get("phase_plan_sha256"),
        "global_dispatch_count": total_requests,
        "global_dispatch_ceiling": _GLOBAL_REQUEST_LIMIT,
        "verified_request_allowance_fraction_used": capacity.get(
            "verified_request_allowance_fraction_used"
        ),
        "verified_resource_unit_allowance_fraction_used": capacity.get(
            "verified_resource_unit_allowance_fraction_used"
        ),
        "azure_execution_units_gb_seconds": (
            runtime_safety.get("observed_execution_units_gb_seconds")
            if isinstance(runtime_safety, Mapping)
            else None
        ),
        "always_ready_units": (
            runtime_safety.get("always_ready_units")
            if isinstance(runtime_safety, Mapping)
            else None
        ),
        "phase_aggregate_metrics": phases,
        "cold_start_classification": (
            "VERIFIED" if epoch_changed else "INCONCLUSIVE"
        ),
        "server_instance_or_start_epoch_changed": epoch_changed,
        "abort_reason_code": abort_reason,
        "phases": phases,
        "final_checkpoint_sha256": _sha256_json(state),
    }
    for key, value in direct_bindings.items():
        if evidence.get(key) != value:
            raise ValueError(
                f"PERFORMANCE_EVIDENCE_STATE_BINDING_INVALID:{key}"
            )
    if evidence.get("idempotent_readback") is True and state.get("status") != "PASSED":
        raise ValueError("PERFORMANCE_EVIDENCE_STATE_BINDING_INVALID")


def _validate_runtime_safety_summary(
    value: Mapping[str, Any], *, capacity: Any
) -> None:
    required = {
        "status",
        "observed_execution_units_gb_seconds",
        "always_ready_units",
        "telemetry_cap_reached",
        "monitor_evidence_sha256",
        "lease_evidence_sha256",
        "capacity_attestation_sha256",
        "observed_at_utc_sha256",
    }
    if (
        not isinstance(capacity, Mapping)
        or set(value) != required
        or value.get("status") != "PASSED"
        or not _valid_nonnegative_number(
            value.get("observed_execution_units_gb_seconds")
        )
        or float(value["observed_execution_units_gb_seconds"])
        > _MAX_EXECUTION_UNITS_GB_SECONDS
        or value.get("always_ready_units") != 0
        or value.get("telemetry_cap_reached") is not False
        or any(
            not isinstance(capacity.get(key), str)
            or _SHA256_RE.fullmatch(capacity[key]) is None
            for key in ("source_evidence_sha256", "monitor_evidence_sha256")
        )
        or capacity.get("monitor_evidence_sha256")
        == capacity.get("source_evidence_sha256")
        or value.get("monitor_evidence_sha256")
        == capacity.get("source_evidence_sha256")
        or value.get("lease_evidence_sha256")
        != capacity.get("lease_evidence_sha256")
        or value.get("capacity_attestation_sha256")
        != capacity.get("attestation_sha256")
        or any(
            not isinstance(value.get(key), str)
            or _SHA256_RE.fullmatch(value[key]) is None
            for key in (
                "monitor_evidence_sha256",
                "lease_evidence_sha256",
                "capacity_attestation_sha256",
                "observed_at_utc_sha256",
            )
        )
    ):
        raise ValueError("PERFORMANCE_STATE_INVALID")


def _validate_redacted_evidence(evidence: Mapping[str, Any]) -> None:
    top_level = {
        "schema_version",
        "contract_id",
        "status",
        "plan_sha256",
        "contract_sha256",
        "activation_hash",
        "owner_approval_body_sha256",
        "approved_capacity_preflight_sha256",
        "started_at_utc",
        "finished_at_utc",
        "idempotent_readback",
        "summary",
        "capacity_preflight",
        "capacity_preflight_sha256",
        "target_binding_sha256",
        "phase_plan_sha256",
        "global_dispatch_count",
        "global_dispatch_ceiling",
        "verified_request_allowance_fraction_used",
        "verified_resource_unit_allowance_fraction_used",
        "azure_execution_units_gb_seconds",
        "always_ready_units",
        "phase_aggregate_metrics",
        "cold_start_classification",
        "server_instance_or_start_epoch_changed",
        "abort_reason_code",
        "phases",
        "boundaries",
        "redaction",
        "final_checkpoint_sha256",
    }
    summary_keys = {
        "phase_count",
        "passed_phase_count",
        "total_request_count",
        "total_error_count",
        "request_limit",
        "journal_event_count",
        "journal_head_sha256",
        "cold_start_classification",
        "instance_epoch_changed",
    }
    boundary_keys = {
        "workspace_id_sha256",
        "matter_id_sha256",
        "endpoint_sha256",
        "raw_token_count",
        "raw_response_body_count",
        "tenant_write_count",
        "infrastructure_restart_count",
        "credential_change_count",
        "permission_change_count",
        "automatic_rollback_count",
        "automatic_deletion_count",
    }
    redaction_keys = {
        "aggregated_metrics_only",
        "contains_tokens",
        "contains_response_bodies",
        "contains_urls",
        "contains_tenant_or_user_ids",
        "contains_correlation_ids",
    }
    capacity_keys = {
        "status",
        "sharepoint_tier_id_sha256",
        "request_allowance_window_seconds",
        "resource_unit_allowance_window_seconds",
        "maximum_dispatches_per_minute",
        "baseline_request_count",
        "baseline_resource_units",
        "projected_request_count",
        "projected_resource_units",
        "verified_request_allowance_fraction_used",
        "verified_resource_unit_allowance_fraction_used",
        "projected_request_units_per_bff_request",
        "maximum_capacity_fraction",
        "always_ready_units",
        "azure_execution_units_gb_seconds",
        "projected_execution_units_gb_seconds",
        "execution_units_below_cap",
        "telemetry_cap_reached",
        "source_evidence_sha256",
        "monitor_evidence_sha256",
        "lease_evidence_sha256",
        "attestation_sha256",
    }
    if (
        not isinstance(evidence, Mapping)
        or set(evidence) != top_level
        or evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION
        or evidence.get("contract_id") != CONTRACT_ID
        or evidence.get("status") not in {"PASSED", "FAILED"}
        or any(
            not isinstance(evidence.get(key), str)
            or _SHA256_RE.fullmatch(evidence[key]) is None
            for key in (
                "plan_sha256",
                "contract_sha256",
                "activation_hash",
                "owner_approval_body_sha256",
                "approved_capacity_preflight_sha256",
                "capacity_preflight_sha256",
                "target_binding_sha256",
                "phase_plan_sha256",
                "final_checkpoint_sha256",
            )
        )
        or evidence.get("cold_start_classification")
        not in {"VERIFIED", "INCONCLUSIVE"}
        or evidence.get("cold_start_classification")
        != evidence.get("summary", {}).get("cold_start_classification")
        or not isinstance(evidence.get("summary"), Mapping)
        or set(evidence["summary"]) != summary_keys
        or not isinstance(evidence.get("boundaries"), Mapping)
        or set(evidence["boundaries"]) != boundary_keys
        or not isinstance(evidence.get("redaction"), Mapping)
        or set(evidence["redaction"]) != redaction_keys
        or not isinstance(evidence.get("capacity_preflight"), Mapping)
        or set(evidence["capacity_preflight"]) != capacity_keys
        or any(
            not isinstance(evidence["capacity_preflight"].get(key), str)
            or _SHA256_RE.fullmatch(evidence["capacity_preflight"][key]) is None
            for key in (
                "source_evidence_sha256",
                "monitor_evidence_sha256",
                "lease_evidence_sha256",
                "attestation_sha256",
            )
        )
        or evidence["capacity_preflight"].get("monitor_evidence_sha256")
        == evidence["capacity_preflight"].get("source_evidence_sha256")
        or evidence.get("phases") != evidence.get("phase_aggregate_metrics")
        or evidence["redaction"]
        != {
            "aggregated_metrics_only": True,
            "contains_tokens": False,
            "contains_response_bodies": False,
            "contains_urls": False,
            "contains_tenant_or_user_ids": False,
            "contains_correlation_ids": False,
        }
        or any(
            evidence["boundaries"].get(key) != 0
            for key in boundary_keys
            if key.endswith("_count")
        )
    ):
        raise ValueError("PERFORMANCE_EVIDENCE_REDACTION_INVALID")
    phases = evidence["phases"]
    if not isinstance(phases, list) or any(
        not _valid_redacted_phase_aggregate(phase) for phase in phases
    ):
        raise ValueError("PERFORMANCE_EVIDENCE_REDACTION_INVALID")
    summary = evidence["summary"]
    total_requests = sum(int(phase["request_count"]) for phase in phases)
    total_errors = sum(int(phase["error_count"]) for phase in phases)
    passed_phases = sum(phase["status"] == "PASSED" for phase in phases)
    journal_events = sum(
        int(phase["reserved_attempt_count"])
        + int(phase["completed_attempt_count"])
        for phase in phases
    )
    capacity = evidence["capacity_preflight"]
    passed = evidence["status"] == "PASSED"
    if (
        summary.get("phase_count") != len(phases)
        or summary.get("passed_phase_count") != passed_phases
        or summary.get("total_request_count") != total_requests
        or summary.get("total_error_count") != total_errors
        or summary.get("journal_event_count") != journal_events
        or evidence.get("global_dispatch_count") != total_requests
        or evidence.get("global_dispatch_ceiling") != _GLOBAL_REQUEST_LIMIT
        or total_requests > _GLOBAL_REQUEST_LIMIT
        or evidence.get("capacity_preflight_sha256")
        != capacity.get("attestation_sha256")
        or evidence.get("verified_request_allowance_fraction_used")
        != capacity.get("verified_request_allowance_fraction_used")
        or evidence.get("verified_resource_unit_allowance_fraction_used")
        != capacity.get("verified_resource_unit_allowance_fraction_used")
        or passed
        and (
            evidence.get("always_ready_units") != 0
            or not _valid_nonnegative_number(
                evidence.get("azure_execution_units_gb_seconds")
            )
            or float(evidence["azure_execution_units_gb_seconds"])
            > _MAX_EXECUTION_UNITS_GB_SECONDS
        )
        or not passed
        and (
            evidence.get("always_ready_units") not in {None, 0}
            or evidence.get("azure_execution_units_gb_seconds") is not None
            and (
                not _valid_nonnegative_number(
                    evidence.get("azure_execution_units_gb_seconds")
                )
                or float(evidence["azure_execution_units_gb_seconds"])
                > _MAX_EXECUTION_UNITS_GB_SECONDS
            )
        )
        or any(
            int(phase["reserved_attempt_count"])
            != int(phase["completed_attempt_count"])
            or int(phase["completed_attempt_count"])
            != int(phase["request_count"])
            or sum(int(count) for count in phase["status_counts"].values())
            != int(phase["request_count"])
            or abs(
                float(phase["error_rate"])
                - (
                    int(phase["error_count"])
                    / max(1, int(phase["request_count"]))
                )
            )
            > 1e-9
            or (
                phase["status"] == "PASSED"
                and (
                    int(phase["request_count"]) != int(phase["request_limit"])
                    or int(phase["error_count"]) != 0
                    or "failure_code" in phase
                )
            )
            or (
                phase["status"] == "FAILED"
                and "failure_code" not in phase
            )
            for phase in phases
        )
        or passed
        and (
            passed_phases != len(phases)
            or total_errors != 0
            or evidence.get("abort_reason_code") is not None
            or total_requests != _GLOBAL_REQUEST_LIMIT
            or summary.get("request_limit") != _GLOBAL_REQUEST_LIMIT
            or [phase.get("phase_id") for phase in phases]
            != [phase.phase_id for phase in PHASES]
            or [phase.get("request_limit") for phase in phases]
            != [phase.request_limit for phase in PHASES]
            or any(
                not _canonical_passed_phase_matches(spec, aggregate)
                for spec, aggregate in zip(PHASES, phases)
            )
        )
        or not passed
        and (
            passed_phases == len(phases)
            or evidence.get("abort_reason_code") is None
        )
    ):
        raise ValueError("PERFORMANCE_EVIDENCE_REDACTION_INVALID")
    raw = _canonical_json(evidence)
    forbidden = (
        "Bearer ",
        "http://",
        "https://",
        _EXPECTED_TENANT_ID,
        "@funktion8.de",
    )
    if any(value.lower() in raw.lower() for value in forbidden):
        raise ValueError("PERFORMANCE_EVIDENCE_REDACTION_INVALID")
    if _contains_sensitive_string(evidence):
        raise ValueError("PERFORMANCE_EVIDENCE_REDACTION_INVALID")


def _canonical_passed_phase_matches(
    spec: PhaseSpec, aggregate: Mapping[str, Any]
) -> bool:
    latency = aggregate.get("latency_ms")
    active_duration_bounded = spec.phase_id not in {
        "capacity_bounded_volume",
        "sustained_2h",
        "soak_24h",
    } or float(aggregate.get("active_elapsed_seconds", float("inf"))) <= (
        spec.duration_seconds + 0.001
    )
    return (
        isinstance(latency, Mapping)
        and aggregate.get("mode") == spec.mode
        and float(aggregate.get("error_rate", 1.0)) <= spec.max_error_rate
        and int(latency.get("p95", spec.max_p95_ms + 1)) <= spec.max_p95_ms
        and int(latency.get("p99", spec.max_p99_ms + 1)) <= spec.max_p99_ms
        and int(latency.get("max", spec.max_latency_ms + 1))
        <= spec.max_latency_ms
        and float(aggregate.get("idle_elapsed_seconds", -1.0))
        >= spec.idle_before_seconds
        and active_duration_bounded
    )


def _valid_redacted_phase_aggregate(value: Any) -> bool:
    common = {
        "phase_id",
        "mode",
        "request_limit",
        "idle_elapsed_seconds",
        "active_elapsed_seconds",
        "checkpoint_count",
        "reserved_attempt_count",
        "completed_attempt_count",
        "instance_epoch_sha256",
        "request_count",
        "error_count",
        "error_rate",
        "latency_ms",
        "status_counts",
        "error_codes",
        "status",
    }
    if not isinstance(value, dict) or frozenset(value) not in {
        frozenset(common),
        frozenset(common | {"failure_code"}),
    }:
        return False
    latency = value.get("latency_ms")
    status_counts = value.get("status_counts")
    error_codes = value.get("error_codes")
    integer_fields = (
        "request_limit",
        "checkpoint_count",
        "reserved_attempt_count",
        "completed_attempt_count",
        "request_count",
        "error_count",
    )
    if (
        not isinstance(value.get("phase_id"), str)
        or re.fullmatch(r"[a-z][a-z0-9_]{1,79}", value["phase_id"]) is None
        or value.get("mode") != "paced"
        or value.get("status") not in {"PASSED", "FAILED"}
        or not isinstance(status_counts, dict)
        or any(
            not isinstance(key, str)
            or re.fullmatch(r"(?:[1-5][0-9]{2}|transport)", key) is None
            for key in status_counts
        )
        or any(type(count) is not int or count < 0 for count in status_counts.values())
        or not isinstance(error_codes, dict)
        or any(_ERROR_CODE_RE.fullmatch(key) is None for key in error_codes)
        or any(type(count) is not int or count < 0 for count in error_codes.values())
        or not isinstance(latency, dict)
        or set(latency) != {"p50", "p95", "p99", "max"}
        or any(type(item) is not int or item < 0 for item in latency.values())
        or any(type(value.get(field)) is not int or value[field] < 0 for field in integer_fields)
        or not _valid_nonnegative_number(value.get("idle_elapsed_seconds"))
        or not _valid_nonnegative_number(value.get("active_elapsed_seconds"))
        or not _valid_nonnegative_number(value.get("error_rate"))
        or (
            value.get("instance_epoch_sha256") is not None
            and (
                not isinstance(value["instance_epoch_sha256"], str)
                or _SHA256_RE.fullmatch(value["instance_epoch_sha256"]) is None
            )
        )
        or (
            "failure_code" in value
            and _ERROR_CODE_RE.fullmatch(value["failure_code"]) is None
        )
    ):
        return False
    return True


def _contains_sensitive_string(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _contains_sensitive_string(key) or _contains_sensitive_string(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_sensitive_string(item) for item in value)
    if not isinstance(value, str):
        return False
    return (
        _JWT_RE.search(value) is not None
        or re.search(
            r"(?i)(?:bearer\s+|authorization|cookie|client[_-]?secret|private[_-]?key)",
            value,
        )
        is not None
        or re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", value)
        is not None
        or re.search(
            r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
            r"[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
            value,
        )
        is not None
    )


def _parse_token(value: str) -> str:
    raw = value.strip()
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        decoded = raw
    if isinstance(decoded, dict):
        decoded = decoded.get("accessToken") or decoded.get("token")
    if (
        not isinstance(decoded, str)
        or len(decoded) > 32_768
        or _JWT_RE.fullmatch(decoded) is None
    ):
        raise ValueError("PERFORMANCE_TOKEN_INVALID")
    return decoded


def _jwt_claims(token: str) -> dict[str, Any]:
    try:
        encoded = token.split(".", 2)[1]
        padding = "=" * (-len(encoded) % 4)
        claims = json.loads(base64.urlsafe_b64decode(encoded + padding))
    except Exception:
        raise ValueError("PERFORMANCE_TOKEN_INVALID") from None
    if not isinstance(claims, dict):
        raise ValueError("PERFORMANCE_TOKEN_INVALID")
    return claims


def _markdown_report(evidence: Mapping[str, Any]) -> str:
    summary = evidence.get("summary", {})
    lines = [
        "# NaC BFF Performance Acceptance",
        "",
        f"- Status: `{evidence.get('status', 'UNKNOWN')}`",
        f"- Plan SHA-256: `{evidence.get('plan_sha256', '')}`",
        f"- Activation SHA-256: `{evidence.get('activation_hash', '')}`",
        f"- Requests: `{summary.get('total_request_count', 0)}`",
        f"- Errors: `{summary.get('total_error_count', 0)}`",
        "- Cold-start classification: "
        f"`{summary.get('cold_start_classification', 'INCONCLUSIVE')}`",
        "- Instance epoch changed: "
        f"`{str(summary.get('instance_epoch_changed', False)).lower()}`",
        "",
        "| Phase | Status | Requests | Errors | p95 ms | p99 ms |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for phase in evidence.get("phases", []):
        latency = phase.get("latency_ms", {})
        lines.append(
            f"| {phase.get('phase_id', '')} | {phase.get('status', '')} | "
            f"{phase.get('request_count', 0)} | {phase.get('error_count', 0)} | "
            f"{latency.get('p95', 0)} | {latency.get('p99', 0)} |"
        )
    return "\n".join(lines) + "\n"


def _read_secure_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        metadata = path.lstat()
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_mode & 0o077
            or metadata.st_size > 8 * 1024 * 1024
        ):
            raise ValueError
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        raise ValueError("PERFORMANCE_STATE_INVALID") from None
    if not isinstance(value, dict):
        raise ValueError("PERFORMANCE_STATE_INVALID")
    return value


def _read_secure_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        metadata = path.lstat()
        value = path.read_text(encoding="ascii").strip()
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or metadata.st_mode & 0o077
            or metadata.st_size > 128
            or _SHA256_RE.fullmatch(value) is None
        ):
            raise ValueError
    except (OSError, UnicodeError, ValueError):
        raise ValueError("PERFORMANCE_CHECKPOINT_INTEGRITY_INVALID") from None
    return value


def _atomic_json_write(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_text_write(path, _canonical_json(value) + "\n")


def _atomic_text_write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256")


def _nonnegative_int(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("PERFORMANCE_STATE_INVALID")
    return value


def _valid_nonnegative_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and float(value) >= 0.0
        and float(value) != float("inf")
    )


def _safe_aggregate_error_code(value: Any) -> str:
    if isinstance(value, str) and _ERROR_CODE_RE.fullmatch(value) is not None:
        return value
    return "UNSAFE_ERROR_CODE_REDACTED"


def _safe_runtime_abort_code(error: Exception) -> str:
    value = str(error)
    if _ERROR_CODE_RE.fullmatch(value) is not None:
        return value
    return "PERFORMANCE_RUNTIME_SAFETY_BLOCKED"


def _count_mapping(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("PERFORMANCE_STATE_INVALID")
    result: dict[str, int] = {}
    for key, count in value.items():
        if not isinstance(key, str):
            raise ValueError("PERFORMANCE_STATE_INVALID")
        result[key] = _nonnegative_int(count)
    return result


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED") from None
    if parsed.tzinfo is None:
        raise ValueError("PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED")
    return parsed.astimezone(UTC)


__all__ = [
    "BoundPerformanceAuthorizationVerifier",
    "CapacityAttestation",
    "CONTRACT_ID",
    "CONTRACT_RELATIVE_PATH",
    "EVIDENCE_SCHEMA_VERSION",
    "FixedBffPerformanceTransport",
    "FixedTransportBindingVerifier",
    "LIVE_COMMAND",
    "LatencyMetrics",
    "M365DelegatedTokenProvider",
    "OUTPUT_ROOT",
    "OWNER_ACTION",
    "PHASES",
    "PLAN_COMMAND",
    "PLAN_SCHEMA_VERSION",
    "PerformanceAcceptanceRunner",
    "PerformanceArtifactStore",
    "PerformanceExecutionAuthorization",
    "PerformanceSample",
    "PhaseSpec",
    "REQUIRED_OWNER_LOGIN",
    "RuntimeSafetyObservation",
    "STATE_SCHEMA_VERSION",
    "TOTAL_REQUEST_LIMIT",
    "build_owner_comment",
    "build_performance_acceptance_plan",
    "validate_correlation_id",
    "verify_activation_success",
    "verify_performance_execution_authorization",
]
