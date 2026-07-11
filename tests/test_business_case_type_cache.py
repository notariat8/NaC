from __future__ import annotations

import unittest

from src.notary_kg.business_case_type_cache import (
    BusinessCaseTypeRegistryCache,
    BusinessCaseTypeViewerCache,
    RegistryCacheEntry,
    ViewerCacheEntry,
)


class CacheTests(unittest.TestCase):
    def test_site_generation_blocks_old_inflight_store(self):
        cache = BusinessCaseTypeRegistryCache()
        key = ("site", "type", "version")
        generation = cache.generation("site")
        cache.invalidate_site("site")
        entry = RegistryCacheEntry("type", "active", True, "version", "etag", 0.0)
        self.assertFalse(cache.store(key, entry, generation=generation))
        self.assertIsNone(cache.get(key))

    def test_catalog_version_change_invalidates_site_partition(self):
        cache = BusinessCaseTypeRegistryCache()
        initial_generation = cache.bind_catalog_version("site", "version-1")
        key = ("site", "type", "version-1")
        cache.store(key, RegistryCacheEntry("type", "active", True, "version-1", "etag", 0.0), generation=initial_generation)
        self.assertEqual(initial_generation + 1, cache.bind_catalog_version("site", "version-2"))
        self.assertIsNone(cache.get(key))

    def test_site_partition_is_bounded(self):
        cache = BusinessCaseTypeRegistryCache(max_entries_per_site=2)
        for index in range(3):
            key = ("site", f"type-{index}", "version")
            generation = cache.generation("site")
            cache.store(key, RegistryCacheEntry(f"type-{index}", "active", True, "version", str(index), float(index)), generation=generation)
        self.assertIsNone(cache.get(("site", "type-0", "version")))
        self.assertIsNotNone(cache.get(("site", "type-2", "version")))

    def test_registry_and_viewer_cache_are_isolated(self):
        registry = BusinessCaseTypeRegistryCache()
        viewer = BusinessCaseTypeViewerCache()
        registry_generation = registry.generation("site")
        viewer_generation = viewer.generation("site")
        registry.store(("site", "type", "version"), RegistryCacheEntry("type", "active", True, "version", "r", 0), generation=registry_generation)
        viewer.store(("site", "type"), ViewerCacheEntry("type", "v", (("ProcessKey", "type"),), 0), generation=viewer_generation)
        registry.invalidate_site("site")
        self.assertIsNone(registry.get(("site", "type", "version")))
        self.assertIsNotNone(viewer.get(("site", "type")))
        self.assertIsNot(registry._lock, viewer._lock)
        self.assertIsNot(registry._entries, viewer._entries)


    def test_registry_store_rejects_invalid_positive_and_negative_shapes(self):
        cache = BusinessCaseTypeRegistryCache()
        generation = cache.generation("site")
        key = ("site", "type", "version")
        invalid = (
            RegistryCacheEntry("type", "retired", True, "version", "etag", 0),
            RegistryCacheEntry("type", "active", 1, "version", "etag", 0),
            RegistryCacheEntry("type", "active", True, "version", "", 0),
            RegistryCacheEntry("type", "invalid", False, "version", "etag", 0, "missing"),
            RegistryCacheEntry("type", "invalid", False, "version", "", 0, ""),
        )
        for entry in invalid:
            with self.assertRaises(ValueError):
                cache.store(key, entry, generation=generation)

    def test_global_site_state_and_key_locks_are_bounded(self):
        cache = BusinessCaseTypeRegistryCache(max_sites=2)
        cache.generation("site-1")
        cache.generation("site-2")
        cache.generation("site-3")
        self.assertEqual(2, len(cache._site_access))
        self.assertEqual(2, len(cache._generations))
        self.assertNotIn("site-1", cache._site_access)
        key = ("site-3", "type", "version")
        with cache.single_flight(key):
            self.assertEqual(1, len(cache._key_locks))
        self.assertEqual({}, cache._key_locks)

    def test_eviction_changes_generation_and_blocks_old_store(self):
        cache = BusinessCaseTypeRegistryCache(max_sites=1)
        old_generation = cache.generation("site-1")
        cache.generation("site-2")
        new_generation = cache.generation("site-1")
        self.assertNotEqual(old_generation, new_generation)
        entry = RegistryCacheEntry("type", "active", True, "version", "etag", 0)
        self.assertFalse(
            cache.store(("site-1", "type", "version"), entry, generation=old_generation)
        )

    def test_viewer_metadata_is_allowlisted_typed_and_unique(self):
        viewer = BusinessCaseTypeViewerCache()
        generation = viewer.generation("site")
        key = ("site", "type")
        valid = ViewerCacheEntry(
            "type",
            "etag",
            (("ProcessKey", "type"), ("ApprovalStatus", "approved")),
            0,
        )
        self.assertTrue(viewer.store(key, valid, generation=generation))
        invalid_metadata = (
            (("MatterId", "matter-1"),),
            (("ProcessKey", "type"), ("ProcessKey", "duplicate")),
            (("ProcessKey", 1),),
        )
        for metadata in invalid_metadata:
            with self.assertRaises(ValueError):
                viewer.store(
                    key,
                    ViewerCacheEntry("type", "etag", metadata, 1),
                    generation=generation,
                )

    def test_internal_entry_types_are_not_package_exports(self):
        import src.notary_kg as package

        self.assertFalse(hasattr(package, "RegistryCacheEntry"))
        self.assertFalse(hasattr(package, "ViewerCacheEntry"))

    def test_cache_entries_cannot_hold_raw_or_matter_payloads(self):
        self.assertEqual(
            {"business_case_type_id", "lifecycle_status", "selectable", "catalog_version", "etag", "validated_at", "negative_reason"},
            set(RegistryCacheEntry.__dataclass_fields__),
        )


if __name__ == "__main__":
    unittest.main()
