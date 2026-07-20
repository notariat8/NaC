from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
import math
import os
import threading
import time
from typing import Any

from .bpmn_asset import CanonicalBpmnAssetFilePort
from .entra_access_token import build_entra_access_token_validator
from .fastapi_adapter import (
    create_fastapi_app,
    create_unconfigured_app,
    run_sync_with_request_budget,
)
from .live_access_decision import LiveAccessDecisionAdapter
from .synthetic_workspace_graph import (
    GRAPH_TOKEN_ACQUISITION_TIMEOUT_SECONDS,
    RawGraphV1Client,
    SyntheticWorkspaceGraphRestAdapter,
)
from .test_environment import TestEnvironmentBff, ValidatedClaims


_ENTRA_JWKS_URI = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
_GRAPH_SCOPE = "https://graph.microsoft.com/.default"
_TOKEN_REFRESH_SKEW_SECONDS = 60.0

# Stable composition-root export; the implementation retains the fixed
# workspace/site/list allowlist enforced by the Graph adapter.
ConfiguredGraphRestPort = SyntheticWorkspaceGraphRestAdapter


class CompositionError(ValueError):
    """Raised when trusted runtime configuration cannot compose the BFF."""


class ManagedIdentityGraphTokenProvider:
    """Bounded, cached Graph token adapter for an Azure user-assigned identity."""

    def __init__(
        self,
        credential: Any,
        *,
        wall_clock: Callable[[], float] = time.time,
    ) -> None:
        if not callable(getattr(credential, "get_token", None)):
            raise CompositionError("managed identity credential is unavailable")
        if not callable(wall_clock):
            raise CompositionError("managed identity clock is unavailable")
        self._credential = credential
        self._wall_clock = wall_clock
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="nac-bff-managed-identity",
        )
        self._lock = threading.Lock()
        self._cached_token: str | None = None
        self._expires_on = 0.0

    def fetch_access_token(self) -> str:
        return self.fetch_access_token_with_timeout(
            timeout_seconds=GRAPH_TOKEN_ACQUISITION_TIMEOUT_SECONDS
        )

    def fetch_access_token_with_timeout(self, *, timeout_seconds: float) -> str:
        timeout = _bounded_seconds(
            timeout_seconds,
            maximum=GRAPH_TOKEN_ACQUISITION_TIMEOUT_SECONDS,
        )
        with _bounded_lock(self._lock, timeout) as timeout_deadline:
            now = self._clock_value()
            if (
                self._cached_token is not None
                and self._expires_on - now > _TOKEN_REFRESH_SKEW_SECONDS
            ):
                return self._cached_token
            future = self._executor.submit(self._credential.get_token, _GRAPH_SCOPE)
            try:
                access_token = future.result(timeout=_remaining_timeout(timeout_deadline))
            except FutureTimeoutError:
                future.cancel()
                raise TimeoutError("managed identity token acquisition timed out") from None
            token = getattr(access_token, "token", None)
            expires_on = getattr(access_token, "expires_on", None)
            if (
                not isinstance(token, str)
                or not token
                or len(token) > 8192
                or "\n" in token
                or "\r" in token
                or isinstance(expires_on, bool)
                or not isinstance(expires_on, (int, float))
                or not math.isfinite(float(expires_on))
                or float(expires_on) <= now
            ):
                raise CompositionError("managed identity token is invalid")
            self._cached_token = token
            self._expires_on = float(expires_on)
            return token

    def _clock_value(self) -> float:
        value = self._wall_clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CompositionError("managed identity clock is invalid")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise CompositionError("managed identity clock is invalid")
        return numeric


def managed_identity_token_provider_from_env(
    env: Mapping[str, str],
    *,
    credential_factory: Callable[..., Any] | None = None,
) -> ManagedIdentityGraphTokenProvider:
    client_id = _aliased_value(
        env,
        primary="NAC_BFF_GRAPH_MANAGED_IDENTITY_CLIENT_ID",
        secondary="AZURE_CLIENT_ID",
    )
    if credential_factory is None:
        try:
            from azure.identity import ManagedIdentityCredential
        except ImportError as exc:
            raise CompositionError("azure-identity is unavailable") from exc
        credential_factory = ManagedIdentityCredential
    try:
        credential = credential_factory(client_id=client_id)
    except Exception:
        raise CompositionError("managed identity credential is unavailable") from None
    return ManagedIdentityGraphTokenProvider(credential)


@dataclass(frozen=True, slots=True)
class BffSettings:
    tenant_id: str
    audience: str
    required_scope: str

    @property
    def issuer(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def jwks_uri(self) -> str:
        return _ENTRA_JWKS_URI

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> BffSettings:
        values = os.environ if env is None else env
        graph_tenant = _required_value(values, "M365_TENANT_ID")
        bff_tenant = _aliased_value(
            values,
            primary="NAC_BFF_TENANT_ID",
            secondary="M365_TENANT_ID",
        )
        if bff_tenant != graph_tenant:
            raise CompositionError(
                "BFF and Microsoft Graph tenant configuration must match"
            )
        audience = _aliased_value(
            values,
            primary="NAC_BFF_AUDIENCE",
            secondary="NAC_BFF_ENTRA_AUDIENCE",
        )
        required_scope = _aliased_value(
            values,
            primary="NAC_BFF_REQUIRED_SCOPE",
            secondary="NAC_BFF_ENTRA_REQUIRED_SCOPE",
        )
        if any(character.isspace() for character in required_scope):
            raise CompositionError("NAC_BFF_REQUIRED_SCOPE must contain one scope")
        return cls(
            tenant_id=bff_tenant,
            audience=audience,
            required_scope=required_scope,
        )


def build_configured_app(
    env: Mapping[str, str] | None = None,
    *,
    validator_factory: Callable[..., Any] = build_entra_access_token_validator,
    token_provider_factory: Callable[
        [Mapping[str, str]], Any
    ] = managed_identity_token_provider_from_env,
    graph_client_factory: Callable[[Any], Any] = RawGraphV1Client,
    access_port_factory: Callable[..., Any] = LiveAccessDecisionAdapter,
    workspace_port_factory: Callable[[Any], Any] = ConfiguredGraphRestPort,
    bpmn_asset_port_factory: Callable[[], Any] = CanonicalBpmnAssetFilePort,
) -> Any:
    """Compose the configured app, raising only generic configuration errors."""

    values = os.environ if env is None else env
    settings = BffSettings.from_env(values)
    validator = validator_factory(
        expected_tenant_id=settings.tenant_id,
        expected_audience=settings.audience,
        expected_issuer=settings.issuer,
        required_scopes={settings.required_scope},
        jwks_uri=settings.jwks_uri,
    )
    if not callable(validator):
        raise CompositionError("Entra access-token validator is unavailable")

    token_provider = token_provider_factory(values)
    graph_client = graph_client_factory(token_provider)
    request_budget_factory = getattr(graph_client, "request_budget", None)
    if not callable(request_budget_factory):
        request_budget_factory = None
    bff = TestEnvironmentBff(
        expected_tenant_id=settings.tenant_id,
        access_decision_port=access_port_factory(
            graph_client,
            expected_tenant_id=settings.tenant_id,
        ),
        graph_rest_port=workspace_port_factory(graph_client),
        bpmn_asset_port=bpmn_asset_port_factory(),
        request_budget_factory=request_budget_factory,
    )
    return create_fastapi_app(
        bff=bff,
        validated_claims_dependency=_claims_dependency(
            validator,
            expected_tenant_id=settings.tenant_id,
        ),
        ready=False,
    )


def create_app_from_env(
    env: Mapping[str, str] | None = None,
    *,
    validator_factory: Callable[..., Any] = build_entra_access_token_validator,
    token_provider_factory: Callable[
        [Mapping[str, str]], Any
    ] = managed_identity_token_provider_from_env,
    graph_client_factory: Callable[[Any], Any] = RawGraphV1Client,
    access_port_factory: Callable[..., Any] = LiveAccessDecisionAdapter,
    workspace_port_factory: Callable[[Any], Any] = ConfiguredGraphRestPort,
    bpmn_asset_port_factory: Callable[[], Any] = CanonicalBpmnAssetFilePort,
) -> Any:
    """Build the runtime app and fail closed to deny-all on every start error."""

    try:
        return build_configured_app(
            env,
            validator_factory=validator_factory,
            token_provider_factory=token_provider_factory,
            graph_client_factory=graph_client_factory,
            access_port_factory=access_port_factory,
            workspace_port_factory=workspace_port_factory,
            bpmn_asset_port_factory=bpmn_asset_port_factory,
        )
    except Exception:
        return create_unconfigured_app()


def _claims_dependency(
    validator: Callable[[object], Any],
    *,
    expected_tenant_id: str,
) -> Callable[..., Any]:
    try:
        from fastapi import Header, HTTPException
    except ImportError as exc:  # pragma: no cover - runtime packaging failure
        raise CompositionError("FastAPI is unavailable") from exc

    async def validated_claims(
        authorization=Header(default=None, alias="Authorization"),
    ) -> ValidatedClaims:
        try:
            claims = await run_sync_with_request_budget(validator, authorization)
        except TimeoutError:
            raise HTTPException(
                status_code=503,
                detail="service unavailable",
            ) from None
        except Exception:
            claims = None
        if (
            not isinstance(claims, ValidatedClaims)
            or claims.tenant_id != expected_tenant_id
        ):
            raise HTTPException(
                status_code=401,
                detail="authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return claims

    return validated_claims


@contextmanager
def _bounded_lock(lock: threading.Lock, timeout_seconds: float):
    deadline = time.monotonic() + timeout_seconds
    if not lock.acquire(timeout=timeout_seconds):
        raise TimeoutError("managed identity token acquisition timed out")
    try:
        yield deadline
    finally:
        lock.release()


def _remaining_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("managed identity token acquisition timed out")
    return remaining

def _bounded_seconds(value: object, *, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CompositionError("timeout must be a positive finite number")
    numeric = float(value)
    if not math.isfinite(numeric) or not 0 < numeric <= maximum:
        raise CompositionError("timeout exceeds the configured bound")
    return numeric


def _required_value(
    values: Mapping[str, str],
    name: str,
    *,
    limit: int = 2048,
) -> str:
    value = values.get(name, "")
    normalized = value.strip() if isinstance(value, str) else ""
    if (
        not normalized
        or normalized != value
        or len(normalized) > limit
        or any(character in normalized for character in "\r\n\x00")
    ):
        raise CompositionError(f"missing or invalid configuration: {name}")
    return normalized


def _aliased_value(
    values: Mapping[str, str],
    *,
    primary: str,
    secondary: str,
) -> str:
    first = values.get(primary)
    second = values.get(secondary)
    if isinstance(first, str) and first and isinstance(second, str) and second:
        normalized_first = _required_value(values, primary)
        normalized_second = _required_value(values, secondary)
        if normalized_first != normalized_second:
            raise CompositionError(
                f"conflicting configuration: {primary}, {secondary}"
            )
        return normalized_first
    if isinstance(first, str) and first:
        return _required_value(values, primary)
    return _required_value(values, secondary)
