from __future__ import annotations

from collections.abc import Iterable
import asyncio
from contextvars import ContextVar
from functools import partial
import math
import re
import threading
import time
from typing import Any, Callable
import uuid

from .test_environment import TestEnvironmentBff, ValidatedClaims
from .workbench_endpoint import WorkbenchEndpoint, WorkbenchResponse


REQUEST_TIMEOUT_SECONDS = 20.0
_REQUEST_DEADLINE: ContextVar[float | None] = ContextVar(
    "nac_bff_request_deadline", default=None
)


def create_fastapi_app(
    *,
    bff: TestEnvironmentBff,
    validated_claims_dependency: Callable[..., ValidatedClaims],
    workbench_endpoint: WorkbenchEndpoint | None = None,
    ready: bool = True,
) -> Any:
    """Create the ASGI adapter around already validated Entra claims.

    FastAPI is imported lazily so the domain package and its tests retain a
    standard-library-only dependency boundary. The injected dependency must
    validate signature, issuer, audience, tenant and token lifetime before it
    returns ``ValidatedClaims``.
    """

    try:
        from fastapi import Depends, FastAPI, Request
        from fastapi.responses import JSONResponse, Response
    except ImportError as exc:  # pragma: no cover - exercised by container wiring
        raise RuntimeError("FastAPI is available only in the nac-bff runtime image") from exc

    app = FastAPI(
        title="NaC M365 Test Environment BFF",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    readiness = _StagedReadiness(ready=ready)

    @app.middleware("http")
    async def request_boundary(request: Request, call_next):
        correlation_id = _correlation_id(request.headers.get("X-Correlation-ID"))
        request.state.correlation_id = correlation_id
        deadline_token = _REQUEST_DEADLINE.set(
            time.monotonic() + REQUEST_TIMEOUT_SECONDS
        )
        try:
            response = await call_next(request)
        except TimeoutError:
            response = (
                _workbench_http_response(Response, _workbench_error(503))
                if _is_workbench_path(request.url.path)
                else JSONResponse(
                    status_code=503,
                    content={"detail": "service unavailable"},
                )
            )
        except Exception:
            response = (
                _workbench_http_response(Response, _workbench_error(503))
                if _is_workbench_path(request.url.path)
                else JSONResponse(
                    status_code=500,
                    content={"detail": "internal server error"},
                )
            )
        finally:
            _REQUEST_DEADLINE.reset(deadline_token)
        if _is_workbench_path(request.url.path):
            if response.status_code == 401:
                authenticate = response.headers.get("WWW-Authenticate")
                response = _workbench_http_response(
                    Response,
                    _workbench_error(401),
                    authenticate=authenticate,
                )
            elif response.status_code == 403:
                response = _workbench_http_response(
                    Response,
                    _workbench_error(403),
                )
            elif response.status_code >= 500:
                response = _workbench_http_response(Response, _workbench_error(503))
        for name, value in _security_headers().items():
            response.headers[name] = value
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return JSONResponse(
            status_code=200,
            content={"status": "ok"},
            headers=_security_headers(),
        )

    @app.get("/readyz", include_in_schema=False)
    async def readyz():
        is_ready = readiness.is_ready()
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={"status": "ready" if is_ready else "unavailable"},
            headers=_security_headers(),
        )

    async def get_workspace(
        request: object,
        workspace_id: str,
        matter_id: str,
        claims: object = Depends(validated_claims_dependency),
    ):
        purpose, request_filters = _parse_workspace_query(
            request.query_params.multi_items()
        )
        response = await run_sync_with_request_budget(
            bff.get_workspace,
            claims=claims,
            workspace_id=workspace_id,
            matter_id=matter_id,
            purpose=purpose,
            request_filters=request_filters,
        )
        if response.status_code == 200:
            readiness.mark_ready()
        elif response.status_code == 503:
            readiness.mark_unavailable()
        return JSONResponse(
            status_code=response.status_code,
            content=response.body,
            headers=_security_headers(),
        )

    # ``Request`` is imported lazily, while postponed annotations otherwise
    # resolve only against module globals during FastAPI route registration.
    get_workspace.__annotations__["request"] = Request
    app.add_api_route(
        "/v1/workspaces/{workspace_id}/matters/{matter_id}",
        get_workspace,
        methods=["GET"],
    )

    if workbench_endpoint is not None:
        async def get_workbench_snapshot(
            request: object,
            workspace_id: str,
            matter_id: str,
            claims: object = Depends(validated_claims_dependency),
        ):
            purpose, request_filters = _parse_workspace_query(
                request.query_params.multi_items()
            )
            response = await run_sync_with_request_budget(
                workbench_endpoint.get_snapshot,
                claims=claims,
                workspace_id=workspace_id,
                matter_id=matter_id,
                purpose=purpose,
                request_filters=request_filters,
            )
            if response.status_code == 200:
                readiness.mark_ready()
            elif response.status_code == 503:
                readiness.mark_unavailable()
            return _workbench_http_response(Response, response)

        get_workbench_snapshot.__annotations__["request"] = Request
        app.add_api_route(
            "/v1/workspaces/{workspace_id}/matters/{matter_id}/workbench-snapshot",
            get_workbench_snapshot,
            methods=["GET"],
        )

    return app



async def run_sync_with_request_budget(
    function: Callable[..., Any],
    /,
    *args: object,
    **kwargs: object,
) -> Any:
    """Run blocking work off-loop with one request-local monotonic deadline."""

    deadline = _REQUEST_DEADLINE.get()
    if deadline is None:
        deadline = time.monotonic() + REQUEST_TIMEOUT_SECONDS
    remaining = deadline - time.monotonic()
    if not math.isfinite(remaining) or remaining <= 0:
        raise TimeoutError("request deadline exceeded")
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, partial(function, *args, **kwargs))
    try:
        return await asyncio.wait_for(asyncio.shield(future), timeout=remaining)
    except asyncio.TimeoutError:
        raise TimeoutError("request deadline exceeded") from None

def create_unconfigured_app() -> Any:
    """Return a fail-closed image smoke target.

    Production composition must inject a validated Entra claims dependency and
    concrete access/Graph ports. The base image deliberately serves no matter
    data until that composition is supplied.
    """

    from .test_environment import AccessDecision

    class _DenyAllAccess:
        def decide(self, **_: str) -> AccessDecision:
            return AccessDecision.deny()

    class _UnavailableGraph:
        def read_synthetic_workspace(self, **_: str) -> None:
            return None

    class _UnavailableBpmnAsset:
        def read_canonical_bpmn(self) -> None:
            return None

    async def _no_validated_claims() -> object:
        return None

    bff = TestEnvironmentBff(
        expected_tenant_id="unconfigured",
        access_decision_port=_DenyAllAccess(),
        graph_rest_port=_UnavailableGraph(),
        bpmn_asset_port=_UnavailableBpmnAsset(),
    )
    workbench_endpoint = WorkbenchEndpoint(
        expected_tenant_id="unconfigured",
        access_decision_port=_DenyAllAccess(),
        graph_rest_port=_UnavailableGraph(),
        bpmn_asset_port=_UnavailableBpmnAsset(),
    )
    return create_fastapi_app(
        bff=bff,
        workbench_endpoint=workbench_endpoint,
        validated_claims_dependency=_no_validated_claims,
        ready=False,
    )


def _parse_workspace_query(
    query_items: Iterable[tuple[str, str]],
) -> tuple[str, dict[str, bool]]:
    """Accept exactly one bounded ``purpose`` parameter and nothing else.

    The marker deliberately contains no request-controlled values. It lets the
    domain boundary return its generic unauthorized response for missing,
    duplicate, malformed or additional query parameters.
    """

    items = list(query_items)
    if len(items) == 1:
        key, value = items[0]
        if key == "purpose" and isinstance(value, str) and 1 <= len(value) <= 80:
            return value, {}
    return "", {"invalid_query_shape": True}


def _security_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }


def _workbench_error(status_code: int) -> WorkbenchResponse:
    if status_code == 401:
        code = "AUTHENTICATION_REQUIRED"
    elif status_code == 403:
        code = "ACCESS_DENIED"
    else:
        code = "SERVICE_UNAVAILABLE"
    body = {"status": status_code, "error": {"code": code}}
    body_bytes = (
        f'{{"status":{status_code},"error":{{"code":"{code}"}}}}'
    ).encode("ascii")
    return WorkbenchResponse(
        status_code=status_code,
        body=body,
        body_bytes=body_bytes,
    )


def _workbench_http_response(
    response_type: Any,
    response: WorkbenchResponse,
    *,
    authenticate: str | None = None,
) -> Any:
    headers = {
        **_security_headers(),
        "Content-Type": "application/json; charset=utf-8",
    }
    if authenticate:
        headers["WWW-Authenticate"] = authenticate
    return response_type(
        content=response.body_bytes,
        status_code=response.status_code,
        headers=headers,
        media_type=None,
    )


def _is_workbench_path(path: object) -> bool:
    return isinstance(path, str) and path.endswith("/workbench-snapshot")


class _StagedReadiness:
    """Cheap readiness state activated by a successful dependency-backed read."""

    def __init__(self, *, ready: bool) -> None:
        self._ready = bool(ready)
        self._lock = threading.Lock()

    def is_ready(self) -> bool:
        with self._lock:
            return self._ready

    def mark_ready(self) -> None:
        with self._lock:
            self._ready = True

    def mark_unavailable(self) -> None:
        with self._lock:
            self._ready = False


_CORRELATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def _correlation_id(value: object) -> str:
    if isinstance(value, str) and _CORRELATION_ID.fullmatch(value):
        return value
    return uuid.uuid4().hex
