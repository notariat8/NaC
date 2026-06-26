from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from importlib import resources
from typing import Any, Protocol

from nac_runtime.demo_seed import seed_notarkammer_first_matter
from nac_runtime.status_display import build_first_matter_status_display
from nac_runtime.store import InMemoryRuntimeStore, RuntimeStoreAdapter


FIRST_MATTER_METADATA_RESOURCE = "notarkammer-first-immobilienkaufvertrag.metadata.json"
DEFAULT_ATP_FIRST_MATTER_OBJECT_KEY = "runtime/notarkammer-first/immobilienkaufvertrag.metadata.json"


class RuntimeMetadataSource(Protocol):
    def load_first_matter_metadata(self) -> Mapping[str, Any]:
        """Return metadata-only runtime JSON for the first matter status view."""


class RuntimeMetadataSourceUnavailable(RuntimeError):
    pass


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


def resolve_first_matter_runtime_metadata_source(
    source: RuntimeMetadataSource | None = None,
) -> RuntimeMetadataSource:
    if source is not None:
        return source
    return PackagedRuntimeMetadataSource()


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
