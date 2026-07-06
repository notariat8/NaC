from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .mcp_runtime import DEFAULT_MCP_CONTRACT, load_mcp_contract
from .mcp_stdio import TeamsSharePointDataMcpServer
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_LIVE_READ_SMOKE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "mcp-live-read-smoke.redacted.json"
)
ALLOWED_SMOKE_TOOLS = {"case_get", "document_list"}


class GraphReadClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...


def run_mcp_live_read_smoke(
    client: GraphReadClient,
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    tool_name: str,
    workspace_id: str,
    case_id: str,
    correlation_id: str = "mcp-live-read-smoke",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if tool_name not in ALLOWED_SMOKE_TOOLS:
        raise ValueError("mcp live-read smoke tool must be case_get or document_list")
    if not workspace_id:
        raise ValueError("mcp live-read smoke requires workspace_id")
    if not case_id:
        raise ValueError("mcp live-read smoke requires case_id")

    server = TeamsSharePointDataMcpServer(
        contract,
        provisioned_state,
        live_read_enabled=True,
        graph_client=client,
    )
    response = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": "mcp-live-read-smoke",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": {
                    "context": {
                        "actor_id": "nac-mcp-live-read-smoke",
                        "actor_role": "runtime_service",
                        "workspace_id": workspace_id,
                        "purpose": "mcp_live_read_smoke",
                        "correlation_id": correlation_id,
                        "case_id": case_id,
                        "role_case_gate": "open",
                        "write_approved": False,
                    },
                    "arguments": {"case_id": case_id},
                },
            },
        }
    )
    if response is None:
        raise RuntimeError("mcp live-read smoke did not receive a JSON-RPC response")
    result = response.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("mcp live-read smoke response did not contain a result object")
    return redact_mcp_live_read_smoke_result(
        result,
        tool_name=tool_name,
        workspace_id=workspace_id,
        case_id=case_id,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )


def run_mcp_live_read_smoke_from_paths(
    client: GraphReadClient,
    *,
    contract_path: Path = DEFAULT_MCP_CONTRACT,
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    tool_name: str,
    workspace_id: str,
    case_id: str,
    correlation_id: str = "mcp-live-read-smoke",
) -> dict[str, Any]:
    return run_mcp_live_read_smoke(
        client,
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        tool_name=tool_name,
        workspace_id=workspace_id,
        case_id=case_id,
        correlation_id=correlation_id,
    )


def write_mcp_live_read_smoke_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def redact_mcp_live_read_smoke_result(
    mcp_tool_result: dict[str, Any],
    *,
    tool_name: str,
    workspace_id: str,
    case_id: str,
    correlation_id: str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    structured = _dict(mcp_tool_result.get("structuredContent"))
    request_plan = _dict(structured.get("requestPlan"))
    graph_response = _dict(structured.get("graphResponse"))
    response_shape = _graph_response_shape(graph_response)
    status = "FAILED" if mcp_tool_result.get("isError") is True else "PASSED"
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    summary: dict[str, Any] = {
        "tool": tool_name,
        "workspace_id": workspace_id,
        "case_id_sha256": _sha256(case_id),
        "correlation_id": correlation_id,
        "runtime_mode": structured.get("runtimeMode"),
        "graph_read_executed": structured.get("executesGraphRequests") is True,
        "value_count": response_shape["valueCount"],
        "raw_graph_response_stored": False,
        "raw_matter_values_stored": False,
    }
    if status != "PASSED":
        summary["error_type"] = structured.get("errorType")
        summary["graph_http_status"] = structured.get("status")

    return {
        "status": status,
        "generated_at": generated_at,
        "summary": summary,
        "requestPlan": _redacted_request_plan(request_plan),
        "graphResponseShape": response_shape,
        "privacy": {
            "storesRawGraphResponse": False,
            "storesRawMatterValues": False,
            "storesRawCaseId": False,
            "storesRawGraphPath": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def _redacted_request_plan(request_plan: dict[str, Any]) -> dict[str, Any]:
    path = request_plan.get("path")
    payload = request_plan.get("payload")
    return {
        "tool": request_plan.get("tool"),
        "method": request_plan.get("method"),
        "listName": request_plan.get("list_name"),
        "pathSha256": _sha256(path) if isinstance(path, str) else None,
        "payloadPresent": payload is not None,
        "readsItems": request_plan.get("reads_items") is True,
        "readsFiles": request_plan.get("reads_files") is True,
        "writesItems": request_plan.get("writes_items") is True,
        "graphRestOnly": request_plan.get("graph_rest_only") is True,
    }


def _graph_response_shape(graph_response: dict[str, Any]) -> dict[str, Any]:
    values = graph_response.get("value")
    items = values if isinstance(values, list) else []
    first_item = _dict(items[0]) if items and isinstance(items[0], dict) else {}
    field_names: set[str] = set()
    item_keys: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        item_keys.update(key for key in item if isinstance(key, str))
        fields = item.get("fields")
        if isinstance(fields, dict):
            field_names.update(key for key in fields if isinstance(key, str))
    if not item_keys:
        item_keys.update(key for key in first_item if isinstance(key, str))
    return {
        "topLevelKeys": sorted(key for key in graph_response if isinstance(key, str)),
        "valueCount": len(items),
        "firstItemKeys": sorted(item_keys),
        "fieldNames": sorted(field_names),
        "odataContextPresent": "@odata.context" in graph_response,
        "nextLinkPresent": "@odata.nextLink" in graph_response,
    }


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
