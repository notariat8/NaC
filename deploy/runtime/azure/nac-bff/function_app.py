from __future__ import annotations

import azure.functions as func

from nac_bff.composition import create_app_from_env


asgi_app = create_app_from_env()
app = func.AsgiFunctionApp(
    app=asgi_app,
    http_auth_level=func.AuthLevel.ANONYMOUS,
)
