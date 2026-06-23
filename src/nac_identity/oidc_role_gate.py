from __future__ import annotations

import hashlib
import hmac
from collections.abc import Iterable
from typing import Any


DEFAULT_REQUIRED_ROLE = "nac-tenant-admin"


def evaluate_oidc_role_gate(
    *,
    claims: dict[str, Any],
    expected_issuer: str,
    expected_audience: str,
    state_validation: dict[str, Any],
    required_role: str = DEFAULT_REQUIRED_ROLE,
) -> dict[str, Any]:
    if state_validation.get("status") != "valid":
        return _closed("state_invalid", required_role=required_role)
    if not state_validation.get("nonce_bound") or not state_validation.get("nonce_hash"):
        return _closed("nonce_not_bound", required_role=required_role)
    expected_issuer_value = _expected_value(expected_issuer)
    if not expected_issuer_value or _expected_value(claims.get("iss")) != expected_issuer_value:
        return _closed("issuer_mismatch", required_role=required_role)
    expected_audience_value = _expected_value(expected_audience)
    if not expected_audience_value or expected_audience_value not in _audiences(claims.get("aud")):
        return _closed("audience_mismatch", required_role=required_role)
    if not _nonce_matches(claims.get("nonce"), str(state_validation["nonce_hash"])):
        return _closed("nonce_mismatch", required_role=required_role)
    if required_role not in _roles(claims):
        return _closed("role_missing", required_role=required_role)

    return {
        "schema_version": "nac.oidc-role-gate/v0.1",
        "status": "open",
        "reason": "authorized",
        "role": required_role,
        "session_allowed": True,
        "guardrails": _guardrails(),
    }


def _closed(reason: str, *, required_role: str) -> dict[str, Any]:
    return {
        "schema_version": "nac.oidc-role-gate/v0.1",
        "status": "closed",
        "reason": reason,
        "role": required_role,
        "session_allowed": False,
        "guardrails": _guardrails(),
    }


def _guardrails() -> dict[str, bool]:
    return {
        "contains_credentials": False,
        "tokens_returned": False,
        "callback_values_exposed": False,
        "workspace_opened": False,
    }


def _audiences(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value} if value else set()
    return set(_string_items(value))


def _roles(claims: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    for key in ("groups", "roles", "group", "role"):
        roles.update(_string_items(claims.get(key)))
    return roles


def _string_items(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if value:
            yield value
        return
    if isinstance(value, dict):
        for key in ("value", "name", "display", "displayName"):
            item = value.get(key)
            if isinstance(item, str) and item:
                yield item
        return
    if isinstance(value, Iterable):
        for item in value:
            yield from _string_items(item)


def _nonce_matches(nonce: Any, expected_hash: str) -> bool:
    if not isinstance(nonce, str) or not nonce or nonce != nonce.strip():
        return False
    supplied_hash = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
    return hmac.compare_digest(supplied_hash, expected_hash)


def _expected_value(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        return ""
    return value.rstrip("/")
