from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .first_wave_gap_review import build_first_wave_bpmn_outline_gap_review
from .first_wave_outline import build_first_wave_bpmn_outline
from .process_ontology_contract import build_process_ontology_contract


SCHEMA_VERSION = "nac.first-wave-process-deep-model/v0.1"


@dataclass(frozen=True, slots=True)
class FirstWaveProcessDeepModelValidation:
    status: str
    errors: tuple[str, ...]


def build_first_wave_process_deep_model(repo_root: Path) -> dict[str, Any]:
    outline = build_first_wave_bpmn_outline(repo_root)
    gap_review = build_first_wave_bpmn_outline_gap_review(repo_root)
    process_contract = build_process_ontology_contract(repo_root)
    process_phases = list(process_contract["contract"]["required_process_phases"])
    role_templates = list(process_contract["contract"]["required_role_templates"])
    sharepoint_lists = list(
        process_contract["contract"]["sharepoint_projection_rules"]["required_lists_or_libraries"]
    )
    gap_index = {item["slug"]: item for item in gap_review["review_items"]}

    case_models = [
        _build_case_model(
            repo_root=repo_root,
            outline_item=outline_item,
            gap_item=gap_index[outline_item["slug"]],
            process_phases=process_phases,
            role_templates=role_templates,
            sharepoint_lists=sharepoint_lists,
        )
        for outline_item in outline["outlines"]
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "mode": "offline_deep_process_model_contract",
        "source": {
            "first_wave_outline_schema": outline["schema_version"],
            "first_wave_outline_status": outline["status"],
            "first_wave_gap_review_schema": gap_review["schema_version"],
            "first_wave_gap_review_status": gap_review["status"],
            "process_ontology_contract_schema": process_contract["schema_version"],
            "process_ontology_contract_status": process_contract["status"],
            "usecase_local_knowledge_graphs_remain_authoritative": True,
            "central_knowledge_graph_folder_allowed": False,
        },
        "summary": {
            "first_wave_count": len(case_models),
            "case_slugs": [case["slug"] for case in case_models],
            "phase_template_count": sum(len(case["phase_plan"]) for case in case_models),
            "role_binding_count": sum(len(case["role_binding_plan"]) for case in case_models),
            "bpmn_flow_node_binding_count": sum(
                case["bpmn_binding_plan"]["flow_node_count"] for case in case_models
            ),
            "required_information_binding_count": sum(
                case["kg_binding_plan"]["required_information_count"] for case in case_models
            ),
            "evidence_binding_count": sum(
                case["evidence_binding_plan"]["evidence_point_count"] for case in case_models
            ),
            "sharepoint_projection_count": sum(
                len(case["sharepoint_projection_plan"]["list_bindings"]) for case in case_models
            ),
            "open_gap_count": sum(case["gap_closure_plan"]["total_gap_count"] for case in case_models),
            "owner_gate_required_now": False,
        },
        "case_models": case_models,
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "mutates_bpmn_sources": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "creates_central_knowledge_graph_folder": False,
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
            "bpmn_remains_process_model_not_runtime_engine": True,
        },
        "next_batch": {
            "recommended_slice": "first_wave_process_instance_seed_plan",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "bpmn_model_mutation",
                "ontology_projection_patch_apply",
                "matter_instance_seed_write",
            ],
        },
        "errors": [],
    }
    validation = validate_first_wave_process_deep_model(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_first_wave_process_deep_model(payload: dict[str, Any]) -> FirstWaveProcessDeepModelValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("mode") != "offline_deep_process_model_contract":
        errors.append("deep process model must remain offline")

    source = payload.get("source", {})
    for key in (
        "first_wave_outline_status",
        "first_wave_gap_review_status",
        "process_ontology_contract_status",
    ):
        if source.get(key) != "PASSED":
            errors.append(f"required upstream source did not pass: {key}")
    if source.get("usecase_local_knowledge_graphs_remain_authoritative") is not True:
        errors.append("usecase-local knowledge graphs must remain authoritative")
    if source.get("central_knowledge_graph_folder_allowed") is not False:
        errors.append("central knowledge-graph folder must remain blocked")

    case_models = payload.get("case_models", [])
    if len(case_models) != 4:
        errors.append("deep model must include exactly four first-wave cases")
    if payload.get("summary", {}).get("phase_template_count") != 32:
        errors.append("deep model must bind eight process phases for each first-wave case")
    if payload.get("summary", {}).get("open_gap_count", 0) <= 0:
        errors.append("deep model must carry forward known gap closure work")

    required_phases = {
        "intake",
        "identity_and_role_check",
        "drafting",
        "review_and_approval",
        "appointment_or_signature",
        "register_or_external_submission",
        "completion",
        "archive",
    }
    required_roles = {
        "notary",
        "notarial_assistant",
        "deputy_notary",
        "deputy_assistant",
        "participant",
        "external_authority",
        "system_runtime",
    }
    for case in case_models:
        slug = case.get("slug", "<missing>")
        phases = case.get("phase_plan", [])
        if {phase.get("phase") for phase in phases} != required_phases:
            errors.append(f"{slug}: phase plan must include the canonical process phases")
        if {role.get("role_template") for role in case.get("role_binding_plan", [])} != required_roles:
            errors.append(f"{slug}: role binding must include every canonical role template")
        if case.get("bpmn_binding_plan", {}).get("is_executable") is not False:
            errors.append(f"{slug}: BPMN binding must stay non-executable")
        if case.get("kg_binding_plan", {}).get("stores_matter_values") is not False:
            errors.append(f"{slug}: KG binding must not store matter values")
        if case.get("evidence_binding_plan", {}).get("stores_document_full_text") is not False:
            errors.append(f"{slug}: evidence binding must not store document full text")
        if case.get("sharepoint_projection_plan", {}).get("writes_sharepoint") is not False:
            errors.append(f"{slug}: SharePoint projection must not write SharePoint")
        if case.get("gap_closure_plan", {}).get("owner_gate_required_before_apply") is not True:
            errors.append(f"{slug}: gap closure must require owner gate before apply")

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
        "mutates_bpmn_sources",
        "stores_matter_instance_values",
        "stores_document_full_text",
        "stores_tokens_or_secrets",
        "creates_central_knowledge_graph_folder",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return FirstWaveProcessDeepModelValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _build_case_model(
    *,
    repo_root: Path,
    outline_item: dict[str, Any],
    gap_item: dict[str, Any],
    process_phases: list[str],
    role_templates: list[str],
    sharepoint_lists: list[str],
) -> dict[str, Any]:
    slug = outline_item["slug"]
    kg_path = repo_root / outline_item["sources"]["knowledge_graph"]
    kg_payload = json.loads(kg_path.read_text(encoding="utf-8"))
    case = _single_case(kg_payload, slug)
    required_information = _redacted_refs(case.get("required_information"), "required_information")
    documents = _redacted_refs(case.get("documents"), "document")
    decisions = _redacted_refs(case.get("decisions"), "decision")
    gates = _redacted_refs(case.get("gates"), "gate")
    evidence = _redacted_refs(case.get("evidence"), "evidence")
    phase_plan = [
        _phase_plan_item(
            phase=phase,
            index=index,
            required_information=required_information,
            documents=documents,
            decisions=decisions,
            gates=gates,
            evidence=evidence,
        )
        for index, phase in enumerate(process_phases)
    ]
    return {
        "slug": slug,
        "title": outline_item["title"],
        "domain": outline_item["domain"],
        "routing": outline_item["routing"],
        "source_paths": outline_item["sources"],
        "phase_plan": phase_plan,
        "role_binding_plan": [_role_binding(role) for role in role_templates],
        "kg_binding_plan": {
            "mode": "redacted_shape_binding",
            "case_id": outline_item["kg_outline"]["case_id"],
            "required_information_count": len(required_information),
            "document_type_count": len(documents),
            "decision_point_count": len(decisions),
            "gate_count": len(gates),
            "evidence_point_count": len(evidence),
            "required_information_refs": required_information,
            "document_refs": documents,
            "decision_refs": decisions,
            "gate_refs": gates,
            "evidence_refs": evidence,
            "stores_matter_values": False,
            "stores_document_full_text": False,
        },
        "bpmn_binding_plan": {
            "mode": "existing_bpmn_source_reference",
            "process_id": outline_item["bpmn_outline"]["process_id"],
            "process_name": outline_item["bpmn_outline"]["process_name"],
            "is_executable": outline_item["bpmn_outline"]["is_executable"],
            "flow_node_count": outline_item["bpmn_outline"]["flow_node_count"],
            "node_type_counts": outline_item["bpmn_outline"]["node_type_counts"],
            "critical_path_node_count": outline_item["bpmn_outline"]["critical_path_node_count"],
            "evidence_required_node_count": outline_item["bpmn_outline"]["evidence_required_node_count"],
            "mutates_bpmn_source": False,
        },
        "evidence_binding_plan": {
            "mode": "evidence_shape_only",
            "evidence_point_count": len(evidence),
            "bpmn_evidence_required_node_count": outline_item["bpmn_outline"]["evidence_required_node_count"],
            "required_readbacks": [
                "process_instance_metadata",
                "task_status_transition",
                "document_pointer_presence",
                "audit_event_presence",
            ],
            "stores_document_full_text": False,
            "stores_matter_values": False,
        },
        "sharepoint_projection_plan": {
            "mode": "metadata_projection_plan_only",
            "rest_only": True,
            "sdk_allowed": False,
            "legacy_sharepoint_api_allowed": False,
            "writes_sharepoint": False,
            "list_bindings": [_list_binding(name, slug) for name in sharepoint_lists],
        },
        "gap_closure_plan": {
            "mode": "plan_only",
            "sharepoint_field_gap_count": len(gap_item["sharepoint_field_gap_plan"]["gaps"]),
            "bpmn_gap_count": len(gap_item["bpmn_gap_plan"]["gaps"]),
            "ontology_patch_count": len(gap_item["ontology_projection_patch_plan"]["patches"]),
            "total_gap_count": (
                len(gap_item["sharepoint_field_gap_plan"]["gaps"])
                + len(gap_item["bpmn_gap_plan"]["gaps"])
                + len(gap_item["ontology_projection_patch_plan"]["patches"])
            ),
            "owner_gate_required_before_apply": True,
            "writes_sharepoint": False,
            "executes_graph_requests": False,
        },
        "verification_contract_plan": {
            "contract_id": f"verification.first_wave_process_deep_model.{slug}",
            "required_checks": [
                "validate_first_wave_process_deep_model",
                "validate_first_wave_bpmn_outline",
                "validate_first_wave_bpmn_outline_gap_review",
                "validate_notarial_process_ontology_contract",
            ],
            "pass_condition": "all_checks_pass_and_no_live_writes",
        },
    }


def _phase_plan_item(
    *,
    phase: str,
    index: int,
    required_information: list[dict[str, Any]],
    documents: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "phase": phase,
        "order": index + 1,
        "task_template_id": f"task.{phase}",
        "primary_role_template": _primary_role_for_phase(phase),
        "required_information_refs": _distributed_refs(required_information, index),
        "document_refs": _distributed_refs(documents, index),
        "decision_refs": _distributed_refs(decisions, index),
        "gate_refs": _distributed_refs(gates, index),
        "evidence_refs": _distributed_refs(evidence, index),
        "bpmn_binding": {
            "mode": "phase_to_existing_bpmn_flow_nodes",
            "binding_required_before_execution": True,
            "mutates_bpmn_source": False,
        },
        "sharepoint_projection": {
            "matter_list": "Akten",
            "task_list": "AufgabenFristen",
            "document_pointer_list": "DokumentRegister",
            "audit_list": "AuditJournalLite",
            "writes_sharepoint": False,
        },
    }


def _role_binding(role: str) -> dict[str, Any]:
    return {
        "role_template": role,
        "binding_mode": "entra_group_or_matter_role_projection",
        "stores_user_identity_values": False,
        "requires_time_limited_delegation": role in {"deputy_notary", "deputy_assistant"},
        "sharepoint_permission_source": "matter_access_projection",
    }


def _list_binding(list_name: str, slug: str) -> dict[str, Any]:
    return {
        "list_or_library": list_name,
        "projection_key": f"{slug}.{list_name}",
        "projection_mode": "metadata_only",
        "stores_document_full_text": False,
        "stores_matter_values": False,
    }


def _primary_role_for_phase(phase: str) -> str:
    mapping = {
        "intake": "notarial_assistant",
        "identity_and_role_check": "notarial_assistant",
        "drafting": "notarial_assistant",
        "review_and_approval": "notary",
        "appointment_or_signature": "notary",
        "register_or_external_submission": "system_runtime",
        "completion": "notarial_assistant",
        "archive": "system_runtime",
    }
    return mapping.get(phase, "notarial_assistant")


def _distributed_refs(items: list[dict[str, Any]], index: int) -> list[str]:
    if not items:
        return []
    if index >= len(items):
        return []
    return [str(items[index]["id"])]


def _redacted_refs(items: Any, fallback_prefix: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for index, item in enumerate(_as_list(items), start=1):
        if isinstance(item, dict):
            ref = {
                "id": str(item.get("id") or f"{fallback_prefix}.{index}"),
                "label": str(item.get("label") or item.get("name") or item.get("id") or fallback_prefix),
                "status": str(item.get("status") or "unknown"),
            }
            if item.get("owner_role"):
                ref["owner_role"] = str(item["owner_role"])
            if item.get("privacy_class"):
                ref["privacy_class"] = str(item["privacy_class"])
            if item.get("contains_personal_data") is not None:
                ref["contains_personal_data"] = bool(item["contains_personal_data"])
            refs.append(ref)
        else:
            refs.append({"id": str(item), "label": str(item), "status": "unknown"})
    return refs


def _single_case(kg_payload: dict[str, Any], slug: str) -> dict[str, Any]:
    for case in _as_list(kg_payload.get("cases")):
        if isinstance(case, dict) and case.get("slug") == slug:
            return case
    raise KeyError(f"KG case not found: {slug}")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
