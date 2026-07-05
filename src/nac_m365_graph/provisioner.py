from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .schema import column_create_payload, list_create_payload, validate_schema


@dataclass(frozen=True, slots=True)
class PlanOperation:
    action: str
    workspace_id: str
    graph_method: str
    graph_path: str
    target: str
    payload: dict[str, Any] | None = None
    owner_gate_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_plan(schema: dict[str, Any]) -> list[PlanOperation]:
    errors = validate_schema(schema)
    if errors:
        raise ValueError("invalid Teams/SharePoint schema: " + "; ".join(errors))

    operations: list[PlanOperation] = []
    lists = schema["sharepoint"]["lists"]
    document_libraries = schema["sharepoint"]["document_libraries"]

    for workspace in schema["workspaces"]:
        workspace_id = workspace["id"]
        team_payload = {
            "template@odata.bind": "https://graph.microsoft.com/v1.0/teamsTemplates('standard')",
            "displayName": workspace["team_display_name"],
            "description": workspace["team_description"],
            "visibility": workspace["visibility"],
            "firstChannelName": workspace.get("first_channel_name", "Akten"),
        }
        operations.append(
            PlanOperation(
                action="ensure_team",
                workspace_id=workspace_id,
                graph_method="POST",
                graph_path="/teams",
                target=workspace["team_display_name"],
                payload=team_payload,
                owner_gate_required=True,
            )
        )
        operations.append(
            PlanOperation(
                action="trigger_files_folder",
                workspace_id=workspace_id,
                graph_method="GET",
                graph_path="/teams/{team-id}/channels/{channel-id}/filesFolder",
                target="team_channel_files_folder",
            )
        )
        operations.append(
            PlanOperation(
                action="resolve_group_site",
                workspace_id=workspace_id,
                graph_method="GET",
                graph_path="/groups/{group-id}/sites/root",
                target="connected_sharepoint_team_site",
            )
        )

        for list_def in lists:
            operations.append(
                PlanOperation(
                    action="ensure_list",
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
                        action="ensure_column",
                        workspace_id=workspace_id,
                        graph_method="POST",
                        graph_path="/sites/{site-id}/lists/{list-id}/columns",
                        target=f"{list_def['display_name']}.{column_def['name']}",
                        payload=column_create_payload(column_def),
                        owner_gate_required=True,
                    )
                )

        for library_def in document_libraries:
            operations.append(
                PlanOperation(
                    action="ensure_document_library",
                    workspace_id=workspace_id,
                    graph_method="POST",
                    graph_path="/sites/{site-id}/lists",
                    target=library_def["display_name"],
                    payload=list_create_payload(library_def),
                    owner_gate_required=True,
                )
            )

    return operations


def summarize_plan(operations: list[PlanOperation]) -> dict[str, Any]:
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
    }
