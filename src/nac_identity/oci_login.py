from __future__ import annotations

import secrets
from urllib.parse import urlencode, urlparse

from .oidc_state import DEFAULT_STATE_TTL_SECONDS, build_signed_state


DEFAULT_OIDC_SCOPES = ("openid", "profile", "email")


def build_login_intent(
    *,
    tenant_hint: str,
    identity_domain_url: str,
    client_id: str,
    redirect_uri: str,
    scopes: tuple[str, ...] = DEFAULT_OIDC_SCOPES,
    state_signing_key: str | None = None,
    now: int | None = None,
    state_ttl_seconds: int = DEFAULT_STATE_TTL_SECONDS,
) -> dict:
    base_url = _normalize_identity_domain_url(identity_domain_url)
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

    authorization_endpoint = f"{base_url}/oauth2/v1/authorize"
    authorization_params = {
        "response_type": "code",
        "client_id": normalized_client_id,
        "redirect_uri": normalized_redirect_uri,
        "scope": scope,
        "state": normalized_state,
        "nonce": normalized_nonce,
    }

    return {
        "schema_version": "nac.oci-login-intent/v0.1",
        "mode": "authorization_code_redirect_intent",
        "provider": "oracle_oci_identity_domains",
        "tenant_context": {
            "tenant_hint": normalized_hint,
            "tenant_authorized_by_hint": False,
        },
        "endpoints": {
            "identity_domain_url": base_url,
            "discovery_endpoint": f"{base_url}/.well-known/openid-configuration",
            "authorization_endpoint": authorization_endpoint,
            "token_endpoint": f"{base_url}/oauth2/v1/token",
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
        "authorization_url": f"{authorization_endpoint}?{urlencode(authorization_params)}",
        "guardrails": {
            "contains_credentials": False,
            "server_generated_state_required": True,
            "server_generated_nonce_required": True,
            "tenant_hint_is_authorization": False,
            "nac_role_gate_required_after_idp_login": True,
            "end_user_oci_console_work_allowed": False,
        },
        "next_step": "redirect_to_oci_idp_then_validate_callback_and_apply_nac_role_gate",
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


def _normalize_identity_domain_url(value: str) -> str:
    raw = value.strip().rstrip("/")
    if raw.endswith("/admin/v1"):
        raw = raw.removesuffix("/admin/v1").rstrip("/")
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("identity_domain_url_invalid")
    hostname = parsed.hostname or ""
    if not _is_oci_identity_domain_host(hostname):
        raise ValueError("identity_domain_url_not_oci_identity_domain")
    if _is_placeholder_identity_domain_host(hostname):
        raise ValueError("identity_domain_url_placeholder")
    return raw


def _normalize_redirect_uri(value: str) -> str:
    raw = value.strip()
    parsed = urlparse(raw)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("redirect_uri_invalid")
    return raw


def _is_oci_identity_domain_host(hostname: str) -> bool:
    return hostname.endswith(".identity.oraclecloud.com") or (
        ".identity." in hostname and hostname.endswith(".oci.oraclecloud.com")
    )


def _is_placeholder_identity_domain_host(hostname: str) -> bool:
    normalized = hostname.lower().strip(".")
    return normalized.startswith("idcs.example.") or ".example." in normalized


def _server_nonce(prefix: str) -> str:
    return f"{prefix}-{secrets.token_urlsafe(24)}"
