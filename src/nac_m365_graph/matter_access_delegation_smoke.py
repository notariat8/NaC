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
from .schema import DEFAULT_SCHEMA, load_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_DELEGATION_SMOKE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-delegation-smoke.redacted.json"
)


def run_matter_access_delegation_smoke(
    contract: dict[str, Any],
    schema: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str = "matter-access-delegation-smoke",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        raise ValueError("matter-access-smoke requires workspace_id")
    if not correlation_id:
        raise ValueError("matter-access-smoke requires correlation_id")

    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    contract_errors = validate_matter_access_delegation_contract(contract, schema)
    operations = [] if contract_errors else build_matter_access_plan(contract, schema)
    summary = summarize_matter_access_plan(operations, contract) if operations else _empty_summary(contract)
    workspace_operations = [operation for operation in operations if operation.workspace_id == workspace_id]
    checks = [
        _contract_check(contract_errors),
        _workspace_plan_check(workspace_id, workspace_operations),
        _owner_gate_check(workspace_operations),
        _mcp_tool_contract_check(contract),
        _privacy_boundary_check(contract, operations),
    ]
    errors = [check["message"] for check in checks if check["status"] != "PASSED"]
    status = "PASSED" if not errors else "FAILED"

    return {
        "schema_version": "nac.m365-matter-access-delegation-smoke/v0.1",
        "status": status,
        "generated_at": generated_at,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "contract_id": summary.get("contract_id"),
            "workspace_count": len(schema.get("workspaces", [])) if isinstance(schema.get("workspaces"), list) else 0,
            "operation_count": summary.get("operation_count", 0),
            "workspace_operation_count": len(workspace_operations),
            "list_count": summary.get("list_count", 0),
            "mcp_tool_contract_count": summary.get("mcp_tool_contract_count", 0),
            "owner_gated_operations": summary.get("owner_gated_operations", 0),
            "owner_gated_workspace_operations": sum(
                1 for operation in workspace_operations if operation.owner_gate_required
            ),
            "planned_action_count": len(summary.get("by_action", {})) if isinstance(summary.get("by_action"), dict) else 0,
            "graph_rest_only": True,
            "legacy_sharepoint_api_allowed": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "reads_sharepoint_file_content": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
            "owner_gate_required_before_future_apply": True,
        },
        "operation_summary": {
            "by_action": summary.get("by_action", {}),
            "by_tool_contract": summary.get("by_tool_contract", {}),
            "workspace_actions": sorted({operation.action for operation in workspace_operations}),
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
        },
        "errors": errors,
    }


def run_matter_access_delegation_smoke_from_paths(
    *,
    contract_path: Path = DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    schema_path: Path = DEFAULT_SCHEMA,
    workspace_id: str,
    correlation_id: str = "matter-access-delegation-smoke",
) -> dict[str, Any]:
    return run_matter_access_delegation_smoke(
        load_matter_access_delegation_contract(contract_path),
        load_schema(schema_path),
        workspace_id=workspace_id,
        correlation_id=correlation_id,
    )


def write_matter_access_delegation_smoke_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _contract_check(errors: list[str]) -> dict[str, Any]:
    return {
        "id": "contract_valid",
        "status": "PASSED" if not errors else "FAILED",
        "message": "matter access delegation contract validates" if not errors else "; ".join(errors),
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


def _owner_gate_check(workspace_operations: list[Any]) -> dict[str, Any]:
    owner_gated = [operation for operation in workspace_operations if operation.owner_gate_required]
    passed = len(owner_gated) == 3 and all(operation.writes_items for operation in owner_gated)
    return {
        "id": "owner_gated_write_plans",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "write request plans are owner-gated"
            if passed
            else "workspace write request plans are not fully owner-gated"
        ),
        "ownerGatedWorkspaceOperations": len(owner_gated),
        "executesGraphRequests": False,
    }


def _mcp_tool_contract_check(contract: dict[str, Any]) -> dict[str, Any]:
    tools = contract.get("mcp_tool_contracts")
    tool_count = len(tools) if isinstance(tools, list) else 0
    passed = tool_count == 4 and all(
        isinstance(tool, dict)
        and tool.get("server") == "teams-sharepoint-data-mcp"
        and tool.get("mode") == "request_plan_only"
        for tool in tools or []
    )
    return {
        "id": "mcp_tool_contracts",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "MCP tool contracts are request-plan-only"
            if passed
            else "MCP tool contracts are not request-plan-only"
        ),
        "mcpToolContractCount": tool_count,
        "executesGraphRequests": False,
    }


def _privacy_boundary_check(contract: dict[str, Any], operations: list[Any]) -> dict[str, Any]:
    scope = contract.get("scope") if isinstance(contract.get("scope"), dict) else {}
    passed = (
        scope.get("executes_graph_requests_now") is False
        and scope.get("tenant_mutation_allowed_now") is False
        and scope.get("team_membership_mutation_allowed_now") is False
        and scope.get("sharepoint_file_content_read_allowed_now") is False
        and scope.get("matter_payload_storage_allowed_now") is False
        and scope.get("stores_tokens_or_secrets") is False
        and all(not operation.executes_graph_requests_now for operation in operations)
        and all(not operation.reads_files for operation in operations)
    )
    return {
        "id": "privacy_boundary",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "smoke is metadata-only and does not execute Graph"
            if passed
            else "smoke privacy boundary failed"
        ),
        "executesGraphRequests": False,
    }


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
