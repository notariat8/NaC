#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
src_text = str(SRC)
if src_text in sys.path:
    sys.path.remove(src_text)
sys.path.insert(0, src_text)

from notary_kg.process_ontology_schema_apply_owner_gated_live_plan import (  # noqa: E402
    SCHEMA_VERSION,
    validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
    write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
)
from notary_kg.process_ontology_schema_apply_runner_dry_run import (  # noqa: E402
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
)


FORBIDDEN_MARKERS = (
    "client_secret",
    "private_key",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "raw_mandate",
    "mandatsdaten",
    "authorization",
    "bearer ",
    "funktion8.sharepoint.com",
    "\"headers\"",
)


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        artifact_root = temp_root / "artifacts"
        artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
        artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
        plan_json = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.json"
        plan_md = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.md"
        write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            REPO_ROOT,
            artifact_json,
            artifact_md,
        )
        payload = write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
            REPO_ROOT,
            artifact_root,
            plan_json,
            plan_md,
            ensure_default_artifacts=False,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(payload)
        errors.extend(validation.errors)

        if payload.get("schema_version") != SCHEMA_VERSION:
            errors.append("unexpected owner-gated live plan schema version")
        if payload.get("status") != "BLOCKED":
            errors.append("owner-gated live plan must be blocked pending S6/S7 approval")
        if payload.get("summary", {}).get("planned_live_step_count") != 66:
            errors.append("owner-gated live plan must cover 66 planned live steps")
        if payload.get("summary", {}).get("owner_gate_required_now") is not False:
            errors.append("owner-gated live plan must not solicit approval before S6/S7")
        if not plan_json.is_file():
            errors.append("JSON owner-gated live plan was not written")
        if not plan_md.is_file():
            errors.append("Markdown owner-gated live plan was not written")

        json_payload = json.loads(plan_json.read_text(encoding="utf-8"))
        if json_payload != payload:
            errors.append("JSON owner-gated live plan must match returned payload")

        combined = plan_json.read_text(encoding="utf-8") + "\n" + plan_md.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in combined.lower():
                errors.append(f"owner-gated live plan must not contain marker: {marker}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("process ontology SharePoint schema apply owner-gated live plan validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
