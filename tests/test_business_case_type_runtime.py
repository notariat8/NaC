from __future__ import annotations

import copy
import unittest
from pathlib import Path

from src.notary_kg.business_case_inventory import build_business_case_inventory
from src.notary_kg.business_case_type_cache import BusinessCaseTypeRegistryCache, RegistryCacheEntry
from src.notary_kg.business_case_type_runtime import (
    DEFAULT_RUNTIME_LIFECYCLE,
    BusinessCaseTypeCatalog,
    BusinessCaseTypeLookupRequest,
    business_case_type_get,
)
from src.notary_kg.business_case_type_transport import BusinessCaseTypeRegistryRow, RegistryFetchResult


ROOT = Path(__file__).resolve().parents[1]


class FakePort:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def fetch_registry(self, **kwargs):
        self.calls.append(kwargs)
        return self.results.pop(0)


def row(catalog, identifier="immobilienkaufvertrag", **overrides):
    values = dict(
        business_case_type_id=identifier,
        lifecycle_status="active",
        selectable=True,
        catalog_version=catalog.catalog_version,
        etag='"etag-1"',
    )
    values.update(overrides)
    return BusinessCaseTypeRegistryRow(**values)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.catalog = BusinessCaseTypeCatalog.from_repo(ROOT)
        self.cache = BusinessCaseTypeRegistryCache()
        self.now = 0.0

    def lookup(self, port, identifier="immobilienkaufvertrag", purpose="canonical_assignment"):
        return business_case_type_get(
            BusinessCaseTypeLookupRequest("site-1", identifier, purpose),
            catalog=self.catalog,
            read_port=port,
            registry_cache=self.cache,
            clock=lambda: self.now,
        )

    def test_catalog_version_is_stable_sha256_and_lifecycle_is_explicit(self):
        second = BusinessCaseTypeCatalog.from_repo(ROOT)
        self.assertEqual(self.catalog.catalog_version, second.catalog_version)
        self.assertRegex(self.catalog.catalog_version, r"^[0-9a-f]{64}$")
        changed = dict(DEFAULT_RUNTIME_LIFECYCLE)
        changed["immobilienkaufvertrag"] = ("retired", False)
        retired = BusinessCaseTypeCatalog.from_inventory(build_business_case_inventory(ROOT), lifecycle=changed)
        self.assertNotEqual(self.catalog.catalog_version, retired.catalog_version)

    def test_future_canonical_type_requires_explicit_lifecycle_decision(self):
        inventory = copy.deepcopy(build_business_case_inventory(ROOT))
        template = next(
            entry for entry in inventory["business_cases"]
            if entry["catalog_entry_kind"] == "canonical"
        )
        future = copy.deepcopy(template)
        future["slug"] = "future-notarial-case"
        future["business_case_type_id"] = "future-notarial-case"
        inventory["business_cases"].append(future)
        with self.assertRaisesRegex(ValueError, "exactly cover canonical IDs"):
            BusinessCaseTypeCatalog.from_inventory(inventory)

    def test_canonical_and_purpose_bound_alias(self):
        result = self.lookup(FakePort([RegistryFetchResult.ok(row(self.catalog))]))
        self.assertEqual("VALID", result.status)
        alias_port = FakePort([RegistryFetchResult.ok(row(self.catalog))])
        alias = self.lookup(alias_port, "grundstueckskaufvertrag", "legacy_read")
        self.assertEqual("VALID", alias.status)
        self.assertTrue(alias.resolved_from_alias)
        self.assertTrue(alias.audit_required)
        self.assertFalse(alias.selectable)
        blocked_port = FakePort([])
        blocked = self.lookup(blocked_port, "grundstueckskaufvertrag", "canonical_assignment")
        self.assertEqual("alias_not_allowed", blocked.reason_code)
        self.assertEqual([], blocked_port.calls)

    def test_exact_identifier_rejects_variants_without_transport(self):
        for identifier in (" Immobilienkaufvertrag", "Immobilienkaufvertrag", "immobilienkaufvertrag ", "immobilienkaufvertrag%20", "immobílienkaufvertrag", "a" * 129):
            port = FakePort([])
            self.assertEqual("INVALID", self.lookup(port, identifier).status)
            self.assertEqual([], port.calls)

    def test_catalog_rejects_alias_chain_cycle_self_unknown_and_collision(self):
        base = build_business_case_inventory(ROOT)
        alias_entries = [entry for entry in base["business_cases"] if entry["catalog_entry_kind"] == "legacy_alias"]
        mutations = []
        chained = copy.deepcopy(base); alias_entries = [e for e in chained["business_cases"] if e["catalog_entry_kind"] == "legacy_alias"]
        alias_entries[0]["legacy_alias"]["target"]["business_case_type_id"] = alias_entries[1]["slug"]; mutations.append(chained)
        self_target = copy.deepcopy(base); target = [e for e in self_target["business_cases"] if e["catalog_entry_kind"] == "legacy_alias"][0]
        target["legacy_alias"]["target"]["business_case_type_id"] = target["slug"]; mutations.append(self_target)
        unknown = copy.deepcopy(base); [e for e in unknown["business_cases"] if e["catalog_entry_kind"] == "legacy_alias"][0]["legacy_alias"]["target"]["business_case_type_id"] = "unknown-type"; mutations.append(unknown)
        collision = copy.deepcopy(base); [e for e in collision["business_cases"] if e["catalog_entry_kind"] == "legacy_alias"][0]["slug"] = "immobilienkaufvertrag"; mutations.append(collision)
        for payload in mutations:
            with self.assertRaises(ValueError):
                BusinessCaseTypeCatalog.from_inventory(payload)

    def test_registry_requires_exactly_one_strict_row(self):
        invalid_results = [
            RegistryFetchResult.ok(),
            RegistryFetchResult.ok(row(self.catalog), row(self.catalog)),
            RegistryFetchResult.ok(row(self.catalog, business_case_type_id="testament-erbvertrag")),
            RegistryFetchResult.ok(row(self.catalog, catalog_version="0" * 64)),
            RegistryFetchResult.ok(row(self.catalog, lifecycle_status="retired")),
            RegistryFetchResult.ok(row(self.catalog, selectable=1)),
            RegistryFetchResult.ok(row(self.catalog, etag="")),
            RegistryFetchResult.ok(row(self.catalog), pages_complete=False),
        ]
        for fetch in invalid_results:
            cache = BusinessCaseTypeRegistryCache()
            result = business_case_type_get(
                BusinessCaseTypeLookupRequest("site-x", "immobilienkaufvertrag", "canonical_assignment"),
                catalog=self.catalog, read_port=FakePort([fetch]), registry_cache=cache, clock=lambda: 0.0,
            )
            self.assertEqual("INVALID", result.status)

    def test_cache_boundaries_revalidation_not_modified_and_hard_expiry(self):
        port = FakePort([RegistryFetchResult.ok(row(self.catalog)), RegistryFetchResult.not_modified(), RegistryFetchResult.unavailable(), RegistryFetchResult.unavailable()])
        self.assertEqual("MISS", self.lookup(port).cache_state)
        self.now = 299.999
        self.assertEqual("FRESH", self.lookup(port).cache_state)
        self.now = 300.0
        self.assertEqual("NOT_MODIFIED", self.lookup(port).cache_state)
        self.now = 1199.999
        stale = self.lookup(port)
        self.assertEqual("VALIDATION_UNAVAILABLE", stale.status)
        self.assertEqual("UNAVAILABLE", stale.cache_state)
        self.now = 1200.0
        expired = self.lookup(port)
        self.assertEqual("VALIDATION_UNAVAILABLE", expired.status)
        self.assertEqual("HARD_EXPIRED", expired.cache_state)

    def test_timeout_at_revalidation_never_authorizes_assignment(self):
        port = FakePort([RegistryFetchResult.ok(row(self.catalog)), RegistryFetchResult.unavailable("timeout")])
        self.assertEqual("VALID", self.lookup(port).status)
        self.now = 300.0
        self.assertEqual("VALIDATION_UNAVAILABLE", self.lookup(port).status)

    def test_not_modified_without_cache_basis_is_protocol_error(self):
        result = self.lookup(FakePort([RegistryFetchResult.not_modified()]))
        self.assertEqual("VALIDATION_UNAVAILABLE", result.status)
        self.assertEqual("not_modified_without_valid_cache_basis", result.reason_code)

    def test_negative_ttl_uses_30_second_boundary(self):
        port = FakePort([RegistryFetchResult.ok(), RegistryFetchResult.ok(row(self.catalog))])
        self.assertEqual("INVALID", self.lookup(port).status)
        self.now = 29.999
        self.assertEqual("NEGATIVE", self.lookup(port).cache_state)
        self.now = 30.0
        self.assertEqual("VALID", self.lookup(port).status)
        self.assertEqual(2, len(port.calls))

    def test_transport_failures_are_not_negative_cached(self):
        port = FakePort([RegistryFetchResult.unavailable(), RegistryFetchResult.ok(row(self.catalog))])
        self.assertEqual("VALIDATION_UNAVAILABLE", self.lookup(port).status)
        self.assertEqual("VALID", self.lookup(port).status)

    def test_transport_exception_is_redacted_and_not_cached(self):
        class RaisingPort:
            def fetch_registry(self, **_kwargs):
                raise TimeoutError("secret upstream response")

        result = self.lookup(RaisingPort())
        self.assertEqual("VALIDATION_UNAVAILABLE", result.status)
        self.assertEqual("registry_transport_exception", result.reason_code)
        self.assertNotIn("secret", result.reason_code)

    def test_incomplete_paging_is_fail_closed(self):
        result = self.lookup(
            FakePort([
                RegistryFetchResult.ok(
                    row(self.catalog),
                    pages_complete=False,
                )
            ])
        )
        self.assertEqual("INVALID", result.status)
        self.assertEqual("registry_paging_incomplete", result.reason_code)

    def test_etag_drift_invalidates_entire_site_partition(self):
        other_key = ("site-1", "testament-erbvertrag", self.catalog.catalog_version)
        generation = self.cache.generation("site-1")
        self.cache.store(other_key, RegistryCacheEntry("testament-erbvertrag", "active", True, self.catalog.catalog_version, "other", 0.0), generation=generation)
        port = FakePort([RegistryFetchResult.ok(row(self.catalog)), RegistryFetchResult.ok(row(self.catalog, etag="\"etag-2\""))])
        self.assertEqual("VALID", self.lookup(port).status)
        self.now = 300.0
        self.assertEqual("VALID", self.lookup(port).status)
        self.assertIsNone(self.cache.get(other_key))
        self.assertEqual(generation + 1, self.cache.generation("site-1"))

    def test_runtime_signature_has_no_viewer_dependency(self):
        import inspect
        self.assertNotIn("viewer", inspect.signature(business_case_type_get).parameters)


if __name__ == "__main__":
    unittest.main()
