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

from notary_kg.process_ontology_contract import (  # noqa: E402
    CONTRACT_RELATIVE_PATH,
    build_process_ontology_contract,
    validate_process_ontology_contract,
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
    payload = build_process_ontology_contract(REPO_ROOT)
    validation = validate_process_ontology_contract(payload)
    errors.extend(validation.errors)

    contract = payload.get("contract", {})
    scope = contract.get("scope", {})
    graph = contract.get("graph_boundary", {})
    source = contract.get("source_of_truth", {})
    agent_boundary = contract.get("agent_runtime_boundary", {})
    sizing = contract.get("sizing_policy", {})
    evaluation = payload.get("evaluation", {})
    summary = evaluation.get("summary", {})
    derived = evaluation.get("derived_decision", {})

    if scope.get("offline_contract_only") is not True:
        errors.append("process ontology contract must remain offline-only")
    if scope.get("executes_graph_requests_now") is not False:
        errors.append("process ontology contract must not execute Graph requests")
    if scope.get("writes_sharepoint_now") is not False:
        errors.append("process ontology contract must not write SharePoint")
    if scope.get("changes_sharepoint_schema_now") is not False:
        errors.append("process ontology contract must not change SharePoint schema")
    if source.get("runtime_store") != "sharepoint_metadata_lists_and_document_pointers":
        errors.append("runtime store must be SharePoint metadata lists and document pointers")
    if graph.get("m365_data_plane") != "microsoft_graph_rest_v1":
        errors.append("M365 data plane must be Microsoft Graph REST v1")
    if graph.get("sdk_allowed") is not False or graph.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("Graph SDK and legacy SharePoint APIs must remain blocked")
    if agent_boundary.get("agentic_toolkit") != "nvidia_nemo_agent_toolkit":
        errors.append("agentic toolkit boundary must remain NVIDIA NeMo Agent Toolkit")
    if agent_boundary.get("bulk_content_memory_allowed") is not False:
        errors.append("bulk Office content in agent memory must remain blocked")
    if sizing.get("all_business_cases_must_be_included") is not True:
        errors.append("all business cases must be included in sizing")
    if summary.get("business_case_count", 0) < summary.get("canonical_required", 0):
        errors.append("business-case count is below canonical threshold")
    if summary.get("case_contract_index_count") != summary.get("business_case_count"):
        errors.append("case contract index must cover every business case")
    if derived.get("ontology_is_product_model_contract") is not True:
        errors.append("ontology must be the product-model contract")
    if derived.get("runtime_reasoning_on_request_path_allowed") is not False:
        errors.append("runtime ontology reasoning must remain off the request path")
    if derived.get("live_apply_required_now") is not False:
        errors.append("contract must not require live apply now")

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
        "OK: Notarial process ontology contract binds all business cases to a "
        "SharePoint MVP projection and keeps ontology/BPMN off the runtime request path."
    )
    print(
        "SIZING: "
        f"{summary['business_case_count']} business cases, "
        f"{summary['entity_class_count']} entity classes, "
        f"{summary['relationship_template_count']} relationship templates, "
        f"{summary['process_phase_count']} process phases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
