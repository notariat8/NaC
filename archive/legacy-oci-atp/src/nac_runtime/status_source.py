from __future__ import annotations

"""Runtime metadata sources.

ATP support in this module is archived legacy compatibility. The active M365
MVP data plane is Teams/SharePoint through Microsoft Graph REST/MCP; do not add
new OCI/ATP callers without an explicit reactivation decision.
"""

import json
import os
from collections.abc import Callable, Mapping
from importlib import resources
from typing import Any, Protocol

from nac_identity.onboarding_requests import (
    OciVaultSecretTextProvider,
    OnboardingRequestStoreUnavailable,
    _oracledb_connect,
    _wallet_materializer_from_env,
    _wallet_password_provider_from_env,
)
from nac_runtime.demo_seed import seed_notarkammer_first_matter
from nac_runtime.status_display import build_first_matter_status_display
from nac_runtime.store import InMemoryRuntimeStore, RuntimeStoreAdapter


FIRST_MATTER_METADATA_RESOURCE = "notarkammer-first-immobilienkaufvertrag.metadata.json"
DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY = "DEMO-PROCESS-IMMOBILIENKAUF-01"
DEFAULT_ATP_RUNTIME_METADATA_PAYLOAD_COLUMN = "payload_json"
DEFAULT_ATP_RUNTIME_METADATA_TABLE = "nac_process_instances"
DEFAULT_ATP_RUNTIME_METADATA_KEY_COLUMN = "process_instance_id"
ATP_RUNTIME_SOURCE_ENV = "NAC_FIRST_MATTER_RUNTIME_SOURCE"
ATP_RUNTIME_OBJECT_KEY_ENV = "NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY"
ATP_RUNTIME_PAYLOAD_COLUMN_ENV = "NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN"
ATP_RUNTIME_TABLE_ENV = "NAC_FIRST_MATTER_RUNTIME_TABLE"
ATP_RUNTIME_KEY_COLUMN_ENV = "NAC_FIRST_MATTER_RUNTIME_KEY_COLUMN"

_ATP_RUNTIME_METADATA_TABLE_COLUMNS = {
    "nac_tenants": {
        "keys": {"tenant_id", "tenant_slug"},
        "payloads": {"payload_json"},
    },
    "nac_user_bindings": {
        "keys": {"user_binding_id", "tenant_id", "subject_hash"},
        "payloads": {"payload_json"},
    },
    "nac_matters": {
        "keys": {"matter_id", "tenant_id", "redacted_reference"},
        "payloads": {"payload_json"},
    },
    "nac_process_templates": {
        "keys": {"process_template_id", "template_slug"},
        "payloads": {"payload_json"},
    },
    "nac_process_instances": {
        "keys": {"process_instance_id", "tenant_id", "matter_id"},
        "payloads": {"payload_json"},
    },
    "nac_process_events": {
        "keys": {"process_event_id", "tenant_id", "process_instance_id"},
        "payloads": {"payload_json"},
    },
    "nac_audit_events": {
        "keys": {"audit_event_id", "tenant_id"},
        "payloads": {"payload_json"},
    },
}


class RuntimeMetadataSource(Protocol):
    def load_first_matter_metadata(self) -> Mapping[str, Any]:
        """Return metadata-only runtime JSON for the first matter status view."""


class RuntimeMetadataSourceUnavailable(RuntimeError):
    pass


class UnavailableRuntimeMetadataSource:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def load_first_matter_metadata(self) -> Mapping[str, Any]:
        raise RuntimeMetadataSourceUnavailable(self.reason)


class PackagedRuntimeMetadataSource:
    def load_first_matter_metadata(self) -> Mapping[str, Any]:
        resource = resources.files("nac_runtime.demo_data").joinpath(FIRST_MATTER_METADATA_RESOURCE)
        payload = json.loads(resource.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("runtime_metadata_source_not_object")
        return payload


class AtpJsonRuntimeMetadataSource:
    def __init__(
        self,
        reader: Callable[[str], Mapping[str, Any]],
        *,
        object_key: str = DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY,
    ) -> None:
        if not callable(reader):
            raise TypeError("runtime_metadata_reader_must_be_callable")
        if not isinstance(object_key, str) or not object_key.strip():
            raise ValueError("runtime_metadata_object_key_missing")
        self._reader = reader
        self.object_key = object_key

    def load_first_matter_metadata(self) -> Mapping[str, Any]:
        payload = self._reader(self.object_key)
        if not isinstance(payload, Mapping):
            raise ValueError("runtime_metadata_source_not_object")
        return dict(payload)


class AtpRuntimeMetadataRowReader:
    def __init__(
        self,
        fetch_row: Callable[[str], Mapping[str, Any] | None],
        *,
        payload_column: str = "payload_json",
    ) -> None:
        if not callable(fetch_row):
            raise TypeError("runtime_metadata_row_fetcher_must_be_callable")
        if not isinstance(payload_column, str) or not payload_column.strip():
            raise ValueError("runtime_metadata_payload_column_missing")
        self._fetch_row = fetch_row
        self.payload_column = payload_column.strip()

    def __call__(self, object_key: str) -> Mapping[str, Any]:
        if not isinstance(object_key, str) or not object_key.strip():
            raise ValueError("runtime_metadata_object_key_missing")
        row = self._fetch_row(object_key)
        if row is None:
            raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_missing")
        if not isinstance(row, Mapping):
            raise ValueError("runtime_metadata_row_not_object")
        return _normalize_runtime_metadata_payload(_runtime_metadata_row_payload(row, self.payload_column))


class AtpRuntimeMetadataRowFetcher:
    def __init__(
        self,
        *,
        user: str,
        dsn: str,
        password_provider: Callable[[], str],
        table_name: str = DEFAULT_ATP_RUNTIME_METADATA_TABLE,
        key_column: str = DEFAULT_ATP_RUNTIME_METADATA_KEY_COLUMN,
        payload_column: str = DEFAULT_ATP_RUNTIME_METADATA_PAYLOAD_COLUMN,
        connector: Callable[..., Any] | None = None,
        config_dir: str = "",
        wallet_location: str = "",
        wallet_materializer: Any | None = None,
        wallet_password_provider: Callable[[], str] | None = None,
    ) -> None:
        self.user = _required_text(user, "runtime_metadata_atp_user_missing")
        self.dsn = _required_text(dsn, "runtime_metadata_atp_dsn_missing")
        if not callable(password_provider):
            raise TypeError("runtime_metadata_password_provider_must_be_callable")
        self.password_provider = password_provider
        self.table_name, self.key_column, self.payload_column = _validate_atp_runtime_metadata_identifiers(
            table_name=table_name,
            key_column=key_column,
            payload_column=payload_column,
        )
        self.connector = connector or _oracledb_connect
        self.config_dir = config_dir
        self.wallet_location = wallet_location
        self.wallet_materializer = wallet_materializer
        self.wallet_password_provider = wallet_password_provider

    def __call__(self, object_key: str) -> Mapping[str, Any] | None:
        normalized_key = _required_text(object_key, "runtime_metadata_object_key_missing")
        try:
            with self._connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        self._select_sql(),
                        {"object_key": normalized_key},
                    )
                    row = cursor.fetchone()
                    if row is None:
                        return None
                    return _row_to_runtime_metadata(cursor, row)
        except Exception as exc:  # pragma: no cover - concrete driver errors are integration-tested
            if isinstance(exc, RuntimeMetadataSourceUnavailable):
                raise
            raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable") from None

    def _connect(self) -> Any:
        try:
            password = self.password_provider()
        except Exception as exc:
            if isinstance(exc, RuntimeMetadataSourceUnavailable):
                raise
            raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable") from None
        if not password:
            raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable")
        config_dir = self.config_dir
        wallet_location = self.wallet_location
        if self.wallet_materializer and (not config_dir or not wallet_location):
            try:
                wallet_path = self.wallet_materializer.materialize()
            except Exception as exc:
                if isinstance(exc, (RuntimeMetadataSourceUnavailable, OnboardingRequestStoreUnavailable)):
                    raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable") from None
                raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable") from None
            config_dir = config_dir or wallet_path
            wallet_location = wallet_location or wallet_path
        kwargs = {"user": self.user, "password": password, "dsn": self.dsn}
        if config_dir:
            kwargs["config_dir"] = config_dir
        if wallet_location:
            kwargs["wallet_location"] = wallet_location
        if (config_dir or wallet_location) and self.wallet_password_provider:
            try:
                wallet_password = self.wallet_password_provider()
            except Exception:
                raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable") from None
            if wallet_password:
                kwargs["wallet_password"] = wallet_password
        try:
            return self.connector(**kwargs)
        except Exception as exc:
            if isinstance(exc, RuntimeMetadataSourceUnavailable):
                raise
            raise RuntimeMetadataSourceUnavailable("runtime_metadata_row_fetcher_unavailable") from None

    def _select_sql(self) -> str:
        return (
            f"SELECT {self.payload_column} "
            f"FROM {self.table_name} "
            f"WHERE {self.key_column} = :object_key "
            "FETCH FIRST 1 ROWS ONLY"
        )


def resolve_first_matter_runtime_metadata_source(
    source: RuntimeMetadataSource | None = None,
) -> RuntimeMetadataSource:
    if source is not None:
        return source
    return PackagedRuntimeMetadataSource()


def build_first_matter_runtime_metadata_source_from_env(
    environ: Mapping[str, str] | None = None,
    *,
    row_fetcher: Callable[[str], Mapping[str, Any] | None] | None = None,
    secret_text_provider: Callable[[str], str] | None = None,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
    connector: Callable[..., Any] | None = None,
) -> RuntimeMetadataSource | None:
    env = environ if environ is not None else os.environ
    mode = str(env.get(ATP_RUNTIME_SOURCE_ENV, "")).strip().lower()
    if mode not in {"atp", "atp-json", "atp_metadata", "atp-runtime-metadata"}:
        return None

    object_key = str(env.get(ATP_RUNTIME_OBJECT_KEY_ENV, "")).strip() or DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY
    payload_column = (
        str(env.get(ATP_RUNTIME_PAYLOAD_COLUMN_ENV, "")).strip()
        or DEFAULT_ATP_RUNTIME_METADATA_PAYLOAD_COLUMN
    )
    if row_fetcher is None:
        try:
            row_fetcher = build_atp_runtime_metadata_row_fetcher_from_env(
                env,
                secret_text_provider=secret_text_provider,
                secret_bytes_provider=secret_bytes_provider,
                object_bytes_provider=object_bytes_provider,
                connector=connector,
            )
        except (TypeError, ValueError):
            return UnavailableRuntimeMetadataSource("runtime_metadata_row_fetcher_invalid_config")
    if row_fetcher is None:
        return UnavailableRuntimeMetadataSource("runtime_metadata_row_fetcher_missing")
    return AtpJsonRuntimeMetadataSource(
        AtpRuntimeMetadataRowReader(row_fetcher, payload_column=payload_column),
        object_key=object_key,
    )


def build_atp_runtime_metadata_row_fetcher_from_env(
    environ: Mapping[str, str] | None = None,
    *,
    secret_text_provider: Callable[[str], str] | None = None,
    secret_bytes_provider: Callable[[str], bytes] | None = None,
    object_bytes_provider: Callable[[str, str, str], bytes] | None = None,
    connector: Callable[..., Any] | None = None,
) -> AtpRuntimeMetadataRowFetcher | None:
    env = dict(environ if environ is not None else os.environ)
    user = env.get("NAC_ATP_USER", "").strip()
    dsn = env.get("NAC_ATP_DSN", "").strip()
    password_secret_id = env.get("NAC_ATP_PASSWORD_SECRET_OCID", "").strip()
    if not user or not dsn or not password_secret_id:
        return None

    provider = secret_text_provider or OciVaultSecretTextProvider(password_secret_id)
    wallet_materializer = _wallet_materializer_from_env(
        env,
        secret_bytes_provider=secret_bytes_provider,
        object_bytes_provider=object_bytes_provider,
    )
    wallet_password_provider = _wallet_password_provider_from_env(env, secret_text_provider=provider)
    payload_column = (
        env.get(ATP_RUNTIME_PAYLOAD_COLUMN_ENV, "").strip()
        or DEFAULT_ATP_RUNTIME_METADATA_PAYLOAD_COLUMN
    )
    return AtpRuntimeMetadataRowFetcher(
        user=user,
        dsn=dsn,
        password_provider=lambda: provider(password_secret_id),
        table_name=env.get(ATP_RUNTIME_TABLE_ENV, "").strip() or DEFAULT_ATP_RUNTIME_METADATA_TABLE,
        key_column=env.get(ATP_RUNTIME_KEY_COLUMN_ENV, "").strip() or DEFAULT_ATP_RUNTIME_METADATA_KEY_COLUMN,
        payload_column=payload_column,
        connector=connector,
        config_dir=env.get("NAC_ATP_CONFIG_DIR", "").strip(),
        wallet_location=env.get("NAC_ATP_WALLET_LOCATION", "").strip(),
        wallet_materializer=wallet_materializer,
        wallet_password_provider=wallet_password_provider,
    )


def build_first_matter_status_display_from_metadata_source(
    *,
    source: RuntimeMetadataSource,
    store_factory: Callable[[], RuntimeStoreAdapter] = InMemoryRuntimeStore,
) -> dict[str, Any]:
    fixture = source.load_first_matter_metadata()
    store = store_factory()
    seed = seed_notarkammer_first_matter(store=store, fixture=fixture)
    return build_first_matter_status_display(
        store=store,
        process_instance_id=seed["process_instance_id"],
    )


def _runtime_metadata_row_payload(row: Mapping[str, Any], payload_column: str) -> Any:
    if payload_column in row:
        return row[payload_column]
    if "payload_json" in row:
        return row["payload_json"]
    if "payload" in row:
        return row["payload"]
    return row


def _validate_atp_runtime_metadata_identifiers(
    *,
    table_name: str,
    key_column: str,
    payload_column: str,
) -> tuple[str, str, str]:
    table = str(table_name).strip().lower()
    key = str(key_column).strip().lower()
    payload = str(payload_column).strip().lower()
    if table not in _ATP_RUNTIME_METADATA_TABLE_COLUMNS:
        raise ValueError("runtime_metadata_table_not_allowed")
    allowed = _ATP_RUNTIME_METADATA_TABLE_COLUMNS[table]
    if key not in allowed["keys"]:
        raise ValueError("runtime_metadata_key_column_not_allowed")
    if payload not in allowed["payloads"]:
        raise ValueError("runtime_metadata_payload_column_not_allowed")
    return table, key, payload


def _row_to_runtime_metadata(cursor: Any, row: tuple[object, ...]) -> dict[str, Any]:
    columns = [str(description[0]).lower() for description in cursor.description]
    return {column: _read_lob_value(value) for column, value in zip(columns, row)}


def _read_lob_value(value: Any) -> Any:
    read = getattr(value, "read", None)
    if callable(read):
        return read()
    return value


def _required_text(value: Any, message: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
    return value.strip()


def _normalize_runtime_metadata_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8")
    if isinstance(payload, str):
        if not payload.strip():
            raise ValueError("runtime_metadata_payload_missing")
        try:
            payload = json.loads(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("runtime_metadata_json_invalid") from exc
    if not isinstance(payload, Mapping):
        raise ValueError("runtime_metadata_payload_not_object")
    try:
        normalized = json.loads(json.dumps(dict(payload), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise TypeError("runtime_metadata_payload_not_json_serializable") from exc
    if not isinstance(normalized, dict):
        raise ValueError("runtime_metadata_payload_not_object")
    _validate_runtime_metadata_payload(normalized)
    return normalized


def _validate_runtime_metadata_payload(payload: Mapping[str, Any]) -> None:
    required_false = {
        "mandate_data_present": "runtime_metadata_mandate_data_not_allowed",
        "raw_mandate_content_loaded": "runtime_metadata_raw_mandate_not_allowed",
        "secret_material_present": "runtime_metadata_secret_material_not_allowed",
        "contains_credentials": "runtime_metadata_credentials_not_allowed",
        "productive_xnp_action": "runtime_metadata_productive_xnp_action_not_allowed",
    }
    for field, message in required_false.items():
        if payload.get(field) is not False:
            raise ValueError(message)
    serialized = json.dumps(payload, sort_keys=True).lower()
    for term in ("client_secret", "private_key", "access_token", "refresh_token", "id_token"):
        if term in serialized:
            raise ValueError("runtime_metadata_forbidden_term: " + term)
