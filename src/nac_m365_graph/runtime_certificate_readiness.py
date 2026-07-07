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
