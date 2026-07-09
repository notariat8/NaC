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

from notary_kg.first_wave_process_deep_model import (  # noqa: E402
    build_first_wave_process_deep_model,
    validate_first_wave_process_deep_model,
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
    payload = build_first_wave_process_deep_model(REPO_ROOT)
    validation = validate_first_wave_process_deep_model(payload)
    errors.extend(validation.errors)

    expected = {
        "online-gmbh-gruendung",
        "immobilienkaufvertrag",
        "handelsregisteranmeldung",
        "vorsorgevollmacht-patientenverfuegung",
    }
    actual = {item.get("slug") for item in payload.get("case_models", [])}
    if actual != expected:
        errors.append(f"unexpected first-wave deep model slugs: {sorted(actual)}")

    summary = payload.get("summary", {})
    if summary.get("phase_template_count") != 32:
        errors.append("expected 32 phase templates across four first-wave cases")
    if summary.get("bpmn_flow_node_binding_count", 0) < 40:
        errors.append("expected BPMN flow-node bindings from existing first-wave models")
    if summary.get("sharepoint_projection_count") < 20:
        errors.append("expected SharePoint projection bindings for required MVP lists")

    for case_model in payload.get("case_models", []):
        slug = case_model.get("slug", "<missing>")
        if case_model.get("sharepoint_projection_plan", {}).get("rest_only") is not True:
            errors.append(f"{slug}: SharePoint projection must be Graph REST only")
        if case_model.get("sharepoint_projection_plan", {}).get("writes_sharepoint") is not False:
            errors.append(f"{slug}: SharePoint projection must not write")
        if case_model.get("bpmn_binding_plan", {}).get("mutates_bpmn_source") is not False:
            errors.append(f"{slug}: BPMN binding must not mutate source")
        if len(case_model.get("phase_plan", [])) != 8:
            errors.append(f"{slug}: expected eight canonical phase templates")

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
        "OK: First-wave process deep model binds phases, roles, BPMN nodes, evidence and "
        "SharePoint projections without live Graph or SharePoint writes."
    )
    print(
        "MODEL: "
        f"{summary['first_wave_count']} cases, "
        f"{summary['phase_template_count']} phases, "
        f"{summary['bpmn_flow_node_binding_count']} BPMN bindings, "
        f"{summary['open_gap_count']} carried-forward gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
