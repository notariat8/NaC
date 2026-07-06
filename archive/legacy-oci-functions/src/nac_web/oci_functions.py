from __future__ import annotations

import io
import logging
import os
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from nac_identity.onboarding_requests import build_onboarding_request_store_from_env
from nac_identity.session_store import build_session_store_from_env
from nac_runtime.status_source import build_first_matter_runtime_metadata_source_from_env
from nac_web.server import NaCLocalWebApp


EXPOSED_GET_ROUTES = {
    "/",
    "/healthz",
    "/login",
    "/api/tenant/login-intent",
    "/onboarding/readiness",
    "/onboarding/dns-check",
}

STATEFUL_GET_ROUTES = {
    "/auth/callback",
    "/workspace",
    "/workspace/immobilienkaufvertrag",
}

EXPOSED_POST_ROUTES = {
    "/onboarding/requests",
}


@dataclass(frozen=True)
class OCIHttpResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes


def dispatch_oci_function_request(
    ctx: Any,
    data: io.BytesIO | None = None,
    *,
    repo_root: Path | None = None,
    expose_stateful_onboarding_routes: bool = True,
) -> OCIHttpResponse:
    _suppress_provider_sdk_debug_logs()
    request_url = _request_url(ctx)
    method = _request_method(ctx).upper()
    onboarding_request_store = (
        build_onboarding_request_store_from_env()
        if expose_stateful_onboarding_routes and _requires_onboarding_request_store(method, request_url)
        else None
    )
    session_store = (
        build_session_store_from_env()
        if expose_stateful_onboarding_routes and _requires_session_store(method, request_url)
        else None
    )
    app = NaCLocalWebApp(
        _repo_root(repo_root),
        onboarding_request_store=onboarding_request_store,
        session_store=session_store,
        first_matter_runtime_metadata_source=build_first_matter_runtime_metadata_source_from_env(),
    )

    response_headers: dict[str, str] = {}
    if method in {"GET", "HEAD"} and _is_exposed_get_route(
        request_url,
        expose_stateful_onboarding_routes=expose_stateful_onboarding_routes,
    ):
        app_response = app.handle(request_url, headers=_headers(ctx))
        status, content_type, response_body = app_response
        response_headers.update(getattr(app_response, "headers", {}))
        if method == "HEAD":
            response_body = b""
    elif method == "POST" and _is_exposed_post_route(
        request_url,
        expose_stateful_onboarding_routes=expose_stateful_onboarding_routes,
    ):
        app_response = app.handle_post(request_url, data.read() if data is not None else b"")
        status, content_type, response_body = app_response
        response_headers.update(getattr(app_response, "headers", {}))
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

    headers = {
        "Content-Type": content_type,
        "X-Content-Type-Options": "nosniff",
    }
    headers.update(response_headers)
    return OCIHttpResponse(status_code=int(status), headers=headers, body=response_body)


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


def _is_exposed_get_route(request_url: str, *, expose_stateful_onboarding_routes: bool = True) -> bool:
    parsed = urlparse(request_url)
    route = unquote(parsed.path) or "/"
    if route in EXPOSED_GET_ROUTES:
        return True
    if _is_bpmn_read_route(route):
        return True
    if expose_stateful_onboarding_routes and route in STATEFUL_GET_ROUTES:
        return True
    if route.startswith("/onboarding/requests/"):
        if not expose_stateful_onboarding_routes:
            return False
        params = parse_qs(parsed.query, keep_blank_values=True)
        return (params.get("audience") or [""])[0] == "customer"
    return False


def _is_bpmn_read_route(route: str) -> bool:
    if route == "/api/bpmn-moddle":
        return True
    segments = route.strip("/").split("/")
    if len(segments) == 2 and segments[0] == "bpmn" and segments[1]:
        return True
    if len(segments) == 3 and segments[0] == "bpmn" and segments[1] and segments[2] == "edit":
        return True
    if len(segments) == 3 and segments[0] == "api" and segments[1] == "bpmn" and segments[2]:
        return True
    if (
        len(segments) == 4
        and segments[0] == "api"
        and segments[1] == "bpmn"
        and segments[2]
        and segments[3] == "xml"
    ):
        return True
    return False


def _is_exposed_post_route(request_url: str, *, expose_stateful_onboarding_routes: bool = True) -> bool:
    if not expose_stateful_onboarding_routes:
        return False
    parsed = urlparse(request_url)
    route = unquote(parsed.path) or "/"
    return route in EXPOSED_POST_ROUTES


def _requires_onboarding_request_store(method: str, request_url: str) -> bool:
    parsed = urlparse(request_url)
    route = unquote(parsed.path) or "/"
    if method == "POST" and route == "/onboarding/requests":
        return True
    if method in {"GET", "HEAD"} and route.startswith("/onboarding/requests/"):
        params = parse_qs(parsed.query, keep_blank_values=True)
        return (params.get("audience") or [""])[0] == "customer"
    return False


def _requires_session_store(method: str, request_url: str) -> bool:
    if method not in {"GET", "HEAD"}:
        return False
    parsed = urlparse(request_url)
    route = unquote(parsed.path) or "/"
    return route in STATEFUL_GET_ROUTES


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


def _suppress_provider_sdk_debug_logs() -> None:
    for logger_name in ("oci", "oci.circuit_breaker", "urllib3", "urllib3.connectionpool"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)
