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

from notary_kg.deep_process_routing import (  # noqa: E402
    build_deep_process_candidate_routing,
    validate_deep_process_candidate_routing,
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
    payload = build_deep_process_candidate_routing(REPO_ROOT)
    validation = validate_deep_process_candidate_routing(payload)
    errors.extend(validation.errors)

    summary = payload.get("summary", {})
    if summary.get("candidate_count", 0) < summary.get("first_wave_count", 0):
        errors.append("candidate_count must be at least first_wave_count")
    if payload.get("routing_policy", {}).get("deep_modeling_required_for_all_candidates") is not False:
        errors.append("deep modeling must not be required for all candidates")
    if payload.get("guardrails", {}).get("writes_sharepoint") is not False:
        errors.append("routing must not write SharePoint")
    if payload.get("guardrails", {}).get("executes_graph_requests") is not False:
        errors.append("routing must not execute Graph requests")

    routes = {route.get("slug"): route for route in payload.get("routes", [])}
    for slug in ("online-gmbh-gruendung", "immobilienkaufvertrag", "handelsregisteranmeldung"):
        if routes.get(slug, {}).get("routing_lane") != "first_wave_deep_process":
            errors.append(f"{slug} must be routed to first_wave_deep_process")
    if routes.get("grundstueckskaufvertrag", {}).get("routing_lane") != "legacy_alias_dedupe":
        errors.append("grundstueckskaufvertrag must be routed to legacy_alias_dedupe")

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
        "OK: Deep-process candidate routing classifies high/medium notarial cases "
        "without live Graph or SharePoint writes."
    )
    print(
        "ROUTING: "
        f"{summary['candidate_count']} candidates, "
        f"{summary['first_wave_count']} first-wave cases, "
        f"lanes={summary['lane_counts']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
