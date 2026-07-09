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
    ARTIFACT_INDEX_SCHEMA_VERSION,
    validate_process_ontology_sharepoint_schema_apply_artifact_index,
    write_process_ontology_sharepoint_schema_apply_artifact_index,
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
        index_json = temp_root / "process-ontology-schema-apply-artifact-index.redacted.json"
        index_md = temp_root / "process-ontology-schema-apply-artifact-index.redacted.md"
        write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
            REPO_ROOT,
            artifact_json,
            artifact_md,
        )
        payload = write_process_ontology_sharepoint_schema_apply_artifact_index(
            REPO_ROOT,
            artifact_root,
            index_json,
            index_md,
            ensure_default_artifact=False,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_artifact_index(payload)
        errors.extend(validation.errors)

        if payload.get("schema_version") != ARTIFACT_INDEX_SCHEMA_VERSION:
            errors.append("unexpected artifact index schema version")
        if payload.get("status") != "PASSED":
            errors.append("artifact index status must pass")
        if payload.get("summary", {}).get("artifact_count") != 1:
            errors.append("artifact index must include one synthetic artifact")
        if payload.get("summary", {}).get("total_dry_run_step_count") != 68:
            errors.append("artifact index must carry the dry-run step total")
        if not index_json.is_file():
            errors.append("JSON artifact index was not written")
        if not index_md.is_file():
            errors.append("Markdown artifact index was not written")

        json_payload = json.loads(index_json.read_text(encoding="utf-8"))
        if json_payload != payload:
            errors.append("JSON artifact index must match returned payload")

        combined = index_json.read_text(encoding="utf-8") + "\n" + index_md.read_text(encoding="utf-8")
        for marker in FORBIDDEN_MARKERS:
            if marker.lower() in combined.lower():
                errors.append(f"artifact index must not contain marker: {marker}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("process ontology SharePoint schema apply artifact index validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
