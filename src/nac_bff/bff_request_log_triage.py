"""Issue #748 offline BFF request-log triage; no Microsoft or credential port.

The one-row classifier is for synthetic tests only. The production entry point
cannot accept rows or a query and remains blocked before any provider access.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .client_http_observation_receipt import (
    ClientHttpObservationError,
    validate_client_http_observation_receipt_bytes,
)
from .current_state_access_client_receipt import (
    ClientObservationReceiptError,
    validate_client_observation_receipt_bytes,
)


CONTRACT_PATH = Path("workflows/verification-contracts/m365-bff-request-log-triage.verification.json")
BASE_RECEIPT_NAME = "client-observation-receipt.json"
HTTP_RECEIPT_NAME = "client-http-observation.json"
_HEX64 = re.compile(r"[0-9a-f]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z\Z")
_ROW_KEYS = frozenset({
    "request_correlation_binding_sha256", "http_class", "method",
    "path_class", "timestamp_utc",
})
_CONTRACT_FLAGS = (
    "target_binding_proven", "query_projection_proven",
    "correlation_capture_proven", "no_refresh_capability_proven",
    "provider_read_authorized", "historical_issue_739_release_authorized",
    "historical_issue_632_live_authorized", "pr_754_authorized",
)
_HISTORICAL_PATHS = (
    "workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml",
    "workflows/contracts/m365-current-state-read-driver-resources.contract.json",
)
_EXPECTED_RECEIPT_SHA256 = {
    "base_receipt_sha256": "ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40",
    "http_receipt_sha256": "daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda",
}
_DOC_PATHS = {
    "specifications": {
        "de": "docs/de/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md",
        "en": "docs/en/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md",
    },
    "plans": {
        "de": "docs/de/superpowers/plans/2026-09-25-m365-bff-request-log-triage.md",
        "en": "docs/en/superpowers/plans/2026-09-25-m365-bff-request-log-triage.md",
    },
}
_ROOT_KEYS = frozenset({
    "schema_version", "contract_id", "leading_issue", "delivery_mode",
    "risk_gate", "status", "specifications", "plans", "acceptance_ids",
    "historical_contract_bindings", "target_scope", "receipts", "resource",
    "target_binding_proven", "query_projection_proven",
    "correlation_capture_proven", "no_refresh_capability_proven",
    "provider_read_authorized", "terminal_blockers",
    "local_preparation_side_effects", "result_boundary",
    "historical_issue_739_release_authorized",
    "historical_issue_632_live_authorized", "pr_754_authorized",
})
_TERMINAL_BLOCKERS = frozenset({
    "BLOCKED_INPUTS_REQUIRED", "BLOCKED_RECEIPT_BINDING",
    "BLOCKED_TARGET_UNBOUND", "BLOCKED_QUERY_PROJECTION_UNPROVEN",
    "BLOCKED_CORRELATION_UNPROVEN", "BLOCKED_AMBIGUOUS_MATCH",
    "BLOCKED_NO_REFRESH_CAPABILITY", "BLOCKED_SINGLE_PRINCIPAL",
})


class TriageBlocked(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TriageBlocked("BLOCKED_CONTRACT_INVALID")
        result[key] = value
    return result


def _valid_hash(value: object) -> bool:
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def _parse_utc(value: object) -> datetime:
    if not isinstance(value, str) or _UTC.fullmatch(value) is None:
        raise TriageBlocked("BLOCKED_RECEIPT_BINDING")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TriageBlocked("BLOCKED_RECEIPT_BINDING") from exc
    if parsed.isoformat(timespec="milliseconds").replace("+00:00", "Z") != value:
        raise TriageBlocked("BLOCKED_RECEIPT_BINDING")
    return parsed


def load_triage_contract(repo_root: Path) -> dict[str, Any]:
    """Validate static offline contract and historic file digests, no I/O beyond Git tree."""
    try:
        raw = (repo_root / CONTRACT_PATH).read_bytes()
        value = json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=_unique_keys)
        if not isinstance(value, dict):
            raise ValueError("root")
        if (
            frozenset(value) != _ROOT_KEYS
            or
            value.get("schema_version") != "nac.m365-bff-request-log-triage/v0.1"
            or value.get("contract_id") != "m365-bff-request-log-triage"
            or value.get("leading_issue") != "https://github.com/notariat8/NaC/issues/748"
            or value.get("status") != "OFFLINE_ONLY_NOT_LIVE_CAPABLE"
            or value.get("delivery_mode") != "Protected PR"
            or value.get("risk_gate") != "Human Approval"
            or any(value.get(flag) is not False for flag in _CONTRACT_FLAGS)
            or value.get("acceptance_ids") != [f"AC-748-TG-{index:02d}" for index in range(1, 7)]
        ):
            raise ValueError("contract")
        historical = value["historical_contract_bindings"]
        if not isinstance(historical, dict) or set(historical) != set(_HISTORICAL_PATHS):
            raise ValueError("historical")
        for relative in _HISTORICAL_PATHS:
            expected = historical[relative]
            if not _valid_hash(expected) or hashlib.sha256((repo_root / relative).read_bytes()).hexdigest() != expected:
                raise ValueError("historic digest")
        target = value["target_scope"]
        if not isinstance(target, dict) or target != {
            "workspace": "notary_team_01",
            "function": "func-nac-bff-test-funktion8",
            "teams_app": "NaC Vorgangsansicht",
            "application_insights_app_id": "PROTECTED_EXTERNAL_EVIDENCE_REQUIRED",
        }:
            raise ValueError("target")
        receipts = value["receipts"]
        if not isinstance(receipts, dict) or set(receipts) != {
            "base_receipt_sha256", "http_receipt_sha256", "window_start_utc",
            "window_end_utc", "required_spfx_subject_available", "required_client_http_class",
        } or any(not _valid_hash(receipts[key]) for key in ("base_receipt_sha256", "http_receipt_sha256")):
            raise ValueError("receipts")
        if (
            any(receipts[key] != expected for key, expected in _EXPECTED_RECEIPT_SHA256.items())
            or
            receipts["window_start_utc"] != "2026-09-25T10:42:03.397Z"
            or receipts["window_end_utc"] != "2026-09-25T10:42:10.487Z"
            or receipts["required_spfx_subject_available"] is not True
            or receipts["required_client_http_class"] != "403"
        ):
            raise ValueError("receipt values")
        resource = value["resource"]
        if not isinstance(resource, dict) or resource != {
            "method": "GET",
            "origin": "https://api.applicationinsights.io",
            "fixed_path_template": "/v1/apps/{app_id}/query",
            "maximum_reads": 1,
            "request_body": False,
            "follow_redirects": False,
            "automatic_retries": 0,
            "pagination": False,
            "free_url_or_query_input": False,
            "query_template_id": "issue748-requests-correlation-window-v1",
            "query_sha256": "PROTECTED_SCHEMA_PROOF_REQUIRED",
            "allowed_result_fields": [
                "request_observed", "http_class", "request_correlation_binding_sha256",
            ],
            "maximum_response_bytes": 65536,
        }:
            raise ValueError("resource")
        effects = value["local_preparation_side_effects"]
        if not isinstance(effects, dict) or set(effects) != {
            "network_reads", "provider_ports_created", "credential_reads",
            "credential_writes", "provider_writes", "logins", "token_refreshes",
        } or any(type(count) is not int or count != 0 for count in effects.values()):
            raise ValueError("effects")
        boundary = value["result_boundary"]
        if not isinstance(boundary, dict) or boundary != {
            "unique_correlated_403": "FUNCTION_TELEMETRY_MATCH_403",
            "empty_log_is_not": "BFF_REQUEST_NOT_OBSERVED",
            "does_not_prove": ["python_endpoint_response", "bff_access_rule"],
        }:
            raise ValueError("result")
        blockers = value.get("terminal_blockers")
        if (
            not isinstance(blockers, list)
            or len(blockers) != len(_TERMINAL_BLOCKERS)
            or frozenset(blockers) != _TERMINAL_BLOCKERS
        ):
            raise ValueError("blockers")
        for field in ("specifications", "plans"):
            paths = value[field]
            if not isinstance(paths, dict) or paths != _DOC_PATHS[field]:
                raise ValueError("docs")
            if any(not (repo_root / paths[language]).is_file() for language in ("de", "en")):
                raise ValueError("docs missing")
        return value
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, KeyError, ValueError, TriageBlocked) as exc:
        raise TriageBlocked("BLOCKED_CONTRACT_INVALID") from exc


def verify_receipt_pair(base_raw: bytes, http_raw: bytes, contract: Mapping[str, Any]) -> str:
    """Verify exact bytes and closed client state; return only the correlation digest."""
    try:
        if not isinstance(base_raw, bytes) or not isinstance(http_raw, bytes):
            raise ValueError("types")
        if hashlib.sha256(base_raw).hexdigest() != contract["base_receipt_sha256"]:
            raise ValueError("base digest")
        if hashlib.sha256(http_raw).hexdigest() != contract["http_receipt_sha256"]:
            raise ValueError("http digest")
        base = validate_client_observation_receipt_bytes(base_raw)
        http = validate_client_http_observation_receipt_bytes(base_raw, http_raw)
        if (
            base["start_utc"] != contract["window_start_utc"]
            or base["end_utc"] != contract["window_end_utc"]
            or base["spfx_subject_available"] is not True
            or http["client_http_class"] != "403"
        ):
            raise ValueError("state")
        return base["request_correlation_binding_sha256"]
    except (ClientObservationReceiptError, ClientHttpObservationError, KeyError, TypeError, ValueError) as exc:
        raise TriageBlocked("BLOCKED_RECEIPT_BINDING") from exc


def classify_synthetic_rows(
    rows: Sequence[Mapping[str, Any]], *, expected_correlation_sha256: str
) -> dict[str, Any]:
    """Exercise the narrow result rule with synthetic, already-redacted rows only."""
    if not _valid_hash(expected_correlation_sha256):
        raise TriageBlocked("BLOCKED_CORRELATION_UNPROVEN")
    if not isinstance(rows, (list, tuple)) or not rows:
        raise TriageBlocked("BLOCKED_CORRELATION_UNPROVEN")
    if len(rows) != 1:
        raise TriageBlocked("BLOCKED_AMBIGUOUS_MATCH")
    row = rows[0]
    if not isinstance(row, Mapping) or frozenset(row) != _ROW_KEYS:
        raise TriageBlocked("BLOCKED_RESPONSE_REDACTION")
    try:
        timestamp = _parse_utc(row["timestamp_utc"])
    except TriageBlocked as exc:
        raise TriageBlocked("BLOCKED_CORRELATION_UNPROVEN") from exc
    if not (_parse_utc("2026-09-25T10:42:03.397Z") <= timestamp <= _parse_utc("2026-09-25T10:42:10.487Z")):
        raise TriageBlocked("BLOCKED_CORRELATION_UNPROVEN")
    if row["request_correlation_binding_sha256"] != expected_correlation_sha256:
        raise TriageBlocked("BLOCKED_CORRELATION_UNPROVEN")
    if row["method"] != "GET" or row["path_class"] != "workbench_snapshot" or row["http_class"] != "403":
        raise TriageBlocked("BLOCKED_RESPONSE_REDACTION")
    return {
        "request_observed": True,
        "http_class": "403",
        "request_correlation_binding_sha256": expected_correlation_sha256,
    }


def _blocked_payload(code: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.m365-bff-request-log-triage-preflight/v0.1",
        "status": "BLOCKED",
        "reason_code": code,
        "network_reads": 0,
        "provider_ports_created": 0,
        "credential_reads": 0,
        "credential_writes": 0,
        "provider_writes": 0,
        "logins": 0,
        "token_refreshes": 0,
        "provider_read_authorized": False,
    }


def run_offline_preflight(
    *, repo_root: Path, input_root: Path | None,
    backend: Any | None = None,
    credential_provider: Callable[[], object] | None = None,
    transport_provider: Callable[[], object] | None = None,
) -> dict[str, Any]:
    """Read only two protected local files and stop before provider construction."""
    del credential_provider, transport_provider
    try:
        contract = load_triage_contract(repo_root)
        if input_root is None:
            raise TriageBlocked("BLOCKED_INPUTS_REQUIRED")
        root = Path(input_root)
        if not root.is_absolute() or root.resolve().is_relative_to(repo_root.resolve()):
            raise TriageBlocked("BLOCKED_INPUT_SECURITY")
        if backend is None:
            from .activation_security_backend import get_platform_security_backend

            backend = get_platform_security_backend()
        session = backend.open_secure_directory(
            root, create=False, require_current_owner=True, require_restrictive_dacl=True,
        )
        try:
            base = session.read_bounded(BASE_RECEIPT_NAME, 16 * 1024)
            http = session.read_bounded(HTTP_RECEIPT_NAME, 1024)
        finally:
            session.close()
        if base is None or http is None:
            raise TriageBlocked("BLOCKED_INPUTS_REQUIRED")
        verify_receipt_pair(base, http, contract["receipts"])
        # No target, KQL schema, captured correlation column, or no-refresh
        # capability has been proven. A green receipt check cannot unlock I/O.
        raise TriageBlocked("BLOCKED_TARGET_UNBOUND")
    except TriageBlocked as exc:
        return _blocked_payload(exc.code)
    except (OSError, RuntimeError, TypeError, ValueError, AttributeError):
        return _blocked_payload("BLOCKED_INPUT_SECURITY")


__all__ = [
    "TriageBlocked", "classify_synthetic_rows", "load_triage_contract",
    "run_offline_preflight", "verify_receipt_pair",
]
