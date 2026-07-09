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

from notary_kg.process_ontology_schema_apply_execution_contract import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_execution_contract,
    validate_process_ontology_sharepoint_schema_apply_execution_contract,
)


PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "raw_mandate",
    "mandatsdaten",
    "authorization",
    "bearer ",
}


def main() -> int:
    errors: list[str] = []
    payload = build_process_ontology_sharepoint_schema_apply_execution_contract(REPO_ROOT)
    validation = validate_process_ontology_sharepoint_schema_apply_execution_contract(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    if summary.get("workspace_count") != 2:
        errors.append("expected two notary workspaces")
    if summary.get("workspace_apply_unit_count") != 68:
        errors.append("expected 68 workspace apply units")
    if summary.get("execution_phase_count") != 8:
        errors.append("expected eight execution phases")
    if payload.get("execution_boundary", {}).get("future_runner_must_require_explicit_live_flag") is not True:
        errors.append("future runner must require an explicit live flag")
    if payload.get("stop_rules", {}).get("automatic_rollback_allowed") is not False:
        errors.append("automatic rollback must remain disabled")
    if payload.get("evidence_contract", {}).get("redacted_evidence_required") is not True:
        errors.append("redacted evidence must be required")

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
        "OK: Process ontology SharePoint schema apply execution contract is "
        "owner-gated, Graph REST only and offline."
    )
    print(
        "CONTRACT: "
        f"{summary['workspace_count']} workspaces, "
        f"{summary['workspace_apply_unit_count']} units, "
        f"{summary['execution_phase_count']} phases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
