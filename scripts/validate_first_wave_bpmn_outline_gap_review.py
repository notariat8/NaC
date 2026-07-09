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

from notary_kg.first_wave_gap_review import (  # noqa: E402
    build_first_wave_bpmn_outline_gap_review,
    validate_first_wave_bpmn_outline_gap_review,
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
    payload = build_first_wave_bpmn_outline_gap_review(REPO_ROOT)
    validation = validate_first_wave_bpmn_outline_gap_review(payload)
    errors.extend(validation.errors)

    expected = {
        "online-gmbh-gruendung",
        "immobilienkaufvertrag",
        "handelsregisteranmeldung",
        "vorsorgevollmacht-patientenverfuegung",
    }
    actual = {item.get("slug") for item in payload.get("review_items", [])}
    if actual != expected:
        errors.append(f"unexpected first-wave review slugs: {sorted(actual)}")
    summary = payload.get("summary", {})
    if summary.get("sharepoint_field_gap_count", 0) < 4:
        errors.append("expected SharePoint field gap plans for all first-wave cases")
    if summary.get("bpmn_gap_count", 0) < 3:
        errors.append("expected BPMN gap plans for first-wave cases")
    if summary.get("ontology_patch_count") != 12:
        errors.append("expected three ontology projection patch plans per first-wave case")

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
        "OK: First-wave BPMN outline gap review produces offline SharePoint, BPMN and "
        "ontology projection plans without live Graph or SharePoint writes."
    )
    print(
        "GAPS: "
        f"{summary['first_wave_count']} cases, "
        f"{summary['sharepoint_field_gap_count']} SharePoint field gaps, "
        f"{summary['bpmn_gap_count']} BPMN gaps, "
        f"{summary['ontology_patch_count']} ontology patches"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
