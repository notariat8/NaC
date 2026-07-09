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

from notary_kg.ontology_scale_budget import (  # noqa: E402
    build_ontology_scale_budget_smoke,
    validate_ontology_scale_budget_smoke,
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
    payload = build_ontology_scale_budget_smoke(REPO_ROOT)
    validation = validate_ontology_scale_budget_smoke(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    thresholds = payload.get("thresholds", {})
    if summary.get("business_case_count", 0) < 20:
        errors.append("scale budget must include at least the canonical Top-10 and Next-10 cases")
    if summary.get("bpmn_source_count") != summary.get("business_case_count"):
        errors.append("all inventory cases must have BPMN sources before scale budget can pass")
    if summary.get("max_projection_entities_estimate", 0) > thresholds.get(
        "max_projection_entities_per_business_case",
        0,
    ):
        errors.append("max projection entity estimate exceeds threshold")
    if summary.get("max_projection_edges_estimate", 0) > thresholds.get("max_projection_edges_per_business_case", 0):
        errors.append("max projection edge estimate exceeds threshold")
    for item in payload.get("budget_cases", []):
        if item.get("projection_entities_pressure") == "over_budget":
            errors.append(f"{item.get('slug', '<missing>')}: projection entity pressure over budget")
        if item.get("projection_edges_pressure") == "over_budget":
            errors.append(f"{item.get('slug', '<missing>')}: projection edge pressure over budget")

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
        "OK: Notarial ontology scale budget covers the full business-case inventory "
        "without requiring a runtime ontology store or live M365 actions."
    )
    print(
        "BUDGET: "
        f"{summary['business_case_count']} cases, "
        f"{summary['bpmn_source_count']} BPMN sources, "
        f"{summary['total_projection_entities_estimate']} projection entities, "
        f"{summary['total_projection_edges_estimate']} projection edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
