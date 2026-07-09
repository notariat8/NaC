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

from notary_kg.process_ontology_schema_apply_runner_dry_run import (  # noqa: E402
    LIVE_READINESS_GATE_SCHEMA_VERSION,
    validate_process_ontology_sharepoint_schema_apply_live_readiness_gate,
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
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        artifact_root = temp_root / "artifacts"
        artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
        artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
        gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
        gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
        write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            REPO_ROOT,
            artifact_json,
            artifact_md,
        )
        payload = write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
            REPO_ROOT,
            artifact_root,
            gate_json,
            gate_md,
            ensure_default_artifacts=False,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_live_readiness_gate(payload)
        errors.extend(validation.errors)

        if payload.get("schema_version") != LIVE_READINESS_GATE_SCHEMA_VERSION:
            errors.append("unexpected live readiness gate schema version")
        if payload.get("status") != "PASSED":
            errors.append("live readiness gate status must pass")
        if payload.get("summary", {}).get("check_count") != 6:
            errors.append("live readiness gate must include six checks")
        if payload.get("summary", {}).get("blocked_check_count") != 0:
            errors.append("live readiness gate must not include blockers")
        if payload.get("summary", {}).get("workspace_apply_unit_count") != 68:
            errors.append("live readiness gate must cover 68 apply units")
        if not gate_json.is_file():
            errors.append("JSON live readiness gate was not written")
        if not gate_md.is_file():
            errors.append("Markdown live readiness gate was not written")

        json_payload = json.loads(gate_json.read_text(encoding="utf-8"))
        if json_payload != payload:
            errors.append("JSON live readiness gate must match returned payload")

        combined = gate_json.read_text(encoding="utf-8") + "\n" + gate_md.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in combined.lower():
                errors.append(f"live readiness gate must not contain marker: {marker}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("process ontology SharePoint schema apply live readiness gate validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
