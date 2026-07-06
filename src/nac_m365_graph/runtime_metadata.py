from __future__ import annotations

import urllib.parse
from typing import Any, Protocol


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphReadClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...


def build_runtime_metadata_snapshot(
    client: GraphReadClient,
    provisioned_state: dict[str, Any],
) -> dict[str, Any]:
    workspaces: list[dict[str, Any]] = []
    for workspace in _workspaces(provisioned_state):
        site_id = workspace["site_id"]
        site_path = urllib.parse.quote(site_id, safe=",")
        site = client.get(f"/sites/{site_path}?$select=id,displayName,webUrl")
        lists = _paged(client, f"/sites/{site_path}/lists?$select=id,displayName,webUrl")
        drives = _paged(client, f"/sites/{site_path}/drives?$select=id,name,webUrl,driveType")

        expected_lists = set(_mapping_keys(workspace.get("lists")))
        actual_lists = {
            item.get("displayName"): item
            for item in lists
            if isinstance(item.get("displayName"), str)
        }
        expected_libraries = set(_mapping_keys(workspace.get("document_libraries")))
        actual_libraries = {
            item.get("name"): item
            for item in drives
            if isinstance(item.get("name"), str)
        }
        missing_lists = sorted(expected_lists - set(actual_lists))
        missing_libraries = sorted(expected_libraries - set(actual_libraries))
        if missing_lists or missing_libraries:
            raise RuntimeError(
                f"runtime metadata for {workspace['team_display_name']} is incomplete: "
                f"missing_lists={missing_lists}; missing_libraries={missing_libraries}"
            )

        workspaces.append(
            {
                "workspaceId": workspace["id"],
                "teamDisplayName": workspace["team_display_name"],
                "siteId": site_id,
                "siteDisplayName": site.get("displayName"),
                "siteWebUrl": site.get("webUrl"),
                "lists": [
                    _list_view(actual_lists[name])
                    for name in sorted(expected_lists)
                ],
                "documentLibraries": [
                    _drive_view(actual_libraries[name])
                    for name in sorted(expected_libraries)
                ],
                "missingLists": [],
                "missingDocumentLibraries": [],
            }
        )

    return {
        "status": "PASSED",
        "summary": {
            "workspaces": len(workspaces),
            "sites_read": len(workspaces),
            "expected_lists": sum(len(item["lists"]) for item in workspaces),
            "expected_document_libraries": sum(len(item["documentLibraries"]) for item in workspaces),
            "missing_lists": 0,
            "missing_document_libraries": 0,
            "list_items_read": 0,
        },
        "workspaces": workspaces,
    }


def _list_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "displayName": item.get("displayName"),
        "webUrl": item.get("webUrl"),
    }


def _drive_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "webUrl": item.get("webUrl"),
        "driveType": item.get("driveType"),
    }


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
