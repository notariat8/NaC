from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_schema_apply_plan import (
    GRAPH_BASE_URL,
    build_process_ontology_sharepoint_schema_apply_plan,
)


PROVISIONED_STATE_PATH = Path("deploy/m365/teams-sharepoint/nac-mvp.provisioned.f8.json")
SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-readiness/v0.2"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_readiness"
REQUIRED_PERMISSION = "Sites.Manage.All"


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyReadinessValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_readiness(repo_root: Path) -> dict[str, Any]:
    apply_plan = build_process_ontology_sharepoint_schema_apply_plan(repo_root)
    provisioned = json.loads((repo_root / PROVISIONED_STATE_PATH).read_text(encoding="utf-8"))
    workspaces = [_workspace_readiness(workspace, apply_plan["steps"]) for workspace in provisioned["workspaces"]]
    total_step_count = sum(workspace["summary"]["workspace_apply_unit_count"] for workspace in workspaces)
    missing_required_list_ids = sum(workspace["summary"]["missing_required_list_id_count"] for workspace in workspaces)
    dynamic_resolution_count = sum(workspace["summary"]["dynamic_resource_resolution_count"] for workspace in workspaces)
    known_list_id_count = sum(workspace["summary"]["known_required_list_id_count"] for workspace in workspaces)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_apply_readiness",
        "source": {
            "apply_plan_schema": apply_plan["schema_version"],
            "apply_plan_status": apply_plan["status"],
            "apply_plan_step_count": apply_plan["summary"]["total_step_count"],
            "apply_plan_sha256": _payload_sha256(apply_plan),
            "live_execution_approval_state": apply_plan["summary"]["live_execution_approval_state"],
            "provisioned_state": str(PROVISIONED_STATE_PATH),
            "provisioned_state_version": provisioned["state_version"],
            "tenant_id_present": bool(provisioned.get("tenant", {}).get("tenant_id")),
            "graph_base_url": provisioned["graph"]["base_url"],
            "graph_rest_only": provisioned["graph"]["rest_only"],
            "legacy_sharepoint_api_allowed": provisioned["graph"]["legacy_sharepoint_api_allowed"],
            "graph_sdk_allowed": provisioned["graph"]["sdk_allowed"],
        },
        "summary": {
            "workspace_count": len(workspaces),
            "apply_plan_step_count": apply_plan["summary"]["total_step_count"],
            "workspace_apply_unit_count": total_step_count,
            "known_site_id_count": sum(1 for workspace in workspaces if workspace["site_id_status"] == "known"),
            "known_required_list_id_count": known_list_id_count,
            "missing_required_list_id_count": missing_required_list_ids,
            "dynamic_resource_resolution_count": dynamic_resolution_count,
            "owner_gate_required_now": False,
            "owner_gate_required_before_live_apply": True,
            "live_apply_readiness": "OWNER_GATE_REQUIRED",
        },
        "permission_readiness": {
            "required_application_permission": REQUIRED_PERMISSION,
            "permission_source": "deploy/m365/teams-sharepoint/nac-mvp.provisioned.f8.json admin_applications.graph_bootstrap_app.application_permissions",
            "permission_present_in_provisioned_state": _permission_present(provisioned, REQUIRED_PERMISSION),
            "delegated_user_context_allowed_for_live_apply": False,
            "application_owner_path_required": True,
        },
        "recovery_evidence_plan": dict(apply_plan["recovery_evidence_plan"]),
        "ordering": {
            "phase_order": [
                "resolve_workspace_site_ids",
                "verify_required_list_ids",
                "create_required_runtime_projection_resources",
                "create_missing_process_columns",
                "resolve_choice_column_ids",
                "extend_choice_columns",
                "readback_schema_metadata",
                "write_redacted_evidence",
            ],
            "idempotency_rule": "Every mutating future request must be preceded by the recorded GET idempotency check.",
            "rollback_rule": "No automatic rollback; failed future apply must stop and emit redacted evidence for owner review.",
        },
        "workspaces": workspaces,
        "apply_boundary": {
            "mode": "offline_readiness_only",
            "owner_gate_required_before_live_apply": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "future_apply_requires_owner_approval": True,
            "future_apply_expected_permission": REQUIRED_PERMISSION,
            "future_apply_endpoint_families": apply_plan["apply_boundary"]["future_apply_endpoint_families"],
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
            "recommended_slice": "process_ontology_sharepoint_schema_owner_gated_apply_decision",
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
    validation = validate_process_ontology_sharepoint_schema_apply_readiness(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def validate_process_ontology_sharepoint_schema_apply_readiness(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyReadinessValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("mode") != "offline_apply_readiness":
        errors.append("readiness must remain offline")

    source = payload.get("source", {})
    if source.get("apply_plan_status") != "PASSED":
        errors.append("apply plan must pass before readiness")
    if source.get("apply_plan_step_count") != payload.get("summary", {}).get("apply_plan_step_count"):
        errors.append("readiness apply-plan count must bind the current plan")
    if not _valid_sha256(source.get("apply_plan_sha256")):
        errors.append("readiness must bind the current apply plan SHA-256")
    if source.get("live_execution_approval_state") != "BLOCKED_PENDING_S6_S7_APPROVAL":
        errors.append("S2 readiness must remain blocked pending S6/S7 approval")
    if source.get("graph_base_url") != GRAPH_BASE_URL:
        errors.append("unexpected Graph base URL")
    if source.get("graph_rest_only") is not True:
        errors.append("Graph REST must remain the only API surface")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")
    if source.get("graph_sdk_allowed") is not False:
        errors.append("Graph SDK must remain blocked")

    summary = payload.get("summary", {})
    if not isinstance(summary.get("apply_plan_step_count"), int) or summary["apply_plan_step_count"] < 0:
        errors.append("readiness apply_plan_step_count must be a non-negative integer")
    if summary.get("workspace_count", 0) < 2:
        errors.append("expected both notary workspaces")
    if summary.get("workspace_apply_unit_count") != summary.get("workspace_count", 0) * summary.get("apply_plan_step_count", 0):
        errors.append("readiness must expand every apply-plan step per workspace")
    if summary.get("missing_required_list_id_count") != 0:
        errors.append("all required MVP list IDs must be known before apply readiness")
    if not isinstance(summary.get("dynamic_resource_resolution_count"), int) or summary["dynamic_resource_resolution_count"] < 0:
        errors.append("dynamic_resource_resolution_count must be a non-negative integer")
    if summary.get("owner_gate_required_before_live_apply") is not True:
        errors.append("live apply must remain owner-gated")
    if summary.get("live_apply_readiness") != "OWNER_GATE_REQUIRED":
        errors.append("readiness must not silently mark live apply as executable")

    recovery = payload.get("recovery_evidence_plan", {})
    if recovery.get("pre_apply_snapshot_required") is not True:
        errors.append("readiness must require a pre-apply schema snapshot")
    if recovery.get("additive_rollback_only") is not True:
        errors.append("readiness rollback must remain additive")
    if recovery.get("automatic_rollback_allowed") is not False:
        errors.append("readiness must block automatic rollback")

    permission = payload.get("permission_readiness", {})
    if permission.get("required_application_permission") != REQUIRED_PERMISSION:
        errors.append("unexpected required permission")
    if permission.get("permission_present_in_provisioned_state") is not True:
        errors.append("required application permission must be visible in provisioned state")
    if permission.get("delegated_user_context_allowed_for_live_apply") is not False:
        errors.append("delegated user context must not be the live apply default")
    if permission.get("application_owner_path_required") is not True:
        errors.append("application owner path must remain required")

    for workspace in payload.get("workspaces", []):
        if workspace.get("site_id_status") != "known":
            errors.append(f"{workspace.get('workspace_id', '<unknown>')}: site id must be known")
        if workspace.get("summary", {}).get("missing_required_list_id_count") != 0:
            errors.append(f"{workspace.get('workspace_id', '<unknown>')}: required list id missing")
        for unit in workspace.get("apply_units", []):
            if unit.get("mode") != "readiness_only":
                errors.append(f"{unit.get('id', '<unknown>')}: unit must be readiness_only")
            for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
                if unit.get(key) is not False:
                    errors.append(f"{unit.get('id', '<unknown>')}: unit must keep {key} false")
            if unit.get("pre_apply_snapshot_required") is not True:
                errors.append(f"{unit.get('id', '<unknown>')}: missing pre-apply snapshot")
            if unit.get("rollback_mode") != "retain_additive_columns_and_values":
                errors.append(f"{unit.get('id', '<unknown>')}: rollback must retain additive data")
            if unit.get("owner_gate_required_before_live_apply") is not True:
                errors.append(f"{unit.get('id', '<unknown>')}: missing owner gate")
            if unit.get("site_id_status") != "known":
                errors.append(f"{unit.get('id', '<unknown>')}: site id must be known")

    apply_boundary = payload.get("apply_boundary", {})
    if apply_boundary.get("mode") != "offline_readiness_only":
        errors.append("apply boundary must remain offline_readiness_only")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if apply_boundary.get(key) is not False:
            errors.append(f"apply boundary must keep {key} false")
    if apply_boundary.get("owner_gate_required_before_live_apply") is not True:
        errors.append("owner gate must be required before live apply")

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
    return ProcessOntologySchemaApplyReadinessValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _workspace_readiness(workspace: dict[str, Any], apply_steps: list[dict[str, Any]]) -> dict[str, Any]:
    list_ids = {name: details["id"] for name, details in workspace.get("lists", {}).items()}
    library_ids = {name: details["id"] for name, details in workspace.get("document_libraries", {}).items()}
    apply_units = [_apply_unit(workspace, list_ids, library_ids, step) for step in apply_steps]
    dynamic_resolution_count = sum(len(unit["dynamic_resolution_required"]) for unit in apply_units)
    missing_required_list_ids = [
        unit["target"]
        for unit in apply_units
        if unit["operation"] in {"create_column", "extend_choice_column"} and unit.get("target_list_id_status") != "known"
    ]
    return {
        "workspace_id": workspace["id"],
        "team_display_name": workspace["team_display_name"],
        "team_id_status": "known" if workspace.get("team_id") else "missing",
        "site_id_status": "known" if workspace.get("site_id") else "missing",
        "site_id": workspace.get("site_id"),
        "site_url": workspace.get("site_url"),
        "known_lists": sorted(list_ids),
        "known_document_libraries": sorted(library_ids),
        "summary": {
            "workspace_apply_unit_count": len(apply_units),
            "known_required_list_id_count": sum(
                1
                for unit in apply_units
                if unit["operation"] in {"create_column", "extend_choice_column"}
                and unit.get("target_list_id_status") == "known"
            ),
            "missing_required_list_id_count": len(set(missing_required_list_ids)),
            "dynamic_resource_resolution_count": dynamic_resolution_count,
        },
        "apply_units": apply_units,
    }


def _apply_unit(
    workspace: dict[str, Any],
    list_ids: dict[str, str],
    library_ids: dict[str, str],
    step: dict[str, Any],
) -> dict[str, Any]:
    target = step["target"]
    target_id = list_ids.get(target) or library_ids.get(target)
    dynamic_resolution_required: list[dict[str, str]] = []
    if step["operation"] in {"create_list", "create_document_library"}:
        dynamic_resolution_required.append(
            {
                "kind": "created_list_id",
                "when": "after_successful_create_or_existing_readback",
                "path_template": "/sites/{site-id}/lists?$filter=displayName eq '{target-display-name}'",
            }
        )
    if step["operation"] == "extend_choice_column":
        dynamic_resolution_required.append(
            {
                "kind": "column_id",
                "when": "before_choice_patch",
                "path_template": "/sites/{site-id}/lists/{list-id}/columns?$filter=name eq '{column-name}'",
            }
        )
    return {
        "id": f"{workspace['id']}.{step['id']}",
        "workspace_id": workspace["id"],
        "source_step_id": step["id"],
        "operation": step["operation"],
        "target": target,
        "mode": "readiness_only",
        "owner_gate_required_before_live_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
        "site_id_status": "known" if workspace.get("site_id") else "missing",
        "target_list_id_status": _target_id_status(step["operation"], target_id),
        "target_list_or_library_id": target_id,
        "dynamic_resolution_required": dynamic_resolution_required,
        "pre_apply_snapshot_required": True,
        "snapshot_scope": ["target_list_metadata", "target_column_definition", "etag_when_available"],
        "rollback_mode": "retain_additive_columns_and_values",
        "preflight_idempotency_check": step["idempotency_check"],
        "future_request_template": {
            "method": step["request"]["method"],
            "path_template": step["request"]["path_template"],
            "expected_success_status": step["expected_success_status"],
        },
    }


def _target_id_status(operation: str, target_id: str | None) -> str:
    if operation in {"create_list", "create_document_library"}:
        return "created_or_resolved_during_owner_gated_apply"
    if target_id:
        return "known"
    return "missing"


def _permission_present(provisioned: dict[str, Any], permission: str) -> bool:
    permissions = (
        provisioned.get("admin_applications", {})
        .get("graph_bootstrap_app", {})
        .get("application_permissions", [])
    )
    return permission in permissions


def _payload_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
