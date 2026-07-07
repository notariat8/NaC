from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Protocol, TextIO

from .graph_client import GraphHttpError
from .mcp_runtime import (
    DEFAULT_MCP_CONTRACT,
    DEFAULT_NOTARIAL_INTERFACE_INVENTORY_CONTRACT,
    McpGateError,
    McpRuntimeError,
    RuntimeContext,
    is_metadata_inventory_tool,
    load_mcp_contract,
    load_notarial_interface_inventory_contract,
    plan_tool_request,
    run_metadata_inventory_tool,
    validate_mcp_contract,
)
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


MCP_PROTOCOL_VERSION = "2025-11-25"
JSONRPC_VERSION = "2.0"
SERVER_NAME = "teams-sharepoint-data-mcp"
LIVE_READ_TOOLS = {"case_get", "document_list"}


class GraphReadClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...


class McpProtocolError(ValueError):
    def __init__(self, code: int, message: str, data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class TeamsSharePointDataMcpServer:
    def __init__(
        self,
        contract: dict[str, Any],
        provisioned_state: dict[str, Any],
        *,
        interface_inventory_contract: dict[str, Any] | None = None,
        live_read_enabled: bool = False,
        graph_client: GraphReadClient | None = None,
    ) -> None:
        errors = validate_mcp_contract(contract)
        if errors:
            raise McpRuntimeError("; ".join(errors))
        self.contract = contract
        self.provisioned_state = provisioned_state
        self.interface_inventory_contract = interface_inventory_contract or load_notarial_interface_inventory_contract()
        self.live_read_enabled = live_read_enabled
        self.graph_client = graph_client

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        is_notification = "id" not in message
        request_id = message.get("id")
        method = message.get("method")
        try:
            if is_notification:
                return None
            if method == "initialize":
                return _success(request_id, self._initialize_result())
            if method == "tools/list":
                return _success(request_id, {"tools": self.tools()})
            if method == "tools/call":
                return _success(request_id, self._call_tool_result(message.get("params", {})))
            raise McpProtocolError(-32601, f"method not found: {method}")
        except McpProtocolError as exc:
            return _error(request_id, exc.code, exc.message, exc.data)

    def tools(self) -> list[dict[str, Any]]:
        return [_tool_definition(tool) for tool in self.contract["tools"]]

    def _initialize_result(self) -> dict[str, Any]:
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {
                    "listChanged": False,
                }
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "title": self.contract.get("title", "Teams/SharePoint Data MCP"),
                "version": self.contract.get("schema_version", ""),
            },
            "instructions": (
                "Plans Microsoft Graph REST v1.0 requests for Teams-connected "
                "SharePoint list metadata, including optional BPMN viewer metadata "
                "request plans, and serves metadata-only notarial interface "
                "inventory checks. Live reads for case_get and document_list are "
                "available only when the server is started in owner-gated live-read "
                "mode. The adapter never executes write tools or stores tokens."
            ),
        }

    def _call_tool_result(self, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise McpProtocolError(-32602, "tools/call params must be an object")
        tool_name = params.get("name")
        if not isinstance(tool_name, str) or not tool_name:
            raise McpProtocolError(-32602, "tools/call requires params.name")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            raise McpProtocolError(-32602, "tools/call params.arguments must be an object")

        try:
            context = runtime_context_from_call_arguments(arguments)
            tool_arguments = tool_arguments_from_call_arguments(arguments)
            if is_metadata_inventory_tool(self.contract, tool_name):
                inventory_result = run_metadata_inventory_tool(
                    self.contract,
                    self.interface_inventory_contract,
                    context,
                    tool_name,
                    tool_arguments,
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"{tool_name} returned metadata-only inventory data. "
                                "No Microsoft Graph or external BNotK request was executed."
                            ),
                        }
                    ],
                    "structuredContent": {
                        "serverId": SERVER_NAME,
                        **inventory_result.to_dict(),
                    },
                }
            plan = plan_tool_request(
                self.contract,
                self.provisioned_state,
                context,
                tool_name,
                tool_arguments,
            )
        except (McpGateError, McpRuntimeError) as exc:
            return {
                "isError": True,
                "content": [{"type": "text", "text": str(exc)}],
                "structuredContent": {
                    "serverId": SERVER_NAME,
                    "runtimeMode": self._runtime_mode(),
                    "errorType": type(exc).__name__,
                    "message": str(exc),
                    "executesGraphRequests": False,
                },
            }

        if self.live_read_enabled:
            live_read_result = self._live_read_result(tool_name, plan)
            if live_read_result is not None:
                return live_read_result

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"{tool_name} planned as {plan.method} {plan.path}. "
                        "No Microsoft Graph request was executed."
                    ),
                }
            ],
            "structuredContent": {
                "serverId": SERVER_NAME,
                "runtimeMode": self._runtime_mode(),
                "graphBaseUrl": self.contract["graph"]["base_url"],
                "executesGraphRequests": False,
                "requestPlan": plan.to_dict(),
                "runtimeContext": asdict(context),
            },
        }

    def _runtime_mode(self) -> str:
        if self.live_read_enabled:
            return "owner_gated_live_read"
        return "request_planning_only"

    def _live_read_result(self, tool_name: str, plan: Any) -> dict[str, Any] | None:
        if tool_name not in LIVE_READ_TOOLS:
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "owner-gated live-read mode only executes case_get and "
                            "document_list. This tool was not executed."
                        ),
                    }
                ],
                "structuredContent": {
                    "serverId": SERVER_NAME,
                    "runtimeMode": self._runtime_mode(),
                    "graphBaseUrl": self.contract["graph"]["base_url"],
                    "executesGraphRequests": False,
                    "requestPlan": plan.to_dict(),
                    "errorType": "McpLiveReadBlocked",
                    "message": "live-read mode does not execute write or non-read tools",
                },
            }
        if plan.method != "GET" or plan.payload is not None or plan.writes_items:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "live-read mode only executes safe GET request plans"}],
                "structuredContent": {
                    "serverId": SERVER_NAME,
                    "runtimeMode": self._runtime_mode(),
                    "graphBaseUrl": self.contract["graph"]["base_url"],
                    "executesGraphRequests": False,
                    "requestPlan": plan.to_dict(),
                    "errorType": "McpLiveReadBlocked",
                    "message": "planned request is not an allowed read-only Graph GET",
                },
            }
        if self.graph_client is None:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "live-read mode requires a configured Graph REST client"}],
                "structuredContent": {
                    "serverId": SERVER_NAME,
                    "runtimeMode": self._runtime_mode(),
                    "graphBaseUrl": self.contract["graph"]["base_url"],
                    "executesGraphRequests": False,
                    "requestPlan": plan.to_dict(),
                    "errorType": "McpLiveReadMissingClient",
                    "message": "live-read mode requires a configured Graph REST client",
                },
            }
        try:
            graph_response = self.graph_client.get(plan.path)
        except GraphHttpError as exc:
            return {
                "isError": True,
                "content": [{"type": "text", "text": str(exc)}],
                "structuredContent": {
                    "serverId": SERVER_NAME,
                    "runtimeMode": self._runtime_mode(),
                    "graphBaseUrl": self.contract["graph"]["base_url"],
                    "executesGraphRequests": True,
                    "requestPlan": plan.to_dict(),
                    "errorType": "GraphHttpError",
                    "status": exc.status,
                    "message": str(exc),
                },
            }
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"{tool_name} executed as live Graph REST read. No write request was executed.",
                }
            ],
            "structuredContent": {
                "serverId": SERVER_NAME,
                "runtimeMode": self._runtime_mode(),
                "graphBaseUrl": self.contract["graph"]["base_url"],
                "executesGraphRequests": True,
                "requestPlan": plan.to_dict(),
                "graphResponse": graph_response,
            },
        }


def runtime_context_from_call_arguments(arguments: dict[str, Any]) -> RuntimeContext:
    raw_context = arguments.get("context")
    if raw_context is None:
        raw_context = arguments
    if not isinstance(raw_context, dict):
        raise McpRuntimeError("tools/call arguments.context must be an object")
    return RuntimeContext(
        actor_id=str(raw_context.get("actor_id", "")),
        actor_role=str(raw_context.get("actor_role", "")),
        workspace_id=str(raw_context.get("workspace_id", "")),
        purpose=str(raw_context.get("purpose", "")),
        correlation_id=str(raw_context.get("correlation_id", "")),
        case_id=_optional_string(raw_context.get("case_id")),
        role_case_gate=str(raw_context.get("role_case_gate", "closed")),
        write_approved=raw_context.get("write_approved") is True,
    )


def tool_arguments_from_call_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    raw_tool_arguments = arguments.get("arguments")
    if raw_tool_arguments is None:
        return {
            key: value
            for key, value in arguments.items()
            if key
            not in {
                "actor_id",
                "actor_role",
                "workspace_id",
                "purpose",
                "correlation_id",
                "role_case_gate",
                "write_approved",
                "context",
            }
        }
    if not isinstance(raw_tool_arguments, dict):
        raise McpRuntimeError("tools/call arguments.arguments must be an object")
    return raw_tool_arguments


def run_stdio_server(
    contract_path: Path = DEFAULT_MCP_CONTRACT,
    interface_inventory_contract_path: Path = DEFAULT_NOTARIAL_INTERFACE_INVENTORY_CONTRACT,
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
    *,
    live_read_enabled: bool = False,
    graph_client: GraphReadClient | None = None,
) -> int:
    input_stream = input_stream or sys.stdin
    output_stream = output_stream or sys.stdout
    server = TeamsSharePointDataMcpServer(
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        interface_inventory_contract=load_notarial_interface_inventory_contract(interface_inventory_contract_path),
        live_read_enabled=live_read_enabled,
        graph_client=graph_client,
    )
    for line in input_stream:
        if not line.strip():
            continue
        response = _handle_raw_line(server, line)
        if response is None:
            continue
        output_stream.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
        output_stream.flush()
    return 0


def _handle_raw_line(server: TeamsSharePointDataMcpServer, line: str) -> dict[str, Any] | None:
    try:
        message = json.loads(line)
    except json.JSONDecodeError as exc:
        return _error(None, -32700, "parse error", {"detail": str(exc)})
    if not isinstance(message, dict):
        return _error(None, -32600, "invalid request")
    if message.get("jsonrpc") != JSONRPC_VERSION:
        return _error(message.get("id"), -32600, "jsonrpc must be 2.0")
    return server.handle_message(message)


def _tool_definition(tool: dict[str, Any]) -> dict[str, Any]:
    required_inputs = tool.get("required_inputs", [])
    return {
        "name": tool["id"],
        "title": tool["id"].replace("_", " ").title(),
        "description": tool["description"],
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "context": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "actor_id",
                        "actor_role",
                        "workspace_id",
                        "purpose",
                        "correlation_id",
                        "role_case_gate",
                    ],
                    "properties": {
                        "actor_id": {"type": "string"},
                        "actor_role": {"type": "string"},
                        "workspace_id": {"type": "string"},
                        "purpose": {"type": "string"},
                        "correlation_id": {"type": "string"},
                        "case_id": {"type": "string"},
                        "role_case_gate": {"type": "string", "enum": ["open", "closed"]},
                        "write_approved": {"type": "boolean"},
                    },
                },
                "arguments": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": required_inputs,
                    "properties": {
                        name: _json_schema_for_argument(name)
                        for name in required_inputs
                    },
                },
            },
            "required": ["context", "arguments"],
        },
        "annotations": {
            "readOnlyHint": not bool(tool["writes_items"]),
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": False,
        },
    }


def _json_schema_for_argument(name: str) -> dict[str, Any]:
    if name == "requires_notary_approval":
        return {"type": "boolean"}
    return {"type": "string"}


def _optional_string(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


def _success(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def _error(
    request_id: Any,
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "jsonrpc": JSONRPC_VERSION,
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if data is not None:
        payload["error"]["data"] = data
    return payload
