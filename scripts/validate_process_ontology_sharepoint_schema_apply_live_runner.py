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

from notary_kg.process_ontology_schema_apply_live_runner import (  # noqa: E402
    SCHEMA_VERSION,
    build_process_ontology_sharepoint_schema_apply_live_runner,
    validate_process_ontology_sharepoint_schema_apply_live_runner,
    write_process_ontology_sharepoint_schema_apply_live_runner,
)
from notary_kg.process_ontology_schema_apply_runner_dry_run import (  # noqa: E402
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate,
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
    blocked_payload = build_process_ontology_sharepoint_schema_apply_live_runner(
        REPO_ROOT,
        live_readiness_gate=Path("missing-live-readiness-gate.redacted.json"),
        ensure_default_artifacts=False,
    )
    blocked_validation = validate_process_ontology_sharepoint_schema_apply_live_runner(blocked_payload)
    errors.extend(blocked_validation.errors)
    if blocked_payload.get("status") != "BLOCKED":
        errors.append("live runner must block without owner gate")
    if "missing --owner-approved" not in blocked_payload.get("owner_gate", {}).get("missing_or_blocking", []):
        errors.append("live runner must explain missing owner approval")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        artifact_root = temp_root / "artifacts"
        artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
        artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
        gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
        gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
        runner_json = temp_root / "process-ontology-schema-apply-live.redacted.json"
        runner_md = temp_root / "process-ontology-schema-apply-live.redacted.md"
        write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            REPO_ROOT,
            artifact_json,
            artifact_md,
        )
        write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
            REPO_ROOT,
            artifact_root,
            gate_json,
            gate_md,
            workspace_ids=["notary_team_01"],
        )
        payload = write_process_ontology_sharepoint_schema_apply_live_runner(
            REPO_ROOT,
            artifact_root,
            runner_json,
            runner_md,
            live_readiness_gate=gate_json,
            workspace_id="notary_team_01",
            correlation_id="nac-schema-apply-live-runner-validator",
            owner_approval_reference="owner-approval-live-runner-validator",
            reason="Validate bound live runner",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            ensure_default_artifacts=False,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_live_runner(payload)
        errors.extend(validation.errors)

        if payload.get("schema_version") != SCHEMA_VERSION:
            errors.append("unexpected live runner schema version")
        if payload.get("status") != "READY_FOR_GRAPH_REST_DISPATCH":
            errors.append("live runner must become ready for Graph REST dispatch after the owner gate")
        if payload.get("summary", {}).get("runner_step_count") != 34:
            errors.append("live runner must expose 34 notary_team_01 runner steps")
        if payload.get("summary", {}).get("executes_graph_requests") is not False:
            errors.append("live runner validator must keep Graph execution false in this slice")
        if payload.get("summary", {}).get("writes_sharepoint") is not False:
            errors.append("live runner validator must keep SharePoint writes false in this slice")
        if not runner_json.is_file():
            errors.append("JSON live runner artifact was not written")
        if not runner_md.is_file():
            errors.append("Markdown live runner artifact was not written")

        json_payload = json.loads(runner_json.read_text(encoding="utf-8"))
        if json_payload != payload:
            errors.append("JSON live runner artifact must match returned payload")

        combined = runner_json.read_text(encoding="utf-8") + "\n" + runner_md.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in combined.lower():
                errors.append(f"live runner artifact must not contain marker: {marker}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("process ontology SharePoint schema apply live runner validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
