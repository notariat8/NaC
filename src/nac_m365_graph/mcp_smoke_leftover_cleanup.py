from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .graph_client import encode_path_segment
from .mcp_smoke_cleanup import SMOKE_CASE_ID_PREFIX
from .privileged_change import load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_SMOKE_LEFTOVER_CLEANUP_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "mcp-smoke-leftover-cleanup.redacted.json"
)
DEFAULT_QUERY_TOP = 200


class GraphLeftoverCleanupClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...

    def delete(self, path: str) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class SmokeLeftoverItem:
    item_id: str
    case_id: str


def run_mcp_smoke_leftover_cleanup(
    client: GraphLeftoverCleanupClient,
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str = "mcp-smoke-leftover-cleanup",
    delete_after: bool = True,
    timestamp: str | None = None,
    query_top: int = DEFAULT_QUERY_TOP,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    workspace = _workspace_by_id(provisioned_state, workspace_id)
    query_path = _prefix_query_path(workspace, query_top=query_top)
    before_response = client.get(query_path)
    before = _extract_prefix_items(before_response)

    deleted: list[SmokeLeftoverItem] = []
    if delete_after:
        for item in before:
            client.delete(_delete_path(workspace, item.item_id))
            deleted.append(item)

    after_response = client.get(query_path) if delete_after else before_response
    after = _extract_prefix_items(after_response)

    return redact_mcp_smoke_leftover_cleanup_result(
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        timestamp=generated_at,
        query_path=query_path,
        before=before,
        deleted=deleted,
        after=after,
        delete_after=delete_after,
        query_top=query_top,
    )


def run_mcp_smoke_leftover_cleanup_from_paths(
    client: GraphLeftoverCleanupClient,
    *,
    provisioned_state_path: Path,
    workspace_id: str,
    correlation_id: str = "mcp-smoke-leftover-cleanup",
    delete_after: bool = True,
) -> dict[str, Any]:
    return run_mcp_smoke_leftover_cleanup(
        client,
        load_provisioned_state(provisioned_state_path),
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        delete_after=delete_after,
    )


def write_mcp_smoke_leftover_cleanup_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def redact_mcp_smoke_leftover_cleanup_result(
    *,
    workspace_id: str,
    correlation_id: str,
    timestamp: str,
    query_path: str,
    before: list[SmokeLeftoverItem],
    deleted: list[SmokeLeftoverItem],
    after: list[SmokeLeftoverItem],
    delete_after: bool,
    query_top: int,
) -> dict[str, Any]:
    status = "PASSED" if not delete_after or not after else "FAILED"
    return {
        "status": status,
        "generated_at": timestamp,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "cleanup_target": "synthetic_mcp_smoke_leftovers",
            "case_id_prefix_required": SMOKE_CASE_ID_PREFIX,
            "query_top": query_top,
            "read_before_value_count": len(before),
            "delete_requested": delete_after,
            "deleted_value_count": len(deleted),
            "read_after_value_count": len(after),
            "graph_rest_only": True,
            "raw_case_id_stored": False,
            "raw_item_id_stored": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "readRequest": {
            "method": "GET",
            "listName": "Akten",
            "pathSha256": _sha256(query_path),
            "filter": "startswith(fields/NacCaseId, smoke-prefix)",
            "graphRestOnly": True,
        },
        "deleted": [
            {
                "item_id_sha256": _sha256(item.item_id),
                "case_id_sha256": _sha256(item.case_id),
            }
            for item in deleted
        ],
        "privacy": {
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "storesRawItemId": False,
            "storesRawGraphPath": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def _workspace_by_id(provisioned_state: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    for workspace in provisioned_state.get("workspaces", []):
        if isinstance(workspace, dict) and workspace.get("id") == workspace_id:
            return workspace
    raise RuntimeError(f"unknown workspace_id: {workspace_id}")


def _prefix_query_path(workspace: dict[str, Any], *, query_top: int) -> str:
    if query_top <= 0:
        raise ValueError("query_top must be positive")
    site_id = workspace.get("site_id")
    list_id = workspace.get("lists", {}).get("Akten", {}).get("id")
    if not isinstance(site_id, str) or not isinstance(list_id, str):
        raise RuntimeError("workspace missing Akten list state")
    filter_expr = urllib.parse.quote(f"startswith(fields/NacCaseId,'{SMOKE_CASE_ID_PREFIX}')", safe="()/$=,'")
    select_expr = urllib.parse.quote("id,fields", safe=",")
    expand_expr = urllib.parse.quote("fields($select=NacCaseId)", safe="(),=$")
    return (
        f"/sites/{urllib.parse.quote(site_id, safe=',')}/lists/{encode_path_segment(list_id)}/items"
        f"?$select={select_expr}&$expand={expand_expr}&$filter={filter_expr}&$top={query_top}"
    )


def _delete_path(workspace: dict[str, Any], item_id: str) -> str:
    site_id = workspace.get("site_id")
    list_id = workspace.get("lists", {}).get("Akten", {}).get("id")
    if not isinstance(site_id, str) or not isinstance(list_id, str):
        raise RuntimeError("workspace missing Akten list state")
    return (
        f"/sites/{urllib.parse.quote(site_id, safe=',')}/lists/{encode_path_segment(list_id)}"
        f"/items/{encode_path_segment(item_id)}"
    )


def _extract_prefix_items(response: dict[str, Any]) -> list[SmokeLeftoverItem]:
    if "@odata.nextLink" in response:
        raise RuntimeError("cleanup refused: prefix query returned pagination")
    values = response.get("value")
    items = values if isinstance(values, list) else []
    leftovers: list[SmokeLeftoverItem] = []
    for item in items:
        if not isinstance(item, dict):
            raise RuntimeError("cleanup refused: query returned a non-object item")
        fields = item.get("fields")
        case_id = fields.get("NacCaseId") if isinstance(fields, dict) else None
        item_id = item.get("id")
        if not isinstance(case_id, str) or not case_id.startswith(SMOKE_CASE_ID_PREFIX):
            raise RuntimeError("cleanup refused: query returned a non-smoke case id")
        if not isinstance(item_id, str) or not item_id:
            raise RuntimeError("cleanup refused: query returned item without id")
        leftovers.append(SmokeLeftoverItem(item_id=item_id, case_id=case_id))
    return leftovers


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
