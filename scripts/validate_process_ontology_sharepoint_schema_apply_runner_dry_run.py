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

from notary_kg.process_ontology_schema_apply_runner_dry_run import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_runner_dry_run,
    validate_process_ontology_sharepoint_schema_apply_runner_dry_run,
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
    payload = build_process_ontology_sharepoint_schema_apply_runner_dry_run(REPO_ROOT)
    validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    if summary.get("workspace_count") != 2:
        errors.append("expected two notary workspaces")
    if summary.get("dry_run_step_count") != 66:
        errors.append("expected 66 dry-run steps")
    if summary.get("future_mutation_request_count") != 66:
        errors.append("expected 66 future mutation request plans")
    if payload.get("evidence_plan", {}).get("raw_graph_response_allowed") is not False:
        errors.append("raw Graph responses must remain blocked")

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
    print("OK: Process ontology SharePoint schema apply runner dry-run is offline and redacted.")
    print(
        "DRY-RUN: "
        f"{summary['workspace_count']} workspaces, "
        f"{summary['dry_run_step_count']} steps, "
        f"{summary['future_mutation_request_count']} future mutation plans"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
