from __future__ import annotations

import json
import urllib.parse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-data-mcp.contract.json"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
WRITE_TOOLS = {"case_create", "case_update_status", "task_create", "grant_request", "audit_append"}


class McpRuntimeError(ValueError):
    """Raised when an MCP tool invocation cannot be planned safely."""


class McpGateError(PermissionError):
    """Raised when role, case or purpose gates block an MCP tool invocation."""


@dataclass(frozen=True, slots=True)
class RuntimeContext:
    actor_id: str
    actor_role: str
    workspace_id: str
    purpose: str
    correlation_id: str
    case_id: str | None = None
    role_case_gate: str = "closed"
    write_approved: bool = False


@dataclass(frozen=True, slots=True)
class GraphRequestPlan:
    tool: str
    method: str
    path: str
    list_name: str | None
    payload: dict[str, Any] | None
    reads_items: bool
    reads_files: bool
    writes_items: bool
    owner_gate_required: bool
    role_case_gate_required: bool
    graph_rest_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_mcp_contract(path: Path = DEFAULT_MCP_CONTRACT) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_mcp_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != "nac.m365-teams-sharepoint-data-mcp/v0.1":
        errors.append("teams-sharepoint-data-mcp schema_version is invalid")
    if contract.get("server_id") != "teams-sharepoint-data-mcp":
        errors.append("teams-sharepoint-data-mcp server_id is invalid")
    if contract.get("graph", {}).get("base_url") != GRAPH_BASE:
        errors.append("teams-sharepoint-data-mcp graph.base_url must be Microsoft Graph v1.0")
    if contract.get("graph", {}).get("rest_only") is not True:
        errors.append("teams-sharepoint-data-mcp graph.rest_only must be true")
    if contract.get("runtime_boundary", {}).get("executes_graph_requests") is not False:
        errors.append("teams-sharepoint-data-mcp skeleton must not execute Graph requests")
    if contract.get("runtime_boundary", {}).get("stores_tokens_or_secrets") is not False:
        errors.append("teams-sharepoint-data-mcp must not store tokens or secrets")
    if contract.get("runtime_boundary", {}).get("reads_sharepoint_file_content") is not False:
        errors.append("teams-sharepoint-data-mcp must not read SharePoint file content")

    tools = _tools_by_id(contract)
    required = {
        "case_get",
        "case_create",
        "case_update_status",
        "task_create",
        "grant_request",
        "audit_append",
        "document_list",
    }
    missing = sorted(required - set(tools))
    for tool_id in missing:
        errors.append(f"teams-sharepoint-data-mcp missing tool {tool_id}")
    for tool_id, tool in sorted(tools.items()):
        path_template = tool.get("graph_path_template", "")
        if not isinstance(path_template, str) or not path_template.startswith("/sites/{site-id}/"):
            errors.append(f"teams-sharepoint-data-mcp {tool_id} graph_path_template must target /sites/{{site-id}}")
        if "_api" in path_template or "graphbeta" in path_template:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} uses a blocked endpoint marker")
        if tool.get("writes_items") is True and tool.get("requires_write_approval") is not True:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} writes must require write approval")
        if tool.get("requires_role_case_purpose_gate") is not True:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} must require role/case/purpose gate")
    return errors


def build_tool_manifest(contract: dict[str, Any] | None = None) -> dict[str, Any]:
    contract = contract or load_mcp_contract()
    return {
        "serverId": contract["server_id"],
        "status": contract["status"],
        "graphBaseUrl": contract["graph"]["base_url"],
        "graphRestOnly": contract["graph"]["rest_only"],
        "executesGraphRequests": contract["runtime_boundary"]["executes_graph_requests"],
        "tools": [
            {
                "name": tool["id"],
                "description": tool["description"],
                "listName": tool["list_name"],
                "method": tool["graph_method"],
                "readsItems": tool["reads_items"],
                "readsFiles": tool["reads_files"],
                "writesItems": tool["writes_items"],
                "requiresRoleCasePurposeGate": tool["requires_role_case_purpose_gate"],
                "requiresWriteApproval": tool["requires_write_approval"],
                "requiredInputs": tool.get("required_inputs", []),
            }
            for tool in contract["tools"]
        ],
    }


def plan_tool_request(
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    context: RuntimeContext,
    tool_name: str,
    arguments: dict[str, Any],
) -> GraphRequestPlan:
    tools = _tools_by_id(contract)
    tool = tools.get(tool_name)
    if tool is None:
        raise McpRuntimeError(f"unknown teams-sharepoint-data-mcp tool: {tool_name}")
    _validate_context(context, bool(tool.get("writes_items")))
    _validate_required_inputs(tool, arguments)

    workspace = _workspace_by_id(provisioned_state, context.workspace_id)
    site_id = workspace["site_id"]
    list_name = tool.get("list_name")
    list_id = _list_id(workspace, list_name) if isinstance(list_name, str) else None
    method = str(tool["graph_method"])
    path = _render_graph_path(tool, site_id, list_id, context, arguments)
    payload = _payload_for_tool(tool_name, context, arguments)
    _assert_graph_rest_path(path)
    return GraphRequestPlan(
        tool=tool_name,
        method=method,
        path=path,
        list_name=list_name,
        payload=payload,
        reads_items=bool(tool["reads_items"]),
        reads_files=bool(tool["reads_files"]),
        writes_items=bool(tool["writes_items"]),
        owner_gate_required=bool(tool["requires_write_approval"]),
        role_case_gate_required=bool(tool["requires_role_case_purpose_gate"]),
    )


def _tools_by_id(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        tool["id"]: tool
        for tool in contract.get("tools", [])
        if isinstance(tool, dict) and isinstance(tool.get("id"), str)
    }


def _validate_context(context: RuntimeContext, writes_items: bool) -> None:
    required = {
        "actor_id": context.actor_id,
        "actor_role": context.actor_role,
        "workspace_id": context.workspace_id,
        "purpose": context.purpose,
        "correlation_id": context.correlation_id,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise McpGateError("missing runtime context: " + ", ".join(missing))
    if context.role_case_gate != "open":
        raise McpGateError("role/case/purpose gate is closed")
    if writes_items and not context.write_approved:
        raise McpGateError("write tool requires explicit write approval")


def _validate_required_inputs(tool: dict[str, Any], arguments: dict[str, Any]) -> None:
    missing = [
        name
        for name in tool.get("required_inputs", [])
        if name not in arguments or arguments[name] is None or arguments[name] == ""
    ]
    if missing:
        raise McpRuntimeError(f"{tool['id']} missing required inputs: " + ", ".join(missing))


def _workspace_by_id(provisioned_state: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    for workspace in provisioned_state.get("workspaces", []):
        if isinstance(workspace, dict) and workspace.get("id") == workspace_id:
            return workspace
    raise McpRuntimeError(f"unknown workspace_id: {workspace_id}")


def _list_id(workspace: dict[str, Any], list_name: str) -> str:
    list_state = workspace.get("lists", {}).get(list_name)
    if not isinstance(list_state, dict) or not isinstance(list_state.get("id"), str):
        raise McpRuntimeError(f"workspace {workspace.get('id')} missing list {list_name}")
    return list_state["id"]


def _render_graph_path(
    tool: dict[str, Any],
    site_id: str,
    list_id: str | None,
    context: RuntimeContext,
    arguments: dict[str, Any],
) -> str:
    path = str(tool["graph_path_template"])
    path = path.replace("{site-id}", _quote_segment(site_id, safe=","))
    if list_id is not None:
        path = path.replace("{list-id}", _quote_segment(list_id))
    if "{item-id}" in path:
        path = path.replace("{item-id}", _quote_segment(str(arguments["item_id"])))
    if "{case-id-filter}" in path:
        case_id = str(arguments.get("case_id") or context.case_id or "")
        if not case_id:
            raise McpRuntimeError(f"{tool['id']} requires case_id")
        path = path.replace("{case-id-filter}", _quote_query_value(case_id))
    return path


def _payload_for_tool(
    tool_name: str,
    context: RuntimeContext,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    if tool_name in {"case_get", "document_list"}:
        return None
    if tool_name == "case_update_status":
        return {"Status": arguments["status"]}
    if tool_name == "case_create":
        return {
            "fields": {
                "NacCaseId": arguments["case_id"],
                "Aktenzeichen": arguments["aktenzeichen"],
                "Vorgangstyp": arguments["vorgangstyp"],
                "Status": arguments["status"],
                "NotarTeam": arguments["notar_team"],
                "Vertraulichkeitsstufe": arguments["vertraulichkeitsstufe"],
                "NacWorkflowVersion": arguments["nac_workflow_version"],
                "KgVersion": arguments["kg_version"],
            }
        }
    if tool_name == "task_create":
        return {
            "fields": {
                "NacTaskId": arguments["task_id"],
                "NacCaseId": arguments["case_id"],
                "BpmnStepCode": arguments["bpmn_step_code"],
                "Status": arguments["status"],
                "RequiresNotaryApproval": arguments["requires_notary_approval"],
            }
        }
    if tool_name == "grant_request":
        return {
            "fields": {
                "GrantId": arguments["grant_id"],
                "NacCaseId": arguments["case_id"],
                "FromUser": arguments["from_user"],
                "ToUser": arguments["to_user"],
                "GrantedRole": arguments["granted_role"],
                "Reason": arguments["reason"],
                "ValidFrom": arguments["valid_from"],
                "ValidUntil": arguments["valid_until"],
                "ApprovedBy": arguments["approved_by"],
                "Status": arguments["status"],
                "AuditCorrelationId": context.correlation_id,
            }
        }
    if tool_name == "audit_append":
        return {
            "fields": {
                "EventId": arguments["event_id"],
                "Timestamp": arguments["timestamp"],
                "NacCaseId": arguments["case_id"],
                "Action": arguments["action"],
                "ObjectType": arguments["object_type"],
                "ObjectId": arguments["object_id"],
                "Reason": arguments.get("reason", ""),
                "CorrelationId": context.correlation_id,
            }
        }
    raise McpRuntimeError(f"payload mapping missing for tool: {tool_name}")


def _assert_graph_rest_path(path: str) -> None:
    if not path.startswith("/"):
        raise McpRuntimeError("Graph REST path must start with /")
    if "_api" in path or "graphbeta" in path or path.startswith("/beta"):
        raise McpRuntimeError("blocked non-v1.0 or legacy SharePoint path")


def _quote_segment(value: str, safe: str = "") -> str:
    return urllib.parse.quote(value, safe=safe)


def _quote_query_value(value: str) -> str:
    return urllib.parse.quote(value.replace("'", "''"), safe="")
