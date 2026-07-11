from __future__ import annotations

import hashlib
import json
import re
import time
from types import MappingProxyType
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal, Mapping

from .business_case_inventory import (
    BUSINESS_CASE_TYPE_ID_MAX_LENGTH,
    BUSINESS_CASE_TYPE_ID_PATTERN,
    build_business_case_inventory,
)
from .business_case_type_cache import BusinessCaseTypeRegistryCache, RegistryCacheEntry, RegistryCacheKey
from .business_case_type_transport import (
    BusinessCaseTypeRegistryReadPort,
    RegistryFetchResult,
    safe_unavailable_reason_code,
)


LookupPurpose = Literal["canonical_assignment", "legacy_read", "migration"]
LookupStatus = Literal["VALID", "INVALID", "VALIDATION_UNAVAILABLE"]
_ID_RE = re.compile(BUSINESS_CASE_TYPE_ID_PATTERN)
_ALLOWED_LIFECYCLE = frozenset({"active", "deprecated", "retired"})

# Explicit runtime policy; usecase source_status is deliberately not consulted.
DEFAULT_RUNTIME_LIFECYCLE: Mapping[str, tuple[str, bool]] = MappingProxyType(
    {
        "adoption-familienrechtliche-erklaerungen": ("active", True),
        "bautraegervertrag": ("active", True),
        "ehevertrag-scheidungsfolgenvereinbarung": ("active", True),
        "erbausschlagung": ("active", True),
        "erbscheinsantrag-nachlass": ("active", True),
        "geschaeftsanteilsuebertragung-gmbh": ("active", True),
        "gesellschafterbeschluss-gmbh-ug": ("active", True),
        "grundschuld-hypothekenbestellung": ("active", True),
        "handelsregisteranmeldung": ("active", True),
        "immobilienkaufvertrag": ("active", True),
        "loeschungsbewilligung-grundbuchloeschung": ("active", True),
        "online-gmbh-gruendung": ("active", True),
        "pflichtteilsverzicht-erbverzicht": ("active", True),
        "schenkungsvertrag-uebertragungsvertrag": ("active", True),
        "teilungserklaerung-weg": ("active", True),
        "testament-erbvertrag": ("active", True),
        "unterschriftsbeglaubigung": ("active", True),
        "vereinsregisteranmeldung": ("active", True),
        "vollmacht-immobilien-gesellschaftsgeschaefte": ("active", True),
        "vorsorgevollmacht-patientenverfuegung": ("active", True),
    }
)


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeCatalogEntry:
    business_case_type_id: str
    lifecycle_status: str
    selectable: bool


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeCatalog:
    entries: tuple[BusinessCaseTypeCatalogEntry, ...]
    aliases: tuple[tuple[str, str], ...]
    catalog_version: str

    @classmethod
    def from_repo(
        cls,
        repo_root: Path,
        *,
        lifecycle: Mapping[str, tuple[str, bool]] = DEFAULT_RUNTIME_LIFECYCLE,
    ) -> "BusinessCaseTypeCatalog":
        return cls.from_inventory(build_business_case_inventory(repo_root), lifecycle=lifecycle)

    @classmethod
    def from_inventory(
        cls,
        inventory: Mapping[str, object],
        *,
        lifecycle: Mapping[str, tuple[str, bool]] = DEFAULT_RUNTIME_LIFECYCLE,
    ) -> "BusinessCaseTypeCatalog":
        raw_cases = inventory.get("business_cases")
        if not isinstance(raw_cases, list):
            raise ValueError("business case inventory must contain a list")
        canonical_ids: list[str] = []
        aliases: list[tuple[str, str]] = []
        for raw_case in raw_cases:
            if not isinstance(raw_case, dict):
                raise ValueError("business case inventory entries must be objects")
            slug = raw_case.get("slug")
            _require_exact_identifier(slug, "catalog identifier")
            kind = raw_case.get("catalog_entry_kind")
            if kind == "canonical":
                identifier = raw_case.get("business_case_type_id")
                _require_exact_identifier(identifier, "canonical business case type ID")
                if identifier != slug:
                    raise ValueError("canonical business case type ID must equal slug")
                canonical_ids.append(identifier)
            elif kind == "legacy_alias":
                alias = raw_case.get("legacy_alias")
                if not isinstance(alias, dict) or set(alias) != {"target"}:
                    raise ValueError("legacy alias must have exactly one target")
                target = alias.get("target")
                if not isinstance(target, dict) or set(target) != {"business_case_type_id"}:
                    raise ValueError("legacy alias target must contain exactly business_case_type_id")
                target_id = target.get("business_case_type_id")
                _require_exact_identifier(target_id, "legacy alias target")
                aliases.append((slug, target_id))
            else:
                raise ValueError("runtime catalog accepts canonical entries and direct aliases only")
        if len(canonical_ids) != len(set(canonical_ids)):
            raise ValueError("duplicate canonical business case type ID")
        if set(lifecycle) != set(canonical_ids):
            raise ValueError("runtime lifecycle policy must exactly cover canonical IDs")
        alias_keys = [alias for alias, _target in aliases]
        if len(alias_keys) != len(set(alias_keys)):
            raise ValueError("duplicate legacy alias")
        canonical_set, alias_set = set(canonical_ids), set(alias_keys)
        if alias_set & canonical_set:
            raise ValueError("legacy alias collides with canonical ID")
        for alias, target in aliases:
            if alias == target:
                raise ValueError("legacy alias self-target is not allowed")
            if target in alias_set:
                raise ValueError("legacy alias chains and cycles are not allowed")
            if target not in canonical_set:
                raise ValueError("legacy alias target must be canonical and known")
        entries: list[BusinessCaseTypeCatalogEntry] = []
        for identifier in sorted(canonical_ids):
            lifecycle_status, selectable = lifecycle[identifier]
            if lifecycle_status not in _ALLOWED_LIFECYCLE:
                raise ValueError(f"unsupported lifecycle status: {lifecycle_status}")
            if type(selectable) is not bool:
                raise ValueError("Selectable must be a strict boolean")
            entries.append(BusinessCaseTypeCatalogEntry(identifier, lifecycle_status, selectable))
        ordered_aliases = tuple(sorted(aliases))
        version_payload = {
            "entries": [
                {
                    "BusinessCaseTypeId": entry.business_case_type_id,
                    "LifecycleStatus": entry.lifecycle_status,
                    "Selectable": entry.selectable,
                }
                for entry in entries
            ],
            "aliases": [{"alias": alias, "target": target} for alias, target in ordered_aliases],
        }
        canonical_json = json.dumps(
            version_payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("ascii")
        return cls(tuple(entries), ordered_aliases, hashlib.sha256(canonical_json).hexdigest())

    def entry(self, identifier: str) -> BusinessCaseTypeCatalogEntry | None:
        return next((entry for entry in self.entries if entry.business_case_type_id == identifier), None)

    def alias_target(self, identifier: str) -> str | None:
        return dict(self.aliases).get(identifier)


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeLookupRequest:
    site_id: str
    identifier: str
    purpose: LookupPurpose


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeLookupResult:
    status: LookupStatus
    requested_identifier: str
    canonical_business_case_type_id: str | None
    catalog_version: str
    registry_etag: str | None
    resolved_from_alias: bool
    audit_required: bool
    selectable: bool
    cache_state: str
    reason_code: str


def _is_exact_identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= BUSINESS_CASE_TYPE_ID_MAX_LENGTH
        and value.isascii()
        and _ID_RE.fullmatch(value) is not None
    )


def _require_exact_identifier(value: object, label: str) -> None:
    if not _is_exact_identifier(value):
        raise ValueError(f"{label} must use exact lowercase ASCII kebab syntax")


def business_case_type_get(
    request: BusinessCaseTypeLookupRequest,
    *,
    catalog: BusinessCaseTypeCatalog,
    read_port: BusinessCaseTypeRegistryReadPort,
    registry_cache: BusinessCaseTypeRegistryCache,
    clock: Callable[[], float] = time.monotonic,
) -> BusinessCaseTypeLookupResult:
    if request.purpose not in {"canonical_assignment", "legacy_read", "migration"}:
        return _result(request, catalog, "INVALID", None, False, "MISS", "invalid_purpose")
    if not isinstance(request.site_id, str) or not request.site_id:
        return _result(request, catalog, "INVALID", None, False, "MISS", "invalid_site_id")
    if not _is_exact_identifier(request.identifier):
        return _result(request, catalog, "INVALID", None, False, "MISS", "invalid_identifier_syntax")
    canonical_id = request.identifier
    alias = False
    alias_target = catalog.alias_target(request.identifier)
    if alias_target is not None:
        if request.purpose == "canonical_assignment":
            return _result(request, catalog, "INVALID", None, True, "MISS", "alias_not_allowed")
        canonical_id, alias = alias_target, True
    catalog_entry = catalog.entry(canonical_id)
    if catalog_entry is None:
        return _result(request, catalog, "INVALID", None, alias, "MISS", "unknown_identifier")
    if catalog_entry.lifecycle_status != "active" or catalog_entry.selectable is not True:
        return _result(request, catalog, "INVALID", canonical_id, alias, "MISS", "catalog_entry_not_selectable")

    registry_cache.bind_catalog_version(request.site_id, catalog.catalog_version)
    key: RegistryCacheKey = (request.site_id, canonical_id, catalog.catalog_version)
    with registry_cache.single_flight(key):
        now = clock()
        cached = registry_cache.get(key)
        if cached is not None:
            age = max(0.0, now - cached.validated_at)
            if cached.is_positive and age < registry_cache.FRESH_TTL_SECONDS:
                return _valid_result(request, catalog, cached, alias, "FRESH")
            if not cached.is_positive and age < registry_cache.NEGATIVE_TTL_SECONDS:
                return _result(request, catalog, "INVALID", canonical_id, alias, "NEGATIVE", cached.negative_reason or "registry_invalid")
            if not cached.is_positive:
                cached = None
        generation = registry_cache.generation(request.site_id)
        try:
            fetch = read_port.fetch_registry(
                site_id=request.site_id,
                business_case_type_id=canonical_id,
                catalog_version=catalog.catalog_version,
                if_none_match=cached.etag if cached is not None else None,
            )
        except Exception:
            return _result(
                request,
                catalog,
                "VALIDATION_UNAVAILABLE",
                canonical_id,
                alias,
                "UNAVAILABLE",
                "registry_transport_exception",
            )
        if fetch.status == "UNAVAILABLE":
            hard_expired = cached is not None and now - cached.validated_at >= registry_cache.HARD_EXPIRY_SECONDS
            return _result(
                request, catalog, "VALIDATION_UNAVAILABLE", canonical_id, alias,
                "HARD_EXPIRED" if hard_expired else "UNAVAILABLE",
                safe_unavailable_reason_code(fetch.reason_code),
                etag=None if hard_expired or cached is None else cached.etag,
            )
        if fetch.status == "NOT_MODIFIED":
            if cached is None or not cached.is_positive or now - cached.validated_at >= registry_cache.HARD_EXPIRY_SECONDS:
                return _result(request, catalog, "VALIDATION_UNAVAILABLE", canonical_id, alias, "UNAVAILABLE", "not_modified_without_valid_cache_basis")
            refreshed = RegistryCacheEntry(
                cached.business_case_type_id, cached.lifecycle_status, cached.selectable,
                cached.catalog_version, cached.etag, now,
            )
            if not registry_cache.store(key, refreshed, generation=generation):
                return _result(request, catalog, "VALIDATION_UNAVAILABLE", canonical_id, alias, "UNAVAILABLE", "site_generation_changed")
            return _valid_result(request, catalog, refreshed, alias, "NOT_MODIFIED")
        if fetch.status != "OK":
            return _result(request, catalog, "VALIDATION_UNAVAILABLE", canonical_id, alias, "UNAVAILABLE", "transport_protocol_error")
        error = _validate_registry_rows(fetch, canonical_id, catalog.catalog_version)
        if error is not None:
            if error == "catalog_version_mismatch":
                generation = registry_cache.invalidate_site(request.site_id)
            negative = RegistryCacheEntry(canonical_id, "invalid", False, catalog.catalog_version, "", now, error)
            registry_cache.store(key, negative, generation=generation)
            return _result(request, catalog, "INVALID", canonical_id, alias, "NEGATIVE", error)
        row = fetch.rows[0]
        if cached is not None and row.etag != cached.etag:
            generation = registry_cache.invalidate_site(request.site_id)
        positive = RegistryCacheEntry(
            row.business_case_type_id, row.lifecycle_status, row.selectable,
            row.catalog_version, row.etag, now,
        )
        if not registry_cache.store(key, positive, generation=generation):
            return _result(request, catalog, "VALIDATION_UNAVAILABLE", canonical_id, alias, "UNAVAILABLE", "site_generation_changed")
        return _valid_result(request, catalog, positive, alias, "REVALIDATED" if cached else "MISS")


def _validate_registry_rows(fetch: RegistryFetchResult, expected_id: str, expected_version: str) -> str | None:
    if fetch.pages_complete is not True:
        return "registry_paging_incomplete"
    if len(fetch.rows) != 1:
        return "registry_row_count_mismatch"
    row = fetch.rows[0]
    if row.business_case_type_id != expected_id:
        return "registry_id_mismatch"
    if row.catalog_version != expected_version:
        return "catalog_version_mismatch"
    if row.lifecycle_status != "active":
        return "registry_lifecycle_not_active"
    if type(row.selectable) is not bool or row.selectable is not True:
        return "registry_not_selectable"
    if not isinstance(row.etag, str) or not row.etag:
        return "registry_etag_missing"
    return None


def _valid_result(request: BusinessCaseTypeLookupRequest, catalog: BusinessCaseTypeCatalog, entry: RegistryCacheEntry, alias: bool, cache_state: str) -> BusinessCaseTypeLookupResult:
    return BusinessCaseTypeLookupResult(
        "VALID", request.identifier, entry.business_case_type_id, catalog.catalog_version,
        entry.etag, alias, alias, entry.selectable and not alias, cache_state,
        "legacy_alias_resolved" if alias else "canonical_type_valid",
    )


def _result(request: BusinessCaseTypeLookupRequest, catalog: BusinessCaseTypeCatalog, status: LookupStatus, canonical_id: str | None, alias: bool, cache_state: str, reason_code: str, *, etag: str | None = None) -> BusinessCaseTypeLookupResult:
    return BusinessCaseTypeLookupResult(
        status, request.identifier, canonical_id, catalog.catalog_version, etag,
        alias, alias, False, cache_state, reason_code,
    )
