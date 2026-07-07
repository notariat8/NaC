from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .mcp_runtime import (
    DEFAULT_MCP_CONTRACT,
    DEFAULT_NOTARIAL_INTERFACE_INVENTORY_CONTRACT,
    load_mcp_contract,
    load_notarial_interface_inventory_contract,
)
from .mcp_stdio import TeamsSharePointDataMcpServer
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_INVENTORY_SMOKE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "mcp-inventory-smoke.redacted.json"
)
DEFAULT_METADATA_INTERFACE_ID = "xjustiz_331"
DEFAULT_OWNER_GATED_INTERFACE_ID = "ben"
DEFAULT_METADATA_OPERATION = "metadata_inventory"
DEFAULT_OWNER_GATED_OPERATION = "productive_ben_send_or_fetch"


def run_mcp_inventory_smoke(
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    inventory_contract: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str = "mcp-inventory-smoke",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        raise ValueError("mcp-inventory-smoke requires workspace_id")
    if not correlation_id:
        raise ValueError("mcp-inventory-smoke requires correlation_id")

    server = TeamsSharePointDataMcpServer(
        contract,
        provisioned_state,
        interface_inventory_contract=inventory_contract,
    )
    context = {
        "actor_id": "nac-mcp-inventory-smoke",
        "actor_role": "runtime_service",
        "workspace_id": workspace_id,
        "purpose": "mcp_inventory_smoke",
        "correlation_id": correlation_id,
        "role_case_gate": "open",
        "write_approved": False,
    }
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    inventory_list = _call_tool(server, "notarial_interface_inventory_list", context, {})
    metadata_check = _call_tool(
        server,
        "notarial_interface_boundary_check",
        context,
        {
            "interface_id": DEFAULT_METADATA_INTERFACE_ID,
            "requested_operation": DEFAULT_METADATA_OPERATION,
        },
    )
    owner_gate_check = _call_tool(
        server,
        "notarial_interface_boundary_check",
        context,
        {
            "interface_id": DEFAULT_OWNER_GATED_INTERFACE_ID,
            "requested_operation": DEFAULT_OWNER_GATED_OPERATION,
        },
    )
    closed_gate_context = {**context, "role_case_gate": "closed"}
    closed_gate = _call_tool(server, "notarial_interface_inventory_list", closed_gate_context, {})

    checks = [
        _summarize_inventory_list(inventory_list),
        _summarize_boundary_check(metadata_check, expected_status="allowed_metadata_only"),
        _summarize_boundary_check(owner_gate_check, expected_status="owner_gate_required"),
        _summarize_closed_gate(closed_gate),
    ]
    errors = [check["message"] for check in checks if check["status"] != "PASSED"]
    graph_executed = any(check.get("executesGraphRequests") is True for check in checks)
    if graph_executed:
        errors.append("mcp-inventory-smoke must not execute Microsoft Graph requests")

    status = "PASSED" if not errors else "FAILED"
    return {
        "status": status,
        "generated_at": generated_at,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "tool_call_count": len(checks),
            "inventory_tool_count": 2,
            "interface_count": checks[0].get("interfaceCount", 0),
            "metadata_boundary_status": checks[1].get("boundaryStatus"),
            "owner_gated_boundary_status": checks[2].get("boundaryStatus"),
            "closed_gate_blocks": checks[3].get("closedGateBlocks") is True,
            "graph_requests_executed": graph_executed,
            "external_bnotk_calls_executed": False,
            "raw_source_content_stored": False,
        },
        "checks": checks,
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMessagePayloads": False,
            "executesGraphRequests": graph_executed,
            "callsExternalBnotkSystems": False,
        },
        "errors": errors,
    }


def run_mcp_inventory_smoke_from_paths(
    *,
    contract_path: Path = DEFAULT_MCP_CONTRACT,
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    interface_inventory_contract_path: Path = DEFAULT_NOTARIAL_INTERFACE_INVENTORY_CONTRACT,
    workspace_id: str,
    correlation_id: str = "mcp-inventory-smoke",
) -> dict[str, Any]:
    return run_mcp_inventory_smoke(
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        load_notarial_interface_inventory_contract(interface_inventory_contract_path),
        workspace_id=workspace_id,
        correlation_id=correlation_id,
    )


def write_mcp_inventory_smoke_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _call_tool(
    server: TeamsSharePointDataMcpServer,
    tool_name: str,
    context: dict[str, Any],
    arguments: dict[str, Any],
) -> dict[str, Any]:
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": f"mcp-inventory-smoke-{tool_name}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {
                    "context": context,
                    "arguments": arguments,
                },
            },
        }
    )
    if response is None:
        raise RuntimeError(f"{tool_name} did not receive a JSON-RPC response")
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError(f"{tool_name} response did not contain a result object")
    return result


def _summarize_inventory_list(result: dict[str, Any]) -> dict[str, Any]:
    structured = _dict(result.get("structuredContent"))
    interfaces = structured.get("interfaces")
    interface_count = len(interfaces) if isinstance(interfaces, list) else 0
    privacy = _dict(structured.get("privacy"))
    passed = (
        result.get("isError") is not True
        and structured.get("tool") == "notarial_interface_inventory_list"
        and structured.get("executes_graph_requests") is False
        and interface_count > 0
        and privacy.get("metadataOnly") is True
        and privacy.get("storesSourceFullText") is False
        and privacy.get("storesRawXsd") is False
        and privacy.get("storesCredentials") is False
        and privacy.get("storesMatterData") is False
        and privacy.get("callsExternalBnotkSystems") is False
    )
    return {
        "tool": "notarial_interface_inventory_list",
        "status": "PASSED" if passed else "FAILED",
        "message": "inventory list returned metadata-only rows" if passed else "inventory list metadata-only check failed",
        "interfaceCount": interface_count,
        "executesGraphRequests": structured.get("executes_graph_requests") is True,
        "runtimeMode": structured.get("runtime_mode"),
    }


def _summarize_boundary_check(result: dict[str, Any], *, expected_status: str) -> dict[str, Any]:
    structured = _dict(result.get("structuredContent"))
    boundary = _dict(structured.get("boundary_check"))
    boundary_status = boundary.get("boundaryStatus")
    passed = (
        result.get("isError") is not True
        and structured.get("tool") == "notarial_interface_boundary_check"
        and structured.get("executes_graph_requests") is False
        and boundary_status == expected_status
        and boundary.get("executesGraphRequests") is False
        and boundary.get("externalBnotkCallAllowed") is False
        and boundary.get("liveConnectorApplyAllowed") is False
    )
    if expected_status == "allowed_metadata_only":
        passed = passed and boundary.get("allowedNow") is True and boundary.get("ownerGateRequired") is False
    if expected_status == "owner_gate_required":
        passed = passed and boundary.get("allowedNow") is False and boundary.get("ownerGateRequired") is True
    return {
        "tool": "notarial_interface_boundary_check",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            f"boundary check returned {expected_status}"
            if passed
            else f"boundary check did not return {expected_status}"
        ),
        "interfaceId": boundary.get("interfaceId"),
        "requestedOperation": boundary.get("requestedOperation"),
        "boundaryStatus": boundary_status,
        "ownerGateRequired": boundary.get("ownerGateRequired"),
        "executesGraphRequests": structured.get("executes_graph_requests") is True
        or boundary.get("executesGraphRequests") is True,
    }


def _summarize_closed_gate(result: dict[str, Any]) -> dict[str, Any]:
    structured = _dict(result.get("structuredContent"))
    passed = (
        result.get("isError") is True
        and structured.get("errorType") == "McpGateError"
        and structured.get("executesGraphRequests") is False
    )
    return {
        "tool": "notarial_interface_inventory_list",
        "status": "PASSED" if passed else "FAILED",
        "message": (
            "closed role/case/purpose gate blocked metadata inventory"
            if passed
            else "closed role/case/purpose gate did not block metadata inventory"
        ),
        "closedGateBlocks": passed,
        "executesGraphRequests": structured.get("executesGraphRequests") is True,
        "errorType": structured.get("errorType"),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
