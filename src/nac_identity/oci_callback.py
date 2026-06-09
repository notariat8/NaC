from __future__ import annotations


def build_auth_callback_result(
    *,
    code: str,
    state: str,
    provider_error: str,
    state_validation_configured: bool,
    token_exchange_configured: bool,
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

    return {
        "schema_version": "nac.auth-callback/v0.1",
        "status": "received",
        "public_message": "Anmeldung empfangen.",
        "state_validation": {
            "status": "configured" if state_validation_configured else "not_configured",
        },
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
