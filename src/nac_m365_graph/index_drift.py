from __future__ import annotations

import json
import urllib.parse
from typing import Any

from .schema import validate_schema


GRAPH_BASE = "https://graph.microsoft.com/v1.0"
PROVISIONED_STATE_VERSION = "nac.m365.teams-sharepoint.provisioned/v0.1"
SOURCE_SCHEMA = "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json"


class _DriftFailure(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def preflight_index_drift(
    schema: dict[str, Any],
    provisioned_state: dict[str, Any],
    workspace_id: str,
) -> tuple[str, list[tuple[dict[str, Any], str]]]:
    """Bind one declared workspace to one saved site and its exact list IDs, without I/O."""
    if not isinstance(schema, dict):
        raise _DriftFailure("SCHEMA_INVALID")
    try:
        schema_errors = validate_schema(schema)
    except (KeyError, TypeError, ValueError) as exc:
        raise _DriftFailure("SCHEMA_INVALID") from exc
    if schema_errors:
        raise _DriftFailure("SCHEMA_INVALID")
    if not isinstance(provisioned_state, dict) or not isinstance(workspace_id, str):
        raise _DriftFailure("TARGET_BINDING_INVALID")
    if (
        provisioned_state.get("state_version") != PROVISIONED_STATE_VERSION
        or provisioned_state.get("source_schema") != SOURCE_SCHEMA
        or not isinstance(provisioned_state.get("tenant"), dict)
        or not isinstance(provisioned_state["tenant"].get("tenant_id"), str)
        or not provisioned_state["tenant"]["tenant_id"]
        or not isinstance(provisioned_state.get("graph"), dict)
        or provisioned_state["graph"].get("base_url") != GRAPH_BASE
    ):
        raise _DriftFailure("TARGET_BINDING_INVALID")
    schema_workspaces = schema.get("workspaces")
    state_workspaces = provisioned_state.get("workspaces")
    if not isinstance(schema_workspaces, list) or not isinstance(state_workspaces, list):
        raise _DriftFailure("TARGET_BINDING_INVALID")
    declared = [item for item in schema_workspaces if isinstance(item, dict) and item.get("id") == workspace_id]
    saved = [item for item in state_workspaces if isinstance(item, dict) and item.get("id") == workspace_id]
    if len(declared) != 1 or len(saved) != 1:
        raise _DriftFailure("TARGET_BINDING_INVALID")
    workspace = saved[0]
    site_id = workspace.get("site_id")
    saved_lists = workspace.get("lists")
    schema_lists = schema["sharepoint"]["lists"]
    expected_names = {item["display_name"] for item in schema_lists}
    if (
        not isinstance(site_id, str)
        or not site_id
        or not isinstance(saved_lists, dict)
        or set(saved_lists) != expected_names
    ):
        raise _DriftFailure("TARGET_BINDING_INVALID")
    bound_lists: list[tuple[dict[str, Any], str]] = []
    seen_ids: set[str] = set()
    for list_def in schema_lists:
        entry = saved_lists.get(list_def["display_name"])
        list_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(list_id, str) or not list_id or list_id in seen_ids:
            raise _DriftFailure("TARGET_BINDING_INVALID")
        seen_ids.add(list_id)
        bound_lists.append((list_def, list_id))
    return site_id, bound_lists


def index_drift_binding_valid(
    schema: dict[str, Any], provisioned_state: dict[str, Any], workspace_id: str
) -> bool:
    """Expose a redacted, credential-free CLI preflight result."""
    try:
        preflight_index_drift(schema, provisioned_state, workspace_id)
    except _DriftFailure:
        return False
    return True


def run_index_drift(
    metadata_by_path: dict[str, Any],
    schema: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
) -> dict[str, Any]:
    """Compare an in-memory metadata snapshot; never call a provider or credential port."""
    reads = 0
    checked_lists = 0
    checked_columns = 0
    reason_code = "NONE"
    try:
        if type(metadata_by_path) is not dict:
            raise _DriftFailure("OFFLINE_METADATA_REQUIRED")
        site_id, bound_lists = preflight_index_drift(schema, provisioned_state, workspace_id)
        site_path = urllib.parse.quote(site_id, safe=",")
        site_request = f"/sites/{site_path}?$select=id"
        lists_request = f"/sites/{site_path}/lists?$select=id,displayName"
        column_requests = [
            f"/sites/{site_path}/lists/{urllib.parse.quote(list_id, safe='')}/columns?$select=id,name,indexed"
            for _list_def, list_id in bound_lists
        ]
        expected_paths = {site_request, lists_request, *column_requests}
        try:
            metadata = json.loads(json.dumps(metadata_by_path, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise _DriftFailure("OFFLINE_METADATA_INVALID") from exc
        if set(metadata) != expected_paths:
            raise _DriftFailure("OFFLINE_METADATA_INVALID")

        def read(path: str) -> dict[str, Any]:
            nonlocal reads
            reads += 1
            response = metadata[path]
            if not isinstance(response, dict):
                raise _DriftFailure("GRAPH_RESPONSE_INVALID")
            if "error" in response:
                raise _DriftFailure("GRAPH_READ_FAILED")
            if "@odata.nextLink" in response:
                raise _DriftFailure("PAGINATED_METADATA")
            return response

        site = read(site_request)
        if not isinstance(site.get("id"), str) or site["id"] != site_id:
            raise _DriftFailure("SITE_BINDING_MISMATCH")

        lists = _collection(
            read(lists_request),
            name_key="displayName",
            invalid_code="LIST_METADATA_INVALID",
        )
        for list_def, list_id in bound_lists:
            actual_list = lists.get(list_def["display_name"])
            if actual_list is None or actual_list["id"] != list_id:
                raise _DriftFailure("LIST_BINDING_MISMATCH")

        for (list_def, _list_id), column_request in zip(bound_lists, column_requests, strict=True):
            columns = _collection(
                read(column_request),
                name_key="name",
                invalid_code="COLUMN_METADATA_INVALID",
                require_indexed=True,
            )
            indexed_names = set(list_def["indexed_columns"])
            for column_def in list_def["columns"]:
                name = column_def["name"]
                actual_column = columns.get(name)
                if actual_column is None:
                    raise _DriftFailure("COLUMN_METADATA_INVALID")
                if actual_column["indexed"] is not (name in indexed_names):
                    raise _DriftFailure("INDEX_MISMATCH")
                checked_columns += 1
            checked_lists += 1
    except _DriftFailure as exc:
        reason_code = exc.code

    return {
        "status": "PASSED" if reason_code == "NONE" else "FAILED",
        "reason_code": reason_code,
        "summary": {
            "metadata_entries_compared": reads,
            "graph_get_requests": 0,
            "graph_write_requests": 0,
            "list_items_read": 0,
            "files_read": 0,
            "checked_lists": checked_lists,
            "checked_columns": checked_columns,
            "raw_provider_data_written_by_checker": False,
        },
    }


def _collection(
    response: dict[str, Any],
    *,
    name_key: str,
    invalid_code: str,
    require_indexed: bool = False,
) -> dict[str, dict[str, Any]]:
    values = response.get("value")
    if not isinstance(values, list):
        raise _DriftFailure(invalid_code)
    result: dict[str, dict[str, Any]] = {}
    ids: set[str] = set()
    for item in values:
        if not isinstance(item, dict):
            raise _DriftFailure(invalid_code)
        name = item.get(name_key)
        identifier = item.get("id")
        if (
            not isinstance(name, str)
            or not name
            or not isinstance(identifier, str)
            or not identifier
            or name in result
            or identifier in ids
            or (require_indexed and not isinstance(item.get("indexed"), bool))
        ):
            raise _DriftFailure(invalid_code)
        ids.add(identifier)
        result[name] = item
    return result
