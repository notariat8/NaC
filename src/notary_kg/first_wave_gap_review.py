from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .first_wave_outline import build_first_wave_bpmn_outline


SCHEMA_VERSION = "nac.first-wave-bpmn-outline-gap-review/v0.1"
SHAREPOINT_SCHEMA_PATH = Path("deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json")
ONTOLOGY_CONTRACT_PATH = Path("workflows/contracts/notarial-ontology-sizing-storage.contract.json")


@dataclass(frozen=True, slots=True)
class FirstWaveGapReviewValidation:
    status: str
    errors: tuple[str, ...]


def build_first_wave_bpmn_outline_gap_review(repo_root: Path) -> dict[str, Any]:
    outline = build_first_wave_bpmn_outline(repo_root)
    sharepoint_schema = json.loads((repo_root / SHAREPOINT_SCHEMA_PATH).read_text(encoding="utf-8"))
    ontology_contract = json.loads((repo_root / ONTOLOGY_CONTRACT_PATH).read_text(encoding="utf-8"))
    sharepoint_lists = _sharepoint_lists(sharepoint_schema)
    review_items = [
        _review_item(case_outline, sharepoint_lists, ontology_contract)
        for case_outline in outline["outlines"]
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "mode": "offline_gap_review",
        "source": {
            "first_wave_outline_schema": outline["schema_version"],
            "first_wave_outline_status": outline["status"],
            "sharepoint_schema": str(SHAREPOINT_SCHEMA_PATH),
            "ontology_storage_contract": str(ONTOLOGY_CONTRACT_PATH),
            "central_knowledge_graph_folder_allowed": False,
            "usecase_local_knowledge_graphs_remain_authoritative": True,
        },
        "summary": {
            "first_wave_count": len(review_items),
            "review_slugs": [item["slug"] for item in review_items],
            "sharepoint_field_gap_count": sum(
                len(item["sharepoint_field_gap_plan"]["gaps"])
                for item in review_items
            ),
            "bpmn_gap_count": sum(len(item["bpmn_gap_plan"]["gaps"]) for item in review_items),
            "ontology_patch_count": sum(
                len(item["ontology_projection_patch_plan"]["patches"])
                for item in review_items
            ),
            "owner_gate_required_now": False,
        },
        "review_items": review_items,
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "creates_central_knowledge_graph_folder": False,
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
            "bpmn_remains_process_model_not_runtime_engine": True,
        },
        "next_batch": {
            "recommended_slice": "first_wave_bpmn_outline_gap_review_artifact",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "bpmn_model_mutation",
                "ontology_projection_patch_apply",
            ],
        },
        "errors": [],
    }
    validation = validate_first_wave_bpmn_outline_gap_review(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_first_wave_bpmn_outline_gap_review(payload: dict[str, Any]) -> FirstWaveGapReviewValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("mode") != "offline_gap_review":
        errors.append("gap review must remain offline")
    source = payload.get("source", {})
    if source.get("first_wave_outline_status") != "PASSED":
        errors.append("first-wave outline must pass before gap review")
    if source.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")
    if source.get("usecase_local_knowledge_graphs_remain_authoritative") is not True:
        errors.append("usecase-local knowledge graphs must remain authoritative")

    review_items = payload.get("review_items", [])
    if len(review_items) != 4:
        errors.append("gap review must include exactly four first-wave cases")
    if payload.get("summary", {}).get("sharepoint_field_gap_count", 0) <= 0:
        errors.append("gap review must surface at least one SharePoint field gap")
    if payload.get("summary", {}).get("bpmn_gap_count", 0) <= 0:
        errors.append("gap review must surface at least one BPMN gap")
    for item in review_items:
        slug = item.get("slug", "<missing>")
        for plan_name in ("sharepoint_field_gap_plan", "bpmn_gap_plan", "ontology_projection_patch_plan"):
            plan = item.get(plan_name, {})
            if plan.get("mode") != "plan_only":
                errors.append(f"{slug}: {plan_name} must be plan_only")
            if plan.get("owner_gate_required_before_apply") is not True:
                errors.append(f"{slug}: {plan_name} must require owner gate before apply")
            if plan.get("writes_sharepoint") is not False:
                errors.append(f"{slug}: {plan_name} must not write SharePoint")
            if plan.get("executes_graph_requests") is not False:
                errors.append(f"{slug}: {plan_name} must not execute Graph requests")
        if item.get("sharepoint_field_gap_plan", {}).get("stores_matter_values") is not False:
            errors.append(f"{slug}: SharePoint gap plan must not store matter values")
        if item.get("ontology_projection_patch_plan", {}).get("stores_document_full_text") is not False:
            errors.append(f"{slug}: ontology patch plan must not store document full text")

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
        "creates_central_knowledge_graph_folder",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return FirstWaveGapReviewValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _review_item(
    case_outline: dict[str, Any],
    sharepoint_lists: dict[str, dict[str, Any]],
    ontology_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "slug": case_outline["slug"],
        "title": case_outline["title"],
        "domain": case_outline["domain"],
        "sources": case_outline["sources"],
        "sharepoint_field_gap_plan": _sharepoint_gap_plan(case_outline, sharepoint_lists),
        "bpmn_gap_plan": _bpmn_gap_plan(case_outline),
        "ontology_projection_patch_plan": _ontology_patch_plan(case_outline, ontology_contract),
        "verification_contract_plan": {
            "mode": "plan_only",
            "required_checks": [
                "first_wave_outline_still_passes",
                "sharepoint_gap_plan_contains_no_values",
                "bpmn_patch_is_non_executable",
                "ontology_patch_is_shape_only",
            ],
            "owner_gate_required_before_apply": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
        },
    }


def _sharepoint_gap_plan(case_outline: dict[str, Any], sharepoint_lists: dict[str, dict[str, Any]]) -> dict[str, Any]:
    slug = case_outline["slug"]
    gaps: list[dict[str, Any]] = []
    akten_columns = sharepoint_lists.get("Akten", {}).get("columns_by_name", {})
    vorgangstyp = akten_columns.get("Vorgangstyp", {})
    if slug not in set(vorgangstyp.get("choices", [])):
        gaps.append(
            {
                "id": f"{slug}.akten.vorgangstyp.choice",
                "list": "Akten",
                "field": "Vorgangstyp",
                "gap_type": "choice_extension_plan",
                "planned_value": slug,
                "reason": "First-wave case type is not selectable in the MVP matter metadata list.",
            }
        )
    if case_outline["kg_outline"]["document_types"] > 0:
        gaps.append(
            {
                "id": f"{slug}.dokumentregister.documenttype.taxonomy",
                "list": "DokumentRegister",
                "field": "DocumentType",
                "gap_type": "case_document_type_taxonomy_review",
                "planned_value_count": case_outline["kg_outline"]["document_types"],
                "reason": "Usecase-local document types need a metadata-only taxonomy mapping before schema apply.",
            }
        )
    if case_outline["kg_outline"]["decision_points"] > 0:
        gaps.append(
            {
                "id": f"{slug}.aufgabenfristen.decision-gate-mapping",
                "list": "AufgabenFristen",
                "field": "BpmnStepCode",
                "gap_type": "decision_and_gate_step_mapping_review",
                "planned_value_count": case_outline["kg_outline"]["decision_points"] + case_outline["kg_outline"]["gates"],
                "reason": "Decision and gate shapes need stable BPMN step codes before task-state materialization.",
            }
        )
    return {
        "mode": "plan_only",
        "source_schema": str(SHAREPOINT_SCHEMA_PATH),
        "gaps": gaps,
        "stores_matter_values": False,
        "stores_document_full_text": False,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "owner_gate_required_before_apply": True,
    }


def _bpmn_gap_plan(case_outline: dict[str, Any]) -> dict[str, Any]:
    bpmn = case_outline["bpmn_outline"]
    kg = case_outline["kg_outline"]
    gaps: list[dict[str, Any]] = []
    if bpmn["critical_path_node_count"] == 0:
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.critical-path",
                "gap_type": "missing_critical_path_annotations",
                "recommended_action": "Add non-executable critical-path annotations to the BPMN source.",
            }
        )
    gateway_count = bpmn["node_type_counts"].get("exclusiveGateway", 0) + bpmn["node_type_counts"].get("parallelGateway", 0)
    if kg["decision_points"] > 0 and gateway_count == 0:
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.decision-gateways",
                "gap_type": "decision_points_not_represented_as_gateways",
                "recommended_action": "Review whether KG decision points need explicit BPMN gateway shapes.",
            }
        )
    if bpmn["evidence_required_node_count"] < max(1, bpmn["flow_node_count"] - 1):
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.evidence-coverage",
                "gap_type": "partial_evidence_annotation_coverage",
                "recommended_action": "Review evidence-required annotations before runtime evidence checks.",
            }
        )
    if kg["gates"] > gateway_count + bpmn["node_type_counts"].get("businessRuleTask", 0):
        gaps.append(
            {
                "id": f"{case_outline['slug']}.bpmn.gate-coverage",
                "gap_type": "kg_gates_exceed_bpmn_gate_shapes",
                "recommended_action": "Map KG gates to BPMN gateway or business-rule shapes before deep modeling apply.",
            }
        )
    return {
        "mode": "plan_only",
        "source_bpmn": case_outline["sources"]["bpmn"],
        "gaps": gaps,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "owner_gate_required_before_apply": True,
    }


def _ontology_patch_plan(case_outline: dict[str, Any], ontology_contract: dict[str, Any]) -> dict[str, Any]:
    kg = case_outline["kg_outline"]
    patches = [
        {
            "id": f"{case_outline['slug']}.business-case-type",
            "patch_type": "business_case_type_shape",
            "entities": ["BusinessCaseType"],
            "source": case_outline["sources"]["knowledge_graph"],
        },
        {
            "id": f"{case_outline['slug']}.process-pointer",
            "patch_type": "process_model_pointer",
            "entities": ["ProcessStep", "Gate"],
            "source": case_outline["sources"]["bpmn"],
        },
        {
            "id": f"{case_outline['slug']}.document-evidence-shapes",
            "patch_type": "document_and_evidence_shape",
            "entities": ["DocumentType", "EvidencePointer"],
            "document_type_count": kg["document_types"],
            "evidence_point_count": kg["evidence_points"],
        },
    ]
    mapping_lists = [
        item["list_or_library"]
        for item in ontology_contract.get("sharepoint_projection_mapping", [])
    ]
    return {
        "mode": "plan_only",
        "projection_mode": ontology_contract["projection_rules"]["projection_mode"],
        "source_of_truth": ontology_contract["projection_rules"]["source_of_truth"],
        "target_sharepoint_lists": mapping_lists,
        "patches": patches,
        "stores_matter_values": False,
        "stores_document_full_text": False,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "owner_gate_required_before_apply": True,
    }


def _sharepoint_lists(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lists: dict[str, dict[str, Any]] = {}
    for item in schema.get("sharepoint", {}).get("lists", []):
        columns = item.get("columns", [])
        lists[item["display_name"]] = {
            **item,
            "columns_by_name": {column["name"]: column for column in columns},
        }
    return lists
