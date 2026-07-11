from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from notary_kg.process_ontology_schema_gap import (  # noqa: E402
    build_process_ontology_sharepoint_schema_gap,
    validate_process_ontology_sharepoint_schema_gap,
)


PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "raw_mandate",
    "mandatsdaten",
}


def main() -> int:
    errors: list[str] = []
    payload = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)
    validation = validate_process_ontology_sharepoint_schema_gap(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    if summary.get("missing_required_list_count") != 0:
        errors.append("current MVP schema must still contain all required lists")
    if summary.get("field_gap_count", 0) < 10:
        errors.append("expected concrete process-instance field gaps")
    if summary.get("choice_gap_count", 0) < 1:
        errors.append("expected process ontology choice gaps")
    if summary.get("required_projection_gap_count") != 1:
        errors.append("expected the required Vorgangsartenregister projection gap")
    if summary.get("optional_projection_gap_count", 0) < 2:
        errors.append("expected Prozessregister and BPMN Models optional projection gaps")
    if summary.get("blocking_shape_mismatch_count") != 0:
        errors.append("existing schema fields must match complete expected shapes")
    if payload.get("legacy_column_contract", {}).get("matches_pinned_baseline") is not True:
        errors.append("legacy Akten.Vorgangstyp must match the independent pinned baseline")
    if payload.get("apply_boundary", {}).get("owner_gate_required_before_apply") is not True:
        errors.append("future schema apply must remain owner-gated")
    if payload.get("guardrails", {}).get("offline_only") is not True:
        errors.append("gap review must be offline-only")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if payload.get("guardrails", {}).get(key) is not False:
            errors.append(f"guardrail must keep {key} false")

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = serialized.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"prohibited marker found: {marker}")

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print(
        "OK: Process ontology to SharePoint schema gap review is plan-only and "
        "surfaces concrete process-instance list/field gaps."
    )
    print(
        "GAPS: "
        f"{summary['field_gap_count']} fields, "
        f"{summary['choice_gap_count']} choice plans, "
        f"{summary['optional_projection_gap_count']} optional projections"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
