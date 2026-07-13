from __future__ import annotations

from typing import Any, Callable

from .test_environment import TestEnvironmentBff, ValidatedClaims


def create_fastapi_app(
    *,
    bff: TestEnvironmentBff,
    validated_claims_dependency: Callable[..., ValidatedClaims],
) -> Any:
    """Create the ASGI adapter around already validated Entra claims.

    FastAPI is imported lazily so the domain package and its tests retain a
    standard-library-only dependency boundary. The injected dependency must
    validate signature, issuer, audience, tenant and token lifetime before it
    returns ``ValidatedClaims``.
    """

    try:
        from fastapi import Depends, FastAPI, Query
        from fastapi.responses import JSONResponse
    except ImportError as exc:  # pragma: no cover - exercised by container wiring
        raise RuntimeError("FastAPI is available only in the nac-bff runtime image") from exc

    app = FastAPI(
        title="NaC M365 Test Environment BFF",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/healthz", include_in_schema=False)
    async def healthz():
        return JSONResponse(
            status_code=200,
            content={"status": "ok"},
            headers=_security_headers(),
        )

    @app.get("/v1/workspaces/{workspace_id}/matters/{matter_id}")
    async def get_workspace(
        workspace_id: str,
        matter_id: str,
        purpose: str = Query(..., min_length=1, max_length=80),
        claims: object = Depends(validated_claims_dependency),
    ):
        response = bff.get_workspace(
            claims=claims,
            workspace_id=workspace_id,
            matter_id=matter_id,
            purpose=purpose,
        )
        return JSONResponse(
            status_code=response.status_code,
            content=response.body,
            headers=_security_headers(),
        )

    return app


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

    async def _no_validated_claims() -> object:
        return None

    bff = TestEnvironmentBff(
        expected_tenant_id="unconfigured",
        access_decision_port=_DenyAllAccess(),
        graph_rest_port=_UnavailableGraph(),
    )
    return create_fastapi_app(bff=bff, validated_claims_dependency=_no_validated_claims)


def _security_headers() -> dict[str, str]:
    return {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
    }
