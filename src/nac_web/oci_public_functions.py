from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from nac_web.oci_functions import OCIHttpResponse, dispatch_oci_function_request


def dispatch_oci_public_function_request(
    ctx: Any,
    data: io.BytesIO | None = None,
    *,
    repo_root: Path | None = None,
) -> OCIHttpResponse:
    return dispatch_oci_function_request(
        ctx,
        data,
        repo_root=repo_root,
        expose_stateful_onboarding_routes=False,
    )


def handler(ctx: Any, data: io.BytesIO | None = None) -> Any:
    result = dispatch_oci_public_function_request(ctx, data)
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
