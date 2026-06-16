from __future__ import annotations

from copy import deepcopy
from typing import Any


TOKEN_EXCHANGE_SCHEMA_VERSION = "nac.oidc-token-exchange/v0.1"
_ALLOWED_STATUSES = {"not_started", "not_configured", "verified", "invalid", "failed", "unavailable"}


class OidcTokenExchangeContract:
    def __init__(self, *, status: str, configuration: str, claims: dict[str, Any] | None = None) -> None:
        self._status = status if status in _ALLOWED_STATUSES else "invalid"
        self._configuration = configuration
        self._claims = deepcopy(claims) if self._status == "verified" and isinstance(claims, dict) else None

    def __repr__(self) -> str:
        return f"OidcTokenExchangeContract(status={self._status!r}, claims=<redacted>)"

    def public_result(self) -> dict[str, Any]:
        return {
            "schema_version": TOKEN_EXCHANGE_SCHEMA_VERSION,
            "status": self._status,
            "configuration": self._configuration,
            "mode": "contract_only",
            "guardrails": _guardrails(),
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
    if status != "verified":
        return OidcTokenExchangeContract(status=status, configuration="configured")
    claims = exchanger_result.get("claims")
    if not isinstance(claims, dict):
        return OidcTokenExchangeContract(status="invalid", configuration="configured")
    return OidcTokenExchangeContract(status="verified", configuration="configured", claims=claims)


def _normalized_status(value: Any) -> str:
    status = str(value or "invalid")
    if status not in _ALLOWED_STATUSES:
        return "invalid"
    return status


def _required_metadata_present(*, redirect_uri: str, token_endpoint: str, client_id: str) -> bool:
    values = (redirect_uri, token_endpoint, client_id)
    return all(isinstance(value, str) and value.strip() == value and bool(value) for value in values)


def _guardrails() -> dict[str, bool]:
    return {
        "contains_credentials": False,
        "tokens_returned": False,
        "provider_error_details_exposed": False,
        "callback_values_exposed": False,
        "live_token_exchange_performed": False,
        "vault_secret_read": False,
    }
