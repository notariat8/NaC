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

from notary_kg.process_ontology_schema_apply_plan import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_plan,
    validate_process_ontology_sharepoint_schema_apply_plan,
)


PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "Authorization",
    "Bearer ",
    "ghp_",
    "gho_",
    "raw_mandate",
    "mandatsdaten",
}


def main() -> int:
    errors: list[str] = []
    payload = build_process_ontology_sharepoint_schema_apply_plan(REPO_ROOT)
    validation = validate_process_ontology_sharepoint_schema_apply_plan(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    if summary.get("total_step_count") != 33:
        errors.append("expected 33 required-only plan steps derived from the current schema gap review")
    if summary.get("create_column_step_count") != 29:
        errors.append("expected 29 create-column steps")
    if summary.get("extend_choice_step_count") != 3:
        errors.append("expected 3 choice-extension steps")
    if summary.get("create_list_step_count") != 1:
        errors.append("expected only the required type-register creation plan")
    if summary.get("create_document_library_step_count") != 0:
        errors.append("optional BPMN model library must stay out of the default S2 plan")
    if summary.get("excluded_optional_projection_gap_count") != 2:
        errors.append("expected two separately exposed optional projection gaps")

    legacy_targets = [
        step for step in payload.get("steps", [])
        if step.get("target") == "Akten"
        and step.get("request", {}).get("body", {}).get("name") == "Vorgangstyp"
    ]
    if legacy_targets:
        errors.append("S2 plan must not target legacy Akten.Vorgangstyp")

    operations = {step.get("operation") for step in payload.get("steps", [])}
    for operation in {"create_list", "create_column", "extend_choice_column"}:
        if operation not in operations:
            errors.append(f"missing apply-plan operation: {operation}")

    endpoints = payload.get("apply_boundary", {}).get("future_apply_endpoint_families", [])
    if "POST /sites/{site-id}/lists" not in endpoints:
        errors.append("missing list create endpoint family")
    if "POST /sites/{site-id}/lists/{list-id}/columns" not in endpoints:
        errors.append("missing column create endpoint family")
    if "PATCH /sites/{site-id}/lists/{list-id}/columns/{column-id}" not in endpoints:
        errors.append("missing column update endpoint family")

    for step in payload.get("steps", []):
        if step.get("mode") != "plan_only":
            errors.append(f"{step.get('id', '<unknown>')}: not plan_only")
        if step.get("owner_gate_required_before_apply") is not True:
            errors.append(f"{step.get('id', '<unknown>')}: missing owner gate")
        for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
            if step.get(key) is not False:
                errors.append(f"{step.get('id', '<unknown>')}: {key} must be false")
        body = step.get("request", {}).get("body", {})
        if step.get("operation") == "create_column" and "name" not in body:
            errors.append(f"{step.get('id', '<unknown>')}: create-column body missing name")
        if step.get("operation") == "extend_choice_column" and not body.get("choice", {}).get("choices"):
            errors.append(f"{step.get('id', '<unknown>')}: choice update body missing choices")

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
        "OK: Process ontology SharePoint schema apply plan is offline, Graph REST only, "
        "and owner-gated before any future apply."
    )
    print(
        "PLAN: "
        f"{summary['total_step_count']} steps "
        f"({summary['create_column_step_count']} columns, "
        f"{summary['extend_choice_step_count']} choice extensions, "
        f"{summary['create_list_step_count']} list, "
        f"{summary['create_document_library_step_count']} library)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
