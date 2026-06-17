from __future__ import annotations

from typing import Any

from .oidc_token_exchange import build_oidc_token_exchange_contract
from .oidc_session import evaluate_oidc_session_boundary


def build_auth_callback_result(
    *,
    code: str,
    state: str,
    provider_error: str,
    state_validation_configured: bool,
    token_exchange_configured: bool,
    state_validation: dict[str, Any] | None = None,
    token_exchange_result: dict[str, Any] | None = None,
    expected_issuer: str = "",
    expected_audience: str = "",
    redirect_uri: str = "",
    token_endpoint: str = "",
    client_id: str = "",
    session_signing_key: str = "",
    session_ttl_seconds: int = 600,
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

    token_exchange_contract = build_oidc_token_exchange_contract(
        configured=token_exchange_configured,
        code=code,
        redirect_uri=redirect_uri,
        token_endpoint=token_endpoint,
        client_id=client_id or expected_audience,
        exchanger_result=token_exchange_result,
    )
    effective_state_validation = (
        state_validation
        if state_validation_configured and isinstance(state_validation, dict)
        else normalized_state_validation
    )
    session_boundary = evaluate_oidc_session_boundary(
        state_validation=effective_state_validation,
        token_exchange_result=token_exchange_contract.session_input(),
        expected_issuer=expected_issuer,
        expected_audience=expected_audience,
        session_signing_key=session_signing_key,
        session_ttl_seconds=session_ttl_seconds,
    )
    token_exchange = token_exchange_contract.public_result()

    return {
        "schema_version": "nac.auth-callback/v0.1",
        "status": "received",
        "public_message": "Anmeldung empfangen.",
        "state_validation": normalized_state_validation,
        "token_exchange": token_exchange,
        "jwt_validation": session_boundary["jwt_validation"],
        "claim_boundary": session_boundary["claim_boundary"],
        "role_gate": session_boundary["role_gate"],
        "session_boundary": session_boundary,
        "guardrails": {
            "contains_credentials": False,
            "callback_values_exposed": False,
            "workspace_opened": False,
            "tokens_returned": False,
            "session_cookie_issued": bool(session_boundary["session"]["cookie_issued"]),
        },
        "next_step": (
            "session_bound_workspace_stays_closed"
            if session_boundary["session"]["cookie_issued"]
            else "exchange_token_then_evaluate_oidc_role_gate_contract"
        ),
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
