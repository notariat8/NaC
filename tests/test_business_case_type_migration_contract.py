from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
SPEC = importlib.util.spec_from_file_location(
    "validate_business_case_type_migration",
    ROOT / "scripts/validate_business_case_type_migration.py",
)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)
from scripts import validate_language_parity

from notary_kg.business_case_type_migration import (  # noqa: E402
    MigrationValidationError,
    canonical_json_hash,
    validate_bundle,
    validate_mapping_table,
)
from notary_kg.business_case_type_runtime import BusinessCaseTypeCatalog  # noqa: E402


class BusinessCaseTypeMigrationContractTests(unittest.TestCase):
    def load(self, relative: str) -> dict[str, object]:
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_standalone_validator_accepts_complete_owned_slice(self) -> None:
        self.assertEqual(validator.validate_repository(ROOT), [])

    def test_contract_closes_live_and_tenant_boundaries(self) -> None:
        contract = self.load("workflows/contracts/business-case-type-migration-s5.contract.json")
        verification = self.load(
            "workflows/verification-contracts/business-case-type-migration-s5.verification.json"
        )
        self.assertEqual(contract["slice"]["allowed_live_calls"], 0)
        self.assertEqual(contract["slice"]["allowed_tenant_writes"], 0)
        self.assertTrue(contract["slice"]["offline_only"])
        self.assertFalse(
            contract["redaction_and_io"]["network_http_dns_graph_sharepoint_entra_allowed"]
        )
        self.assertFalse(
            contract["redaction_and_io"]["tenant_schema_matter_registry_process_writes_allowed"]
        )
        self.assertEqual(verification["thresholds"]["allowed_live_calls"], 0)
        self.assertEqual(verification["thresholds"]["allowed_tenant_writes"], 0)
        self.assertEqual(
            contract["input_bundle"]["post_scan_fields_exact"],
            ["post_scan_observed_at", "post_scan_registry_snapshot", "post_scan_process_snapshot"],
        )
        self.assertEqual(
            contract["input_bundle"]["bindings_keys_exact"],
            ["site_hash", "schema_hash", "matter_list_hash", "registry_list_hash", "process_list_hash"],
        )
        self.assertTrue(contract["manifest"]["matter_page_metadata_and_boundaries_bound"])
        self.assertTrue(contract["manifest"]["role_approval_references_stored_as_hashes"])
        self.assertTrue(contract["readiness"]["post_scan_observed_at_strictly_after_scan_two"])
        self.assertEqual(
            contract["redaction_and_io"]["stdout_fields_exact"],
            [
                "status",
                "readiness_scope",
                "live_cutover_status",
                "allowed_live_calls",
                "allowed_tenant_writes",
                "reason_codes",
                "class_counts",
                "top_level_hashes",
            ],
        )

    def test_mapping_matches_domain_exact_four_typed_baseline(self) -> None:
        mapping = self.load(
            "workflows/migrations/business-case-type/legacy-choice.mapping.json"
        )
        catalog = BusinessCaseTypeCatalog.from_repo(ROOT)
        known = frozenset(entry.business_case_type_id for entry in catalog.entries)
        validated = validate_mapping_table(mapping, known)
        self.assertEqual(set(validated), set(validator.BASELINE))
        self.assertEqual(validated, {value: value for value in validator.BASELINE})
        self.assertEqual(validator.validate_mapping(mapping), [])

        drifted = copy.deepcopy(mapping)
        drifted["mappings"].append({"source": "extra", "target": "immobilienkaufvertrag"})
        with self.assertRaises(MigrationValidationError):
            validate_mapping_table(drifted, known)

    def test_mapping_source_and_target_are_typed_identifiers_not_human_text(self) -> None:
        mapping = self.load(
            "workflows/migrations/business-case-type/legacy-choice.mapping.json"
        )
        self.assertEqual(
            validate_language_parity._scan_json_value_for_umlauts(
                mapping,
                "workflows/migrations/business-case-type/legacy-choice.mapping.json",
            ),
            [],
        )

    def test_runtime_candidates_are_independently_hash_pinned_for_domain_api(self) -> None:
        candidates = self.load(
            "workflows/migrations/business-case-type/runtime-candidates.json"
        )
        self.assertEqual(
            [(item["candidate_id"], item["contract_version"]) for item in candidates["candidates"]],
            [("runtime-current", "v2"), ("runtime-previous", "v1")],
        )
        self.assertEqual(candidates["scenarios_exact"], list(validator.SCENARIOS))
        for candidate in candidates["candidates"]:
            self.assertEqual(
                candidate["profile_sha256"], canonical_json_hash(candidate["profile"])
            )
        self.assertEqual(validator.validate_candidates(candidates), [])

        drifted = copy.deepcopy(candidates)
        drifted["candidates"][1]["profile"]["reads_canonical_id"] = False
        self.assertTrue(
            any("profile" in error for error in validator.validate_candidates(drifted))
        )

    def test_all_valid_fixtures_use_exact_completed_bundle_api(self) -> None:
        fixture_root = ROOT / "tests/fixtures/business-case-type-migration"
        expected = {
            "clean-ready.fixture.json",
            "all-classes-blocked.fixture.json",
            "process-present.fixture.json",
            "process-not-provisioned.fixture.json",
            "replay-blocked.fixture.json",
            "quarantine-retry.fixture.json",
            "quarantine-divergent.fixture.json",
        }
        actual = {path.name for path in fixture_root.glob("*.fixture.json")}
        self.assertEqual(actual, expected)
        for path in sorted(fixture_root.glob("*.fixture.json")):
            with self.subTest(path=path.name):
                fixture = json.loads(path.read_text(encoding="utf-8"))
                records = validate_bundle(fixture)
                self.assertTrue(records)
                self.assertEqual(fixture["data_classification"], "synthetic")
                self.assertFalse(fixture["contains_production_data"])
                self.assertEqual(validator._walk_fixture_boundary(fixture), [])

    def test_paging_drift_fixture_is_rejected_without_partial_result(self) -> None:
        fixture = self.load(
            "tests/fixtures/business-case-type-migration/paging-drift.invalid.json"
        )
        with self.assertRaises(MigrationValidationError):
            validate_bundle(fixture)

    def test_classification_oracle_covers_normative_order(self) -> None:
        fixture = self.load(
            "tests/fixtures/business-case-type-migration/all-classes-blocked.fixture.json"
        )
        mapping_doc = self.load(
            "workflows/migrations/business-case-type/legacy-choice.mapping.json"
        )
        mapping = validator.mapping_table(mapping_doc)
        known = {
            row["business_case_type_id"] for row in fixture["registry_snapshot"]["rows"]
        }
        classes = [
            validator.classify_row(row, mapping, known)
            for page in fixture["matter_pages"]
            for row in page["rows"]
        ]
        self.assertEqual(classes, list(validator.CLASSES))


if __name__ == "__main__":
    unittest.main()
