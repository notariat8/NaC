from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.teams-sharepoint.json"
REQUIRED_WORKSPACES = {"notary_team_01", "notary_team_02"}
REQUIRED_LISTS = {
    "Akten",
    "Beteiligte",
    "AufgabenFristen",
    "Vertretungsfreigaben",
    "AuditJournalLite",
    "DokumentRegister",
}
REQUIRED_DOCUMENT_LIBRARIES = {"AktenDokumente", "Vorlagen"}
REQUIRED_AKTEN_COLUMNS = {
    "NacCaseId",
    "Aktenzeichen",
    "Vorgangstyp",
    "Status",
    "NotarTeam",
    "NacWorkflowVersion",
    "KgVersion",
}
SUPPORTED_COLUMN_TYPES = {"text", "choice", "boolean", "dateTime", "user"}
RESERVED_SHAREPOINT_COLUMN_NAMES = {
    "WorkflowVersion",
}


def load_schema(path: Path = DEFAULT_SCHEMA) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if schema.get("schema_version") != "nac.teams-sharepoint-graph-data-plane/v0.1":
        errors.append("schema_version must be nac.teams-sharepoint-graph-data-plane/v0.1")
    graph = schema.get("graph")
    if not isinstance(graph, dict):
        errors.append("graph must be an object")
    else:
        if graph.get("base_url") != "https://graph.microsoft.com/v1.0":
            errors.append("graph.base_url must be https://graph.microsoft.com/v1.0")
        if graph.get("rest_only") is not True:
            errors.append("graph.rest_only must be true")
        if graph.get("sdk_allowed") is not False:
            errors.append("graph.sdk_allowed must be false")
        if graph.get("legacy_sharepoint_api_allowed") is not False:
            errors.append("graph.legacy_sharepoint_api_allowed must be false")

    workspaces = schema.get("workspaces")
    if not isinstance(workspaces, list) or not workspaces:
        errors.append("workspaces must be a non-empty list")
    else:
        workspace_ids = {item.get("id") for item in workspaces if isinstance(item, dict)}
        for missing in sorted(REQUIRED_WORKSPACES - workspace_ids):
            errors.append(f"workspaces missing {missing}")
        for workspace in workspaces:
            if not isinstance(workspace, dict):
                errors.append("workspaces entries must be objects")
                continue
            if workspace.get("visibility") != "private":
                errors.append(f"workspace {workspace.get('id')} visibility must be private")
            if workspace.get("membership_model") != "notary_and_assigned_clerk":
                errors.append(f"workspace {workspace.get('id')} membership_model must be notary_and_assigned_clerk")

    sharepoint = schema.get("sharepoint")
    if not isinstance(sharepoint, dict):
        return errors + ["sharepoint must be an object"]

    lists = sharepoint.get("lists")
    if not isinstance(lists, list) or not lists:
        errors.append("sharepoint.lists must be a non-empty list")
    else:
        by_name = {
            item.get("display_name"): item
            for item in lists
            if isinstance(item, dict) and isinstance(item.get("display_name"), str)
        }
        for missing in sorted(REQUIRED_LISTS - set(by_name)):
            errors.append(f"sharepoint.lists missing {missing}")
        akten = by_name.get("Akten")
        if isinstance(akten, dict):
            column_names = {
                item.get("name")
                for item in akten.get("columns", [])
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }
            for missing in sorted(REQUIRED_AKTEN_COLUMNS - column_names):
                errors.append(f"Akten columns missing {missing}")
        for list_def in lists:
            errors.extend(_validate_list_definition(list_def))

    libraries = sharepoint.get("document_libraries")
    if not isinstance(libraries, list) or not libraries:
        errors.append("sharepoint.document_libraries must be a non-empty list")
    else:
        library_names = {item.get("display_name") for item in libraries if isinstance(item, dict)}
        for missing in sorted(REQUIRED_DOCUMENT_LIBRARIES - library_names):
            errors.append(f"sharepoint.document_libraries missing {missing}")
        for library in libraries:
            if isinstance(library, dict) and library.get("template") != "documentLibrary":
                errors.append(f"document library {library.get('display_name')} template must be documentLibrary")

    return errors


def list_create_payload(list_def: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "displayName": list_def["display_name"],
        "list": {"template": list_def.get("template", "genericList")},
    }
    if list_def.get("description"):
        payload["description"] = list_def["description"]
    return payload


def column_create_payload(column_def: dict[str, Any]) -> dict[str, Any]:
    name = column_def["name"]
    column_type = column_def["type"]
    payload: dict[str, Any] = {
        "name": name,
        "displayName": name,
        "required": bool(column_def.get("required", False)),
    }
    if column_def.get("enforce_unique_values") is True:
        payload["enforceUniqueValues"] = True
        payload["indexed"] = True

    if column_type == "text":
        payload["text"] = {}
    elif column_type == "choice":
        payload["choice"] = {
            "allowTextEntry": False,
            "choices": list(column_def.get("choices", [])),
        }
    elif column_type == "boolean":
        payload["boolean"] = {}
    elif column_type == "dateTime":
        payload["dateTime"] = {"displayAs": "default"}
    elif column_type == "user":
        payload["personOrGroup"] = {
            "allowMultipleSelection": False,
            "chooseFromType": "peopleOnly",
        }
    else:
        raise ValueError(f"unsupported column type: {column_type}")
    return payload


def _validate_list_definition(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["sharepoint.lists entries must be objects"]
    display_name = value.get("display_name")
    if not isinstance(display_name, str) or not display_name:
        errors.append("list display_name must be set")
    if value.get("template") != "genericList":
        errors.append(f"list {display_name} template must be genericList")
    columns = value.get("columns")
    if not isinstance(columns, list) or not columns:
        errors.append(f"list {display_name} columns must be a non-empty list")
        return errors
    names: set[str] = set()
    for column in columns:
        if not isinstance(column, dict):
            errors.append(f"list {display_name} column entries must be objects")
            continue
        name = column.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"list {display_name} column name must be set")
        elif name in names:
            errors.append(f"list {display_name} has duplicate column {name}")
        else:
            names.add(name)
        column_type = column.get("type")
        if column_type not in SUPPORTED_COLUMN_TYPES:
            errors.append(f"list {display_name} column {name} has unsupported type {column_type}")
        if name in RESERVED_SHAREPOINT_COLUMN_NAMES:
            errors.append(f"list {display_name} column {name} conflicts with a SharePoint system field")
        if column_type == "choice" and not column.get("choices"):
            errors.append(f"list {display_name} choice column {name} must define choices")
    return errors
