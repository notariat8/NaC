from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class AccessTokenProvider(Protocol):
    def fetch_access_token(self) -> str:
        ...


class GraphHttpError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"Microsoft Graph request failed with HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


@dataclass(frozen=True, slots=True)
class GraphRestClient:
    token_provider: AccessTokenProvider
    base_url: str = "https://graph.microsoft.com/v1.0"

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.base_url != "https://graph.microsoft.com/v1.0":
            raise ValueError("Only https://graph.microsoft.com/v1.0 is allowed")
        if not path.startswith("/"):
            raise ValueError("Graph REST path must start with /")
        if path.startswith("/_api") or "/_api/" in path:
            raise ValueError("Legacy SharePoint REST paths are blocked")

        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token_provider.fetch_access_token()}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read().decode("utf-8")
                if not response_body:
                    return {}
                return json.loads(response_body)
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise GraphHttpError(exc.code, error_body) from exc

    def get(self, path: str) -> dict[str, Any]:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", path, payload)

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", path, payload)


def encode_path_segment(value: str) -> str:
    return urllib.parse.quote(value, safe="")
