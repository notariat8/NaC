from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .provisioner import PlanOperation
from .schema import column_create_payload, list_create_payload, load_schema, validate_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BPMN_VIEWER_PROVISIONING = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-bpmn-viewer.provisioning.json"
)
REQUIRED_DOCUMENT_LIBRARIES = {"BPMN Models"}
REQUIRED_LISTS = {"Prozessregister"}
REQUIRED_BPMN_MODELS_COLUMNS = {
    "NacBpmnModelId",
    "ProcessKey",
    "NacBpmnVersion",
    "BpmnDriveItemId",
    "BpmnContentMode",
    "BpmnGitPath",
    "BpmnGitCommitSha",
    "BpmnXmlSha256",
    "BpmnXmlMimeType",
    "ApprovalStatus",
    "NacDataClass",
    "ContainsMatterData",
    "ViewerEnabled",
}
REQUIRED_PROZESSREGISTER_COLUMNS = {
    "NacProcessId",
    "ProcessKey",
    "ProcessName",
    "ProcessOwner",
    "ProcessStatus",
    "NacBpmnModelId",
    "BpmnDriveItemId",
    "BpmnXmlSha256",
    "BpmnGitPath",
    "BpmnGitCommitSha",
    "NacBpmnVersion",
    "BpmnContentMode",
    "ViewerEnabled",
    "OverlayPolicy",
}
PROCESS_ROW_BPMN_FIELDS = {
    "NacBpmnModelId",
    "BpmnDriveItemId",
    "BpmnXmlSha256",
    "BpmnGitPath",
    "BpmnGitCommitSha",
    "NacBpmnVersion",
    "BpmnContentMode",
}
SUPPORTED_COLUMN_TYPES = {"text", "choice", "boolean", "dateTime", "user"}
REQUIRED_BLOCKED_OPERATIONS = {
    "live_apply",
    "write_bpmn_xml",
    "save_bpmn_model",
    "execute_workflow",
    "start_process_instance",
    "mutate_team_or_site_membership",
    "read_matter_document_content",
    "read_matter_payload",
    "legacy_sharepoint_rest",
    "sharepoint_csom",
    "pnp",
    "microsoft_graph_sdk",
    "graph_beta",
}


def load_bpmn_viewer_provisioning_config(
    path: Path = DEFAULT_BPMN_VIEWER_PROVISIONING,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_bpmn_viewer_provisioning_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != "nac.m365-bpmn-viewer-provisioning/v0.2":
        errors.append("bpmn viewer provisioning schema_version must be nac.m365-bpmn-viewer-provisioning/v0.2")
    if config.get("status") != "optional_plan_only_no_live_apply":
        errors.append("bpmn viewer provisioning status must be optional_plan_only_no_live_apply")
    graph = config.get("graph")
    if not isinstance(graph, dict):
        errors.append("bpmn viewer provisioning graph must be an object")
    else:
        if graph.get("base_url") != "https://graph.microsoft.com/v1.0":
            errors.append("bpmn viewer provisioning graph.base_url must be https://graph.microsoft.com/v1.0")
        for flag in ("rest_only",):
            if graph.get(flag) is not True:
                errors.append(f"bpmn viewer provisioning graph.{flag} must be true")
        for flag in ("sdk_allowed", "legacy_sharepoint_api_allowed", "graph_beta_allowed"):
            if graph.get(flag) is not False:
                errors.append(f"bpmn viewer provisioning graph.{flag} must be false")

    source = config.get("source_of_truth")
    if not isinstance(source, dict):
        errors.append("bpmn viewer provisioning source_of_truth must be an object")
    else:
        for flag in (
            "git_bpmn_templates_remain_source_of_truth",
            "python_validation_required_before_publish",
            "pull_request_required_before_publish",
            "sharepoint_stores_approved_copies_or_pointers_only",
        ):
            if source.get(flag) is not True:
                errors.append(f"bpmn viewer provisioning source_of_truth.{flag} must be true")

    live_apply = config.get("live_apply")
    if not isinstance(live_apply, dict):
        errors.append("bpmn viewer provisioning live_apply must be an object")
    else:
        if live_apply.get("implemented") is not False:
            errors.append("bpmn viewer provisioning live_apply.implemented must be false")
        if live_apply.get("mutates_tenant_now") is not False:
            errors.append("bpmn viewer provisioning live_apply.mutates_tenant_now must be false")
        if live_apply.get("owner_gate_required_before_future_apply") is not True:
            errors.append("bpmn viewer provisioning future live apply must require an owner gate")

    sharepoint = config.get("sharepoint")
    if not isinstance(sharepoint, dict):
        errors.append("bpmn viewer provisioning sharepoint must be an object")
        return errors

    libraries = sharepoint.get("document_libraries")
    if not isinstance(libraries, list) or not libraries:
        errors.append("bpmn viewer provisioning sharepoint.document_libraries must be a non-empty list")
    else:
        library_names = {item.get("display_name") for item in libraries if isinstance(item, dict)}
        for missing in sorted(REQUIRED_DOCUMENT_LIBRARIES - library_names):
            errors.append(f"bpmn viewer provisioning document_libraries missing {missing}")
        by_name = {item.get("display_name"): item for item in libraries if isinstance(item, dict)}
        bpmn_models = by_name.get("BPMN Models")
        if isinstance(bpmn_models, dict):
            columns = _columns_by_name(bpmn_models)
            for missing in sorted(REQUIRED_BPMN_MODELS_COLUMNS - set(columns)):
                errors.append(f"bpmn viewer provisioning BPMN Models columns missing {missing}")
            for name in sorted(PROCESS_ROW_BPMN_FIELDS):
                column = columns.get(name)
                if isinstance(column, dict) and column.get("required") is not True:
                    errors.append(f"bpmn viewer provisioning BPMN Models column {name} must be required")
        for library in libraries:
            if not isinstance(library, dict):
                errors.append("bpmn viewer provisioning document library entries must be objects")
                continue
            if library.get("template") != "documentLibrary":
                errors.append(f"bpmn viewer provisioning library {library.get('display_name')} must be documentLibrary")
            errors.extend(_validate_columns(library, f"library {library.get('display_name')}"))

    lists = sharepoint.get("lists")
    if not isinstance(lists, list) or not lists:
        errors.append("bpmn viewer provisioning sharepoint.lists must be a non-empty list")
    else:
        by_name = {item.get("display_name"): item for item in lists if isinstance(item, dict)}
        for missing in sorted(REQUIRED_LISTS - set(by_name)):
            errors.append(f"bpmn viewer provisioning lists missing {missing}")
        process_register = by_name.get("Prozessregister")
        if isinstance(process_register, dict):
            columns = _columns_by_name(process_register)
            for missing in sorted(REQUIRED_PROZESSREGISTER_COLUMNS - set(columns)):
                errors.append(f"bpmn viewer provisioning Prozessregister columns missing {missing}")
            process_key = columns.get("ProcessKey")
            if isinstance(process_key, dict) and process_key.get("enforce_unique_values") is not True:
                errors.append("bpmn viewer provisioning Prozessregister ProcessKey must enforce unique values")
            if "ProcessKey" not in set(_strings(process_register.get("indexed_columns"))):
                errors.append("bpmn viewer provisioning Prozessregister ProcessKey must be indexed")
            for name in sorted(PROCESS_ROW_BPMN_FIELDS):
                column = columns.get(name)
                if isinstance(column, dict) and column.get("required") is not False:
                    errors.append(f"bpmn viewer provisioning Prozessregister column {name} must be nullable")
        for list_def in lists:
            errors.extend(_validate_list_definition(list_def))

    blocked = set(_strings(config.get("blocked_operations")))
    for missing in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked):
        errors.append(f"bpmn viewer provisioning blocked_operations missing {missing}")
    return errors


def build_bpmn_viewer_provisioning_plan(
    config: dict[str, Any],
    base_schema: dict[str, Any] | None = None,
) -> list[PlanOperation]:
    errors = validate_bpmn_viewer_provisioning_config(config)
    schema = base_schema or load_schema()
    errors.extend(validate_schema(schema))
    if errors:
        raise ValueError("invalid BPMN viewer provisioning config: " + "; ".join(errors))

    operations: list[PlanOperation] = []
    lists = config["sharepoint"]["lists"]
    document_libraries = config["sharepoint"]["document_libraries"]
    for workspace in schema["workspaces"]:
        workspace_id = workspace["id"]
        for library_def in document_libraries:
            operations.append(
                PlanOperation(
                    action="ensure_optional_bpmn_viewer_document_library",
                    workspace_id=workspace_id,
                    graph_method="POST",
                    graph_path="/sites/{site-id}/lists",
                    target=library_def["display_name"],
                    payload=list_create_payload(library_def),
                    owner_gate_required=True,
                )
            )
            for column_def in library_def.get("columns", []):
                operations.append(
                    PlanOperation(
                        action="ensure_optional_bpmn_viewer_library_column",
                        workspace_id=workspace_id,
                        graph_method="POST",
                        graph_path="/sites/{site-id}/lists/{list-id}/columns",
                        target=f"{library_def['display_name']}.{column_def['name']}",
                        payload=column_create_payload(column_def),
                        owner_gate_required=True,
                    )
                )
        for list_def in lists:
            operations.append(
                PlanOperation(
                    action="ensure_optional_bpmn_viewer_list",
                    workspace_id=workspace_id,
                    graph_method="POST",
                    graph_path="/sites/{site-id}/lists",
                    target=list_def["display_name"],
                    payload=list_create_payload(list_def),
                    owner_gate_required=True,
                )
            )
            for column_def in list_def["columns"]:
                operations.append(
                    PlanOperation(
                        action="ensure_optional_bpmn_viewer_column",
                        workspace_id=workspace_id,
                        graph_method="POST",
                        graph_path="/sites/{site-id}/lists/{list-id}/columns",
                        target=f"{list_def['display_name']}.{column_def['name']}",
                        payload=column_create_payload(column_def),
                        owner_gate_required=True,
                    )
                )
    return operations


def summarize_bpmn_viewer_provisioning_plan(operations: list[PlanOperation]) -> dict[str, Any]:
    by_action: dict[str, int] = {}
    by_workspace: dict[str, int] = {}
    for operation in operations:
        by_action[operation.action] = by_action.get(operation.action, 0) + 1
        by_workspace[operation.workspace_id] = by_workspace.get(operation.workspace_id, 0) + 1
    return {
        "operation_count": len(operations),
        "by_action": dict(sorted(by_action.items())),
        "by_workspace": dict(sorted(by_workspace.items())),
        "owner_gated_operations": sum(1 for operation in operations if operation.owner_gate_required),
        "mutates_tenant_now": False,
        "live_apply_implemented": False,
    }


def _validate_list_definition(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["bpmn viewer provisioning list entries must be objects"]
    display_name = value.get("display_name")
    if not isinstance(display_name, str) or not display_name:
        errors.append("bpmn viewer provisioning list display_name must be set")
    if value.get("template") != "genericList":
        errors.append(f"bpmn viewer provisioning list {display_name} template must be genericList")
    columns = value.get("columns")
    if not isinstance(columns, list) or not columns:
        errors.append(f"bpmn viewer provisioning list {display_name} columns must be a non-empty list")
        return errors
    errors.extend(_validate_columns(value, f"list {display_name}"))
    return errors


def _validate_columns(value: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    columns = value.get("columns")
    if not isinstance(columns, list) or not columns:
        errors.append(f"bpmn viewer provisioning {label} columns must be a non-empty list")
        return errors
    names: set[str] = set()
    for column in columns:
        if not isinstance(column, dict):
            errors.append(f"bpmn viewer provisioning {label} column entries must be objects")
            continue
        name = column.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"bpmn viewer provisioning {label} column name must be set")
        elif name in names:
            errors.append(f"bpmn viewer provisioning {label} has duplicate column {name}")
        else:
            names.add(name)
        column_type = column.get("type")
        if column_type not in SUPPORTED_COLUMN_TYPES:
            errors.append(f"bpmn viewer provisioning {label} column {name} has unsupported type {column_type}")
        if column_type == "choice" and not column.get("choices"):
            errors.append(f"bpmn viewer provisioning {label} choice column {name} must define choices")
    return errors


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _columns_by_name(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item["name"]: item
        for item in value.get("columns", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
