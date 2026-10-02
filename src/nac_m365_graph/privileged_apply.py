from __future__ import annotations

import urllib.parse
from typing import Any, Protocol

from .graph_client import GraphHttpError
from .privileged_change import validate_privileged_change_config
from .team_ownership import TECHNICAL_OWNER_UPN, bound_workspaces


GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"


class GraphWriteClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


def apply_privileged_change_path(
    client: GraphWriteClient,
    config: dict[str, Any],
    provisioned_state: dict[str, Any],
) -> dict[str, Any]:
    if validate_privileged_change_config(config):
        raise RuntimeError("invalid privileged change config")
    technical_owner_upn = config["technical_owner_user"]["user_principal_name"]
    delegated_actor = _resolve_delegated_actor(client, technical_owner_upn)
    technical_owner = _resolve_technical_owner(client, technical_owner_upn)
    if technical_owner.get("id") != delegated_actor["id"]:
        raise RuntimeError(
            "privileged apply requires the configured delegated technical owner"
        )
    team_owner_checks = _verify_team_owners(
        client,
        provisioned_state,
        technical_owner["id"],
    )
    graph_sp, graph_roles = _get_graph_service_principal(client)
    _inspect_existing_application_role_boundaries(
        client,
        config["applications"],
        graph_sp,
        graph_roles,
    )
    governance_group = _ensure_governance_group(client, config["governance_group"])

    applications: dict[str, Any] = {}
    runtime_app: dict[str, Any] | None = None
    for app_def in config["applications"]:
        app = _ensure_application(client, app_def, graph_roles)
        service_principal = _ensure_service_principal(client, app)
        owner_status = _ensure_application_owner(client, app, technical_owner)
        assignments = _ensure_app_role_assignments(
            client,
            service_principal,
            graph_sp,
            graph_roles,
            _strings(app_def.get("bootstrap_application_permissions")),
        )
        applications[app_def["id"]] = {
            "displayName": app["displayName"],
            "applicationObjectId": app["id"],
            "clientId": app["appId"],
            "applicationStatus": app["_status"],
            "servicePrincipalId": service_principal["id"],
            "servicePrincipalStatus": service_principal["_status"],
            "technicalOwnerStatus": owner_status,
            "appRoleAssignments": assignments,
        }
        if app_def.get("runtime_allowed") is True:
            runtime_app = app

    if runtime_app is None:
        raise RuntimeError("privileged change config must define a runtime app")

    site_permissions = _ensure_site_permissions(client, provisioned_state, runtime_app)
    return {
        "status": "PASSED",
        "technicalOwner": _owner_view(technical_owner),
        "teamOwnerChecks": team_owner_checks,
        "governanceGroup": _group_view(governance_group),
        "applications": applications,
        "sitePermissions": site_permissions,
    }


def _resolve_delegated_actor(
    client: GraphWriteClient,
    expected_user_principal_name: str,
) -> dict[str, Any]:
    try:
        actor = client.get("/me?$select=id,displayName,userPrincipalName")
    except GraphHttpError as exc:
        raise RuntimeError(
            "privileged apply requires delegated technical-owner authentication"
        ) from exc
    if (
        not isinstance(actor, dict)
        or not isinstance(actor.get("id"), str)
        or not actor["id"].strip()
        or not isinstance(actor.get("userPrincipalName"), str)
        or actor["userPrincipalName"].strip().lower()
        != expected_user_principal_name.strip().lower()
    ):
        raise RuntimeError(
            "privileged apply requires the configured delegated technical owner"
        )
    return actor


def _resolve_technical_owner(client: GraphWriteClient, user_principal_name: str) -> dict[str, Any]:
    users = _complete_owner_collection(
        client,
        "/users?"
        + urllib.parse.urlencode(
            {
                "$filter": f"userPrincipalName eq '{user_principal_name}'",
                "$select": "id,displayName,userPrincipalName,assignedLicenses",
            }
        ),
    )
    user = _single(users, "configured technical owner")
    if (not isinstance(user.get("id"), str) or not user["id"].strip()
            or not isinstance(user.get("userPrincipalName"), str)
            or user["userPrincipalName"].casefold() != user_principal_name.casefold()):
        raise RuntimeError("technical-owner lookup does not match the configured user")
    licenses = user.get("assignedLicenses", [])
    if not isinstance(licenses, list) or any(not isinstance(item, dict) for item in licenses):
        raise RuntimeError("technical-owner license metadata must be a list of objects")
    return user


def _complete_owner_collection(client: GraphWriteClient, path: str) -> list[dict[str, Any]]:
    page = client.get(path)
    if (not isinstance(page, dict) or "@odata.nextLink" in page
            or not isinstance(page.get("value"), list)
            or any(not isinstance(item, dict) for item in page["value"])):
        # Partial or paginated evidence cannot establish the exact owner set.
        # Never follow a provider-selected continuation URL during this preflight.
        raise RuntimeError("team-owner preflight requires complete, unpaginated evidence")
    return page["value"]


def _verify_team_owners(
    client: GraphWriteClient,
    provisioned_state: dict[str, Any],
    technical_owner_id: str,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for workspace in bound_workspaces(provisioned_state):
        owners = _complete_owner_collection(
            client,
            f"/groups/{workspace['team_id']}/owners?"
            + urllib.parse.urlencode({"$select": "id,userPrincipalName"}),
        )
        if (len(owners) != 1
                or owners[0].get("@odata.type") != "#microsoft.graph.user"
                or owners[0].get("id") != technical_owner_id
                or not isinstance(owners[0].get("userPrincipalName"), str)
                or owners[0]["userPrincipalName"].casefold() != TECHNICAL_OWNER_UPN.casefold()):
            raise RuntimeError("group must have exactly the configured technical user as owner")
        members = _complete_owner_collection(
            client, f"/teams/{workspace['team_id']}/members?"
            + urllib.parse.urlencode({"$select": "id,userId,roles"}),
        )
        seen_users: set[str] = set()
        seen_memberships: set[str] = set()
        team_owner_ids: list[str] = []
        for member in members:
            user_id = member.get("userId")
            membership_id = member.get("id")
            roles = member.get("roles")
            if (member.get("@odata.type") != "#microsoft.graph.aadUserConversationMember"
                    or not isinstance(user_id, str) or not user_id.strip()
                    or not isinstance(membership_id, str) or not membership_id.strip()
                    or user_id in seen_users or membership_id in seen_memberships
                    or roles not in ([], ["guest"], ["owner"])):
                raise RuntimeError("team-owner preflight requires complete, unique member roles")
            seen_users.add(user_id)
            seen_memberships.add(membership_id)
            if roles == ["owner"]:
                team_owner_ids.append(user_id)
        if team_owner_ids != [technical_owner_id]:
            raise RuntimeError("Team must have exactly the configured technical user as owner")
        checks.append(
            {
                "workspaceId": workspace["id"],
                "teamDisplayName": workspace["team_display_name"],
                "ownerCount": len(owners),
                "teamOwnerCount": len(team_owner_ids),
                "technicalOwnerOnly": True,
                "standardUsersMembersOnly": True,
                "groupAndTeamOwnersVerified": True,
            }
        )
    return checks


def _ensure_governance_group(client: GraphWriteClient, group_def: dict[str, Any]) -> dict[str, Any]:
    groups = _paged(
        client,
        "/groups?"
        + urllib.parse.urlencode(
            {
                "$filter": (
                    f"displayName eq '{group_def['display_name']}' "
                    f"or mailNickname eq '{group_def['mail_nickname']}'"
                ),
                "$select": "id,displayName,mailNickname,securityEnabled,mailEnabled",
            }
        ),
    )
    if len(groups) > 1:
        raise RuntimeError("governance group lookup returned multiple results")
    if groups:
        return {**groups[0], "_status": "existing"}
    created = client.post(
        "/groups",
        {
            "displayName": group_def["display_name"],
            "mailEnabled": False,
            "mailNickname": group_def["mail_nickname"],
            "securityEnabled": True,
        },
    )
    return {**created, "_status": "created"}


def _get_graph_service_principal(client: GraphWriteClient) -> tuple[dict[str, Any], dict[str, str]]:
    service_principals = _paged(
        client,
        "/servicePrincipals?"
        + urllib.parse.urlencode(
            {
                "$filter": f"appId eq '{GRAPH_APP_ID}'",
                "$select": "id,appId,displayName,appRoles",
            }
        ),
    )
    graph_sp = _single(service_principals, "Microsoft Graph service principal")
    roles = {
        role["value"]: role["id"]
        for role in graph_sp.get("appRoles", [])
        if "Application" in role.get("allowedMemberTypes", []) and role.get("value")
    }
    return graph_sp, roles


def _inspect_existing_application_role_boundaries(
    client: GraphWriteClient,
    applications: list[dict[str, Any]],
    graph_sp: dict[str, Any],
    graph_roles: dict[str, str],
) -> None:
    """Inventory every existing app role boundary before the first write."""

    for app_def in applications:
        permissions = _strings(app_def.get("bootstrap_application_permissions"))
        desired_role_ids = {graph_roles[permission] for permission in permissions}
        app = _lookup_bound_application(
            client,
            app_def,
            select="id,appId,displayName",
        )
        if app is None:
            continue
        service_principals = _paged(
            client,
            "/servicePrincipals?"
            + urllib.parse.urlencode(
                {
                    "$filter": f"appId eq '{app['appId']}'",
                    "$select": "id,appId,displayName",
                }
            ),
        )
        if len(service_principals) > 1:
            raise RuntimeError(
                f"service principal lookup returned multiple results for "
                f"{app_def['display_name']}"
            )
        if not service_principals:
            continue
        existing = _paged(
            client,
            f"/servicePrincipals/{service_principals[0]['id']}"
            "/appRoleAssignments",
        )
        _validate_effective_graph_assignments(
            existing,
            graph_sp,
            desired_role_ids,
        )


def _validate_effective_graph_assignments(
    assignments: list[dict[str, Any]],
    graph_sp: dict[str, Any],
    desired_role_ids: set[str],
) -> set[str]:
    graph_assignments = [
        item for item in assignments if item.get("resourceId") == graph_sp["id"]
    ]
    effective_role_ids = [item.get("appRoleId") for item in graph_assignments]
    if any(role_id not in desired_role_ids for role_id in effective_role_ids):
        raise RuntimeError(
            "application has an unexpected Microsoft Graph application role"
        )
    if len(effective_role_ids) != len(set(effective_role_ids)):
        raise RuntimeError(
            "application has duplicate Microsoft Graph application role assignments"
        )
    return set(effective_role_ids)


def _lookup_bound_application(
    client: GraphWriteClient,
    app_def: dict[str, Any],
    *,
    select: str,
) -> dict[str, Any] | None:
    expected_client_id = app_def.get("expected_client_id")
    if isinstance(expected_client_id, str) and expected_client_id:
        filter_expression = f"appId eq '{expected_client_id}'"
    else:
        filter_expression = f"displayName eq '{app_def['display_name']}'"
    apps = _paged(
        client,
        "/applications?"
        + urllib.parse.urlencode(
            {
                "$filter": filter_expression,
                "$select": select,
            }
        ),
    )
    if len(apps) > 1:
        raise RuntimeError(
            f"application lookup returned multiple results for {app_def['id']}"
        )
    if not apps:
        if app_def.get("existing_application_required") is True:
            raise RuntimeError(
                f"bound existing application is missing for {app_def['id']}"
            )
        return None
    app = apps[0]
    if (
        not isinstance(app.get("id"), str)
        or not app["id"]
        or app.get("displayName") != app_def["display_name"]
        or (
            isinstance(expected_client_id, str)
            and expected_client_id
            and app.get("appId") != expected_client_id
        )
    ):
        raise RuntimeError(
            f"bound existing application mismatch for {app_def['id']}"
        )
    return app


def _ensure_application(
    client: GraphWriteClient,
    app_def: dict[str, Any],
    graph_roles: dict[str, str],
) -> dict[str, Any]:
    permissions = _strings(app_def.get("bootstrap_application_permissions"))
    for permission in permissions:
        if permission not in graph_roles:
            raise RuntimeError(f"Microsoft Graph application role is not available: {permission}")
    app = _lookup_bound_application(
        client,
        app_def,
        select="id,appId,displayName,requiredResourceAccess",
    )
    required_resource_access = [
        {
            "resourceAppId": GRAPH_APP_ID,
            "resourceAccess": [
                {"id": graph_roles[permission], "type": "Role"}
                for permission in permissions
            ],
        }
    ]
    if app is not None:
        client.patch(
            f"/applications/{app['id']}",
            {"requiredResourceAccess": required_resource_access},
        )
        return {**app, "_status": "existing"}
    created = client.post(
        "/applications",
        {
            "displayName": app_def["display_name"],
            "signInAudience": "AzureADMyOrg",
            "requiredResourceAccess": required_resource_access,
        },
    )
    return {**created, "_status": "created"}


def _ensure_service_principal(client: GraphWriteClient, app: dict[str, Any]) -> dict[str, Any]:
    service_principals = _paged(
        client,
        "/servicePrincipals?"
        + urllib.parse.urlencode(
            {
                "$filter": f"appId eq '{app['appId']}'",
                "$select": "id,appId,displayName",
            }
        ),
    )
    if len(service_principals) > 1:
        raise RuntimeError(f"service principal lookup returned multiple results for {app['displayName']}")
    if service_principals:
        return {**service_principals[0], "_status": "existing"}
    created = client.post("/servicePrincipals", {"appId": app["appId"]})
    return {**created, "_status": "created"}


def _ensure_application_owner(
    client: GraphWriteClient,
    app: dict[str, Any],
    owner: dict[str, Any],
) -> str:
    owners = _paged(client, f"/applications/{app['id']}/owners?$select=id,displayName")
    if any(item.get("id") == owner["id"] for item in owners):
        return "existing"
    try:
        client.post(
            f"/applications/{app['id']}/owners/$ref",
            {"@odata.id": f"{GRAPH_BASE}/directoryObjects/{owner['id']}"},
        )
    except GraphHttpError as exc:
        if exc.status != 400 or "added object references already exist" not in exc.body:
            raise
    return "created"


def _ensure_app_role_assignments(
    client: GraphWriteClient,
    service_principal: dict[str, Any],
    graph_sp: dict[str, Any],
    graph_roles: dict[str, str],
    permissions: list[str],
) -> list[dict[str, Any]]:
    existing = _paged(
        client,
        f"/servicePrincipals/{service_principal['id']}/appRoleAssignments",
    )
    desired_role_ids = {graph_roles[permission] for permission in permissions}
    existing_role_ids = _validate_effective_graph_assignments(
        existing,
        graph_sp,
        desired_role_ids,
    )
    results: list[dict[str, Any]] = []
    for permission in permissions:
        role_id = graph_roles[permission]
        if role_id in existing_role_ids:
            results.append({"permission": permission, "status": "existing", "appRoleId": role_id})
            continue
        client.post(
            f"/servicePrincipals/{service_principal['id']}/appRoleAssignments",
            {
                "principalId": service_principal["id"],
                "resourceId": graph_sp["id"],
                "appRoleId": role_id,
            },
        )
        results.append({"permission": permission, "status": "created", "appRoleId": role_id})
    return results


def _ensure_site_permissions(
    client: GraphWriteClient,
    provisioned_state: dict[str, Any],
    runtime_app: dict[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for workspace in _workspaces(provisioned_state):
        site_id = workspace["site_id"]
        site_path = urllib.parse.quote(site_id, safe=",")
        existing = _paged(client, f"/sites/{site_path}/permissions")
        if any(_site_permission_matches(permission, runtime_app["appId"]) for permission in existing):
            results.append({"workspaceId": workspace["id"], "siteId": site_id, "status": "existing", "role": "write"})
            continue
        permission = client.post(
            f"/sites/{site_path}/permissions",
            {
                "roles": ["write"],
                "grantedToIdentities": [
                    {
                        "application": {
                            "id": runtime_app["appId"],
                            "displayName": runtime_app["displayName"],
                        }
                    }
                ],
            },
        )
        results.append(
            {
                "workspaceId": workspace["id"],
                "siteId": site_id,
                "status": "created",
                "role": "write",
                "permissionId": permission.get("id"),
            }
        )
    return results


def _site_permission_matches(permission: dict[str, Any], app_id: str) -> bool:
    identities = list(permission.get("grantedToIdentities", []) or [])
    identities.extend(permission.get("grantedToIdentitiesV2", []) or [])
    return any((identity.get("application") or {}).get("id") == app_id for identity in identities)


def _paged(client: GraphWriteClient, path: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    while path:
        payload = client.get(path)
        values.extend(payload.get("value", []))
        next_link = payload.get("@odata.nextLink")
        path = next_link.removeprefix(GRAPH_BASE) if isinstance(next_link, str) else ""
    return values


def _single(items: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if len(items) != 1:
        raise RuntimeError(f"{label} expected exactly one result, got {len(items)}")
    return items[0]


def _owner_view(owner: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": owner.get("id"),
        "displayName": owner.get("displayName"),
        "userPrincipalName": owner.get("userPrincipalName"),
        "assignedLicenseCount": len(owner.get("assignedLicenses", [])),
    }


def _group_view(group: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": group.get("_status"),
        "id": group.get("id"),
        "displayName": group.get("displayName"),
        "mailNickname": group.get("mailNickname"),
        "securityEnabled": group.get("securityEnabled"),
        "mailEnabled": group.get("mailEnabled"),
    }


def _workspaces(provisioned_state: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        workspace
        for workspace in provisioned_state.get("workspaces", [])
        if isinstance(workspace, dict)
    ]


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
