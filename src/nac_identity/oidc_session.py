from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Mapping, MutableSequence
from http.cookies import CookieError, SimpleCookie
from typing import Any, Callable

from .oidc_role_gate import DEFAULT_REQUIRED_ROLE, evaluate_oidc_role_gate
from .session_store import RuntimeSessionStoreAdapter

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
    role_membership_resolver: Callable[..., dict[str, Any]] | None = None,
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
    role_evidence = None
    if role_gate["status"] != "open" and role_gate.get("reason") == "role_missing":
        role_evidence = _resolve_server_role_membership(
            resolver=role_membership_resolver,
            claims=claims,
            required_role=required_role,
        )
        if role_evidence is not None:
            if role_evidence["status"] == "confirmed":
                role_gate = _server_confirmed_role_gate(required_role=required_role)
            elif role_evidence["status"] == "unavailable":
                role_gate = _closed_role_gate("server_membership_unavailable", required_role=required_role)
            elif role_evidence["status"] == "missing":
                role_gate = _closed_role_gate("server_membership_missing", required_role=required_role)
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
            role_evidence=role_evidence,
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
        role_evidence=role_evidence,
    )


def validate_session_cookie(
    cookie_header: str,
    *,
    signing_key: str,
    now: int | None = None,
    session_store: Mapping[str, Mapping[str, Any]] | RuntimeSessionStoreAdapter | None = None,
    require_server_session_store: bool = False,
    audit_log: MutableSequence[dict[str, Any]] | None = None,
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
    server_session = None
    if require_server_session_store and session_store is None:
        _append_session_audit_event(
            audit_log=audit_log,
            status="unavailable",
            reason="server_session_store_required",
            checked_at=checked_at,
            audit_event_id="",
        )
        return _session_validation_result("unavailable", "server_session_store_required")
    if session_store is not None:
        server_session = _validate_server_session_record(
            session_store=session_store,
            session_id=payload["sid"],
            checked_at=checked_at,
        )
        server_session_status = server_session["status"]
        server_session_reason = server_session["reason"]
        _append_session_audit_event(
            audit_log=audit_log,
            status="valid" if server_session_status == "active" else server_session_status,
            reason="session_cookie_valid" if server_session_status == "active" else server_session_reason,
            checked_at=checked_at,
            audit_event_id=server_session.get("audit_event_id"),
        )
        if server_session_status != "active":
            return _session_validation_result(
                server_session_status,
                server_session_reason,
                server_session=server_session,
            )
    return _session_validation_result(
        "valid",
        "session_cookie_valid",
        session_allowed=True,
        protected_start_page_allowed=True,
        issued_at=issued_at,
        expires_at=expires_at,
        ttl_remaining_seconds=expires_at - checked_at,
        server_session=server_session,
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
    if role_gate_reason in {"role_missing", "server_membership_missing", "server_membership_unavailable"}:
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


def _closed_role_gate(reason: str, *, required_role: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.oidc-role-gate/v0.1",
        "status": "closed",
        "reason": reason,
        "role": required_role,
        "session_allowed": False,
        "guardrails": _guardrails(),
    }


def _server_confirmed_role_gate(*, required_role: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.oidc-role-gate/v0.1",
        "status": "open",
        "reason": "server_membership_confirmed",
        "role": required_role,
        "session_allowed": True,
        "guardrails": _guardrails(),
    }


def _resolve_server_role_membership(
    *,
    resolver: Callable[..., dict[str, Any]] | None,
    claims: dict[str, Any],
    required_role: str,
) -> dict[str, Any] | None:
    if resolver is None:
        return None
    try:
        evidence = resolver(claims=claims, required_role=required_role)
    except Exception:
        return _role_evidence("unavailable", required_role=required_role)
    if not isinstance(evidence, dict):
        return _role_evidence("unavailable", required_role=required_role)
    status = str(evidence.get("status") or "")
    role = str(evidence.get("role") or "")
    if status in {"confirmed", "verified", "open"} and hmac.compare_digest(role, required_role):
        return _role_evidence("confirmed", required_role=required_role)
    if status == "missing":
        return _role_evidence("missing", required_role=required_role)
    return _role_evidence(
        "unavailable",
        required_role=required_role,
        failure_class=_safe_role_lookup_failure_class(evidence.get("failure_class")),
    )


def _role_evidence(status: str, *, required_role: str, failure_class: str = "") -> dict[str, Any]:
    evidence = {
        "schema_version": "nac.server-role-evidence/v0.1",
        "status": status,
        "role": required_role,
        "contains_credentials": False,
        "tokens_returned": False,
        "claims_exposed": False,
        "provider_details_exposed": False,
    }
    safe_failure_class = _safe_role_lookup_failure_class(failure_class)
    if status == "unavailable" and safe_failure_class:
        evidence["failure_class"] = safe_failure_class
    return evidence


def _safe_role_lookup_failure_class(value: Any) -> str:
    failure_class = str(value or "")
    if failure_class in {
        "idp_lookup_client_error",
        "idp_lookup_forbidden",
        "idp_lookup_http_error",
        "idp_lookup_network_error",
        "idp_lookup_server_error",
        "idp_lookup_timeout",
        "idp_lookup_unavailable",
        "idp_lookup_unauthorized",
    }:
        return failure_class
    return ""


def _result(
    *,
    status: str,
    token_exchange: dict[str, str],
    claim_boundary: dict[str, Any],
    role_gate: dict[str, Any],
    session_allowed: bool,
    jwt_validation_status: str,
    issued_session: dict[str, Any] | None = None,
    role_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = {
        "session_allowed": bool(session_allowed),
        "cookie_issued": bool(issued_session),
        "workspace_opened": False,
    }
    if issued_session:
        session.update(issued_session)
    result = {
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
    if role_evidence is not None:
        result["role_evidence"] = role_evidence
    return result


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
    server_session: dict[str, Any] | None = None,
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
    result = {
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
    if server_session is not None:
        result["server_session"] = server_session
    return result


def _validate_server_session_record(
    *,
    session_store: Mapping[str, Mapping[str, Any]] | RuntimeSessionStoreAdapter,
    session_id: str,
    checked_at: int,
) -> dict[str, Any]:
    record = _lookup_server_session_record(session_store=session_store, session_id=session_id)
    if record is _SESSION_STORE_UNAVAILABLE:
        return _server_session_result("unavailable", "server_session_store_unavailable")
    if not isinstance(record, Mapping):
        return _server_session_result("missing", "server_session_missing")
    if not _record_boolean_is_false(record, "contains_credentials"):
        return _server_session_result("invalid", "server_session_unsafe")
    if not _record_boolean_is_false(record, "tokens_stored"):
        return _server_session_result("invalid", "server_session_unsafe")
    if not _record_boolean_is_false(record, "claims_stored"):
        return _server_session_result("invalid", "server_session_unsafe")
    recorded_session_id = record.get("session_id")
    if isinstance(recorded_session_id, str) and recorded_session_id and recorded_session_id != session_id:
        return _server_session_result("invalid", "server_session_mismatch")
    audit_event_id = _safe_audit_event_id(record.get("audit_event_id"))
    revoked_at = _integer_or_none(record.get("revoked_at"))
    if revoked_at is not None and revoked_at <= checked_at:
        return _server_session_result("revoked", "server_session_revoked", audit_event_id=audit_event_id)
    expires_at = _integer_or_none(record.get("expires_at"))
    if expires_at is None:
        return _server_session_result("invalid", "server_session_time_invalid", audit_event_id=audit_event_id)
    if checked_at >= expires_at:
        return _server_session_result("expired", "server_session_expired", audit_event_id=audit_event_id)
    return _server_session_result(
        "active",
        "server_session_active",
        audit_event_id=audit_event_id,
        bindings=_server_session_bindings(record),
    )


_SESSION_STORE_UNAVAILABLE = object()


def _lookup_server_session_record(
    *,
    session_store: Mapping[str, Mapping[str, Any]] | RuntimeSessionStoreAdapter,
    session_id: str,
) -> Mapping[str, Any] | object | None:
    try:
        if hasattr(session_store, "get_session_record"):
            return session_store.get_session_record(session_id)  # type: ignore[union-attr]
        return session_store.get(session_id)  # type: ignore[union-attr]
    except Exception:
        return _SESSION_STORE_UNAVAILABLE


def _server_session_result(
    status: str,
    reason: str,
    *,
    audit_event_id: str = "",
    bindings: dict[str, bool] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "nac.server-session/v0.1",
        "status": status,
        "reason": reason,
        "record_required": True,
        "session_id_exposed": False,
        "contains_credentials": False,
        "tokens_stored": False,
        "claims_stored": False,
        "workspace_opened": False,
        "mandate_data_loaded": False,
    }
    if audit_event_id:
        result["audit_event_id"] = audit_event_id
    if bindings is not None:
        result["bindings"] = dict(bindings)
    return result


def _server_session_bindings(record: Mapping[str, Any]) -> dict[str, bool]:
    return {
        "tenant_bound": _record_boolean_is_true(record, "tenant_bound"),
        "subject_bound": _record_boolean_is_true(record, "subject_bound"),
        "role_bound": _record_boolean_is_true(record, "role_bound"),
        "case_bound": _record_boolean_is_true(record, "case_bound"),
        "purpose_bound": _record_boolean_is_true(record, "purpose_bound"),
    }


def _append_session_audit_event(
    *,
    audit_log: MutableSequence[dict[str, Any]] | None,
    status: str,
    reason: str,
    checked_at: int,
    audit_event_id: Any,
) -> None:
    if audit_log is None:
        return
    event = {
        "schema_version": "nac.session-audit/v0.1",
        "event_type": "session_validation",
        "status": status,
        "reason": reason,
        "checked_at": int(checked_at),
        "contains_credentials": False,
        "tokens_returned": False,
        "claims_exposed": False,
        "session_cookie_exposed": False,
        "workspace_opened": False,
        "mandate_data_loaded": False,
    }
    safe_audit_event_id = _safe_audit_event_id(audit_event_id)
    if safe_audit_event_id:
        event["audit_event_id"] = safe_audit_event_id
    audit_log.append(event)


def _record_boolean_is_false(record: Mapping[str, Any], key: str) -> bool:
    return record.get(key) is False


def _record_boolean_is_true(record: Mapping[str, Any], key: str) -> bool:
    return record.get(key) is True


def _safe_audit_event_id(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    stripped = value.strip()
    if not stripped:
        return ""
    return "".join(char for char in stripped[:80] if char.isalnum() or char in {"-", "_", "."})


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
