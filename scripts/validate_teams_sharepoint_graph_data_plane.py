from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.bpmn_viewer_provisioning import (  # noqa: E402
    build_bpmn_viewer_provisioning_plan,
    summarize_bpmn_viewer_provisioning_plan,
    validate_bpmn_viewer_provisioning_config,
)
from nac_m365_graph.privileged_change import (  # noqa: E402
    build_privileged_change_plan,
    summarize_privileged_change_plan,
    validate_privileged_change_config,
)
from nac_m365_graph.provisioner import build_plan, summarize_plan  # noqa: E402
from nac_m365_graph.mcp_runtime import (  # noqa: E402
    RuntimeContext,
    build_tool_manifest,
    plan_tool_request,
    validate_mcp_contract,
)
from nac_m365_graph.schema import validate_schema  # noqa: E402


CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-graph-data-plane.contract.json"
MCP_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-data-mcp.contract.json"
SCHEMA = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.teams-sharepoint.json"
BPMN_VIEWER_CONFIG = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-bpmn-viewer.provisioning.json"
PRIVILEGED_CHANGE_CONFIG = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.privileged-change-path.json"
)
PROVISIONED_STATE = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.provisioned.f8.json"
PRIVILEGED_APPLIED_STATE = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.privileged-change-path.applied.f8.json"
)
RUNTIME_SMOKE_STATE = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.runtime-smoke.f8.json"
)
RUNTIME_METADATA_STATE = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.runtime-metadata.f8.json"
)
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "teams-sharepoint-graph-data-plane.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "teams-sharepoint-graph-data-plane.md"
RUNBOOK_DE = REPO_ROOT / "docs" / "de" / "runbooks" / "m365-cli-admin-accelerator.md"
RUNBOOK_EN = REPO_ROOT / "docs" / "en" / "runbooks" / "m365-cli-admin-accelerator.md"
BATCH_APPROVAL_DE = REPO_ROOT / "docs" / "de" / "operations" / "m365-mcp-batch-approval.md"
BATCH_APPROVAL_EN = REPO_ROOT / "docs" / "en" / "operations" / "m365-mcp-batch-approval.md"
PROVISIONER_SCRIPT = REPO_ROOT / "scripts" / "provision_teams_sharepoint_graph.py"
PACKAGE_ROOT = REPO_ROOT / "src" / "nac_m365_graph"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"

REQUIRED_LISTS = {
    "Akten",
    "Beteiligte",
    "AufgabenFristen",
    "Vertretungsfreigaben",
    "AuditJournalLite",
    "DokumentRegister",
}
REQUIRED_LIBRARIES = {"AktenDokumente", "Vorlagen"}
REQUIRED_WORKSPACES = {"notary_team_01", "notary_team_02"}
REQUIRED_ALLOWED_ENDPOINTS = {
    "POST /teams",
    "GET /teams/{team-id}",
    "GET /teams/{team-id}/channels",
    "GET /teams/{team-id}/channels/{channel-id}/filesFolder",
    "GET /groups/{group-id}/sites/root",
    "GET /sites/{site-id}/lists",
    "POST /sites/{site-id}/lists",
    "GET /sites/{site-id}/lists/{list-id}/columns",
    "POST /sites/{site-id}/lists/{list-id}/columns",
    "GET /sites/{site-id}/drives",
}
REQUIRED_FORBIDDEN_API_FAMILIES = {
    "sharepoint_legacy_rest_api",
    "sharepoint_csom",
    "pnp_powershell",
    "microsoft_graph_sdk",
    "sharepoint_sdk",
    "direct_sql",
    "office_automation_for_server_side_provisioning",
}
FORBIDDEN_SOURCE_MARKERS = {
    "GraphServiceClient",
    "msgraph",
    "office365.sharepoint",
    "shareplum",
    "ClientContext(",
    "m365 spo",
    "@spo",
    "@graphbeta",
}
PROHIBITED_SECRET_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Teams/SharePoint Graph data plane contract, schema, REST-only provisioner and docs are aligned.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT, errors)
    mcp_contract = _read_json(MCP_CONTRACT, errors)
    schema = _read_json(SCHEMA, errors)
    bpmn_viewer_config = _read_json(BPMN_VIEWER_CONFIG, errors)
    privileged_change_config = _read_json(PRIVILEGED_CHANGE_CONFIG, errors)
    provisioned_state = _read_json(PROVISIONED_STATE, errors)
    privileged_applied_state = _read_json(PRIVILEGED_APPLIED_STATE, errors)
    runtime_smoke_state = _read_json(RUNTIME_SMOKE_STATE, errors)
    runtime_metadata_state = _read_json(RUNTIME_METADATA_STATE, errors)
    if contract:
        errors.extend(_validate_contract(contract))
    if mcp_contract:
        errors.extend(_validate_mcp_runtime_contract(mcp_contract, contract, schema, bpmn_viewer_config))
    if schema:
        errors.extend(validate_schema(schema))
        errors.extend(_validate_schema_against_contract(schema, contract))
        try:
            plan = build_plan(schema)
            summary = summarize_plan(plan)
            if summary["operation_count"] < 100:
                errors.append("provisioning plan must include workspace, list, column and library operations")
        except ValueError as exc:
            errors.append(str(exc))
    if privileged_change_config:
        errors.extend(validate_privileged_change_config(privileged_change_config))
        if provisioned_state:
            try:
                privileged_plan = build_privileged_change_plan(privileged_change_config, provisioned_state)
                summary = summarize_privileged_change_plan(privileged_plan)
                required_actions = {
                    "resolve_technical_owner_user",
                    "ensure_governance_group",
                    "ensure_application",
                    "assign_direct_application_owner",
                    "grant_runtime_sites_selected_site_permission",
                    "verify_human_team_owner",
                }
                actions = set(summary["by_action"])
                for action in sorted(required_actions - actions):
                    errors.append(f"privileged change plan missing action {action}")
            except ValueError as exc:
                errors.append(str(exc))
    if bpmn_viewer_config and schema:
        errors.extend(validate_bpmn_viewer_provisioning_config(bpmn_viewer_config))
        try:
            bpmn_viewer_plan = build_bpmn_viewer_provisioning_plan(bpmn_viewer_config, schema)
            summary = summarize_bpmn_viewer_provisioning_plan(bpmn_viewer_plan)
            if summary["operation_count"] < 50:
                errors.append("BPMN viewer provisioning plan must include optional library, list and column operations")
            if summary["mutates_tenant_now"] is not False:
                errors.append("BPMN viewer provisioning plan must not mutate tenant state now")
        except ValueError as exc:
            errors.append(str(exc))
    if privileged_applied_state:
        errors.extend(
            _validate_privileged_applied_state(
                privileged_applied_state,
                privileged_change_config,
                provisioned_state,
            )
        )
    if runtime_smoke_state:
        errors.extend(
            _validate_runtime_smoke_state(
                runtime_smoke_state,
                privileged_applied_state,
                provisioned_state,
                schema,
            )
        )
    if runtime_metadata_state:
        errors.extend(
            _validate_runtime_metadata_state(
                runtime_metadata_state,
                runtime_smoke_state,
                provisioned_state,
                schema,
            )
        )
    errors.extend(_validate_docs())
    errors.extend(_validate_code_boundary())
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing JSON artifact: {path.relative_to(REPO_ROOT)}")
        return {}
    text = path.read_text(encoding="utf-8")
    _reject_secret_markers(path, text, errors)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return {}
    return payload


def _validate_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": "nac.m365-data-plane/v0.1",
        "contract_id": "m365.teams_sharepoint_graph_data_plane",
        "status": "final_m365_mvp_data_plane",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} must be {value}")

    target = payload.get("target_decision")
    if not isinstance(target, dict):
        errors.append("target_decision must be an object")
    else:
        if target.get("workspace_model") != "team_per_notary_team":
            errors.append("target_decision.workspace_model must be team_per_notary_team")
        for flag in (
            "graph_rest_only",
            "mcp_allowed_only_when_backed_by_graph_rest",
            "sharepoint_as_start_data_store",
            "nac_remains_process_logic_and_authorization_gate",
        ):
            if target.get(flag) is not True:
                errors.append(f"target_decision.{flag} must be true")

    graph = payload.get("graph_policy")
    if not isinstance(graph, dict):
        errors.append("graph_policy must be an object")
    else:
        if graph.get("base_url") != "https://graph.microsoft.com/v1.0":
            errors.append("graph_policy.base_url must be https://graph.microsoft.com/v1.0")
        if graph.get("raw_http_required") is not True:
            errors.append("graph_policy.raw_http_required must be true")
        for flag in ("sdk_usage_allowed", "legacy_sharepoint_api_allowed", "pnp_allowed", "csom_allowed"):
            if graph.get(flag) is not False:
                errors.append(f"graph_policy.{flag} must be false")
        endpoints = set(_strings(graph.get("allowed_endpoint_patterns")))
        for missing in sorted(REQUIRED_ALLOWED_ENDPOINTS - endpoints):
            errors.append(f"graph_policy.allowed_endpoint_patterns missing {missing}")
        forbidden = set(_strings(graph.get("forbidden_api_families")))
        for missing in sorted(REQUIRED_FORBIDDEN_API_FAMILIES - forbidden):
            errors.append(f"graph_policy.forbidden_api_families missing {missing}")

    admin_tooling = payload.get("admin_tooling")
    if not isinstance(admin_tooling, dict):
        errors.append("admin_tooling must be an object")
    else:
        if admin_tooling.get("cli_microsoft365_allowed") is not True:
            errors.append("admin_tooling.cli_microsoft365_allowed must be true")
        if admin_tooling.get("cli_microsoft365_role") != "owner_gated_admin_bootstrap_and_graph_smoke_only":
            errors.append(
                "admin_tooling.cli_microsoft365_role must be "
                "owner_gated_admin_bootstrap_and_graph_smoke_only"
            )
        for flag in ("cli_microsoft365_runtime_dependency_allowed", "cli_microsoft365_product_data_path_allowed"):
            if admin_tooling.get(flag) is not False:
                errors.append(f"admin_tooling.{flag} must be false")
        if admin_tooling.get("graph_request_base") != "@graph":
            errors.append("admin_tooling.graph_request_base must be @graph")
        if admin_tooling.get("graph_request_endpoint_version") != "v1.0":
            errors.append("admin_tooling.graph_request_endpoint_version must be v1.0")
        for flag in (
            "setup_can_create_cli_app_registration",
            "setup_create_app_uses_azure_cli_login",
            "direct_login_requires_explicit_app_id",
            "tenant_scoped_login_required",
            "separate_cli_app_and_nac_runtime_app_required",
        ):
            if admin_tooling.get(flag) is not True:
                errors.append(f"admin_tooling.{flag} must be true")
        for flag in (
            "legacy_sharepoint_rest_blocked",
            "admin_consent_owner_gate_required",
            "secrets_in_cli_output_must_not_be_committed",
        ):
            if admin_tooling.get(flag) is not True:
                errors.append(f"admin_tooling.{flag} must be true")
        allowed_commands = set(_strings(admin_tooling.get("allowed_commands")))
        for command in (
            "m365 setup",
            "m365 login --appId <app-id> --tenant <tenant-id> --authType deviceCode",
            "m365 status",
            "m365 request --url @graph/...",
            "m365 entra app add",
        ):
            if command not in allowed_commands:
                errors.append(f"admin_tooling.allowed_commands missing {command}")
        routes = set(_strings(admin_tooling.get("bootstrap_routes")))
        for route in (
            "m365_setup_create_cli_app_registration_via_azure_cli",
            "existing_cli_app_registration_device_code_login",
            "authenticated_m365_entra_app_add_for_nac_bootstrap_or_runtime_apps",
        ):
            if route not in routes:
                errors.append(f"admin_tooling.bootstrap_routes missing {route}")
        forbidden_commands = set(_strings(admin_tooling.get("forbidden_commands")))
        for command in (
            "m365 spo",
            "m365 request --url @spo/...",
            "m365 request --url .../_api/...",
            "m365 request --url @graphbeta/...",
        ):
            if command not in forbidden_commands:
                errors.append(f"admin_tooling.forbidden_commands missing {command}")
        if admin_tooling.get("runbook_de") != "docs/de/runbooks/m365-cli-admin-accelerator.md":
            errors.append("admin_tooling.runbook_de must point to the German CLI runbook")
        if admin_tooling.get("runbook_en") != "docs/en/runbooks/m365-cli-admin-accelerator.md":
            errors.append("admin_tooling.runbook_en must point to the English CLI runbook")

    handoff = payload.get("operator_handoff")
    if not isinstance(handoff, dict):
        errors.append("operator_handoff must be an object")
    else:
        for flag in ("prepared_request_required", "applies_before_requesting_user_values", "applies_before_admin_portal_actions"):
            if handoff.get(flag) is not True:
                errors.append(f"operator_handoff.{flag} must be true")
        for flag in (
            "plain_unprepared_value_requests_allowed",
            "secrets_in_chat_allowed",
            "live_tenant_change_without_explicit_owner_approval_allowed",
        ):
            if handoff.get(flag) is not False:
                errors.append(f"operator_handoff.{flag} must be false")
        sections = set(_strings(handoff.get("minimum_sections")))
        for section in (
            "purpose_and_risk",
            "exact_values_or_actions_needed",
            "source_links",
            "copy_paste_commands_with_placeholders",
            "secret_handling",
            "owner_gate_and_stop_condition",
            "expected_next_step_after_user_action",
        ):
            if section not in sections:
                errors.append(f"operator_handoff.minimum_sections missing {section}")

    permissions = payload.get("permission_model")
    if not isinstance(permissions, dict):
        errors.append("permission_model must be an object")
    else:
        bootstrap = set(_strings(permissions.get("bootstrap_application_permissions")))
        for permission in ("Team.Create", "Sites.Manage.All"):
            if permission not in bootstrap:
                errors.append(f"permission_model.bootstrap_application_permissions missing {permission}")
        if "Sites.Selected" not in set(_strings(permissions.get("runtime_target_permissions"))):
            errors.append("permission_model.runtime_target_permissions must include Sites.Selected")
        if permissions.get("team_member_mutation_in_mvp") is not False:
            errors.append("permission_model.team_member_mutation_in_mvp must be false")
        if permissions.get("runtime_app_must_be_site_scoped_after_bootstrap") is not True:
            errors.append("permission_model.runtime_app_must_be_site_scoped_after_bootstrap must be true")
        for flag in (
            "standard_users_must_not_hold_m365_admin_permissions",
            "privileged_m365_changes_must_run_through_app_or_api",
            "application_governance_group_required",
            "direct_application_owner_must_be_user_or_service_principal",
            "technical_application_owner_user_allowed",
            "human_team_owner_still_required",
            "technical_bootstrap_owner_user_allowed",
            "technical_bootstrap_owner_user_must_not_be_sole_owner",
            "licensed_human_team_owner_required",
            "technical_owner_must_not_hold_m365_admin_roles",
            "technical_owner_use_requires_license_terms_review",
            "privileged_change_audit_required",
        ):
            if permissions.get(flag) is not True:
                errors.append(f"permission_model.{flag} must be true")
        if permissions.get("application_governance_group_target") != "nac_platform_admins":
            errors.append("permission_model.application_governance_group_target must be nac_platform_admins")
        if permissions.get("direct_application_owner_group_supported_by_graph") is not False:
            errors.append("permission_model.direct_application_owner_group_supported_by_graph must be false")
        if permissions.get("technical_application_owner_user_target") != "funktion8@funktion8.de":
            errors.append("permission_model.technical_application_owner_user_target must be funktion8@funktion8.de")
        if permissions.get("technical_bootstrap_owner_user_target") != "funktion8@funktion8.de":
            errors.append("permission_model.technical_bootstrap_owner_user_target must be funktion8@funktion8.de")

    roadmap = payload.get("next_iteration_roadmap")
    if not isinstance(roadmap, list):
        errors.append("next_iteration_roadmap must be a list")
    else:
        ids = {item.get("id") for item in roadmap if isinstance(item, dict)}
        if "m365-application-owned-privileged-change-path" not in ids:
            errors.append(
                "next_iteration_roadmap must include m365-application-owned-privileged-change-path"
            )

    provisioning = payload.get("provisioning_model")
    if not isinstance(provisioning, dict):
        errors.append("provisioning_model must be an object")
    else:
        expected_paths = {
            "schema_artifact": "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json",
            "provisioner_script": "scripts/provision_teams_sharepoint_graph.py",
            "python_package": "src/nac_m365_graph",
        }
        for key, expected_path in expected_paths.items():
            if provisioning.get(key) != expected_path:
                errors.append(f"provisioning_model.{key} must be {expected_path}")
        for flag in ("team_creation_owner_gated", "schema_apply_owner_gated", "plan_without_credentials_required"):
            if provisioning.get(flag) is not True:
                errors.append(f"provisioning_model.{flag} must be true")
        for flag in ("live_apply_by_default", "stores_secret_values_in_repo", "stores_tenant_specific_ids_in_public_contract"):
            if provisioning.get(flag) is not False:
                errors.append(f"provisioning_model.{flag} must be false")

    workspace_templates = payload.get("workspace_templates")
    if not isinstance(workspace_templates, list):
        errors.append("workspace_templates must be a list")
    else:
        workspace_ids = {item.get("id") for item in workspace_templates if isinstance(item, dict)}
        for missing in sorted(REQUIRED_WORKSPACES - workspace_ids):
            errors.append(f"workspace_templates missing {missing}")

    if set(_strings(payload.get("required_lists"))) != REQUIRED_LISTS:
        errors.append("required_lists must match the MVP list set")
    if set(_strings(payload.get("required_document_libraries"))) != REQUIRED_LIBRARIES:
        errors.append("required_document_libraries must match the MVP library set")

    guardrails = payload.get("guardrails")
    if not isinstance(guardrails, dict):
        errors.append("guardrails must be an object")
    else:
        for flag in (
            "one_team_for_all_notary_users_allowed",
            "team_per_case_default_allowed",
            "private_channel_per_case_default_allowed",
            "standard_channel_is_security_boundary",
            "chat_files_as_matter_source_of_truth_allowed",
            "item_level_permissions_as_default_allowed",
            "raw_matter_payload_in_product_repo_allowed",
        ):
            if guardrails.get(flag) is not False:
                errors.append(f"guardrails.{flag} must be false")
        for flag in ("nac_role_case_gate_required", "substitution_requires_reason_duration_audit"):
            if guardrails.get(flag) is not True:
                errors.append(f"guardrails.{flag} must be true")

    mcp = payload.get("mcp_boundary")
    if not isinstance(mcp, dict):
        errors.append("mcp_boundary must be an object")
    else:
        if mcp.get("server_id") != "teams-sharepoint-data-mcp":
            errors.append("mcp_boundary.server_id must be teams-sharepoint-data-mcp")
        if mcp.get("current_transport") != "stdio":
            errors.append("mcp_boundary.current_transport must be stdio")
        if mcp.get("current_protocol_version") != "2025-11-25":
            errors.append("mcp_boundary.current_protocol_version must be 2025-11-25")
        if mcp.get("current_runtime_mode") != "request_planning_with_owner_gated_live_read":
            errors.append("mcp_boundary.current_runtime_mode must be request_planning_with_owner_gated_live_read")
        if mcp.get("mcp_must_use_graph_rest_only") is not True:
            errors.append("mcp_boundary.mcp_must_use_graph_rest_only must be true")
        if mcp.get("owner_gated_live_read_allowed") is not True:
            errors.append("mcp_boundary.owner_gated_live_read_allowed must be true")
        if set(_strings(mcp.get("owner_gated_live_read_allowed_tools"))) != {"case_get", "document_list"}:
            errors.append("mcp_boundary.owner_gated_live_read_allowed_tools must be case_get and document_list")
        if mcp.get("owner_gated_live_read_smoke_command") != "nac m365 teams-sharepoint mcp-live-read-smoke":
            errors.append("mcp_boundary.owner_gated_live_read_smoke_command is invalid")
        if (
            mcp.get("owner_gated_live_read_smoke_redacted_artifact")
            != "out/m365/teams-sharepoint/mcp-live-read-smoke.redacted.json"
        ):
            errors.append("mcp_boundary.owner_gated_live_read_smoke_redacted_artifact is invalid")
        for flag in (
            "owner_gated_live_read_smoke_stores_raw_graph_response",
            "owner_gated_live_read_smoke_stores_raw_matter_values",
        ):
            if mcp.get(flag) is not False:
                errors.append(f"mcp_boundary.{flag} must be false")
        if mcp.get("runtime_writes_executed_by_mcp") is not False:
            errors.append("mcp_boundary.runtime_writes_executed_by_mcp must be false")
        for tool in ("case_get", "case_create", "grant_request", "audit_append", "document_list"):
            if tool not in set(_strings(mcp.get("allowed_runtime_tools"))):
                errors.append(f"mcp_boundary.allowed_runtime_tools missing {tool}")

    docs = payload.get("documentation")
    if not isinstance(docs, dict):
        errors.append("documentation must be an object")
    else:
        if docs.get("de") != "docs/de/architecture/teams-sharepoint-graph-data-plane.md":
            errors.append("documentation.de must point to the German architecture doc")
        if docs.get("en") != "docs/en/architecture/teams-sharepoint-graph-data-plane.md":
            errors.append("documentation.en must point to the English architecture doc")

    return errors


def _validate_mcp_runtime_contract(
    payload: dict[str, Any],
    data_plane_contract: dict[str, Any],
    schema: dict[str, Any] | None = None,
    bpmn_viewer_config: dict[str, Any] | None = None,
) -> list[str]:
    errors = validate_mcp_contract(payload)
    if errors:
        return errors
    manifest = build_tool_manifest(payload)
    if manifest.get("serverId") != "teams-sharepoint-data-mcp":
        errors.append("teams-sharepoint-data-mcp manifest serverId is invalid")
    if manifest.get("executesGraphRequests") is not False:
        errors.append("teams-sharepoint-data-mcp manifest must not execute Graph requests")

    tool_names = {
        tool.get("name")
        for tool in manifest.get("tools", [])
        if isinstance(tool, dict)
    }
    data_plane_tools = set(
        _strings(data_plane_contract.get("mcp_boundary", {}).get("allowed_runtime_tools"))
    ) if data_plane_contract else set()
    if tool_names != data_plane_tools:
        errors.append("teams-sharepoint-data-mcp tools must match data-plane mcp_boundary.allowed_runtime_tools")

    optional_mcp_lists = _bpmn_viewer_mcp_list_names(bpmn_viewer_config)
    allowed_tool_lists = REQUIRED_LISTS | optional_mcp_lists
    for tool in payload.get("tools", []):
        if not isinstance(tool, dict):
            errors.append("teams-sharepoint-data-mcp tools entries must be objects")
            continue
        if tool.get("graph_method") not in {"GET", "POST", "PATCH"}:
            errors.append(f"teams-sharepoint-data-mcp {tool.get('id')} graph_method is invalid")
        if tool.get("list_name") not in allowed_tool_lists:
            errors.append(f"teams-sharepoint-data-mcp {tool.get('id')} list_name must target an MVP or optional BPMN viewer list")
        if tool.get("reads_files") is not False:
            errors.append(f"teams-sharepoint-data-mcp {tool.get('id')} must not read files")
        if tool.get("writes_items") is True and tool.get("graph_method") == "GET":
            errors.append(f"teams-sharepoint-data-mcp {tool.get('id')} write tool cannot use GET")
    if schema:
        errors.extend(_validate_mcp_schema_binding(payload, schema, bpmn_viewer_config))
    return errors


def _validate_mcp_schema_binding(
    payload: dict[str, Any],
    schema: dict[str, Any],
    bpmn_viewer_config: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    schema_lists = _schema_lists_by_name(schema)
    schema_lists.update(_bpmn_viewer_mcp_lists_by_name(bpmn_viewer_config))
    provisioned_state = _dummy_provisioned_state(schema_lists)
    context = RuntimeContext(
        actor_id="validator",
        actor_role="runtime_service",
        workspace_id="notary_team_01",
        purpose="schema_binding_validation",
        correlation_id="schema-binding-validation",
        case_id="case-1",
        role_case_gate="open",
        write_approved=True,
    )
    for tool in payload.get("tools", []):
        if not isinstance(tool, dict):
            continue
        tool_id = str(tool.get("id", ""))
        list_name = tool.get("list_name")
        if not isinstance(list_name, str) or list_name not in schema_lists:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} list_name must exist in SharePoint schema")
            continue
        list_schema = schema_lists[list_name]
        indexed_columns = set(_strings(list_schema.get("indexed_columns")))
        if tool_id in {"case_get", "document_list", "bpmn_viewer_overlay_get"} and "NacCaseId" not in indexed_columns:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} must filter on indexed NacCaseId")
        if tool_id == "bpmn_model_get" and "NacBpmnModelId" not in indexed_columns:
            errors.append("teams-sharepoint-data-mcp bpmn_model_get must filter on indexed NacBpmnModelId")
        if tool_id == "bpmn_model_get" and "ViewerEnabled" not in indexed_columns:
            errors.append("teams-sharepoint-data-mcp bpmn_model_get must filter on indexed ViewerEnabled")
        if tool_id == "process_register_list" and "ViewerEnabled" not in indexed_columns:
            errors.append("teams-sharepoint-data-mcp process_register_list must filter on indexed ViewerEnabled")
        sample_args = _sample_mcp_arguments(tool_id)
        if sample_args is None:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} missing schema-binding sample arguments")
            continue
        try:
            plan = plan_tool_request(payload, provisioned_state, context, tool_id, sample_args)
        except Exception as exc:  # noqa: BLE001 - validator reports contract errors, it does not raise them.
            errors.append(f"teams-sharepoint-data-mcp {tool_id} cannot be planned for schema binding: {exc}")
            continue
        if plan.list_name != list_name:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} plan list_name must match contract")
        if plan.payload is not None:
            errors.extend(_validate_mcp_payload_fields(tool_id, list_schema, plan.payload))
    return errors


def _validate_mcp_payload_fields(tool_id: str, list_schema: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fields = payload.get("fields")
    if not isinstance(fields, dict):
        fields = payload
    if not isinstance(fields, dict):
        errors.append(f"teams-sharepoint-data-mcp {tool_id} write payload must use SharePoint fields")
        return errors
    columns = _schema_columns_by_name(list_schema)
    for field_name, field_value in fields.items():
        column = columns.get(field_name)
        if column is None:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} writes unknown schema field {field_name}")
            continue
        if column.get("type") == "choice" and field_value not in set(_strings(column.get("choices"))):
            errors.append(
                f"teams-sharepoint-data-mcp {tool_id} writes invalid choice value {field_value!r} for {field_name}"
            )
    if tool_id.endswith("_create") or tool_id in {"grant_request", "audit_append"}:
        required_columns = {
            name
            for name, column in columns.items()
            if column.get("required") is True
        }
        missing = sorted(required_columns - set(fields))
        if missing:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} write payload missing required fields: {', '.join(missing)}")
    return errors


def _schema_lists_by_name(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["display_name"]): item
        for item in schema.get("sharepoint", {}).get("lists", [])
        if isinstance(item, dict) and isinstance(item.get("display_name"), str)
    }


def _bpmn_viewer_mcp_lists_by_name(config: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(config, dict):
        return {}
    sharepoint = config.get("sharepoint")
    if not isinstance(sharepoint, dict):
        return {}
    items: list[dict[str, Any]] = []
    for key in ("lists", "document_libraries"):
        values = sharepoint.get(key)
        if isinstance(values, list):
            items.extend(item for item in values if isinstance(item, dict))
    return {
        str(item["display_name"]): item
        for item in items
        if isinstance(item.get("display_name"), str)
    }


def _bpmn_viewer_mcp_list_names(config: dict[str, Any] | None) -> set[str]:
    return set(_bpmn_viewer_mcp_lists_by_name(config))


def _schema_columns_by_name(list_schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(column["name"]): column
        for column in list_schema.get("columns", [])
        if isinstance(column, dict) and isinstance(column.get("name"), str)
    }


def _dummy_provisioned_state(schema_lists: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "workspaces": [
            {
                "id": "notary_team_01",
                "site_id": "example.sharepoint.com,site-id,web-id",
                "lists": {
                    list_name: {"id": f"list-{index}"}
                    for index, list_name in enumerate(sorted(schema_lists), start=1)
                },
            }
        ]
    }


def _sample_mcp_arguments(tool_id: str) -> dict[str, Any] | None:
    samples: dict[str, dict[str, Any]] = {
        "case_get": {"case_id": "case-1"},
        "case_create": {
            "case_id": "case-1",
            "aktenzeichen": "SMOKE-1",
            "vorgangstyp": "immobilienkaufvertrag",
            "status": "Entwurf",
            "notar_team": "NaC-Notar-01",
            "vertraulichkeitsstufe": "Normal",
            "nac_workflow_version": "m365-mcp-smoke-v0.1",
            "kg_version": "kg-smoke-v0.1",
        },
        "case_update_status": {"item_id": "item-1", "status": "Vollzug"},
        "task_create": {
            "task_id": "task-1",
            "case_id": "case-1",
            "bpmn_step_code": "draft_review",
            "status": "Offen",
            "requires_notary_approval": True,
        },
        "grant_request": {
            "grant_id": "grant-1",
            "case_id": "case-1",
            "from_user": "from-user",
            "to_user": "to-user",
            "granted_role": "NurLesen",
            "reason": "synthetic validation",
            "valid_from": "2026-07-07T00:00:00Z",
            "valid_until": "2026-07-08T00:00:00Z",
            "approved_by": "validator",
            "status": "Aktiv",
        },
        "audit_append": {
            "event_id": "event-1",
            "case_id": "case-1",
            "timestamp": "2026-07-07T00:00:00Z",
            "action": "CaseCreated",
            "object_type": "Case",
            "object_id": "case-1",
        },
        "document_list": {"case_id": "case-1"},
        "bpmn_model_get": {"bpmn_model_id": "bpmn-model-1"},
        "process_register_list": {},
        "bpmn_viewer_overlay_get": {"case_id": "case-1"},
    }
    sample = samples.get(tool_id)
    return dict(sample) if sample is not None else None


def _validate_schema_against_contract(schema: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not contract:
        return errors
    lists = {
        item.get("display_name")
        for item in schema.get("sharepoint", {}).get("lists", [])
        if isinstance(item, dict)
    }
    libraries = {
        item.get("display_name")
        for item in schema.get("sharepoint", {}).get("document_libraries", [])
        if isinstance(item, dict)
    }
    if lists != set(_strings(contract.get("required_lists"))):
        errors.append("schema lists must match contract.required_lists")
    if libraries != set(_strings(contract.get("required_document_libraries"))):
        errors.append("schema document libraries must match contract.required_document_libraries")
    return errors


def _validate_privileged_applied_state(
    state: dict[str, Any],
    config: dict[str, Any],
    provisioned_state: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if state.get("state_version") != "nac.m365-privileged-change-path.applied/v0.1":
        errors.append("privileged applied state_version must be nac.m365-privileged-change-path.applied/v0.1")
    if state.get("source_config") != "deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json":
        errors.append("privileged applied source_config must point to nac-mvp.privileged-change-path.json")

    tenant = state.get("tenant")
    if not isinstance(tenant, dict) or tenant.get("tenant_id") != "870c862b-56f7-4c9b-b0d9-f1f7d32c835c":
        errors.append("privileged applied tenant.tenant_id must match f8 tenant")

    config_owner = config.get("technical_owner_user", {}) if isinstance(config, dict) else {}
    technical_owner = state.get("technical_owner_user")
    if not isinstance(technical_owner, dict):
        errors.append("privileged applied technical_owner_user must be an object")
    else:
        if technical_owner.get("user_principal_name") != config_owner.get("user_principal_name"):
            errors.append("privileged applied technical owner must match privileged config")
        if technical_owner.get("assigned_license_count") != 0:
            errors.append("privileged applied technical owner must remain unlicensed in the captured state")
        _require_nonempty_string(technical_owner, "id", "privileged applied technical_owner_user", errors)

    config_group = config.get("governance_group", {}) if isinstance(config, dict) else {}
    governance_group = state.get("governance_group")
    if not isinstance(governance_group, dict):
        errors.append("privileged applied governance_group must be an object")
    else:
        if governance_group.get("display_name") != config_group.get("display_name"):
            errors.append("privileged applied governance_group.display_name must match privileged config")
        if governance_group.get("security_enabled") is not True:
            errors.append("privileged applied governance_group.security_enabled must be true")
        if governance_group.get("mail_enabled") is not False:
            errors.append("privileged applied governance_group.mail_enabled must be false")
        _require_nonempty_string(governance_group, "id", "privileged applied governance_group", errors)

    applications = state.get("applications")
    config_apps = {
        app.get("id"): app
        for app in config.get("applications", [])
        if isinstance(app, dict) and isinstance(app.get("id"), str)
    } if isinstance(config, dict) else {}
    if not isinstance(applications, dict):
        errors.append("privileged applied applications must be an object")
        applications = {}
    for app_id in ("m365_provisioning_app", "m365_runtime_app"):
        app = applications.get(app_id)
        config_app = config_apps.get(app_id, {})
        if not isinstance(app, dict):
            errors.append(f"privileged applied applications missing {app_id}")
            continue
        for key in ("application_object_id", "client_id", "service_principal_id"):
            _require_nonempty_string(app, key, f"privileged applied {app_id}", errors)
        if app.get("display_name") != config_app.get("display_name"):
            errors.append(f"privileged applied {app_id}.display_name must match privileged config")
        if set(_strings(app.get("application_permissions"))) != set(_strings(config_app.get("bootstrap_application_permissions"))):
            errors.append(f"privileged applied {app_id}.application_permissions must match privileged config")
        if app.get("runtime_allowed") is not bool(config_app.get("runtime_allowed")):
            errors.append(f"privileged applied {app_id}.runtime_allowed must match privileged config")
        if app.get("direct_technical_owner_user") != config_owner.get("user_principal_name"):
            errors.append(f"privileged applied {app_id}.direct_technical_owner_user must match technical owner")

    team_owner_checks = state.get("team_owner_checks")
    provisioned_workspaces = {
        workspace.get("id"): workspace
        for workspace in provisioned_state.get("workspaces", [])
        if isinstance(workspace, dict) and isinstance(workspace.get("id"), str)
    } if isinstance(provisioned_state, dict) else {}
    if not isinstance(team_owner_checks, list):
        errors.append("privileged applied team_owner_checks must be a list")
    else:
        by_workspace = {item.get("workspace_id"): item for item in team_owner_checks if isinstance(item, dict)}
        for workspace_id in sorted(REQUIRED_WORKSPACES):
            check = by_workspace.get(workspace_id)
            if not isinstance(check, dict):
                errors.append(f"privileged applied team_owner_checks missing {workspace_id}")
                continue
            if check.get("team_id") != provisioned_workspaces.get(workspace_id, {}).get("team_id"):
                errors.append(f"privileged applied {workspace_id} team_id must match provisioned state")
            if not isinstance(check.get("licensed_human_owner_count"), int) or check["licensed_human_owner_count"] < 1:
                errors.append(f"privileged applied {workspace_id} must retain at least one licensed human owner")

    site_permissions = state.get("runtime_site_permissions")
    runtime_app = applications.get("m365_runtime_app") if isinstance(applications, dict) else None
    runtime_client_id = runtime_app.get("client_id") if isinstance(runtime_app, dict) else None
    if not isinstance(site_permissions, list):
        errors.append("privileged applied runtime_site_permissions must be a list")
    else:
        by_workspace = {item.get("workspace_id"): item for item in site_permissions if isinstance(item, dict)}
        for workspace_id in sorted(REQUIRED_WORKSPACES):
            permission = by_workspace.get(workspace_id)
            if not isinstance(permission, dict):
                errors.append(f"privileged applied runtime_site_permissions missing {workspace_id}")
                continue
            if permission.get("site_id") != provisioned_workspaces.get(workspace_id, {}).get("site_id"):
                errors.append(f"privileged applied {workspace_id} site_id must match provisioned state")
            if permission.get("application_client_id") != runtime_client_id:
                errors.append(f"privileged applied {workspace_id} application_client_id must match runtime app")
            if permission.get("role") != "write":
                errors.append(f"privileged applied {workspace_id} role must be write")
    return errors


def _validate_runtime_smoke_state(
    state: dict[str, Any],
    privileged_state: dict[str, Any],
    provisioned_state: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if state.get("state_version") != "nac.m365-runtime-smoke/v0.1":
        errors.append("runtime smoke state_version must be nac.m365-runtime-smoke/v0.1")
    if state.get("source_provisioned_state") != "deploy/m365/teams-sharepoint/nac-mvp.provisioned.f8.json":
        errors.append("runtime smoke source_provisioned_state must point to nac-mvp.provisioned.f8.json")
    if state.get("source_privileged_applied_state") != "deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.applied.f8.json":
        errors.append("runtime smoke source_privileged_applied_state must point to privileged applied state")

    tenant = state.get("tenant")
    if not isinstance(tenant, dict) or tenant.get("tenant_id") != "870c862b-56f7-4c9b-b0d9-f1f7d32c835c":
        errors.append("runtime smoke tenant.tenant_id must match f8 tenant")

    runtime = state.get("runtime_application")
    privileged_apps = privileged_state.get("applications", {}) if isinstance(privileged_state, dict) else {}
    privileged_runtime = privileged_apps.get("m365_runtime_app") if isinstance(privileged_apps, dict) else {}
    if not isinstance(runtime, dict):
        errors.append("runtime smoke runtime_application must be an object")
    else:
        if runtime.get("client_id") != privileged_runtime.get("client_id"):
            errors.append("runtime smoke runtime application client_id must match privileged state")
        if runtime.get("application_object_id") != privileged_runtime.get("application_object_id"):
            errors.append("runtime smoke runtime application object id must match privileged state")
        if runtime.get("authentication_mode") != "client_credentials_with_certificate":
            errors.append("runtime smoke authentication_mode must be client_credentials_with_certificate")
        _require_nonempty_string(runtime, "certificate_thumbprint_sha1", "runtime smoke runtime_application", errors)
        _require_nonempty_string(runtime, "certificate_expires_at_utc", "runtime smoke runtime_application", errors)
        if set(_strings(runtime.get("application_permissions"))) != {"Sites.Selected"}:
            errors.append("runtime smoke runtime_application.application_permissions must be Sites.Selected only")

    smoke = state.get("smoke_result")
    if not isinstance(smoke, dict):
        errors.append("runtime smoke smoke_result must be an object")
    else:
        if smoke.get("status") != "PASSED":
            errors.append("runtime smoke status must be PASSED")
        if smoke.get("sites_read") != len(REQUIRED_WORKSPACES):
            errors.append("runtime smoke sites_read must match required workspaces")
        if smoke.get("missing_lists") != 0:
            errors.append("runtime smoke missing_lists must be 0")

    provisioned_workspaces = {
        workspace.get("id"): workspace
        for workspace in provisioned_state.get("workspaces", [])
        if isinstance(workspace, dict) and isinstance(workspace.get("id"), str)
    } if isinstance(provisioned_state, dict) else {}
    schema_lists = _schema_list_names(schema)
    workspaces = state.get("workspaces")
    if not isinstance(workspaces, list):
        errors.append("runtime smoke workspaces must be a list")
    else:
        by_workspace = {item.get("workspace_id"): item for item in workspaces if isinstance(item, dict)}
        for workspace_id in sorted(REQUIRED_WORKSPACES):
            workspace = by_workspace.get(workspace_id)
            provisioned = provisioned_workspaces.get(workspace_id, {})
            if not isinstance(workspace, dict):
                errors.append(f"runtime smoke workspaces missing {workspace_id}")
                continue
            if workspace.get("site_id") != provisioned.get("site_id"):
                errors.append(f"runtime smoke {workspace_id} site_id must match provisioned state")
            if workspace.get("expected_list_count") != len(schema_lists):
                errors.append(f"runtime smoke {workspace_id} expected_list_count must match schema lists")
            if workspace.get("observed_list_count", 0) < workspace.get("expected_list_count", 0):
                errors.append(f"runtime smoke {workspace_id} observed_list_count must cover expected lists")
            if workspace.get("missing_lists") != []:
                errors.append(f"runtime smoke {workspace_id} missing_lists must be empty")
    return errors


def _validate_runtime_metadata_state(
    state: dict[str, Any],
    runtime_smoke_state: dict[str, Any],
    provisioned_state: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if state.get("state_version") != "nac.m365-runtime-metadata/v0.1":
        errors.append("runtime metadata state_version must be nac.m365-runtime-metadata/v0.1")
    if state.get("source_runtime_smoke_state") != "deploy/m365/teams-sharepoint/nac-mvp.runtime-smoke.f8.json":
        errors.append("runtime metadata source_runtime_smoke_state must point to runtime smoke state")
    if state.get("source_provisioned_state") != "deploy/m365/teams-sharepoint/nac-mvp.provisioned.f8.json":
        errors.append("runtime metadata source_provisioned_state must point to provisioned state")

    runtime = state.get("runtime_application")
    smoke_runtime = runtime_smoke_state.get("runtime_application", {}) if isinstance(runtime_smoke_state, dict) else {}
    if not isinstance(runtime, dict):
        errors.append("runtime metadata runtime_application must be an object")
    else:
        if runtime.get("client_id") != smoke_runtime.get("client_id"):
            errors.append("runtime metadata runtime application client_id must match runtime smoke")
        if runtime.get("certificate_thumbprint_sha1") != smoke_runtime.get("certificate_thumbprint_sha1"):
            errors.append("runtime metadata certificate thumbprint must match runtime smoke")
        if runtime.get("authentication_mode") != "client_credentials_with_certificate":
            errors.append("runtime metadata authentication_mode must be client_credentials_with_certificate")
        if set(_strings(runtime.get("application_permissions"))) != {"Sites.Selected"}:
            errors.append("runtime metadata runtime_application.application_permissions must be Sites.Selected only")

    metadata = state.get("metadata_result")
    if not isinstance(metadata, dict):
        errors.append("runtime metadata metadata_result must be an object")
    else:
        if metadata.get("status") != "PASSED":
            errors.append("runtime metadata status must be PASSED")
        if metadata.get("sites_read") != len(REQUIRED_WORKSPACES):
            errors.append("runtime metadata sites_read must match required workspaces")
        if metadata.get("missing_lists") != 0:
            errors.append("runtime metadata missing_lists must be 0")
        if metadata.get("missing_document_libraries") != 0:
            errors.append("runtime metadata missing_document_libraries must be 0")
        if metadata.get("list_items_read") != 0:
            errors.append("runtime metadata list_items_read must be 0")

    provisioned_workspaces = {
        workspace.get("id"): workspace
        for workspace in provisioned_state.get("workspaces", [])
        if isinstance(workspace, dict) and isinstance(workspace.get("id"), str)
    } if isinstance(provisioned_state, dict) else {}
    schema_lists = set(_schema_list_names(schema))
    schema_libraries = set(_schema_library_names(schema))
    workspaces = state.get("workspaces")
    if not isinstance(workspaces, list):
        errors.append("runtime metadata workspaces must be a list")
    else:
        by_workspace = {item.get("workspace_id"): item for item in workspaces if isinstance(item, dict)}
        for workspace_id in sorted(REQUIRED_WORKSPACES):
            workspace = by_workspace.get(workspace_id)
            provisioned = provisioned_workspaces.get(workspace_id, {})
            if not isinstance(workspace, dict):
                errors.append(f"runtime metadata workspaces missing {workspace_id}")
                continue
            if workspace.get("site_id") != provisioned.get("site_id"):
                errors.append(f"runtime metadata {workspace_id} site_id must match provisioned state")
            if set(_strings(workspace.get("lists"))) != schema_lists:
                errors.append(f"runtime metadata {workspace_id} lists must match schema lists")
            if set(_strings(workspace.get("document_libraries"))) != schema_libraries:
                errors.append(
                    f"runtime metadata {workspace_id} document_libraries must match schema document libraries"
                )
            if workspace.get("missing_lists") != []:
                errors.append(f"runtime metadata {workspace_id} missing_lists must be empty")
            if workspace.get("missing_document_libraries") != []:
                errors.append(f"runtime metadata {workspace_id} missing_document_libraries must be empty")
    return errors


def _require_nonempty_string(payload: dict[str, Any], key: str, label: str, errors: list[str]) -> None:
    if not isinstance(payload.get(key), str) or not payload[key]:
        errors.append(f"{label}.{key} must be a non-empty string")


def _schema_list_names(schema: dict[str, Any]) -> list[str]:
    return [
        item["display_name"]
        for item in schema.get("sharepoint", {}).get("lists", [])
        if isinstance(item, dict) and isinstance(item.get("display_name"), str)
    ]


def _schema_library_names(schema: dict[str, Any]) -> list[str]:
    return [
        item["display_name"]
        for item in schema.get("sharepoint", {}).get("document_libraries", [])
        if isinstance(item, dict) and isinstance(item.get("display_name"), str)
    ]


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Teams-SharePoint-Graph-Datenebene"),
        (DOC_DE, "Microsoft Teams Team pro Notar-Team"),
        (DOC_DE, "Graph-REST-Grenze"),
        (DOC_DE, "Privilegierte Änderungen Über App/API"),
        (DOC_DE, "M365 Provisioning"),
        (DOC_DE, "Microsoft-Graph-Grenzen"),
        (DOC_DE, "technische Bootstrap-Owner-User `technical_owner_user`"),
        (DOC_DE, "privileged-plan"),
        (DOC_DE, "CLI for Microsoft 365"),
        (DOC_DE, "`teams-sharepoint-data-mcp`"),
        (DOC_DE, "mcp-manifest"),
        (DOC_DE, "mcp-stdio"),
        (DOC_DE, "mcp-live-read"),
        (DOC_DE, "mcp-live-read-smoke"),
        (DOC_DE, "mcp-live-read-smoke.redacted.json"),
        (DOC_DE, "owner-gated Live-Read-Modus"),
        (DOC_DE, "MCP-Protokollversion `2025-11-25`"),
        (DOC_DE, "nac_m365_graph.mcp_runtime"),
        (DOC_DE, "nac_m365_graph.mcp_stdio"),
        (DOC_EN, "Teams SharePoint Graph Data Plane"),
        (DOC_EN, "Microsoft Teams team per notary team"),
        (DOC_EN, "Graph REST Boundary"),
        (DOC_EN, "Privileged Changes Through App/API"),
        (DOC_EN, "M365 Provisioning"),
        (DOC_EN, "Microsoft Graph boundary"),
        (DOC_EN, "technical bootstrap owner user `technical_owner_user`"),
        (DOC_EN, "privileged-plan"),
        (DOC_EN, "CLI for Microsoft 365"),
        (DOC_EN, "`teams-sharepoint-data-mcp`"),
        (DOC_EN, "mcp-manifest"),
        (DOC_EN, "mcp-stdio"),
        (DOC_EN, "mcp-live-read"),
        (DOC_EN, "mcp-live-read-smoke"),
        (DOC_EN, "mcp-live-read-smoke.redacted.json"),
        (DOC_EN, "owner-gated live-read mode"),
        (DOC_EN, "MCP protocol version `2025-11-25`"),
        (DOC_EN, "nac_m365_graph.mcp_runtime"),
        (DOC_EN, "nac_m365_graph.mcp_stdio"),
        (RUNBOOK_DE, "Microsoft-365-CLI-Admin-Beschleuniger"),
        (RUNBOOK_DE, "Pflicht-Handoff Vor Nutzeraktion"),
        (RUNBOOK_DE, "Bootstrap-Route A: CLI-App durch `m365 setup`"),
        (RUNBOOK_DE, "Nach Login: NaC-App per CLI anlegen"),
        (RUNBOOK_DE, "Microsoft Entra Admin Center: Tenant Overview"),
        (RUNBOOK_DE, "Fehlerbild AADSTS7000218"),
        (RUNBOOK_DE, "https://microsoft.com/devicelogin"),
        (RUNBOOK_DE, "m365 request --url \"@graph/organization\""),
        (RUNBOOK_DE, "privileged-apply --owner-approved"),
        (RUNBOOK_DE, "runtime-smoke --owner-approved"),
        (RUNBOOK_DE, "runtime-metadata --owner-approved"),
        (RUNBOOK_EN, "Microsoft 365 CLI Admin Accelerator"),
        (RUNBOOK_EN, "Required Handoff Before User Action"),
        (RUNBOOK_EN, "Bootstrap Route A: CLI App Through `m365 setup`"),
        (RUNBOOK_EN, "After Login: Create NaC App Through CLI"),
        (RUNBOOK_EN, "Microsoft Entra Admin Center: Tenant Overview"),
        (RUNBOOK_EN, "AADSTS7000218 Failure"),
        (RUNBOOK_EN, "https://microsoft.com/devicelogin"),
        (RUNBOOK_EN, "m365 request --url \"@graph/organization\""),
        (RUNBOOK_EN, "privileged-apply --owner-approved"),
        (RUNBOOK_EN, "runtime-smoke --owner-approved"),
        (RUNBOOK_EN, "runtime-metadata --owner-approved"),
    )
    for path, marker in required_markers:
        _validate_doc_required_marker(path, marker, errors)
    _validate_product_edge_docs(errors)
    return errors


def _validate_product_edge_docs(errors: list[str]) -> None:
    for path, marker in _product_edge_required_doc_markers():
        _validate_doc_required_marker(path, marker, errors)
    for path, marker in _product_edge_prohibited_doc_markers():
        _validate_doc_prohibited_marker(path, marker, errors)


def _product_edge_required_doc_markers() -> tuple[tuple[Path, str], ...]:
    return (
        (DOC_DE, "scripts/nac.py m365 teams-sharepoint privileged-plan"),
        (DOC_EN, "scripts/nac.py m365 teams-sharepoint privileged-plan"),
        (BATCH_APPROVAL_DE, "`release-gate-run` ist der Standard-Betriebsnachweis"),
        (BATCH_APPROVAL_EN, "`release-gate-run` is the standard runtime evidence"),
        (BATCH_APPROVAL_DE, "Diagnose-/Komponentenpfad"),
        (BATCH_APPROVAL_EN, "diagnostic/component path"),
    )


def _product_edge_prohibited_doc_markers() -> tuple[tuple[Path, str], ...]:
    return (
        (DOC_DE, "python3 scripts/provision_teams_sharepoint_graph.py"),
        (DOC_EN, "python3 scripts/provision_teams_sharepoint_graph.py"),
        (BATCH_APPROVAL_DE, "Die Smoke Suite ist der Standard-Betriebsnachweis"),
        (BATCH_APPROVAL_EN, "The smoke suite is the standard runtime evidence"),
    )


def _validate_doc_required_marker(path: Path, marker: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing doc: {_display_path(path)}")
        return
    text = path.read_text(encoding="utf-8")
    _reject_secret_markers(path, text, errors)
    if marker not in text:
        errors.append(f"{_display_path(path)} missing marker {marker}")


def _validate_doc_prohibited_marker(path: Path, marker: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing doc: {_display_path(path)}")
        return
    text = path.read_text(encoding="utf-8")
    _reject_secret_markers(path, text, errors)
    if marker in text:
        errors.append(f"{_display_path(path)} contains prohibited product-edge marker {marker}")


def _validate_code_boundary() -> list[str]:
    errors: list[str] = []
    for path in (PROVISIONER_SCRIPT, QUALITY_GATE):
        if not path.is_file():
            errors.append(f"missing code file: {path.relative_to(REPO_ROOT)}")
    if not PACKAGE_ROOT.is_dir():
        errors.append("missing src/nac_m365_graph package")
        return errors

    for path in sorted(PACKAGE_ROOT.glob("*.py")) + [PROVISIONER_SCRIPT]:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        _reject_secret_markers(path, text, errors)
        for marker in FORBIDDEN_SOURCE_MARKERS:
            if marker in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} contains forbidden SDK/API marker: {marker}")
    quality_text = QUALITY_GATE.read_text(encoding="utf-8") if QUALITY_GATE.is_file() else ""
    if "teams_sharepoint_graph_data_plane" not in quality_text:
        errors.append("quality_gate.py must include teams_sharepoint_graph_data_plane")
    return errors


def _reject_secret_markers(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_SECRET_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{_display_path(path)} contains prohibited marker: {marker}")


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
