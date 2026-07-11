from __future__ import annotations

import math
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock, RLock
from typing import Iterator


RegistryCacheKey = tuple[str, str, str]
ViewerCacheKey = tuple[str, str]
_VIEWER_METADATA_TYPES = {
    "ApprovalStatus": str,
    "BpmnFileUrl": str,
    "BpmnModelRef": str,
    "BusinessCaseTypeId": str,
    "ModelStatus": str,
    "NacBpmnVersion": str,
    "ProcessKey": str,
    "SvgFileUrl": str,
    "Title": str,
}


@dataclass(frozen=True, slots=True)
class RegistryCacheEntry:
    business_case_type_id: str
    lifecycle_status: str
    selectable: bool
    catalog_version: str
    etag: str
    validated_at: float
    negative_reason: str | None = None

    @property
    def is_positive(self) -> bool:
        return self.negative_reason is None


@dataclass(slots=True)
class _FlightState:
    lock: Lock
    users: int = 0


class BusinessCaseTypeRegistryCache:
    FRESH_TTL_SECONDS = 300.0
    HARD_EXPIRY_SECONDS = 900.0
    NEGATIVE_TTL_SECONDS = 30.0

    def __init__(self, *, max_entries_per_site: int = 256, max_sites: int = 64) -> None:
        if max_entries_per_site < 1 or max_sites < 1:
            raise ValueError("cache limits must be positive")
        self._max_entries_per_site = max_entries_per_site
        self._max_sites = max_sites
        self._entries: dict[RegistryCacheKey, RegistryCacheEntry] = {}
        self._generations: dict[str, int] = {}
        self._site_catalog_versions: dict[str, str] = {}
        self._site_access: OrderedDict[str, None] = OrderedDict()
        self._next_generation = 1
        self._lock = RLock()
        self._key_locks: dict[RegistryCacheKey, _FlightState] = {}

    def get(self, key: RegistryCacheKey) -> RegistryCacheEntry | None:
        with self._lock:
            if key[0] in self._site_access:
                self._site_access.move_to_end(key[0])
            return self._entries.get(key)

    def generation(self, site_id: str) -> int:
        with self._lock:
            self._ensure_site_locked(site_id)
            return self._generations[site_id]

    def bind_catalog_version(self, site_id: str, catalog_version: str) -> int:
        if not isinstance(catalog_version, str) or not catalog_version:
            raise ValueError("catalog_version must be nonempty")
        with self._lock:
            self._ensure_site_locked(site_id)
            previous = self._site_catalog_versions.get(site_id)
            if previous is None:
                self._site_catalog_versions[site_id] = catalog_version
            elif previous != catalog_version:
                self._clear_entries_locked(site_id)
                self._site_catalog_versions[site_id] = catalog_version
                self._generations[site_id] += 1
            return self._generations[site_id]

    def store(self, key: RegistryCacheKey, entry: RegistryCacheEntry, *, generation: int) -> bool:
        site_id, business_case_type_id, catalog_version = key
        self._validate_entry(entry)
        if (
            not all(isinstance(value, str) and value for value in key)
            or entry.business_case_type_id != business_case_type_id
            or entry.catalog_version != catalog_version
        ):
            raise ValueError("registry cache entry does not match key")
        with self._lock:
            self._ensure_site_locked(site_id)
            if self._generations[site_id] != generation:
                return False
            bound_version = self._site_catalog_versions.get(site_id)
            if bound_version is not None and bound_version != catalog_version:
                return False
            self._entries[key] = entry
            self._evict_entries_locked(site_id)
            return True

    def invalidate_site(self, site_id: str) -> int:
        with self._lock:
            self._ensure_site_locked(site_id)
            self._clear_entries_locked(site_id)
            self._generations[site_id] += 1
            return self._generations[site_id]

    @contextmanager
    def single_flight(self, key: RegistryCacheKey) -> Iterator[None]:
        with self._lock:
            self._ensure_site_locked(key[0])
            state = self._key_locks.get(key)
            if state is None:
                state = _FlightState(Lock())
                self._key_locks[key] = state
            state.users += 1
        state.lock.acquire()
        try:
            yield
        finally:
            state.lock.release()
            with self._lock:
                state.users -= 1
                if state.users == 0 and self._key_locks.get(key) is state:
                    del self._key_locks[key]

    @staticmethod
    def _validate_entry(entry: RegistryCacheEntry) -> None:
        if type(entry.validated_at) not in {int, float} or not math.isfinite(entry.validated_at):
            raise ValueError("registry cache validated_at must be finite")
        if entry.is_positive:
            if entry.lifecycle_status != "active" or entry.selectable is not True or not isinstance(entry.etag, str) or not entry.etag:
                raise ValueError("positive registry cache entry has invalid shape")
        elif (
            not isinstance(entry.negative_reason, str)
            or not entry.negative_reason
            or entry.lifecycle_status != "invalid"
            or entry.selectable is not False
            or entry.etag != ""
        ):
            raise ValueError("negative registry cache entry has invalid shape")

    def _ensure_site_locked(self, site_id: str) -> None:
        if not isinstance(site_id, str) or not site_id:
            raise ValueError("site_id must be nonempty")
        if site_id in self._site_access:
            self._site_access.move_to_end(site_id)
            return
        while len(self._site_access) >= self._max_sites:
            if not self._evict_oldest_inactive_site_locked():
                raise RuntimeError("registry cache site capacity exhausted")
        self._site_access[site_id] = None
        self._generations[site_id] = self._next_generation
        self._next_generation += 1

    def _evict_oldest_inactive_site_locked(self) -> bool:
        active_sites = {key[0] for key, state in self._key_locks.items() if state.users > 0}
        for site_id in tuple(self._site_access):
            if site_id not in active_sites:
                self._clear_entries_locked(site_id)
                self._site_catalog_versions.pop(site_id, None)
                self._generations.pop(site_id, None)
                self._site_access.pop(site_id, None)
                return True
        return False

    def _clear_entries_locked(self, site_id: str) -> None:
        for key in tuple(self._entries):
            if key[0] == site_id:
                del self._entries[key]

    def _evict_entries_locked(self, site_id: str) -> None:
        site_entries = sorted(
            ((key, entry) for key, entry in self._entries.items() if key[0] == site_id),
            key=lambda item: item[1].validated_at,
        )
        for key, _entry in site_entries[: max(0, len(site_entries) - self._max_entries_per_site)]:
            del self._entries[key]


@dataclass(frozen=True, slots=True)
class ViewerCacheEntry:
    business_case_type_id: str
    etag: str
    metadata: tuple[tuple[str, str], ...]
    validated_at: float


class BusinessCaseTypeViewerCache:
    """Isolated optional viewer cache; never used for type validity."""

    def __init__(self, *, max_entries_per_site: int = 256, max_sites: int = 64) -> None:
        if max_entries_per_site < 1 or max_sites < 1:
            raise ValueError("cache limits must be positive")
        self._max_entries_per_site = max_entries_per_site
        self._max_sites = max_sites
        self._entries: dict[ViewerCacheKey, ViewerCacheEntry] = {}
        self._generations: dict[str, int] = {}
        self._site_access: OrderedDict[str, None] = OrderedDict()
        self._next_generation = 1
        self._lock = RLock()
        self._key_locks: dict[ViewerCacheKey, _FlightState] = {}

    def get(self, key: ViewerCacheKey) -> ViewerCacheEntry | None:
        with self._lock:
            if key[0] in self._site_access:
                self._site_access.move_to_end(key[0])
            return self._entries.get(key)

    def generation(self, site_id: str) -> int:
        with self._lock:
            self._ensure_site_locked(site_id)
            return self._generations[site_id]

    def store(self, key: ViewerCacheKey, entry: ViewerCacheEntry, *, generation: int) -> bool:
        self._validate_entry(entry)
        if not all(isinstance(value, str) and value for value in key) or entry.business_case_type_id != key[1]:
            raise ValueError("viewer cache entry does not match key")
        with self._lock:
            self._ensure_site_locked(key[0])
            if self._generations[key[0]] != generation:
                return False
            self._entries[key] = entry
            self._evict_entries_locked(key[0])
            return True

    def invalidate_site(self, site_id: str) -> int:
        with self._lock:
            self._ensure_site_locked(site_id)
            self._clear_entries_locked(site_id)
            self._generations[site_id] += 1
            return self._generations[site_id]

    @contextmanager
    def single_flight(self, key: ViewerCacheKey) -> Iterator[None]:
        with self._lock:
            self._ensure_site_locked(key[0])
            state = self._key_locks.get(key)
            if state is None:
                state = _FlightState(Lock())
                self._key_locks[key] = state
            state.users += 1
        state.lock.acquire()
        try:
            yield
        finally:
            state.lock.release()
            with self._lock:
                state.users -= 1
                if state.users == 0 and self._key_locks.get(key) is state:
                    del self._key_locks[key]

    @staticmethod
    def _validate_entry(entry: ViewerCacheEntry) -> None:
        if (
            not isinstance(entry.business_case_type_id, str)
            or not entry.business_case_type_id
            or not isinstance(entry.etag, str)
            or not entry.etag
            or type(entry.validated_at) not in {int, float}
            or not math.isfinite(entry.validated_at)
        ):
            raise ValueError("viewer cache entry has invalid shape")
        keys: set[str] = set()
        for item in entry.metadata:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("viewer metadata must contain key/value pairs")
            key, value = item
            expected_type = _VIEWER_METADATA_TYPES.get(key)
            if expected_type is None:
                raise ValueError("viewer metadata key is not allowed")
            if key in keys:
                raise ValueError("viewer metadata keys must be unique")
            if type(value) is not expected_type:
                raise ValueError("viewer metadata value has invalid type")
            keys.add(key)

    def _ensure_site_locked(self, site_id: str) -> None:
        if not isinstance(site_id, str) or not site_id:
            raise ValueError("site_id must be nonempty")
        if site_id in self._site_access:
            self._site_access.move_to_end(site_id)
            return
        while len(self._site_access) >= self._max_sites:
            if not self._evict_oldest_inactive_site_locked():
                raise RuntimeError("viewer cache site capacity exhausted")
        self._site_access[site_id] = None
        self._generations[site_id] = self._next_generation
        self._next_generation += 1

    def _evict_oldest_inactive_site_locked(self) -> bool:
        active_sites = {key[0] for key, state in self._key_locks.items() if state.users > 0}
        for site_id in tuple(self._site_access):
            if site_id not in active_sites:
                self._clear_entries_locked(site_id)
                self._generations.pop(site_id, None)
                self._site_access.pop(site_id, None)
                return True
        return False

    def _clear_entries_locked(self, site_id: str) -> None:
        for key in tuple(self._entries):
            if key[0] == site_id:
                del self._entries[key]

    def _evict_entries_locked(self, site_id: str) -> None:
        site_entries = sorted(
            ((key, entry) for key, entry in self._entries.items() if key[0] == site_id),
            key=lambda item: item[1].validated_at,
        )
        for key, _entry in site_entries[: max(0, len(site_entries) - self._max_entries_per_site)]:
            del self._entries[key]
