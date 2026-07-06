from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .graph_client import encode_path_segment
from .mcp_runtime import RuntimeContext, load_mcp_contract, plan_tool_request
from .privileged_change import load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_SMOKE_CLEANUP_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "mcp-smoke-cleanup.redacted.json"
)
SMOKE_CASE_ID_PREFIX = "NAC-SMOKE-WRITE-READ-"


class GraphCleanupClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...

    def delete(self, path: str) -> dict[str, Any]:
        ...


def run_mcp_smoke_cleanup(
    client: GraphCleanupClient,
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    case_id: str,
    correlation_id: str = "mcp-smoke-cleanup",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not case_id.startswith(SMOKE_CASE_ID_PREFIX):
        raise ValueError(f"cleanup is limited to synthetic case ids starting with {SMOKE_CASE_ID_PREFIX}")

    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    context = RuntimeContext(
        actor_id="nac-mcp-smoke-cleanup",
        actor_role="runtime_service",
        workspace_id=workspace_id,
        purpose="m365_mcp_smoke_cleanup",
        correlation_id=correlation_id,
        case_id=case_id,
        role_case_gate="open",
        write_approved=True,
    )
    read_plan = plan_tool_request(contract, provisioned_state, context, "case_get", {"case_id": case_id})
    before = client.get(read_plan.path)
    item = _single_matching_item(before, case_id)
    item_id = str(item["id"])
    delete_path = _delete_path_for_item(read_plan.path, item_id)
    client.delete(delete_path)
    after = client.get(read_plan.path)
    after_count = _value_count(after)

    return redact_mcp_smoke_cleanup_result(
        read_plan=asdict(read_plan),
        workspace_id=workspace_id,
        case_id=case_id,
        correlation_id=correlation_id,
        timestamp=generated_at,
        item_id=item_id,
        before_count=1,
        after_count=after_count,
    )


def run_mcp_smoke_cleanup_from_paths(
    client: GraphCleanupClient,
    *,
    contract_path: Path,
    provisioned_state_path: Path,
    workspace_id: str,
    case_id: str,
    correlation_id: str = "mcp-smoke-cleanup",
) -> dict[str, Any]:
    return run_mcp_smoke_cleanup(
        client,
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        workspace_id=workspace_id,
        case_id=case_id,
        correlation_id=correlation_id,
    )


def write_mcp_smoke_cleanup_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def redact_mcp_smoke_cleanup_result(
    *,
    read_plan: dict[str, Any],
    workspace_id: str,
    case_id: str,
    correlation_id: str,
    timestamp: str,
    item_id: str,
    before_count: int,
    after_count: int,
) -> dict[str, Any]:
    return {
        "status": "PASSED" if after_count == 0 else "FAILED",
        "generated_at": timestamp,
        "summary": {
            "workspace_id": workspace_id,
            "case_id_sha256": _sha256(case_id),
            "correlation_id": correlation_id,
            "cleanup_target": "synthetic_mcp_smoke_case",
            "case_id_prefix_required": SMOKE_CASE_ID_PREFIX,
            "read_before_value_count": before_count,
            "delete_status": "PASSED",
            "deleted_item_id_sha256": _sha256(item_id),
            "read_after_value_count": after_count,
            "graph_rest_only": True,
            "raw_case_id_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "readRequest": _redacted_read_plan(read_plan),
        "privacy": {
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "storesRawGraphPath": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def _single_matching_item(response: dict[str, Any], case_id: str) -> dict[str, Any]:
    values = response.get("value")
    items = values if isinstance(values, list) else []
    matches = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = item.get("fields")
        if isinstance(fields, dict) and fields.get("NacCaseId") == case_id and isinstance(item.get("id"), str):
            matches.append(item)
    if len(matches) != 1:
        raise RuntimeError(f"cleanup requires exactly one matching synthetic smoke item; found {len(matches)}")
    return matches[0]


def _delete_path_for_item(read_path: str, item_id: str) -> str:
    if "/items?" not in read_path:
        raise RuntimeError("cannot derive cleanup delete path from case_get request plan")
    list_path = read_path.split("/items?", 1)[0]
    return f"{list_path}/items/{encode_path_segment(item_id)}"


def _value_count(response: dict[str, Any]) -> int:
    values = response.get("value")
    return len(values) if isinstance(values, list) else 0


def _redacted_read_plan(read_plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "tool": read_plan.get("tool"),
        "method": read_plan.get("method"),
        "listName": read_plan.get("list_name"),
        "pathSha256": _sha256(read_plan["path"]) if isinstance(read_plan.get("path"), str) else None,
        "readsItems": read_plan.get("reads_items") is True,
        "writesItems": read_plan.get("writes_items") is True,
        "graphRestOnly": read_plan.get("graph_rest_only") is True,
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
