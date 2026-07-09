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

from notary_kg.first_wave_outline import (  # noqa: E402
    build_first_wave_bpmn_outline,
    validate_first_wave_bpmn_outline,
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
    payload = build_first_wave_bpmn_outline(REPO_ROOT)
    validation = validate_first_wave_bpmn_outline(payload)
    errors.extend(validation.errors)

    expected = {
        "online-gmbh-gruendung",
        "immobilienkaufvertrag",
        "handelsregisteranmeldung",
        "vorsorgevollmacht-patientenverfuegung",
    }
    actual = {outline.get("slug") for outline in payload.get("outlines", [])}
    if actual != expected:
        errors.append(f"unexpected first-wave outline slugs: {sorted(actual)}")
    for outline in payload.get("outlines", []):
        slug = outline.get("slug", "<missing>")
        if outline.get("projection_plan", {}).get("writes_sharepoint") is not False:
            errors.append(f"{slug}: projection plan must not write SharePoint")
        if outline.get("bpmn_outline", {}).get("process_id") == "":
            errors.append(f"{slug}: process id missing")
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

    summary = payload["summary"]
    print("STATUS: PASSED")
    print(
        "OK: First-wave BPMN outline contract binds existing BPMN and usecase-local KG sources "
        "without live Graph or SharePoint writes."
    )
    print(
        "OUTLINE: "
        f"{summary['first_wave_count']} cases, "
        f"{summary['total_bpmn_flow_nodes']} BPMN flow nodes, "
        f"{summary['total_required_information_nodes']} required-information nodes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
