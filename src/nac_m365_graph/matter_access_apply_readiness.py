from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .matter_access_delegation import (
    DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    build_matter_access_plan,
    load_matter_access_delegation_contract,
    summarize_matter_access_plan,
    validate_matter_access_delegation_contract,
)
from .mcp_runtime import DEFAULT_MCP_CONTRACT, load_mcp_contract, validate_mcp_contract
from .schema import DEFAULT_SCHEMA, load_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_APPLY_READINESS_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-apply-readiness.redacted.json"
)

_REQUIRED_ACCESS_FLAGS = {
    "grant_must_include_reason",
    "grant_must_include_valid_from",
    "grant_must_include_valid_until",
    "grant_must_include_approver",
    "grant_must_include_audit_correlation_id",
}
_REQUIRED_GRANT_INPUTS = {
    "grant_id",
    "case_id",
    "from_user",
    "to_user",
    "granted_role",
    "reason",
    "valid_from",
    "valid_until",
    "approved_by",
    "status",
}
_REQUIRED_AUDIT_INPUTS = {
    "event_id",
    "case_id",
    "timestamp",
    "action",
    "object_type",
    "object_id",
}
_FUTURE_APPLY_ACTIONS = {
    "write_deputy_grant_request",
    "append_access_audit_event",
}


def build_matter_access_apply_readiness(
    contract: dict[str, Any],
    schema: dict[str, Any],
    mcp_contract: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str = "matter-access-apply-readiness",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        raise ValueError("matter-access-apply-readiness requires workspace_id")
    if not correlation_id:
        raise ValueError("matter-access-apply-readiness requires correlation_id")

    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contract_errors = validate_matter_access_delegation_contract(contract, schema)
    mcp_errors = validate_mcp_contract(mcp_contract)
    operations = [] if contract_errors else build_matter_access_plan(contract, schema)
    summary = summarize_matter_access_plan(operations, contract) if operations else _empty_summary(contract)
    workspace_operations = [operation for operation in operations if operation.workspace_id == workspace_id]
    future_apply_operations = [
        operation for operation in workspace_operations if operation.action in _FUTURE_APPLY_ACTIONS
    ]

    checks = [
        _contract_check(contract_errors),
        _mcp_contract_check(mcp_errors),
        _workspace_plan_check(workspace_id, workspace_operations),
        _future_apply_operation_check(future_apply_operations),
        _access_decision_gate_check(contract),
        _mcp_apply_tool_check(mcp_contract),
        _privacy_boundary_check(contract, workspace_operations),
    ]
    errors = [check["message"] for check in checks if check["status"] != "PASSED"]
    status = "PASSED" if not errors else "FAILED"

    access = contract.get("access_decision") if isinstance(contract.get("access_decision"), dict) else {}
    return {
        "schema_version": "nac.m365-matter-access-apply-readiness/v0.1",
        "status": status,
        "generated_at": generated_at,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "contract_id": summary.get("contract_id"),
            "future_apply_mode": "owner_gated_graph_rest_item_writes",
            "workspace_operation_count": len(workspace_operations),
            "planned_apply_operation_count": len(future_apply_operations),
            "grant_request_ready": _tool_ready(
                mcp_contract,
                "grant_request",
                list_name="Vertretungsfreigaben",
                method="POST",
                required_inputs=_REQUIRED_GRANT_INPUTS,
            ),
            "audit_append_ready": _tool_ready(
                mcp_contract,
                "audit_append",
                list_name="AuditJournalLite",
                method="POST",
                required_inputs=_REQUIRED_AUDIT_INPUTS,
            ),
            "required_write_approval": True,
            "owner_gate_required": True,
            "role_case_purpose_gate_required": True,
            "reason_required": access.get("grant_must_include_reason") is True,
            "valid_from_required": access.get("grant_must_include_valid_from") is True,
            "valid_until_required": access.get("grant_must_include_valid_until") is True,
            "valid_until_after_valid_from_required": True,
            "approver_required": access.get("grant_must_include_approver") is True,
            "audit_correlation_required": access.get("grant_must_include_audit_correlation_id") is True,
            "automation_may_approve_grant": access.get("automation_may_approve_grant") is True,
            "graph_rest_only": True,
            "legacy_sharepoint_api_allowed": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "reads_sharepoint_file_content": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
        },
        "readiness_boundary": {
            "required_context": sorted(_strings(access.get("required_context"))),
            "required_grant_fields": sorted(_strings(access.get("deputy_grant_fields"))),
            "planned_mcp_tools": ["grant_request", "audit_append"],
            "planned_apply_lists": ["Vertretungsfreigaben", "AuditJournalLite"],
            "future_apply_actions": sorted(_FUTURE_APPLY_ACTIONS),
            "blocked_operations": sorted(_strings(contract.get("blocked_operations"))),
        },
        "checks": checks,
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesMessagePayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
        "errors": errors,
    }


def build_matter_access_apply_readiness_from_paths(
    *,
    contract_path: Path = DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    schema_path: Path = DEFAULT_SCHEMA,
    mcp_contract_path: Path = DEFAULT_MCP_CONTRACT,
    workspace_id: str,
    correlation_id: str = "matter-access-apply-readiness",
) -> dict[str, Any]:
    return build_matter_access_apply_readiness(
        load_matter_access_delegation_contract(contract_path),
        load_schema(schema_path),
        load_mcp_contract(mcp_contract_path),
        workspace_id=workspace_id,
        correlation_id=correlation_id,
    )


def write_matter_access_apply_readiness_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _contract_check(errors: list[str]) -> dict[str, Any]:
    return {
        "id": "delegation_contract_valid",
        "status": "PASSED" if not errors else "FAILED",
        "message": "matter access delegation contract validates" if not errors else "; ".join(errors),
        "executesGraphRequests": False,
    }


def _mcp_contract_check(errors: list[str]) -> dict[str, Any]:
    return {
        "id": "mcp_contract_valid",
        "status": "PASSED" if not errors else "FAILED",
        "message": "teams-sharepoint-data-mcp contract validates" if not errors else "; ".join(errors),
        "executesGraphRequests": False,
    }


def _workspace_plan_check(workspace_id: str, workspace_operations: list[Any]) -> dict[str, Any]:
    passed = len(workspace_operations) == 6 and all(not operation.reads_files for operation in workspace_operations)
    return {
        "id": "workspace_request_plan",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "workspace has six redacted request-plan operations"
            if passed
            else f"workspace {workspace_id!r} does not have six request-plan operations"
        ),
        "workspaceOperationCount": len(workspace_operations),
        "executesGraphRequests": False,
    }


def _future_apply_operation_check(future_apply_operations: list[Any]) -> dict[str, Any]:
    passed = (
        len(future_apply_operations) == 2
        and {operation.action for operation in future_apply_operations} == _FUTURE_APPLY_ACTIONS
        and all(operation.writes_items for operation in future_apply_operations)
        and all(operation.owner_gate_required for operation in future_apply_operations)
    )
    return {
        "id": "future_apply_operations_owner_gated",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "future grant and audit apply operations are owner-gated"
            if passed
            else "future grant and audit apply operations are not owner-gated"
        ),
        "plannedApplyOperationCount": len(future_apply_operations),
        "executesGraphRequests": False,
    }


def _access_decision_gate_check(contract: dict[str, Any]) -> dict[str, Any]:
    access = contract.get("access_decision") if isinstance(contract.get("access_decision"), dict) else {}
    passed = all(access.get(flag) is True for flag in _REQUIRED_ACCESS_FLAGS) and (
        access.get("automation_may_approve_grant") is False
    )
    return {
        "id": "timeboxed_deputy_grant_gate",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "grant requires reason, validity window, approver and audit correlation"
            if passed
            else "grant gate is missing reason, validity, approver or audit correlation requirements"
        ),
        "executesGraphRequests": False,
    }


def _mcp_apply_tool_check(mcp_contract: dict[str, Any]) -> dict[str, Any]:
    grant_ready = _tool_ready(
        mcp_contract,
        "grant_request",
        list_name="Vertretungsfreigaben",
        method="POST",
        required_inputs=_REQUIRED_GRANT_INPUTS,
    )
    audit_ready = _tool_ready(
        mcp_contract,
        "audit_append",
        list_name="AuditJournalLite",
        method="POST",
        required_inputs=_REQUIRED_AUDIT_INPUTS,
    )
    return {
        "id": "mcp_apply_tools_ready",
        "status": "PASSED" if grant_ready and audit_ready else "FAILED",
        "message": (
            "grant_request and audit_append are owner-gated write tools"
            if grant_ready and audit_ready
            else "grant_request or audit_append is not ready as owner-gated write tool"
        ),
        "grantRequestReady": grant_ready,
        "auditAppendReady": audit_ready,
        "executesGraphRequests": False,
    }


def _privacy_boundary_check(contract: dict[str, Any], workspace_operations: list[Any]) -> dict[str, Any]:
    scope = contract.get("scope") if isinstance(contract.get("scope"), dict) else {}
    passed = (
        scope.get("executes_graph_requests_now") is False
        and scope.get("tenant_mutation_allowed_now") is False
        and scope.get("team_membership_mutation_allowed_now") is False
        and scope.get("sharepoint_item_permission_mutation_allowed_now") is False
        and scope.get("sharepoint_file_content_read_allowed_now") is False
        and scope.get("matter_payload_storage_allowed_now") is False
        and scope.get("stores_tokens_or_secrets") is False
        and all(not operation.executes_graph_requests_now for operation in workspace_operations)
        and all(not operation.reads_files for operation in workspace_operations)
    )
    return {
        "id": "privacy_boundary",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "apply readiness is metadata-only and does not execute Graph"
            if passed
            else "apply readiness privacy boundary failed"
        ),
        "executesGraphRequests": False,
    }


def _tool_ready(
    mcp_contract: dict[str, Any],
    tool_id: str,
    *,
    list_name: str,
    method: str,
    required_inputs: set[str],
) -> bool:
    tool = _tool_by_id(mcp_contract).get(tool_id)
    if not isinstance(tool, dict):
        return False
    return (
        tool.get("graph_method") == method
        and tool.get("list_name") == list_name
        and set(_strings(tool.get("required_inputs"))) >= required_inputs
        and tool.get("reads_items") is False
        and tool.get("reads_files") is False
        and tool.get("writes_items") is True
        and tool.get("requires_role_case_purpose_gate") is True
        and tool.get("requires_write_approval") is True
    )


def _tool_by_id(mcp_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tools = mcp_contract.get("tools")
    if not isinstance(tools, list):
        return {}
    return {str(tool.get("id")): tool for tool in tools if isinstance(tool, dict) and isinstance(tool.get("id"), str)}


def _empty_summary(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "contract_id": contract.get("contract_id"),
        "operation_count": 0,
        "by_action": {},
        "by_tool_contract": {},
        "list_count": 0,
        "mcp_tool_contract_count": 0,
        "owner_gated_operations": 0,
    }


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
