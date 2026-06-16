from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_EXCHANGE_SCHEMA_VERSION = "nac.oidc-token-exchange/v0.1"
_ALLOWED_STATUSES = {"not_started", "not_configured", "verified", "invalid", "failed", "unavailable"}
_CONTRACT_MODE = "contract_only"
_LIVE_EXCHANGE_MODE = "server_side_token_exchange"
_ALLOWED_MODES = {_CONTRACT_MODE, _LIVE_EXCHANGE_MODE}
OidcHttpPost = Callable[[str, bytes, dict[str, str], float], dict[str, object]]
OidcIdTokenVerifier = Callable[[str], dict[str, Any] | None]


class OidcTokenExchangeContract:
    def __init__(
        self,
        *,
        status: str,
        configuration: str,
        claims: dict[str, Any] | None = None,
        mode: str = _CONTRACT_MODE,
        live_token_exchange_performed: bool = False,
    ) -> None:
        self._status = status if status in _ALLOWED_STATUSES else "invalid"
        self._configuration = configuration
        self._claims = deepcopy(claims) if self._status == "verified" and isinstance(claims, dict) else None
        self._mode = mode if mode in _ALLOWED_MODES else _CONTRACT_MODE
        self._live_token_exchange_performed = bool(live_token_exchange_performed and self._mode == _LIVE_EXCHANGE_MODE)

    def __repr__(self) -> str:
        return f"OidcTokenExchangeContract(status={self._status!r}, claims=<redacted>)"

    def public_result(self) -> dict[str, Any]:
        return {
            "schema_version": TOKEN_EXCHANGE_SCHEMA_VERSION,
            "status": self._status,
            "configuration": self._configuration,
            "mode": self._mode,
            "guardrails": _guardrails(live_token_exchange_performed=self._live_token_exchange_performed),
        }

    def session_input(self) -> dict[str, Any]:
        result: dict[str, Any] = {"status": self._status}
        if self._claims is not None:
            result["claims"] = deepcopy(self._claims)
        return result


def build_oidc_token_exchange_contract(
    *,
    configured: bool,
    code: str,
    redirect_uri: str,
    token_endpoint: str,
    client_id: str,
    exchanger_result: dict[str, Any] | None = None,
) -> OidcTokenExchangeContract:
    if not configured:
        return OidcTokenExchangeContract(status="not_configured", configuration="not_configured")
    if not _required_metadata_present(redirect_uri=redirect_uri, token_endpoint=token_endpoint, client_id=client_id):
        return OidcTokenExchangeContract(status="not_configured", configuration="metadata_missing")
    if not code:
        return OidcTokenExchangeContract(status="not_started", configuration="configured")
    if exchanger_result is None:
        return OidcTokenExchangeContract(status="not_started", configuration="configured")
    if not isinstance(exchanger_result, dict):
        return OidcTokenExchangeContract(status="invalid", configuration="configured")

    status = _normalized_status(exchanger_result.get("status"))
    mode = _normalized_mode(exchanger_result.get("mode"))
    live_token_exchange_performed = bool(exchanger_result.get("live_token_exchange_performed"))
    if status != "verified":
        return OidcTokenExchangeContract(
            status=status,
            configuration="configured",
            mode=mode,
            live_token_exchange_performed=live_token_exchange_performed,
        )
    claims = exchanger_result.get("claims")
    if not isinstance(claims, dict):
        return OidcTokenExchangeContract(
            status="invalid",
            configuration="configured",
            mode=mode,
            live_token_exchange_performed=live_token_exchange_performed,
        )
    return OidcTokenExchangeContract(
        status="verified",
        configuration="configured",
        claims=claims,
        mode=mode,
        live_token_exchange_performed=live_token_exchange_performed,
    )


def exchange_oidc_authorization_code(
    *,
    code: str,
    redirect_uri: str,
    token_endpoint: str,
    client_id: str,
    client_secret: str,
    id_token_verifier: OidcIdTokenVerifier | None,
    http_post: OidcHttpPost | None = None,
    timeout_seconds: float = 5.0,
) -> dict[str, Any]:
    if not _required_metadata_present(redirect_uri=redirect_uri, token_endpoint=token_endpoint, client_id=client_id):
        return _exchange_result("not_configured", live_token_exchange_performed=False)
    if not _safe_non_empty_text(client_secret) or id_token_verifier is None:
        return _exchange_result("not_configured", live_token_exchange_performed=False)
    if not _safe_non_empty_text(code):
        return _exchange_result("not_started", live_token_exchange_performed=False)

    post_body = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    post = http_post or _urllib_http_post
    try:
        response = post(token_endpoint, post_body, headers, float(timeout_seconds))
    except Exception:
        return _exchange_result("unavailable", live_token_exchange_performed=True)

    try:
        status_code = int(response.get("status_code", 0))
    except (TypeError, ValueError, AttributeError):
        return _exchange_result("unavailable", live_token_exchange_performed=True)
    if status_code < 200 or status_code >= 300:
        return _exchange_result("failed", live_token_exchange_performed=True)

    token_payload = _json_body(response.get("body"))
    if not isinstance(token_payload, dict):
        return _exchange_result("invalid", live_token_exchange_performed=True)
    id_token = token_payload.get("id_token")
    if not _safe_non_empty_text(id_token):
        return _exchange_result("invalid", live_token_exchange_performed=True)

    try:
        claims = id_token_verifier(str(id_token))
    except Exception:
        return _exchange_result("invalid", live_token_exchange_performed=True)
    if not isinstance(claims, dict):
        return _exchange_result("invalid", live_token_exchange_performed=True)
    return _exchange_result("verified", live_token_exchange_performed=True, claims=claims)


def _normalized_status(value: Any) -> str:
    status = str(value or "invalid")
    if status not in _ALLOWED_STATUSES:
        return "invalid"
    return status


def _normalized_mode(value: Any) -> str:
    mode = str(value or _CONTRACT_MODE)
    if mode not in _ALLOWED_MODES:
        return _CONTRACT_MODE
    return mode


def _required_metadata_present(*, redirect_uri: str, token_endpoint: str, client_id: str) -> bool:
    values = (redirect_uri, token_endpoint, client_id)
    return all(isinstance(value, str) and value.strip() == value and bool(value) for value in values)


def _safe_non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and value.strip() == value and bool(value)


def _exchange_result(
    status: str,
    *,
    live_token_exchange_performed: bool,
    claims: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": _normalized_status(status),
        "mode": _LIVE_EXCHANGE_MODE,
        "live_token_exchange_performed": bool(live_token_exchange_performed),
        "guardrails": _guardrails(live_token_exchange_performed=live_token_exchange_performed),
    }
    if result["status"] == "verified" and isinstance(claims, dict):
        result["claims"] = deepcopy(claims)
    return result


def _json_body(body: object) -> object:
    if isinstance(body, str):
        raw = body.encode("utf-8")
    elif isinstance(body, bytes):
        raw = body
    else:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _urllib_http_post(url: str, body: bytes, headers: dict[str, str], timeout_seconds: float) -> dict[str, object]:
    request = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310 - target URL is server-side IdP config.
            return {
                "status_code": int(response.status),
                "body": response.read(),
            }
    except HTTPError as error:
        return {
            "status_code": int(error.code),
            "body": error.read(),
        }


def _guardrails(*, live_token_exchange_performed: bool) -> dict[str, bool]:
    return {
        "contains_credentials": False,
        "tokens_returned": False,
        "provider_error_details_exposed": False,
        "callback_values_exposed": False,
        "live_token_exchange_performed": bool(live_token_exchange_performed),
        "vault_secret_read": False,
    }
