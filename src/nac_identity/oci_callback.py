from __future__ import annotations

from typing import Any


def build_auth_callback_result(
    *,
    code: str,
    state: str,
    provider_error: str,
    state_validation_configured: bool,
    token_exchange_configured: bool,
    state_validation: dict[str, Any] | None = None,
) -> dict:
    if provider_error or not code or not state:
        return {
            "schema_version": "nac.auth-callback/v0.1",
            "status": "rejected",
            "public_message": "Anmeldung nicht abgeschlossen.",
            "state_validation": {"status": "not_started"},
            "token_exchange": {"status": "not_started"},
            "role_gate": {
                "status": "closed",
                "reason": "callback_not_complete",
            },
            "guardrails": {
                "contains_credentials": False,
                "callback_values_exposed": False,
                "workspace_opened": False,
            },
        }
    normalized_state_validation = _state_validation_result(
        configured=state_validation_configured,
        validation=state_validation,
    )
    if normalized_state_validation["status"] in {"invalid", "expired", "not_started"}:
        return {
            "schema_version": "nac.auth-callback/v0.1",
            "status": "rejected",
            "public_message": "Anmeldung nicht abgeschlossen.",
            "state_validation": normalized_state_validation,
            "token_exchange": {"status": "not_started"},
            "role_gate": {
                "status": "closed",
                "reason": f"state_{normalized_state_validation['status']}",
            },
            "guardrails": {
                "contains_credentials": False,
                "callback_values_exposed": False,
                "workspace_opened": False,
            },
        }

    return {
        "schema_version": "nac.auth-callback/v0.1",
        "status": "received",
        "public_message": "Anmeldung empfangen.",
        "state_validation": normalized_state_validation,
        "token_exchange": {
            "status": "not_started",
            "configuration": "configured" if token_exchange_configured else "not_configured",
        },
        "role_gate": {
            "status": "closed",
            "reason": "session_not_established",
        },
        "guardrails": {
            "contains_credentials": False,
            "callback_values_exposed": False,
            "workspace_opened": False,
        },
        "next_step": "validate_state_then_exchange_token_then_apply_nac_role_gate",
    }


def _state_validation_result(*, configured: bool, validation: dict[str, Any] | None) -> dict[str, Any]:
    if not configured:
        return {"status": "not_configured"}
    if not validation:
        return {"status": "not_started"}
    status = str(validation.get("status", "invalid"))
    if status not in {"valid", "invalid", "expired"}:
        status = "invalid"
    result: dict[str, Any] = {"status": status}
    if status == "valid" and validation.get("tenant_hint"):
        result["tenant_hint"] = str(validation["tenant_hint"])[:120]
    if status == "valid":
        result["nonce_bound"] = bool(validation.get("nonce_bound"))
    return result
