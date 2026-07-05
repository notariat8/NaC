from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PRIVILEGED_CHANGE_CONFIG = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.privileged-change-path.json"
)
DEFAULT_PROVISIONED_STATE = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.provisioned.f8.json"
)


@dataclass(frozen=True, slots=True)
class PrivilegedChangeOperation:
    action: str
    graph_method: str
    graph_path: str
    target: str
    payload: dict[str, Any] | None = None
    owner_gate_required: bool = True
    notes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_privileged_change_config(path: Path = DEFAULT_PRIVILEGED_CHANGE_CONFIG) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_provisioned_state(path: Path = DEFAULT_PROVISIONED_STATE) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_privileged_change_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if config.get("schema_version") != "nac.m365-privileged-change-path/v0.1":
        errors.append("schema_version must be nac.m365-privileged-change-path/v0.1")

    graph = config.get("graph")
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

    governance = config.get("governance")
    if not isinstance(governance, dict):
        errors.append("governance must be an object")
    else:
        for flag in (
            "standard_users_must_not_hold_m365_admin_permissions",
            "privileged_changes_must_run_through_app_or_api",
            "human_team_owner_still_required",
            "privileged_change_audit_required",
            "owner_gate_required_for_live_apply",
        ):
            if governance.get(flag) is not True:
                errors.append(f"governance.{flag} must be true")

    group = config.get("governance_group")
    if not isinstance(group, dict):
        errors.append("governance_group must be an object")
    else:
        if group.get("display_name") != "nac_platform_admins":
            errors.append("governance_group.display_name must be nac_platform_admins")
        if group.get("security_enabled") is not True:
            errors.append("governance_group.security_enabled must be true")
        if group.get("mail_enabled") is not False:
            errors.append("governance_group.mail_enabled must be false")
        if group.get("direct_application_owner_supported") is not False:
            errors.append("governance_group.direct_application_owner_supported must be false")

    technical_owner = config.get("technical_owner_user")
    if not isinstance(technical_owner, dict):
        errors.append("technical_owner_user must be an object")
    else:
        if technical_owner.get("display_name") != "funktion8":
            errors.append("technical_owner_user.display_name must be funktion8")
        if technical_owner.get("user_principal_name") != "funktion8@funktion8.de":
            errors.append("technical_owner_user.user_principal_name must be funktion8@funktion8.de")
        for flag in (
            "allowed_as_direct_application_owner",
            "allowed_as_team_creation_anchor",
            "must_not_be_sole_team_owner",
            "must_not_hold_m365_admin_roles",
            "license_terms_review_required",
        ):
            if technical_owner.get(flag) is not True:
                errors.append(f"technical_owner_user.{flag} must be true")

    applications = config.get("applications")
    if not isinstance(applications, list) or not applications:
        errors.append("applications must be a non-empty list")
    else:
        application_ids = {item.get("id") for item in applications if isinstance(item, dict)}
        for required in ("m365_provisioning_app", "m365_runtime_app"):
            if required not in application_ids:
                errors.append(f"applications missing {required}")
        for application in applications:
            if not isinstance(application, dict):
                errors.append("applications entries must be objects")
                continue
            if application.get("direct_owner") != "technical_owner_user":
                errors.append(f"application {application.get('id')} direct_owner must be technical_owner_user")
            permissions = application.get("bootstrap_application_permissions")
            if not isinstance(permissions, list) or not permissions:
                errors.append(f"application {application.get('id')} must define bootstrap_application_permissions")
            if application.get("id") == "m365_runtime_app":
                if "Sites.Selected" not in permissions:
                    errors.append("m365_runtime_app must request Sites.Selected")
                if application.get("sites_selected_grants") is not True:
                    errors.append("m365_runtime_app.sites_selected_grants must be true")

    team_owner_policy = config.get("team_owner_policy")
    if not isinstance(team_owner_policy, dict):
        errors.append("team_owner_policy must be an object")
    else:
        for flag in (
            "technical_owner_user_may_be_owner",
            "technical_owner_user_must_not_be_sole_owner",
            "licensed_human_team_owner_required",
            "verify_existing_team_owners_before_membership_mutation",
        ):
            if team_owner_policy.get(flag) is not True:
                errors.append(f"team_owner_policy.{flag} must be true")

    live_apply = config.get("live_apply")
    if not isinstance(live_apply, dict):
        errors.append("live_apply must be an object")
    else:
        if live_apply.get("enabled_by_default") is not False:
            errors.append("live_apply.enabled_by_default must be false")
        for flag in (
            "requires_owner_approval",
            "requires_drift_export_before",
            "requires_drift_export_after",
            "requires_license_terms_review_for_technical_owner_user",
        ):
            if live_apply.get(flag) is not True:
                errors.append(f"live_apply.{flag} must be true")
    return errors


def build_privileged_change_plan(
    config: dict[str, Any],
    provisioned_state: dict[str, Any],
) -> list[PrivilegedChangeOperation]:
    errors = validate_privileged_change_config(config)
    if errors:
        raise ValueError("invalid privileged change config: " + "; ".join(errors))

    operations: list[PrivilegedChangeOperation] = []
    technical_owner_upn = config["technical_owner_user"]["user_principal_name"]
    governance_group_name = config["governance_group"]["display_name"]

    operations.append(
        PrivilegedChangeOperation(
            action="resolve_technical_owner_user",
            graph_method="GET",
            graph_path=f"/users?$filter=userPrincipalName eq '{technical_owner_upn}'",
            target=technical_owner_upn,
            owner_gate_required=False,
            notes=[f"Resolve {technical_owner_upn} before any direct owner or team-owner operation."],
        )
    )
    operations.append(
        PrivilegedChangeOperation(
            action="ensure_governance_group",
            graph_method="POST",
            graph_path="/groups",
            target=governance_group_name,
            payload={
                "displayName": governance_group_name,
                "mailEnabled": False,
                "mailNickname": config["governance_group"]["mail_nickname"],
                "securityEnabled": True,
            },
            notes=["Governance group is not a direct application owner in Microsoft Graph."],
        )
    )

    for application in config["applications"]:
        display_name = application["display_name"]
        operations.extend(
            [
                PrivilegedChangeOperation(
                    action="ensure_application",
                    graph_method="POST",
                    graph_path="/applications",
                    target=display_name,
                    payload={
                        "displayName": display_name,
                        "signInAudience": "AzureADMyOrg",
                    },
                ),
                PrivilegedChangeOperation(
                    action="ensure_service_principal",
                    graph_method="POST",
                    graph_path="/servicePrincipals",
                    target=display_name,
                    payload={"appId": "{application-app-id}"},
                ),
                PrivilegedChangeOperation(
                    action="assign_direct_application_owner",
                    graph_method="POST",
                    graph_path="/applications/{application-object-id}/owners/$ref",
                    target=f"{display_name}:{technical_owner_upn}",
                    payload={"@odata.id": "https://graph.microsoft.com/v1.0/directoryObjects/{technical-owner-user-id}"},
                    notes=["Direct application owner must be a user or service principal, not nac_platform_admins."],
                ),
                PrivilegedChangeOperation(
                    action="assign_application_permissions",
                    graph_method="POST",
                    graph_path="/servicePrincipals/{application-service-principal-id}/appRoleAssignments",
                    target=display_name,
                    payload={
                        "resourceId": "{microsoft-graph-service-principal-id}",
                        "appRoleIds": application["bootstrap_application_permissions"],
                    },
                ),
            ]
        )

    for workspace in _workspaces(provisioned_state):
        team_id = workspace["team_id"]
        site_id = workspace["site_id"]
        operations.append(
            PrivilegedChangeOperation(
                action="verify_human_team_owner",
                graph_method="GET",
                graph_path=f"/groups/{team_id}/owners",
                target=workspace["team_display_name"],
                owner_gate_required=False,
                notes=[f"Technical owner {technical_owner_upn} must not be the only team owner."],
            )
        )
        operations.append(
            PrivilegedChangeOperation(
                action="grant_runtime_sites_selected_site_permission",
                graph_method="POST",
                graph_path=f"/sites/{site_id}/permissions",
                target=f"{workspace['id']}:NaC M365 Runtime",
                payload={
                    "roles": ["write"],
                    "grantedToIdentities": [
                        {
                            "application": {
                                "id": "{runtime-application-client-id}",
                                "displayName": "NaC M365 Runtime",
                            }
                        }
                    ],
                },
                notes=["Requires a separate owner-gated grant operation before runtime access works."],
            )
        )

    operations.extend(
        [
            PrivilegedChangeOperation(
                action="export_drift_before",
                graph_method="GET",
                graph_path="/applications?$filter=startswith(displayName,'NaC M365')",
                target="m365_privileged_change_evidence",
                owner_gate_required=True,
            ),
            PrivilegedChangeOperation(
                action="export_drift_after",
                graph_method="GET",
                graph_path="/applications?$filter=startswith(displayName,'NaC M365')",
                target="m365_privileged_change_evidence",
                owner_gate_required=True,
            ),
        ]
    )
    return operations


def summarize_privileged_change_plan(operations: list[PrivilegedChangeOperation]) -> dict[str, Any]:
    by_action: dict[str, int] = {}
    for operation in operations:
        by_action[operation.action] = by_action.get(operation.action, 0) + 1
    return {
        "operation_count": len(operations),
        "by_action": dict(sorted(by_action.items())),
        "owner_gated_operations": sum(1 for operation in operations if operation.owner_gate_required),
    }


def _workspaces(provisioned_state: dict[str, Any]) -> list[dict[str, Any]]:
    workspaces = provisioned_state.get("workspaces")
    if not isinstance(workspaces, list):
        return []
    return [workspace for workspace in workspaces if isinstance(workspace, dict)]
