from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.privileged_change import (  # noqa: E402
    build_privileged_change_plan,
    summarize_privileged_change_plan,
    validate_privileged_change_config,
)
from nac_m365_graph.provisioner import build_plan, summarize_plan  # noqa: E402
from nac_m365_graph.schema import validate_schema  # noqa: E402


CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-graph-data-plane.contract.json"
SCHEMA = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.teams-sharepoint.json"
PRIVILEGED_CHANGE_CONFIG = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.privileged-change-path.json"
)
PROVISIONED_STATE = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.provisioned.f8.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "teams-sharepoint-graph-data-plane.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "teams-sharepoint-graph-data-plane.md"
RUNBOOK_DE = REPO_ROOT / "docs" / "de" / "runbooks" / "m365-cli-admin-accelerator.md"
RUNBOOK_EN = REPO_ROOT / "docs" / "en" / "runbooks" / "m365-cli-admin-accelerator.md"
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
    schema = _read_json(SCHEMA, errors)
    privileged_change_config = _read_json(PRIVILEGED_CHANGE_CONFIG, errors)
    provisioned_state = _read_json(PROVISIONED_STATE, errors)
    if contract:
        errors.extend(_validate_contract(contract))
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
        "status": "planned_mvp_contract_and_skeleton_no_live_apply",
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
        if mcp.get("mcp_must_use_graph_rest_only") is not True:
            errors.append("mcp_boundary.mcp_must_use_graph_rest_only must be true")
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
        (RUNBOOK_DE, "Microsoft-365-CLI-Admin-Beschleuniger"),
        (RUNBOOK_DE, "Pflicht-Handoff Vor Nutzeraktion"),
        (RUNBOOK_DE, "Bootstrap-Route A: CLI-App durch `m365 setup`"),
        (RUNBOOK_DE, "Nach Login: NaC-App per CLI anlegen"),
        (RUNBOOK_DE, "Microsoft Entra Admin Center: Tenant Overview"),
        (RUNBOOK_DE, "Fehlerbild AADSTS7000218"),
        (RUNBOOK_DE, "https://microsoft.com/devicelogin"),
        (RUNBOOK_DE, "m365 request --url \"@graph/organization\""),
        (RUNBOOK_EN, "Microsoft 365 CLI Admin Accelerator"),
        (RUNBOOK_EN, "Required Handoff Before User Action"),
        (RUNBOOK_EN, "Bootstrap Route A: CLI App Through `m365 setup`"),
        (RUNBOOK_EN, "After Login: Create NaC App Through CLI"),
        (RUNBOOK_EN, "Microsoft Entra Admin Center: Tenant Overview"),
        (RUNBOOK_EN, "AADSTS7000218 Failure"),
        (RUNBOOK_EN, "https://microsoft.com/devicelogin"),
        (RUNBOOK_EN, "m365 request --url \"@graph/organization\""),
    )
    for path, marker in required_markers:
        if not path.is_file():
            errors.append(f"missing doc: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_secret_markers(path, text, errors)
        if marker not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker}")
    return errors


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
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker: {marker}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
