from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import build_business_case_inventory
from .ontology_storage_contract import CONTRACT_RELATIVE_PATH


SCHEMA_VERSION = "nac.notarial-ontology-scale-budget/v0.1"
FLOW_NODE_TAGS = {
    "startEvent",
    "endEvent",
    "userTask",
    "manualTask",
    "serviceTask",
    "businessRuleTask",
    "sendTask",
    "exclusiveGateway",
    "parallelGateway",
}


@dataclass(frozen=True, slots=True)
class OntologyScaleBudgetValidation:
    status: str
    errors: tuple[str, ...]


def build_ontology_scale_budget_smoke(repo_root: Path) -> dict[str, Any]:
    contract = json.loads((repo_root / CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8"))
    inventory = build_business_case_inventory(repo_root)
    thresholds = contract["sizing_thresholds"]
    cases = [_case_budget(repo_root, item, thresholds) for item in inventory["business_cases"]]
    total_projection_entities = sum(item["projection_entities_estimate"] for item in cases)
    total_projection_edges = sum(item["projection_edges_estimate"] for item in cases)
    total_bpmn_flow_nodes = sum(item["bpmn_flow_nodes"] for item in cases)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "mode": "offline_scale_budget_smoke",
        "source": {
            "business_case_inventory_schema": inventory["schema_version"],
            "business_case_inventory_status": inventory["status"],
            "ontology_storage_contract": str(CONTRACT_RELATIVE_PATH),
            "central_knowledge_graph_folder_allowed": False,
            "usecase_local_knowledge_graphs_remain_authoritative": True,
        },
        "thresholds": {
            "max_supported_business_cases_without_store_migration": thresholds[
                "max_supported_business_cases_without_store_migration"
            ],
            "max_projection_entities_per_business_case": thresholds["max_projection_entities_per_business_case"],
            "max_projection_edges_per_business_case": thresholds["max_projection_edges_per_business_case"],
            "max_runtime_graph_reads_per_user_action": thresholds["max_runtime_graph_reads_per_user_action"],
            "max_runtime_sharepoint_lists_per_user_action": thresholds["max_runtime_sharepoint_lists_per_user_action"],
        },
        "summary": {
            "business_case_count": len(cases),
            "canonical_covered_count": inventory["summary"]["canonical_covered_count"],
            "canonical_target_count": inventory["summary"]["canonical_target_count"],
            "bpmn_source_count": sum(1 for item in cases if item["bpmn_exists"]),
            "total_bpmn_flow_nodes": total_bpmn_flow_nodes,
            "total_projection_entities_estimate": total_projection_entities,
            "total_projection_edges_estimate": total_projection_edges,
            "max_projection_entities_estimate": max(
                (item["projection_entities_estimate"] for item in cases),
                default=0,
            ),
            "max_projection_edges_estimate": max((item["projection_edges_estimate"] for item in cases), default=0),
            "max_runtime_graph_reads_per_user_action_estimate": 2,
            "max_runtime_sharepoint_lists_per_user_action_estimate": 2,
            "pressure_cases": [
                item["slug"]
                for item in cases
                if item["projection_entities_pressure"] in {"high", "at_budget"}
                or item["projection_edges_pressure"] in {"high", "at_budget"}
            ],
        },
        "budget_cases": cases,
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "runtime_ontology_reasoning_on_request_path_allowed": False,
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
        },
        "next_batch": {
            "recommended_slice": "first_wave_bpmn_outline_gap_review",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "matter_payload_storage",
                "runtime_ontology_store_migration",
            ],
        },
        "errors": [],
    }
    validation = validate_ontology_scale_budget_smoke(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_ontology_scale_budget_smoke(payload: dict[str, Any]) -> OntologyScaleBudgetValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("mode") != "offline_scale_budget_smoke":
        errors.append("scale budget smoke must remain offline")
    source = payload.get("source", {})
    if source.get("business_case_inventory_status") != "PASSED":
        errors.append("business-case inventory must pass before scale budget smoke")
    if source.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")
    if source.get("usecase_local_knowledge_graphs_remain_authoritative") is not True:
        errors.append("usecase-local knowledge graphs must remain authoritative")

    thresholds = payload.get("thresholds", {})
    summary = payload.get("summary", {})
    if summary.get("business_case_count", 0) > thresholds.get("max_supported_business_cases_without_store_migration", 0):
        errors.append("business-case count exceeds no-migration threshold")
    if summary.get("canonical_covered_count") != summary.get("canonical_target_count"):
        errors.append("canonical business cases are not fully covered")
    if summary.get("max_projection_entities_estimate", 0) > thresholds.get("max_projection_entities_per_business_case", 0):
        errors.append("projection entity estimate exceeds per-case threshold")
    if summary.get("max_projection_edges_estimate", 0) > thresholds.get("max_projection_edges_per_business_case", 0):
        errors.append("projection edge estimate exceeds per-case threshold")
    if summary.get("max_runtime_graph_reads_per_user_action_estimate", 0) > thresholds.get(
        "max_runtime_graph_reads_per_user_action",
        0,
    ):
        errors.append("runtime Graph read estimate exceeds request-path threshold")
    if summary.get("max_runtime_sharepoint_lists_per_user_action_estimate", 0) > thresholds.get(
        "max_runtime_sharepoint_lists_per_user_action",
        0,
    ):
        errors.append("runtime SharePoint list estimate exceeds request-path threshold")

    for item in payload.get("budget_cases", []):
        slug = item.get("slug", "<missing>")
        if not item.get("bpmn_exists"):
            errors.append(f"{slug}: BPMN source missing")
        if item.get("projection_entities_estimate", 0) > thresholds.get("max_projection_entities_per_business_case", 0):
            errors.append(f"{slug}: projection entities exceed threshold")
        if item.get("projection_edges_estimate", 0) > thresholds.get("max_projection_edges_per_business_case", 0):
            errors.append(f"{slug}: projection edges exceed threshold")
        boundaries = item.get("runtime_boundaries", {})
        if boundaries.get("ontology_runtime_reasoning_required") is not False:
            errors.append(f"{slug}: ontology runtime reasoning must not be required")
        if boundaries.get("document_full_text_in_ontology") is not False:
            errors.append(f"{slug}: document full text must not enter ontology")
        if boundaries.get("matter_values_in_repo") is not False:
            errors.append(f"{slug}: matter values must not enter repo")

    guardrails = payload.get("guardrails", {})
    for key in (
        "offline_only",
        "sharepoint_remains_mvp_store",
        "ontology_remains_projection_contract",
    ):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in (
        "executes_graph_requests",
        "writes_sharepoint",
        "changes_sharepoint_schema",
        "stores_matter_instance_values",
        "stores_document_full_text",
        "stores_tokens_or_secrets",
        "runtime_ontology_reasoning_on_request_path_allowed",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return OntologyScaleBudgetValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _case_budget(repo_root: Path, entry: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    sizing = entry["sizing"]
    projection_entities = (
        1
        + sizing["required_information_nodes"]
        + sizing["document_types"]
        + sizing["decision_points"]
        + sizing["gates"]
        + sizing["evidence_points"]
        + sizing["plugin_dependencies"]
        + sizing["workflow_dependencies"]
    )
    projection_edges = (
        sizing["required_information_nodes"]
        + sizing["document_types"]
        + sizing["decision_points"] * 2
        + sizing["gates"] * 2
        + sizing["evidence_points"]
        + sizing["plugin_dependencies"]
        + sizing["workflow_dependencies"]
    )
    bpmn_path = _bpmn_path(repo_root, entry["slug"])
    bpmn_flow_nodes = _bpmn_flow_node_count(bpmn_path) if bpmn_path.is_file() else 0
    return {
        "slug": entry["slug"],
        "domain": entry["domain"],
        "inventory_scope": entry["inventory_scope"],
        "implementation_depth": entry["implementation_depth"],
        "projection_entities_estimate": projection_entities,
        "projection_edges_estimate": projection_edges,
        "projection_entities_pressure": _pressure(
            projection_entities,
            int(thresholds["max_projection_entities_per_business_case"]),
        ),
        "projection_edges_pressure": _pressure(
            projection_edges,
            int(thresholds["max_projection_edges_per_business_case"]),
        ),
        "bpmn": str(bpmn_path.relative_to(repo_root)),
        "bpmn_exists": bpmn_path.is_file(),
        "bpmn_flow_nodes": bpmn_flow_nodes,
        "complexity_score": sizing["complexity_score"],
        "complexity_band": sizing["complexity_band"],
        "runtime_boundaries": entry["runtime_boundaries"],
    }


def _bpmn_path(repo_root: Path, slug: str) -> Path:
    canonical = repo_root / "bpmn" / f"{slug}.bpmn"
    if canonical.is_file():
        return canonical
    return repo_root / "bpmn" / "usecases" / f"{slug}.bpmn"


def _bpmn_flow_node_count(path: Path) -> int:
    root = ET.parse(path).getroot()
    process = next(child for child in root if _local_name(child.tag) == "process")
    return sum(1 for child in process if _local_name(child.tag) in FLOW_NODE_TAGS)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _pressure(value: int, threshold: int) -> str:
    if value > threshold:
        return "over_budget"
    if value == threshold:
        return "at_budget"
    if value >= int(threshold * 0.8):
        return "high"
    return "normal"
