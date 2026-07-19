from __future__ import annotations

import copy
import json
import unittest
import urllib.parse
import uuid
from typing import Any

from nac_bff.azure_activation import (
    API_APP_DISPLAY_NAME,
    API_APP_URI,
    CLI_TEST_CLIENT_ID,
    DELEGATED_SCOPE,
)
from nac_bff.graph_activation import (
    GRAPH_APP_ID,
    MATTER_READ_SCOPE_ID,
    PROVISIONER_CLIENT_ID,
    PROVISIONER_GRAPH_APPLICATION_ROLES,
    TARGET_SITE_ID,
    GraphActivationError,
    ReadbackPolicy,
    activate_nac_bff_graph,
    ensure_entra_api_application,
    ensure_site_read_permission,
    ensure_uami_sites_selected,
    inspect_entra_api_application,
    inspect_provisioner_application_roles,
    inspect_site_permission_administration,
    inspect_site_read_permission,
    inspect_uami_sites_selected,
)


APP_OBJECT_ID = "11111111-1111-4111-8111-111111111111"
APP_CLIENT_ID = "22222222-2222-4222-8222-222222222222"
APP_SERVICE_PRINCIPAL_ID = "33333333-3333-4333-8333-333333333333"
UAMI_APP_ID = "44444444-4444-4a44-8444-444444444444"
UAMI_PRINCIPAL_ID = "55555555-5555-4555-8555-555555555555"
GRAPH_PRINCIPAL_ID = "66666666-6666-4666-8666-666666666666"
SITES_SELECTED_ROLE_ID = "77777777-7777-4777-8777-777777777777"
BROADER_ROLE_ID = "88888888-8888-4888-8888-888888888888"
OTHER_APP_ID = "99999999-9999-4999-8999-999999999999"
PROVISIONER_PRINCIPAL_ID = "aaaaaaaa-1111-4111-8111-111111111111"
PROVISIONER_ROLE_IDS = {
    name: f"bbbbbbbb-2222-4222-8222-{index:012d}"
    for index, name in enumerate(PROVISIONER_GRAPH_APPLICATION_ROLES, start=1)
}


class FakeGraphActivationClient:
    def __init__(self) -> None:
        self.applications: list[dict[str, Any]] = []
        self.service_principals: list[dict[str, Any]] = [
            {
                "id": GRAPH_PRINCIPAL_ID,
                "appId": GRAPH_APP_ID,
                "displayName": "Microsoft Graph",
                "servicePrincipalType": "Application",
                "appRoles": [
                    {
                        "id": SITES_SELECTED_ROLE_ID,
                        "value": "Sites.Selected",
                        "isEnabled": True,
                        "allowedMemberTypes": ["Application"],
                    },
                    {
                        "id": BROADER_ROLE_ID,
                        "value": "Sites.Read.All",
                        "isEnabled": True,
                        "allowedMemberTypes": ["Application"],
                    },
                    *[
                        {
                            "id": role_id,
                            "value": name,
                            "isEnabled": True,
                            "allowedMemberTypes": ["Application"],
                        }
                        for name, role_id in PROVISIONER_ROLE_IDS.items()
                    ],
                ],
            },
            {
                "id": PROVISIONER_PRINCIPAL_ID,
                "appId": PROVISIONER_CLIENT_ID,
                "displayName": "NaC M365 Provisioning",
                "servicePrincipalType": "Application",
                "appRoles": [],
            },
            {
                "id": UAMI_PRINCIPAL_ID,
                "appId": UAMI_APP_ID,
                "displayName": "func-nac-bff-test-funktion8",
                "servicePrincipalType": "ManagedIdentity",
                "appRoles": [],
            },
        ]
        self.assignments: list[dict[str, Any]] = []
        self.provisioner_assignments: list[dict[str, Any]] = [
            {
                "id": f"assignment-{index}",
                "principalId": PROVISIONER_PRINCIPAL_ID,
                "resourceId": GRAPH_PRINCIPAL_ID,
                "appRoleId": PROVISIONER_ROLE_IDS[name],
            }
            for index, name in enumerate(
                PROVISIONER_GRAPH_APPLICATION_ROLES,
                start=1,
            )
        ]
        self.permissions: list[dict[str, Any]] = []
        self.gets: list[str] = []
        self.posts: list[tuple[str, dict[str, Any]]] = []
        self.patches: list[tuple[str, dict[str, Any]]] = []
        self.application_lookup_override: list[dict[str, Any]] | None = None
        self.application_readback_delay = 0
        self.api_service_principal_readback_delay = 0
        self.uami_lookup_delay = 0
        self.assignment_readback_delay = 0
        self.permission_readback_delay = 0
        self._application_hidden_reads = 0
        self._api_service_principal_hidden_reads = 0
        self._assignment_hidden_reads = 0
        self._permission_hidden_reads = 0
        self.drop_application_create = False
        self.drop_service_principal_create = False
        self.drop_assignment_create = False
        self.drop_permission_create = False
        self.request_error: Exception | None = None

    def get(self, path: str) -> dict[str, Any]:
        self.gets.append(path)
        if self.request_error is not None:
            raise self.request_error
        if path.startswith("/applications?"):
            if self.application_lookup_override is not None:
                values = self.application_lookup_override
            else:
                values = [
                    app
                    for app in self.applications
                    if API_APP_URI in app.get("identifierUris", [])
                ]
            if self._application_hidden_reads:
                self._application_hidden_reads -= 1
                values = []
            return {"value": copy.deepcopy(values)}
        if path.startswith("/servicePrincipals?"):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
            filter_value = query["$filter"][0]
            app_id = filter_value.split("'")[1]
            values = [
                item
                for item in self.service_principals
                if item.get("appId") == app_id
            ]
            if app_id == APP_CLIENT_ID and self._api_service_principal_hidden_reads:
                self._api_service_principal_hidden_reads -= 1
                values = []
            if app_id == UAMI_APP_ID and self.uami_lookup_delay:
                self.uami_lookup_delay -= 1
                values = []
            return {"value": copy.deepcopy(values)}
        if path.startswith(
            f"/servicePrincipals/{PROVISIONER_PRINCIPAL_ID}/appRoleAssignments"
        ):
            return {"value": copy.deepcopy(self.provisioner_assignments)}
        if path.startswith(
            f"/servicePrincipals/{UAMI_PRINCIPAL_ID}/appRoleAssignments"
        ):
            values = self.assignments
            if self._assignment_hidden_reads:
                self._assignment_hidden_reads -= 1
                values = []
            return {"value": copy.deepcopy(values)}
        if path.startswith("/sites/") and path.endswith("/permissions"):
            values = self.permissions
            if self._permission_hidden_reads:
                self._permission_hidden_reads -= 1
                values = []
            return {"value": copy.deepcopy(values)}
        raise AssertionError(f"unexpected GET path: {path}")

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.posts.append((path, copy.deepcopy(payload)))
        if path == "/applications":
            created = {
                **copy.deepcopy(payload),
                "id": APP_OBJECT_ID,
                "appId": APP_CLIENT_ID,
            }
            if not self.drop_application_create:
                self.applications.append(created)
                self._application_hidden_reads = self.application_readback_delay
            return copy.deepcopy(created)
        if path == "/servicePrincipals":
            created = {
                "id": APP_SERVICE_PRINCIPAL_ID,
                "appId": payload["appId"],
                "displayName": API_APP_DISPLAY_NAME,
                "servicePrincipalType": "Application",
                "appRoles": [],
            }
            if not self.drop_service_principal_create:
                self.service_principals.append(created)
                self._api_service_principal_hidden_reads = (
                    self.api_service_principal_readback_delay
                )
            return copy.deepcopy(created)
        if path.endswith("/appRoleAssignments"):
            created = {
                **copy.deepcopy(payload),
                "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            }
            if not self.drop_assignment_create:
                self.assignments.append(created)
                self._assignment_hidden_reads = self.assignment_readback_delay
            return copy.deepcopy(created)
        if path.startswith("/sites/") and path.endswith("/permissions"):
            created = {
                **copy.deepcopy(payload),
                "id": "site-permission-1",
            }
            if not self.drop_permission_create:
                self.permissions.append(created)
                self._permission_hidden_reads = self.permission_readback_delay
            return copy.deepcopy(created)
        raise AssertionError(f"unexpected POST path: {path}")

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.patches.append((path, copy.deepcopy(payload)))
        return {}

    def exact_application(self) -> dict[str, Any]:
        return {
            "id": APP_OBJECT_ID,
            "appId": APP_CLIENT_ID,
            "displayName": API_APP_DISPLAY_NAME,
            "identifierUris": [API_APP_URI],
            "signInAudience": "AzureADMyOrg",
            "api": {
                "requestedAccessTokenVersion": 2,
                "oauth2PermissionScopes": [
                    {
                        "id": MATTER_READ_SCOPE_ID,
                        "value": DELEGATED_SCOPE,
                        "type": "User",
                        "isEnabled": True,
                    }
                ],
                "preAuthorizedApplications": [
                    {
                        "appId": CLI_TEST_CLIENT_ID,
                        "delegatedPermissionIds": [MATTER_READ_SCOPE_ID],
                    }
                ],
            },
            "appRoles": [],
            "requiredResourceAccess": [],
        }

    def exact_api_service_principal(self) -> dict[str, Any]:
        return {
            "id": APP_SERVICE_PRINCIPAL_ID,
            "appId": APP_CLIENT_ID,
            "displayName": API_APP_DISPLAY_NAME,
            "servicePrincipalType": "Application",
            "appRoles": [],
        }

    def exact_assignment(self) -> dict[str, Any]:
        return {
            "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "principalId": UAMI_PRINCIPAL_ID,
            "resourceId": GRAPH_PRINCIPAL_ID,
            "appRoleId": SITES_SELECTED_ROLE_ID,
        }

    def exact_permission(self) -> dict[str, Any]:
        return {
            "id": "site-permission-1",
            "roles": ["read"],
            "grantedToIdentitiesV2": [
                {"application": {"id": UAMI_APP_ID, "displayName": "BFF UAMI"}}
            ],
        }


class NacBffGraphActivationTests(unittest.TestCase):
    def test_create_then_reuse_is_strictly_idempotent_and_redacted(self) -> None:
        client = FakeGraphActivationClient()

        first = activate_nac_bff_graph(client, UAMI_APP_ID)
        post_count = len(client.posts)
        second = activate_nac_bff_graph(client, UAMI_APP_ID)
        serialized = json.dumps(second, sort_keys=True)

        self.assertEqual(first["status"], "PASSED")
        self.assertEqual(first["api_application"]["status"], "created")
        self.assertEqual(
            first["api_application"]["service_principal"]["status"], "created"
        )
        self.assertEqual(first["uami_graph_access"]["status"], "created")
        self.assertEqual(first["site_access"]["status"], "created")
        self.assertEqual(second["api_application"]["status"], "reused")
        self.assertEqual(second["uami_graph_access"]["status"], "reused")
        self.assertEqual(second["site_access"]["status"], "reused")
        self.assertEqual(len(client.posts), post_count)
        self.assertEqual(client.patches, [])
        self.assertEqual(second["site_access"]["roles"], ["read"])
        self.assertEqual(
            second["uami_graph_access"]["application_role"], "Sites.Selected"
        )
        for raw_value in (
            APP_OBJECT_ID,
            APP_CLIENT_ID,
            APP_SERVICE_PRINCIPAL_ID,
            UAMI_APP_ID,
            UAMI_PRINCIPAL_ID,
            GRAPH_PRINCIPAL_ID,
            SITES_SELECTED_ROLE_ID,
            TARGET_SITE_ID,
            API_APP_URI,
            MATTER_READ_SCOPE_ID,
        ):
            self.assertNotIn(raw_value, serialized)
        self.assertTrue(second["site_access"]["site_ref"].startswith("sha256:"))
        self.assertFalse(second["boundaries"]["privileged_apply_used"])

    def test_application_create_uses_stable_scope_and_exact_contract(self) -> None:
        client = FakeGraphActivationClient()

        result = ensure_entra_api_application(client)
        application_payload = client.posts[0][1]
        scope = application_payload["api"]["oauth2PermissionScopes"][0]

        self.assertEqual(result["status"], "created")
        self.assertEqual(
            MATTER_READ_SCOPE_ID,
            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{API_APP_URI}#{DELEGATED_SCOPE}")),
        )
        self.assertEqual(application_payload["identifierUris"], [API_APP_URI])
        self.assertEqual(application_payload["signInAudience"], "AzureADMyOrg")
        self.assertEqual(application_payload["requiredResourceAccess"], [])
        self.assertEqual(application_payload["api"]["requestedAccessTokenVersion"], 2)
        self.assertEqual(scope["id"], MATTER_READ_SCOPE_ID)
        self.assertEqual(scope["value"], "Matter.Read")
        self.assertEqual(
            application_payload["api"]["preAuthorizedApplications"],
            [
                {
                    "appId": CLI_TEST_CLIENT_ID,
                    "delegatedPermissionIds": [MATTER_READ_SCOPE_ID],
                }
            ],
        )

    def test_application_reuse_performs_no_write(self) -> None:
        client = FakeGraphActivationClient()
        client.applications = [client.exact_application()]
        client.service_principals.append(client.exact_api_service_principal())

        result = ensure_entra_api_application(client)

        self.assertEqual(result["status"], "reused")
        self.assertEqual(result["service_principal"]["status"], "reused")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.patches, [])

    def test_api_application_inspection_is_read_only_and_redacted(self) -> None:
        client = FakeGraphActivationClient()

        absent = inspect_entra_api_application(client)
        client.applications = [client.exact_application()]
        without_principal = inspect_entra_api_application(client)
        client.service_principals.append(client.exact_api_service_principal())
        present = inspect_entra_api_application(client)

        self.assertEqual(absent["status"], "absent")
        self.assertEqual(absent["service_principal"]["status"], "absent")
        self.assertEqual(without_principal["status"], "present")
        self.assertEqual(
            without_principal["service_principal"]["status"], "absent"
        )
        self.assertEqual(present["status"], "present")
        self.assertEqual(present["service_principal"]["status"], "present")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.patches, [])
        serialized = json.dumps([absent, without_principal, present])
        for raw_value in (
            APP_OBJECT_ID,
            APP_CLIENT_ID,
            APP_SERVICE_PRINCIPAL_ID,
            API_APP_URI,
            MATTER_READ_SCOPE_ID,
        ):
            self.assertNotIn(raw_value, serialized)

    def test_api_application_inspection_fails_closed_on_invalid_state(self) -> None:
        duplicate = FakeGraphActivationClient()
        duplicate.applications = [
            duplicate.exact_application(),
            duplicate.exact_application(),
        ]
        self._assert_error(
            "API_APPLICATION_DUPLICATE", inspect_entra_api_application, duplicate
        )

        mismatch = FakeGraphActivationClient()
        application = mismatch.exact_application()
        application["displayName"] = "Unexpected API"
        mismatch.applications = [application]
        self._assert_error(
            "API_APPLICATION_MISMATCH", inspect_entra_api_application, mismatch
        )
        self.assertEqual(duplicate.posts, [])
        self.assertEqual(mismatch.posts, [])

    def test_application_and_service_principal_poll_delayed_readback(self) -> None:
        client = FakeGraphActivationClient()
        client.application_readback_delay = 2
        client.api_service_principal_readback_delay = 1
        sleeps: list[float] = []
        policy = ReadbackPolicy(4, 0.25, sleeps.append)

        result = ensure_entra_api_application(client, readback_policy=policy)

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["service_principal"]["status"], "created")
        self.assertEqual(sleeps, [0.25, 0.25, 0.25])
        self.assertEqual(
            [path for path, _payload in client.posts if path == "/applications"],
            ["/applications"],
        )
        self.assertEqual(
            [path for path, _payload in client.posts if path == "/servicePrincipals"],
            ["/servicePrincipals"],
        )

    def test_application_readback_timeout_is_bounded_and_redacted(self) -> None:
        client = FakeGraphActivationClient()
        client.drop_application_create = True
        sleeps: list[float] = []
        policy = ReadbackPolicy(3, 0.5, sleeps.append)

        self._assert_error(
            "API_APPLICATION_READBACK_TIMEOUT",
            ensure_entra_api_application,
            client,
            readback_policy=policy,
        )

        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(
            [path for path, _payload in client.posts if path == "/applications"],
            ["/applications"],
        )

    def test_service_principal_readback_timeout_does_not_repeat_post(self) -> None:
        client = FakeGraphActivationClient()
        client.applications = [client.exact_application()]
        client.drop_service_principal_create = True
        sleeps: list[float] = []
        policy = ReadbackPolicy(3, 0.5, sleeps.append)

        self._assert_error(
            "API_SERVICE_PRINCIPAL_READBACK_TIMEOUT",
            ensure_entra_api_application,
            client,
            readback_policy=policy,
        )

        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(
            [path for path, _payload in client.posts if path == "/servicePrincipals"],
            ["/servicePrincipals"],
        )

    def test_duplicate_application_fails_closed_without_write(self) -> None:
        client = FakeGraphActivationClient()
        client.applications = [
            client.exact_application(),
            client.exact_application(),
        ]

        self._assert_error(
            "API_APPLICATION_DUPLICATE", ensure_entra_api_application, client
        )
        self.assertEqual(client.posts, [])

    def test_application_contract_mismatches_fail_closed(self) -> None:
        mutations = (
            lambda app: app.update(signInAudience="AzureADMultipleOrgs"),
            lambda app: app["api"].update(requestedAccessTokenVersion=1),
            lambda app: app["api"]["oauth2PermissionScopes"].append(
                {
                    "id": str(uuid.uuid4()),
                    "value": "Matter.Write",
                    "type": "User",
                    "isEnabled": True,
                }
            ),
            lambda app: app.update(
                requiredResourceAccess=[{"resourceAppId": GRAPH_APP_ID}]
            ),
            lambda app: app.update(
                appRoles=[
                    {
                        "id": str(uuid.uuid4()),
                        "value": "Matter.Read.All",
                        "isEnabled": True,
                        "allowedMemberTypes": ["Application"],
                    }
                ]
            ),
            lambda app: app.update(identifierUris=[API_APP_URI, "api://broader"]),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                client = FakeGraphActivationClient()
                application = client.exact_application()
                mutate(application)
                client.application_lookup_override = [application]

                self._assert_error(
                    "API_APPLICATION_MISMATCH", ensure_entra_api_application, client
                )
                self.assertEqual(client.posts, [])

    def test_api_service_principal_duplicate_and_mismatch_fail_closed(self) -> None:
        duplicate = FakeGraphActivationClient()
        duplicate.applications = [duplicate.exact_application()]
        duplicate.service_principals.extend(
            [
                duplicate.exact_api_service_principal(),
                duplicate.exact_api_service_principal(),
            ]
        )
        self._assert_error(
            "API_SERVICE_PRINCIPAL_DUPLICATE",
            ensure_entra_api_application,
            duplicate,
        )

        mismatch = FakeGraphActivationClient()
        mismatch.applications = [mismatch.exact_application()]
        wrong = mismatch.exact_api_service_principal()
        wrong["displayName"] = "Unexpected API"
        mismatch.service_principals.append(wrong)
        self._assert_error(
            "API_SERVICE_PRINCIPAL_MISMATCH",
            ensure_entra_api_application,
            mismatch,
        )

        broader = FakeGraphActivationClient()
        broader.applications = [broader.exact_application()]
        principal = broader.exact_api_service_principal()
        principal["appRoles"] = [
            {
                "id": str(uuid.uuid4()),
                "value": "Matter.Read.All",
                "isEnabled": True,
                "allowedMemberTypes": ["Application"],
            }
        ]
        broader.service_principals.append(principal)
        self._assert_error(
            "API_SERVICE_PRINCIPAL_MISMATCH",
            inspect_entra_api_application,
            broader,
        )
        self.assertEqual(broader.posts, [])

    def test_uami_resolution_polls_delayed_visibility_without_write(self) -> None:
        client = FakeGraphActivationClient()
        client.uami_lookup_delay = 2
        client.assignments = [client.exact_assignment()]
        sleeps: list[float] = []
        policy = ReadbackPolicy(4, 0.25, sleeps.append)

        result = ensure_uami_sites_selected(
            client, UAMI_APP_ID, readback_policy=policy
        )

        self.assertEqual(result["status"], "reused")
        self.assertEqual(sleeps, [0.25, 0.25])
        self.assertEqual(client.posts, [])

    def test_uami_resolution_timeout_is_bounded_and_performs_no_write(self) -> None:
        client = FakeGraphActivationClient()
        client.service_principals = [client.service_principals[0]]
        sleeps: list[float] = []
        policy = ReadbackPolicy(3, 0.5, sleeps.append)

        self._assert_error(
            "UAMI_SERVICE_PRINCIPAL_READBACK_TIMEOUT",
            ensure_uami_sites_selected,
            client,
            UAMI_APP_ID,
            readback_policy=policy,
        )

        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(client.posts, [])

    def test_uami_sites_selected_create_and_reuse_are_idempotent(self) -> None:
        client = FakeGraphActivationClient()

        first = ensure_uami_sites_selected(client, UAMI_APP_ID)
        second = ensure_uami_sites_selected(client, UAMI_APP_ID)

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "reused")
        assignment_posts = [
            path
            for path, _payload in client.posts
            if path.endswith("appRoleAssignments")
        ]
        self.assertEqual(len(assignment_posts), 1)
        self.assertNotIn(UAMI_APP_ID, json.dumps(second))

    def test_uami_sites_selected_inspection_is_read_only_and_redacted(self) -> None:
        client = FakeGraphActivationClient()

        absent = inspect_uami_sites_selected(client, UAMI_APP_ID)
        client.assignments = [client.exact_assignment()]
        present = inspect_uami_sites_selected(client, UAMI_APP_ID)

        self.assertEqual(absent["status"], "absent")
        self.assertEqual(absent["assignment_count"], 0)
        self.assertEqual(present["status"], "present")
        self.assertEqual(present["assignment_count"], 1)
        self.assertEqual(client.posts, [])
        self.assertEqual(client.patches, [])
        serialized = json.dumps([absent, present])
        for raw_value in (
            UAMI_APP_ID,
            UAMI_PRINCIPAL_ID,
            GRAPH_PRINCIPAL_ID,
            SITES_SELECTED_ROLE_ID,
        ):
            self.assertNotIn(raw_value, serialized)

    def test_broader_graph_application_role_blocks_before_write(self) -> None:
        client = FakeGraphActivationClient()
        client.assignments = [
            {
                "id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                "principalId": UAMI_PRINCIPAL_ID,
                "resourceId": GRAPH_PRINCIPAL_ID,
                "appRoleId": BROADER_ROLE_ID,
            }
        ]

        self._assert_error(
            "GRAPH_ROLE_ASSIGNMENT_BROADER",
            inspect_uami_sites_selected,
            client,
            UAMI_APP_ID,
        )
        self.assertEqual(client.posts, [])

    def test_duplicate_sites_selected_assignments_block(self) -> None:
        client = FakeGraphActivationClient()
        client.assignments = [client.exact_assignment(), client.exact_assignment()]

        self._assert_error(
            "GRAPH_ROLE_ASSIGNMENT_DUPLICATE",
            inspect_uami_sites_selected,
            client,
            UAMI_APP_ID,
        )

    def test_sites_selected_inspection_blocks_principal_mismatch(self) -> None:
        client = FakeGraphActivationClient()
        assignment = client.exact_assignment()
        assignment["principalId"] = OTHER_APP_ID
        client.assignments = [assignment]

        self._assert_error(
            "GRAPH_ROLE_ASSIGNMENT_MISMATCH",
            inspect_uami_sites_selected,
            client,
            UAMI_APP_ID,
        )
        self.assertEqual(client.posts, [])

    def test_assignment_create_polls_delayed_visibility_once(self) -> None:
        client = FakeGraphActivationClient()
        client.assignment_readback_delay = 2
        sleeps: list[float] = []
        policy = ReadbackPolicy(4, 0.25, sleeps.append)

        result = ensure_uami_sites_selected(
            client, UAMI_APP_ID, readback_policy=policy
        )

        self.assertEqual(result["status"], "created")
        self.assertEqual(sleeps, [0.25, 0.25])
        self.assertEqual(
            [
                path
                for path, _payload in client.posts
                if path.endswith("/appRoleAssignments")
            ],
            [f"/servicePrincipals/{UAMI_PRINCIPAL_ID}/appRoleAssignments"],
        )

    def test_assignment_readback_timeout_does_not_repeat_post(self) -> None:
        client = FakeGraphActivationClient()
        client.drop_assignment_create = True
        sleeps: list[float] = []
        policy = ReadbackPolicy(3, 0.5, sleeps.append)

        self._assert_error(
            "GRAPH_ROLE_ASSIGNMENT_READBACK_TIMEOUT",
            ensure_uami_sites_selected,
            client,
            UAMI_APP_ID,
            readback_policy=policy,
        )

        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(
            [
                path
                for path, _payload in client.posts
                if path.endswith("/appRoleAssignments")
            ],
            [f"/servicePrincipals/{UAMI_PRINCIPAL_ID}/appRoleAssignments"],
        )

    def test_provisioner_application_roles_are_exact_and_read_only(self) -> None:
        client = FakeGraphActivationClient()

        result = inspect_provisioner_application_roles(client)

        self.assertEqual(result["status"], "present")
        self.assertEqual(
            set(result["application_roles"]),
            set(PROVISIONER_GRAPH_APPLICATION_ROLES),
        )
        self.assertEqual(
            result["assignment_count"],
            len(PROVISIONER_GRAPH_APPLICATION_ROLES),
        )
        self.assertEqual(client.posts, [])

    def test_provisioner_application_roles_block_broader_assignment(self) -> None:
        client = FakeGraphActivationClient()
        client.provisioner_assignments.append(
            {
                "id": "assignment-broader",
                "principalId": PROVISIONER_PRINCIPAL_ID,
                "resourceId": GRAPH_PRINCIPAL_ID,
                "appRoleId": BROADER_ROLE_ID,
            }
        )

        self._assert_error(
            "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH",
            inspect_provisioner_application_roles,
            client,
        )

    def test_site_permission_admin_capability_is_read_only_and_redacted(
        self,
    ) -> None:
        client = FakeGraphActivationClient()
        client.permissions = [client.exact_permission()]

        result = inspect_site_permission_administration(client)

        self.assertEqual(result["status"], "available")
        self.assertEqual(result["permission_count"], 1)
        self.assertNotIn(TARGET_SITE_ID, json.dumps(result))
        self.assertEqual(client.posts, [])

    def test_site_permission_admin_capability_maps_request_failure(self) -> None:
        client = FakeGraphActivationClient()
        client.request_error = PermissionError("forbidden")

        self._assert_error(
            "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE",
            inspect_site_permission_administration,
            client,
        )

    def test_site_permission_admin_capability_maps_invalid_shape(self) -> None:
        client = FakeGraphActivationClient()
        client.get = lambda _path: {"value": "invalid"}

        self._assert_error(
            "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE",
            inspect_site_permission_administration,
            client,
        )

    def test_site_permission_admin_capability_maps_invalid_paging(self) -> None:
        client = FakeGraphActivationClient()
        client.get = lambda _path: {
            "value": [],
            "@odata.nextLink": 42,
        }

        self._assert_error(
            "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE",
            inspect_site_permission_administration,
            client,
        )

    def test_site_permission_create_polls_delayed_visibility_once(self) -> None:
        client = FakeGraphActivationClient()
        client.permission_readback_delay = 2
        sleeps: list[float] = []
        policy = ReadbackPolicy(4, 0.25, sleeps.append)

        result = ensure_site_read_permission(
            client, UAMI_APP_ID, readback_policy=policy
        )

        self.assertEqual(result["status"], "created")
        self.assertEqual(sleeps, [0.25, 0.25])
        self.assertEqual(
            [
                path
                for path, _payload in client.posts
                if path.startswith("/sites/") and path.endswith("/permissions")
            ],
            [f"/sites/{TARGET_SITE_ID}/permissions"],
        )

    def test_site_read_create_and_reuse_are_idempotent(self) -> None:
        client = FakeGraphActivationClient()

        first = ensure_site_read_permission(client, UAMI_APP_ID)
        second = ensure_site_read_permission(client, UAMI_APP_ID)

        self.assertEqual(first["status"], "created")
        self.assertEqual(second["status"], "reused")
        permission_posts = [
            payload
            for path, payload in client.posts
            if path.startswith("/sites/") and path.endswith("/permissions")
        ]
        self.assertEqual(len(permission_posts), 1)
        self.assertEqual(permission_posts[0]["roles"], ["read"])

    def test_site_read_inspection_deduplicates_legacy_and_v2_identity(self) -> None:
        client = FakeGraphActivationClient()

        absent = inspect_site_read_permission(client, UAMI_APP_ID)
        client.permissions = [
            {
                "id": "site-permission-1",
                "roles": ["read"],
                "grantedTo": {
                    "application": {
                        "id": UAMI_APP_ID,
                        "displayName": "func-nac-bff-test-funktion8",
                    }
                },
                "grantedToV2": {
                    "application": {
                        "id": UAMI_APP_ID.upper(),
                        "displayName": "func-nac-bff-test-funktion8",
                    }
                },
            }
        ]
        present = inspect_site_read_permission(client, UAMI_APP_ID)
        reused = ensure_site_read_permission(client, UAMI_APP_ID)

        self.assertEqual(absent["status"], "absent")
        self.assertEqual(absent["permission_count"], 0)
        self.assertEqual(present["status"], "present")
        self.assertEqual(present["permission_count"], 1)
        self.assertEqual(reused["status"], "reused")
        self.assertEqual(client.posts, [])
        self.assertEqual(client.patches, [])
        serialized = json.dumps([absent, present, reused])
        for raw_value in (UAMI_APP_ID, UAMI_PRINCIPAL_ID, TARGET_SITE_ID):
            self.assertNotIn(raw_value, serialized)

    def test_site_read_inspection_deduplicates_identity_collections(self) -> None:
        client = FakeGraphActivationClient()
        legacy_identity = {
            "application": {
                "id": UAMI_APP_ID,
                "displayName": "func-nac-bff-test-funktion8",
            }
        }
        v2_identity = {
            "application": {
                "id": UAMI_APP_ID.upper(),
                "displayName": "func-nac-bff-test-funktion8",
            }
        }
        client.permissions = [
            {
                "id": "site-permission-1",
                "roles": ["read"],
                "grantedToIdentities": [legacy_identity],
                "grantedToIdentitiesV2": [v2_identity],
            }
        ]

        result = inspect_site_read_permission(client, UAMI_APP_ID)

        self.assertEqual(result["status"], "present")
        self.assertEqual(result["permission_count"], 1)
        self.assertEqual(client.posts, [])
        self.assertEqual(client.patches, [])

    def test_broader_or_duplicate_site_grants_block(self) -> None:
        broader = FakeGraphActivationClient()
        permission = broader.exact_permission()
        permission["roles"] = ["write"]
        broader.permissions = [permission]
        self._assert_error(
            "SITE_PERMISSION_BROADER",
            inspect_site_read_permission,
            broader,
            UAMI_APP_ID,
        )
        self.assertEqual(broader.posts, [])

        duplicate = FakeGraphActivationClient()
        duplicate.permissions = [
            duplicate.exact_permission(),
            duplicate.exact_permission(),
        ]
        self._assert_error(
            "SITE_PERMISSION_DUPLICATE",
            inspect_site_read_permission,
            duplicate,
            UAMI_APP_ID,
        )

    def test_site_grant_with_additional_identity_blocks(self) -> None:
        client = FakeGraphActivationClient()
        permission = client.exact_permission()
        permission["grantedToIdentitiesV2"].append(
            {"application": {"id": OTHER_APP_ID, "displayName": "Other"}}
        )
        client.permissions = [permission]

        self._assert_error(
            "SITE_PERMISSION_MISMATCH",
            inspect_site_read_permission,
            client,
            UAMI_APP_ID,
        )

    def test_site_readback_timeout_and_target_allowlist_are_required(self) -> None:
        missing = FakeGraphActivationClient()
        missing.drop_permission_create = True
        sleeps: list[float] = []
        policy = ReadbackPolicy(3, 0.5, sleeps.append)
        self._assert_error(
            "SITE_PERMISSION_READBACK_TIMEOUT",
            ensure_site_read_permission,
            missing,
            UAMI_APP_ID,
            readback_policy=policy,
        )
        self.assertEqual(sleeps, [0.5, 0.5])
        self.assertEqual(
            [
                path
                for path, _payload in missing.posts
                if path.startswith("/sites/") and path.endswith("/permissions")
            ],
            [f"/sites/{TARGET_SITE_ID}/permissions"],
        )

        wrong_site = FakeGraphActivationClient()
        self._assert_error(
            "INVALID_TARGET_SITE",
            ensure_site_read_permission,
            wrong_site,
            UAMI_APP_ID,
            site_id="other.sharepoint.com,site,web",
        )
        self.assertEqual(wrong_site.posts, [])

    def test_uami_lookup_null_duplicate_and_mismatch_fail_closed(self) -> None:
        missing = FakeGraphActivationClient()
        missing.service_principals = missing.service_principals[:2]
        self._assert_error(
            "UAMI_SERVICE_PRINCIPAL_READBACK_TIMEOUT",
            ensure_uami_sites_selected,
            missing,
            UAMI_APP_ID,
            readback_policy=ReadbackPolicy(1, 0, lambda _delay: None),
        )

        duplicate = FakeGraphActivationClient()
        duplicate.service_principals.append(
            copy.deepcopy(duplicate.service_principals[2])
        )
        self._assert_error(
            "UAMI_SERVICE_PRINCIPAL_DUPLICATE",
            ensure_uami_sites_selected,
            duplicate,
            UAMI_APP_ID,
        )

        mismatch = FakeGraphActivationClient()
        mismatch.service_principals[2]["servicePrincipalType"] = "Application"
        self._assert_error(
            "UAMI_SERVICE_PRINCIPAL_MISMATCH",
            ensure_uami_sites_selected,
            mismatch,
            UAMI_APP_ID,
        )

    def test_readback_policy_rejects_invalid_bounds(self) -> None:
        for attempts in (0, -1, True):
            with self.subTest(max_attempts=attempts):
                with self.assertRaises(ValueError):
                    ReadbackPolicy(attempts, 0, lambda _delay: None)
        for backoff in (-0.1, True):
            with self.subTest(backoff_seconds=backoff):
                with self.assertRaises(ValueError):
                    ReadbackPolicy(1, backoff, lambda _delay: None)

    def test_transport_failure_is_wrapped_without_raw_error_data(self) -> None:
        client = FakeGraphActivationClient()
        secret = "provider-response-with-sensitive-id"
        client.request_error = RuntimeError(secret)

        with self.assertRaises(GraphActivationError) as caught:
            ensure_entra_api_application(client)

        self.assertEqual(caught.exception.code, "GRAPH_REQUEST_FAILED")
        serialized = json.dumps(caught.exception.redacted_result())
        self.assertNotIn(secret, serialized)
        self.assertEqual(
            caught.exception.redacted_result()["error"]["code"],
            "GRAPH_REQUEST_FAILED",
        )

    def _assert_error(
        self,
        code: str,
        callable_: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        with self.assertRaises(GraphActivationError) as caught:
            callable_(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.redacted_result()["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
