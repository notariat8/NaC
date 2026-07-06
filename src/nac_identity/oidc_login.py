from __future__ import annotations

import secrets
from urllib.parse import urlencode, urlparse

from .oidc_state import DEFAULT_STATE_TTL_SECONDS, build_signed_state


DEFAULT_OIDC_SCOPES = ("openid", "profile", "email")


def build_login_intent(
    *,
    tenant_hint: str,
    issuer_url: str,
    client_id: str,
    redirect_uri: str,
    scopes: tuple[str, ...] = DEFAULT_OIDC_SCOPES,
    state_signing_key: str | None = None,
    now: int | None = None,
    state_ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS,
) -> dict:
    issuer = _normalize_issuer_url(issuer_url)
    normalized_client_id = _normalize_client_id(client_id)
    normalized_redirect_uri = _normalize_redirect_uri(redirect_uri)
    normalized_hint = tenant_hint.strip()[:120]
    normalized_nonce = _server_nonce("nonce")
    if state_signing_key:
        normalized_state = build_signed_state(
            tenant_hint=normalized_hint,
            signing_key=state_signing_key,
            nonce=normalized_nonce,
            now=now,
            ttl_seconds=state_ttl_seconds,
        )
        state_binding = {
            "status": "signed",
            "ttl_seconds": state_ttl_seconds,
            "tenant_hint_bound": True,
            "nonce_bound": True,
        }
    else:
        normalized_state = _server_nonce("state")
        state_binding = {
            "status": "opaque_server_generated",
            "ttl_seconds": None,
            "tenant_hint_bound": False,
            "nonce_bound": False,
        }
    scope = " ".join(scope.strip() for scope in scopes if scope.strip())
    if "openid" not in scope.split():
        raise ValueError("scope_openid_missing")

    endpoints = _oidc_endpoints_from_issuer(issuer)
    authorization_params = {
        "response_type": "code",
        "client_id": normalized_client_id,
        "redirect_uri": normalized_redirect_uri,
        "scope": scope,
        "state": normalized_state,
        "nonce": normalized_nonce,
    }

    return {
        "schema_version": "nac.oidc-login-intent/v0.1",
        "mode": "authorization_code_redirect_intent",
        "provider": _provider_from_issuer(issuer),
        "tenant_context": {
            "tenant_hint": normalized_hint,
            "tenant_authorized_by_hint": False,
        },
        "endpoints": {
            "issuer_url": issuer,
            "discovery_endpoint": f"{issuer}/.well-known/openid-configuration",
            "authorization_endpoint": endpoints["authorization_endpoint"],
            "token_endpoint": endpoints["token_endpoint"],
        },
        "oidc": {
            "response_type": "code",
            "scope": scope,
            "client_id": normalized_client_id,
            "redirect_uri": normalized_redirect_uri,
            "state": normalized_state,
            "nonce": normalized_nonce,
        },
        "state_binding": state_binding,
        "authorization_url": f"{endpoints['authorization_endpoint']}?{urlencode(authorization_params)}",
        "guardrails": {
            "contains_credentials": False,
            "server_generated_state_required": True,
            "server_generated_nonce_required": True,
            "tenant_hint_is_authorization": False,
            "nac_role_gate_required_after_idp_login": True,
            "end_user_identity_console_work_allowed": False,
        },
        "next_step": "redirect_to_oidc_idp_then_validate_callback_and_apply_nac_role_gate",
    }


def _required_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field}_empty")
    return normalized


def _normalize_client_id(value: str) -> str:
    normalized = _required_text(value, "client_id")
    if normalized in {"nac-local-preview", "local-preview", "demo", "example"}:
        raise ValueError("client_id_placeholder")
    return normalized


def _normalize_issuer_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("issuer_url_invalid")
    hostname = parsed.hostname or ""
    if _is_placeholder_issuer_host(hostname):
        raise ValueError("issuer_url_placeholder")
    if raw.endswith("/oauth2/v2.0") and _is_entra_host(hostname):
        raw = raw.removesuffix("/oauth2/v2.0").rstrip("/") + "/v2.0"
    return raw


def _normalize_redirect_uri(value: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("redirect_uri_invalid")
    return raw


def _oidc_endpoints_from_issuer(issuer: str) -> dict[str, str]:
    parsed = urlparse(issuer)
    hostname = (parsed.hostname or "").lower()
    if _is_entra_host(hostname) and parsed.path.rstrip("/").endswith("/v2.0"):
        tenant_base = issuer.removesuffix("/v2.0").rstrip("/")
        return {
            "authorization_endpoint": f"{tenant_base}/oauth2/v2.0/authorize",
            "token_endpoint": f"{tenant_base}/oauth2/v2.0/token",
        }
    return {
        "authorization_endpoint": f"{issuer}/oauth2/v1/authorize",
        "token_endpoint": f"{issuer}/oauth2/v1/token",
    }


def _provider_from_issuer(issuer: str) -> str:
    parsed = urlparse(issuer)
    return "microsoft_entra_id" if _is_entra_host((parsed.hostname or "").lower()) else "oidc"


def _is_entra_host(hostname: str) -> bool:
    return hostname in {"login.microsoftonline.com", "login.windows.net", "sts.windows.net"}


def _is_placeholder_issuer_host(hostname: str) -> bool:
    normalized = hostname.lower().strip(".")
    return (
        normalized in {"example.com", "example.invalid", "example.net", "example.org"}
        or ".example." in normalized
        or normalized.endswith(".invalid")
    )


def _server_nonce(prefix: str) -> str:
    return f"{prefix}-{secrets.token_urlsafe(24)}"
