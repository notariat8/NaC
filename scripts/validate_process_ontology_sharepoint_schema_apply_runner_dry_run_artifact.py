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
    ARTIFACT_SCHEMA_VERSION,
    validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
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
        json_path = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
        markdown_path = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
        payload = write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            REPO_ROOT,
            json_path,
            markdown_path,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(payload)
        errors.extend(validation.errors)

        if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
            errors.append("unexpected artifact schema version")
        if payload.get("status") != "PASSED":
            errors.append("artifact status must pass")
        if not json_path.is_file():
            errors.append("JSON artifact was not written")
        if not markdown_path.is_file():
            errors.append("Markdown artifact was not written")

        json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        if json_payload != payload:
            errors.append("JSON artifact must match returned payload")

        combined = json_path.read_text(encoding="utf-8") + "\n" + markdown_path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in combined.lower():
                errors.append(f"artifact must not contain marker: {marker}")

        if payload.get("summary", {}).get("dry_run_step_count") != 66:
            errors.append("artifact must include all 66 required-only dry-run steps")
        if len(payload.get("dry_run_step_index", [])) != 66:
            errors.append("artifact dry-run step index must include 66 entries")
        for attachment in payload.get("evidence_attachments", []):
            if attachment.get("required_for_live_apply_readiness") is not True:
                errors.append("artifact evidence must be required for live apply readiness")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("process ontology SharePoint schema apply runner dry-run artifact validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
