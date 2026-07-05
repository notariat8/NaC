from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class GraphConfigError(ValueError):
    """Raised when required Microsoft 365 Graph configuration is missing."""


@dataclass(frozen=True, slots=True)
class GraphConfig:
    tenant_id: str
    client_id: str
    client_credential: str
    graph_base_url: str = "https://graph.microsoft.com/v1.0"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "GraphConfig":
        values = env or os.environ
        tenant_id = values.get("M365_TENANT_ID", "").strip()
        client_id = values.get("M365_PROVISIONER_CLIENT_ID", "").strip()
        client_credential = values.get("M365_PROVISIONER_CLIENT_SECRET", "").strip()
        graph_base_url = values.get("M365_GRAPH_BASE_URL", "https://graph.microsoft.com/v1.0").strip()

        missing = [
            name
            for name, value in (
                ("M365_TENANT_ID", tenant_id),
                ("M365_PROVISIONER_CLIENT_ID", client_id),
                ("M365_PROVISIONER_CLIENT_SECRET", client_credential),
            )
            if not value
        ]
        if missing:
            raise GraphConfigError("missing Microsoft 365 environment values: " + ", ".join(missing))
        if graph_base_url != "https://graph.microsoft.com/v1.0":
            raise GraphConfigError("M365_GRAPH_BASE_URL must be https://graph.microsoft.com/v1.0")
        return cls(
            tenant_id=tenant_id,
            client_id=client_id,
            client_credential=client_credential,
            graph_base_url=graph_base_url,
        )


class ClientCredentialsTokenProvider:
    def __init__(self, config: GraphConfig):
        self.config = config

    def fetch_access_token(self) -> str:
        endpoint = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"
        form = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_credential,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials",
        }
        request = urllib.request.Request(
            endpoint,
            data=urllib.parse.urlencode(form).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise GraphConfigError("token response did not contain access_token")
        return token


class StaticAccessTokenProvider:
    def __init__(self, token: str):
        token = token.strip()
        if not token:
            raise GraphConfigError("Microsoft Graph access token is empty")
        self._token = token

    def fetch_access_token(self) -> str:
        return self._token


def token_provider_from_env(env: Mapping[str, str] | None = None) -> ClientCredentialsTokenProvider | StaticAccessTokenProvider:
    values = env or os.environ
    inline_token = values.get("M365_GRAPH_ACCESS_TOKEN", "").strip()
    token_file = values.get("M365_GRAPH_ACCESS_TOKEN_FILE", "").strip()
    if inline_token and token_file:
        raise GraphConfigError("set only one of M365_GRAPH_ACCESS_TOKEN or M365_GRAPH_ACCESS_TOKEN_FILE")
    if token_file:
        try:
            return StaticAccessTokenProvider(Path(token_file).expanduser().read_text(encoding="utf-8"))
        except OSError as exc:
            raise GraphConfigError(f"cannot read M365_GRAPH_ACCESS_TOKEN_FILE: {exc}") from exc
    if inline_token:
        return StaticAccessTokenProvider(inline_token)
    return ClientCredentialsTokenProvider(GraphConfig.from_env(values))
