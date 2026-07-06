from __future__ import annotations

import urllib.parse
from typing import Any, Protocol


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


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
