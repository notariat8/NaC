from __future__ import annotations

import io
import os
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from nac_web.server import NaCLocalWebApp


EXPOSED_GET_ROUTES = {
    "/",
    "/healthz",
    "/login",
    "/onboarding/readiness",
    "/onboarding/dns-check",
}


@dataclass(frozen=True)
class OCIHttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


def dispatch_oci_function_request(ctx: Any, data: io.BytesIO | None = None, *, repo_root: Path | None = None) -> OCIHttpResponse:
    request_url = _request_url(ctx)
    method = _request_method(ctx).upper()
    app = NaCLocalWebApp(_repo_root(repo_root))

    if method in {"GET", "HEAD"} and _is_exposed_get_route(request_url):
        status, content_type, response_body = app.handle(request_url)
        if method == "HEAD":
            response_body = b""
    elif method in {"GET", "HEAD"}:
        status = HTTPStatus.NOT_FOUND
        content_type = "application/json; charset=utf-8"
        response_body = b'{"error": "Route is not exposed by the OCI Functions public runtime."}'
    else:
        status = HTTPStatus.METHOD_NOT_ALLOWED
        content_type = "application/json; charset=utf-8"
        response_body = (
            b'{"error": "OCI Functions public runtime is read-only in this release slice."}'
        )

    return OCIHttpResponse(
        status_code=int(status),
        headers={
            "Content-Type": content_type,
            "X-Content-Type-Options": "nosniff",
        },
        body=response_body,
    )


def handler(ctx: Any, data: io.BytesIO | None = None) -> Any:
    result = dispatch_oci_function_request(ctx, data)
    try:
        from fdk import response
    except ImportError:
        return result
    return response.Response(
        ctx,
        response_data=result.body,
        headers=result.headers,
        status_code=result.status_code,
    )


def _repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root
    configured = os.environ.get("NAC_REPO_ROOT")
    if configured:
        return Path(configured)
    return Path.cwd()


def _request_method(ctx: Any) -> str:
    method = _call_context_method(ctx, "Method")
    if method:
        return method
    headers = _headers(ctx)
    return headers.get("fn-http-method") or headers.get("Fn-Http-Method") or "GET"


def _request_url(ctx: Any) -> str:
    request_url = _call_context_method(ctx, "RequestURL")
    if request_url:
        return request_url
    headers = _headers(ctx)
    return headers.get("fn-http-request-url") or headers.get("Fn-Http-Request-Url") or "/"


def _is_exposed_get_route(request_url: str) -> bool:
    parsed = urlparse(request_url)
    route = unquote(parsed.path) or "/"
    return route in EXPOSED_GET_ROUTES


def _headers(ctx: Any) -> dict[str, str]:
    raw_headers = _call_context_method(ctx, "Headers")
    if not isinstance(raw_headers, dict):
        return {}
    return {str(key): str(value) for key, value in raw_headers.items()}


def _call_context_method(ctx: Any, name: str) -> Any:
    candidate = getattr(ctx, name, None)
    if callable(candidate):
        return candidate()
    return None
