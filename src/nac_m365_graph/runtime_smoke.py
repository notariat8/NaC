from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
import urllib.parse
from typing import Any, Protocol


REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
DEFAULT_RUNTIME_SMOKE_OUTPUT = REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "runtime-smoke.redacted.json"


class GraphReadClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...


def run_runtime_site_smoke(
    client: GraphReadClient,
    provisioned_state: dict[str, Any],
    expected_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    workspace_results: list[dict[str, Any]] = []
    for workspace in _workspaces(provisioned_state):
        site_id = workspace["site_id"]
        site_path = urllib.parse.quote(site_id, safe=",")
        site = client.get(f"/sites/{site_path}?$select=id,displayName,webUrl")
        lists = _paged(client, f"/sites/{site_path}/lists?$select=id,displayName,webUrl")
        expected_lists = set(_expected_list_names(workspace, expected_schema))
        actual_lists = {item.get("displayName") for item in lists if isinstance(item.get("displayName"), str)}
        missing_lists = sorted(expected_lists - actual_lists)
        if missing_lists:
            raise RuntimeError(
                f"runtime smoke for {workspace['team_display_name']} missing lists: "
                + ", ".join(missing_lists)
            )
        workspace_results.append(
            {
                "workspaceId": workspace["id"],
                "teamDisplayName": workspace["team_display_name"],
                "siteId": site_id,
                "siteDisplayName": site.get("displayName"),
                "siteWebUrl": site.get("webUrl"),
                "expectedListCount": len(expected_lists),
                "observedListCount": len(actual_lists),
                "expectationSource": _expectation_source(expected_schema),
                "missingLists": [],
            }
        )
    return {
        "status": "PASSED",
        "summary": {
            "workspaces": len(workspace_results),
            "sites_read": len(workspace_results),
            "missing_lists": 0,
        },
        "workspaces": workspace_results,
    }


def redact_runtime_site_smoke_result(result: dict[str, Any], *, timestamp: str | None = None) -> dict[str, Any]:
    summary = dict(result.get("summary") if isinstance(result.get("summary"), dict) else {})
    summary.update(
        {
            "graph_rest_only": True,
            "raw_site_id_stored": False,
            "raw_site_url_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
            "list_items_read": 0,
        }
    )
    return {
        "status": result.get("status"),
        "generated_at": timestamp or _now(),
        "summary": summary,
        "workspaces": [
            _redacted_workspace(workspace)
            for workspace in result.get("workspaces", [])
            if isinstance(workspace, dict)
        ],
        "privacy": {
            "storesRawGraphResponse": False,
            "storesRawSiteId": False,
            "storesRawSiteUrl": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def write_runtime_site_smoke_artifact(result: dict[str, Any], output_path: Path) -> dict[str, Any]:
    artifact = redact_runtime_site_smoke_result(result)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return artifact


def _expected_list_names(workspace: dict[str, Any], expected_schema: dict[str, Any] | None) -> list[str]:
    if expected_schema is None:
        return _mapping_keys(workspace.get("lists"))
    return [
        item["display_name"]
        for item in expected_schema.get("sharepoint", {}).get("lists", [])
        if isinstance(item, dict) and isinstance(item.get("display_name"), str)
    ]


def _expectation_source(expected_schema: dict[str, Any] | None) -> str:
    if expected_schema is None:
        return "provisioned_state"
    return "schema"


def _paged(client: GraphReadClient, path: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    while path:
        payload = client.get(path)
        values.extend(payload.get("value", []))
        next_link = payload.get("@odata.nextLink")
        path = next_link.removeprefix(GRAPH_BASE) if isinstance(next_link, str) else ""
    return values


def _workspaces(provisioned_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        workspace
        for workspace in provisioned_state.get("workspaces", [])
        if isinstance(workspace, dict)
    ]


def _mapping_keys(value: object) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [key for key in value if isinstance(key, str)]


def _redacted_workspace(workspace: dict[str, Any]) -> dict[str, Any]:
    team_display_name = workspace.get("teamDisplayName")
    site_display_name = workspace.get("siteDisplayName")
    return {
        "workspaceId": workspace.get("workspaceId"),
        "teamDisplayNameSha256": _sha256(team_display_name) if isinstance(team_display_name, str) else None,
        "siteDisplayNameSha256": _sha256(site_display_name) if isinstance(site_display_name, str) else None,
        "expectedListCount": workspace.get("expectedListCount"),
        "observedListCount": workspace.get("observedListCount"),
        "expectationSource": workspace.get("expectationSource"),
        "missingLists": workspace.get("missingLists", []),
    }


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
