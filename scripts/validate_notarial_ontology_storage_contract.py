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

from notary_kg.ontology_storage_contract import (  # noqa: E402
    CONTRACT_RELATIVE_PATH,
    build_ontology_storage_contract,
    validate_ontology_storage_contract,
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
    contract_path = REPO_ROOT / CONTRACT_RELATIVE_PATH
    if not contract_path.exists():
        errors.append(f"missing contract: {CONTRACT_RELATIVE_PATH}")
    payload = build_ontology_storage_contract(REPO_ROOT)
    validation = validate_ontology_storage_contract(payload)
    errors.extend(validation.errors)

    contract = payload.get("contract", {})
    scope = contract.get("scope", {})
    storage_roles = contract.get("storage_roles", {})
    projection_rules = contract.get("projection_rules", {})
    graph = contract.get("graph", {})
    evaluation = payload.get("evaluation", {})

    if scope.get("offline_contract_only") is not True:
        errors.append("contract must remain offline-only")
    if scope.get("executes_graph_requests_now") is not False:
        errors.append("contract must not execute Graph requests")
    if scope.get("changes_sharepoint_schema_now") is not False:
        errors.append("contract must not change SharePoint schema")
    if graph.get("rest_only") is not True:
        errors.append("Graph boundary must be REST-only")
    if graph.get("sdk_allowed") is not False:
        errors.append("Graph SDK must remain blocked")
    if graph.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")
    if storage_roles.get("sharepoint", {}).get("role") != "operative_mvp_data_store":
        errors.append("SharePoint must remain operative MVP data store")
    if storage_roles.get("ontology", {}).get("role") != "versioned_repo_catalog_and_projection_contract":
        errors.append("ontology must remain versioned repo projection contract")
    if projection_rules.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")
    if evaluation.get("derived_decision", {}).get("runtime_reasoning_on_request_path_allowed") is not False:
        errors.append("runtime ontology reasoning must remain off the request path")

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

    current = evaluation["current_sizing"]
    print("STATUS: PASSED")
    print(
        "OK: Notarial ontology storage contract keeps SharePoint as MVP store, "
        "ontology as bounded projection and Graph REST as the only M365 data plane."
    )
    print(
        "SIZING: "
        f"{current['business_case_count']} business cases, "
        f"{current['canonical_covered_count']}/{current['canonical_required']} canonical coverage, "
        f"max complexity {current['max_complexity_score']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
