from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import build_business_case_inventory
from .process_ontology_contract import (
    CONTRACT_RELATIVE_PATH as PROCESS_ONTOLOGY_CONTRACT_PATH,
    build_process_ontology_contract,
)


SHAREPOINT_SCHEMA_PATH = Path("deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json")
SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-gap/v0.1"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_gap"


EXPECTED_PROCESS_COLUMNS: dict[str, list[dict[str, Any]]] = {
    "Akten": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable runtime process-instance identifier."},
        {"name": "CurrentPhase", "type": "choice", "required": True, "reason": "Current canonical process phase from the process ontology contract."},
        {"name": "CurrentBpmnStepCode", "type": "text", "required": False, "reason": "Current BPMN step pointer for task and evidence routing."},
        {"name": "BpmnModelRef", "type": "text", "required": False, "reason": "Approved BPMN model pointer for the matter's business-case type."},
        {"name": "LastProcessEventId", "type": "text", "required": False, "reason": "Last redacted event pointer for idempotent agent/runtime updates."},
    ],
    "Beteiligte": [
        {"name": "RoleBindingId", "type": "text", "required": True, "reason": "Stable role-binding identifier separate from the party identifier."},
        {"name": "RoleTemplate", "type": "choice", "required": True, "reason": "Canonical role template from the process ontology contract."},
        {"name": "AccessPurpose", "type": "choice", "required": False, "reason": "Purpose-bound participant access and delegation context."},
        {"name": "AuthorizedUntil", "type": "dateTime", "required": False, "reason": "Time-boxed participant access boundary when needed."},
    ],
    "AufgabenFristen": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key."},
        {"name": "ProcessPhase", "type": "choice", "required": True, "reason": "Canonical phase for process dashboards and bounded agent tools."},
        {"name": "TaskType", "type": "choice", "required": True, "reason": "Typed task shape for repeatable workflow execution."},
        {"name": "GateType", "type": "choice", "required": False, "reason": "Gate and decision-point shape from the process ontology contract."},
        {"name": "EvidenceRequired", "type": "boolean", "required": True, "reason": "Machine-readable evidence obligation before completion."},
        {"name": "CompletedAt", "type": "dateTime", "required": False, "reason": "Completion timestamp for process state and audit correlation."},
    ],
    "DokumentRegister": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key."},
        {"name": "BpmnStepCode", "type": "text", "required": False, "reason": "Document pointer to the process step that produced or requires it."},
        {"name": "EvidencePointerId", "type": "text", "required": False, "reason": "Evidence pointer join key without storing document content."},
        {"name": "DocumentVersionLabel", "type": "text", "required": False, "reason": "Version label for document lifecycle without raw document payload."},
        {"name": "ReviewStatus", "type": "choice", "required": False, "reason": "Review and approval status separate from draft status."},
    ],
    "Vertretungsfreigaben": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key for deputy grants."},
        {"name": "AccessPurpose", "type": "choice", "required": True, "reason": "Purpose-bound delegation as required by the access model."},
        {"name": "ValidityWindowId", "type": "text", "required": False, "reason": "Explicit validity-window pointer for replay and audit."},
        {"name": "RevokedAt", "type": "dateTime", "required": False, "reason": "Revocation timestamp for time-boxed delegation history."},
    ],
    "AuditJournalLite": [
        {"name": "ProcessInstanceId", "type": "text", "required": True, "reason": "Stable process-instance join key for audit events."},
        {"name": "ProcessPhase", "type": "choice", "required": False, "reason": "Phase context for redacted process event evidence."},
        {"name": "BpmnStepCode", "type": "text", "required": False, "reason": "Step context for redacted process event evidence."},
        {"name": "EvidencePointerId", "type": "text", "required": False, "reason": "Evidence pointer without raw file or payload content."},
    ],
}

OPTIONAL_PROCESS_PROJECTIONS = {
    "lists": {
        "Prozessregister": [
            {"name": "ProcessModelId", "type": "text", "required": True},
            {"name": "BusinessCaseType", "type": "choice", "required": True},
            {"name": "ProcessPhaseTemplate", "type": "multiChoice", "required": True},
            {"name": "BpmnModelRef", "type": "text", "required": False},
            {"name": "ModelStatus", "type": "choice", "required": True},
            {"name": "Version", "type": "text", "required": True},
        ]
    },
    "document_libraries": {
        "BPMN Models": [
            {"name": "BusinessCaseType", "type": "choice", "required": True},
            {"name": "ModelStatus", "type": "choice", "required": True},
            {"name": "Version", "type": "text", "required": True},
        ]
    },
}


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaGapValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_gap(repo_root: Path) -> dict[str, Any]:
    process_contract = build_process_ontology_contract(repo_root)
    inventory = build_business_case_inventory(repo_root)
    sharepoint_schema = json.loads((repo_root / SHAREPOINT_SCHEMA_PATH).read_text(encoding="utf-8"))
    list_index = _sharepoint_list_index(sharepoint_schema)
    library_index = _sharepoint_library_index(sharepoint_schema)
    required_lists = process_contract["contract"]["sharepoint_projection_rules"]["required_lists_or_libraries"]
    process_phases = process_contract["contract"]["required_process_phases"]
    role_templates = process_contract["contract"]["required_role_templates"]
    all_case_slugs = [item["slug"] for item in inventory["business_cases"]]

    missing_required_lists = [list_name for list_name in required_lists if list_name not in list_index]
    optional_projection_gaps = _optional_projection_gaps(list_index, library_index)
    field_gaps = _field_gaps(list_index)
    choice_gaps = _choice_gaps(list_index, all_case_slugs, process_phases, role_templates)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_schema_gap_review",
        "source": {
            "process_ontology_contract": str(PROCESS_ONTOLOGY_CONTRACT_PATH),
            "process_ontology_contract_status": process_contract["status"],
            "sharepoint_schema": str(SHAREPOINT_SCHEMA_PATH),
            "sharepoint_schema_version": sharepoint_schema["schema_version"],
            "business_case_inventory_schema": inventory["schema_version"],
            "business_case_inventory_status": inventory["status"],
            "graph_rest_only": sharepoint_schema["graph"]["rest_only"],
            "legacy_sharepoint_api_allowed": sharepoint_schema["graph"]["legacy_sharepoint_api_allowed"],
        },
        "summary": {
            "business_case_count": len(all_case_slugs),
            "required_list_count": len(required_lists),
            "missing_required_list_count": len(missing_required_lists),
            "optional_projection_gap_count": len(optional_projection_gaps),
            "field_gap_count": len(field_gaps),
            "choice_gap_count": len(choice_gaps),
            "total_gap_count": len(missing_required_lists) + len(optional_projection_gaps) + len(field_gaps) + len(choice_gaps),
            "owner_gate_required_now": False,
        },
        "missing_required_lists": _missing_required_list_gaps(missing_required_lists),
        "optional_projection_gaps": optional_projection_gaps,
        "field_gaps": field_gaps,
        "choice_gaps": choice_gaps,
        "apply_boundary": {
            "mode": "plan_only",
            "owner_gate_required_before_apply": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "rest_endpoint_family": "microsoft_graph_v1_lists_columns_future_apply",
        },
        "guardrails": {
            "offline_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "creates_central_knowledge_graph_folder": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_plan",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "sharepoint_schema_apply",
                "graph_live_write",
                "provision_optional_process_register",
                "provision_bpmn_models_library",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_gap(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_process_ontology_sharepoint_schema_gap(payload: dict[str, Any]) -> ProcessOntologySchemaGapValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("mode") != "offline_schema_gap_review":
        errors.append("schema gap review must remain offline")
    source = payload.get("source", {})
    if source.get("process_ontology_contract_status") != "PASSED":
        errors.append("process ontology contract must pass before schema gap review")
    if source.get("business_case_inventory_status") != "PASSED":
        errors.append("business-case inventory must pass before schema gap review")
    if source.get("graph_rest_only") is not True:
        errors.append("SharePoint schema must remain Graph REST only")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")

    summary = payload.get("summary", {})
    if summary.get("business_case_count", 0) < 20:
        errors.append("schema gap review must cover all canonical business cases")
    if summary.get("missing_required_list_count") != 0:
        errors.append("MVP required SharePoint lists must exist before field gap review")
    if summary.get("field_gap_count", 0) <= 0:
        errors.append("expected process-instance field gaps to be surfaced")
    if summary.get("choice_gap_count", 0) <= 0:
        errors.append("expected process ontology choice gaps to be surfaced")
    if summary.get("optional_projection_gap_count", 0) <= 0:
        errors.append("expected optional Prozessregister/BPMN Models projection gaps")

    for gap in [*payload.get("field_gaps", []), *payload.get("choice_gaps", []), *payload.get("optional_projection_gaps", [])]:
        if gap.get("mode") != "plan_only":
            errors.append(f"{gap.get('id', '<unknown>')}: gap must be plan_only")
        if gap.get("owner_gate_required_before_apply") is not True:
            errors.append(f"{gap.get('id', '<unknown>')}: owner gate must be required before apply")
        if gap.get("executes_graph_requests") is not False:
            errors.append(f"{gap.get('id', '<unknown>')}: must not execute Graph requests")
        if gap.get("writes_sharepoint") is not False:
            errors.append(f"{gap.get('id', '<unknown>')}: must not write SharePoint")

    apply_boundary = payload.get("apply_boundary", {})
    if apply_boundary.get("mode") != "plan_only":
        errors.append("apply boundary must remain plan_only")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if apply_boundary.get(key) is not False:
            errors.append(f"apply boundary must keep {key} false")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only",):
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
        "legacy_sharepoint_api_allowed",
        "graph_sdk_allowed",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return ProcessOntologySchemaGapValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _sharepoint_list_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["display_name"]: {
            **item,
            "columns_by_name": {column["name"]: column for column in item.get("columns", [])},
        }
        for item in schema.get("sharepoint", {}).get("lists", [])
    }


def _sharepoint_library_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["display_name"]: item
        for item in schema.get("sharepoint", {}).get("document_libraries", [])
    }


def _missing_required_list_gaps(missing_required_lists: list[str]) -> list[dict[str, Any]]:
    return [
        _gap(
            gap_id=f"missing-required-list.{list_name}",
            target=list_name,
            gap_type="missing_required_list",
            required_for_mvp=True,
            reason="Required by the process ontology contract SharePoint projection rules.",
        )
        for list_name in missing_required_lists
    ]


def _optional_projection_gaps(
    list_index: dict[str, dict[str, Any]],
    library_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for list_name, columns in OPTIONAL_PROCESS_PROJECTIONS["lists"].items():
        if list_name not in list_index:
            gaps.append(
                _gap(
                    gap_id=f"optional-list.{list_name}",
                    target=list_name,
                    gap_type="missing_optional_process_projection_list",
                    required_for_mvp=False,
                    reason="Optional process model registry for BPMN/SPFx viewer and process template selection.",
                    planned_columns=columns,
                )
            )
    for library_name, columns in OPTIONAL_PROCESS_PROJECTIONS["document_libraries"].items():
        if library_name not in library_index:
            gaps.append(
                _gap(
                    gap_id=f"optional-library.{library_name}",
                    target=library_name,
                    gap_type="missing_optional_bpmn_model_library",
                    required_for_mvp=False,
                    reason="Optional SharePoint document library for approved BPMN model files.",
                    planned_columns=columns,
                )
            )
    return gaps


def _field_gaps(list_index: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for list_name, expected_columns in EXPECTED_PROCESS_COLUMNS.items():
        existing_columns = list_index.get(list_name, {}).get("columns_by_name", {})
        for expected in expected_columns:
            existing = existing_columns.get(expected["name"])
            if existing is None:
                gaps.append(
                    _gap(
                        gap_id=f"{list_name}.{expected['name']}.missing",
                        target=list_name,
                        gap_type="missing_process_field",
                        field=expected,
                        required_for_mvp=bool(expected["required"]),
                        reason=expected["reason"],
                    )
                )
                continue
            if existing.get("type") != expected["type"]:
                gaps.append(
                    _gap(
                        gap_id=f"{list_name}.{expected['name']}.type",
                        target=list_name,
                        gap_type="field_type_mismatch",
                        field=expected,
                        existing_type=existing.get("type"),
                        required_for_mvp=bool(expected["required"]),
                        reason=expected["reason"],
                    )
                )
    return gaps


def _choice_gaps(
    list_index: dict[str, dict[str, Any]],
    all_case_slugs: list[str],
    process_phases: list[str],
    role_templates: list[str],
) -> list[dict[str, Any]]:
    checks = [
        {
            "list": "Akten",
            "field": "Vorgangstyp",
            "required_choices": all_case_slugs,
            "gap_type": "business_case_choice_extension_plan",
            "required_for_mvp": True,
        },
        {
            "list": "Akten",
            "field": "CurrentPhase",
            "required_choices": process_phases,
            "gap_type": "process_phase_choice_extension_plan",
            "required_for_mvp": True,
        },
        {
            "list": "AufgabenFristen",
            "field": "ProcessPhase",
            "required_choices": process_phases,
            "gap_type": "process_phase_choice_extension_plan",
            "required_for_mvp": True,
        },
        {
            "list": "Beteiligte",
            "field": "RoleTemplate",
            "required_choices": role_templates,
            "gap_type": "role_template_choice_extension_plan",
            "required_for_mvp": True,
        },
    ]
    gaps: list[dict[str, Any]] = []
    for check in checks:
        columns = list_index.get(str(check["list"]), {}).get("columns_by_name", {})
        column = columns.get(str(check["field"]))
        existing_choices = set(column.get("choices", [])) if column else set()
        missing_choices = [choice for choice in check["required_choices"] if choice not in existing_choices]
        if not missing_choices:
            continue
        gaps.append(
            _gap(
                gap_id=f"{check['list']}.{check['field']}.choices",
                target=str(check["list"]),
                gap_type=str(check["gap_type"]),
                field={"name": check["field"], "type": "choice", "required": check["required_for_mvp"]},
                required_for_mvp=bool(check["required_for_mvp"]),
                reason="Choice values are incomplete for the process ontology contract.",
                missing_choice_count=len(missing_choices),
                missing_choices=missing_choices,
            )
        )
    return gaps


def _gap(
    *,
    gap_id: str,
    target: str,
    gap_type: str,
    required_for_mvp: bool,
    reason: str,
    field: dict[str, Any] | None = None,
    planned_columns: list[dict[str, Any]] | None = None,
    existing_type: str | None = None,
    missing_choice_count: int | None = None,
    missing_choices: list[str] | None = None,
) -> dict[str, Any]:
    gap = {
        "id": gap_id,
        "target": target,
        "gap_type": gap_type,
        "mode": "plan_only",
        "required_for_mvp_process_instances": required_for_mvp,
        "reason": reason,
        "owner_gate_required_before_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
    }
    if field is not None:
        gap["field"] = field
    if planned_columns is not None:
        gap["planned_columns"] = planned_columns
    if existing_type is not None:
        gap["existing_type"] = existing_type
    if missing_choice_count is not None:
        gap["missing_choice_count"] = missing_choice_count
    if missing_choices is not None:
        gap["missing_choices"] = missing_choices
    return gap
