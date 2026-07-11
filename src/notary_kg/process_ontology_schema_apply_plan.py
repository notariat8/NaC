from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_contract import build_process_ontology_contract
from .process_ontology_schema_gap import (
    SHAREPOINT_SCHEMA_PATH,
    build_process_ontology_sharepoint_schema_gap,
)


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-plan/v0.2"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_plan"
LIVE_EXECUTION_APPROVAL_STATE = "BLOCKED_PENDING_S6_S7_APPROVAL"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_LIST_CREATE_DOC = "https://learn.microsoft.com/en-us/graph/api/list-create?view=graph-rest-1.0"
GRAPH_COLUMN_CREATE_DOC = "https://learn.microsoft.com/en-us/graph/api/list-post-columns?view=graph-rest-1.0"
GRAPH_COLUMN_UPDATE_DOC = "https://learn.microsoft.com/en-us/graph/api/columndefinition-update?view=graph-rest-1.0"
CHOICE_COLUMN_ODATA_TYPE = "microsoft.graph.choiceColumn"


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyPlanValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_plan(repo_root: Path) -> dict[str, Any]:
    gap_review = build_process_ontology_sharepoint_schema_gap(repo_root)
    process_contract = build_process_ontology_contract(repo_root)
    sharepoint_schema = json.loads((repo_root / SHAREPOINT_SCHEMA_PATH).read_text(encoding="utf-8"))
    existing_lists = _sharepoint_list_index(sharepoint_schema)
    choice_catalog = _choice_catalog(gap_review, process_contract)

    steps: list[dict[str, Any]] = []
    for gap in gap_review["required_projection_gaps"]:
        steps.append(_create_list_step(gap, choice_catalog, len(steps) + 1, "genericList"))

    for gap in gap_review["field_gaps"]:
        if gap["gap_type"] == "missing_process_field":
            steps.append(_create_column_step(gap, choice_catalog, len(steps) + 1))

    for gap in gap_review["choice_gaps"]:
        steps.append(_extend_choice_step(gap, existing_lists, choice_catalog, len(steps) + 1))

    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_graph_rest_apply_plan",
        "source": {
            "schema_gap_review": gap_review["schema_version"],
            "schema_gap_status": gap_review["status"],
            "schema_gap_contract_id": gap_review["contract_id"],
            "legacy_column_contract": gap_review["legacy_column_contract"],
            "sharepoint_schema": str(SHAREPOINT_SCHEMA_PATH),
            "sharepoint_schema_version": sharepoint_schema["schema_version"],
            "graph_base_url": GRAPH_BASE_URL,
            "graph_rest_only": sharepoint_schema["graph"]["rest_only"],
            "legacy_sharepoint_api_allowed": sharepoint_schema["graph"]["legacy_sharepoint_api_allowed"],
            "graph_sdk_allowed": sharepoint_schema["graph"]["sdk_allowed"],
        },
        "summary": {
            "source_total_gap_count": gap_review["summary"]["total_gap_count"],
            "source_required_gap_count": (
                len(gap_review["required_projection_gaps"])
                + sum(1 for gap in gap_review["field_gaps"] if gap["gap_type"] == "missing_process_field")
                + len(gap_review["choice_gaps"])
            ),
            "excluded_optional_projection_gap_count": len(gap_review["optional_projection_gaps"]),
            "create_list_step_count": sum(1 for step in steps if step["operation"] == "create_list"),
            "create_document_library_step_count": sum(
                1 for step in steps if step["operation"] == "create_document_library"
            ),
            "create_column_step_count": sum(1 for step in steps if step["operation"] == "create_column"),
            "extend_choice_step_count": sum(1 for step in steps if step["operation"] == "extend_choice_column"),
            "total_step_count": len(steps),
            "owner_gate_required_now": False,
            "owner_gate_required_before_apply": True,
            "live_execution_approval_state": LIVE_EXECUTION_APPROVAL_STATE,
        },
        "apply_boundary": {
            "mode": "plan_only",
            "owner_gate_required_before_apply": True,
            "live_execution_approval_state": LIVE_EXECUTION_APPROVAL_STATE,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "future_apply_requires_owner_approval": True,
            "future_apply_expected_permission": "Sites.Manage.All",
            "future_apply_endpoint_families": [
                "POST /sites/{site-id}/lists",
                "POST /sites/{site-id}/lists/{list-id}/columns",
                "PATCH /sites/{site-id}/lists/{list-id}/columns/{column-id}",
            ],
        },
        "recovery_evidence_plan": {
            "pre_apply_snapshot_required": True,
            "snapshot_scope": [
                "target_list_metadata",
                "target_column_definitions",
                "list_and_column_etags_when_available",
            ],
            "additive_rollback_only": True,
            "delete_created_columns_on_rollback": False,
            "delete_canonical_values_on_rollback": False,
            "restore_projection_metadata_with_etag_guards": True,
            "automatic_rollback_allowed": False,
        },
        "documentation_references": [
            {
                "id": "graph_list_create",
                "url": GRAPH_LIST_CREATE_DOC,
                "endpoint": "POST /sites/{site-id}/lists",
            },
            {
                "id": "graph_column_create",
                "url": GRAPH_COLUMN_CREATE_DOC,
                "endpoint": "POST /sites/{site-id}/lists/{list-id}/columns",
            },
            {
                "id": "graph_column_update",
                "url": GRAPH_COLUMN_UPDATE_DOC,
                "endpoint": "PATCH /sites/{site-id}/lists/{list-id}/columns/{column-id}",
            },
        ],
        "steps": steps,
        "optional_projection_plan": {
            "mode": "separate_opt_in_plan",
            "included_in_default_s2_plan": False,
            "gap_count": len(gap_review["optional_projection_gaps"]),
            "gaps": gap_review["optional_projection_gaps"],
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
            "recommended_slice": "process_ontology_sharepoint_schema_apply_readiness",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "graph_live_write",
                "sharepoint_schema_apply",
                "provision_optional_process_register",
                "provision_bpmn_models_library",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_apply_plan(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_process_ontology_sharepoint_schema_apply_plan(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyPlanValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("mode") != "offline_graph_rest_apply_plan":
        errors.append("apply plan must remain offline")

    source = payload.get("source", {})
    legacy = source.get("legacy_column_contract", {})
    if legacy.get("target") != "Akten.Vorgangstyp" or legacy.get("protected") is not True:
        errors.append("apply plan must bind the protected legacy Choice fingerprint")
    if legacy.get("expected_type") != "choice":
        errors.append("apply plan must preserve legacy Akten.Vorgangstyp as Choice")
    if source.get("schema_gap_status") != "PASSED":
        errors.append("schema gap review must pass before building apply plan")
    if source.get("graph_rest_only") is not True:
        errors.append("Graph REST must remain the only API surface")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")
    if source.get("graph_sdk_allowed") is not False:
        errors.append("Graph SDK must remain blocked for this apply-plan contract")

    summary = payload.get("summary", {})
    for key in ("source_total_gap_count", "source_required_gap_count", "excluded_optional_projection_gap_count"):
        if not isinstance(summary.get(key), int) or summary[key] < 0:
            errors.append(f"{key} must be a non-negative integer")
    if summary.get("total_step_count") != summary.get("source_required_gap_count"):
        errors.append("default apply plan must contain exactly one step per required source gap")
    operation_count = sum(
        int(summary.get(key, 0))
        for key in (
            "create_list_step_count",
            "create_document_library_step_count",
            "create_column_step_count",
            "extend_choice_step_count",
        )
    )
    if summary.get("total_step_count") != operation_count:
        errors.append("apply plan operation counts must equal total_step_count")
    if summary.get("owner_gate_required_now") is not False:
        errors.append("offline plan creation must not require owner gate now")
    if summary.get("owner_gate_required_before_apply") is not True:
        errors.append("live apply must remain owner-gated")

    apply_boundary = payload.get("apply_boundary", {})
    if apply_boundary.get("mode") != "plan_only":
        errors.append("apply boundary must remain plan_only")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if apply_boundary.get(key) is not False:
            errors.append(f"apply boundary must keep {key} false")
    if apply_boundary.get("future_apply_requires_owner_approval") is not True:
        errors.append("future apply must require owner approval")
    if apply_boundary.get("live_execution_approval_state") != LIVE_EXECUTION_APPROVAL_STATE:
        errors.append("S2 live execution must remain blocked pending S6/S7 approval")

    for expected in (
        "POST /sites/{site-id}/lists",
        "POST /sites/{site-id}/lists/{list-id}/columns",
        "PATCH /sites/{site-id}/lists/{list-id}/columns/{column-id}",
    ):
        if expected not in apply_boundary.get("future_apply_endpoint_families", []):
            errors.append(f"missing Graph endpoint family: {expected}")

    if any(
        step.get("target") == "Akten"
        and (
            step.get("source_gap_id") == "Akten.Vorgangstyp.choices"
            or step.get("request", {}).get("body", {}).get("name") == "Vorgangstyp"
        )
        for step in payload.get("steps", [])
    ):
        errors.append("legacy Akten.Vorgangstyp must not be targeted by the S2 plan")

    optional_plan = payload.get("optional_projection_plan", {})
    if optional_plan.get("mode") != "separate_opt_in_plan":
        errors.append("optional projections must use a separate opt-in plan")
    if optional_plan.get("included_in_default_s2_plan") is not False:
        errors.append("optional projections must not be included in the default S2 plan")
    optional_targets = {gap.get("target") for gap in optional_plan.get("gaps", [])}
    if optional_plan.get("gap_count") != len(optional_plan.get("gaps", [])):
        errors.append("optional projection gap_count must match gaps")
    if optional_plan.get("gap_count", 0) > 0 and not {"Prozessregister", "BPMN Models"}.issubset(optional_targets):
        errors.append("non-empty optional projection plan must retain Prozessregister and BPMN Models")
    if any(step.get("target") in optional_targets for step in payload.get("steps", [])):
        errors.append("default S2 plan must not contain optional projection steps")

    recovery = payload.get("recovery_evidence_plan", {})
    for key in ("pre_apply_snapshot_required", "additive_rollback_only", "restore_projection_metadata_with_etag_guards"):
        if recovery.get(key) is not True:
            errors.append(f"recovery evidence plan must require {key}")
    for key in ("delete_created_columns_on_rollback", "delete_canonical_values_on_rollback", "automatic_rollback_allowed"):
        if recovery.get(key) is not False:
            errors.append(f"recovery evidence plan must keep {key} false")

    seen_sequences: set[int] = set()
    for step in payload.get("steps", []):
        sequence = step.get("sequence")
        if not isinstance(sequence, int) or sequence in seen_sequences:
            errors.append(f"{step.get('id', '<unknown>')}: invalid sequence")
        if isinstance(sequence, int):
            seen_sequences.add(sequence)
        if step.get("mode") != "plan_only":
            errors.append(f"{step.get('id', '<unknown>')}: step must be plan_only")
        if step.get("owner_gate_required_before_apply") is not True:
            errors.append(f"{step.get('id', '<unknown>')}: owner gate must be required before apply")
        for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
            if step.get(key) is not False:
                errors.append(f"{step.get('id', '<unknown>')}: step must keep {key} false")
        request = step.get("request", {})
        if request.get("base_url") != GRAPH_BASE_URL:
            errors.append(f"{step.get('id', '<unknown>')}: unexpected Graph base URL")
        if not str(request.get("path_template", "")).startswith("/sites/{site-id}/lists"):
            errors.append(f"{step.get('id', '<unknown>')}: request path must target Graph lists")
        if request.get("headers") != {"Content-Type": "application/json"}:
            errors.append(f"{step.get('id', '<unknown>')}: request must not carry auth/secrets in headers")
        request_body = request.get("body", {})
        if step.get("operation") == "extend_choice_column":
            choice = request_body.get("choice", {})
            if choice.get("@odata.type") != CHOICE_COLUMN_ODATA_TYPE:
                errors.append(
                    f"{step.get('id', '<unknown>')}: choice PATCH must declare {CHOICE_COLUMN_ODATA_TYPE}"
                )
        column_definitions = [request_body, *request_body.get("columns", [])]
        for column in column_definitions:
            choice = column.get("choice", {})
            if choice.get("displayAs") == "checkBoxes" and column.get("indexed") is not False:
                errors.append(
                    f"{step.get('id', '<unknown>')}: multi-valued choice columns cannot be indexed"
                )

    guardrails = payload.get("guardrails", {})
    if guardrails.get("offline_only") is not True:
        errors.append("guardrail must be true: offline_only")
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
    return ProcessOntologySchemaApplyPlanValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _create_list_step(
    gap: dict[str, Any],
    choice_catalog: dict[str, list[str]],
    sequence: int,
    template: str,
) -> dict[str, Any]:
    operation = "create_document_library" if template == "documentLibrary" else "create_list"
    columns = [_column_definition(column, choice_catalog) for column in gap.get("planned_columns", [])]
    return _step(
        sequence=sequence,
        source_gap=gap,
        operation=operation,
        method="POST",
        path_template="/sites/{site-id}/lists",
        request_body={
            "displayName": gap["target"],
            "columns": columns,
            "list": {"template": template},
        },
        expected_success_status=201,
        idempotency_check={
            "method": "GET",
            "path_template": "/sites/{site-id}/lists?$filter=displayName eq '{target-display-name}'",
            "match": {"displayName": gap["target"]},
        },
        documentation_reference=GRAPH_LIST_CREATE_DOC,
    )


def _create_column_step(
    gap: dict[str, Any],
    choice_catalog: dict[str, list[str]],
    sequence: int,
) -> dict[str, Any]:
    return _step(
        sequence=sequence,
        source_gap=gap,
        operation="create_column",
        method="POST",
        path_template="/sites/{site-id}/lists/{list-id}/columns",
        request_body=_column_definition(gap["field"], choice_catalog),
        expected_success_status=201,
        idempotency_check={
            "method": "GET",
            "path_template": "/sites/{site-id}/lists/{list-id}/columns?$filter=name eq '{column-name}'",
            "match": {"name": gap["field"]["name"]},
        },
        documentation_reference=GRAPH_COLUMN_CREATE_DOC,
    )


def _extend_choice_step(
    gap: dict[str, Any],
    existing_lists: dict[str, dict[str, Any]],
    choice_catalog: dict[str, list[str]],
    sequence: int,
) -> dict[str, Any]:
    column_name = str(gap["field"]["name"])
    existing_choices = (
        existing_lists.get(gap["target"], {})
        .get("columns_by_name", {})
        .get(column_name, {})
        .get("choices", [])
    )
    planned_choices = _merge_unique([*existing_choices, *choice_catalog.get(column_name, []), *gap.get("missing_choices", [])])
    return _step(
        sequence=sequence,
        source_gap=gap,
        operation="extend_choice_column",
        method="PATCH",
        path_template="/sites/{site-id}/lists/{list-id}/columns/{column-id}",
        request_body={
            "name": column_name,
            "choice": {
                "@odata.type": CHOICE_COLUMN_ODATA_TYPE,
                "allowTextEntry": False,
                "displayAs": "dropDownMenu",
                "choices": planned_choices,
            },
        },
        expected_success_status=200,
        idempotency_check={
            "method": "GET",
            "path_template": "/sites/{site-id}/lists/{list-id}/columns/{column-id}",
            "required_choice_values": gap.get("missing_choices", []),
        },
        documentation_reference=GRAPH_COLUMN_UPDATE_DOC,
    )


def _step(
    *,
    sequence: int,
    source_gap: dict[str, Any],
    operation: str,
    method: str,
    path_template: str,
    request_body: dict[str, Any],
    expected_success_status: int,
    idempotency_check: dict[str, Any],
    documentation_reference: str,
) -> dict[str, Any]:
    return {
        "id": f"step-{sequence:03d}.{source_gap['id']}",
        "sequence": sequence,
        "source_gap_id": source_gap["id"],
        "operation": operation,
        "target": source_gap["target"],
        "mode": "plan_only",
        "required_for_mvp_process_instances": source_gap["required_for_mvp_process_instances"],
        "owner_gate_required_before_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
        "request": {
            "base_url": GRAPH_BASE_URL,
            "method": method,
            "path_template": path_template,
            "headers": {"Content-Type": "application/json"},
            "body": request_body,
        },
        "idempotency_check": idempotency_check,
        "expected_success_status": expected_success_status,
        "documentation_reference": documentation_reference,
        "future_apply_effect": {
            "executes_graph_requests": True,
            "writes_sharepoint": True,
            "changes_sharepoint_schema": True,
            "requires_owner_approval": True,
        },
        "reason": source_gap["reason"],
    }


def _column_definition(field: dict[str, Any], choice_catalog: dict[str, list[str]]) -> dict[str, Any]:
    column_type = field["type"]
    body: dict[str, Any] = {
        "name": field["name"],
        "description": field.get("reason", "Process ontology projection field."),
        "required": bool(field.get("required", False)),
        "hidden": False,
        "indexed": bool(field.get("indexed", field.get("required", False) or field["name"].endswith("Id"))),
    }
    if field.get("enforceUniqueValues") is not None:
        body["enforceUniqueValues"] = bool(field["enforceUniqueValues"])
    if column_type == "text":
        body["text"] = {"allowMultipleLines": False, "maxLength": int(field.get("maxLength", 255))}
    elif column_type == "choice":
        body["choice"] = {
            "allowTextEntry": False,
            "displayAs": "dropDownMenu",
            "choices": list(field.get("choices", choice_catalog.get(field["name"], []))),
        }
    elif column_type == "multiChoice":
        body["indexed"] = False
        body["choice"] = {
            "allowTextEntry": False,
            "displayAs": "checkBoxes",
            "choices": list(field.get("choices", choice_catalog.get(field["name"], []))),
        }
    elif column_type == "boolean":
        body["boolean"] = {}
    elif column_type == "dateTime":
        body["dateTime"] = {"displayAs": "default"}
    else:
        body["text"] = {"allowMultipleLines": False, "maxLength": 255}
        body["description"] = f"{body['description']} Original requested type: {column_type}."
    return body


def _choice_catalog(gap_review: dict[str, Any], process_contract: dict[str, Any]) -> dict[str, list[str]]:
    business_case_choices = list(gap_review.get("business_case_type_ids", []))
    process_phases = process_contract["contract"]["required_process_phases"]
    role_templates = process_contract["contract"]["required_role_templates"]
    return {
        "Vorgangstyp": business_case_choices,
        "BusinessCaseType": business_case_choices,
        "CurrentPhase": process_phases,
        "ProcessPhase": process_phases,
        "ProcessPhaseTemplate": process_phases,
        "RoleTemplate": role_templates,
        "ModelStatus": ["draft", "review", "approved", "superseded", "archived"],
        "AccessPurpose": ["primary_assignment", "temporary_delegation", "readback_audit", "runtime_smoke"],
        "TaskType": ["intake", "draft", "review", "appointment", "register_submission", "completion", "archive"],
        "GateType": ["manual_review", "owner_approval", "external_submission", "evidence_required"],
        "ReviewStatus": ["draft", "in_review", "approved", "rejected", "superseded"],
    }


def _sharepoint_list_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["display_name"]: {
            **item,
            "columns_by_name": {column["name"]: column for column in item.get("columns", [])},
        }
        for item in schema.get("sharepoint", {}).get("lists", [])
    }


def _merge_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
