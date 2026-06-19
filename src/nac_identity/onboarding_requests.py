from __future__ import annotations

import base64
import hashlib
import io
import logging
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from nac_identity.oci_tenant import check_domain_ready


ONBOARDING_REQUEST_SCHEMA_VERSION = "nac.onboarding-request/v0.1"
ONBOARDING_REVIEW_AUDIT_SCHEMA_VERSION = "nac.onboarding-review-audit/v0.1"
DEFAULT_REQUEST_STATUS = "submitted"
DEFAULT_INVITATION_STATUS = "not_sent"
DEFAULT_CREATED_BY_SURFACE = "app.notariat8.de"
LOGGER = logging.getLogger(__name__)


class OnboardingRequestStoreDisabled(RuntimeError):
    pass


class OnboardingRequestStoreUnavailable(RuntimeError):
    pass


class DisabledOnboardingRequestStore:
    def create_request(self, payload: dict) -> dict:
        raise OnboardingRequestStoreDisabled("onboarding_request_store_disabled")

    def review_request(self, **_kwargs: str) -> dict:
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
        wallet_materializer: "AtpWalletZipMaterializer | None" = None,
        wallet_password_provider: Callable[[], str] | None = None,
    ) -> None:
        self.user = user
        self.dsn = dsn
        self.password_provider = password_provider
        self.connector = connector or _oracledb_connect
        self.config_dir = config_dir
        self.wallet_location = wallet_location
        self.wallet_materializer = wallet_materializer
        self.wallet_password_provider = wallet_password_provider

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

    def review_request(self, *, request_id: str, decision: str, now: str | None = None) -> dict:
        normalized_request_id = request_id.strip()
        if not normalized_request_id:
            raise ValueError("request_id_missing")
        review = _review_status_from_decision(decision)
        updated_at = _normalize_timestamp(now)
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        _ONBOARDING_REQUEST_REVIEW_SQL,
                        {
                            "request_id": normalized_request_id,
                            "request_status": review["request_status"],
                            "invitation_status": review["invitation_status"],
                            "updated_at": updated_at,
                        },
                    )
                    cursor.execute(
                        _ONBOARDING_REQUEST_SELECT_SQL + " WHERE request_id = :request_id",
                        {"request_id": normalized_request_id},
                    )
                    row = cursor.fetchone()
                    reviewed = _row_to_request(cursor, row) if row else None
                connection.commit()
            if reviewed is None:
                raise ValueError("onboarding_request_not_found")
            reviewed = dict(reviewed)
            reviewed["review_audit"] = build_onboarding_review_audit_metadata(
                request_id=normalized_request_id,
                decision=decision,
                reviewed_at=updated_at,
            )
            return reviewed
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, (OnboardingRequestStoreUnavailable, ValueError)):
                raise
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc

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
        try:
            password = self.password_provider()
        except Exception as exc:
            _log_store_unavailable("app_password_secret")
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
        if not password:
            _log_store_unavailable("app_password_secret")
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable")
        config_dir = self.config_dir
        wallet_location = self.wallet_location
        if self.wallet_materializer and (not config_dir or not wallet_location):
            wallet_path = self.wallet_materializer.materialize()
            config_dir = config_dir or wallet_path
            wallet_location = wallet_location or wallet_path
        kwargs = {
            "user": self.user,
            "password": password,
            "dsn": self.dsn,
        }
        if config_dir:
            kwargs["config_dir"] = config_dir
        if wallet_location:
            kwargs["wallet_location"] = wallet_location
        if (config_dir or wallet_location) and self.wallet_password_provider:
            try:
                wallet_password = self.wallet_password_provider()
            except Exception as exc:
                _log_store_unavailable("wallet_password_secret")
                if isinstance(exc, OnboardingRequestStoreUnavailable):
                    raise
                raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
            if wallet_password:
                kwargs["wallet_password"] = wallet_password
        try:
            return self.connector(**kwargs)
        except Exception as exc:
            _log_store_unavailable("atp_connect")
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise

    @staticmethod
    def _validate_payload(payload: dict) -> None:
        missing = [field for field in _ONBOARDING_REQUEST_FIELDS if not str(payload.get(field, "")).strip()]
        if missing:
            raise ValueError("missing_onboarding_request_fields: " + ", ".join(missing))


def build_onboarding_request_store_from_env(
    environ: dict[str, str] | None = None,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
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
    wallet_materializer = _wallet_materializer_from_env(
        env,
        secret_bytes_provider=secret_bytes_provider,
        object_bytes_provider=object_bytes_provider,
    )
    wallet_password_provider = _wallet_password_provider_from_env(env, secret_text_provider=provider)
    return AtpOnboardingRequestStore(
        user=user,
        dsn=dsn,
        password_provider=lambda: provider(password_secret_id),
        connector=connector,
        config_dir=env.get("NAC_ATP_CONFIG_DIR", "").strip(),
        wallet_location=env.get("NAC_ATP_WALLET_LOCATION", "").strip(),
        wallet_materializer=wallet_materializer,
        wallet_password_provider=wallet_password_provider,
    )


def _wallet_materializer_from_env(
    env: dict[str, str],
    *,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
) -> "AtpWalletZipMaterializer | None":
    object_namespace = env.get("NAC_ATP_WALLET_OBJECT_STORAGE_NAMESPACE", "").strip()
    object_bucket = env.get("NAC_ATP_WALLET_BUCKET_NAME", "").strip()
    object_name = env.get("NAC_ATP_WALLET_OBJECT_NAME", "").strip()
    object_config = [object_namespace, object_bucket, object_name]
    if all(object_config):
        provider = object_bytes_provider or OciObjectStorageBytesProvider(
            namespace=object_namespace,
            bucket_name=object_bucket,
            object_name=object_name,
        )
        return AtpWalletZipMaterializer(
            wallet_reference=f"oci-object://{object_namespace}/{object_bucket}/{object_name}",
            wallet_zip_provider=lambda _reference: provider(object_namespace, object_bucket, object_name),
            extract_root=env.get("NAC_ATP_WALLET_EXTRACT_DIR", "").strip(),
        )
    if any(object_config):
        return FailingAtpWalletMaterializer()

    wallet_secret_id = env.get("NAC_ATP_WALLET_ZIP_SECRET_OCID", "").strip()
    if not wallet_secret_id:
        return None
    provider = secret_bytes_provider or OciVaultSecretBytesProvider(wallet_secret_id)
    return AtpWalletZipMaterializer(
        wallet_secret_id=wallet_secret_id,
        wallet_zip_provider=provider,
        extract_root=env.get("NAC_ATP_WALLET_EXTRACT_DIR", "").strip(),
    )


def _wallet_password_provider_from_env(
    env: dict[str, str],
    *,
    secret_text_provider: Callable[[str], str],
) -> Callable[[], str] | None:
    wallet_password_secret_id = env.get("NAC_ATP_WALLET_PASSWORD_SECRET_OCID", "").strip()
    if not wallet_password_secret_id:
        return None
    return lambda: secret_text_provider(wallet_password_secret_id)


class OciVaultSecretTextProvider:
    def __init__(self, secret_id: str) -> None:
        self.secret_id = secret_id

    def __call__(self, secret_id: str | None = None) -> str:
        return _read_oci_secret_bundle_bytes(secret_id or self.secret_id).decode("utf-8")


class OciVaultSecretBytesProvider:
    def __init__(self, secret_id: str) -> None:
        self.secret_id = secret_id

    def __call__(self, secret_id: str | None = None) -> bytes:
        return _read_oci_secret_bundle_bytes(secret_id or self.secret_id)


def _read_oci_secret_bundle_bytes(secret_id: str) -> bytes:
    try:
        import oci

        signer = oci.auth.signers.get_resource_principals_signer()
        client = oci.secrets.SecretsClient(config={}, signer=signer)
        bundle = client.get_secret_bundle(secret_id).data
        encoded = bundle.secret_bundle_content.content
        return base64.b64decode(encoded)
    except Exception as exc:  # pragma: no cover - requires OCI Resource Principal integration
        raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc


class OciObjectStorageBytesProvider:
    def __init__(self, *, namespace: str, bucket_name: str, object_name: str) -> None:
        self.namespace = namespace
        self.bucket_name = bucket_name
        self.object_name = object_name

    def __call__(
        self,
        namespace: str | None = None,
        bucket_name: str | None = None,
        object_name: str | None = None,
    ) -> bytes:
        return _read_oci_object_bytes(
            namespace or self.namespace,
            bucket_name or self.bucket_name,
            object_name or self.object_name,
        )


def _read_oci_object_bytes(namespace: str, bucket_name: str, object_name: str) -> bytes:
    try:
        import oci

        signer = oci.auth.signers.get_resource_principals_signer()
        client = oci.object_storage.ObjectStorageClient(config={}, signer=signer)
        response = client.get_object(namespace, bucket_name, object_name)
        data = response.data
        if isinstance(data, bytes):
            return data
        content = getattr(data, "content", None)
        if isinstance(content, bytes):
            return content
        read = getattr(data, "read", None)
        if callable(read):
            return read()
        return bytes(data)
    except Exception as exc:  # pragma: no cover - requires OCI Resource Principal integration
        raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc


class FailingAtpWalletMaterializer:
    def materialize(self) -> str:
        raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable")


class AtpWalletZipMaterializer:
    def __init__(
        self,
        *,
        wallet_reference: str | None = None,
        wallet_secret_id: str | None = None,
        wallet_zip_provider: Callable[[str], bytes],
        extract_root: str = "",
    ) -> None:
        self.wallet_reference = wallet_reference or wallet_secret_id or ""
        self.wallet_zip_provider = wallet_zip_provider
        self.extract_root = Path(extract_root) if extract_root else Path(tempfile.gettempdir())
        self._materialized_path: Path | None = None

    def materialize(self) -> str:
        if self._materialized_path and self._wallet_marker_exists(self._materialized_path):
            return str(self._materialized_path)
        try:
            try:
                wallet_zip = self.wallet_zip_provider(self.wallet_reference)
            except Exception as exc:
                _log_store_unavailable(self._provider_stage())
                if isinstance(exc, OnboardingRequestStoreUnavailable):
                    raise
                raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
            if not wallet_zip:
                raise ValueError("empty_wallet_zip")
            target_dir = self._target_dir()
            target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._extract_wallet_zip(wallet_zip, target_dir)
            if not self._wallet_marker_exists(target_dir):
                raise ValueError("wallet_marker_missing")
            self._materialized_path = target_dir
            return str(target_dir)
        except Exception as exc:
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            _log_store_unavailable("wallet_materialize")
            raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc

    def _target_dir(self) -> Path:
        digest = hashlib.sha256(self.wallet_reference.encode("utf-8")).hexdigest()[:16]
        return self.extract_root / f"nac-atp-wallet-{digest}"

    def _provider_stage(self) -> str:
        if self.wallet_reference.startswith("oci-object://"):
            return "wallet_object"
        return "wallet_secret"

    @staticmethod
    def _wallet_marker_exists(path: Path) -> bool:
        return (path / "cwallet.sso").exists() or (path / "ewallet.pem").exists()

    @staticmethod
    def _extract_wallet_zip(wallet_zip: bytes, target_dir: Path) -> None:
        target_root = target_dir.resolve()
        with zipfile.ZipFile(io.BytesIO(wallet_zip)) as wallet:
            for info in wallet.infolist():
                if info.is_dir():
                    continue
                target_path = (target_dir / info.filename).resolve()
                try:
                    target_path.relative_to(target_root)
                except ValueError as exc:
                    raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
                target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with target_path.open("wb") as target:
                    target.write(wallet.read(info))
                os.chmod(target_path, 0o600)


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


def build_onboarding_review_audit_metadata(
    *,
    request_id: str,
    decision: str,
    reviewed_at: str,
    review_surface: str = "admin.onboarding.review",
) -> dict[str, Any]:
    return {
        "schema_version": ONBOARDING_REVIEW_AUDIT_SCHEMA_VERSION,
        "request_id": request_id.strip(),
        "decision": decision.strip().lower(),
        "reviewed_at": reviewed_at.strip(),
        "review_surface": review_surface,
        "contains_mandate_data": False,
        "customer_mail_dispatched": False,
        "oci_write_executed": False,
        "atp_schema_change_required": False,
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

_ONBOARDING_REQUEST_REVIEW_SQL = """
UPDATE onboarding_requests
SET
    request_status = :request_status,
    invitation_status = :invitation_status,
    updated_at = :updated_at
WHERE request_id = :request_id
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


def _review_status_from_decision(decision: str) -> dict[str, str]:
    normalized = decision.strip().lower()
    if normalized == "approve":
        return {"request_status": "approved", "invitation_status": "not_sent"}
    if normalized == "reject":
        return {"request_status": "rejected", "invitation_status": "not_sent"}
    raise ValueError("unsupported_onboarding_review_decision")


def _row_to_request(cursor: Any, row: tuple[object, ...]) -> dict:
    columns = [str(description[0]).lower() for description in cursor.description]
    return {column: value for column, value in zip(columns, row)}


def _oracledb_connect(**kwargs: object) -> Any:
    try:
        import oracledb
    except ImportError as exc:  # pragma: no cover - dependency is packaged for Functions
        raise OnboardingRequestStoreUnavailable("onboarding_request_store_unavailable") from exc
    return oracledb.connect(**kwargs)


def _log_store_unavailable(stage: str) -> None:
    LOGGER.warning("nac_onboarding_request_store_unavailable stage=%s", stage)
