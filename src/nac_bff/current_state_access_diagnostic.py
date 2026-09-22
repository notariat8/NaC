from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping


SPFX_SUBJECT_MISSING = "SPFX_SUBJECT_MISSING"
BFF_REQUEST_NOT_OBSERVED = "BFF_REQUEST_NOT_OBSERVED"
BFF_AUTHENTICATION_REJECTED_401 = "BFF_AUTHENTICATION_REJECTED_401"
BFF_AUTHORIZATION_REJECTED_403 = "BFF_AUTHORIZATION_REJECTED_403"

DIAGNOSTIC_CLASSES = frozenset(
    {
        SPFX_SUBJECT_MISSING,
        BFF_REQUEST_NOT_OBSERVED,
        BFF_AUTHENTICATION_REJECTED_401,
        BFF_AUTHORIZATION_REJECTED_403,
    }
)
OBSERVATION_KEYS = frozenset(
    {
        "spfx_subject_available",
        "matching_bff_request_observed",
        "bff_http_class",
        "delegated_scope_contract_matches",
        "access_decision_evidence_matches",
    }
)
TARGET_KEYS = frozenset({"workspace_id", "app_id"})
BINDING_KEYS = frozenset(
    {
        "final_head_sha256",
        "final_tree_sha256",
        "contract_sha256",
        "resolver_sha256",
        "account_run_binding",
        "principal_run_binding",
        "dpa_avv_binding_sha256",
    }
)
WINDOW_KEYS = frozenset(
    {
        "start_utc",
        "end_utc",
        "window_binding_sha256",
        "client_receipt_sha256",
        "request_correlation_binding_sha256",
    }
)
SIDE_EFFECT_KEYS = frozenset(
    {
        "port_factory",
        "network_read",
        "run_gate_consume_write",
        "result_evidence_write",
        "login",
        "device_code",
        "browser_authentication",
        "token_refresh",
        "token_import",
        "credential_export",
        "credential_write",
        "cache_write",
        "configuration_write",
        "redirect_follow",
        "retry",
        "second_real_run",
        "tenant_write",
        "provider_write",
        "deployment",
        "issue_739_release",
        "issue_632_authorization",
    }
)
ALLOWED_NONZERO_COUNTERS_BY_CLASS = {
    SPFX_SUBJECT_MISSING: {
        "port_factory": 1,
        "network_read": 2,
        "run_gate_consume_write": 1,
        "result_evidence_write": 1,
    },
    BFF_REQUEST_NOT_OBSERVED: {
        "port_factory": 1,
        "network_read": 6,
        "run_gate_consume_write": 1,
        "result_evidence_write": 1,
    },
    BFF_AUTHENTICATION_REJECTED_401: {
        "port_factory": 1,
        "network_read": 6,
        "run_gate_consume_write": 1,
        "result_evidence_write": 1,
    },
    BFF_AUTHORIZATION_REJECTED_403: {
        "port_factory": 1,
        "network_read": 6,
        "run_gate_consume_write": 1,
        "result_evidence_write": 1,
    },
}
_HEX64 = re.compile(r"[0-9a-f]{64}")


class DiagnosticBlockedError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _closed_mapping(
    value: Mapping[str, Any], keys: frozenset[str], code: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or frozenset(value) != keys:
        raise DiagnosticBlockedError(code)
    return MappingProxyType(dict(value))


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    # The contract permits only strings, booleans and integers; for this closed
    # domain, sorted compact JSON is the RFC 8785 representation.
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DiagnosticBlockedError("BLOCKED_TIMESTAMP_INVALID")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DiagnosticBlockedError("BLOCKED_TIMESTAMP_INVALID") from exc


def classify_observations(observations: Mapping[str, Any]) -> str:
    observations = _closed_mapping(
        observations, OBSERVATION_KEYS, "BLOCKED_OBSERVATION_SCHEMA"
    )
    booleans = (
        observations["spfx_subject_available"],
        observations["matching_bff_request_observed"],
        observations["delegated_scope_contract_matches"],
        observations["access_decision_evidence_matches"],
    )
    if not all(type(value) is bool for value in booleans):
        raise DiagnosticBlockedError("BLOCKED_OBSERVATION_TYPE")
    http_class = observations["bff_http_class"]
    if http_class not in {"none", "401", "403"}:
        raise DiagnosticBlockedError("BLOCKED_HTTP_CLASS")
    subject = observations["spfx_subject_available"]
    request = observations["matching_bff_request_observed"]
    if subject is False and request is False and http_class == "none":
        return SPFX_SUBJECT_MISSING
    if (
        observations["delegated_scope_contract_matches"] is not True
        or observations["access_decision_evidence_matches"] is not True
    ):
        raise DiagnosticBlockedError("BLOCKED_CONTRACT_EVIDENCE_MISMATCH")
    if subject is True and request is False and http_class == "none":
        return BFF_REQUEST_NOT_OBSERVED
    if subject is True and request is True and http_class == "401":
        return BFF_AUTHENTICATION_REJECTED_401
    if subject is True and request is True and http_class == "403":
        return BFF_AUTHORIZATION_REJECTED_403
    raise DiagnosticBlockedError("BLOCKED_AMBIGUOUS_DIAGNOSIS")


@dataclass(frozen=True)
class DecisionProjection:
    target: Mapping[str, Any]
    bindings: Mapping[str, Any]
    observation_window: Mapping[str, Any]
    observations: Mapping[str, Any]
    classification: str
    side_effect_counters: Mapping[str, int]

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "target": dict(self.target),
            "bindings": dict(self.bindings),
            "observation_window": dict(self.observation_window),
            "observations": dict(self.observations),
            "classification": self.classification,
            "side_effect_counters": dict(self.side_effect_counters),
        }


@dataclass(frozen=True)
class AcquisitionEnvelope:
    sequence: int
    acquired_at_utc: str
    provider_read_receipt_sha256: str
    port_receipt_sha256: tuple[str, ...] = ()


@dataclass(frozen=True)
class DiagnosticSnapshot:
    schema_version: str
    acquisition_envelope: AcquisitionEnvelope
    decision_projection: DecisionProjection
    decision_projection_sha256: str


def build_decision_projection(
    *,
    target: Mapping[str, Any],
    bindings: Mapping[str, Any],
    observation_window: Mapping[str, Any],
    observations: Mapping[str, Any],
    side_effect_counters: Mapping[str, int],
) -> DecisionProjection:
    target = _closed_mapping(target, TARGET_KEYS, "BLOCKED_TARGET_SCHEMA")
    if dict(target) != {
        "workspace_id": "notary_team_01",
        "app_id": "nac-vorgangsansicht",
    }:
        raise DiagnosticBlockedError("BLOCKED_TARGET_BINDING")
    bindings = _closed_mapping(bindings, BINDING_KEYS, "BLOCKED_BINDING_SCHEMA")
    digest_keys = BINDING_KEYS - {"account_run_binding", "principal_run_binding"}
    if not all(
        isinstance(bindings[key], str) and _HEX64.fullmatch(bindings[key])
        for key in digest_keys
    ) or not all(
        isinstance(bindings[key], str) and bindings[key]
        for key in {"account_run_binding", "principal_run_binding"}
    ):
        raise DiagnosticBlockedError("BLOCKED_BINDING_VALUE")
    observation_window = _closed_mapping(
        observation_window, WINDOW_KEYS, "BLOCKED_WINDOW_SCHEMA"
    )
    start = _parse_utc(observation_window["start_utc"])
    end = _parse_utc(observation_window["end_utc"])
    if start >= end:
        raise DiagnosticBlockedError("BLOCKED_WINDOW_INVALID")
    for key in WINDOW_KEYS - {"start_utc", "end_utc"}:
        if not isinstance(observation_window[key], str) or not _HEX64.fullmatch(
            observation_window[key]
        ):
            raise DiagnosticBlockedError("BLOCKED_WINDOW_BINDING")
    observations = _closed_mapping(
        observations, OBSERVATION_KEYS, "BLOCKED_OBSERVATION_SCHEMA"
    )
    classification = classify_observations(observations)
    counters = _closed_mapping(
        side_effect_counters, SIDE_EFFECT_KEYS, "BLOCKED_COUNTER_SCHEMA"
    )
    if not all(type(value) is int and value >= 0 for value in counters.values()):
        raise DiagnosticBlockedError("BLOCKED_COUNTER_VALUE")
    for key, value in counters.items():
        expected = ALLOWED_NONZERO_COUNTERS_BY_CLASS[classification].get(key, 0)
        if value != expected:
            raise DiagnosticBlockedError("BLOCKED_SIDE_EFFECT_COUNTER")
    return DecisionProjection(
        target=target,
        bindings=bindings,
        observation_window=observation_window,
        observations=observations,
        classification=classification,
        side_effect_counters=MappingProxyType(dict(counters)),
    )


def build_snapshot(
    *, envelope: AcquisitionEnvelope, projection: DecisionProjection
) -> DiagnosticSnapshot:
    if envelope.sequence not in {1, 2}:
        raise DiagnosticBlockedError("BLOCKED_SNAPSHOT_SEQUENCE")
    acquired = _parse_utc(envelope.acquired_at_utc)
    window_end = _parse_utc(projection.observation_window["end_utc"])
    if acquired < window_end or not _HEX64.fullmatch(
        envelope.provider_read_receipt_sha256
    ):
        raise DiagnosticBlockedError("BLOCKED_ACQUISITION_ENVELOPE")
    expected_receipts = 3 if projection.classification == SPFX_SUBJECT_MISSING else 7
    if (
        len(envelope.port_receipt_sha256) != expected_receipts
        or len(set(envelope.port_receipt_sha256)) != expected_receipts
        or not all(_HEX64.fullmatch(item) for item in envelope.port_receipt_sha256)
    ):
        raise DiagnosticBlockedError("BLOCKED_PORT_RECEIPT_ENVELOPE")
    digest = _sha256(_canonical_bytes(projection.canonical_payload()))
    return DiagnosticSnapshot(
        schema_version="nac.m365-current-state-access-diagnostic/v0.1",
        acquisition_envelope=envelope,
        decision_projection=projection,
        decision_projection_sha256=digest,
    )


def compare_snapshots(
    first: DiagnosticSnapshot, second: DiagnosticSnapshot
) -> str:
    if (
        first.schema_version != "nac.m365-current-state-access-diagnostic/v0.1"
        or second.schema_version != first.schema_version
        or first.acquisition_envelope.sequence != 1
        or second.acquisition_envelope.sequence != 2
        or first.acquisition_envelope.provider_read_receipt_sha256
        == second.acquisition_envelope.provider_read_receipt_sha256
        or not set(first.acquisition_envelope.port_receipt_sha256).isdisjoint(
            second.acquisition_envelope.port_receipt_sha256
        )
        or _parse_utc(first.acquisition_envelope.acquired_at_utc)
        >= _parse_utc(second.acquisition_envelope.acquired_at_utc)
        or first.decision_projection_sha256 != second.decision_projection_sha256
        or first.decision_projection.canonical_payload()
        != second.decision_projection.canonical_payload()
    ):
        raise DiagnosticBlockedError("BLOCKED_SNAPSHOT_DIFFERENCE")
    classification = first.decision_projection.classification
    if classification not in DIAGNOSTIC_CLASSES:
        raise DiagnosticBlockedError("BLOCKED_CLASSIFICATION")
    return classification


__all__ = [
    "AcquisitionEnvelope",
    "BFF_AUTHENTICATION_REJECTED_401",
    "BFF_AUTHORIZATION_REJECTED_403",
    "BFF_REQUEST_NOT_OBSERVED",
    "DecisionProjection",
    "DiagnosticBlockedError",
    "DiagnosticSnapshot",
    "SPFX_SUBJECT_MISSING",
    "build_decision_projection",
    "build_snapshot",
    "classify_observations",
    "compare_snapshots",
]
