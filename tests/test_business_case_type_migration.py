from __future__ import annotations

import copy
import unittest

from src.notary_kg.business_case_inventory import CANONICAL_SLUGS
from src.notary_kg.business_case_type_migration import (
    BLOCKER_CLASSIFICATIONS,
    CLASSIFICATIONS,
    FROZEN_LEGACY_CHOICES,
    LocalMigrationReplayPort,
    MigrationValidationError,
    baseline_fingerprint,
    build_backfill_plan,
    build_forward_recovery_plan,
    build_manifest,
    build_readiness_evidence_anchor,
    build_rollback_plan,
    build_scan,
    canonical_json_bytes,
    canonical_json_hash,
    classify_record,
    classify_records,
    evaluate_cutover_readiness,
    run_migration_replay,
    text_hash,
    validate_bundle,
    validate_mapping_table,
    validate_pages,
    validate_registry_catalog_coverage,
)


KNOWN_IDS = frozenset(
    {
        "immobilienkaufvertrag",
        "unterschriftsbeglaubigung",
        "online-gmbh-gruendung",
        "handelsregisteranmeldung",
        "testament-erbvertrag",
        "new-canonical-type",
    }
)
CANONICAL_IDS = frozenset(CANONICAL_SLUGS)
MAPPING = {
    "immobilienkaufvertrag": "immobilienkaufvertrag",
    "unterschriftsbeglaubigung": "unterschriftsbeglaubigung",
    "online-gmbh-gruendung": "online-gmbh-gruendung",
    "handelsregisteranmeldung": "handelsregisteranmeldung",
}


def mapping_table() -> dict[str, object]:
    return {
        "schema_version": "nac.business-case-type-legacy-choice-mapping/v0.1",
        "mapping_id": "business-case-type-legacy-choice-baseline",
        "mapping_version": "2026-07-12.1",
        "typed_namespaces": {"source": "LegacyChoice", "target": "BusinessCaseTypeId"},
        "normalization_allowed": False,
        "mappings": [
            {"source": source, "target": target}
            for source, target in sorted(MAPPING.items())
        ],
    }


def row(
    record_ref: str = "synref-a",
    *,
    legacy_choice: object = "immobilienkaufvertrag",
    business_case_type_id: object = None,
    snapshot_etag: object = "synthetic-etag-1",
    current_etag: object = "synthetic-etag-1",
    read_status: object = "complete",
) -> dict[str, object]:
    return {
        "record_ref": record_ref,
        "snapshot_etag": snapshot_etag,
        "current_etag": current_etag,
        "legacy_choice": legacy_choice,
        "business_case_type_id": business_case_type_id,
        "read_status": read_status,
    }


def pages(*rows: dict[str, object]) -> list[dict[str, object]]:
    return [{"page_number": 1, "page_count": 1, "complete": True, "rows": list(rows)}]


def registry_snapshot(*ids: str) -> dict[str, object]:
    return {
        "status": "present",
        "complete": True,
        "rows": [
            {"business_case_type_id": identifier, "etag": f"synthetic-etag-registry-{index}", "selectable": True}
            for index, identifier in enumerate(ids, 1)
        ],
    }


def process_snapshot() -> dict[str, object]:
    return {
        "status": "present",
        "complete": True,
        "rows": [{"process_id": "p-1", "etag": "synthetic-etag-process-1", "bpmn_link": None}],
    }


def bindings() -> dict[str, str]:
    return {
        "site_hash": "1" * 64,
        "schema_hash": "2" * 64,
        "matter_list_hash": "3" * 64,
        "registry_list_hash": "4" * 64,
        "process_list_hash": "5" * 64,
    }


def profile() -> dict[str, object]:
    return {
        "canonical_field": "VorgangstypId",
        "reads_canonical_id": True,
        "ignores_additive_registry_fields": True,
        "unknown_id_decision": "BLOCKED",
        "unknown_id_reason_code": "unknown_business_case_type_id",
        "new_type_without_legacy_decision": "READ_ONLY",
        "legacy_choice_required_for_display": False,
    }


def candidate_registry() -> dict[str, object]:
    local_profile = profile()
    return {
        "schema_version": "nac.business-case-type-migration-runtime-candidates/v0.1",
        "registry_id": "business-case-type-migration-s5-replay-candidates",
        "registry_version": "2026-07-12.1",
        "scenarios_exact": [
            "read-vorgangstyp-id",
            "ignore-additive-registry-fields",
            "unknown-id-fail-closed",
            "new-type-without-legacy-read-only",
        ],
        "candidates": [
            {
                "candidate_id": candidate_id,
                "contract_version": contract_version,
                "profile": copy.deepcopy(local_profile),
                "profile_sha256": canonical_json_hash(local_profile),
            }
            for candidate_id, contract_version in (
                ("runtime-current", "v2"),
                ("runtime-previous", "v1"),
            )
        ],
    }


def replay_scenarios() -> dict[str, dict[str, object]]:
    return {
        "read-vorgangstyp-id": {
            "registry_row": {"VorgangstypId": "immobilienkaufvertrag"}
        },
        "ignore-additive-registry-fields": {
            "registry_row": {
                "VorgangstypId": "immobilienkaufvertrag",
                "future_field": "ignored",
            }
        },
        "unknown-id-fail-closed": {"registry_row": {"VorgangstypId": "unknown-type"}},
        "new-type-without-legacy-read-only": {
            "registry_row": {"VorgangstypId": "new-canonical-type", "legacy_choice": None}
        },
    }


def valid_bundle() -> dict[str, object]:
    matter_pages = pages(row())
    registry = registry_snapshot(*sorted(CANONICAL_IDS))
    process = {"status": "not_provisioned"}
    scans = [
        build_scan(
            scan_id="scan-one",
            scanned_at="2026-07-12T10:00:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=copy.deepcopy(matter_pages),
        ),
        build_scan(
            scan_id="scan-two",
            scanned_at="2026-07-12T10:15:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=copy.deepcopy(matter_pages),
        ),
    ]
    return {
        "schema_version": "nac.business-case-type-migration-fixture/v1",
        "data_classification": "synthetic",
        "contains_production_data": False,
        "observed_at": "2026-07-12T10:00:00Z",
        "catalog_version": "2026.07",
        "matter_pages": matter_pages,
        "registry_snapshot": registry,
        "process_snapshot": process,
        "post_scan_observed_at": "2026-07-12T10:15:01Z",
        "post_scan_registry_snapshot": copy.deepcopy(registry),
        "post_scan_process_snapshot": copy.deepcopy(process),
        "scans": scans,
        "replay_scenarios": replay_scenarios(),
        "bindings": bindings(),
        "role_approval_refs": ["synthetic-approval-privacy-review-1"],
    }


class CanonicalHashTests(unittest.TestCase):
    def test_hash_uses_sorted_ascii_compact_json(self) -> None:
        value = {"z": "ä", "a": [True, None, 2]}
        self.assertEqual(canonical_json_bytes(value), b'{"a":[true,null,2],"z":"\\u00e4"}')
        self.assertEqual(canonical_json_hash(value), canonical_json_hash({"a": [True, None, 2], "z": "ä"}))

    def test_rejects_floats_non_string_keys_custom_values_and_cycles(self) -> None:
        for value in (1.0, {1: "value"}, ("tuple",)):
            with self.subTest(value=value), self.assertRaises(MigrationValidationError):
                canonical_json_hash(value)
        cyclic: list[object] = []
        cyclic.append(cyclic)
        with self.assertRaises(MigrationValidationError):
            canonical_json_hash(cyclic)


class MappingTests(unittest.TestCase):
    def test_accepts_exact_four_choice_table_including_identity_mappings(self) -> None:
        self.assertEqual(validate_mapping_table(mapping_table(), KNOWN_IDS), MAPPING)
        self.assertEqual(set(MAPPING), FROZEN_LEGACY_CHOICES)

    def test_rejects_baseline_drift_duplicates_extra_missing_and_unknown_targets(self) -> None:
        mutations = []
        drift = mapping_table()
        drift["typed_namespaces"]["source"] = "WrongNamespace"
        mutations.append(drift)
        duplicate = mapping_table()
        duplicate["mappings"][1]["source"] = duplicate["mappings"][0]["source"]
        mutations.append(duplicate)
        extra = mapping_table()
        extra["mappings"].append({"source": "extra", "target": "testament-erbvertrag"})
        mutations.append(extra)
        missing = mapping_table()
        missing["mappings"].pop()
        mutations.append(missing)
        unknown = mapping_table()
        unknown["mappings"][0]["target"] = "not-canonical"
        mutations.append(unknown)
        for table in mutations:
            with self.subTest(table=table), self.assertRaises(MigrationValidationError):
                validate_mapping_table(table, KNOWN_IDS)

    def test_rejects_unknown_mapping_or_entry_keys(self) -> None:
        table = mapping_table()
        table["comment"] = "not part of the contract"
        with self.assertRaises(MigrationValidationError):
            validate_mapping_table(table, KNOWN_IDS)
        table = mapping_table()
        table["mappings"][0]["alias"] = True
        with self.assertRaises(MigrationValidationError):
            validate_mapping_table(table, KNOWN_IDS)


class ClassificationTests(unittest.TestCase):
    def test_normative_order_covers_exactly_seven_disjoint_classes(self) -> None:
        cases = {
            "already_canonical": row(business_case_type_id="immobilienkaufvertrag"),
            "mappable": row(),
            "conflict": row(business_case_type_id="unterschriftsbeglaubigung"),
            "unknown": row(legacy_choice="not-a-choice"),
            "missing": row(legacy_choice=None),
            "etag_skipped": row(current_etag='"2"'),
            "unresolved": row(read_status="partial"),
        }
        self.assertEqual(set(cases), set(CLASSIFICATIONS))
        for expected, fixture in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(classify_record(fixture, MAPPING, KNOWN_IDS).classification, expected)

    def test_new_only_known_is_canonical_and_new_only_unknown_is_unknown(self) -> None:
        known = classify_record(row(legacy_choice=None, business_case_type_id="testament-erbvertrag"), MAPPING, KNOWN_IDS)
        unknown = classify_record(row(legacy_choice=None, business_case_type_id="TESTAMENT-ERBVERTRAG"), MAPPING, KNOWN_IDS)
        self.assertEqual(known.classification, "already_canonical")
        self.assertEqual(unknown.classification, "unknown")

    def test_invalid_business_type_and_whitespace_are_unresolved_before_etag(self) -> None:
        for value in ("", "  ", 7, False, []):
            classified = classify_record(row(legacy_choice=value, snapshot_etag="", current_etag=""), MAPPING, KNOWN_IDS)
            self.assertEqual(classified.classification, "unresolved")

    def test_values_are_not_trimmed_or_normalized(self) -> None:
        classified = classify_record(row(legacy_choice=" immobilienkaufvertrag "), MAPPING, KNOWN_IDS)
        self.assertEqual(classified.classification, "unknown")

    def test_missing_or_extra_keys_and_invalid_ref_invalidate_shape(self) -> None:
        fixtures = [row(record_ref="case-1"), {**row(), "free_text": "forbidden"}, row()]
        fixtures[2].pop("current_etag")
        for fixture in fixtures:
            with self.subTest(fixture=fixture), self.assertRaises(MigrationValidationError):
                classify_record(fixture, MAPPING, KNOWN_IDS)


class PageAndBundleTests(unittest.TestCase):
    def test_pages_are_contiguous_complete_and_deduplicated_across_boundaries(self) -> None:
        fixture = [
            {"page_number": 1, "page_count": 2, "complete": False, "rows": [row("synref-a")]},
            {"page_number": 2, "page_count": 2, "complete": True, "rows": [row("synref-b")]},
        ]
        self.assertEqual([item["record_ref"] for item in validate_pages(fixture)], ["synref-a", "synref-b"])
        duplicate = copy.deepcopy(fixture)
        duplicate[1]["rows"][0]["record_ref"] = "synref-a"
        with self.assertRaises(MigrationValidationError):
            validate_pages(duplicate)

    def test_invalid_page_metadata_and_limits_produce_no_result(self) -> None:
        invalid = [
            [],
            [{"page_number": 0, "page_count": 1, "complete": True, "rows": []}],
            [{"page_number": 1, "page_count": 2, "complete": True, "rows": []}],
            [{"page_number": 1, "page_count": 1, "complete": False, "rows": []}],
            pages(*(row(f"synref-r-{index}") for index in range(101))),
        ]
        for fixture in invalid:
            with self.subTest(fixture_len=len(fixture)), self.assertRaises(MigrationValidationError):
                validate_pages(fixture)

    def test_registry_catalog_coverage_requires_exact_full_canonical_set(self) -> None:
        complete = registry_snapshot(*sorted(CANONICAL_IDS))
        normalized = validate_registry_catalog_coverage(complete, CANONICAL_IDS)
        self.assertEqual(
            [item["business_case_type_id"] for item in normalized["rows"]],
            sorted(CANONICAL_IDS),
        )
        missing = registry_snapshot(*sorted(CANONICAL_IDS - {"bautraegervertrag"}))
        extra = registry_snapshot(*sorted(CANONICAL_IDS | {"not-canonical"}))
        for snapshot in (missing, extra):
            with self.assertRaises(MigrationValidationError):
                validate_registry_catalog_coverage(snapshot, CANONICAL_IDS)

    def test_top_level_classification_pages_must_equal_scan_two_pages(self) -> None:
        bundle = valid_bundle()
        bundle["matter_pages"][0]["rows"][0]["current_etag"] = "synthetic-etag-top-level"
        bundle["matter_pages"][0]["rows"][0]["snapshot_etag"] = "synthetic-etag-top-level"
        with self.assertRaises(MigrationValidationError):
            validate_bundle(bundle)

    def test_scan_one_may_differ_but_readiness_blocks_as_scan_unstable(self) -> None:
        bundle = valid_bundle()
        scan_one_pages = copy.deepcopy(bundle["scans"][0]["matter_pages"])
        scan_one_pages[0]["rows"][0]["current_etag"] = "synthetic-etag-scan-one"
        scan_one_pages[0]["rows"][0]["snapshot_etag"] = "synthetic-etag-scan-one"
        bundle["scans"][0] = build_scan(
            scan_id="scan-one",
            scanned_at="2026-07-12T10:00:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=scan_one_pages,
        )

        self.assertEqual(len(validate_bundle(bundle)), 1)
        result = evaluate_cutover_readiness(
            classification_counts={
                name: (1 if name == "already_canonical" else 0)
                for name in CLASSIFICATIONS
            },
            scans=bundle["scans"],
            manifest_registry_snapshot_hash=canonical_json_hash(
                bundle["registry_snapshot"]
            ),
            current_registry_snapshot=bundle["post_scan_registry_snapshot"],
            manifest_process_snapshot_hash=canonical_json_hash(
                bundle["process_snapshot"]
            ),
            current_process_snapshot=bundle["post_scan_process_snapshot"],
            replay_result={"status": "PASSED"},
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason_codes"], ["scan_unstable"])

    def test_scan_hash_binds_page_boundaries(self) -> None:
        source = [row(f"synref-{name}") for name in ("a", "b", "c")]
        first_pages = [
            {"page_number": 1, "page_count": 2, "complete": False, "rows": source[:2]},
            {"page_number": 2, "page_count": 2, "complete": True, "rows": source[2:]},
        ]
        second_pages = [
            {"page_number": 1, "page_count": 2, "complete": False, "rows": source[:1]},
            {"page_number": 2, "page_count": 2, "complete": True, "rows": source[1:]},
        ]
        first = build_scan(
            scan_id="scan-one",
            scanned_at="2026-07-12T10:00:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=first_pages,
        )
        second = build_scan(
            scan_id="scan-two",
            scanned_at="2026-07-12T10:15:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=second_pages,
        )
        self.assertNotEqual(first["scan_hash"], second["scan_hash"])

    def test_strict_synthetic_bundle_validation(self) -> None:
        bundle = valid_bundle()
        self.assertEqual(len(validate_bundle(bundle)), 1)
        for key, value in (("contains_production_data", True), ("data_classification", "internal")):
            invalid = copy.deepcopy(bundle)
            invalid[key] = value
            with self.assertRaises(MigrationValidationError):
                validate_bundle(invalid)
        invalid = copy.deepcopy(bundle)
        invalid["documents"] = []
        with self.assertRaises(MigrationValidationError):
            validate_bundle(invalid)

    def test_rejects_fabricated_scan_summaries_and_boolean_counts_on_both_scans(self) -> None:
        mutations = (
            (0, "record_count", 0),
            (0, "record_count", True),
            (1, "record_count", False),
            (0, "scan_hash", "f" * 64),
        )
        for scan_index, field, value in mutations:
            bundle = valid_bundle()
            bundle["scans"][scan_index][field] = value
            with self.subTest(scan_index=scan_index, field=field), self.assertRaises(
                MigrationValidationError
            ):
                validate_bundle(bundle)

    def test_post_scan_capture_is_independent_nonempty_and_strictly_later(self) -> None:
        for mutate in (
            lambda bundle: bundle.update(post_scan_observed_at="2026-07-12T10:15:00Z"),
            lambda bundle: bundle.update(post_scan_observed_at="2026-07-12T10:14:59Z"),
            lambda bundle: bundle["post_scan_registry_snapshot"].update(rows=[]),
            lambda bundle: bundle["post_scan_registry_snapshot"]["rows"][0].update(secret="token"),
        ):
            bundle = valid_bundle()
            mutate(bundle)
            with self.assertRaises(MigrationValidationError):
                validate_bundle(bundle)

    def test_rejects_arbitrary_bindings_approvals_etags_and_snapshot_fields(self) -> None:
        mutations = (
            lambda bundle: bundle.update(bindings={}),
            lambda bundle: bundle["bindings"].update(site_hash="A" * 64),
            lambda bundle: bundle["bindings"].update(extra_hash="a" * 64),
            lambda bundle: bundle.update(role_approval_refs=["client-secret-value"]),
            lambda bundle: bundle["matter_pages"][0]["rows"][0].update(current_etag="Bearer-secret"),
            lambda bundle: bundle["matter_pages"][0]["rows"][0].update(
                current_etag="synthetic-etag-" + "a" * 65
            ),
            lambda bundle: bundle["registry_snapshot"]["rows"][0].update(etag="synthetic-etag-UPPER"),
            lambda bundle: bundle["registry_snapshot"]["rows"][0].update(etag="synthetic-etag-bad-"),
            lambda bundle: bundle["registry_snapshot"]["rows"][0].update(etag="registry-secret"),
            lambda bundle: bundle["process_snapshot"].update(secret="value"),
        )
        for mutate in mutations:
            bundle = valid_bundle()
            mutate(bundle)
            with self.assertRaises(MigrationValidationError):
                validate_bundle(bundle)


class ManifestAndPlanTests(unittest.TestCase):
    def _manifest(
        self,
        source_pages: list[dict[str, object]],
        registry: dict[str, object] | None = None,
        *,
        initial_process: dict[str, object] | None = None,
        final_scans: list[dict[str, object]] | None = None,
        post_scan_observed_at: str = "2026-07-12T10:15:01Z",
        post_registry: dict[str, object] | None = None,
        post_process: dict[str, object] | None = None,
        manifest_bindings: dict[str, str] | None = None,
    ) -> dict[str, object]:
        registry = registry or registry_snapshot(*sorted(CANONICAL_IDS))
        initial_process = initial_process or process_snapshot()
        final_scans = final_scans or [
            build_scan(
                scan_id=scan_id,
                scanned_at=scanned_at,
                writes_frozen=True,
                complete=True,
                pages_complete=True,
                matter_pages=copy.deepcopy(source_pages),
            )
            for scan_id, scanned_at in (
                ("scan-one", "2026-07-12T10:00:00Z"),
                ("scan-two", "2026-07-12T10:15:00Z"),
            )
        ]
        return build_manifest(
            repository_commit="a" * 40,
            catalog_version="2026.07",
            mapping_table=mapping_table(),
            matter_pages=source_pages,
            registry_snapshot=registry,
            process_snapshot=initial_process,
            bindings=bindings() if manifest_bindings is None else manifest_bindings,
            role_approval_refs=["synthetic-approval-privacy", "synthetic-approval-external-service"],
            schema_version="fixture/v1",
            runtime_version="runtime/v2",
            contract_version_n="contract/v2",
            candidate_n_minus_1="runtime-previous",
            runtime_candidate_registry=candidate_registry(),
            final_scans=final_scans,
            post_scan_observed_at=post_scan_observed_at,
            post_scan_registry_snapshot=post_registry or copy.deepcopy(registry),
            post_scan_process_snapshot=post_process or copy.deepcopy(initial_process),
            canonical_business_case_type_ids=CANONICAL_IDS,
        )

    def test_manifest_binds_hashes_counts_versions_etags_and_nullable_bpmn(self) -> None:
        manifest = self._manifest(pages(row()))
        self.assertEqual(manifest["matter_snapshot"]["row_count"], 1)
        self.assertEqual(len(manifest["manifest_hash"]), 64)
        changed = self._manifest(
            pages(
                row(
                    current_etag="synthetic-etag-changed",
                    snapshot_etag="synthetic-etag-changed",
                )
            )
        )
        self.assertNotEqual(manifest["matter_snapshot"]["hash"], changed["matter_snapshot"]["hash"])
        changed_process = process_snapshot()
        changed_process["rows"][0]["bpmn_link"] = "models/p-1.bpmn"
        other = self._manifest(
            pages(row()),
            initial_process=changed_process,
            post_process=copy.deepcopy(changed_process),
        )
        self.assertNotEqual(manifest["process_snapshot_hash"], other["process_snapshot_hash"])

    def test_manifest_snapshot_hashes_ignore_input_row_order(self) -> None:
        first = registry_snapshot(*sorted(CANONICAL_IDS))
        second = copy.deepcopy(first)
        second["rows"].reverse()
        self.assertEqual(
            self._manifest(pages(row()), first)["registry_snapshot_hash"],
            self._manifest(pages(row()), second)["registry_snapshot_hash"],
        )

    def test_manifest_matter_hash_binds_page_metadata_and_ignores_only_in_page_order(self) -> None:
        rows = [row(f"synref-{name}") for name in ("a", "b", "c", "d")]
        first = [
            {"page_number": 1, "page_count": 2, "complete": False, "rows": rows[:2]},
            {"page_number": 2, "page_count": 2, "complete": True, "rows": rows[2:]},
        ]
        reordered = copy.deepcopy(first)
        reordered[0]["rows"].reverse()
        boundary_changed = [
            {"page_number": 1, "page_count": 2, "complete": False, "rows": rows[:1]},
            {"page_number": 2, "page_count": 2, "complete": True, "rows": rows[1:]},
        ]
        first_hash = self._manifest(first)["matter_snapshot"]["hash"]
        self.assertEqual(first_hash, self._manifest(reordered)["matter_snapshot"]["hash"])
        self.assertNotEqual(
            first_hash,
            self._manifest(boundary_changed)["matter_snapshot"]["hash"],
        )

    def test_manifest_rejects_scan_two_classification_population_drift(self) -> None:
        source_pages = pages(row())
        first = build_scan(
            scan_id="scan-one",
            scanned_at="2026-07-12T10:00:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=source_pages,
        )
        divergent_second = build_scan(
            scan_id="scan-two",
            scanned_at="2026-07-12T10:15:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=pages(row("synref-other")),
        )
        with self.assertRaises(MigrationValidationError):
            self._manifest(
                source_pages,
                final_scans=[first, divergent_second],
            )

    def test_manifest_binds_unstable_scans_and_defers_policy_to_readiness(self) -> None:
        source_pages = pages(row())
        first = build_scan(
            scan_id="scan-one",
            scanned_at="2026-07-12T10:00:00Z",
            writes_frozen=False,
            complete=False,
            pages_complete=False,
            matter_pages=pages(row("synref-a"), row("synref-b")),
        )
        second = build_scan(
            scan_id="scan-two",
            scanned_at="2026-07-12T10:15:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=source_pages,
        )
        manifest = self._manifest(source_pages, final_scans=[first, second])
        self.assertEqual(manifest["final_scans"][0]["record_count"], 2)
        self.assertNotEqual(first["scan_hash"], second["scan_hash"])

        registry = registry_snapshot(*sorted(CANONICAL_IDS))
        process = process_snapshot()
        readiness = evaluate_cutover_readiness(
            classification_counts={
                name: (1 if name == "already_canonical" else 0)
                for name in CLASSIFICATIONS
            },
            scans=[first, second],
            manifest_registry_snapshot_hash=canonical_json_hash(registry),
            current_registry_snapshot=registry,
            manifest_process_snapshot_hash=canonical_json_hash(process),
            current_process_snapshot=process,
            replay_result={"status": "PASSED"},
        )
        self.assertEqual(readiness["status"], "BLOCKED")
        self.assertEqual(readiness["reason_codes"], ["scan_unstable"])

    def test_manifest_hash_changes_with_every_readiness_evidence_component(self) -> None:
        source_pages = pages(row())
        baseline = self._manifest(source_pages)
        changed_scan_pages = pages(
            row(
                current_etag="synthetic-etag-scan-changed",
                snapshot_etag="synthetic-etag-scan-changed",
            )
        )
        changed_scans = [
            build_scan(
                scan_id="scan-one",
                scanned_at="2026-07-12T10:00:00Z",
                writes_frozen=True,
                complete=True,
                pages_complete=True,
                matter_pages=changed_scan_pages,
            ),
            build_scan(
                scan_id="scan-two",
                scanned_at="2026-07-12T10:15:00Z",
                writes_frozen=True,
                complete=True,
                pages_complete=True,
                matter_pages=source_pages,
            ),
        ]
        changed_registry = registry_snapshot(*sorted(CANONICAL_IDS))
        changed_registry["rows"][0]["etag"] = "synthetic-etag-registry-changed"
        changed_process = process_snapshot()
        changed_process["rows"][0]["bpmn_link"] = "models/p-1.bpmn"
        variants = (
            self._manifest(source_pages, final_scans=changed_scans),
            self._manifest(source_pages, post_scan_observed_at="2026-07-12T10:15:02Z"),
            self._manifest(source_pages, post_registry=changed_registry),
            self._manifest(source_pages, post_process=changed_process),
        )
        for variant in variants:
            self.assertNotEqual(baseline["manifest_hash"], variant["manifest_hash"])
        self.assertIn("final_scans_hash", baseline)
        self.assertIn("post_scan_registry_snapshot_hash", baseline)
        self.assertIn("post_scan_process_snapshot_hash", baseline)

    def test_manifest_requires_exact_bindings_and_hashes_approval_refs(self) -> None:
        manifest = self._manifest(pages(row()))
        self.assertNotIn("role_approval_refs", manifest)
        self.assertEqual(
            manifest["role_approval_ref_hashes"],
            sorted(
                [
                    text_hash("synthetic-approval-privacy"),
                    text_hash("synthetic-approval-external-service"),
                ]
            ),
        )
        for invalid_bindings in ({}, {**bindings(), "site_hash": "A" * 64}):
            with self.subTest(bindings=invalid_bindings), self.assertRaises(MigrationValidationError):
                self._manifest(pages(row()), manifest_bindings=invalid_bindings)

    def test_snapshot_schema_and_local_bpmn_link_are_exact(self) -> None:
        for link in ("https://example.test/model.bpmn", "../model.bpmn", "models/Bad.bpmn", "models/a/b.bpmn"):
            process = process_snapshot()
            process["rows"][0]["bpmn_link"] = link
            with self.subTest(link=link), self.assertRaises(MigrationValidationError):
                self._manifest(pages(row()), initial_process=process)

    def test_backfill_plans_only_mappable_rows_and_repaginates_at_100(self) -> None:
        source = [row(f"synref-record-{index:03d}") for index in range(101)]
        source.extend(
            [
                row("synref-canonical", business_case_type_id="immobilienkaufvertrag"),
                row("synref-conflict", business_case_type_id="unterschriftsbeglaubigung"),
            ]
        )
        classified = classify_records(source, MAPPING, KNOWN_IDS)
        plan = build_backfill_plan(classified, manifest_hash="a" * 64, observed_at="2026-07-12T10:00:00Z")
        self.assertEqual(plan["operation_count"], 101)
        self.assertEqual([page["operation_count"] for page in plan["pages"]], [100, 1])
        self.assertEqual(plan["page_hashes"], [page["page_hash"] for page in plan["pages"]])
        operations = [operation for page in plan["pages"] for operation in page["operations"]]
        self.assertEqual([item["record_ref_hash"] for item in operations], sorted(item["record_ref_hash"] for item in operations))
        self.assertTrue(all(set(item) == {"record_ref_hash", "field", "value", "if_match", "idempotency_key"} for item in operations))
        self.assertTrue(all(item["field"] == "VorgangstypId" for item in operations))
        self.assertEqual(len(plan["quarantine"]), 1)
        self.assertEqual(plan["quarantine"][0]["classification"], "conflict")

    def test_plan_is_stable_across_input_order_and_observed_at_is_not_record_identity(self) -> None:
        classified = classify_records([row("synref-z"), row("synref-a", legacy_choice=None)], MAPPING, KNOWN_IDS)
        first = build_backfill_plan(classified, manifest_hash="a" * 64, observed_at="2026-07-12T10:00:00Z")
        second = build_backfill_plan(tuple(reversed(classified)), manifest_hash="a" * 64, observed_at="2026-07-12T11:00:00Z")
        self.assertEqual(first["pages"], second["pages"])
        self.assertEqual(first["quarantine"][0]["record_id"], second["quarantine"][0]["record_id"])
        self.assertNotEqual(first["quarantine"][0]["observed_at"], second["quarantine"][0]["observed_at"])
        self.assertEqual(set(item["classification"] for item in first["quarantine"]), BLOCKER_CLASSIFICATIONS & {"missing"})


class ReadinessEvidenceAnchorTests(unittest.TestCase):
    def _inputs(self) -> dict[str, object]:
        return {
            "base_manifest_hash": "a" * 64,
            "backfill_plan": {"operation_count": 1, "page_hashes": ["b" * 64]},
            "replay_scenarios": replay_scenarios(),
            "profile_evaluation_result": {"status": "PASSED", "candidates": []},
            "reconciled_quarantine_index": {
                "status": "RECONCILED",
                "record_hashes": ["c" * 64],
            },
        }

    def test_anchor_exposes_canonical_component_hashes(self) -> None:
        inputs = self._inputs()
        anchor = build_readiness_evidence_anchor(**inputs)
        expected = {
            "base_manifest_hash": inputs["base_manifest_hash"],
            "backfill_plan_hash": canonical_json_hash(inputs["backfill_plan"]),
            "replay_scenarios_hash": canonical_json_hash(inputs["replay_scenarios"]),
            "profile_evaluation_result_hash": canonical_json_hash(
                inputs["profile_evaluation_result"]
            ),
            "reconciled_quarantine_index_hash": canonical_json_hash(
                inputs["reconciled_quarantine_index"]
            ),
        }
        self.assertEqual(
            anchor,
            {**expected, "readiness_evidence_hash": canonical_json_hash(expected)},
        )

    def test_anchor_changes_when_any_readiness_component_changes(self) -> None:
        baseline_inputs = self._inputs()
        baseline = build_readiness_evidence_anchor(**baseline_inputs)
        mutations = {
            "base_manifest_hash": "f" * 64,
            "backfill_plan": {"operation_count": 2, "page_hashes": ["b" * 64]},
            "replay_scenarios": {**replay_scenarios(), "extra": {}},
            "profile_evaluation_result": {
                "status": "BLOCKED",
                "candidates": [],
            },
            "reconciled_quarantine_index": {
                "status": "RECONCILED",
                "record_hashes": [],
            },
        }
        for name, value in mutations.items():
            inputs = self._inputs()
            inputs[name] = value
            changed = build_readiness_evidence_anchor(**inputs)
            with self.subTest(component=name):
                self.assertNotEqual(
                    baseline["readiness_evidence_hash"],
                    changed["readiness_evidence_hash"],
                )

    def test_anchor_rejects_invalid_base_manifest_hash(self) -> None:
        inputs = self._inputs()
        inputs["base_manifest_hash"] = "not-a-hash"
        with self.assertRaises(MigrationValidationError):
            build_readiness_evidence_anchor(**inputs)


class ScanReadinessTests(unittest.TestCase):
    def _ready_inputs(self) -> dict[str, object]:
        source = [row(business_case_type_id="immobilienkaufvertrag")]
        first = build_scan(
            scan_id="scan-one",
            scanned_at="2026-07-12T10:00:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=pages(*source),
        )
        second = build_scan(
            scan_id="scan-two",
            scanned_at="2026-07-12T10:15:00Z",
            writes_frozen=True,
            complete=True,
            pages_complete=True,
            matter_pages=pages(*source),
        )
        registry = registry_snapshot("immobilienkaufvertrag")
        process = {"status": "not_provisioned"}
        return {
            "classification_counts": {name: (1 if name == "already_canonical" else 0) for name in CLASSIFICATIONS},
            "scans": [first, second],
            "manifest_registry_snapshot_hash": canonical_json_hash(registry),
            "current_registry_snapshot": registry,
            "manifest_process_snapshot_hash": canonical_json_hash(process),
            "current_process_snapshot": process,
            "replay_result": {"status": "PASSED"},
        }

    def test_ready_requires_two_identical_complete_frozen_scans_at_900_seconds(self) -> None:
        self.assertEqual(evaluate_cutover_readiness(**self._ready_inputs())["status"], "READY")

    def test_each_scan_replay_snapshot_or_classification_drift_blocks(self) -> None:
        mutators = [
            lambda data: data["scans"][1].update(scanned_at="2026-07-12T10:14:59Z"),
            lambda data: data["scans"][1].update(scan_id="scan-one"),
            lambda data: data["scans"][1].update(writes_frozen=False),
            lambda data: data["scans"][1].update(scan_hash="f" * 64),
            lambda data: data["classification_counts"].update(mappable=1),
            lambda data: data["replay_result"].update(status="BLOCKED"),
            lambda data: data.update(manifest_registry_snapshot_hash="f" * 64),
            lambda data: data.update(manifest_process_snapshot_hash="f" * 64),
        ]
        for mutate in mutators:
            data = self._ready_inputs()
            mutate(data)
            result = evaluate_cutover_readiness(**data)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertTrue(result["requires_two_new_complete_scans"])


class ReplayAndRecoveryTests(unittest.TestCase):
    def test_local_port_executes_all_four_cases_for_n_and_n_minus_1(self) -> None:
        result = run_migration_replay(
            candidate_registry=candidate_registry(),
            scenarios=replay_scenarios(),
            canonical_business_case_type_ids=KNOWN_IDS,
            port=LocalMigrationReplayPort(),
        )
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual({candidate["generation"] for candidate in result["candidates"]}, {"N", "N-1"})
        self.assertTrue(all(len(candidate["checks"]) == 4 for candidate in result["candidates"]))
        self.assertTrue(all(check["passed"] for candidate in result["candidates"] for check in candidate["checks"]))

    def test_profile_hash_drift_and_behavior_failure_block_replay(self) -> None:
        registry = candidate_registry()
        registry["candidates"][0]["profile"]["unknown_id_decision"] = "ACCEPTED"
        result = run_migration_replay(
            candidate_registry=registry,
            scenarios=replay_scenarios(),
            canonical_business_case_type_ids=KNOWN_IDS,
            port=LocalMigrationReplayPort(),
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["candidates"][0]["profile_hash_matches"])
        unknown_check = next(
            check for check in result["candidates"][0]["checks"] if check["scenario_id"] == "unknown-id-fail-closed"
        )
        self.assertEqual(unknown_check["reason_code"], "unknown_id_accepted")

    def test_candidate_registry_is_independent_and_exactly_n_and_n_minus_1(self) -> None:
        registry = candidate_registry()
        registry["candidates"][1]["candidate_id"] = registry["candidates"][0]["candidate_id"]
        with self.assertRaises(MigrationValidationError):
            run_migration_replay(
                candidate_registry=registry,
                scenarios=replay_scenarios(),
                canonical_business_case_type_ids=KNOWN_IDS,
                port=LocalMigrationReplayPort(),
            )

    def test_rollback_order_and_forward_recovery_remain_non_executing_and_blocked(self) -> None:
        rollback = build_rollback_plan(manifest_hash="a" * 64, candidate_n_minus_1="runtime-previous")
        forward = build_forward_recovery_plan(manifest_hash="a" * 64, candidate_n="runtime-current")
        self.assertEqual([step["step_number"] for step in rollback["steps"]], [1, 2, 3, 4, 5, 6])
        self.assertIn("require_executable_validation_before_switching_to_n_minus_1", rollback["steps"][3]["action"])
        self.assertFalse(rollback["deletes_columns"])
        self.assertFalse(rollback["deletes_canonical_values"])
        self.assertFalse(rollback["executes_actions"])
        self.assertEqual(rollback["status"], "BLOCKED_PENDING_S6_S7_APPROVAL")
        self.assertEqual(forward["status"], "BLOCKED_PENDING_S6_S7_APPROVAL")
        self.assertTrue(forward["requires_s6_outbox"])
        self.assertTrue(forward["requires_s7_approval"])
        self.assertFalse(forward["creates_legacy_substitute_values"])
        self.assertFalse(forward["executes_actions"])


class PurityTests(unittest.TestCase):
    def test_module_exposes_no_io_configuration_or_live_transport_surface(self) -> None:
        import src.notary_kg.business_case_type_migration as module

        forbidden = {"Path", "open", "os", "subprocess", "requests", "urllib", "socket"}
        self.assertTrue(forbidden.isdisjoint(vars(module)))
        self.assertEqual(text_hash("synref-a"), text_hash("synref-a"))


if __name__ == "__main__":
    unittest.main()
