from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
FIXTURE_ROOT = Path("tests/fixtures/business-case-type-migration")
MAPPING_PATH = Path("workflows/migrations/business-case-type/legacy-choice.mapping.json")
CANDIDATES_PATH = Path("workflows/migrations/business-case-type/runtime-candidates.json")
DOMAIN_CONTRACT_PATH = Path("workflows/contracts/business-case-type-migration-s5.contract.json")
VERIFICATION_CONTRACT_PATH = Path(
    "workflows/verification-contracts/business-case-type-migration-s5.verification.json"
)
AGENT_CONTEXT_PATH = Path("agent-context/index.json")
DECISION_INDEX_PATH = Path("agent-context/decision-index.json")
INVARIANT_INDEX_PATH = Path("agent-context/invariant-index.json")

CLASSES = (
    "already_canonical",
    "mappable",
    "conflict",
    "unknown",
    "missing",
    "etag_skipped",
    "unresolved",
)
BLOCKER_CLASSES = CLASSES[2:]
BASELINE = (
    "handelsregisteranmeldung",
    "immobilienkaufvertrag",
    "online-gmbh-gruendung",
    "unterschriftsbeglaubigung",
)
SCENARIOS = (
    "read-vorgangstyp-id",
    "ignore-additive-registry-fields",
    "unknown-id-fail-closed",
    "new-type-without-legacy-read-only",
)
CANDIDATE_IDS = ("runtime-current", "runtime-previous")
ROW_KEYS = {
    "record_ref",
    "snapshot_etag",
    "current_etag",
    "legacy_choice",
    "business_case_type_id",
    "read_status",
}
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
REF_RE = re.compile(r"^synref-[a-z0-9-]+$")
FORBIDDEN_FIXTURE_KEYS = {
    "token",
    "access_token",
    "refresh_token",
    "credential",
    "certificate",
    "person",
    "document",
    "free_text",
    "graph_response",
    "site_id",
    "list_id",
    "matter_id",
    "url",
}


def canonical_bytes(value: object) -> bytes:
    def reject_floats(item: object) -> None:
        if isinstance(item, float):
            raise ValueError("floats are forbidden in canonical migration data")
        if isinstance(item, list):
            for child in item:
                reject_floats(child)
        elif isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings")
                reject_floats(child)

    reject_floats(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_hash(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    canonical_bytes(value)
    return value


def _nonempty_exact_string(value: object) -> bool:
    return isinstance(value, str) and bool(value) and bool(value.strip())


def classify_row(
    row: Mapping[str, object],
    mapping: Mapping[str, str],
    known_canonical_ids: set[str],
) -> str:
    legacy = row.get("legacy_choice")
    canonical = row.get("business_case_type_id")
    valid_business_value = lambda value: value is None or _nonempty_exact_string(value)
    if row.get("read_status") != "complete" or not valid_business_value(legacy) or not valid_business_value(canonical):
        return "unresolved"
    snapshot_etag, current_etag = row.get("snapshot_etag"), row.get("current_etag")
    if not _nonempty_exact_string(snapshot_etag) or not _nonempty_exact_string(current_etag) or snapshot_etag != current_etag:
        return "etag_skipped"
    if legacy is None and canonical is None:
        return "missing"
    if isinstance(legacy, str) and isinstance(canonical, str):
        if canonical in known_canonical_ids and mapping.get(legacy) == canonical:
            return "already_canonical"
        return "conflict"
    if legacy is None and isinstance(canonical, str):
        return "already_canonical" if canonical in known_canonical_ids else "unknown"
    if isinstance(legacy, str) and canonical is None:
        return "mappable" if legacy in mapping else "unknown"
    return "unresolved"


def validate_mapping(mapping_doc: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    expected_keys = {
        "schema_version",
        "mapping_id",
        "mapping_version",
        "typed_namespaces",
        "normalization_allowed",
        "mappings",
    }
    if set(mapping_doc) != expected_keys:
        errors.append("mapping top-level shape mismatch")
    if mapping_doc.get("schema_version") != "nac.business-case-type-legacy-choice-mapping/v0.1":
        errors.append("mapping schema_version mismatch")
    if mapping_doc.get("mapping_version") != "2026-07-12.1":
        errors.append("mapping version mismatch")
    if mapping_doc.get("typed_namespaces") != {"source": "LegacyChoice", "target": "BusinessCaseTypeId"}:
        errors.append("mapping typed namespaces mismatch")
    if mapping_doc.get("normalization_allowed") is not False:
        errors.append("mapping normalization must be forbidden")
    rows = mapping_doc.get("mappings")
    if not isinstance(rows, list) or any(not isinstance(row, dict) or set(row) != {"source", "target"} for row in rows):
        return errors + ["mapping rows must contain exactly source and target"]
    sources = [row.get("source") for row in rows]
    targets = [row.get("target") for row in rows]
    if sources != list(BASELINE) or targets != list(BASELINE):
        errors.append("mapping must be the sorted exact four-row typed identity baseline")
    if len(set(sources)) != len(sources) or len(set(targets)) != len(targets):
        errors.append("mapping sources and direct targets must be unique")
    return errors


def mapping_table(mapping_doc: Mapping[str, object]) -> dict[str, str]:
    rows = mapping_doc.get("mappings", [])
    return {
        str(row["source"]): str(row["target"])
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("source"), str) and isinstance(row.get("target"), str)
    }


def validate_candidates(document: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    if set(document) != {"schema_version", "registry_id", "registry_version", "scenarios_exact", "candidates"}:
        errors.append("runtime candidate registry top-level shape mismatch")
    if document.get("schema_version") != "nac.business-case-type-migration-runtime-candidates/v0.1":
        errors.append("runtime candidate schema_version mismatch")
    if document.get("scenarios_exact") != list(SCENARIOS):
        errors.append("runtime candidate scenarios must be the exact four ordered scenarios")
    candidates = document.get("candidates")
    if not isinstance(candidates, list) or [item.get("candidate_id") for item in candidates if isinstance(item, dict)] != list(CANDIDATE_IDS):
        return errors + ["runtime candidates must be exact ordered N and N-1"]
    expected_profile = {
        "canonical_field": "VorgangstypId",
        "reads_canonical_id": True,
        "ignores_additive_registry_fields": True,
        "unknown_id_decision": "BLOCKED",
        "unknown_id_reason_code": "unknown_business_case_type_id",
        "new_type_without_legacy_decision": "READ_ONLY",
        "legacy_choice_required_for_display": False,
    }
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict) or set(candidate) != {"candidate_id", "contract_version", "profile", "profile_sha256"}:
            errors.append("runtime candidate shape mismatch")
            continue
        if candidate.get("contract_version") != ("v2" if index == 0 else "v1"):
            errors.append(f"{candidate.get('candidate_id')} contract version mismatch")
        if candidate.get("profile") != expected_profile:
            errors.append(f"{candidate.get('candidate_id')} replay profile semantic drift")
        expected_hash = canonical_hash(candidate.get("profile"))
        if candidate.get("profile_sha256") != expected_hash:
            errors.append(f"{candidate.get('candidate_id')} profile_sha256 mismatch; expected {expected_hash}")
    return errors


def _walk_fixture_boundary(value: object, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.lower() in FORBIDDEN_FIXTURE_KEYS:
                errors.append(f"{path}.{key} is forbidden in synthetic migration fixtures")
            errors.extend(_walk_fixture_boundary(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_fixture_boundary(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        lowered = value.lower()
        if "://" in lowered or "graph.microsoft" in lowered or "sharepoint.com" in lowered:
            errors.append(f"{path} contains a forbidden network or tenant locator")
    return errors


def validate_contracts(domain: Mapping[str, object], verification: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    if domain.get("schema_version") != "nac.business-case-type-migration-s5/v0.1" or domain.get("contract_id") != "notary-kg.business_case_type_migration_s5":
        errors.append("domain contract identity mismatch")
    if domain.get("leading_issue") != "https://github.com/notariat8/NaC/issues/618":
        errors.append("domain contract Issue #618 traceability mismatch")
    slice_boundary = domain.get("slice", {})
    if not isinstance(slice_boundary, dict) or slice_boundary.get("allowed_live_calls") != 0 or slice_boundary.get("allowed_tenant_writes") != 0 or slice_boundary.get("offline_only") is not True:
        errors.append("domain contract no-live boundary mismatch")
    classification = domain.get("classification", {})
    if not isinstance(classification, dict) or classification.get("classes_exact") != list(CLASSES):
        errors.append("domain contract exact seven classes mismatch")
    if domain.get("mapping", {}).get("sources_exact") != list(BASELINE):
        errors.append("domain contract exact baseline mapping mismatch")
    input_bundle = domain.get("input_bundle", {})
    if input_bundle.get("post_scan_fields_exact") != ["post_scan_observed_at", "post_scan_registry_snapshot", "post_scan_process_snapshot"]:
        errors.append("domain contract independent post-scan fields mismatch")
    if input_bundle.get("catalog_version_must_equal_runtime_catalog") is not True:
        errors.append("domain contract runtime catalog binding mismatch")
    if (
        input_bundle.get("max_fixture_bytes") != 4 * 1024 * 1024
        or input_bundle.get("top_level_matter_pages_must_equal_second_scan") is not True
    ):
        errors.append("domain contract bounded fixture/final-classification binding mismatch")
    if input_bundle.get("synthetic_etag_suffix_max_length") != 64:
        errors.append("domain contract synthetic ETag boundary mismatch")
    if input_bundle.get("bindings_keys_exact") != ["site_hash", "schema_hash", "matter_list_hash", "registry_list_hash", "process_list_hash"]:
        errors.append("domain contract exact binding keys mismatch")
    manifest = domain.get("manifest", {})
    if manifest.get("matter_page_metadata_and_boundaries_bound") is not True:
        errors.append("domain contract page-bound manifest mismatch")
    if manifest.get("role_approval_references_stored_as_hashes") is not True:
        errors.append("domain contract approval-reference redaction mismatch")
    if (
        manifest.get("binds_independent_final_scan_pages_and_summaries") is not True
        or manifest.get("binds_post_scan_observed_at_and_snapshots") is not True
        or manifest.get("registry_snapshot_ids_must_exactly_equal_runtime_catalog") is not True
        or manifest.get("cross_scan_instability_is_readiness_blocker_not_manifest_error") is not True
    ):
        errors.append("domain contract complete readiness-evidence binding mismatch")
    quarantine = domain.get("quarantine", {})
    if (
        quarantine.get("filesystem_exclusive_lock_required") is not True
        or quarantine.get("durability_failure_restores_previous_committed_index_or_output") is not True
        or quarantine.get("nonempty_reconciled_store_blocks_ready") is not True
        or quarantine.get("lock_held_through_readiness_and_output_commit") is not True
        or quarantine.get("deterministic_recovery_marker_suffix") != ".previous"
        or quarantine.get("nonblocking_existing_file_reads") is not True
        or quarantine.get("max_record_bytes") != 16 * 1024
        or quarantine.get("max_index_bytes") != 32 * 1024 * 1024
        or quarantine.get("max_directory_entries") != 100_128
    ):
        errors.append("domain contract quarantine serialization/readiness mismatch")
    readiness = domain.get("readiness", {})
    if readiness.get("ready_class_exact") != "already_canonical" or readiness.get("minimum_separation_seconds") != 900:
        errors.append("domain contract strict cutover readiness mismatch")
    if readiness.get("post_scan_observed_at_strictly_after_scan_two") is not True:
        errors.append("domain contract post-scan timing mismatch")
    if (
        readiness.get("readiness_scope_exact") != "S5_OFFLINE_ONLY"
        or readiness.get("live_cutover_status_exact") != "BLOCKED_PENDING_S6_S7_APPROVAL"
        or readiness.get("independent_scan_page_sets_required") is not True
        or readiness.get("reconciled_quarantine_must_be_empty") is not True
    ):
        errors.append("domain contract qualified offline-readiness mismatch")
    replay = domain.get("replay", {})
    if (
        replay.get("candidates_exact") != list(CANDIDATE_IDS)
        or replay.get("candidate_contract_versions_exact") != ["v2", "v1"]
        or replay.get("scenarios_exact") != list(SCENARIOS)
        or replay.get("fixture_boolean_assertions_are_replay") is not False
        or replay.get("mode_exact") != "pinned_profile_evaluation_not_runtime_execution"
        or replay.get("executes_binary_or_deployment") is not False
        or replay.get("failed_or_drifted_profile_evaluation_behavior") != "BLOCKED"
    ):
        errors.append("domain contract replay boundary mismatch")
    anchor = domain.get("readiness_evidence_anchor", {})
    if anchor != {
        "base_manifest_hash_required": True,
        "binds_backfill_plan_hash": True,
        "binds_replay_scenarios_hash": True,
        "binds_profile_evaluation_result_hash": True,
        "binds_reconciled_quarantine_index_hash": True,
        "hash_field_exact": "readiness_evidence_hash",
    }:
        errors.append("domain contract final readiness-evidence anchor mismatch")
    recovery = domain.get("recovery", {})
    if (
        not isinstance(recovery.get("rollback_steps_exact"), list)
        or len(recovery["rollback_steps_exact"]) != 6
        or recovery["rollback_steps_exact"][3] != "require_executable_validation_before_switching_to_n_minus_1"
        or recovery.get("status_exact") != "BLOCKED_PENDING_S6_S7_APPROVAL"
    ):
        errors.append("domain contract rollback/forward recovery mismatch")
    io = domain.get("redaction_and_io", {})
    if io.get("network_http_dns_graph_sharepoint_entra_allowed") is not False or io.get("tenant_schema_matter_registry_process_writes_allowed") is not False:
        errors.append("domain contract external service or tenant-write boundary mismatch")
    if (
        io.get("git_admin_default_max_bytes") != 1024 * 1024
        or io.get("packed_refs_max_bytes") != 8 * 1024 * 1024
        or io.get("output_specific_filesystem_lock_required") is not True
        or io.get("conditional_rollback_on_replacement_inode") is not True
        or io.get("declared_recovery_marker_reconciled_before_write") is not True
    ):
        errors.append("domain contract bounded-read/output-commit boundary mismatch")
    if io.get("stdout_fields_exact") != [
        "status",
        "readiness_scope",
        "live_cutover_status",
        "allowed_live_calls",
        "allowed_tenant_writes",
        "reason_codes",
        "class_counts",
        "top_level_hashes",
    ]:
        errors.append("domain contract stdout shape mismatch")
    criteria = domain.get("acceptance_criteria")
    expected_ids = [f"AC-S5-{number:02d}" for number in range(1, 8)]
    if not isinstance(criteria, list) or [item.get("id") for item in criteria if isinstance(item, dict)] != expected_ids:
        errors.append("domain contract AC-S5-01..07 coverage mismatch")

    if verification.get("schema_version") != "nac.verification-contract/v0.1" or verification.get("domain_contract_id") != domain.get("contract_id"):
        errors.append("verification contract identity/domain binding mismatch")
    if verification.get("acceptance_ids") != expected_ids:
        errors.append("verification contract AC-S5-01..07 coverage mismatch")
    thresholds = verification.get("thresholds", {})
    if thresholds.get("allowed_live_calls") != 0 or thresholds.get("allowed_tenant_writes") != 0 or thresholds.get("legacy_mapping_rows") != 4:
        errors.append("verification thresholds mismatch")
    policy = verification.get("evidence_policy", {})
    if policy.get("synthetic_only") is not True or policy.get("allowed_live_calls") != 0 or policy.get("allowed_tenant_writes") != 0:
        errors.append("verification synthetic no-live evidence policy mismatch")
    required_checks = {
        "python3 scripts/validate_business_case_type_migration.py",
        "python3 -m unittest tests.test_business_case_type_migration tests.test_business_case_type_migration_quarantine tests.test_business_case_type_migration_cli tests.test_business_case_type_migration_contract",
    }
    if not required_checks.issubset(set(verification.get("checks", []))):
        errors.append("verification required focused checks mismatch")
    return errors


def validate_agent_indexes(
    agent_context: Mapping[str, object],
    decisions: Mapping[str, object],
    invariants: Mapping[str, object],
) -> list[str]:
    errors: list[str] = []
    categories = [
        category
        for layer in agent_context.get("layers", [])
        if isinstance(layer, dict)
        for category in layer.get("categories", [])
        if isinstance(category, dict) and category.get("id") == "business_case_type_migration_s5"
    ]
    if len(categories) != 1:
        errors.append("agent context requires exactly one S5 migration route")
    indexed_decisions = [
        item for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("context_key") == "business_case_type_migration_s5"
    ]
    if len(indexed_decisions) != 1:
        errors.append("decision index requires exactly one S5 migration decision")
    required_invariants = {
        "invariant.business_case_type.migration_exact_classification",
        "invariant.business_case_type.migration_quarantine_no_delete",
        "invariant.business_case_type.migration_zero_live_calls_writes",
    }
    actual_invariants = {
        item.get("id") for item in invariants.get("invariants", [])
        if isinstance(item, dict) and item.get("domain") == "business_case_type_migration"
    }
    for invariant_id in sorted(required_invariants - actual_invariants):
        errors.append(f"invariant index missing {invariant_id}")
    return errors


def validate_domain_fixtures(root: Path, mapping_doc: Mapping[str, object], candidates: Mapping[str, object]) -> list[str]:
    errors: list[str] = []
    try:
        from notary_kg.business_case_type_migration import (
            LocalMigrationReplayPort,
            MigrationValidationError,
            build_backfill_plan,
            build_scan,
            canonical_json_hash,
            classify_records,
            evaluate_cutover_readiness,
            run_migration_replay,
            validate_bundle,
            validate_mapping_table,
        )
        from notary_kg.business_case_type_runtime import BusinessCaseTypeCatalog
    except ImportError:
        return []

    fixture_dir = root / FIXTURE_ROOT
    expected_names = {
        "clean-ready.fixture.json",
        "all-classes-blocked.fixture.json",
        "process-present.fixture.json",
        "process-not-provisioned.fixture.json",
        "paging-drift.invalid.json",
        "replay-blocked.fixture.json",
        "quarantine-retry.fixture.json",
        "quarantine-divergent.fixture.json",
    }
    actual_names = {path.name for path in fixture_dir.glob("*.json")} if fixture_dir.is_dir() else set()
    if actual_names != expected_names:
        errors.append(f"fixture inventory mismatch: expected {sorted(expected_names)}, got {sorted(actual_names)}")
        return errors

    catalog = BusinessCaseTypeCatalog.from_repo(root)
    known = frozenset(entry.business_case_type_id for entry in catalog.entries)
    try:
        mapping = validate_mapping_table(mapping_doc, known)
    except MigrationValidationError as exc:
        return [f"domain mapping validation failed: {exc}"]

    loaded: dict[str, Mapping[str, object]] = {}
    plans: dict[str, Mapping[str, object]] = {}
    for path in sorted(fixture_dir.glob("*.json")):
        try:
            fixture = _load(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: invalid JSON/canonical type: {exc}")
            continue
        boundary_errors = _walk_fixture_boundary(fixture)
        errors.extend(f"{path.name}: {error}" for error in boundary_errors)
        if path.name == "paging-drift.invalid.json":
            try:
                validate_bundle(fixture)
            except MigrationValidationError:
                continue
            errors.append("paging-drift.invalid.json: page drift unexpectedly validates")
            continue
        try:
            records = validate_bundle(fixture)
            classified = classify_records(records, mapping, known)
        except MigrationValidationError as exc:
            errors.append(f"{path.name}: completed domain API rejected fixture: {exc}")
            continue
        loaded[path.name] = fixture
        counts = Counter(item.classification for item in classified)
        normalized = {name: counts.get(name, 0) for name in CLASSES}
        if path.name == "all-classes-blocked.fixture.json":
            if normalized != {name: 1 for name in CLASSES}:
                errors.append(f"{path.name}: expected all seven classes once, got {normalized}")
        elif path.name.startswith("quarantine-"):
            if normalized != {name: (1 if name == "conflict" else 0) for name in CLASSES}:
                errors.append(f"{path.name}: expected one conflict, got {normalized}")
        elif normalized != {name: (1 if name == "already_canonical" else 0) for name in CLASSES}:
            errors.append(f"{path.name}: expected one already_canonical row, got {normalized}")

        for index, scan in enumerate(fixture["scans"]):
            rebuilt = build_scan(
                scan_id=scan["scan_id"],
                scanned_at=scan["scanned_at"],
                writes_frozen=scan["writes_frozen"],
                complete=scan["complete"],
                pages_complete=scan["pages_complete"],
                matter_pages=scan["matter_pages"],
            )
            if rebuilt != scan:
                errors.append(f"{path.name}: scan {index + 1} hash/shape drift")
        replay = run_migration_replay(
            candidate_registry=candidates,
            scenarios=fixture["replay_scenarios"],
            canonical_business_case_type_ids=known,
            port=LocalMigrationReplayPort(),
        )
        expected_replay = "BLOCKED" if path.name == "replay-blocked.fixture.json" else "PASSED"
        if replay["status"] != expected_replay:
            errors.append(f"{path.name}: expected replay {expected_replay}, got {replay['status']}")
        readiness = evaluate_cutover_readiness(
            classification_counts=normalized,
            scans=fixture["scans"],
            manifest_registry_snapshot_hash=canonical_json_hash(fixture["registry_snapshot"]),
            current_registry_snapshot=fixture["post_scan_registry_snapshot"],
            manifest_process_snapshot_hash=canonical_json_hash(fixture["process_snapshot"]),
            current_process_snapshot=fixture["post_scan_process_snapshot"],
            replay_result=replay,
        )
        expected_status = "READY" if path.name in {
            "clean-ready.fixture.json", "process-present.fixture.json", "process-not-provisioned.fixture.json"
        } else "BLOCKED"
        if readiness['status'] != expected_status:
            errors.append(f"{path.name}: expected readiness {expected_status}, got {readiness['status']}")
        plan = build_backfill_plan(classified, manifest_hash="a" * 64, observed_at=fixture["observed_at"])
        plans[path.name] = plan

    retry = plans.get("quarantine-retry.fixture.json", {}).get("quarantine", [])
    divergent = plans.get("quarantine-divergent.fixture.json", {}).get("quarantine", [])
    if len(retry) != 1 or len(divergent) != 1:
        errors.append("quarantine fixtures must each produce one persistent record")
    elif retry[0].get("record_id") != divergent[0].get("record_id"):
        errors.append("quarantine divergent evidence must retain the same content-addressed identity")
    elif canonical_bytes(retry[0]) == canonical_bytes(divergent[0]):
        errors.append("quarantine divergent fixture must produce divergent bytes under the same identity")
    return errors


def validate_repository(root: Path = ROOT) -> list[str]:
    try:
        mapping_doc = _load(root / MAPPING_PATH)
        candidates = _load(root / CANDIDATES_PATH)
        domain = _load(root / DOMAIN_CONTRACT_PATH)
        verification = _load(root / VERIFICATION_CONTRACT_PATH)
        agent_context = _load(root / AGENT_CONTEXT_PATH)
        decisions = _load(root / DECISION_INDEX_PATH)
        invariants = _load(root / INVARIANT_INDEX_PATH)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"required migration artifact unavailable or invalid: {exc}"]
    errors = validate_mapping(mapping_doc)
    errors.extend(validate_candidates(candidates))
    errors.extend(validate_contracts(domain, verification))
    errors.extend(validate_agent_indexes(agent_context, decisions, invariants))
    if root.resolve() == ROOT.resolve() and str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    errors.extend(validate_domain_fixtures(root, mapping_doc, candidates))
    return errors

def main() -> int:
    errors = validate_repository()
    print(json.dumps({"status": "PASSED" if not errors else "FAILED", "errors": errors}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
