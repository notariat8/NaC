from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from typing import Any, Callable

from nac_identity.oci_tenant import check_domain_ready


ONBOARDING_REQUEST_SCHEMA_VERSION = "nac.onboarding-request/v0.1"
DEFAULT_REQUEST_STATUS = "submitted"
DEFAULT_INVITATION_STATUS = "not_sent"
DEFAULT_CREATED_BY_SURFACE = "app.notariat8.de"


class OnboardingRequestStoreDisabled(RuntimeError):
    pass


class OnboardingRequestStoreUnavailable(RuntimeError):
    pass


class DisabledOnboardingRequestStore:
    def create_request(self, payload: dict) -> dict:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def get_request(self, request_id: str) -> dict | None:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def list_requests(self, limit: int = 50) -> list[dict]:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")


class AtpOnboardingRequestStore:
    def __init__(
        self,
        *,
        user: str,
        dsn: str,
        password_provider: Callable[[], str],
        connector: Callable[..., Any] | None = None,
        config_dir: str = "",
        wallet_location: str = "",
    ) -> None:
        self.user = user
        self.dsn = dsn
        self.password_provider = password_provider
        self.connector = connector or _oracledb_connect
        self.config_dir = config_dir
        self.wallet_location = wallet_location

    def create_request(self, payload: dict) -> dict:
        self._validate_payload(payload)
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_ONBOARDING_REQUEST_INSERT_SQL, _request_binds(payload))
                connection.commit()
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
        return dict(payload)

    def get_request(self, request_id: str) -> dict | None:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        _ONBOARDING_REQUEST_SELECT_SQL + " WHERE request_id = :request_id",
                        {"request_id": request_id},
                    )
                    row = cursor.fetchone()
                    return _row_to_request(cursor, row) if row else None
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc

    def list_requests(self, limit: int = 50) -> list[dict]:
        capped_limit = max(1, min(int(limit), 100))
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        _ONBOARDING_REQUEST_SELECT_SQL
                        + f" ORDER BY created_at DESC FETCH FIRST {capped_limit} ROWS ONLY"
                    )
                    return [_row_to_request(cursor, row) for row in cursor.fetchall()]
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc

    def _connect(self) -> Any:
        password = self.password_provider()
        if not password:
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable")
        kwargs = {
            "user": self.user,
            "password": password,
            "dsn": self.dsn,
        }
        if self.config_dir:
            kwargs["config_dir"] = self.config_dir
        if self.wallet_location:
            kwargs["wallet_location"] = self.wallet_location
        return self.connector(**kwargs)

    @staticmethod
    def _validate_payload(payload: dict) -> None:
        missing = [field for field in _ONBOARDING_REQUEST_FIELDS if not str(payload.get(field, "")).strip()]
        if missing:
            raise ValueError("missing_onboarding_request_fields: " + ", ".join(missing))


def build_onboarding_request_store_from_env(
    environ: dict[str, str] | None = None,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    connector: Callable[..., Any] | None = None,
) -> DisabledOnboardingRequestStore | AtpOnboardingRequestStore:
    env = environ if environ is not None else os.environ
    mode = env.get("NAC_ONBOARDING_STORE", "").strip().lower()
    if mode != "atp":
        return DisabledOnboardingRequestStore()

    user = env.get("NAC_ATP_USER", "").strip()
    dsn = env.get("NAC_ATP_DSN", "").strip()
    password_secret_id = env.get("NAC_ATP_PASSWORD_SECRET_OCID", "").strip()
    if not user or not dsn or not password_secret_id:
        return DisabledOnboardingRequestStore()

    provider = secret_text_provider or OciVaultSecretTextProvider(password_secret_id)
    return AtpOnboardingRequestStore(
        user=user,
        dsn=dsn,
        password_provider=lambda: provider(password_secret_id),
        connector=connector,
        config_dir=env.get("NAC_ATP_CONFIG_DIR", "").strip(),
        wallet_location=env.get("NAC_ATP_WALLET_LOCATION", "").strip(),
    )


class OciVaultSecretTextProvider:
    def __init__(self, secret_id: str) -> None:
        self.secret_id = secret_id

    def __call__(self, secret_id: str | None = None) -> str:
        target_secret_id = secret_id or self.secret_id
        try:
            import oci

            signer = oci.auth.signers.get_resource_principals_signer()
            client = oci.secrets.SecretsClient(config={}, signer=signer)
            bundle = client.get_secret_bundle(target_secret_id).data
            encoded = bundle.secret_bundle_content.content
            return base64.b64decode(encoded).decode("utf-8")
        except Exception as exc:  # pragma: no cover - requires OCI Resource Principal integration
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc


def build_onboarding_request(
    *,
    domain: str,
    tenant_slug: str,
    admin_email: str,
    dns_status: str,
    now: str | None = None,
    created_by_surface: str = DEFAULT_CREATED_BY_SURFACE,
) -> dict:
    normalized_dns_status = dns_status.strip().lower()
    if normalized_dns_status != "verified":
        raise ValueError("dns_status_not_verified")

    readiness = check_domain_ready(domain=domain, tenant_slug=tenant_slug, admin_email=admin_email)
    if not readiness["ready"]:
        raise ValueError(", ".join(readiness["blocking_findings"]))

    timestamp = _normalize_timestamp(now)
    request_id = _request_id(readiness["tenant_slug"], timestamp)

    return {
        "schema_version": ONBOARDING_REQUEST_SCHEMA_VERSION,
        "request_id": request_id,
        "tenant_id": f"tenant.{readiness['tenant_slug']}",
        "tenant_slug": readiness["tenant_slug"],
        "domain": readiness["domain"],
        "admin_email": readiness["admin_email"],
        "dns_status": normalized_dns_status,
        "request_status": DEFAULT_REQUEST_STATUS,
        "invitation_status": DEFAULT_INVITATION_STATUS,
        "created_at": timestamp,
        "updated_at": timestamp,
        "created_by_surface": created_by_surface.strip() or DEFAULT_CREATED_BY_SURFACE,
    }


def _normalize_timestamp(now: str | None) -> str:
    if now is None:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    normalized = now.strip()
    if not normalized:
        raise ValueError("created_at_missing")
    if normalized.endswith("+00:00"):
        normalized = normalized[:-6] + "Z"
    datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    return normalized


def _request_id(tenant_slug: str, timestamp: str) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "").replace("T", "_").replace("Z", "")
    return f"onr_{tenant_slug}_{compact_time}"


_ONBOARDING_REQUEST_FIELDS = (
    "request_id",
    "tenant_id",
    "tenant_slug",
    "domain",
    "admin_email",
    "dns_status",
    "request_status",
    "invitation_status",
    "created_at",
    "updated_at",
    "created_by_surface",
)

_ONBOARDING_REQUEST_INSERT_SQL = """
INSERT INTO onboarding_requests (
    request_id,
    tenant_id,
    tenant_slug,
    domain,
    admin_email,
    dns_status,
    request_status,
    invitation_status,
    created_at,
    updated_at,
    created_by_surface
) VALUES (
    :request_id,
    :tenant_id,
    :tenant_slug,
    :domain,
    :admin_email,
    :dns_status,
    :request_status,
    :invitation_status,
    :created_at,
    :updated_at,
    :created_by_surface
)
"""

_ONBOARDING_REQUEST_SELECT_SQL = """
SELECT
    request_id,
    tenant_id,
    tenant_slug,
    domain,
    admin_email,
    dns_status,
    request_status,
    invitation_status,
    created_at,
    updated_at,
    created_by_surface
FROM onboarding_requests
"""


def _request_binds(payload: dict) -> dict[str, object]:
    return {field: payload[field] for field in _ONBOARDING_REQUEST_FIELDS}


def _row_to_request(cursor: Any, row: tuple[object, ...]) -> dict:
    columns = [str(description[0]).lower() for description in cursor.description]
    return {column: value for column, value in zip(columns, row)}


def _oracledb_connect(**kwargs: object) -> Any:
    try:
        import oracledb
    except ImportError as exc:  # pragma: no cover - dependency is packaged for Functions
        raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
    return oracledb.connect(**kwargs)
