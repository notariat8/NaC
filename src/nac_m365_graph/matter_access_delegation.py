from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .schema import load_schema, validate_schema


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT = (
    REPO_ROOT / "workflows" / "contracts" / "m365-matter-access-delegation.contract.json"
)
REQUIRED_LISTS = {"Akten", "Vertretungsfreigaben", "AuditJournalLite"}
REQUIRED_LIST_COLUMNS = {
    "Akten": {
        "NacCaseId",
        "NotarTeam",
        "FederfuehrenderNotar",
        "Sachbearbeitung",
        "Status",
        "Vertraulichkeitsstufe",
    },
    "Vertretungsfreigaben": {
        "GrantId",
        "NacCaseId",
        "FromUser",
        "ToUser",
        "GrantedRole",
        "Reason",
        "ValidFrom",
        "ValidUntil",
        "ApprovedBy",
        "Status",
        "AuditCorrelationId",
    },
    "AuditJournalLite": {
        "EventId",
        "Timestamp",
        "Actor",
        "NacCaseId",
        "Action",
        "ObjectType",
        "ObjectId",
        "Reason",
        "CorrelationId",
    },
}
REQUIRED_TOOLS = {
    "matter_visibility_get",
    "matter_delegation_plan",
    "matter_delegation_revoke_plan",
    "matter_delegation_audit_list",
}
REQUIRED_TEMPLATES = {
    "read_primary_matter_assignment",
    "read_active_deputy_grants",
    "write_deputy_grant_request",
    "revoke_deputy_grant",
    "append_access_audit_event",
    "read_delegation_audit_events",
}
BLOCKED_OPERATIONS = {
    "unbounded_tenant_access",
    "one_team_for_all_notary_users",
    "default_all_staff_matter_visibility",
    "permanent_deputy_grant_without_valid_until",
    "deputy_grant_without_reason",
    "automation_approves_deputy_grant",
    "sharepoint_file_content_read",
    "raw_matter_payload_storage",
    "legacy_sharepoint_rest",
    "sharepoint_csom",
    "pnp",
    "microsoft_graph_sdk",
    "graph_beta",
    "secret_or_token_storage",
}


@dataclass(frozen=True, slots=True)
class MatterAccessPlanOperation:
    action: str
    workspace_id: str
    graph_method: str
    graph_path: str
    target_list: str
    tool_contract: str
    reads_items: bool
    reads_files: bool
    writes_items: bool
    owner_gate_required: bool
    executes_graph_requests_now: bool = False
    graph_rest_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_matter_access_delegation_contract(
    path: Path = DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_matter_access_delegation_contract(
    contract: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != "nac.m365-matter-access-delegation/v0.1":
        errors.append("matter access delegation schema_version is invalid")
    if contract.get("contract_id") != "m365.matter_access_delegation":
        errors.append("matter access delegation contract_id is invalid")
    if contract.get("status") != "offline_contract_no_live_apply":
        errors.append("matter access delegation status must be offline_contract_no_live_apply")

    graph = contract.get("graph")
    if not isinstance(graph, dict):
        errors.append("matter access delegation graph must be an object")
    else:
        if graph.get("base_url") != "https://graph.microsoft.com/v1.0":
            errors.append("matter access delegation graph.base_url must be Microsoft Graph v1.0")
        for flag in ("rest_only", "raw_http_required"):
            if graph.get(flag) is not True:
                errors.append(f"matter access delegation graph.{flag} must be true")
        for flag in ("sdk_allowed", "legacy_sharepoint_api_allowed", "graph_beta_allowed"):
            if graph.get(flag) is not False:
                errors.append(f"matter access delegation graph.{flag} must be false")

    scope = contract.get("scope")
    if not isinstance(scope, dict):
        errors.append("matter access delegation scope must be an object")
    else:
        for flag in ("offline_plan_only", "owner_gate_required_before_future_apply"):
            if scope.get(flag) is not True:
                errors.append(f"matter access delegation scope.{flag} must be true")
        for flag in (
            "executes_graph_requests_now",
            "tenant_mutation_allowed_now",
            "team_membership_mutation_allowed_now",
            "sharepoint_item_permission_mutation_allowed_now",
            "sharepoint_file_content_read_allowed_now",
            "matter_payload_storage_allowed_now",
            "stores_tokens_or_secrets",
        ):
            if scope.get(flag) is not False:
                errors.append(f"matter access delegation scope.{flag} must be false")

    workspace_model = contract.get("workspace_model")
    if not isinstance(workspace_model, dict):
        errors.append("matter access delegation workspace_model must be an object")
    else:
        if workspace_model.get("team_strategy") != "team_per_notary_team":
            errors.append("matter access delegation workspace_model.team_strategy must be team_per_notary_team")
        for flag in ("primary_assignment_is_one_to_one", "deputy_membership_is_timeboxed_exception"):
            if workspace_model.get(flag) is not True:
                errors.append(f"matter access delegation workspace_model.{flag} must be true")
        for flag in ("one_team_for_all_notary_users_allowed", "team_per_case_default_allowed"):
            if workspace_model.get(flag) is not False:
                errors.append(f"matter access delegation workspace_model.{flag} must be false")

    errors.extend(_validate_source_documents(contract))
    errors.extend(_validate_contract_lists(contract))
    if schema is not None:
        errors.extend(validate_schema(schema))
        errors.extend(_validate_schema_lists(schema))
    errors.extend(_validate_roles(contract))
    errors.extend(_validate_access_decision(contract))
    errors.extend(_validate_mcp_tool_contracts(contract))
    errors.extend(_validate_request_templates(contract))
    errors.extend(_validate_evidence_and_blocked_operations(contract))
    return errors


def build_matter_access_plan(
    contract: dict[str, Any],
    schema: dict[str, Any] | None = None,
) -> list[MatterAccessPlanOperation]:
    schema_payload = schema or load_schema()
    errors = validate_matter_access_delegation_contract(contract, schema_payload)
    if errors:
        raise ValueError("invalid matter access delegation contract: " + "; ".join(errors))

    templates = {
        str(template["id"]): template
        for template in contract["planned_graph_request_templates"]
        if isinstance(template, dict)
    }
    tool_by_action = {
        "read_primary_matter_assignment": "matter_visibility_get",
        "read_active_deputy_grants": "matter_visibility_get",
        "write_deputy_grant_request": "matter_delegation_plan",
        "revoke_deputy_grant": "matter_delegation_revoke_plan",
        "append_access_audit_event": "matter_delegation_plan",
        "read_delegation_audit_events": "matter_delegation_audit_list",
    }
    read_actions = {
        "read_primary_matter_assignment",
        "read_active_deputy_grants",
        "read_delegation_audit_events",
    }
    write_actions = {
        "write_deputy_grant_request",
        "revoke_deputy_grant",
        "append_access_audit_event",
    }
    operations: list[MatterAccessPlanOperation] = []
    for workspace in schema_payload["workspaces"]:
        workspace_id = workspace["id"]
        for action in (
            "read_primary_matter_assignment",
            "read_active_deputy_grants",
            "write_deputy_grant_request",
            "revoke_deputy_grant",
            "append_access_audit_event",
            "read_delegation_audit_events",
        ):
            template = templates[action]
            operations.append(
                MatterAccessPlanOperation(
                    action=action,
                    workspace_id=workspace_id,
                    graph_method=template["method"],
                    graph_path=template["path"],
                    target_list=template["list"],
                    tool_contract=tool_by_action[action],
                    reads_items=action in read_actions,
                    reads_files=False,
                    writes_items=action in write_actions,
                    owner_gate_required=action in write_actions,
                )
            )
    return operations


def summarize_matter_access_plan(
    operations: list[MatterAccessPlanOperation],
    contract: dict[str, Any],
) -> dict[str, Any]:
    by_action: dict[str, int] = {}
    by_workspace: dict[str, int] = {}
    by_tool: dict[str, int] = {}
    for operation in operations:
        by_action[operation.action] = by_action.get(operation.action, 0) + 1
        by_workspace[operation.workspace_id] = by_workspace.get(operation.workspace_id, 0) + 1
        by_tool[operation.tool_contract] = by_tool.get(operation.tool_contract, 0) + 1
    return {
        "contract_id": contract["contract_id"],
        "operation_count": len(operations),
        "by_action": dict(sorted(by_action.items())),
        "by_workspace": dict(sorted(by_workspace.items())),
        "by_tool_contract": dict(sorted(by_tool.items())),
        "list_count": len(contract["sharepoint_lists"]),
        "mcp_tool_contract_count": len(contract["mcp_tool_contracts"]),
        "owner_gated_operations": sum(1 for operation in operations if operation.owner_gate_required),
        "executes_graph_requests_now": False,
        "tenant_mutation_allowed_now": False,
        "team_membership_mutation_allowed_now": False,
        "reads_sharepoint_file_content": False,
        "stores_tokens_or_secrets": False,
        "stores_matter_payloads": False,
    }


def _validate_source_documents(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    sources = contract.get("source_documents")
    if not isinstance(sources, dict):
        return ["matter access delegation source_documents must be an object"]
    for key, value in sorted(sources.items()):
        if not isinstance(value, str) or not value:
            errors.append(f"matter access delegation source_documents.{key} must be a path")
            continue
        if not (REPO_ROOT / value).is_file():
            errors.append(f"matter access delegation source_documents.{key} points to missing file: {value}")
    return errors


def _validate_contract_lists(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lists = contract.get("sharepoint_lists")
    if not isinstance(lists, list) or not lists:
        return ["matter access delegation sharepoint_lists must be a non-empty list"]
    by_name = {item.get("display_name"): item for item in lists if isinstance(item, dict)}
    for missing in sorted(REQUIRED_LISTS - set(by_name)):
        errors.append(f"matter access delegation sharepoint_lists missing {missing}")
    for list_name, required_columns in sorted(REQUIRED_LIST_COLUMNS.items()):
        list_def = by_name.get(list_name)
        if not isinstance(list_def, dict):
            continue
        columns = set(_strings(list_def.get("required_columns")))
        for missing in sorted(required_columns - columns):
            errors.append(f"matter access delegation {list_name} required_columns missing {missing}")
    return errors


def _validate_schema_lists(schema: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lists = schema.get("sharepoint", {}).get("lists")
    if not isinstance(lists, list):
        return ["Teams/SharePoint schema sharepoint.lists must be a list"]
    by_name = {item.get("display_name"): item for item in lists if isinstance(item, dict)}
    for missing in sorted(REQUIRED_LISTS - set(by_name)):
        errors.append(f"Teams/SharePoint schema missing list {missing}")
    for list_name, required_columns in sorted(REQUIRED_LIST_COLUMNS.items()):
        list_def = by_name.get(list_name)
        if not isinstance(list_def, dict):
            continue
        columns = {
            column.get("name")
            for column in list_def.get("columns", [])
            if isinstance(column, dict) and isinstance(column.get("name"), str)
        }
        for missing in sorted(required_columns - columns):
            errors.append(f"Teams/SharePoint schema list {list_name} missing column {missing}")
    return errors


def _validate_roles(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    roles = contract.get("roles")
    if not isinstance(roles, list) or not roles:
        return ["matter access delegation roles must be a non-empty list"]
    role_ids = {item.get("id") for item in roles if isinstance(item, dict)}
    for missing in ("lead_notary", "assigned_notary_clerk", "deputy_notary", "deputy_notary_clerk", "runtime_service"):
        if missing not in role_ids:
            errors.append(f"matter access delegation roles missing {missing}")
    by_id = {item.get("id"): item for item in roles if isinstance(item, dict)}
    runtime = by_id.get("runtime_service")
    if isinstance(runtime, dict):
        if runtime.get("may_plan_graph_requests") is not True:
            errors.append("matter access delegation runtime_service must be allowed to plan Graph requests")
        for flag in ("may_read_matter_payload", "may_approve_deputy_grant"):
            if runtime.get(flag) is not False:
                errors.append(f"matter access delegation runtime_service.{flag} must be false")
    return errors


def _validate_access_decision(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    access = contract.get("access_decision")
    if not isinstance(access, dict):
        return ["matter access delegation access_decision must be an object"]
    for field in ("actor_id", "actor_role", "workspace_id", "case_id", "purpose", "correlation_id", "role_case_gate"):
        if field not in set(_strings(access.get("required_context"))):
            errors.append(f"matter access delegation access_decision.required_context missing {field}")
    for flag in (
        "grant_must_be_active",
        "grant_must_match_case",
        "grant_must_match_actor",
        "grant_must_include_reason",
        "grant_must_include_valid_from",
        "grant_must_include_valid_until",
        "grant_must_include_approver",
        "grant_must_include_audit_correlation_id",
    ):
        if access.get(flag) is not True:
            errors.append(f"matter access delegation access_decision.{flag} must be true")
    for flag in ("automation_may_approve_grant", "unbounded_team_access_allowed"):
        if access.get(flag) is not False:
            errors.append(f"matter access delegation access_decision.{flag} must be false")
    for field in ("Vertretungsfreigaben.Reason", "Vertretungsfreigaben.ValidUntil", "Vertretungsfreigaben.ApprovedBy"):
        if field not in set(_strings(access.get("deputy_grant_fields"))):
            errors.append(f"matter access delegation access_decision.deputy_grant_fields missing {field}")
    return errors


def _validate_mcp_tool_contracts(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tools = contract.get("mcp_tool_contracts")
    if not isinstance(tools, list) or not tools:
        return ["matter access delegation mcp_tool_contracts must be a non-empty list"]
    by_id = {item.get("id"): item for item in tools if isinstance(item, dict)}
    for missing in sorted(REQUIRED_TOOLS - set(by_id)):
        errors.append(f"matter access delegation mcp_tool_contracts missing {missing}")
    for tool_id, tool in sorted(by_id.items()):
        if tool.get("server") != "teams-sharepoint-data-mcp":
            errors.append(f"matter access delegation tool {tool_id} must target teams-sharepoint-data-mcp")
        if tool.get("mode") != "request_plan_only":
            errors.append(f"matter access delegation tool {tool_id} mode must be request_plan_only")
        if tool.get("requires_role_case_purpose_gate") is not True:
            errors.append(f"matter access delegation tool {tool_id} must require role/case/purpose gate")
        if tool.get("reads_files") is not False:
            errors.append(f"matter access delegation tool {tool_id} must not read files")
        if tool_id in {"matter_delegation_plan", "matter_delegation_revoke_plan"}:
            if tool.get("writes_items") is not True:
                errors.append(f"matter access delegation tool {tool_id} must plan writes")
            if tool.get("requires_owner_approval") is not True:
                errors.append(f"matter access delegation tool {tool_id} must require owner approval")
            for field in ("reason", "valid_until"):
                if tool_id == "matter_delegation_plan" and field not in set(_strings(tool.get("required_inputs"))):
                    errors.append(f"matter access delegation tool {tool_id} required_inputs missing {field}")
        else:
            if tool.get("writes_items") is not False:
                errors.append(f"matter access delegation tool {tool_id} must be read-only")
    return errors


def _validate_request_templates(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    templates = contract.get("planned_graph_request_templates")
    if not isinstance(templates, list) or not templates:
        return ["matter access delegation planned_graph_request_templates must be a non-empty list"]
    by_id = {item.get("id"): item for item in templates if isinstance(item, dict)}
    for missing in sorted(REQUIRED_TEMPLATES - set(by_id)):
        errors.append(f"matter access delegation planned_graph_request_templates missing {missing}")
    for template_id, template in sorted(by_id.items()):
        path = template.get("path")
        if not isinstance(path, str) or not path.startswith("/sites/{site-id}/"):
            errors.append(f"matter access delegation template {template_id} must target /sites/{{site-id}}")
            continue
        if "_api" in path or "graphbeta" in path or path.startswith("/beta"):
            errors.append(f"matter access delegation template {template_id} uses a blocked non-v1.0 path")
        if template.get("executes_now") is not False:
            errors.append(f"matter access delegation template {template_id} executes_now must be false")
        if template.get("list") not in REQUIRED_LISTS:
            errors.append(f"matter access delegation template {template_id} targets an unknown list")
    return errors


def _validate_evidence_and_blocked_operations(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence = set(_strings(contract.get("required_evidence_fields")))
    for field in (
        "reason",
        "valid_from",
        "valid_until",
        "approved_by_hash_or_directory_ref",
        "audit_event_ref",
        "no_file_content_read_attestation",
        "no_matter_payload_storage_attestation",
    ):
        if field not in evidence:
            errors.append(f"matter access delegation required_evidence_fields missing {field}")
    blocked = set(_strings(contract.get("blocked_operations")))
    for missing in sorted(BLOCKED_OPERATIONS - blocked):
        errors.append(f"matter access delegation blocked_operations missing {missing}")
    return errors


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
