from __future__ import annotations

import hashlib
import time
import urllib.parse
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from nac_bff.azure_activation import (
    API_APP_DISPLAY_NAME,
    API_APP_URI,
    CLI_TEST_CLIENT_ID,
    DELEGATED_SCOPE,
    PROVISIONER_CLIENT_ID,
    PROVISIONER_GRAPH_APPLICATION_ROLES,
    REQUESTED_ACCESS_TOKEN_VERSION,
    SITE_ID,
)


SCHEMA_VERSION = "nac.m365-bff-graph-activation/v1"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"
GRAPH_ROLE = "Sites.Selected"
SITE_ROLE = "read"
TARGET_SITE_ID = SITE_ID
MATTER_READ_SCOPE_ID = str(
    uuid.uuid5(uuid.NAMESPACE_URL, f"{API_APP_URI}#{DELEGATED_SCOPE}")
)
PERFORMANCE_LEASE_APP_ROLE = "Performance.Lease"
PERFORMANCE_LEASE_APP_ROLE_ID = str(
    uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"{API_APP_URI}#{PERFORMANCE_LEASE_APP_ROLE}",
    )
)
DEFAULT_READBACK_MAX_ATTEMPTS = 6
DEFAULT_READBACK_BACKOFF_SECONDS = 2.0


@dataclass(frozen=True, slots=True)
class ReadbackPolicy:
    """Bounded GET-only polling after one provider write."""

    max_attempts: int = DEFAULT_READBACK_MAX_ATTEMPTS
    backoff_seconds: float = DEFAULT_READBACK_BACKOFF_SECONDS
    sleeper: Callable[[float], None] = time.sleep

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_attempts, bool)
            or not isinstance(self.max_attempts, int)
            or self.max_attempts < 1
        ):
            raise ValueError("max_attempts must be a positive integer")
        if (
            isinstance(self.backoff_seconds, bool)
            or not isinstance(self.backoff_seconds, (int, float))
            or self.backoff_seconds < 0
        ):
            raise ValueError("backoff_seconds must be non-negative")
        if not callable(self.sleeper):
            raise TypeError("sleeper must be callable")


DEFAULT_READBACK_POLICY = ReadbackPolicy()
_ReadbackState = TypeVar("_ReadbackState")


class GraphActivationClient(Protocol):
    def get(self, path: str) -> dict[str, Any]:
        ...

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...


_ERROR_MESSAGES = {
    "INVALID_UAMI_APP_ID": "The managed identity application ID is invalid.",
    "INVALID_TARGET_SITE": "The requested site is outside the activation allowlist.",
    "GRAPH_REQUEST_FAILED": "A Microsoft Graph request failed.",
    "PROVISIONER_SERVICE_PRINCIPAL_MISSING": (
        "The provisioner service principal is missing."
    ),
    "PROVISIONER_SERVICE_PRINCIPAL_DUPLICATE": (
        "The provisioner service principal lookup is not unique."
    ),
    "PROVISIONER_SERVICE_PRINCIPAL_MISMATCH": (
        "The provisioner service principal does not match the required contract."
    ),
    "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH": (
        "The provisioner Microsoft Graph application roles do not match the allowlist."
    ),
    "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE": (
        "The provisioner cannot inspect target-site permissions."
    ),
    "GRAPH_RESPONSE_INVALID": "Microsoft Graph returned an invalid response shape.",
    "GRAPH_PAGING_INVALID": "Microsoft Graph returned a non-v1.0 paging link.",
    "API_APPLICATION_DUPLICATE": "The API application lookup is not unique.",
    "API_APPLICATION_READBACK_MISSING": "The API application readback is missing.",
    "API_APPLICATION_READBACK_TIMEOUT": (
        "The API application was not visible before the bounded readback deadline."
    ),
    "API_APPLICATION_MISMATCH": "The API application does not match the required contract.",
    "API_SERVICE_PRINCIPAL_DUPLICATE": "The API service principal lookup is not unique.",
    "API_SERVICE_PRINCIPAL_READBACK_MISSING": "The API service principal readback is missing.",
    "API_SERVICE_PRINCIPAL_READBACK_TIMEOUT": (
        "The API service principal was not visible before the bounded readback deadline."
    ),
    "API_SERVICE_PRINCIPAL_MISMATCH": "The API service principal does not match the required contract.",
    "API_ROLE_ASSIGNMENT_DUPLICATE": (
        "The BFF API has duplicate performance lease role assignments."
    ),
    "API_ROLE_ASSIGNMENT_BROADER": (
        "The BFF API has a non-allowlisted application role assignment."
    ),
    "API_ROLE_ASSIGNMENT_MISMATCH": (
        "The BFF API role assignment does not match the provisioner."
    ),
    "API_ROLE_ASSIGNMENT_READBACK_TIMEOUT": (
        "The performance lease role assignment was not visible before the bounded "
        "readback deadline."
    ),
    "UAMI_SERVICE_PRINCIPAL_MISSING": "The managed identity service principal is missing.",
    "UAMI_SERVICE_PRINCIPAL_READBACK_TIMEOUT": (
        "The managed identity service principal was not visible before the bounded "
        "readback deadline."
    ),
    "UAMI_SERVICE_PRINCIPAL_DUPLICATE": "The managed identity service principal lookup is not unique.",
    "UAMI_SERVICE_PRINCIPAL_MISMATCH": "The managed identity service principal does not match the required contract.",
    "GRAPH_SERVICE_PRINCIPAL_MISSING": "The Microsoft Graph service principal is missing.",
    "GRAPH_SERVICE_PRINCIPAL_DUPLICATE": "The Microsoft Graph service principal lookup is not unique.",
    "GRAPH_SERVICE_PRINCIPAL_MISMATCH": "The Microsoft Graph service principal does not match the required contract.",
    "SITES_SELECTED_ROLE_MISSING": "The Sites.Selected application role is missing.",
    "SITES_SELECTED_ROLE_DUPLICATE": "The Sites.Selected application role is not unique.",
    "SITES_SELECTED_ROLE_MISMATCH": "The Sites.Selected application role does not match the required contract.",
    "GRAPH_ROLE_ASSIGNMENT_DUPLICATE": "The managed identity has duplicate Microsoft Graph role assignments.",
    "GRAPH_ROLE_ASSIGNMENT_BROADER": "The managed identity has a non-allowlisted Microsoft Graph application role.",
    "GRAPH_ROLE_ASSIGNMENT_MISMATCH": "The Microsoft Graph role assignment does not match the managed identity.",
    "GRAPH_ROLE_ASSIGNMENT_READBACK_MISSING": "The Sites.Selected role assignment readback is missing.",
    "GRAPH_ROLE_ASSIGNMENT_READBACK_TIMEOUT": (
        "The Sites.Selected role assignment was not visible before the bounded "
        "readback deadline."
    ),
    "SITE_PERMISSION_DUPLICATE": "The managed identity has duplicate permissions on the target site.",
    "SITE_PERMISSION_BROADER": "The managed identity has a non-read permission on the target site.",
    "SITE_PERMISSION_MISMATCH": "The target site permission is not exclusive to the managed identity.",
    "SITE_PERMISSION_READBACK_MISSING": "The target site read permission readback is missing.",
    "SITE_PERMISSION_READBACK_TIMEOUT": (
        "The target site read permission was not visible before the bounded readback "
        "deadline."
    ),
}


class GraphActivationError(RuntimeError):
    """A stable, value-free activation failure suitable for redacted evidence."""

    def __init__(self, code: str):
        message = _ERROR_MESSAGES[code]
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message

    def redacted_result(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "BLOCKED",
            "error": {"code": self.code, "message": self.message},
        }


@dataclass(frozen=True, slots=True)
class _ApiApplicationState:
    object_id: str
    app_id: str
    application_status: str
    service_principal_id: str
    service_principal_status: str


@dataclass(frozen=True, slots=True)
class ApiApplicationBinding:
    """Internal deployment binding; callers must never place app_id in evidence."""

    app_id: str
    service_principal_id: str
    redacted_result: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _UamiState:
    app_id: str
    principal_id: str
    display_name: str


def activate_nac_bff_graph(
    client: GraphActivationClient,
    uami_app_id: str,
    *,
    site_id: str = TARGET_SITE_ID,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> dict[str, Any]:
    """Ensure the exact BFF app, UAMI Graph role, and site read grant."""

    _require_target_site(site_id)
    api_state = _ensure_api_application(client, readback_policy)
    uami = _resolve_uami(client, uami_app_id, readback_policy=readback_policy)
    graph_access = _ensure_sites_selected(client, uami, readback_policy)
    site_access = _ensure_site_read(client, uami, site_id, readback_policy)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASSED",
        "graph_api": "Microsoft Graph v1.0",
        "api_application": _api_application_result(api_state),
        "uami_graph_access": graph_access,
        "site_access": site_access,
        "boundaries": {
            "identifier_uri_lookup": "exact",
            "application_role_allowlist": [GRAPH_ROLE],
            "api_application_role_allowlist": [PERFORMANCE_LEASE_APP_ROLE],
            "site_role_allowlist": [SITE_ROLE],
            "raw_responses_emitted": False,
            "raw_ids_emitted": False,
            "privileged_apply_used": False,
        },
    }


def ensure_entra_api_application(
    client: GraphActivationClient,
    *,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> dict[str, Any]:
    return _api_application_result(_ensure_api_application(client, readback_policy))


def inspect_entra_api_application(client: GraphActivationClient) -> dict[str, Any]:
    """Inspect the exact API application and service principal without writes."""

    applications = _lookup_api_applications(client)
    if len(applications) > 1:
        raise GraphActivationError("API_APPLICATION_DUPLICATE")
    if not applications:
        return _api_application_contract_result(
            application_status="absent",
            object_id=None,
            app_id=None,
            service_principal_status="absent",
            service_principal_id=None,
        )

    object_id, app_id = _validate_api_application(applications[0])
    service_principals = _lookup_service_principals(client, app_id)
    if len(service_principals) > 1:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")
    if not service_principals:
        return _api_application_contract_result(
            application_status="present",
            object_id=object_id,
            app_id=app_id,
            service_principal_status="absent",
            service_principal_id=None,
        )

    service_principal_id = _validate_api_service_principal(
        service_principals[0], app_id
    )
    return _api_application_contract_result(
        application_status="present",
        object_id=object_id,
        app_id=app_id,
        service_principal_status="present",
        service_principal_id=service_principal_id,
    )


def ensure_provisioner_performance_lease(
    client: GraphActivationClient,
    *,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> dict[str, Any]:
    """Ensure the sole BFF app-role assignment belongs to the provisioner."""

    provisioner_id = _resolve_provisioner(client)
    _preflight_existing_performance_lease_boundary(client, provisioner_id)
    api_state = _ensure_api_application(client, readback_policy)
    return _ensure_performance_lease_assignment(
        client,
        api_state.service_principal_id,
        provisioner_id,
        readback_policy,
    )


def inspect_provisioner_performance_lease(
    client: GraphActivationClient,
) -> dict[str, Any]:
    """Inspect the exact provisioner performance lease assignment read-only."""

    applications = _lookup_api_applications(client)
    if len(applications) > 1:
        raise GraphActivationError("API_APPLICATION_DUPLICATE")
    if not applications:
        return _performance_lease_assignment_result("absent", 0)
    _object_id, app_id = _validate_api_application(applications[0])
    service_principals = _lookup_service_principals(client, app_id)
    if len(service_principals) > 1:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")
    if not service_principals:
        return _performance_lease_assignment_result("absent", 0)
    service_principal_id = _validate_api_service_principal(
        service_principals[0], app_id
    )
    provisioner_id = _resolve_provisioner(client)
    assignments = _paged(
        client, _performance_lease_assignments_path(service_principal_id)
    )
    exact_count = _inspect_performance_lease_assignments(
        assignments, service_principal_id, provisioner_id
    )
    return _performance_lease_assignment_result(
        "present" if exact_count else "absent", exact_count
    )


def ensure_entra_api_application_binding(
    client: GraphActivationClient,
    *,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> ApiApplicationBinding:
    state = _ensure_api_application(client, readback_policy)
    return ApiApplicationBinding(
        app_id=state.app_id,
        service_principal_id=state.service_principal_id,
        redacted_result=_api_application_result(state),
    )


def ensure_uami_sites_selected(
    client: GraphActivationClient,
    uami_app_id: str,
    *,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> dict[str, Any]:
    return _ensure_sites_selected(
        client,
        _resolve_uami(client, uami_app_id, readback_policy=readback_policy),
        readback_policy,
    )


def inspect_uami_sites_selected(
    client: GraphActivationClient,
    uami_app_id: str,
) -> dict[str, Any]:
    """Inspect the exact UAMI Sites.Selected assignment without writes."""

    uami = _resolve_uami(client, uami_app_id)
    graph_principal, sites_selected_role_id = _resolve_graph_role(client)
    assignments = _paged(client, _graph_assignments_path(uami))
    exact_count = _inspect_graph_assignments(
        assignments, uami, graph_principal, sites_selected_role_id
    )
    return _uami_graph_access_result(
        "present" if exact_count else "absent", uami, exact_count
    )


def ensure_site_read_permission(
    client: GraphActivationClient,
    uami_app_id: str,
    *,
    site_id: str = TARGET_SITE_ID,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> dict[str, Any]:
    _require_target_site(site_id)
    return _ensure_site_read(
        client,
        _resolve_uami(client, uami_app_id, readback_policy=readback_policy),
        site_id,
        readback_policy,
    )


def inspect_site_read_permission(
    client: GraphActivationClient,
    uami_app_id: str,
    *,
    site_id: str = TARGET_SITE_ID,
) -> dict[str, Any]:
    """Inspect the exact target-site read permission without writes."""

    _require_target_site(site_id)
    uami = _resolve_uami(client, uami_app_id)
    permissions = _paged(client, _site_permissions_path(site_id))
    exact_count = _inspect_site_permissions(permissions, uami.app_id)
    return _site_access_result(
        "present" if exact_count else "absent", uami, site_id, exact_count
    )


def inspect_provisioner_application_roles(
    client: GraphActivationClient,
) -> dict[str, Any]:
    """Prove the effective provisioner Microsoft Graph roles read-only."""

    provisioner_id = _resolve_provisioner(client)

    graph_principals = _lookup_service_principals(client, GRAPH_APP_ID)
    if len(graph_principals) != 1:
        raise GraphActivationError("PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH")
    graph_principal = graph_principals[0]
    try:
        graph_principal_id = _canonical_uuid(graph_principal.get("id"))
        graph_valid = (
            _canonical_uuid(graph_principal.get("appId")) == GRAPH_APP_ID
            and graph_principal.get("displayName") == "Microsoft Graph"
            and graph_principal.get("servicePrincipalType") == "Application"
        )
    except (TypeError, ValueError):
        graph_valid = False
        graph_principal_id = ""
    app_roles = graph_principal.get("appRoles")
    if not graph_valid or not isinstance(app_roles, list):
        raise GraphActivationError("PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH")

    role_ids: dict[str, str] = {}
    for role in app_roles:
        if (
            not isinstance(role, dict)
            or role.get("value") not in PROVISIONER_GRAPH_APPLICATION_ROLES
        ):
            continue
        try:
            role_id = _canonical_uuid(role.get("id"))
        except (TypeError, ValueError):
            raise GraphActivationError(
                "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH"
            ) from None
        if (
            role.get("isEnabled") is not True
            or role.get("allowedMemberTypes") != ["Application"]
            or role["value"] in role_ids
        ):
            raise GraphActivationError(
                "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH"
            )
        role_ids[role["value"]] = role_id
    if set(role_ids) != set(PROVISIONER_GRAPH_APPLICATION_ROLES):
        raise GraphActivationError("PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH")

    assignments = _paged(
        client,
        f"/servicePrincipals/{provisioner_id}/appRoleAssignments?"
        + urllib.parse.urlencode(
            {"$select": "id,appRoleId,principalId,resourceId"}
        ),
    )
    role_names_by_id = {role_id: name for name, role_id in role_ids.items()}
    effective_roles: list[str] = []
    for assignment in assignments:
        try:
            resource_id = _canonical_uuid(assignment.get("resourceId"))
        except (TypeError, ValueError):
            raise GraphActivationError(
                "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH"
            ) from None
        if resource_id != graph_principal_id:
            continue
        try:
            principal_id = _canonical_uuid(assignment.get("principalId"))
            role_id = _canonical_uuid(assignment.get("appRoleId"))
        except (TypeError, ValueError):
            raise GraphActivationError(
                "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH"
            ) from None
        if (
            principal_id != provisioner_id
            or role_id not in role_names_by_id
        ):
            raise GraphActivationError(
                "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH"
            )
        effective_roles.append(role_names_by_id[role_id])
    if (
        len(effective_roles) != len(set(effective_roles))
        or set(effective_roles) != set(PROVISIONER_GRAPH_APPLICATION_ROLES)
    ):
        raise GraphActivationError("PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH")
    return {
        "status": "present",
        "application_roles": sorted(effective_roles),
        "assignment_count": len(effective_roles),
        "raw_ids_emitted": False,
    }


def _resolve_provisioner(client: GraphActivationClient) -> str:
    provisioners = _lookup_service_principals(client, PROVISIONER_CLIENT_ID)
    if not provisioners:
        raise GraphActivationError("PROVISIONER_SERVICE_PRINCIPAL_MISSING")
    if len(provisioners) > 1:
        raise GraphActivationError("PROVISIONER_SERVICE_PRINCIPAL_DUPLICATE")
    provisioner = provisioners[0]
    try:
        provisioner_id = _canonical_uuid(provisioner.get("id"))
        provisioner_valid = (
            _canonical_uuid(provisioner.get("appId")) == PROVISIONER_CLIENT_ID
            and provisioner.get("displayName") == "NaC M365 Provisioning"
            and provisioner.get("servicePrincipalType") == "Application"
        )
    except (TypeError, ValueError):
        provisioner_valid = False
        provisioner_id = ""
    if not provisioner_valid:
        raise GraphActivationError("PROVISIONER_SERVICE_PRINCIPAL_MISMATCH")
    return provisioner_id


def inspect_site_permission_administration(
    client: GraphActivationClient,
    *,
    site_id: str = TARGET_SITE_ID,
) -> dict[str, Any]:
    """Prove the provisioner's target-site permission-admin capability read-only."""

    _require_target_site(site_id)
    try:
        permissions = _paged(client, _site_permissions_path(site_id))
    except GraphActivationError as exc:
        raise GraphActivationError(
            "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE"
        ) from exc
    return {
        "status": "available",
        "site_ref": _hashed_ref(site_id),
        "permission_count": len(permissions),
    }


def ensure_nac_bff_graph_activation(
    client: GraphActivationClient,
    uami_app_id: str,
    *,
    site_id: str = TARGET_SITE_ID,
    readback_policy: ReadbackPolicy = DEFAULT_READBACK_POLICY,
) -> dict[str, Any]:
    return activate_nac_bff_graph(
        client,
        uami_app_id,
        site_id=site_id,
        readback_policy=readback_policy,
    )


def _ensure_api_application(
    client: GraphActivationClient, readback_policy: ReadbackPolicy
) -> _ApiApplicationState:
    applications = _lookup_api_applications(client)
    if len(applications) > 1:
        raise GraphActivationError("API_APPLICATION_DUPLICATE")

    application_status = "reused"
    if not applications:
        _post(client, "/applications", _application_payload())
        application_status = "created"
        applications = _poll_readback(
            lambda: _lookup_api_applications(client),
            bool,
            policy=readback_policy,
            timeout_code="API_APPLICATION_READBACK_TIMEOUT",
        )
        if len(applications) > 1:
            raise GraphActivationError("API_APPLICATION_DUPLICATE")
    else:
        try:
            _validate_api_application(applications[0])
        except GraphActivationError as exc:
            if exc.code != "API_APPLICATION_MISMATCH":
                raise
            object_id, _app_id = _validate_api_application(
                applications[0], expected_app_roles=[]
            )
            legacy_service_principals = _lookup_service_principals(
                client, _app_id
            )
            if len(legacy_service_principals) > 1:
                raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")
            if legacy_service_principals:
                _validate_api_service_principal_transition_state(
                    legacy_service_principals[0], _app_id
                )
            _patch(
                client,
                f"/applications/{object_id}",
                {"appRoles": [_performance_lease_app_role()]},
            )
            application_status = "migrated"
            applications = _poll_readback(
                lambda: _lookup_api_applications(client),
                _api_application_role_visible,
                policy=readback_policy,
                timeout_code="API_APPLICATION_READBACK_TIMEOUT",
            )
            if len(applications) > 1:
                raise GraphActivationError("API_APPLICATION_DUPLICATE")

    application = applications[0]
    object_id, app_id = _validate_api_application(application)
    service_principals = _lookup_service_principals(client, app_id)
    if len(service_principals) > 1:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")

    service_principal_status = "reused"
    if not service_principals:
        _post(client, "/servicePrincipals", {"appId": app_id})
        service_principal_status = "created"
    service_principals = _poll_readback(
        lambda: _lookup_service_principals(client, app_id),
        lambda values: _api_service_principal_role_visible(values, app_id),
        policy=readback_policy,
        timeout_code="API_SERVICE_PRINCIPAL_READBACK_TIMEOUT",
    )
    if len(service_principals) > 1:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")

    service_principal_id = _validate_api_service_principal(
        service_principals[0], app_id
    )
    return _ApiApplicationState(
        object_id=object_id,
        app_id=app_id,
        application_status=application_status,
        service_principal_id=service_principal_id,
        service_principal_status=service_principal_status,
    )


def _lookup_api_applications(client: GraphActivationClient) -> list[dict[str, Any]]:
    filter_value = f"identifierUris/any(uri:uri eq '{_odata_literal(API_APP_URI)}')"
    return _paged(
        client,
        _query_path(
            "/applications",
            filter_value,
            "id,appId,displayName,identifierUris,signInAudience,api,appRoles,requiredResourceAccess",
        ),
    )


def _application_payload() -> dict[str, Any]:
    return {
        "displayName": API_APP_DISPLAY_NAME,
        "identifierUris": [API_APP_URI],
        "signInAudience": "AzureADMyOrg",
        "api": {
            "requestedAccessTokenVersion": REQUESTED_ACCESS_TOKEN_VERSION,
            "oauth2PermissionScopes": [
                {
                    "adminConsentDescription": "Read assigned NaC matters.",
                    "adminConsentDisplayName": "Read assigned NaC matters",
                    "id": MATTER_READ_SCOPE_ID,
                    "isEnabled": True,
                    "type": "User",
                    "userConsentDescription": "Read NaC matters assigned to the signed-in user.",
                    "userConsentDisplayName": "Read assigned NaC matters",
                    "value": DELEGATED_SCOPE,
                }
            ],
            "preAuthorizedApplications": [
                {
                    "appId": CLI_TEST_CLIENT_ID,
                    "delegatedPermissionIds": [MATTER_READ_SCOPE_ID],
                }
            ],
        },
        "appRoles": [_performance_lease_app_role()],
        "requiredResourceAccess": [],
    }


def _performance_lease_app_role() -> dict[str, Any]:
    return {
        "allowedMemberTypes": ["Application"],
        "description": "Acquire the bounded NaC performance lease.",
        "displayName": "Acquire NaC performance lease",
        "id": PERFORMANCE_LEASE_APP_ROLE_ID,
        "isEnabled": True,
        "value": PERFORMANCE_LEASE_APP_ROLE,
    }


def _validate_api_application(
    application: dict[str, Any],
    *,
    expected_app_roles: list[dict[str, Any]] | None = None,
) -> tuple[str, str]:
    if expected_app_roles is None:
        expected_app_roles = [_performance_lease_app_role()]
    try:
        object_id = _canonical_uuid(application.get("id"))
        app_id = _canonical_uuid(application.get("appId"))
        api = application.get("api")
        scopes = api.get("oauth2PermissionScopes") if isinstance(api, dict) else None
        scope = scopes[0] if isinstance(scopes, list) and len(scopes) == 1 else None
        valid = (
            application.get("displayName") == API_APP_DISPLAY_NAME
            and application.get("identifierUris") == [API_APP_URI]
            and application.get("signInAudience") == "AzureADMyOrg"
            and application.get("appRoles") == expected_app_roles
            and application.get("requiredResourceAccess") == []
            and isinstance(api, dict)
            and api.get("requestedAccessTokenVersion")
            == REQUESTED_ACCESS_TOKEN_VERSION
            and isinstance(scope, dict)
            and _canonical_uuid(scope.get("id")) == MATTER_READ_SCOPE_ID
            and scope.get("value") == DELEGATED_SCOPE
            and scope.get("type") == "User"
            and scope.get("isEnabled") is True
            and api.get("preAuthorizedApplications")
            == [
                {
                    "appId": CLI_TEST_CLIENT_ID,
                    "delegatedPermissionIds": [MATTER_READ_SCOPE_ID],
                }
            ]
        )
    except (TypeError, ValueError):
        valid = False
        object_id = ""
        app_id = ""
    if not valid:
        raise GraphActivationError("API_APPLICATION_MISMATCH")
    return object_id, app_id


def _api_application_role_visible(
    applications: list[dict[str, Any]],
) -> bool:
    if not applications:
        return False
    if len(applications) > 1:
        return True
    try:
        _validate_api_application(applications[0])
        return True
    except GraphActivationError:
        _validate_api_application(applications[0], expected_app_roles=[])
        return False


def _lookup_service_principals(
    client: GraphActivationClient, app_id: str
) -> list[dict[str, Any]]:
    return _paged(
        client,
        _query_path(
            "/servicePrincipals",
            f"appId eq '{_odata_literal(app_id)}'",
            "id,appId,displayName,servicePrincipalType,appRoles",
        ),
    )


def _validate_api_service_principal(
    service_principal: dict[str, Any],
    app_id: str,
    *,
    expected_app_roles: list[dict[str, Any]] | None = None,
) -> str:
    if expected_app_roles is None:
        expected_app_roles = [_performance_lease_app_role()]
    try:
        principal_id = _canonical_uuid(service_principal.get("id"))
        valid = (
            _canonical_uuid(service_principal.get("appId")) == app_id
            and service_principal.get("displayName") == API_APP_DISPLAY_NAME
            and service_principal.get("servicePrincipalType") == "Application"
            and service_principal.get("appRoles") == expected_app_roles
        )
    except (TypeError, ValueError):
        valid = False
        principal_id = ""
    if not valid:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_MISMATCH")
    return principal_id


def _api_service_principal_role_visible(
    service_principals: list[dict[str, Any]], app_id: str
) -> bool:
    if not service_principals:
        return False
    if len(service_principals) > 1:
        return True
    try:
        _validate_api_service_principal(service_principals[0], app_id)
        return True
    except GraphActivationError:
        _validate_api_service_principal(
            service_principals[0], app_id, expected_app_roles=[]
        )
        return False


def _validate_api_service_principal_transition_state(
    service_principal: dict[str, Any], app_id: str
) -> str:
    try:
        return _validate_api_service_principal(service_principal, app_id)
    except GraphActivationError:
        return _validate_api_service_principal(
            service_principal, app_id, expected_app_roles=[]
        )


def _preflight_existing_performance_lease_boundary(
    client: GraphActivationClient, provisioner_id: str
) -> None:
    applications = _lookup_api_applications(client)
    if len(applications) > 1:
        raise GraphActivationError("API_APPLICATION_DUPLICATE")
    if not applications:
        return
    try:
        _object_id, app_id = _validate_api_application(applications[0])
    except GraphActivationError:
        _object_id, app_id = _validate_api_application(
            applications[0], expected_app_roles=[]
        )
    service_principals = _lookup_service_principals(client, app_id)
    if len(service_principals) > 1:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")
    if not service_principals:
        return
    api_service_principal_id = (
        _validate_api_service_principal_transition_state(
            service_principals[0], app_id
        )
    )
    assignments = _paged(
        client,
        _performance_lease_assignments_path(api_service_principal_id),
    )
    _inspect_performance_lease_assignments(
        assignments, api_service_principal_id, provisioner_id
    )


def _ensure_performance_lease_assignment(
    client: GraphActivationClient,
    api_service_principal_id: str,
    provisioner_id: str,
    readback_policy: ReadbackPolicy,
) -> dict[str, Any]:
    assignments_path = _performance_lease_assignments_path(
        api_service_principal_id
    )
    assignments = _paged(client, assignments_path)
    exact_count = _inspect_performance_lease_assignments(
        assignments, api_service_principal_id, provisioner_id
    )
    status = "reused"
    if exact_count == 0:
        _post(
            client,
            f"/servicePrincipals/{provisioner_id}/appRoleAssignments",
            {
                "principalId": provisioner_id,
                "resourceId": api_service_principal_id,
                "appRoleId": PERFORMANCE_LEASE_APP_ROLE_ID,
            },
        )
        status = "created"
        assignments = _poll_readback(
            lambda: _paged(client, assignments_path),
            lambda values: bool(
                _inspect_performance_lease_assignments(
                    values, api_service_principal_id, provisioner_id
                )
            ),
            policy=readback_policy,
            timeout_code="API_ROLE_ASSIGNMENT_READBACK_TIMEOUT",
        )
        exact_count = _inspect_performance_lease_assignments(
            assignments, api_service_principal_id, provisioner_id
        )
    return _performance_lease_assignment_result(status, exact_count)


def _performance_lease_assignments_path(
    api_service_principal_id: str,
) -> str:
    return (
        f"/servicePrincipals/{api_service_principal_id}/appRoleAssignedTo?"
        + urllib.parse.urlencode(
            {"$select": "id,appRoleId,principalId,resourceId"}
        )
    )


def _inspect_performance_lease_assignments(
    assignments: list[dict[str, Any]],
    api_service_principal_id: str,
    provisioner_id: str,
) -> int:
    exact_count = 0
    for assignment in assignments:
        try:
            resource_id = _canonical_uuid(assignment.get("resourceId"))
            principal_id = _canonical_uuid(assignment.get("principalId"))
            role_id = _canonical_uuid(assignment.get("appRoleId"))
        except (TypeError, ValueError):
            raise GraphActivationError("API_ROLE_ASSIGNMENT_MISMATCH") from None
        if (
            resource_id != api_service_principal_id
            or principal_id != provisioner_id
        ):
            raise GraphActivationError("API_ROLE_ASSIGNMENT_MISMATCH")
        if role_id != PERFORMANCE_LEASE_APP_ROLE_ID:
            raise GraphActivationError("API_ROLE_ASSIGNMENT_BROADER")
        exact_count += 1
    if exact_count > 1:
        raise GraphActivationError("API_ROLE_ASSIGNMENT_DUPLICATE")
    return exact_count


def _performance_lease_assignment_result(
    status: str, assignment_count: int
) -> dict[str, Any]:
    return {
        "status": status,
        "resource": API_APP_DISPLAY_NAME,
        "principal": "NaC M365 Provisioning",
        "application_role": PERFORMANCE_LEASE_APP_ROLE,
        "role_ref": _hashed_ref(PERFORMANCE_LEASE_APP_ROLE_ID),
        "assignment_count": assignment_count,
        "raw_ids_emitted": False,
    }


def _resolve_uami(
    client: GraphActivationClient,
    uami_app_id: str,
    *,
    readback_policy: ReadbackPolicy | None = None,
) -> _UamiState:
    try:
        canonical_app_id = _canonical_uuid(uami_app_id)
    except (TypeError, ValueError) as exc:
        raise GraphActivationError("INVALID_UAMI_APP_ID") from exc

    if readback_policy is None:
        service_principals = _lookup_service_principals(client, canonical_app_id)
    else:
        service_principals = _poll_readback(
            lambda: _lookup_service_principals(client, canonical_app_id),
            bool,
            policy=readback_policy,
            timeout_code="UAMI_SERVICE_PRINCIPAL_READBACK_TIMEOUT",
        )
    if not service_principals:
        raise GraphActivationError("UAMI_SERVICE_PRINCIPAL_MISSING")
    if len(service_principals) > 1:
        raise GraphActivationError("UAMI_SERVICE_PRINCIPAL_DUPLICATE")
    service_principal = service_principals[0]
    try:
        principal_id = _canonical_uuid(service_principal.get("id"))
        display_name = service_principal.get("displayName")
        valid = (
            _canonical_uuid(service_principal.get("appId")) == canonical_app_id
            and service_principal.get("servicePrincipalType") == "ManagedIdentity"
            and isinstance(display_name, str)
            and bool(display_name.strip())
        )
    except (TypeError, ValueError):
        valid = False
        principal_id = ""
        display_name = ""
    if not valid:
        raise GraphActivationError("UAMI_SERVICE_PRINCIPAL_MISMATCH")
    return _UamiState(canonical_app_id, principal_id, display_name)


def _ensure_sites_selected(
    client: GraphActivationClient,
    uami: _UamiState,
    readback_policy: ReadbackPolicy,
) -> dict[str, Any]:
    graph_principal, sites_selected_role_id = _resolve_graph_role(client)
    assignments_path = _graph_assignments_path(uami)
    assignments = _paged(client, assignments_path)
    exact_count = _inspect_graph_assignments(
        assignments, uami, graph_principal, sites_selected_role_id
    )
    status = "reused"
    if exact_count == 0:
        _post(
            client,
            f"/servicePrincipals/{uami.principal_id}/appRoleAssignments",
            {
                "principalId": uami.principal_id,
                "resourceId": graph_principal,
                "appRoleId": sites_selected_role_id,
            },
        )
        status = "created"
        assignments = _poll_readback(
            lambda: _paged(client, assignments_path),
            lambda values: bool(
                _inspect_graph_assignments(
                    values, uami, graph_principal, sites_selected_role_id
                )
            ),
            policy=readback_policy,
            timeout_code="GRAPH_ROLE_ASSIGNMENT_READBACK_TIMEOUT",
        )
        exact_count = _inspect_graph_assignments(
            assignments, uami, graph_principal, sites_selected_role_id
        )
    return _uami_graph_access_result(status, uami, exact_count)


def _graph_assignments_path(uami: _UamiState) -> str:
    return (
        f"/servicePrincipals/{uami.principal_id}/appRoleAssignments?"
        + urllib.parse.urlencode(
            {"$select": "id,appRoleId,principalId,resourceId"}
        )
    )


def _uami_graph_access_result(
    status: str, uami: _UamiState, assignment_count: int
) -> dict[str, Any]:
    return {
        "status": status,
        "principal_ref": _hashed_ref(uami.principal_id),
        "resource": "Microsoft Graph",
        "application_role": GRAPH_ROLE,
        "assignment_count": assignment_count,
    }


def _resolve_graph_role(client: GraphActivationClient) -> tuple[str, str]:
    principals = _lookup_service_principals(client, GRAPH_APP_ID)
    if not principals:
        raise GraphActivationError("GRAPH_SERVICE_PRINCIPAL_MISSING")
    if len(principals) > 1:
        raise GraphActivationError("GRAPH_SERVICE_PRINCIPAL_DUPLICATE")
    principal = principals[0]
    try:
        principal_id = _canonical_uuid(principal.get("id"))
        valid = (
            _canonical_uuid(principal.get("appId")) == GRAPH_APP_ID
            and principal.get("displayName") == "Microsoft Graph"
            and principal.get("servicePrincipalType") == "Application"
        )
    except (TypeError, ValueError):
        valid = False
        principal_id = ""
    if not valid:
        raise GraphActivationError("GRAPH_SERVICE_PRINCIPAL_MISMATCH")

    app_roles = principal.get("appRoles")
    if not isinstance(app_roles, list):
        raise GraphActivationError("GRAPH_SERVICE_PRINCIPAL_MISMATCH")
    matching_roles = [
        role
        for role in app_roles
        if isinstance(role, dict) and role.get("value") == GRAPH_ROLE
    ]
    if not matching_roles:
        raise GraphActivationError("SITES_SELECTED_ROLE_MISSING")
    if len(matching_roles) > 1:
        raise GraphActivationError("SITES_SELECTED_ROLE_DUPLICATE")
    role = matching_roles[0]
    try:
        role_id = _canonical_uuid(role.get("id"))
        role_valid = (
            role.get("isEnabled") is True
            and role.get("allowedMemberTypes") == ["Application"]
        )
    except (TypeError, ValueError):
        role_valid = False
        role_id = ""
    if not role_valid:
        raise GraphActivationError("SITES_SELECTED_ROLE_MISMATCH")
    return principal_id, role_id


def _inspect_graph_assignments(
    assignments: list[dict[str, Any]],
    uami: _UamiState,
    graph_principal_id: str,
    sites_selected_role_id: str,
) -> int:
    exact_count = 0
    for assignment in assignments:
        try:
            resource_id = _canonical_uuid(assignment.get("resourceId"))
        except (TypeError, ValueError) as exc:
            raise GraphActivationError("GRAPH_RESPONSE_INVALID") from exc
        if resource_id != graph_principal_id:
            continue
        try:
            principal_id = _canonical_uuid(assignment.get("principalId"))
            role_id = _canonical_uuid(assignment.get("appRoleId"))
        except (TypeError, ValueError) as exc:
            raise GraphActivationError("GRAPH_ROLE_ASSIGNMENT_MISMATCH") from exc
        if principal_id != uami.principal_id:
            raise GraphActivationError("GRAPH_ROLE_ASSIGNMENT_MISMATCH")
        if role_id != sites_selected_role_id:
            raise GraphActivationError("GRAPH_ROLE_ASSIGNMENT_BROADER")
        exact_count += 1
    if exact_count > 1:
        raise GraphActivationError("GRAPH_ROLE_ASSIGNMENT_DUPLICATE")
    return exact_count


def _ensure_site_read(
    client: GraphActivationClient,
    uami: _UamiState,
    site_id: str,
    readback_policy: ReadbackPolicy,
) -> dict[str, Any]:
    _require_target_site(site_id)
    permissions_path = _site_permissions_path(site_id)
    permissions = _paged(client, permissions_path)
    exact_count = _inspect_site_permissions(permissions, uami.app_id)
    status = "reused"
    if exact_count == 0:
        _post(
            client,
            permissions_path,
            {
                "roles": [SITE_ROLE],
                "grantedToIdentities": [
                    {
                        "application": {
                            "id": uami.app_id,
                            "displayName": uami.display_name,
                        }
                    }
                ],
            },
        )
        status = "created"
        permissions = _poll_readback(
            lambda: _paged(client, permissions_path),
            lambda values: bool(_inspect_site_permissions(values, uami.app_id)),
            policy=readback_policy,
            timeout_code="SITE_PERMISSION_READBACK_TIMEOUT",
        )
        exact_count = _inspect_site_permissions(permissions, uami.app_id)
    return _site_access_result(status, uami, site_id, exact_count)


def _site_permissions_path(site_id: str) -> str:
    site_path = urllib.parse.quote(site_id, safe=",")
    return f"/sites/{site_path}/permissions"


def _site_access_result(
    status: str,
    uami: _UamiState,
    site_id: str,
    permission_count: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "site_ref": _hashed_ref(site_id),
        "application_ref": _hashed_ref(uami.app_id),
        "roles": [SITE_ROLE],
        "permission_count": permission_count,
    }


def _inspect_site_permissions(
    permissions: list[dict[str, Any]], uami_app_id: str
) -> int:
    matching: list[dict[str, Any]] = []
    for permission in permissions:
        identities = _permission_identities(permission)
        application_ids: set[str] = set()
        has_non_application_identity = False
        for identity in identities:
            application = identity.get("application")
            if application is None:
                has_non_application_identity = True
                continue
            if not isinstance(application, dict):
                raise GraphActivationError("GRAPH_RESPONSE_INVALID")
            try:
                application_ids.add(_canonical_uuid(application.get("id")))
            except (TypeError, ValueError) as exc:
                raise GraphActivationError("GRAPH_RESPONSE_INVALID") from exc
        if uami_app_id not in application_ids:
            continue
        if has_non_application_identity or application_ids != {uami_app_id}:
            raise GraphActivationError("SITE_PERMISSION_MISMATCH")
        matching.append(permission)

    if len(matching) > 1:
        raise GraphActivationError("SITE_PERMISSION_DUPLICATE")
    if matching and matching[0].get("roles") != [SITE_ROLE]:
        raise GraphActivationError("SITE_PERMISSION_BROADER")
    return len(matching)


def _permission_identities(permission: dict[str, Any]) -> list[dict[str, Any]]:
    identities: list[dict[str, Any]] = []
    for key in ("grantedToIdentitiesV2", "grantedToIdentities"):
        value = permission.get(key, [])
        if value is None:
            continue
        if not isinstance(value, list) or not all(
            isinstance(item, dict) for item in value
        ):
            raise GraphActivationError("GRAPH_RESPONSE_INVALID")
        identities.extend(value)
    for key in ("grantedToV2", "grantedTo"):
        value = permission.get(key)
        if value is None:
            continue
        if not isinstance(value, dict):
            raise GraphActivationError("GRAPH_RESPONSE_INVALID")
        identities.append(value)
    return identities


def _api_application_result(state: _ApiApplicationState) -> dict[str, Any]:
    return _api_application_contract_result(
        application_status=state.application_status,
        object_id=state.object_id,
        app_id=state.app_id,
        service_principal_status=state.service_principal_status,
        service_principal_id=state.service_principal_id,
    )


def _api_application_contract_result(
    *,
    application_status: str,
    object_id: str | None,
    app_id: str | None,
    service_principal_status: str,
    service_principal_id: str | None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": application_status,
        "identifier_uri_ref": _hashed_ref(API_APP_URI),
        "sign_in_audience": "AzureADMyOrg",
        "requested_access_token_version": REQUESTED_ACCESS_TOKEN_VERSION,
        "oauth_scope": {
            "value": DELEGATED_SCOPE,
            "scope_ref": _hashed_ref(MATTER_READ_SCOPE_ID),
            "type": "User",
            "enabled": True,
        },
        "application_role": {
            "value": PERFORMANCE_LEASE_APP_ROLE,
            "role_ref": _hashed_ref(PERFORMANCE_LEASE_APP_ROLE_ID),
            "allowed_member_types": ["Application"],
            "enabled": True,
        },
        "service_principal": {
            "status": service_principal_status,
        },
    }
    if object_id is not None and app_id is not None:
        result["application_ref"] = _hashed_ref(object_id)
        result["client_ref"] = _hashed_ref(app_id)
    if service_principal_id is not None:
        result["service_principal"]["principal_ref"] = _hashed_ref(
            service_principal_id
        )
    return result


def _query_path(resource: str, filter_value: str, select: str) -> str:
    return resource + "?" + urllib.parse.urlencode(
        {"$filter": filter_value, "$select": select}
    )


def _paged(client: GraphActivationClient, path: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    current = path
    while current:
        payload = _get(client, current)
        page = payload.get("value")
        if not isinstance(page, list) or not all(
            isinstance(item, dict) for item in page
        ):
            raise GraphActivationError("GRAPH_RESPONSE_INVALID")
        values.extend(page)
        next_link = payload.get("@odata.nextLink")
        if next_link is None:
            current = ""
        elif isinstance(next_link, str):
            current = _normalize_next_link(next_link)
        else:
            raise GraphActivationError("GRAPH_PAGING_INVALID")
    return values


def _poll_readback(
    read: Callable[[], _ReadbackState],
    visible: Callable[[_ReadbackState], bool],
    *,
    policy: ReadbackPolicy,
    timeout_code: str,
) -> _ReadbackState:
    for attempt in range(policy.max_attempts):
        state = read()
        if visible(state):
            return state
        if attempt + 1 < policy.max_attempts:
            policy.sleeper(policy.backoff_seconds)
    raise GraphActivationError(timeout_code)


def _get(client: GraphActivationClient, path: str) -> dict[str, Any]:
    _require_graph_path(path)
    try:
        payload = client.get(path)
    except GraphActivationError:
        raise
    except Exception as exc:
        raise GraphActivationError("GRAPH_REQUEST_FAILED") from exc
    if not isinstance(payload, dict):
        raise GraphActivationError("GRAPH_RESPONSE_INVALID")
    return payload


def _post(
    client: GraphActivationClient, path: str, payload: dict[str, Any]
) -> dict[str, Any]:
    _require_graph_path(path)
    try:
        response = client.post(path, payload)
    except GraphActivationError:
        raise
    except Exception as exc:
        raise GraphActivationError("GRAPH_REQUEST_FAILED") from exc
    if not isinstance(response, dict):
        raise GraphActivationError("GRAPH_RESPONSE_INVALID")
    return response


def _patch(
    client: GraphActivationClient, path: str, payload: dict[str, Any]
) -> dict[str, Any]:
    _require_graph_path(path)
    try:
        response = client.patch(path, payload)
    except GraphActivationError:
        raise
    except Exception as exc:
        raise GraphActivationError("GRAPH_REQUEST_FAILED") from exc
    if not isinstance(response, dict):
        raise GraphActivationError("GRAPH_RESPONSE_INVALID")
    return response


def _require_graph_path(path: str) -> None:
    if (
        not path.startswith("/")
        or path.startswith("/beta")
        or path.startswith("/v1.0")
        or path.startswith("/_api")
        or "/_api/" in path
        or "://" in path
    ):
        raise GraphActivationError("GRAPH_PAGING_INVALID")


def _normalize_next_link(next_link: str) -> str:
    parsed = urllib.parse.urlsplit(next_link)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "graph.microsoft.com"
        or not parsed.path.startswith("/v1.0/")
        or parsed.fragment
    ):
        raise GraphActivationError("GRAPH_PAGING_INVALID")
    path = parsed.path.removeprefix("/v1.0")
    return path + (f"?{parsed.query}" if parsed.query else "")


def _require_target_site(site_id: str) -> None:
    if site_id != TARGET_SITE_ID:
        raise GraphActivationError("INVALID_TARGET_SITE")


def _canonical_uuid(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("UUID value must be text")
    return str(uuid.UUID(value))


def _odata_literal(value: str) -> str:
    return value.replace("'", "''")


def _hashed_ref(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "GRAPH_APP_ID",
    "GRAPH_ROLE",
    "MATTER_READ_SCOPE_ID",
    "PERFORMANCE_LEASE_APP_ROLE",
    "PERFORMANCE_LEASE_APP_ROLE_ID",
    "SCHEMA_VERSION",
    "SITE_ROLE",
    "TARGET_SITE_ID",
    "ApiApplicationBinding",
    "GraphActivationClient",
    "GraphActivationError",
    "activate_nac_bff_graph",
    "ensure_entra_api_application",
    "ensure_entra_api_application_binding",
    "ensure_provisioner_performance_lease",
    "ensure_nac_bff_graph_activation",
    "ensure_site_read_permission",
    "ensure_uami_sites_selected",
    "inspect_entra_api_application",
    "inspect_provisioner_application_roles",
    "inspect_provisioner_performance_lease",
    "inspect_site_permission_administration",
    "inspect_site_read_permission",
    "inspect_uami_sites_selected",
]
