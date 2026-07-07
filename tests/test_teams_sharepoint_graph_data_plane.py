from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import urllib.parse
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.privileged_change import (  # noqa: E402
    DEFAULT_PRIVILEGED_CHANGE_CONFIG,
    DEFAULT_PROVISIONED_STATE,
    build_application_owner_readiness,
    build_privileged_change_plan,
    load_privileged_applied_state,
    load_privileged_change_config,
    load_provisioned_state,
    summarize_privileged_change_plan,
    validate_privileged_change_config,
)
from nac_m365_graph.privileged_apply import apply_privileged_change_path  # noqa: E402
from nac_m365_graph.provisioner import build_plan, summarize_plan  # noqa: E402
from nac_m365_graph.runtime_metadata import (  # noqa: E402
    build_runtime_metadata_snapshot,
    redact_runtime_metadata_snapshot,
    write_runtime_metadata_artifact,
)
from nac_m365_graph.runtime_certificate_readiness import (  # noqa: E402
    build_runtime_certificate_readiness,
)
from nac_m365_graph.runtime_smoke import (  # noqa: E402
    redact_runtime_site_smoke_result,
    run_runtime_site_smoke,
    write_runtime_site_smoke_artifact,
)
from nac_m365_graph.schema import (  # noqa: E402
    DEFAULT_SCHEMA,
    column_create_payload,
    load_schema,
    validate_schema,
)


CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-graph-data-plane.contract.json"
APPLIED_STATE = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.privileged-change-path.applied.f8.json"
RUNTIME_SMOKE_STATE = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.runtime-smoke.f8.json"
RUNTIME_METADATA_STATE = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.runtime-metadata.f8.json"
GRAPH_APP_ID = "00000003-0000-0000-c000-000000000000"


class FakeGraphWriteClient:
    def __init__(self, provisioned_state: dict) -> None:
        self.provisioned_state = provisioned_state
        self.posts: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, dict]] = []
        self.group: dict | None = None
        self.applications_by_display_name: dict[str, dict] = {}
        self.service_principals_by_app_id: dict[str, dict] = {}
        self.owners_by_application_id: dict[str, list[dict]] = {}
        self.assignments_by_service_principal_id: dict[str, list[dict]] = {}
        self.site_permissions_by_site_id: dict[str, list[dict]] = {}

    def get(self, path: str) -> dict:
        if path.startswith("/users?"):
            return {
                "value": [
                    {
                        "id": "technical-owner",
                        "displayName": "funktion8",
                        "userPrincipalName": "funktion8@funktion8.de",
                        "assignedLicenses": [],
                    }
                ]
            }
        if path.startswith("/groups/") and "/owners/" in path:
            return {
                "value": [
                    {
                        "id": "licensed-human-owner",
                        "displayName": "Owner",
                        "userPrincipalName": "owner@example.test",
                        "assignedLicenses": [{"skuId": "m365"}],
                    }
                ]
            }
        if path.startswith("/groups?"):
            return {"value": [] if self.group is None else [self.group]}
        if path.startswith("/servicePrincipals?"):
            app_id = self._filter_value(path, "appId")
            if app_id == GRAPH_APP_ID:
                return {
                    "value": [
                        {
                            "id": "graph-service-principal",
                            "appId": GRAPH_APP_ID,
                            "displayName": "Microsoft Graph",
                            "appRoles": [
                                {
                                    "id": "role-team-create",
                                    "value": "Team.Create",
                                    "allowedMemberTypes": ["Application"],
                                },
                                {
                                    "id": "role-sites-manage-all",
                                    "value": "Sites.Manage.All",
                                    "allowedMemberTypes": ["Application"],
                                },
                                {
                                    "id": "role-sites-selected",
                                    "value": "Sites.Selected",
                                    "allowedMemberTypes": ["Application"],
                                },
                            ],
                        }
                    ]
                }
            service_principal = self.service_principals_by_app_id.get(app_id)
            return {"value": [] if service_principal is None else [service_principal]}
        if path.startswith("/applications?"):
            app = self.applications_by_display_name.get(self._filter_value(path, "displayName"))
            return {"value": [] if app is None else [app]}
        if path.startswith("/applications/") and path.endswith("/owners?$select=id,displayName"):
            app_id = path.split("/")[2]
            return {"value": self.owners_by_application_id.get(app_id, [])}
        if path.startswith("/servicePrincipals/") and path.endswith("/appRoleAssignments"):
            service_principal_id = path.split("/")[2]
            return {"value": self.assignments_by_service_principal_id.get(service_principal_id, [])}
        if path.startswith("/sites/") and "/lists?" in path:
            site_id = urllib.parse.unquote(path.removeprefix("/sites/").split("/lists?", 1)[0])
            workspace = self._workspace_by_site_id(site_id)
            return {
                "value": [
                    {
                        "id": details.get("id", display_name),
                        "displayName": display_name,
                        "webUrl": details.get("web_url", ""),
                    }
                    for display_name, details in workspace.get("lists", {}).items()
                    if isinstance(details, dict)
                ]
            }
        if path.startswith("/sites/") and "?$select=id,displayName,webUrl" in path:
            site_id = urllib.parse.unquote(path.removeprefix("/sites/").split("?", 1)[0])
            workspace = self._workspace_by_site_id(site_id)
            return {
                "id": site_id,
                "displayName": workspace["team_display_name"],
                "webUrl": workspace.get("site_url", ""),
            }
        if path.startswith("/sites/") and "/drives?" in path:
            site_id = urllib.parse.unquote(path.removeprefix("/sites/").split("/drives?", 1)[0])
            workspace = self._workspace_by_site_id(site_id)
            return {
                "value": [
                    {
                        "id": details.get("id", name),
                        "name": name,
                        "webUrl": details.get("web_url", ""),
                        "driveType": "documentLibrary",
                    }
                    for name, details in workspace.get("document_libraries", {}).items()
                    if isinstance(details, dict)
                ]
            }
        if path.startswith("/sites/") and path.endswith("/permissions"):
            site_id = self._site_id_from_path(path)
            return {"value": self.site_permissions_by_site_id.get(site_id, [])}
        raise AssertionError(f"unexpected GET {path}")

    def post(self, path: str, payload: dict) -> dict:
        self.posts.append((path, payload))
        if path == "/groups":
            self.group = {
                "id": "governance-group",
                "displayName": payload["displayName"],
                "mailNickname": payload["mailNickname"],
                "securityEnabled": payload["securityEnabled"],
                "mailEnabled": payload["mailEnabled"],
            }
            return self.group
        if path == "/applications":
            app = {
                "id": "app-" + payload["displayName"].lower().replace(" ", "-"),
                "appId": "client-" + payload["displayName"].lower().replace(" ", "-"),
                "displayName": payload["displayName"],
                "requiredResourceAccess": payload["requiredResourceAccess"],
            }
            self.applications_by_display_name[app["displayName"]] = app
            return app
        if path == "/servicePrincipals":
            service_principal = {
                "id": "sp-" + payload["appId"],
                "appId": payload["appId"],
                "displayName": payload["appId"],
            }
            self.service_principals_by_app_id[payload["appId"]] = service_principal
            return service_principal
        if path.startswith("/applications/") and path.endswith("/owners/$ref"):
            app_id = path.split("/")[2]
            self.owners_by_application_id.setdefault(app_id, []).append(
                {"id": "technical-owner", "displayName": "funktion8"}
            )
            return {}
        if path.startswith("/servicePrincipals/") and path.endswith("/appRoleAssignments"):
            service_principal_id = path.split("/")[2]
            assignment = {
                "principalId": payload["principalId"],
                "resourceId": payload["resourceId"],
                "appRoleId": payload["appRoleId"],
            }
            self.assignments_by_service_principal_id.setdefault(service_principal_id, []).append(assignment)
            return assignment
        if path.startswith("/sites/") and path.endswith("/permissions"):
            site_id = self._site_id_from_path(path)
            permission = {
                "id": f"permission-{len(self.site_permissions_by_site_id.get(site_id, [])) + 1}",
                **payload,
            }
            self.site_permissions_by_site_id.setdefault(site_id, []).append(permission)
            return permission
        raise AssertionError(f"unexpected POST {path}")

    def patch(self, path: str, payload: dict) -> dict:
        self.patches.append((path, payload))
        if path.startswith("/applications/"):
            app_id = path.split("/")[2]
            for app in self.applications_by_display_name.values():
                if app["id"] == app_id:
                    app.update(payload)
                    return app
        raise AssertionError(f"unexpected PATCH {path}")

    @staticmethod
    def _filter_value(path: str, field: str) -> str:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
        filter_text = query.get("$filter", [""])[0]
        prefix = f"{field} eq '"
        if prefix not in filter_text:
            return ""
        return filter_text.split(prefix, 1)[1].split("'", 1)[0]

    @staticmethod
    def _site_id_from_path(path: str) -> str:
        return urllib.parse.unquote(path.removeprefix("/sites/").removesuffix("/permissions"))

    def _workspace_by_site_id(self, site_id: str) -> dict:
        for workspace in self.provisioned_state.get("workspaces", []):
            if isinstance(workspace, dict) and workspace.get("site_id") == site_id:
                return workspace
        raise AssertionError(f"unknown site id {site_id}")


class TeamsSharePointGraphDataPlaneTests(unittest.TestCase):
    def test_contract_sets_graph_rest_only_decision(self) -> None:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["contract_id"], "m365.teams_sharepoint_graph_data_plane")
        self.assertEqual(payload["status"], "final_m365_mvp_data_plane")
        self.assertTrue(payload["target_decision"]["graph_rest_only"])
        self.assertTrue(payload["target_decision"]["mcp_allowed_only_when_backed_by_graph_rest"])
        self.assertFalse(payload["graph_policy"]["sdk_usage_allowed"])
        self.assertFalse(payload["graph_policy"]["legacy_sharepoint_api_allowed"])
        self.assertEqual(payload["target_decision"]["workspace_model"], "team_per_notary_team")
        self.assertIn("Sites.Selected", payload["permission_model"]["runtime_target_permissions"])

    def test_contract_captures_application_owned_privileged_change_path(self) -> None:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        permission_model = payload["permission_model"]

        self.assertTrue(permission_model["standard_users_must_not_hold_m365_admin_permissions"])
        self.assertTrue(permission_model["privileged_m365_changes_must_run_through_app_or_api"])
        self.assertTrue(permission_model["application_governance_group_required"])
        self.assertEqual(permission_model["application_governance_group_target"], "nac_platform_admins")
        self.assertFalse(permission_model["direct_application_owner_group_supported_by_graph"])
        self.assertTrue(permission_model["direct_application_owner_must_be_user_or_service_principal"])
        self.assertTrue(permission_model["technical_application_owner_user_allowed"])
        self.assertEqual(permission_model["technical_application_owner_user_target"], "funktion8@funktion8.de")
        self.assertTrue(permission_model["human_team_owner_still_required"])
        self.assertTrue(permission_model["technical_bootstrap_owner_user_allowed"])
        self.assertEqual(permission_model["technical_bootstrap_owner_user_target"], "funktion8@funktion8.de")
        self.assertTrue(permission_model["technical_bootstrap_owner_user_must_not_be_sole_owner"])
        self.assertTrue(permission_model["licensed_human_team_owner_required"])
        self.assertTrue(permission_model["technical_owner_must_not_hold_m365_admin_roles"])
        self.assertTrue(permission_model["technical_owner_use_requires_license_terms_review"])

        roadmap_ids = {item["id"] for item in payload["next_iteration_roadmap"]}
        self.assertIn("m365-application-owned-privileged-change-path", roadmap_ids)

    def test_schema_validates_and_contains_required_lists(self) -> None:
        schema = load_schema(DEFAULT_SCHEMA)

        self.assertEqual(validate_schema(schema), [])
        list_names = {item["display_name"] for item in schema["sharepoint"]["lists"]}
        self.assertGreaterEqual(
            list_names,
            {
                "Akten",
                "Beteiligte",
                "AufgabenFristen",
                "Vertretungsfreigaben",
                "AuditJournalLite",
                "DokumentRegister",
            },
        )

    def test_schema_rejects_reserved_sharepoint_column_names(self) -> None:
        schema = load_schema(DEFAULT_SCHEMA)
        schema["sharepoint"]["lists"][0]["columns"].append(
            {
                "name": "WorkflowVersion",
                "type": "text",
            }
        )

        self.assertIn(
            "list Akten column WorkflowVersion conflicts with a SharePoint system field",
            validate_schema(schema),
        )

    def test_plan_runs_without_credentials(self) -> None:
        schema = load_schema(DEFAULT_SCHEMA)
        plan = build_plan(schema)
        summary = summarize_plan(plan)

        self.assertEqual(summary["by_action"]["ensure_team"], 2)
        self.assertEqual(summary["by_action"]["resolve_group_site"], 2)
        self.assertEqual(summary["by_action"]["ensure_document_library"], 4)
        self.assertGreater(summary["by_action"]["ensure_column"], 80)

    def test_privileged_change_plan_runs_without_credentials(self) -> None:
        config = load_privileged_change_config(DEFAULT_PRIVILEGED_CHANGE_CONFIG)
        state = load_provisioned_state(DEFAULT_PROVISIONED_STATE)

        self.assertEqual(validate_privileged_change_config(config), [])
        plan = build_privileged_change_plan(config, state)
        summary = summarize_privileged_change_plan(plan)

        self.assertEqual(summary["by_action"]["resolve_technical_owner_user"], 1)
        self.assertEqual(summary["by_action"]["ensure_governance_group"], 1)
        self.assertEqual(summary["by_action"]["ensure_application"], 2)
        self.assertEqual(summary["by_action"]["assign_direct_application_owner"], 2)
        self.assertEqual(summary["by_action"]["verify_human_team_owner"], 2)
        self.assertEqual(summary["by_action"]["grant_runtime_sites_selected_site_permission"], 2)

    def test_application_owner_readiness_is_offline_and_redacted(self) -> None:
        config = load_privileged_change_config(DEFAULT_PRIVILEGED_CHANGE_CONFIG)
        applied_state = load_privileged_applied_state(APPLIED_STATE)

        readiness = build_application_owner_readiness(config, applied_state)
        serialized = json.dumps(readiness)
        checks = {check["id"]: check for check in readiness["checks"]}

        self.assertEqual(readiness["status"], "PASSED")
        self.assertFalse(readiness["summary"]["executes_graph_requests"])
        self.assertFalse(readiness["summary"]["executes_graph_writes"])
        self.assertFalse(readiness["summary"]["mandate_data_allowed"])
        self.assertTrue(readiness["summary"]["graph_rest_only"])
        self.assertFalse(readiness["summary"]["sdk_allowed"])
        self.assertFalse(readiness["summary"]["legacy_sharepoint_api_allowed"])
        self.assertFalse(readiness["summary"]["direct_application_owner_group_supported"])
        self.assertEqual(readiness["summary"]["direct_application_owner_kind"], "user_or_service_principal")
        self.assertEqual(readiness["summary"]["technical_owner_user"], "funktion8@funktion8.de")
        self.assertTrue(readiness["summary"]["technical_owner_must_not_hold_m365_admin_roles"])
        self.assertTrue(readiness["summary"]["technical_owner_license_terms_review_required"])
        self.assertEqual(readiness["summary"]["provisioning_app_count"], 1)
        self.assertEqual(readiness["summary"]["runtime_app_count"], 1)
        self.assertTrue(readiness["summary"]["runtime_sites_selected_required"])
        self.assertEqual(readiness["summary"]["runtime_site_permissions_recorded"], 2)
        self.assertFalse(readiness["summary"]["secret_material_stored"])
        self.assertEqual(checks["technical_owner_license_terms_review"]["status"], "REVIEW_REQUIRED")
        self.assertEqual(checks["secret_material_not_stored"]["status"], "PASSED")
        self.assertNotIn("870c862b-56f7-4c9b-b0d9-f1f7d32c835c", serialized)
        self.assertNotIn("6845f6c3-896c-4e44-a50f-2a5086a13fac", serialized)
        self.assertNotIn("funktion8.sharepoint.com,31324d31", serialized)

    def test_privileged_apply_is_idempotent_with_graph_rest_client_boundary(self) -> None:
        config = load_privileged_change_config(DEFAULT_PRIVILEGED_CHANGE_CONFIG)
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                },
                {
                    "id": "notary_team_02",
                    "team_display_name": "NaC-Notar-02",
                    "team_id": "team-02",
                    "site_id": "example.sharepoint.com,site-02,web-02",
                },
            ]
        }
        client = FakeGraphWriteClient(state)

        first = apply_privileged_change_path(client, config, state)
        second = apply_privileged_change_path(client, config, state)

        self.assertEqual(first["status"], "PASSED")
        self.assertEqual(second["status"], "PASSED")
        self.assertEqual(second["governanceGroup"]["status"], "existing")
        self.assertEqual(len(second["sitePermissions"]), 2)
        self.assertTrue(all(item["status"] == "existing" for item in second["sitePermissions"]))
        for app in second["applications"].values():
            self.assertEqual(app["applicationStatus"], "existing")
            self.assertEqual(app["servicePrincipalStatus"], "existing")
            self.assertEqual(app["technicalOwnerStatus"], "existing")
            self.assertTrue(all(item["status"] == "existing" for item in app["appRoleAssignments"]))
        site_permission_posts = [
            path
            for path, _payload in client.posts
            if path.startswith("/sites/") and path.endswith("/permissions")
        ]
        assignment_posts = [
            path
            for path, _payload in client.posts
            if path.startswith("/servicePrincipals/") and path.endswith("/appRoleAssignments")
        ]
        self.assertEqual(len(site_permission_posts), 2)
        self.assertEqual(len(assignment_posts), 3)

    def test_runtime_site_smoke_reads_expected_lists_with_runtime_boundary(self) -> None:
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                    "site_url": "https://example.sharepoint.com/sites/NaC-Notar-01",
                    "lists": {
                        "Akten": {"id": "list-akten", "web_url": "https://example.test/akten"},
                        "Beteiligte": {"id": "list-beteiligte", "web_url": "https://example.test/beteiligte"},
                    },
                }
            ]
        }
        client = FakeGraphWriteClient(state)

        result = run_runtime_site_smoke(client, state)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["sites_read"], 1)
        self.assertEqual(result["workspaces"][0]["expectedListCount"], 2)
        self.assertEqual(result["workspaces"][0]["observedListCount"], 2)

    def test_runtime_site_smoke_redacted_artifact_excludes_raw_site_metadata(self) -> None:
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                    "site_url": "https://example.sharepoint.com/sites/NaC-Notar-01",
                    "lists": {
                        "Akten": {"id": "list-akten", "web_url": "https://example.test/akten"},
                    },
                }
            ]
        }
        client = FakeGraphWriteClient(state)

        result = run_runtime_site_smoke(client, state)
        artifact = redact_runtime_site_smoke_result(result, timestamp="2026-07-07T04:30:00Z")
        serialized = json.dumps(artifact)

        self.assertEqual(artifact["status"], "PASSED")
        self.assertTrue(artifact["summary"]["graph_rest_only"])
        self.assertFalse(artifact["summary"]["raw_site_id_stored"])
        self.assertFalse(artifact["summary"]["raw_site_url_stored"])
        self.assertEqual(artifact["summary"]["list_items_read"], 0)
        self.assertNotIn("example.sharepoint.com,site-01,web-01", serialized)
        self.assertNotIn("https://example.sharepoint.com/sites/NaC-Notar-01", serialized)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "runtime-smoke.redacted.json"
            written = write_runtime_site_smoke_artifact(result, output)
            self.assertTrue(output.exists())
            self.assertEqual(written["status"], "PASSED")

    def test_runtime_site_smoke_uses_schema_expectations_to_detect_list_drift(self) -> None:
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                    "site_url": "https://example.sharepoint.com/sites/NaC-Notar-01",
                    "lists": {
                        "Akten": {"id": "list-akten", "web_url": "https://example.test/akten"},
                    },
                }
            ]
        }
        client = FakeGraphWriteClient(state)

        with self.assertRaisesRegex(RuntimeError, "missing lists: DokumentRegister"):
            run_runtime_site_smoke(client, state, _schema_expectations(["Akten", "DokumentRegister"]))

    def test_runtime_metadata_reads_lists_and_libraries_without_items(self) -> None:
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                    "site_url": "https://example.sharepoint.com/sites/NaC-Notar-01",
                    "lists": {
                        "Akten": {"id": "list-akten", "web_url": "https://example.test/akten"},
                        "Beteiligte": {"id": "list-beteiligte", "web_url": "https://example.test/beteiligte"},
                    },
                    "document_libraries": {
                        "AktenDokumente": {"id": "drive-akten", "web_url": "https://example.test/akten-docs"},
                        "Vorlagen": {"id": "drive-vorlagen", "web_url": "https://example.test/vorlagen"},
                    },
                }
            ]
        }
        client = FakeGraphWriteClient(state)

        result = build_runtime_metadata_snapshot(client, state)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["expected_lists"], 2)
        self.assertEqual(result["summary"]["expected_document_libraries"], 2)
        self.assertEqual(result["summary"]["list_items_read"], 0)
        self.assertEqual(
            [item["displayName"] for item in result["workspaces"][0]["lists"]],
            ["Akten", "Beteiligte"],
        )
        self.assertEqual(
            [item["name"] for item in result["workspaces"][0]["documentLibraries"]],
            ["AktenDokumente", "Vorlagen"],
        )

    def test_runtime_metadata_redacted_artifact_excludes_raw_list_and_drive_metadata(self) -> None:
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                    "site_url": "https://example.sharepoint.com/sites/NaC-Notar-01",
                    "lists": {
                        "Akten": {"id": "list-akten", "web_url": "https://example.test/akten"},
                    },
                    "document_libraries": {
                        "AktenDokumente": {"id": "drive-akten", "web_url": "https://example.test/akten-docs"},
                    },
                }
            ]
        }
        client = FakeGraphWriteClient(state)

        result = build_runtime_metadata_snapshot(client, state)
        artifact = redact_runtime_metadata_snapshot(result, timestamp="2026-07-07T04:30:00Z")
        serialized = json.dumps(artifact)

        self.assertEqual(artifact["status"], "PASSED")
        self.assertTrue(artifact["summary"]["graph_rest_only"])
        self.assertFalse(artifact["summary"]["raw_list_id_stored"])
        self.assertFalse(artifact["summary"]["raw_drive_id_stored"])
        self.assertEqual(artifact["summary"]["list_items_read"], 0)
        self.assertNotIn("list-akten", serialized)
        self.assertNotIn("drive-akten", serialized)
        self.assertNotIn("https://example.test/akten", serialized)
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "runtime-metadata.redacted.json"
            written = write_runtime_metadata_artifact(result, output)
            self.assertTrue(output.exists())
            self.assertEqual(written["status"], "PASSED")

    def test_runtime_metadata_uses_schema_expectations_to_detect_library_drift(self) -> None:
        state = {
            "workspaces": [
                {
                    "id": "notary_team_01",
                    "team_display_name": "NaC-Notar-01",
                    "team_id": "team-01",
                    "site_id": "example.sharepoint.com,site-01,web-01",
                    "site_url": "https://example.sharepoint.com/sites/NaC-Notar-01",
                    "lists": {
                        "Akten": {"id": "list-akten", "web_url": "https://example.test/akten"},
                    },
                    "document_libraries": {
                        "AktenDokumente": {"id": "drive-akten", "web_url": "https://example.test/akten-docs"},
                    },
                }
            ]
        }
        client = FakeGraphWriteClient(state)

        with self.assertRaisesRegex(RuntimeError, "missing_libraries=\\['Vorlagen'\\]"):
            build_runtime_metadata_snapshot(
                client,
                state,
                _schema_expectations(["Akten"], ["AktenDokumente", "Vorlagen"]),
            )

    def test_applied_privileged_state_captures_runtime_site_grants(self) -> None:
        state = json.loads(APPLIED_STATE.read_text(encoding="utf-8"))
        runtime_app = state["applications"]["m365_runtime_app"]

        self.assertEqual(state["state_version"], "nac.m365-privileged-change-path.applied/v0.1")
        self.assertEqual(runtime_app["application_permissions"], ["Sites.Selected"])
        self.assertTrue(runtime_app["runtime_allowed"])
        self.assertEqual(len(state["runtime_site_permissions"]), 2)
        for permission in state["runtime_site_permissions"]:
            self.assertEqual(permission["application_client_id"], runtime_app["client_id"])
            self.assertEqual(permission["role"], "write")
        for owner_check in state["team_owner_checks"]:
            self.assertGreaterEqual(owner_check["licensed_human_owner_count"], 1)

    def test_runtime_smoke_state_captures_site_readiness(self) -> None:
        privileged = json.loads(APPLIED_STATE.read_text(encoding="utf-8"))
        state = json.loads(RUNTIME_SMOKE_STATE.read_text(encoding="utf-8"))
        runtime_app = state["runtime_application"]

        self.assertEqual(state["state_version"], "nac.m365-runtime-smoke/v0.1")
        self.assertEqual(state["smoke_result"]["status"], "PASSED")
        self.assertEqual(state["smoke_result"]["sites_read"], 2)
        self.assertEqual(state["smoke_result"]["missing_lists"], 0)
        self.assertEqual(runtime_app["client_id"], privileged["applications"]["m365_runtime_app"]["client_id"])
        self.assertEqual(runtime_app["application_permissions"], ["Sites.Selected"])
        self.assertEqual(runtime_app["authentication_mode"], "client_credentials_with_certificate")
        self.assertNotIn("private_key", json.dumps(state).lower())
        self.assertNotIn("access_token", json.dumps(state).lower())
        for workspace in state["workspaces"]:
            self.assertGreaterEqual(workspace["observed_list_count"], workspace["expected_list_count"])
            self.assertEqual(workspace["missing_lists"], [])

    def test_runtime_certificate_readiness_is_offline_and_redacted(self) -> None:
        smoke_state = json.loads(RUNTIME_SMOKE_STATE.read_text(encoding="utf-8"))
        metadata_state = json.loads(RUNTIME_METADATA_STATE.read_text(encoding="utf-8"))

        readiness = build_runtime_certificate_readiness(
            smoke_state,
            metadata_state,
            now_utc="2026-07-07T00:00:00Z",
        )
        serialized = json.dumps(readiness)
        checks = {check["id"]: check for check in readiness["checks"]}

        self.assertEqual(readiness["status"], "PASSED")
        self.assertEqual(readiness["summary"]["preferred_authentication_mode"], "client_credentials_with_certificate")
        self.assertTrue(readiness["summary"]["certificate_thumbprint_present"])
        self.assertFalse(readiness["summary"]["certificate_thumbprint_emitted"])
        self.assertGreaterEqual(readiness["summary"]["certificate_days_until_expiry"], 360)
        self.assertFalse(readiness["summary"]["certificate_rotation_review_required"])
        self.assertTrue(readiness["summary"]["runtime_metadata_thumbprint_matches_smoke"])
        self.assertFalse(readiness["summary"]["secret_env_values_read"])
        self.assertFalse(readiness["summary"]["credential_files_read"])
        self.assertFalse(readiness["summary"]["executes_graph_requests"])
        self.assertFalse(readiness["summary"]["executes_graph_writes"])
        self.assertFalse(readiness["summary"]["mandate_data_allowed"])
        self.assertFalse(readiness["summary"]["private_key_allowed_in_repo"])
        self.assertFalse(readiness["summary"]["certificate_body_allowed_in_repo"])
        self.assertTrue(readiness["summary"]["certificate_generation_owner_gate_required"])
        self.assertTrue(readiness["summary"]["app_credential_upload_owner_gate_required"])
        self.assertIn("M365_RUNTIME_CLIENT_CERTIFICATE_PATH", readiness["summary"]["required_environment_variables"])
        self.assertEqual(checks["certificate_rotation_window"]["status"], "PASSED")
        self.assertEqual(checks["secret_material_not_stored"]["status"], "PASSED")
        self.assertNotIn("870c862b-56f7-4c9b-b0d9-f1f7d32c835c", serialized)
        self.assertNotIn("0d98b5a5-479b-452d-9b43-c3fbbcab9d24", serialized)
        self.assertNotIn("563B190496ABCBD1B89AC0CFC955A510CF30C3D0", serialized)
        self.assertNotIn("funktion8.sharepoint.com", serialized)

    def test_column_mapping_uses_graph_column_payloads(self) -> None:
        payload = column_create_payload(
            {
                "name": "Status",
                "type": "choice",
                "required": True,
                "choices": ["Offen", "Erledigt"],
            }
        )

        self.assertEqual(payload["displayName"], "Status")
        self.assertTrue(payload["required"])
        self.assertEqual(payload["choice"]["choices"], ["Offen", "Erledigt"])

    def test_unique_columns_are_indexed_for_graph(self) -> None:
        payload = column_create_payload(
            {
                "name": "NacCaseId",
                "type": "text",
                "enforce_unique_values": True,
            }
        )

        self.assertTrue(payload["enforceUniqueValues"])
        self.assertTrue(payload["indexed"])

    def test_validator_accepts_repository_state(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_teams_sharepoint_graph_data_plane.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)

    def test_cli_plan_runs_without_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "plan", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertGreater(payload["summary"]["operation_count"], 100)

    def test_cli_privileged_plan_runs_without_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "privileged-plan", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["by_action"]["ensure_application"], 2)
        self.assertEqual(
            payload["summary"]["by_action"]["grant_runtime_sites_selected_site_permission"],
            2,
        )

    def test_cli_application_owner_readiness_runs_without_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "application-owner-readiness", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertEqual(payload["summary"]["governance_group"], "nac_platform_admins")
        self.assertEqual(payload["summary"]["technical_owner_user"], "funktion8@funktion8.de")

    def test_cli_runtime_certificate_readiness_runs_without_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "runtime-certificate-readiness", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["credential_files_read"])
        self.assertTrue(payload["summary"]["certificate_generation_owner_gate_required"])

    def test_cli_privileged_apply_requires_owner_approval_before_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "privileged-apply", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("privileged-apply requires --owner-approved", payload["errors"])

    def test_cli_runtime_smoke_requires_owner_approval_before_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "runtime-smoke", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("runtime-smoke requires --owner-approved", payload["errors"])

    def test_cli_runtime_metadata_requires_owner_approval_before_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "runtime-metadata", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("runtime-metadata requires --owner-approved", payload["errors"])

    def test_nac_cli_exposes_m365_teams_sharepoint_privileged_plan(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "privileged-plan",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["by_action"]["ensure_application"], 2)

    def test_nac_cli_exposes_application_owner_readiness(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "application-owner-readiness",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertTrue(payload["summary"]["owner_gate_required_for_live_apply"])

    def test_nac_cli_exposes_runtime_certificate_readiness(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "runtime-certificate-readiness",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["secret_env_values_read"])

    def test_nac_cli_exposes_m365_teams_sharepoint_runtime_smoke_gate(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "runtime-smoke",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("runtime-smoke requires --owner-approved", payload["errors"])

    def test_nac_cli_exposes_m365_teams_sharepoint_runtime_metadata_gate(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "runtime-metadata",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("runtime-metadata requires --owner-approved", payload["errors"])

def _schema_expectations(
    lists: list[str],
    document_libraries: list[str] | None = None,
) -> dict:
    return {
        "sharepoint": {
            "lists": [{"display_name": name} for name in lists],
            "document_libraries": [
                {"display_name": name}
                for name in (document_libraries or [])
            ],
        },
    }


if __name__ == "__main__":
    unittest.main()
