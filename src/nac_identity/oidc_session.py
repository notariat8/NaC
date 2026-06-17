from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from http.cookies import CookieError, SimpleCookie
from typing import Any

from .oidc_role_gate import DEFAULT_REQUIRED_ROLE, evaluate_oidc_role_gate

DEFAULT_SESSION_COOKIE_NAME = "__Host-nac_session"
DEFAULT_SESSION_TTL_SECONDS = 600


def evaluate_oidc_session_boundary(
    *,
    state_validation: dict[str, Any],
    token_exchange_result: dict[str, Any] | None,
    expected_issuer: str,
    expected_audience: str,
    required_role: str = DEFAULT_REQUIRED_ROLE,
    session_signing_key: str = "",
    now: int | None = None,
    session_ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS,
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
            claim_boundary=_claim_boundary(
                status="verified",
                reason="forwarded_to_role_gate",
                claims_forwarded_to_role_gate=True,
                role_gate_evaluated=True,
            ),
            role_gate=role_gate,
            session_allowed=False,
            jwt_validation_status=_jwt_validation_status(role_gate["reason"]),
        )
    issued_session = _issued_session_cookie(
        signing_key=session_signing_key,
        now=now,
        ttl_seconds=session_ttl_seconds,
    )
    return _result(
        status="session_bound" if issued_session else "session_allowed",
        token_exchange=token_exchange,
        claim_boundary=_claim_boundary(
            status="verified",
            reason="forwarded_to_role_gate",
            claims_forwarded_to_role_gate=True,
            role_gate_evaluated=True,
        ),
        role_gate=role_gate,
        session_allowed=True,
        jwt_validation_status="verified",
        issued_session=issued_session,
    )


def validate_session_cookie(
    cookie_header: str,
    *,
    signing_key: str,
    now: int | None = None,
) -> dict[str, Any]:
    key = signing_key.strip()
    if not key:
        return _session_validation_result("not_configured", "session_signing_key_missing")
    cookie_value = _session_cookie_value(cookie_header)
    if not cookie_value:
        return _session_validation_result("missing", "session_cookie_missing")

    parts = cookie_value.split(".")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return _session_validation_result("invalid", "session_cookie_invalid")
    payload_part, signature_part = parts
    try:
        expected_signature = hmac.new(
            key.encode("utf-8"),
            payload_part.encode("ascii"),
            hashlib.sha256,
        ).digest()
        supplied_signature = _base64url_decode(signature_part)
        if not hmac.compare_digest(expected_signature, supplied_signature):
            return _session_validation_result("invalid", "session_cookie_signature_invalid")
        payload = json.loads(_base64url_decode(payload_part).decode("utf-8"))
    except (UnicodeDecodeError, ValueError, TypeError, json.JSONDecodeError):
        return _session_validation_result("invalid", "session_cookie_invalid")

    if not isinstance(payload, dict) or payload.get("schema_version") != "nac.session-cookie/v0.1":
        return _session_validation_result("invalid", "session_cookie_schema_invalid")
    if not isinstance(payload.get("sid"), str) or not payload["sid"]:
        return _session_validation_result("invalid", "session_cookie_subject_invalid")
    issued_at = _integer_or_none(payload.get("iat"))
    expires_at = _integer_or_none(payload.get("exp"))
    if issued_at is None or expires_at is None or expires_at <= issued_at:
        return _session_validation_result("invalid", "session_cookie_time_invalid")

    checked_at = int(time.time() if now is None else now)
    if checked_at >= expires_at:
        return _session_validation_result(
            "expired",
            "session_cookie_expired",
            issued_at=issued_at,
            expires_at=expires_at,
            ttl_remaining_seconds=0,
        )
    return _session_validation_result(
        "valid",
        "session_cookie_valid",
        session_allowed=True,
        protected_start_page_allowed=True,
        issued_at=issued_at,
        expires_at=expires_at,
        ttl_remaining_seconds=expires_at - checked_at,
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
        claim_boundary=_claim_boundary(
            status="closed",
            reason=reason,
            claims_forwarded_to_role_gate=False,
            role_gate_evaluated=False,
        ),
        role_gate=role_gate,
        session_allowed=False,
        jwt_validation_status=jwt_validation_status,
    )


def _result(
    *,
    status: str,
    token_exchange: dict[str, str],
    claim_boundary: dict[str, Any],
    role_gate: dict[str, Any],
    session_allowed: bool,
    jwt_validation_status: str,
    issued_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = {
        "session_allowed": bool(session_allowed),
        "cookie_issued": bool(issued_session),
        "workspace_opened": False,
    }
    if issued_session:
        session.update(issued_session)
    return {
        "schema_version": "nac.oidc-session-boundary/v0.2" if issued_session else "nac.oidc-session-boundary/v0.1",
        "status": status,
        "token_exchange": token_exchange,
        "jwt_validation": {
            "status": jwt_validation_status,
        },
        "claim_boundary": claim_boundary,
        "role_gate": role_gate,
        "session": session,
        "guardrails": _guardrails(session_cookie_issued=bool(issued_session)),
    }


def _guardrails(*, session_cookie_issued: bool = False) -> dict[str, bool]:
    return {
        "contains_credentials": False,
        "tokens_returned": False,
        "callback_values_exposed": False,
        "workspace_opened": False,
        "session_cookie_issued": bool(session_cookie_issued),
        "live_token_exchange_performed": False,
    }


def _issued_session_cookie(
    *,
    signing_key: str,
    now: int | None,
    ttl_seconds: int,
) -> dict[str, Any] | None:
    key = signing_key.strip()
    if not key:
        return None
    issued_at = int(time.time() if now is None else now)
    ttl = _normalized_ttl_seconds(ttl_seconds)
    expires_at = issued_at + ttl
    payload = {
        "schema_version": "nac.session-cookie/v0.1",
        "sid": secrets.token_urlsafe(24),
        "iat": issued_at,
        "exp": expires_at,
    }
    payload_text = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload_part = _base64url(payload_text)
    signature = hmac.new(key.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    value = f"{payload_part}.{_base64url(signature)}"
    return {
        "cookie_name": DEFAULT_SESSION_COOKIE_NAME,
        "ttl_seconds": ttl,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "set_cookie": (
            f"{DEFAULT_SESSION_COOKIE_NAME}={value}; "
            f"Max-Age={ttl}; Path=/; HttpOnly; Secure; SameSite=Lax"
        ),
    }


def _normalized_ttl_seconds(value: int) -> int:
    try:
        ttl = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SESSION_TTL_SECONDS
    if ttl < 60:
        return 60
    if ttl > 3600:
        return 3600
    return ttl


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _session_cookie_value(cookie_header: str) -> str:
    if not isinstance(cookie_header, str) or not cookie_header.strip():
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except CookieError:
        return ""
    morsel = cookie.get(DEFAULT_SESSION_COOKIE_NAME)
    if morsel is None:
        return ""
    return morsel.value.strip()


def _integer_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _session_validation_result(
    status: str,
    reason: str,
    *,
    session_allowed: bool = False,
    protected_start_page_allowed: bool = False,
    issued_at: int | None = None,
    expires_at: int | None = None,
    ttl_remaining_seconds: int | None = None,
) -> dict[str, Any]:
    session: dict[str, Any] = {
        "session_allowed": bool(session_allowed),
        "protected_start_page_allowed": bool(protected_start_page_allowed),
        "workspace_opened": False,
        "mandate_data_loaded": False,
    }
    if issued_at is not None:
        session["issued_at"] = int(issued_at)
    if expires_at is not None:
        session["expires_at"] = int(expires_at)
    if ttl_remaining_seconds is not None:
        session["ttl_remaining_seconds"] = int(ttl_remaining_seconds)
    return {
        "schema_version": "nac.session-validation/v0.1",
        "status": status,
        "reason": reason,
        "cookie_name": DEFAULT_SESSION_COOKIE_NAME,
        "session": session,
        "guardrails": {
            "contains_credentials": False,
            "tokens_returned": False,
            "claims_exposed": False,
            "session_cookie_exposed": False,
            "workspace_opened": False,
            "mandate_data_loaded": False,
        },
    }


def _claim_boundary(
    *,
    status: str,
    reason: str,
    claims_forwarded_to_role_gate: bool,
    role_gate_evaluated: bool,
) -> dict[str, Any]:
    return {
        "schema_version": "nac.oidc-claim-boundary/v0.1",
        "status": status,
        "reason": reason,
        "claims_forwarded_to_role_gate": bool(claims_forwarded_to_role_gate),
        "role_gate_evaluated": bool(role_gate_evaluated),
        "claims_exposed": False,
        "tokens_returned": False,
        "guardrails": {
            "contains_credentials": False,
            "tokens_returned": False,
            "claims_exposed": False,
            "workspace_opened": False,
            "session_cookie_issued": False,
        },
    }
