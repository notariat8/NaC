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
