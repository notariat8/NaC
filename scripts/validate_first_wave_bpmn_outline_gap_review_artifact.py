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

from notary_kg.first_wave_gap_review import (  # noqa: E402
    ARTIFACT_SCHEMA_VERSION,
    validate_first_wave_bpmn_outline_gap_review_artifact,
    write_first_wave_bpmn_outline_gap_review_artifact,
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
    "planned_value",
)


def main() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        json_path = temp_root / "first-wave-gap-review.redacted.json"
        markdown_path = temp_root / "first-wave-gap-review.redacted.md"
        payload = write_first_wave_bpmn_outline_gap_review_artifact(REPO_ROOT, json_path, markdown_path)
        validation = validate_first_wave_bpmn_outline_gap_review_artifact(payload)
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

        if len(payload.get("review_index", [])) != 4:
            errors.append("artifact must include exactly four first-wave review index entries")
        for attachment in payload.get("evidence_attachments", []):
            if attachment.get("required_for_release_readiness") is not False:
                errors.append("artifact evidence must remain optional for release readiness")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("first-wave BPMN outline gap review artifact validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
