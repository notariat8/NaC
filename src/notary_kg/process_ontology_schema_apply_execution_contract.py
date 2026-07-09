from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_schema_apply_readiness import (
    REQUIRED_PERMISSION,
    build_process_ontology_sharepoint_schema_apply_readiness,
)


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-execution-contract/v0.1"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_execution_contract"


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyExecutionContractValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_execution_contract(repo_root: Path) -> dict[str, Any]:
    readiness = build_process_ontology_sharepoint_schema_apply_readiness(repo_root)
    phase_order = list(readiness["ordering"]["phase_order"])
    workspace_contracts = [_workspace_contract(workspace, phase_order) for workspace in readiness["workspaces"]]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_owner_gated_execution_contract",
        "source": {
            "apply_readiness_schema": readiness["schema_version"],
            "apply_readiness_status": readiness["status"],
            "apply_readiness_contract_id": readiness["contract_id"],
            "graph_base_url": readiness["source"]["graph_base_url"],
            "graph_rest_only": readiness["source"]["graph_rest_only"],
            "legacy_sharepoint_api_allowed": readiness["source"]["legacy_sharepoint_api_allowed"],
            "graph_sdk_allowed": readiness["source"]["graph_sdk_allowed"],
        },
        "summary": {
            "workspace_count": len(workspace_contracts),
            "execution_phase_count": len(phase_order),
            "workspace_apply_unit_count": sum(
                contract["summary"]["workspace_apply_unit_count"] for contract in workspace_contracts
            ),
            "mutating_operation_count": sum(
                contract["summary"]["mutating_operation_count"] for contract in workspace_contracts
            ),
            "dynamic_resolution_count": sum(
                contract["summary"]["dynamic_resolution_count"] for contract in workspace_contracts
            ),
            "owner_gate_required_now": False,
            "owner_gate_required_before_live_apply": True,
            "live_apply_contract_status": "READY_FOR_OWNER_GATED_EXECUTION",
        },
        "permission_gate": {
            "required_application_permission": REQUIRED_PERMISSION,
            "permission_present_in_readiness": readiness["permission_readiness"][
                "permission_present_in_provisioned_state"
            ],
            "application_owner_path_required": True,
            "delegated_user_context_allowed": False,
            "technical_owner_user": "funktion8@funktion8.de",
        },
        "execution_boundary": {
            "mode": "contract_only",
            "future_runner_must_require_owner_approval": True,
            "future_runner_must_require_explicit_live_flag": True,
            "future_runner_required_flags": [
                "--owner-approved",
                "--execute-live-schema-apply",
                "--write-redacted-evidence",
            ],
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "graph_rest_only": True,
            "graph_sdk_allowed": False,
            "legacy_sharepoint_api_allowed": False,
        },
        "execution_phases": [_phase_contract(phase, workspace_contracts) for phase in phase_order],
        "workspace_contracts": workspace_contracts,
        "stop_rules": {
            "stop_on_first_failed_preflight": True,
            "stop_on_first_unexpected_status": True,
            "stop_if_idempotency_readback_is_ambiguous": True,
            "stop_if_required_list_id_missing": True,
            "stop_if_runtime_permission_missing": True,
            "automatic_rollback_allowed": False,
            "manual_owner_review_required_after_failure": True,
        },
        "evidence_contract": {
            "redacted_evidence_required": True,
            "raw_graph_response_allowed": False,
            "tokens_or_auth_headers_allowed": False,
            "minimum_evidence_items": [
                "owner_approval_reference",
                "workspace_execution_summary",
                "per_step_preflight_result",
                "per_mutation_expected_status",
                "per_mutation_readback_result",
                "stop_rule_evaluation",
                "post_apply_schema_snapshot_metadata",
            ],
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
            "recommended_slice": "process_ontology_sharepoint_schema_apply_runner_dry_run",
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
    validation = validate_process_ontology_sharepoint_schema_apply_execution_contract(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_process_ontology_sharepoint_schema_apply_execution_contract(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyExecutionContractValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("mode") != "offline_owner_gated_execution_contract":
        errors.append("execution contract must remain offline")

    source = payload.get("source", {})
    if source.get("apply_readiness_status") != "PASSED":
        errors.append("apply readiness must pass before execution contract")
    if source.get("graph_rest_only") is not True:
        errors.append("Graph REST must remain the only API surface")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")
    if source.get("graph_sdk_allowed") is not False:
        errors.append("Graph SDK must remain blocked")

    summary = payload.get("summary", {})
    if summary.get("workspace_count", 0) < 2:
        errors.append("execution contract must cover both notary workspaces")
    if summary.get("execution_phase_count") != 8:
        errors.append("execution contract must keep the eight readiness phases")
    if summary.get("workspace_apply_unit_count", 0) < 60:
        errors.append("execution contract must cover expanded workspace apply units")
    if summary.get("mutating_operation_count") != summary.get("workspace_apply_unit_count"):
        errors.append("each apply unit is a future mutating operation and must be counted")
    if summary.get("owner_gate_required_before_live_apply") is not True:
        errors.append("live apply must require owner gate")
    if summary.get("live_apply_contract_status") != "READY_FOR_OWNER_GATED_EXECUTION":
        errors.append("unexpected live apply contract status")

    permission_gate = payload.get("permission_gate", {})
    if permission_gate.get("required_application_permission") != REQUIRED_PERMISSION:
        errors.append("unexpected required application permission")
    if permission_gate.get("permission_present_in_readiness") is not True:
        errors.append("required permission must be present in readiness")
    if permission_gate.get("application_owner_path_required") is not True:
        errors.append("application owner path must be required")
    if permission_gate.get("delegated_user_context_allowed") is not False:
        errors.append("delegated user-context apply must remain blocked")

    boundary = payload.get("execution_boundary", {})
    if boundary.get("mode") != "contract_only":
        errors.append("execution boundary must be contract_only")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if boundary.get(key) is not False:
            errors.append(f"execution boundary must keep {key} false")
    for key in ("future_runner_must_require_owner_approval", "future_runner_must_require_explicit_live_flag"):
        if boundary.get(key) is not True:
            errors.append(f"execution boundary must require {key}")
    for required_flag in ("--owner-approved", "--execute-live-schema-apply", "--write-redacted-evidence"):
        if required_flag not in boundary.get("future_runner_required_flags", []):
            errors.append(f"missing required future runner flag: {required_flag}")

    if len(payload.get("execution_phases", [])) != 8:
        errors.append("execution phase contracts must include eight phases")
    for phase in payload.get("execution_phases", []):
        if phase.get("mode") != "contract_only":
            errors.append(f"{phase.get('phase', '<unknown>')}: phase must be contract_only")
        if phase.get("writes_sharepoint") is not False:
            errors.append(f"{phase.get('phase', '<unknown>')}: phase must not write SharePoint")

    for workspace in payload.get("workspace_contracts", []):
        if workspace.get("site_id_status") != "known":
            errors.append(f"{workspace.get('workspace_id', '<unknown>')}: site id must be known")
        if workspace.get("summary", {}).get("missing_required_list_id_count") != 0:
            errors.append(f"{workspace.get('workspace_id', '<unknown>')}: required list id missing")
        for phase in workspace.get("phase_contracts", []):
            if phase.get("owner_gate_required_before_live_apply") is not True:
                errors.append(f"{workspace.get('workspace_id', '<unknown>')}: missing owner gate")
            if phase.get("writes_sharepoint") is not False:
                errors.append(f"{workspace.get('workspace_id', '<unknown>')}: phase must not write now")

    stop_rules = payload.get("stop_rules", {})
    for key in (
        "stop_on_first_failed_preflight",
        "stop_on_first_unexpected_status",
        "stop_if_idempotency_readback_is_ambiguous",
        "stop_if_required_list_id_missing",
        "stop_if_runtime_permission_missing",
        "manual_owner_review_required_after_failure",
    ):
        if stop_rules.get(key) is not True:
            errors.append(f"stop rule must be true: {key}")
    if stop_rules.get("automatic_rollback_allowed") is not False:
        errors.append("automatic rollback must remain blocked")

    evidence = payload.get("evidence_contract", {})
    if evidence.get("redacted_evidence_required") is not True:
        errors.append("redacted evidence must be required")
    for key in ("raw_graph_response_allowed", "tokens_or_auth_headers_allowed"):
        if evidence.get(key) is not False:
            errors.append(f"evidence contract must keep {key} false")

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
    return ProcessOntologySchemaApplyExecutionContractValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def _workspace_contract(workspace: dict[str, Any], phase_order: list[str]) -> dict[str, Any]:
    apply_units = list(workspace["apply_units"])
    phase_contracts = [_workspace_phase_contract(workspace, phase, apply_units) for phase in phase_order]
    return {
        "workspace_id": workspace["workspace_id"],
        "team_display_name": workspace["team_display_name"],
        "site_id_status": workspace["site_id_status"],
        "site_id": workspace.get("site_id"),
        "site_url": workspace.get("site_url"),
        "summary": {
            "workspace_apply_unit_count": workspace["summary"]["workspace_apply_unit_count"],
            "mutating_operation_count": len(apply_units),
            "dynamic_resolution_count": workspace["summary"]["dynamic_resource_resolution_count"],
            "missing_required_list_id_count": workspace["summary"]["missing_required_list_id_count"],
        },
        "phase_contracts": phase_contracts,
    }


def _workspace_phase_contract(
    workspace: dict[str, Any],
    phase: str,
    apply_units: list[dict[str, Any]],
) -> dict[str, Any]:
    selected = _phase_units(phase, apply_units)
    return {
        "phase": phase,
        "mode": "contract_only",
        "owner_gate_required_before_live_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
        "unit_count": len(selected),
        "operation_counts": _operation_counts(selected),
        "required_readbacks": _required_readbacks(phase),
    }


def _phase_contract(phase: str, workspace_contracts: list[dict[str, Any]]) -> dict[str, Any]:
    workspace_phase_count = 0
    unit_count = 0
    for workspace in workspace_contracts:
        for workspace_phase in workspace["phase_contracts"]:
            if workspace_phase["phase"] == phase:
                workspace_phase_count += 1
                unit_count += workspace_phase["unit_count"]
    return {
        "phase": phase,
        "mode": "contract_only",
        "workspace_phase_count": workspace_phase_count,
        "unit_count": unit_count,
        "owner_gate_required_before_live_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
    }


def _phase_units(phase: str, apply_units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if phase == "create_optional_process_projection_resources":
        return [
            unit
            for unit in apply_units
            if unit["operation"] in {"create_list", "create_document_library"}
        ]
    if phase == "create_missing_process_columns":
        return [unit for unit in apply_units if unit["operation"] == "create_column"]
    if phase == "extend_choice_columns":
        return [unit for unit in apply_units if unit["operation"] == "extend_choice_column"]
    if phase in {
        "resolve_workspace_site_ids",
        "verify_required_list_ids",
        "resolve_choice_column_ids",
        "readback_schema_metadata",
        "write_redacted_evidence",
    }:
        return []
    return []


def _operation_counts(apply_units: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for unit in apply_units:
        operation = str(unit["operation"])
        counts[operation] = counts.get(operation, 0) + 1
    return counts


def _required_readbacks(phase: str) -> list[str]:
    mapping = {
        "resolve_workspace_site_ids": ["site_metadata"],
        "verify_required_list_ids": ["required_list_metadata"],
        "create_optional_process_projection_resources": ["created_or_existing_list_metadata"],
        "create_missing_process_columns": ["created_or_existing_column_metadata"],
        "resolve_choice_column_ids": ["choice_column_metadata"],
        "extend_choice_columns": ["updated_choice_column_metadata"],
        "readback_schema_metadata": ["post_apply_schema_snapshot_metadata"],
        "write_redacted_evidence": ["redacted_evidence_artifact"],
    }
    return mapping.get(phase, [])
