from __future__ import annotations

from typing import Any

from .oidc_role_gate import DEFAULT_REQUIRED_ROLE, evaluate_oidc_role_gate


def evaluate_oidc_session_boundary(
    *,
    state_validation: dict[str, Any],
    token_exchange_result: dict[str, Any] | None,
    expected_issuer: str,
    expected_audience: str,
    required_role: str = DEFAULT_REQUIRED_ROLE,
) -> dict[str, Any]:
    token_exchange = _token_exchange_summary(token_exchange_result)
    if state_validation.get("status") != "valid":
        return _closed(
            _state_reason(state_validation.get("status")),
            token_exchange=token_exchange,
            required_role=required_role,
        )
    if token_exchange["status"] != "verified":
        return _closed(
            _token_exchange_reason(token_exchange["status"]),
            token_exchange=token_exchange,
            required_role=required_role,
        )

    claims = token_exchange_result.get("claims") if isinstance(token_exchange_result, dict) else None
    if not isinstance(claims, dict):
        return _closed(
            "token_invalid",
            token_exchange=token_exchange,
            required_role=required_role,
            jwt_validation_status="invalid",
        )

    role_gate = evaluate_oidc_role_gate(
        claims=claims,
        expected_issuer=expected_issuer,
        expected_audience=expected_audience,
        state_validation=state_validation,
        required_role=required_role,
    )
    if role_gate["status"] != "open":
        return _result(
            status="closed",
            token_exchange=token_exchange,
            role_gate=role_gate,
            session_allowed=False,
            jwt_validation_status=_jwt_validation_status(role_gate["reason"]),
        )
    return _result(
        status="session_allowed",
        token_exchange=token_exchange,
        role_gate=role_gate,
        session_allowed=True,
        jwt_validation_status="verified",
    )


def _token_exchange_summary(token_exchange_result: dict[str, Any] | None) -> dict[str, str]:
    if not isinstance(token_exchange_result, dict):
        return {"status": "not_started"}
    status = str(token_exchange_result.get("status", "invalid"))
    if status not in {"not_started", "not_configured", "verified", "invalid", "failed", "unavailable"}:
        status = "invalid"
    return {"status": status}


def _token_exchange_reason(status: str) -> str:
    return {
        "not_started": "token_exchange_not_started",
        "not_configured": "token_exchange_not_configured",
        "invalid": "token_invalid",
        "failed": "token_exchange_failed",
        "unavailable": "token_exchange_unavailable",
    }.get(status, "token_invalid")


def _state_reason(status: Any) -> str:
    normalized = str(status or "invalid")
    if normalized in {"invalid", "expired", "not_started", "not_configured"}:
        return f"state_{normalized}"
    return "state_invalid"


def _jwt_validation_status(role_gate_reason: str) -> str:
    if role_gate_reason in {"role_missing"}:
        return "verified"
    return "invalid"


def _closed(
    reason: str,
    *,
    token_exchange: dict[str, str],
    required_role: str,
    jwt_validation_status: str = "not_started",
) -> dict[str, Any]:
    role_gate = {
        "schema_version": "nac.oidc-role-gate/v0.1",
        "status": "closed",
        "reason": reason,
        "role": required_role,
        "session_allowed": False,
        "guardrails": _guardrails(),
    }
    return _result(
        status="closed",
        token_exchange=token_exchange,
        role_gate=role_gate,
        session_allowed=False,
        jwt_validation_status=jwt_validation_status,
    )


def _result(
    *,
    status: str,
    token_exchange: dict[str, str],
    role_gate: dict[str, Any],
    session_allowed: bool,
    jwt_validation_status: str,
) -> dict[str, Any]:
    return {
        "schema_version": "nac.oidc-session-boundary/v0.1",
        "status": status,
        "token_exchange": token_exchange,
        "jwt_validation": {
            "status": jwt_validation_status,
        },
        "role_gate": role_gate,
        "session": {
            "session_allowed": bool(session_allowed),
            "cookie_issued": False,
            "workspace_opened": False,
        },
        "guardrails": _guardrails(),
    }


def _guardrails() -> dict[str, bool]:
    return {
        "contains_credentials": False,
        "tokens_returned": False,
        "callback_values_exposed": False,
        "workspace_opened": False,
        "session_cookie_issued": False,
        "live_token_exchange_performed": False,
    }
