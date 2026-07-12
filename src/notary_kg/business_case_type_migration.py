from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Mapping, Protocol, Sequence

from .business_case_inventory import CANONICAL_SLUGS


Classification = Literal[
    "already_canonical",
    "mappable",
    "conflict",
    "unknown",
    "missing",
    "etag_skipped",
    "unresolved",
]

CLASSIFICATIONS: tuple[Classification, ...] = (
    "already_canonical",
    "mappable",
    "conflict",
    "unknown",
    "missing",
    "etag_skipped",
    "unresolved",
)
BLOCKER_CLASSIFICATIONS = frozenset(
    {"conflict", "unknown", "missing", "etag_skipped", "unresolved"}
)
FROZEN_LEGACY_CHOICES = frozenset(
    {
        "immobilienkaufvertrag",
        "unterschriftsbeglaubigung",
        "online-gmbh-gruendung",
        "handelsregisteranmeldung",
    }
)
ROW_KEYS = frozenset(
    {
        "record_ref",
        "snapshot_etag",
        "current_etag",
        "legacy_choice",
        "business_case_type_id",
        "read_status",
    }
)
PAGE_KEYS = frozenset({"page_number", "page_count", "complete", "rows"})
SCAN_KEYS = frozenset(
    {
        "scan_id",
        "scanned_at",
        "writes_frozen",
        "complete",
        "pages_complete",
        "record_count",
        "scan_hash",
        "matter_pages",
    }
)
MAX_PAGES = 1_000
PAGE_SIZE = 100
MAX_RECORDS = 100_000
RECOVERY_STATUS = "BLOCKED_PENDING_S6_S7_APPROVAL"
REPLAY_SCENARIOS = (
    "read-vorgangstyp-id",
    "ignore-additive-registry-fields",
    "unknown-id-fail-closed",
    "new-type-without-legacy-read-only",
)

_RECORD_REF = re.compile(r"synref-[a-z0-9-]+\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_UTC_SECONDS = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_SYNTHETIC_ETAG = re.compile(r"synthetic-etag-(?=[a-z0-9-]{1,64}\Z)[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_SYNTHETIC_APPROVAL = re.compile(r"synthetic-approval-[a-z0-9-]+\Z")
_SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_BPMN_LINK = re.compile(r"models/[a-z0-9]+(?:-[a-z0-9]+)*\.bpmn\Z")
BINDING_KEYS = frozenset(
    {
        "site_hash",
        "schema_hash",
        "matter_list_hash",
        "registry_list_hash",
        "process_list_hash",
    }
)


class MigrationValidationError(ValueError):
    """Raised when an S5 input cannot be evaluated without guessing."""


@dataclass(frozen=True, slots=True)
class ClassifiedRecord:
    record_ref: str
    record_ref_hash: str
    classification: Classification
    target_business_case_type_id: str | None
    current_etag: str | None


class MigrationReplayPort(Protocol):
    def replay(
        self,
        *,
        candidate: Mapping[str, Any],
        scenario_id: str,
        scenario: Mapping[str, Any],
        known_business_case_type_ids: frozenset[str],
    ) -> Mapping[str, Any]: ...


def canonical_json_bytes(value: Any) -> bytes:
    _validate_json_value(value, path="$", seen=set())
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def canonical_json_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def text_hash(value: str) -> str:
    if type(value) is not str:
        raise MigrationValidationError("hash input must be a string")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def baseline_fingerprint() -> str:
    return canonical_json_hash(sorted(FROZEN_LEGACY_CHOICES))


def validate_mapping_table(
    mapping_table: Mapping[str, Any],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str],
) -> dict[str, str]:
    _require_exact_keys(
        mapping_table,
        {"schema_version", "mapping_id", "mapping_version", "typed_namespaces", "normalization_allowed", "mappings"},
        "mapping table",
    )
    _require_nonempty_string(mapping_table["schema_version"], "mapping table schema_version")
    _require_nonempty_string(mapping_table["mapping_id"], "mapping table mapping_id")
    _require_nonempty_string(mapping_table["mapping_version"], "mapping table mapping_version")
    if mapping_table["typed_namespaces"] != {"source": "LegacyChoice", "target": "BusinessCaseTypeId"}:
        raise MigrationValidationError("mapping typed namespaces are invalid")
    if mapping_table["normalization_allowed"] is not False:
        raise MigrationValidationError("mapping normalization must remain disabled")

    known_ids = _validate_identifier_set(canonical_business_case_type_ids)
    raw_entries = mapping_table["mappings"]
    if type(raw_entries) is not list or len(raw_entries) != len(FROZEN_LEGACY_CHOICES):
        raise MigrationValidationError("mapping table must contain exactly four mappings")

    result: dict[str, str] = {}
    for index, entry in enumerate(raw_entries):
        _require_exact_keys(entry, {"source", "target"}, f"mapping {index}")
        source = _require_nonempty_string(entry["source"], f"mapping {index} source")
        target = _require_nonempty_string(entry["target"], f"mapping {index} target")
        if source in result:
            raise MigrationValidationError(f"duplicate mapping source: {source}")
        if target not in known_ids:
            raise MigrationValidationError(f"mapping target is not canonical: {target}")
        result[source] = target
    if frozenset(result) != FROZEN_LEGACY_CHOICES:
        raise MigrationValidationError("mapping sources must exactly equal the frozen four-choice baseline")
    return result


def validate_pages(pages: Any) -> tuple[dict[str, Any], ...]:
    if type(pages) is not list or not pages or len(pages) > MAX_PAGES:
        raise MigrationValidationError("matter pages must contain between 1 and 1000 pages")
    expected_count = len(pages)
    records: list[dict[str, Any]] = []
    seen_refs: set[str] = set()
    for index, page in enumerate(pages, start=1):
        _require_exact_keys(page, PAGE_KEYS, f"page {index}")
        if type(page["page_number"]) is not int or page["page_number"] != index:
            raise MigrationValidationError("page_number must start at 1 and be contiguous")
        if type(page["page_count"]) is not int or page["page_count"] != expected_count:
            raise MigrationValidationError("page_count must equal the complete page count on every page")
        if type(page["complete"]) is not bool or page["complete"] is not (index == expected_count):
            raise MigrationValidationError("only the final page may be complete")
        rows = page["rows"]
        if type(rows) is not list or len(rows) > PAGE_SIZE:
            raise MigrationValidationError("each page must contain at most 100 rows")
        for row_index, row in enumerate(rows):
            _validate_row_shape(row, f"page {index} row {row_index}")
            _validate_synthetic_row_etags(row, f"page {index} row {row_index}")
            record_ref = row["record_ref"]
            if record_ref in seen_refs:
                raise MigrationValidationError(f"duplicate record_ref: {record_ref}")
            seen_refs.add(record_ref)
            records.append(dict(row))
    if len(records) > MAX_RECORDS:
        raise MigrationValidationError("bundle exceeds 100000 records")
    return tuple(records)


def validate_bundle(
    bundle: Mapping[str, Any],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str] = frozenset(CANONICAL_SLUGS),
) -> tuple[dict[str, Any], ...]:
    required = {
        "schema_version",
        "data_classification",
        "contains_production_data",
        "observed_at",
        "catalog_version",
        "matter_pages",
        "registry_snapshot",
        "process_snapshot",
        "post_scan_observed_at",
        "post_scan_registry_snapshot",
        "post_scan_process_snapshot",
        "scans",
        "replay_scenarios",
        "bindings",
        "role_approval_refs",
    }
    _require_exact_keys(bundle, required, "bundle")
    _require_nonempty_string(bundle["schema_version"], "bundle schema_version")
    _require_nonempty_string(bundle["catalog_version"], "bundle catalog_version")
    if bundle["data_classification"] != "synthetic" or bundle["contains_production_data"] is not False:
        raise MigrationValidationError("bundle must contain synthetic data only")
    _parse_utc_seconds(bundle["observed_at"], "observed_at")
    for key in (
        "registry_snapshot",
        "process_snapshot",
        "post_scan_registry_snapshot",
        "post_scan_process_snapshot",
        "bindings",
    ):
        if type(bundle[key]) is not dict:
            raise MigrationValidationError(f"{key} must be an object")
    if type(bundle["scans"]) is not list or len(bundle["scans"]) != 2:
        raise MigrationValidationError("bundle must contain exactly two final scans")
    if type(bundle["replay_scenarios"]) is not dict:
        raise MigrationValidationError("replay_scenarios must be an object")
    if frozenset(bundle["replay_scenarios"]) != frozenset(REPLAY_SCENARIOS):
        raise MigrationValidationError("bundle must contain exactly the four replay scenarios")
    _validate_bindings(bundle["bindings"])
    _validate_approval_refs(bundle["role_approval_refs"])
    validate_registry_catalog_coverage(
        bundle["registry_snapshot"], canonical_business_case_type_ids
    )
    _validate_process_snapshot(bundle["process_snapshot"])
    validate_registry_catalog_coverage(
        bundle["post_scan_registry_snapshot"], canonical_business_case_type_ids
    )
    _validate_process_snapshot(bundle["post_scan_process_snapshot"])
    _validate_json_value(bundle, path="$", seen=set())
    records = validate_pages(bundle["matter_pages"])
    validated_scans = [
        _validate_scan(supplied_scan, f"scan {index}")
        for index, supplied_scan in enumerate(bundle["scans"], start=1)
    ]
    if _canonical_matter_pages(bundle["matter_pages"]) != validated_scans[1]["matter_pages"]:
        raise MigrationValidationError(
            "top-level matter_pages must canonically equal the second final scan"
        )
    post_scan_time = _parse_utc_seconds(bundle["post_scan_observed_at"], "post_scan_observed_at")
    scan_two_time = _parse_utc_seconds(bundle["scans"][1]["scanned_at"], "second scan time")
    if post_scan_time <= scan_two_time:
        raise MigrationValidationError("post-scan snapshots must be captured strictly after scan two")
    return records


def classify_record(
    row: Mapping[str, Any],
    mapping: Mapping[str, str],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str],
) -> ClassifiedRecord:
    _validate_row_shape(row, "record")
    known_ids = _validate_identifier_set(canonical_business_case_type_ids)
    legacy = row["legacy_choice"]
    canonical = row["business_case_type_id"]
    current_etag = row["current_etag"]

    if row["read_status"] != "complete" or not _business_value_valid(legacy) or not _business_value_valid(canonical):
        classification: Classification = "unresolved"
    elif not _valid_etag(row["snapshot_etag"]) or not _valid_etag(current_etag) or row["snapshot_etag"] != current_etag:
        classification = "etag_skipped"
    elif legacy is None and canonical is None:
        classification = "missing"
    elif legacy is not None and canonical is not None:
        classification = (
            "already_canonical"
            if canonical in known_ids and mapping.get(legacy) == canonical
            else "conflict"
        )
    elif canonical is not None:
        classification = "already_canonical" if canonical in known_ids else "unknown"
    else:
        classification = "mappable" if legacy in mapping else "unknown"

    target = mapping.get(legacy) if classification == "mappable" else None
    return ClassifiedRecord(
        record_ref=row["record_ref"],
        record_ref_hash=text_hash(row["record_ref"]),
        classification=classification,
        target_business_case_type_id=target,
        current_etag=current_etag if type(current_etag) is str else None,
    )


def classify_records(
    records: Sequence[Mapping[str, Any]],
    mapping: Mapping[str, str],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str],
) -> tuple[ClassifiedRecord, ...]:
    seen: set[str] = set()
    classified: list[ClassifiedRecord] = []
    for row in records:
        item = classify_record(row, mapping, canonical_business_case_type_ids)
        if item.record_ref in seen:
            raise MigrationValidationError(f"duplicate record_ref: {item.record_ref}")
        seen.add(item.record_ref)
        classified.append(item)
    return tuple(classified)


def build_manifest(
    *,
    repository_commit: str,
    catalog_version: str,
    mapping_table: Mapping[str, Any],
    matter_pages: Sequence[Mapping[str, Any]],
    registry_snapshot: Mapping[str, Any],
    process_snapshot: Mapping[str, Any],
    bindings: Mapping[str, Any],
    role_approval_refs: Sequence[str],
    schema_version: str,
    runtime_version: str,
    contract_version_n: str,
    candidate_n_minus_1: str,
    runtime_candidate_registry: Mapping[str, Any],
    final_scans: Sequence[Mapping[str, Any]],
    post_scan_observed_at: str,
    post_scan_registry_snapshot: Mapping[str, Any],
    post_scan_process_snapshot: Mapping[str, Any],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str],
) -> dict[str, Any]:
    for name, value in {
        "repository_commit": repository_commit,
        "catalog_version": catalog_version,
        "schema_version": schema_version,
        "runtime_version": runtime_version,
        "contract_version_n": contract_version_n,
        "candidate_n_minus_1": candidate_n_minus_1,
    }.items():
        _require_nonempty_string(value, name)
    records = validate_pages(list(matter_pages))
    registry = validate_registry_catalog_coverage(
        registry_snapshot, canonical_business_case_type_ids
    )
    process = _validate_process_snapshot(process_snapshot)
    if type(final_scans) not in {list, tuple} or len(final_scans) != 2:
        raise MigrationValidationError("manifest must bind exactly two final scans")
    validated_scans = [
        _validate_scan(scan, f"final scan {index}")
        for index, scan in enumerate(final_scans, start=1)
    ]
    if _canonical_matter_pages(matter_pages) != validated_scans[1]["matter_pages"]:
        raise MigrationValidationError(
            "manifest matter_pages must canonically equal the second final scan"
        )
    post_scan_time = _parse_utc_seconds(post_scan_observed_at, "post_scan_observed_at")
    scan_two_time = _parse_utc_seconds(validated_scans[1]["scanned_at"], "second scan time")
    if post_scan_time <= scan_two_time:
        raise MigrationValidationError("post-scan snapshots must be captured strictly after scan two")
    post_registry = validate_registry_catalog_coverage(
        post_scan_registry_snapshot, canonical_business_case_type_ids
    )
    post_process = _validate_process_snapshot(post_scan_process_snapshot)

    canonical_pages = _canonical_matter_pages(matter_pages)
    validated_bindings = _validate_bindings(bindings)
    refs = _validate_approval_refs(role_approval_refs)
    payload = {
        "repository_commit": repository_commit,
        "catalog_version": catalog_version,
        "mapping_version": mapping_table.get("mapping_version"),
        "mapping_baseline_fingerprint": baseline_fingerprint(),
        "schema_version": schema_version,
        "runtime_version": runtime_version,
        "contract_version_n": contract_version_n,
        "candidate_n_minus_1": candidate_n_minus_1,
        "bindings_hash": canonical_json_hash(validated_bindings),
        "matter_snapshot": {"row_count": len(records), "hash": canonical_json_hash(canonical_pages)},
        "registry_snapshot_hash": canonical_json_hash(registry),
        "process_snapshot_hash": canonical_json_hash(process),
        "final_scans_hash": canonical_json_hash(validated_scans),
        "final_scans": [
            {
                "scan_id": scan["scan_id"],
                "scanned_at": scan["scanned_at"],
                "record_count": scan["record_count"],
                "scan_hash": scan["scan_hash"],
                "matter_pages_hash": canonical_json_hash(scan["matter_pages"]),
            }
            for scan in validated_scans
        ],
        "post_scan_observed_at": post_scan_observed_at,
        "post_scan_registry_snapshot_hash": canonical_json_hash(post_registry),
        "post_scan_process_snapshot_hash": canonical_json_hash(post_process),
        "mapping_hash": canonical_json_hash(mapping_table),
        "runtime_candidate_registry_hash": canonical_json_hash(runtime_candidate_registry),
        "role_approval_ref_hashes": sorted(text_hash(ref) for ref in refs),
    }
    return {**payload, "manifest_hash": canonical_json_hash(payload)}


def build_readiness_evidence_anchor(
    *,
    base_manifest_hash: str,
    backfill_plan: Mapping[str, Any],
    replay_scenarios: Mapping[str, Any],
    profile_evaluation_result: Mapping[str, Any],
    reconciled_quarantine_index: Mapping[str, Any],
) -> dict[str, str]:
    _require_sha256(base_manifest_hash, "base_manifest_hash")
    payload = {
        "base_manifest_hash": base_manifest_hash,
        "backfill_plan_hash": canonical_json_hash(backfill_plan),
        "replay_scenarios_hash": canonical_json_hash(replay_scenarios),
        "profile_evaluation_result_hash": canonical_json_hash(profile_evaluation_result),
        "reconciled_quarantine_index_hash": canonical_json_hash(
            reconciled_quarantine_index
        ),
    }
    return {**payload, "readiness_evidence_hash": canonical_json_hash(payload)}


def build_backfill_plan(
    classified_records: Sequence[ClassifiedRecord],
    *,
    manifest_hash: str,
    observed_at: str,
) -> dict[str, Any]:
    _require_sha256(manifest_hash, "manifest_hash")
    _parse_utc_seconds(observed_at, "observed_at")
    counts = {name: 0 for name in CLASSIFICATIONS}
    operations: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in classified_records:
        if item.record_ref_hash in seen:
            raise MigrationValidationError("duplicate classified record")
        seen.add(item.record_ref_hash)
        counts[item.classification] += 1
        if item.classification == "mappable":
            if item.target_business_case_type_id is None or not _valid_etag(item.current_etag):
                raise MigrationValidationError("mappable record lacks target or current ETag")
            identity = [manifest_hash, item.record_ref_hash, item.target_business_case_type_id, item.current_etag]
            operations.append(
                {
                    "record_ref_hash": item.record_ref_hash,
                    "field": "VorgangstypId",
                    "value": item.target_business_case_type_id,
                    "if_match": item.current_etag,
                    "idempotency_key": canonical_json_hash(identity),
                }
            )
        elif item.classification in BLOCKER_CLASSIFICATIONS:
            current_etag = item.current_etag or ""
            quarantine.append(
                {
                    "record_id": canonical_json_hash(
                        [manifest_hash, item.record_ref_hash, item.classification, current_etag]
                    ),
                    "record_ref_hash": item.record_ref_hash,
                    "classification": item.classification,
                    "current_etag": current_etag,
                    "manifest_hash": manifest_hash,
                    "observed_at": observed_at,
                }
            )
    operations.sort(key=lambda value: value["record_ref_hash"])
    quarantine.sort(key=lambda value: value["record_id"])
    pages: list[dict[str, Any]] = []
    for offset in range(0, len(operations), PAGE_SIZE):
        page_operations = operations[offset : offset + PAGE_SIZE]
        page_number = len(pages) + 1
        page_hash = canonical_json_hash(page_operations)
        pages.append(
            {
                "page_number": page_number,
                "operation_count": len(page_operations),
                "page_hash": page_hash,
                "operations": page_operations,
            }
        )
    return {
        "manifest_hash": manifest_hash,
        "operation_count": len(operations),
        "page_size": PAGE_SIZE,
        "page_count": len(pages),
        "page_hashes": [page["page_hash"] for page in pages],
        "pages": pages,
        "classification_counts": counts,
        "quarantine": quarantine,
    }


def build_scan(
    *,
    scan_id: str,
    scanned_at: str,
    writes_frozen: bool,
    complete: bool,
    pages_complete: bool,
    matter_pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    _require_nonempty_string(scan_id, "scan_id")
    _parse_utc_seconds(scanned_at, "scanned_at")
    if type(writes_frozen) is not bool or type(complete) is not bool or type(pages_complete) is not bool:
        raise MigrationValidationError("scan flags must be booleans")
    pages = _canonical_matter_pages(matter_pages)
    rows = validate_pages(pages)
    return {
        "scan_id": scan_id,
        "scanned_at": scanned_at,
        "writes_frozen": writes_frozen,
        "complete": complete,
        "pages_complete": pages_complete,
        "record_count": len(rows),
        "scan_hash": canonical_json_hash(pages),
        "matter_pages": pages,
    }


def evaluate_cutover_readiness(
    *,
    classification_counts: Mapping[str, Any],
    scans: Sequence[Mapping[str, Any]],
    manifest_registry_snapshot_hash: str,
    current_registry_snapshot: Mapping[str, Any],
    manifest_process_snapshot_hash: str,
    current_process_snapshot: Mapping[str, Any],
    replay_result: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []
    if set(classification_counts) != set(CLASSIFICATIONS) or any(
        type(classification_counts.get(name)) is not int or classification_counts[name] < 0
        for name in CLASSIFICATIONS
    ):
        raise MigrationValidationError("classification_counts must exactly cover all seven classes")
    if any(classification_counts[name] for name in CLASSIFICATIONS if name != "already_canonical"):
        reasons.extend(name for name in CLASSIFICATIONS if name != "already_canonical" and classification_counts[name])
    if len(scans) != 2 or not _stable_scans(scans[0], scans[1]):
        reasons.append("scan_unstable")
    if canonical_json_hash(_sorted_snapshot(current_registry_snapshot, "business_case_type_id")) != manifest_registry_snapshot_hash:
        reasons.append("scan_unstable")
    if canonical_json_hash(_validate_process_snapshot(current_process_snapshot)) != manifest_process_snapshot_hash:
        reasons.append("scan_unstable")
    if replay_result.get("status") != "PASSED":
        reasons.append("profile_evaluation_failed")
    reasons = list(dict.fromkeys(reasons))
    return {
        "status": "READY" if not reasons else "BLOCKED",
        "reason_codes": reasons,
        "requires_two_new_complete_scans": bool(reasons),
    }


class LocalMigrationReplayPort:
    """Interprets pinned local profiles; it never loads or executes candidates."""

    def replay(
        self,
        *,
        candidate: Mapping[str, Any],
        scenario_id: str,
        scenario: Mapping[str, Any],
        known_business_case_type_ids: frozenset[str],
    ) -> Mapping[str, Any]:
        profile = candidate["profile"]
        row = scenario.get("registry_row")
        if type(row) is not dict:
            return {"decision": "BLOCKED", "reason_code": "scenario_invalid"}
        value = row.get("VorgangstypId")
        known = type(value) is str and value in known_business_case_type_ids
        if scenario_id == "read-vorgangstyp-id":
            passed = profile.get("canonical_field") == "VorgangstypId" and profile.get("reads_canonical_id") is True and known
            reason = "canonical_id_read" if passed else "canonical_id_not_read"
        elif scenario_id == "ignore-additive-registry-fields":
            passed = profile.get("ignores_additive_registry_fields") is True and known
            reason = "additive_fields_ignored" if passed else "additive_fields_rejected"
        elif scenario_id == "unknown-id-fail-closed":
            passed = not known and profile.get("unknown_id_decision") == "BLOCKED" and profile.get("unknown_id_reason_code") == "unknown_business_case_type_id"
            reason = "unknown_id_blocked" if passed else "unknown_id_accepted"
        elif scenario_id == "new-type-without-legacy-read-only":
            passed = known and row.get("legacy_choice") is None and profile.get("new_type_without_legacy_decision") == "READ_ONLY" and profile.get("legacy_choice_required_for_display") is False
            reason = "new_type_read_only" if passed else "new_type_not_read_only"
        else:
            raise MigrationValidationError(f"unknown replay scenario: {scenario_id}")
        return {"decision": "PASSED" if passed else "BLOCKED", "reason_code": reason}


def run_migration_replay(
    *,
    candidate_registry: Mapping[str, Any],
    scenarios: Mapping[str, Mapping[str, Any]],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str],
    port: MigrationReplayPort,
) -> dict[str, Any]:
    _require_exact_keys(candidate_registry, {"schema_version", "registry_id", "registry_version", "scenarios_exact", "candidates"}, "candidate registry")
    if candidate_registry["scenarios_exact"] != list(REPLAY_SCENARIOS):
        raise MigrationValidationError("candidate registry scenarios do not match the fixed replay set")
    if frozenset(scenarios) != frozenset(REPLAY_SCENARIOS):
        raise MigrationValidationError("replay must contain exactly four scenarios")
    candidates = candidate_registry["candidates"]
    if type(candidates) is not list or len(candidates) != 2:
        raise MigrationValidationError("candidate registry must pin exactly N and N-1")
    known_ids = _validate_identifier_set(canonical_business_case_type_ids)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    all_passed = True
    for index, candidate in enumerate(candidates):
        _require_exact_keys(
            candidate,
            {"candidate_id", "contract_version", "profile", "profile_sha256"},
            f"candidate {index}",
        )
        candidate_id = _require_nonempty_string(candidate["candidate_id"], f"candidate {index} ID")
        _require_nonempty_string(candidate["contract_version"], f"candidate {index} contract version")
        if candidate_id in seen:
            raise MigrationValidationError("candidate IDs must be unique")
        seen.add(candidate_id)
        generation = "N" if index == 0 else "N-1"
        profile_matches = canonical_json_hash(candidate["profile"]) == candidate["profile_sha256"]
        checks: list[dict[str, Any]] = []
        for scenario_id in REPLAY_SCENARIOS:
            decision = dict(
                port.replay(
                    candidate=candidate,
                    scenario_id=scenario_id,
                    scenario=scenarios[scenario_id],
                    known_business_case_type_ids=known_ids,
                )
            )
            if set(decision) != {"decision", "reason_code"}:
                raise MigrationValidationError("replay port must return decision and reason_code")
            passed = profile_matches and decision["decision"] == "PASSED"
            all_passed = all_passed and passed
            checks.append({"scenario_id": scenario_id, **decision, "passed": passed})
        results.append(
            {
                "candidate_id": candidate_id,
                "generation": generation,
                "contract_version": candidate["contract_version"],
                "profile_hash_matches": profile_matches,
                "checks": checks,
            }
        )
    return {"status": "PASSED" if all_passed else "BLOCKED", "candidates": results}


def build_rollback_plan(*, manifest_hash: str, candidate_n_minus_1: str) -> dict[str, Any]:
    _require_sha256(manifest_hash, "manifest_hash")
    _require_nonempty_string(candidate_n_minus_1, "candidate_n_minus_1")
    actions = [
        "stop_mutating_workflows",
        "preserve_intent_snapshots_etags_and_quarantine_for_s6",
        "disable_canonical_write_and_invalidate_caches",
        "require_executable_validation_before_switching_to_n_minus_1",
        "conditionally_restore_projections_with_manifest_etags",
        "readback_rescan_and_reopen_only_unambiguous_legacy_writes",
    ]
    return {
        "status": RECOVERY_STATUS,
        "manifest_hash": manifest_hash,
        "candidate_n_minus_1": candidate_n_minus_1,
        "steps": [{"step_number": index, "action": action} for index, action in enumerate(actions, 1)],
        "executes_actions": False,
        "deletes_columns": False,
        "deletes_canonical_values": False,
    }


def build_forward_recovery_plan(*, manifest_hash: str, candidate_n: str) -> dict[str, Any]:
    _require_sha256(manifest_hash, "manifest_hash")
    _require_nonempty_string(candidate_n, "candidate_n")
    actions = [
        "redeploy_tested_n_candidate",
        "reload_catalog_registry_and_process_registry",
        "require_immutable_s6_outbox_and_plan_idempotent_replay",
        "require_resolution_of_all_quarantine_cases",
        "run_two_new_stable_complete_scans",
        "request_s7_live_approval",
    ]
    return {
        "status": RECOVERY_STATUS,
        "manifest_hash": manifest_hash,
        "candidate_n": candidate_n,
        "steps": [{"step_number": index, "action": action} for index, action in enumerate(actions, 1)],
        "executes_actions": False,
        "creates_legacy_substitute_values": False,
        "requires_s6_outbox": True,
        "requires_s7_approval": True,
    }


def _validate_json_value(value: Any, *, path: str, seen: set[int]) -> None:
    if value is None or type(value) in {bool, int, str}:
        return
    if type(value) is float:
        raise MigrationValidationError(f"{path}: floats are forbidden")
    if type(value) not in {list, dict}:
        raise MigrationValidationError(f"{path}: value is not canonical JSON")
    identity = id(value)
    if identity in seen:
        raise MigrationValidationError(f"{path}: cyclic JSON value")
    seen.add(identity)
    if type(value) is list:
        for index, item in enumerate(value):
            _validate_json_value(item, path=f"{path}[{index}]", seen=seen)
    else:
        for key, item in value.items():
            if type(key) is not str:
                raise MigrationValidationError(f"{path}: object keys must be strings")
            _validate_json_value(item, path=f"{path}.{key}", seen=seen)
    seen.remove(identity)


def _require_exact_keys(value: Any, keys: set[str] | frozenset[str], label: str) -> None:
    if type(value) is not dict or set(value) != set(keys):
        raise MigrationValidationError(f"{label} must contain exactly: {', '.join(sorted(keys))}")


def _require_nonempty_string(value: Any, label: str) -> str:
    if type(value) is not str or not value or not value.strip():
        raise MigrationValidationError(f"{label} must be a non-empty string")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise MigrationValidationError(f"{label} must be a lowercase SHA-256 hash")
    return value


def _validate_identifier_set(values: Sequence[str] | frozenset[str]) -> frozenset[str]:
    if type(values) not in {list, tuple, frozenset, set}:
        raise MigrationValidationError("canonical IDs must be a sequence")
    if not values or any(type(value) is not str or not value or not value.strip() for value in values):
        raise MigrationValidationError("canonical IDs must be non-empty strings")
    result = frozenset(values)
    if len(result) != len(values):
        raise MigrationValidationError("canonical IDs must be unique")
    return result


def _validate_row_shape(row: Any, label: str) -> None:
    _require_exact_keys(row, ROW_KEYS, label)
    if type(row["record_ref"]) is not str or _RECORD_REF.fullmatch(row["record_ref"]) is None:
        raise MigrationValidationError(f"{label} record_ref is invalid")
    if type(row["read_status"]) is not str:
        raise MigrationValidationError(f"{label} read_status must be a string")


def _business_value_valid(value: Any) -> bool:
    return value is None or (type(value) is str and bool(value) and bool(value.strip()))


def _valid_etag(value: Any) -> bool:
    return type(value) is str and bool(value) and bool(value.strip())


def _parse_utc_seconds(value: Any, label: str) -> datetime:
    if type(value) is not str or _UTC_SECONDS.fullmatch(value) is None:
        raise MigrationValidationError(f"{label} must be RFC-3339 UTC at whole-second precision")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise MigrationValidationError(f"{label} is not a valid UTC timestamp") from exc
    return parsed


def _canonical_matter_pages(pages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "page_number": page["page_number"],
            "page_count": page["page_count"],
            "complete": page["complete"],
            "rows": sorted((dict(row) for row in page["rows"]), key=lambda row: row["record_ref"]),
        }
        for page in pages
    ]


def _sorted_snapshot(snapshot: Mapping[str, Any], technical_key: str) -> dict[str, Any]:
    _require_exact_keys(snapshot, {"status", "complete", "rows"}, "registry snapshot")
    if snapshot["status"] != "present" or snapshot["complete"] is not True:
        raise MigrationValidationError("registry snapshot must be present and complete")
    rows = snapshot["rows"]
    if type(rows) is not list or not rows:
        raise MigrationValidationError("present snapshot rows must be a non-empty list")
    row_keys = (
        {"business_case_type_id", "etag", "selectable"}
        if technical_key == "business_case_type_id"
        else {"process_id", "etag", "bpmn_link"}
    )
    copied: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        _require_exact_keys(row, row_keys, f"snapshot row {index}")
        key = _require_nonempty_string(row[technical_key], f"snapshot {technical_key}")
        if _SLUG.fullmatch(key) is None:
            raise MigrationValidationError(f"snapshot {technical_key} must be a lowercase slug")
        _require_synthetic_etag(row["etag"], "snapshot etag")
        if technical_key == "business_case_type_id" and type(row["selectable"]) is not bool:
            raise MigrationValidationError("registry snapshot selectable must be a boolean")
        if key in seen:
            raise MigrationValidationError("duplicate snapshot technical key")
        seen.add(key)
        copied.append(dict(row))
    return {"status": "present", "complete": True, "rows": sorted(copied, key=lambda row: row[technical_key])}


def validate_registry_catalog_coverage(
    snapshot: Mapping[str, Any],
    canonical_business_case_type_ids: Sequence[str] | frozenset[str],
) -> dict[str, Any]:
    known_ids = _validate_identifier_set(canonical_business_case_type_ids)
    normalized = _sorted_snapshot(snapshot, "business_case_type_id")
    observed_ids = frozenset(row["business_case_type_id"] for row in normalized["rows"])
    if observed_ids != known_ids:
        raise MigrationValidationError(
            "registry snapshot must exactly cover the canonical BusinessCaseTypeId catalog"
        )
    return normalized


def _validate_process_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if type(snapshot) is not dict or snapshot.get("status") not in {"present", "not_provisioned"}:
        raise MigrationValidationError("process snapshot status must be present or not_provisioned")
    if snapshot["status"] == "not_provisioned":
        _require_exact_keys(snapshot, {"status"}, "not-provisioned process snapshot")
        return {"status": "not_provisioned"}
    result = _sorted_snapshot(snapshot, "process_id")
    for row in result["rows"]:
        if row["bpmn_link"] is not None and (
            type(row["bpmn_link"]) is not str or _BPMN_LINK.fullmatch(row["bpmn_link"]) is None
        ):
            raise MigrationValidationError("process snapshot bpmn_link must be null or models/<slug>.bpmn")
    return result


def _require_synthetic_etag(value: Any, label: str) -> str:
    if type(value) is not str or _SYNTHETIC_ETAG.fullmatch(value) is None:
        raise MigrationValidationError(
            f"{label} must match synthetic-etag-[a-z0-9-] with a 1-64 character suffix"
        )
    return value


def _validate_synthetic_row_etags(row: Mapping[str, Any], label: str) -> None:
    _require_synthetic_etag(row["snapshot_etag"], f"{label} snapshot_etag")
    _require_synthetic_etag(row["current_etag"], f"{label} current_etag")


def _validate_scan(scan: Any, label: str) -> dict[str, Any]:
    _require_exact_keys(scan, SCAN_KEYS, label)
    if type(scan["record_count"]) is not int:
        raise MigrationValidationError(f"{label} record_count must be an integer")
    if type(scan["matter_pages"]) is not list:
        raise MigrationValidationError(f"{label} matter_pages must be a list")
    try:
        rebuilt = build_scan(
            scan_id=scan["scan_id"],
            scanned_at=scan["scanned_at"],
            writes_frozen=scan["writes_frozen"],
            complete=scan["complete"],
            pages_complete=scan["pages_complete"],
            matter_pages=scan["matter_pages"],
        )
    except (KeyError, TypeError) as exc:
        raise MigrationValidationError(f"{label} has an invalid shape") from exc
    if scan != rebuilt:
        raise MigrationValidationError(
            f"{label} summary does not match its independently captured matter pages"
        )
    return rebuilt


def _validate_bindings(bindings: Any) -> dict[str, str]:
    _require_exact_keys(bindings, BINDING_KEYS, "bindings")
    return {key: _require_sha256(bindings[key], f"bindings {key}") for key in sorted(BINDING_KEYS)}


def _validate_approval_refs(refs: Any) -> list[str]:
    if type(refs) is not list or not refs:
        raise MigrationValidationError("role approval references must be a non-empty list")
    if any(type(ref) is not str or _SYNTHETIC_APPROVAL.fullmatch(ref) is None for ref in refs):
        raise MigrationValidationError("role approval references must match synthetic-approval-[a-z0-9-]+")
    if len(set(refs)) != len(refs):
        raise MigrationValidationError("role approval references must be unique")
    return list(refs)


def _stable_scans(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    required = SCAN_KEYS
    if type(first) is not dict or type(second) is not dict or set(first) != required or set(second) != required:
        return False
    try:
        first_time = _parse_utc_seconds(first["scanned_at"], "first scan time")
        second_time = _parse_utc_seconds(second["scanned_at"], "second scan time")
    except MigrationValidationError:
        return False
    return (
        type(first["scan_id"]) is str
        and type(second["scan_id"]) is str
        and bool(first["scan_id"])
        and bool(second["scan_id"])
        and first["scan_id"] != second["scan_id"]
        and first["complete"] is True
        and second["complete"] is True
        and first["pages_complete"] is True
        and second["pages_complete"] is True
        and first["writes_frozen"] is True
        and second["writes_frozen"] is True
        and (second_time - first_time).total_seconds() >= 900
        and type(first["record_count"]) is int
        and type(second["record_count"]) is int
        and first["record_count"] >= 0
        and first["record_count"] == second["record_count"]
        and _SHA256.fullmatch(first["scan_hash"] or "") is not None
        and first["scan_hash"] == second["scan_hash"]
    )
