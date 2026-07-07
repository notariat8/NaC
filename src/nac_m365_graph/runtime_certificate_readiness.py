from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNTIME_SMOKE_STATE = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.runtime-smoke.f8.json"
)
DEFAULT_RUNTIME_METADATA_STATE = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.runtime-metadata.f8.json"
)
DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_MONITOR_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "runtime-certificate-expiry-monitor.redacted.json"
)
DEFAULT_CERTIFICATE_EXPIRY_WARNING_DAYS = 90
DEFAULT_CERTIFICATE_EXPIRY_CRITICAL_DAYS = 30

REQUIRED_CERTIFICATE_ENVIRONMENT = [
    "M365_TENANT_ID",
    "M365_RUNTIME_CLIENT_ID",
    "M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
    "M365_RUNTIME_CLIENT_KEY_PATH",
]
OPTIONAL_CERTIFICATE_ENVIRONMENT = ["M365_RUNTIME_CLIENT_KEY_PASSWORD"]


def load_runtime_certificate_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_runtime_certificate_readiness(
    runtime_smoke_state: dict[str, Any] | None = None,
    runtime_metadata_state: dict[str, Any] | None = None,
    *,
    now_utc: str | None = None,
) -> dict[str, Any]:
    smoke_runtime = _runtime_application(runtime_smoke_state)
    metadata_runtime = _runtime_application(runtime_metadata_state)
    smoke_thumbprint = _text(smoke_runtime.get("certificate_thumbprint_sha1"))
    metadata_thumbprint = _text(metadata_runtime.get("certificate_thumbprint_sha1"))
    expires_at = _text(smoke_runtime.get("certificate_expires_at_utc"))
    days_until_expiry = _days_until_expiry(expires_at, now_utc)
    secret_material_stored = _contains_sensitive_keys(runtime_smoke_state or {}) or _contains_sensitive_keys(
        runtime_metadata_state or {}
    )
    auth_mode = _text(smoke_runtime.get("authentication_mode"))
    metadata_auth_mode = _text(metadata_runtime.get("authentication_mode"))
    thumbprint_matches = bool(smoke_thumbprint and metadata_thumbprint and smoke_thumbprint == metadata_thumbprint)
    expiry_review_required = days_until_expiry is None or days_until_expiry <= 30

    checks = [
        _check(
            "certificate_auth_mode_evidence",
            "PASSED" if auth_mode == "client_credentials_with_certificate" else "REVIEW_REQUIRED",
            "Runtime smoke evidence uses client_credentials_with_certificate."
            if auth_mode == "client_credentials_with_certificate"
            else "Runtime smoke certificate-auth evidence is missing.",
            owner_gate_required=False,
        ),
        _check(
            "runtime_metadata_auth_mode_matches",
            "PASSED" if metadata_auth_mode == auth_mode == "client_credentials_with_certificate" else "REVIEW_REQUIRED",
            "Runtime metadata evidence matches the certificate auth mode.",
            owner_gate_required=False,
        ),
        _check(
            "certificate_thumbprint_evidence_present",
            "PASSED" if smoke_thumbprint else "REVIEW_REQUIRED",
            "Certificate thumbprint evidence is present but not emitted in readiness output.",
            owner_gate_required=False,
        ),
        _check(
            "runtime_metadata_thumbprint_matches_smoke",
            "PASSED" if thumbprint_matches else "REVIEW_REQUIRED",
            "Runtime metadata certificate thumbprint matches runtime smoke evidence.",
            owner_gate_required=False,
        ),
        _check(
            "certificate_rotation_window",
            "REVIEW_REQUIRED" if expiry_review_required else "PASSED",
            "Certificate expires within 30 days or expiry evidence is missing."
            if expiry_review_required
            else "Certificate expiry is outside the 30-day review window.",
            owner_gate_required=True,
        ),
        _check(
            "secret_material_not_stored",
            "PASSED" if not secret_material_stored else "FAILED",
            "No token, client secret, private key, password or certificate body key is stored in evidence.",
            owner_gate_required=False,
        ),
        _check(
            "credential_files_not_read",
            "PASSED",
            "Readiness does not read certificate or private-key files.",
            owner_gate_required=False,
        ),
        _check(
            "secret_env_values_not_read",
            "PASSED",
            "Readiness exposes environment variable names only, not their values.",
            owner_gate_required=False,
        ),
        _check(
            "certificate_generation_owner_gated",
            "PASSED",
            "Certificate generation is a separate owner-gated operation.",
            owner_gate_required=True,
        ),
        _check(
            "app_credential_upload_owner_gated",
            "PASSED",
            "Entra app credential upload is a separate owner-gated Graph/portal operation.",
            owner_gate_required=True,
        ),
    ]
    failed_checks = [check for check in checks if check["status"] == "FAILED"]
    review_checks = [check for check in checks if check["status"] == "REVIEW_REQUIRED"]

    return {
        "schema_version": "nac.m365-runtime-certificate-readiness/v0.1",
        "status": "FAILED" if failed_checks else "PASSED",
        "summary": {
            "preferred_authentication_mode": "client_credentials_with_certificate",
            "runtime_smoke_state_attached": runtime_smoke_state is not None,
            "runtime_metadata_state_attached": runtime_metadata_state is not None,
            "certificate_thumbprint_present": bool(smoke_thumbprint),
            "certificate_thumbprint_emitted": False,
            "certificate_expires_at_utc": expires_at,
            "certificate_days_until_expiry": days_until_expiry,
            "certificate_rotation_review_required": expiry_review_required,
            "runtime_metadata_thumbprint_matches_smoke": thumbprint_matches,
            "required_environment_variables": list(REQUIRED_CERTIFICATE_ENVIRONMENT),
            "optional_environment_variables": list(OPTIONAL_CERTIFICATE_ENVIRONMENT),
            "secret_env_values_read": False,
            "credential_files_read": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "mandate_data_allowed": False,
            "private_key_allowed_in_repo": False,
            "certificate_body_allowed_in_repo": False,
            "certificate_generation_owner_gate_required": True,
            "app_credential_upload_owner_gate_required": True,
            "secret_material_stored": secret_material_stored,
            "raw_tenant_id_stored": False,
            "raw_client_id_stored": False,
            "raw_site_id_stored": False,
            "review_required_checks": len(review_checks),
        },
        "checks": checks,
        "warnings": [check["message"] for check in review_checks],
    }


def build_runtime_certificate_expiry_monitor(
    runtime_smoke_state: dict[str, Any] | None = None,
    runtime_metadata_state: dict[str, Any] | None = None,
    *,
    now_utc: str | None = None,
    warning_days: int = DEFAULT_CERTIFICATE_EXPIRY_WARNING_DAYS,
    critical_days: int = DEFAULT_CERTIFICATE_EXPIRY_CRITICAL_DAYS,
) -> dict[str, Any]:
    smoke_runtime = _runtime_application(runtime_smoke_state)
    metadata_runtime = _runtime_application(runtime_metadata_state)
    smoke_thumbprint = _text(smoke_runtime.get("certificate_thumbprint_sha1"))
    metadata_thumbprint = _text(metadata_runtime.get("certificate_thumbprint_sha1"))
    expires_at = _text(smoke_runtime.get("certificate_expires_at_utc"))
    days_until_expiry = _days_until_expiry(expires_at, now_utc)
    auth_mode = _text(smoke_runtime.get("authentication_mode"))
    metadata_auth_mode = _text(metadata_runtime.get("authentication_mode"))
    secret_material_stored = _contains_sensitive_keys(runtime_smoke_state or {}) or _contains_sensitive_keys(
        runtime_metadata_state or {}
    )
    thumbprint_matches = bool(smoke_thumbprint and metadata_thumbprint and smoke_thumbprint == metadata_thumbprint)
    threshold_errors = _certificate_threshold_errors(
        warning_days=warning_days,
        critical_days=critical_days,
    )
    expiry_level = _certificate_expiry_level(
        days_until_expiry,
        warning_days=warning_days,
        critical_days=critical_days,
        evidence_missing=not expires_at or bool(threshold_errors),
    )

    checks = [
        _check(
            "certificate_expiry_evidence_present",
            "PASSED" if days_until_expiry is not None else "BLOCKED",
            "Certificate expiry evidence is present."
            if days_until_expiry is not None
            else "Certificate expiry evidence is missing or invalid.",
            owner_gate_required=False,
        ),
        _check(
            "certificate_expiry_thresholds_valid",
            "PASSED" if not threshold_errors else "BLOCKED",
            "Certificate expiry monitor thresholds are valid."
            if not threshold_errors
            else "; ".join(threshold_errors),
            owner_gate_required=False,
        ),
        _check(
            "certificate_auth_mode_evidence",
            "PASSED" if auth_mode == "client_credentials_with_certificate" else "BLOCKED",
            "Runtime smoke evidence uses client_credentials_with_certificate."
            if auth_mode == "client_credentials_with_certificate"
            else "Runtime smoke certificate-auth evidence is missing.",
            owner_gate_required=False,
        ),
        _check(
            "runtime_metadata_auth_mode_matches",
            "PASSED" if metadata_auth_mode == auth_mode == "client_credentials_with_certificate" else "BLOCKED",
            "Runtime metadata evidence matches the certificate auth mode.",
            owner_gate_required=False,
        ),
        _check(
            "runtime_metadata_thumbprint_matches_smoke",
            "PASSED" if thumbprint_matches else "BLOCKED",
            "Runtime metadata certificate thumbprint matches runtime smoke evidence."
            if thumbprint_matches
            else "Runtime metadata certificate thumbprint does not match runtime smoke evidence.",
            owner_gate_required=False,
        ),
        _check(
            "certificate_expiry_window",
            "PASSED" if expiry_level == "OK" else ("FAILED" if expiry_level == "EXPIRED" else "REVIEW_REQUIRED"),
            _certificate_expiry_message(expiry_level, days_until_expiry, warning_days, critical_days),
            owner_gate_required=expiry_level != "OK",
        ),
        _check(
            "secret_material_not_stored",
            "PASSED" if not secret_material_stored else "FAILED",
            "No token, client secret, private key, password or certificate body key is stored in evidence.",
            owner_gate_required=False,
        ),
        _check(
            "credential_files_not_read",
            "PASSED",
            "Expiry monitor does not read certificate or private-key files.",
            owner_gate_required=False,
        ),
        _check(
            "graph_requests_not_executed",
            "PASSED",
            "Expiry monitor uses local redacted evidence only and does not call Microsoft Graph.",
            owner_gate_required=False,
        ),
    ]
    failed_checks = [check for check in checks if check["status"] == "FAILED"]
    blocked_checks = [check for check in checks if check["status"] == "BLOCKED"]
    review_checks = [check for check in checks if check["status"] == "REVIEW_REQUIRED"]
    status = "PASSED"
    if blocked_checks:
        status = "BLOCKED"
    elif failed_checks:
        status = "FAILED"
    elif review_checks:
        status = "REVIEW_REQUIRED"

    return {
        "schema_version": "nac.m365-runtime-certificate-expiry-monitor/v0.1",
        "status": status,
        "summary": {
            "certificate_expires_at_utc": expires_at,
            "certificate_days_until_expiry": days_until_expiry,
            "certificate_expiry_level": expiry_level,
            "certificate_expiry_warning_days": warning_days,
            "certificate_expiry_critical_days": critical_days,
            "certificate_rotation_required": expiry_level in {"WARNING", "CRITICAL", "EXPIRED"},
            "certificate_thumbprint_present": bool(smoke_thumbprint),
            "certificate_thumbprint_emitted": False,
            "runtime_metadata_thumbprint_matches_smoke": thumbprint_matches,
            "preferred_authentication_mode": "client_credentials_with_certificate",
            "secret_env_values_read": False,
            "credential_files_read": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "graph_rest_only": True,
            "mandate_data_allowed": False,
            "private_key_allowed_in_repo": False,
            "certificate_body_allowed_in_repo": False,
            "stores_tokens_or_secrets": secret_material_stored,
            "raw_case_id_stored": False,
            "raw_site_id_stored": False,
            "raw_site_url_stored": False,
            "raw_graph_response_stored": False,
            "reads_sharepoint_file_content": False,
            "owner_gate_required_for_rotation": expiry_level in {"WARNING", "CRITICAL", "EXPIRED"},
            "recommended_owner_gate": "m365_runtime_certificate_rotation_lifecycle"
            if expiry_level in {"WARNING", "CRITICAL", "EXPIRED"}
            else None,
        },
        "checks": checks,
        "warnings": [check["message"] for check in review_checks],
        "errors": [check["message"] for check in [*blocked_checks, *failed_checks]],
    }


def write_runtime_certificate_expiry_monitor_artifact(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _runtime_application(state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {}
    runtime = state.get("runtime_application")
    return runtime if isinstance(runtime, dict) else {}


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _days_until_expiry(expires_at: str | None, now_utc: str | None) -> int | None:
    if not expires_at:
        return None
    try:
        expiry = _parse_utc(expires_at)
        now = _parse_utc(now_utc) if now_utc else datetime.now(UTC).replace(microsecond=0)
    except ValueError:
        return None
    return (expiry - now).days


def _parse_utc(value: str | None) -> datetime:
    if not value:
        raise ValueError("missing datetime")
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _check(
    check_id: str,
    status: str,
    message: str,
    *,
    owner_gate_required: bool,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": status,
        "message": message,
        "owner_gate_required": owner_gate_required,
    }


def _certificate_threshold_errors(*, warning_days: int, critical_days: int) -> list[str]:
    errors = []
    if warning_days <= 0:
        errors.append("warning_days must be greater than 0")
    if critical_days < 0:
        errors.append("critical_days must be greater than or equal to 0")
    if critical_days >= warning_days:
        errors.append("critical_days must be lower than warning_days")
    return errors


def _certificate_expiry_level(
    days_until_expiry: int | None,
    *,
    warning_days: int,
    critical_days: int,
    evidence_missing: bool,
) -> str:
    if evidence_missing or days_until_expiry is None:
        return "UNKNOWN"
    if days_until_expiry < 0:
        return "EXPIRED"
    if days_until_expiry <= critical_days:
        return "CRITICAL"
    if days_until_expiry <= warning_days:
        return "WARNING"
    return "OK"


def _certificate_expiry_message(
    expiry_level: str,
    days_until_expiry: int | None,
    warning_days: int,
    critical_days: int,
) -> str:
    if expiry_level == "OK":
        return f"Certificate expiry is outside the {warning_days}-day warning window."
    if expiry_level == "WARNING":
        return f"Certificate expires within {warning_days} days; prepare rotation."
    if expiry_level == "CRITICAL":
        return f"Certificate expires within {critical_days} days; rotate before further release gates."
    if expiry_level == "EXPIRED":
        return "Certificate is expired; runtime certificate rotation is required."
    if days_until_expiry is None:
        return "Certificate expiry cannot be evaluated."
    return "Certificate expiry monitor cannot determine a safe rotation level."


def _contains_sensitive_keys(payload: Any) -> bool:
    sensitive_keys = {
        "access_token",
        "certificate_body",
        "client_secret",
        "password",
        "private_key",
        "refresh_token",
        "secret",
        "token",
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key).lower()
            if key_text in sensitive_keys or key_text.endswith("_secret") or key_text.endswith("_token"):
                return True
            if _contains_sensitive_keys(value):
                return True
    if isinstance(payload, list):
        return any(_contains_sensitive_keys(item) for item in payload)
    return False
