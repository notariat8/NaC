from __future__ import annotations

import hashlib
import os
from collections.abc import Mapping
from typing import Any, Callable, Protocol

from nac_identity.onboarding_requests import (
    OciVaultSecretTextProvider,
    OnboardingRequestStoreUnavailable,
    _oracledb_connect,
    _wallet_materializer_from_env,
    _wallet_password_provider_from_env,
)


class RuntimeSessionStoreAdapter(Protocol):
    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        """Return a server-side session record for a signed session id."""


class RuntimeSessionWriteStoreAdapter(RuntimeSessionStoreAdapter, Protocol):
    def create_session_record(
        self,
        *,
        session_id: str,
        tenant_slug: str,
        subject_hash: str,
        role_class: str,
        usecase_slug: str,
        purpose: str,
        issued_at: int,
        expires_at: int,
        audit_event_id: str = "",
    ) -> Mapping[str, Any]:
        """Persist a redacted server-side session record."""


class MappingSessionStoreAdapter:
    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self._records = records

    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        return self._records.get(session_id)


class DisabledSessionStore:
    def get_session_record(self, _session_id: str) -> Mapping[str, Any] | None:
        raise OnboardingRequestStoreUnavailable("session_store_disabled")


class AtpSessionStore:
    def __init__(
        self,
        *,
        user: str,
        dsn: str,
        password_provider: Callable[[], str],
        connector: Callable[..., Any] | None = None,
        config_dir: str = "",
        wallet_location: str = "",
        wallet_materializer: Any | None = None,
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

    def create_session_record(
        self,
        *,
        session_id: str,
        tenant_slug: str,
        subject_hash: str,
        role_class: str,
        usecase_slug: str,
        purpose: str,
        issued_at: int,
        expires_at: int,
        audit_event_id: str = "",
    ) -> Mapping[str, Any]:
        binds = {
            "session_id_hash": _session_id_hash(session_id),
            "tenant_slug": _safe_store_text(tenant_slug, 80),
            "subject_hash": _safe_store_text(subject_hash, 128),
            "role_class": _safe_store_text(role_class, 80),
            "usecase_slug": _safe_store_text(usecase_slug, 120),
            "purpose": _safe_store_text(purpose, 80),
            "issued_at": int(issued_at),
            "expires_at": int(expires_at),
            "revoked_at": None,
            "audit_event_id": _safe_store_text(audit_event_id, 120),
            "contains_credentials": 0,
            "tokens_stored": 0,
            "claims_stored": 0,
        }
        _validate_session_binds(binds)
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_SESSION_UPSERT_SQL, binds)
                connection.commit()
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("session_store_unavailable") from exc
        return _record_creation_summary(binds)

    def get_session_record(self, session_id: str) -> Mapping[str, Any] | None:
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(_SESSION_SELECT_SQL, {"session_id_hash": _session_id_hash(session_id)})
                    row = cursor.fetchone()
                    return _row_to_session_record(cursor, row) if row else None
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("session_store_unavailable") from exc

    def _connect(self) -> Any:
        try:
            password = self.password_provider()
        except Exception as exc:
            if isinstance(exc, OnboardingRequestStoreUnavailable):
                raise
            raise OnboardingRequestStoreUnavailable("session_store_unavailable") from exc
        if not password:
            raise OnboardingRequestStoreUnavailable("session_store_unavailable")
        config_dir = self.config_dir
        wallet_location = self.wallet_location
        if self.wallet_materializer and (not config_dir or not wallet_location):
            wallet_path = self.wallet_materializer.materialize()
            config_dir = config_dir or wallet_path
            wallet_location = wallet_location or wallet_path
        kwargs = {"user": self.user, "password": password, "dsn": self.dsn}
        if config_dir:
            kwargs["config_dir"] = config_dir
        if wallet_location:
            kwargs["wallet_location"] = wallet_location
        if (config_dir or wallet_location) and self.wallet_password_provider:
            wallet_password = self.wallet_password_provider()
            if wallet_password:
                kwargs["wallet_password"] = wallet_password
        return self.connector(**kwargs)


def build_session_store_from_env(
    environ: dict[str, str] | None = None,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
    connector: Callable[..., Any] | None = None,
) -> DisabledSessionStore | AtpSessionStore:
    env = environ if environ is not None else os.environ
    mode = env.get("NAC_SESSION_STORE", "").strip().lower()
    if mode != "atp":
        return DisabledSessionStore()

    user = env.get("NAC_ATP_USER", "").strip()
    dsn = env.get("NAC_ATP_DSN", "").strip()
    password_secret_id = env.get("NAC_ATP_PASSWORD_SECRET_OCID", "").strip()
    if not user or not dsn or not password_secret_id:
        return DisabledSessionStore()

    provider = secret_text_provider or OciVaultSecretTextProvider(password_secret_id)
    wallet_materializer = _wallet_materializer_from_env(
        env,
        secret_bytes_provider=secret_bytes_provider,
        object_bytes_provider=object_bytes_provider,
    )
    wallet_password_provider = _wallet_password_provider_from_env(env, secret_text_provider=provider)
    return AtpSessionStore(
        user=user,
        dsn=dsn,
        password_provider=lambda: provider(password_secret_id),
        connector=connector,
        config_dir=env.get("NAC_ATP_CONFIG_DIR", "").strip(),
        wallet_location=env.get("NAC_ATP_WALLET_LOCATION", "").strip(),
        wallet_materializer=wallet_materializer,
        wallet_password_provider=wallet_password_provider,
    )


def _session_id_hash(session_id: str) -> str:
    normalized = session_id.strip()
    if not normalized:
        raise ValueError("session_id_missing")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _safe_store_text(value: Any, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _validate_session_binds(binds: Mapping[str, Any]) -> None:
    required = ("session_id_hash", "tenant_slug", "subject_hash", "role_class", "usecase_slug", "purpose")
    missing = [field for field in required if not str(binds.get(field, "")).strip()]
    if missing:
        raise ValueError("missing_session_fields: " + ", ".join(missing))
    if int(binds["expires_at"]) <= int(binds["issued_at"]):
        raise ValueError("session_time_invalid")


def _record_creation_summary(binds: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "nac.server-session/v0.1",
        "session_id_exposed": False,
        "tenant_bound": bool(binds.get("tenant_slug")),
        "subject_bound": bool(binds.get("subject_hash")),
        "role_bound": bool(binds.get("role_class")),
        "case_bound": bool(binds.get("usecase_slug")),
        "purpose_bound": bool(binds.get("purpose")),
        "contains_credentials": False,
        "tokens_stored": False,
        "claims_stored": False,
        "workspace_opened": False,
        "mandate_data_loaded": False,
    }


def _row_to_session_record(cursor: Any, row: tuple[object, ...]) -> dict[str, Any]:
    columns = [str(description[0]).lower() for description in cursor.description]
    values = {column: value for column, value in zip(columns, row)}
    return {
        "schema_version": "nac.server-session/v0.1",
        "issued_at": _int_or_none(values.get("issued_at")),
        "expires_at": _int_or_none(values.get("expires_at")),
        "revoked_at": _int_or_none(values.get("revoked_at")),
        "audit_event_id": _safe_store_text(values.get("audit_event_id"), 120),
        "contains_credentials": _db_bool(values.get("contains_credentials")),
        "tokens_stored": _db_bool(values.get("tokens_stored")),
        "claims_stored": _db_bool(values.get("claims_stored")),
        "tenant_bound": bool(_safe_store_text(values.get("tenant_slug"), 80)),
        "subject_bound": bool(_safe_store_text(values.get("subject_hash"), 128)),
        "role_bound": bool(_safe_store_text(values.get("role_class"), 80)),
        "case_bound": bool(_safe_store_text(values.get("usecase_slug"), 120)),
        "purpose_bound": bool(_safe_store_text(values.get("purpose"), 80)),
    }


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _db_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


_SESSION_UPSERT_SQL = """
MERGE INTO nac_sessions target
USING (
    SELECT
        :session_id_hash AS session_id_hash,
        :tenant_slug AS tenant_slug,
        :subject_hash AS subject_hash,
        :role_class AS role_class,
        :usecase_slug AS usecase_slug,
        :purpose AS purpose,
        :issued_at AS issued_at,
        :expires_at AS expires_at,
        :revoked_at AS revoked_at,
        :audit_event_id AS audit_event_id,
        :contains_credentials AS contains_credentials,
        :tokens_stored AS tokens_stored,
        :claims_stored AS claims_stored
    FROM dual
) source
ON (target.session_id_hash = source.session_id_hash)
WHEN MATCHED THEN UPDATE SET
    target.expires_at = source.expires_at,
    target.revoked_at = source.revoked_at,
    target.audit_event_id = source.audit_event_id
WHEN NOT MATCHED THEN INSERT (
    session_id_hash,
    tenant_slug,
    subject_hash,
    role_class,
    usecase_slug,
    purpose,
    issued_at,
    expires_at,
    revoked_at,
    audit_event_id,
    contains_credentials,
    tokens_stored,
    claims_stored
) VALUES (
    source.session_id_hash,
    source.tenant_slug,
    source.subject_hash,
    source.role_class,
    source.usecase_slug,
    source.purpose,
    source.issued_at,
    source.expires_at,
    source.revoked_at,
    source.audit_event_id,
    source.contains_credentials,
    source.tokens_stored,
    source.claims_stored
)
"""


_SESSION_SELECT_SQL = """
SELECT
    session_id_hash,
    tenant_slug,
    subject_hash,
    role_class,
    usecase_slug,
    purpose,
    issued_at,
    expires_at,
    revoked_at,
    audit_event_id,
    contains_credentials,
    tokens_stored,
    claims_stored
FROM nac_sessions
WHERE session_id_hash = :session_id_hash
"""
