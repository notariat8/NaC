from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .deep_process_routing import build_deep_process_candidate_routing


SCHEMA_VERSION = "nac.first-wave-bpmn-outline/v0.1"
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
NAC_NS = "https://github.com/notariat8/NaC/bpmn/nac"


@dataclass(frozen=True, slots=True)
class FirstWaveOutlineValidation:
    status: str
    errors: tuple[str, ...]


def build_first_wave_bpmn_outline(repo_root: Path) -> dict[str, Any]:
    routing = build_deep_process_candidate_routing(repo_root)
    first_wave_slugs = list(routing.get("recommended_batch", []))
    outlines = [_build_case_outline(repo_root, slug, routing) for slug in first_wave_slugs]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "mode": "offline_outline_contract",
        "source": {
            "deep_process_routing_schema": routing["schema_version"],
            "deep_process_routing_status": routing["status"],
            "recommended_batch": first_wave_slugs,
            "usecase_local_knowledge_graphs_remain_authoritative": True,
            "central_knowledge_graph_folder_allowed": False,
        },
        "summary": {
            "first_wave_count": len(outlines),
            "outline_slugs": [outline["slug"] for outline in outlines],
            "total_bpmn_flow_nodes": sum(outline["bpmn_outline"]["flow_node_count"] for outline in outlines),
            "total_required_information_nodes": sum(outline["kg_outline"]["required_information_nodes"] for outline in outlines),
            "total_decision_points": sum(outline["kg_outline"]["decision_points"] for outline in outlines),
            "total_evidence_points": sum(outline["kg_outline"]["evidence_points"] for outline in outlines),
        },
        "outlines": outlines,
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
            "bpmn_remains_process_model_not_runtime_engine": True,
        },
        "next_batch": {
            "recommended_slice": "first_wave_bpmn_outline_gap_review",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "document_content_read",
                "matter_payload_storage",
            ],
        },
        "errors": [],
    }
    validation = validate_first_wave_bpmn_outline(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_first_wave_bpmn_outline(payload: dict[str, Any]) -> FirstWaveOutlineValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("mode") != "offline_outline_contract":
        errors.append("first-wave outline must remain offline")
    source = payload.get("source", {})
    if source.get("deep_process_routing_status") != "PASSED":
        errors.append("deep-process routing must pass before outline generation")
    if source.get("usecase_local_knowledge_graphs_remain_authoritative") is not True:
        errors.append("usecase-local knowledge graphs must remain authoritative")
    if source.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")

    outlines = payload.get("outlines", [])
    if len(outlines) != 4:
        errors.append("first-wave outline must include exactly four cases")
    expected = set(source.get("recommended_batch", []))
    actual = {outline.get("slug") for outline in outlines}
    if expected != actual:
        errors.append("first-wave outlines must match the routing recommended batch")
    for outline in outlines:
        slug = outline.get("slug", "<missing>")
        if not outline.get("sources", {}).get("bpmn_exists"):
            errors.append(f"{slug}: BPMN source missing")
        if not outline.get("sources", {}).get("knowledge_graph_exists"):
            errors.append(f"{slug}: KG source missing")
        if outline.get("bpmn_outline", {}).get("is_executable") is not False:
            errors.append(f"{slug}: BPMN outline must be non-executable")
        if outline.get("bpmn_outline", {}).get("flow_node_count", 0) <= 0:
            errors.append(f"{slug}: BPMN outline must expose flow nodes")
        if outline.get("kg_outline", {}).get("required_information_nodes", 0) <= 0:
            errors.append(f"{slug}: KG outline must expose required information")
        if outline.get("projection_plan", {}).get("stores_matter_values") is not False:
            errors.append(f"{slug}: projection plan must not store matter values")
        if outline.get("projection_plan", {}).get("stores_document_full_text") is not False:
            errors.append(f"{slug}: projection plan must not store document full text")

    guardrails = payload.get("guardrails", {})
    for key in (
        "offline_only",
        "sharepoint_remains_mvp_store",
        "ontology_remains_projection_contract",
        "bpmn_remains_process_model_not_runtime_engine",
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
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return FirstWaveOutlineValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _build_case_outline(repo_root: Path, slug: str, routing: dict[str, Any]) -> dict[str, Any]:
    route = next(route for route in routing["routes"] if route["slug"] == slug)
    kg_path = repo_root / "usecases" / slug / "knowledge-graph.graph.json"
    bpmn_path = _bpmn_path(repo_root, slug)
    kg_payload = json.loads(kg_path.read_text(encoding="utf-8"))
    case = _single_case(kg_payload, slug)
    bpmn_outline = _bpmn_outline(bpmn_path)
    return {
        "slug": slug,
        "title": route["title"],
        "domain": route["domain"],
        "routing": {
            "lane": route["routing_lane"],
            "reasons": route["routing_reasons"],
            "complexity_score": route["complexity_score"],
            "complexity_band": route["complexity_band"],
        },
        "sources": {
            "knowledge_graph": str(kg_path.relative_to(repo_root)),
            "knowledge_graph_exists": kg_path.is_file(),
            "bpmn": str(bpmn_path.relative_to(repo_root)),
            "bpmn_exists": bpmn_path.is_file(),
        },
        "kg_outline": {
            "case_id": str(case.get("id", "")),
            "required_information_nodes": len(_as_list(case.get("required_information"))),
            "document_types": len(_as_list(case.get("documents"))),
            "decision_points": len(_as_list(case.get("decisions"))),
            "gates": len(_as_list(case.get("gates"))),
            "evidence_points": len(_as_list(case.get("evidence"))),
            "plugin_dependencies": [str(item) for item in _as_list(case.get("plugin_dependencies"))],
            "workflow_dependencies": [str(item) for item in _as_list(case.get("workflow_dependencies"))],
        },
        "bpmn_outline": bpmn_outline,
        "projection_plan": {
            "ontology_patch_mode": "shape_only_patch_plan",
            "bpmn_binding_mode": "existing_bpmn_source_reference",
            "sharepoint_field_gap_mode": "metadata_mapping_plan_only",
            "verification_contract_mode": "offline_contract_before_apply",
            "stores_matter_values": False,
            "stores_document_full_text": False,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
        },
        "recommended_next_artifacts": [
            "bpmn_outline_gap_review",
            "ontology_projection_patch_plan",
            "sharepoint_field_gap_plan",
            "verification_contract",
        ],
    }


def _bpmn_path(repo_root: Path, slug: str) -> Path:
    canonical = repo_root / "bpmn" / f"{slug}.bpmn"
    if canonical.is_file():
        return canonical
    return repo_root / "bpmn" / "usecases" / f"{slug}.bpmn"


def _bpmn_outline(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    process = next(child for child in root if _local_name(child.tag) == "process")
    flow_nodes = [
        child
        for child in process
        if _local_name(child.tag) in FLOW_NODE_TAGS
    ]
    node_type_counts: dict[str, int] = {}
    critical_path_count = 0
    evidence_required_count = 0
    for node in flow_nodes:
        node_type = _local_name(node.tag)
        node_type_counts[node_type] = node_type_counts.get(node_type, 0) + 1
        if node.attrib.get(f"{{{NAC_NS}}}criticalPath") == "true":
            critical_path_count += 1
        if node.attrib.get(f"{{{NAC_NS}}}evidence") == "required":
            evidence_required_count += 1
    return {
        "process_id": process.attrib.get("id", ""),
        "process_name": process.attrib.get("name", ""),
        "is_executable": process.attrib.get("isExecutable") == "true",
        "flow_node_count": len(flow_nodes),
        "node_type_counts": node_type_counts,
        "critical_path_node_count": critical_path_count,
        "evidence_required_node_count": evidence_required_count,
    }


def _single_case(kg_payload: dict[str, Any], slug: str) -> dict[str, Any]:
    for case in _as_list(kg_payload.get("cases")):
        if isinstance(case, dict) and case.get("slug") == slug:
            return case
    raise KeyError(slug)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", maxsplit=1)[-1]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
