from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


DEFAULT_STATE_TTL_SECONDS = 600


def build_signed_state(
    *,
    tenant_hint: str,
    signing_key: str,
    nonce: str | None = None,
    now: int | None = None,
    ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS,
) -> str:
    normalized_key = _required_signing_key(signing_key)
    issued_at = int(time.time() if now is None else now)
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds_invalid")
    payload = {
        "v": 1,
        "tenant_hint": tenant_hint.strip()[:120],
        "iat": issued_at,
        "exp": issued_at + int(ttl_seconds),
        "jti": secrets.token_urlsafe(18),
    }
    nonce_hash = _nonce_hash(nonce)
    if nonce_hash:
        payload["nonce_hash"] = nonce_hash
    encoded_payload = _b64url_encode(_canonical_json(payload))
    signature = _sign(encoded_payload, normalized_key)
    return f"state.{encoded_payload}.{signature}"


def validate_signed_state(state: str, *, signing_key: str, now: int | None = None) -> dict[str, Any]:
    normalized_key = _required_signing_key(signing_key)
    checked_at = int(time.time() if now is None else now)
    guardrails = {
        "contains_credentials": False,
        "state_value_returned": False,
        "signing_key_returned": False,
    }
    if not isinstance(state, str):
        return {"schema_version": "nac.oidc-state/v0.1", "status": "invalid", "guardrails": guardrails}
    try:
        prefix, encoded_payload, supplied_signature = state.split(".", 2)
        if prefix != "state":
            raise ValueError("state_prefix_invalid")
        expected_signature = _sign(encoded_payload, normalized_key)
        if not hmac.compare_digest(supplied_signature, expected_signature):
            return {"schema_version": "nac.oidc-state/v0.1", "status": "invalid", "guardrails": guardrails}
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
        if int(payload["v"]) != 1:
            raise ValueError("state_version_invalid")
        issued_at = int(payload["iat"])
        expires_at = int(payload["exp"])
        if checked_at < issued_at:
            return {"schema_version": "nac.oidc-state/v0.1", "status": "invalid", "guardrails": guardrails}
        if checked_at >= expires_at:
            return {
                "schema_version": "nac.oidc-state/v0.1",
                "status": "expired",
                "issued_at": issued_at,
                "expires_at": expires_at,
                "guardrails": guardrails,
            }
        return {
            "schema_version": "nac.oidc-state/v0.1",
            "status": "valid",
            "tenant_hint": str(payload.get("tenant_hint", ""))[:120],
            "nonce_bound": bool(payload.get("nonce_hash")),
            **({"nonce_hash": str(payload["nonce_hash"])} if payload.get("nonce_hash") else {}),
            "issued_at": issued_at,
            "expires_at": expires_at,
            "guardrails": guardrails,
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {"schema_version": "nac.oidc-state/v0.1", "status": "invalid", "guardrails": guardrails}


def _required_signing_key(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("state_signing_key_empty")
    return normalized


def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign(encoded_payload: str, signing_key: str) -> str:
    digest = hmac.new(signing_key.encode("utf-8"), encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _nonce_hash(nonce: str | None) -> str:
    normalized = (nonce or "").strip()
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
