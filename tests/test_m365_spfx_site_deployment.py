from __future__ import annotations

import json
import sys
import tempfile
import unittest
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.spfx_site_deployment import (  # noqa: E402
    PACKAGE_CONFIG_RELATIVE_PATH,
    PACKAGE_NAME,
    PACKAGE_RELATIVE_PATH,
    PAGE_LAYOUT,
    PAGE_NAME,
    SITE_URL,
    SOLUTION_PRODUCT_ID,
    SOLUTION_TITLE,
    TEAM_ID,
    TEAMS_INSTALLED_APPS_URL,
    WEB_PART_ID,
    WORKSPACE_ID,
    DeploymentPlanError,
    build_spfx_site_deployment_plan,
    run_spfx_site_deployment,
)


APP_CATALOG_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TEAMS_CATALOG_ID = "11111111-2222-3333-4444-555555555555"
TEAMS_EXTERNAL_ID = "66666666-7777-8888-9999-aaaaaaaaaaaa"
RAW_SECRET = "raw-session-token-do-not-emit"


@dataclass(frozen=True)
class FakeResult:
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


class FakeRunner:
    def __init__(self, handler: Callable[[tuple[str, ...]], FakeResult]) -> None:
        self.handler = handler
        self.commands: list[tuple[str, ...]] = []

    def run(self, argv: Sequence[str]) -> FakeResult:
        command = tuple(argv)
        self.commands.append(command)
        return self.handler(command)


class M365SpfxSiteDeploymentTests(unittest.TestCase):
    def test_plan_is_hash_bound_and_fixed_to_the_approved_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)

            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            payload = plan.to_redacted_dict()

            self.assertEqual(plan.workspace_id, WORKSPACE_ID)
            self.assertEqual(plan.site_url, SITE_URL)
            self.assertEqual(plan.team_id, TEAM_ID)
            self.assertEqual(plan.page_name, PAGE_NAME)
            self.assertEqual(plan.page_layout, PAGE_LAYOUT)
            self.assertEqual(plan.web_part_id, WEB_PART_ID)
            self.assertEqual(len(plan.package_sha256), 64)
            self.assertEqual(payload["package_sha256"], plan.package_sha256)
            self.assertEqual(payload["app_catalog_scope"], "tenant")
            self.assertFalse(payload["tenant_wide_deployment"])
            self.assertFalse(payload["destructive_rollback"])
            self.assertFalse(payload["raw_session_data"])
            self.assertIn("install_or_reuse_teams_app_on_target_team", payload["planned_operations"])

            rebound = build_spfx_site_deployment_plan(
                repo_root=root,
                expected_package_sha256=plan.package_sha256.upper(),
            )
            self.assertEqual(rebound.package_sha256, plan.package_sha256)
            with self.assertRaisesRegex(DeploymentPlanError, "SHA256"):
                build_spfx_site_deployment_plan(repo_root=root, expected_package_sha256="0" * 64)

    def test_plan_rejects_other_workspaces_sites_teams_and_tenant_wide_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)

            with self.assertRaisesRegex(DeploymentPlanError, "workspace"):
                build_spfx_site_deployment_plan(repo_root=root, workspace_id="notary_team_02")
            with self.assertRaisesRegex(DeploymentPlanError, "site"):
                build_spfx_site_deployment_plan(
                    repo_root=root,
                    site_url="https://funktion8.sharepoint.com/sites/Other",
                )
            with self.assertRaisesRegex(DeploymentPlanError, "team"):
                build_spfx_site_deployment_plan(
                    repo_root=root,
                    include_teams=True,
                    team_id="99999999-9999-9999-9999-999999999999",
                )

            self._write_package_fixture(root, skip_feature_deployment=True)
            with self.assertRaisesRegex(DeploymentPlanError, "skipFeatureDeployment"):
                build_spfx_site_deployment_plan(repo_root=root)

    def test_plan_rejects_nonempty_or_malformed_api_permission_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(
                root,
                web_api_permission_requests=[
                    {"resource": "Microsoft Graph", "scope": "Sites.Read.All"}
                ],
            )
            with self.assertRaisesRegex(DeploymentPlanError, "permissions"):
                build_spfx_site_deployment_plan(repo_root=root)

            self._write_package_fixture(root, web_api_permission_requests={"scope": "Sites.Read.All"})
            with self.assertRaisesRegex(DeploymentPlanError, "permissions"):
                build_spfx_site_deployment_plan(repo_root=root)

    def test_plan_rejects_permission_request_embedded_in_sppkg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root, embedded_permission=True)
            with self.assertRaisesRegex(DeploymentPlanError, "permission request"):
                build_spfx_site_deployment_plan(repo_root=root)

    def test_create_run_orders_commands_and_scopes_every_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)
            runner = FakeRunner(self._create_handler)

            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(
                [self._command_head(command) for command in runner.commands],
                [
                    ("spo", "app", "list"),
                    ("spo", "app", "add"),
                    ("spo", "app", "get"),
                    ("spo", "app", "deploy"),
                    ("spo", "app", "instance", "list"),
                    ("spo", "app", "install"),
                    ("spo", "page", "list"),
                    ("spo", "page", "add"),
                    ("spo", "page", "get"),
                    ("spo", "page", "clientsidewebpart", "add"),
                    ("spo", "page", "set"),
                ],
            )
            self.assertEqual(
                evidence["classifications"]["install_or_reuse_app_on_target_site"],
                "create",
            )
            self.assertEqual(evidence["classifications"]["create_or_update_modern_page"], "create")
            self.assertEqual(evidence["classifications"]["add_or_reuse_web_part"], "create")
            self._assert_commands_are_strictly_scoped(runner.commands, include_teams=False)

            app_add = runner.commands[1]
            self.assertNotIn("--overwrite", app_add)
            deploy = runner.commands[3]
            self.assertNotIn("--skipFeatureDeployment", deploy)
            page_add = runner.commands[7]
            self.assertEqual(self._value(page_add, "--layoutType"), "SingleWebPartAppPage")
            web_part_add = runner.commands[9]
            self.assertEqual(self._value(web_part_add, "--webPartId"), WEB_PART_ID)

    def test_existing_resources_are_updated_or_reused_without_duplicate_web_part(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            runner = FakeRunner(self._existing_handler)

            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(evidence["classifications"]["add_or_overwrite_tenant_app"], "update")
            self.assertEqual(evidence["classifications"]["install_or_reuse_app_on_target_site"], "update")
            self.assertEqual(evidence["classifications"]["create_or_update_modern_page"], "update")
            self.assertEqual(evidence["classifications"]["add_or_reuse_web_part"], "reuse")
            self.assertEqual(
                evidence["classifications"]["publish_or_update_teams_catalog_app"],
                "update",
            )
            self.assertEqual(
                evidence["classifications"]["install_or_reuse_teams_app_on_target_team"],
                "reuse",
            )
            heads = [self._command_head(command) for command in runner.commands]
            self.assertIn(("spo", "app", "upgrade"), heads)
            self.assertIn(("teams", "app", "update"), heads)
            self.assertIn(("request",), heads)
            app_add = next(
                command
                for command in runner.commands
                if self._command_head(command) == ("spo", "app", "add")
            )
            self.assertIn("--overwrite", app_add)
            self.assertNotIn(("spo", "app", "install"), heads)
            self.assertNotIn(("spo", "page", "add"), heads)
            self.assertNotIn(("spo", "page", "clientsidewebpart", "add"), heads)
            self._assert_commands_are_strictly_scoped(runner.commands, include_teams=True)

            teams_install = next(
                command
                for command in runner.commands
                if self._command_head(command) == ("teams", "app", "install")
            )
            self.assertEqual(self._value(teams_install, "--teamId"), TEAM_ID)

    def test_package_mutation_is_blocked_before_the_first_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)
            with plan.package_path.open("ab") as package:
                package.write(b"changed-after-plan")
            runner = FakeRunner(self._create_handler)

            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(evidence["steps"][0]["name"], "verify_package_sha256")
            self.assertEqual(
                evidence["steps"][0]["error"]["category"],
                "package_hash_mismatch",
            )
            self.assertEqual(runner.commands, [])

    def test_partial_failure_is_redacted_and_does_not_attempt_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)

            def fail_deploy(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == ("spo", "app", "deploy"):
                    return FakeResult(
                        returncode=17,
                        stdout=f'{{"access_token":"{RAW_SECRET}"}}',
                        stderr=f"tenant session failed: {RAW_SECRET}",
                    )
                return self._create_handler(command)

            runner = FakeRunner(fail_deploy)
            evidence = run_spfx_site_deployment(plan, runner)
            serialized = json.dumps(evidence)

            self.assertEqual(evidence["status"], "FAILED")
            self.assertNotIn(RAW_SECRET, serialized)
            self.assertNotIn("access_token", serialized)
            self.assertFalse(evidence["raw_session_data_included"])
            self.assertEqual(evidence["steps"][-1]["error"]["exit_code"], 17)
            self.assertEqual(
                self._command_head(runner.commands[-1]),
                ("spo", "app", "deploy"),
            )
            all_tokens = {token.lower() for command in runner.commands for token in command}
            self.assertTrue(
                {"remove", "retract", "uninstall", "delete", "rollback"}.isdisjoint(all_tokens)
            )

    def test_catalog_response_with_tenant_wide_flag_stops_before_deploy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)

            def unsafe_catalog(command: tuple[str, ...]) -> FakeResult:
                result = self._create_handler(command)
                if self._command_head(command) == ("spo", "app", "get"):
                    payload = json.loads(result.stdout)
                    payload["IsPackageDefaultSkipFeatureDeployment"] = True
                    return FakeResult(stdout=json.dumps(payload))
                return result

            runner = FakeRunner(unsafe_catalog)
            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "unsafe_control_plane_response",
            )
            self.assertNotIn(("spo", "app", "deploy"), [self._command_head(c) for c in runner.commands])

    def test_catalog_must_explicitly_prove_empty_aad_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)

            for aad_permissions, include_field in (([{"scope": "Sites.Read.All"}], True), (None, False)):
                def unsafe_catalog(command: tuple[str, ...]) -> FakeResult:
                    result = self._create_handler(command)
                    if self._command_head(command) == ("spo", "app", "get"):
                        payload = json.loads(result.stdout)
                        if include_field:
                            payload["AadPermissions"] = aad_permissions
                        else:
                            payload.pop("AadPermissions", None)
                        return FakeResult(stdout=json.dumps(payload))
                    return result

                runner = FakeRunner(unsafe_catalog)
                evidence = run_spfx_site_deployment(plan, runner)
                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertNotIn(
                    ("spo", "app", "deploy"),
                    [self._command_head(command) for command in runner.commands],
                )


    def test_catalog_name_or_file_collision_with_wrong_identity_fails_before_write(self) -> None:
        collisions = (
            {"Title": SOLUTION_TITLE, "ProductId": "ffffffff-ffff-ffff-ffff-ffffffffffff"},
            {"FileName": PACKAGE_NAME},
            {"Name": PACKAGE_NAME, "ProductId": ""},
        )
        for collision in collisions:
            with self.subTest(collision=collision), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root)

                def collision_handler(command: tuple[str, ...]) -> FakeResult:
                    if self._command_head(command) == ("spo", "app", "list"):
                        return FakeResult(stdout=json.dumps([collision]))
                    return self._create_handler(command)

                runner = FakeRunner(collision_handler)
                evidence = run_spfx_site_deployment(plan, runner)

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertEqual(
                    [self._command_head(command) for command in runner.commands],
                    [("spo", "app", "list")],
                )

    def test_exact_product_id_is_the_only_overwrite_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)

            def exact_product_handler(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == ("spo", "app", "list"):
                    return FakeResult(
                        stdout=json.dumps(
                            [
                                {
                                    "ProductId": SOLUTION_PRODUCT_ID.upper(),
                                    "Title": "Unrelated title",
                                    "FileName": "unrelated.sppkg",
                                }
                            ]
                        )
                    )
                return self._existing_handler(command)

            runner = FakeRunner(exact_product_handler)
            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "PASSED")
            app_add = next(
                command
                for command in runner.commands
                if self._command_head(command) == ("spo", "app", "add")
            )
            self.assertIn("--overwrite", app_add)

    def test_duplicate_exact_product_ids_fail_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)

            def duplicate_handler(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == ("spo", "app", "list"):
                    return FakeResult(
                        stdout=json.dumps(
                            [
                                {"ProductId": SOLUTION_PRODUCT_ID, "ID": APP_CATALOG_ID},
                                {
                                    "ProductId": SOLUTION_PRODUCT_ID.upper(),
                                    "ID": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                                },
                            ]
                        )
                    )
                return self._create_handler(command)

            runner = FakeRunner(duplicate_handler)
            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                [self._command_head(command) for command in runner.commands],
                [("spo", "app", "list")],
            )

    def test_teams_download_is_replaceable_and_manifest_id_drives_catalog_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            plan.teams_package_path.write_bytes(b"stale-download")
            runner = FakeRunner(self._existing_handler)

            first = run_spfx_site_deployment(plan, runner)
            second = run_spfx_site_deployment(plan, runner)

            self.assertEqual(first["status"], "PASSED")
            self.assertEqual(second["status"], "PASSED")
            updates = [
                command
                for command in runner.commands
                if self._command_head(command) == ("teams", "app", "update")
            ]
            self.assertEqual(len(updates), 2)
            self.assertTrue(all(self._value(command, "--id") == TEAMS_CATALOG_ID for command in updates))

    def test_generic_teams_conflict_is_not_accepted_as_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def generic_conflict(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == ("teams", "app", "install"):
                    return FakeResult(returncode=1, stderr="Conflict")
                return self._existing_handler(command)

            runner = FakeRunner(generic_conflict)
            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "control_plane_command_failed",
            )
            self.assertEqual(
                self._command_head(runner.commands[-1]),
                ("teams", "app", "install"),
            )
            self.assertNotIn(("request",), [self._command_head(c) for c in runner.commands])

    def test_teams_install_readback_requires_exact_catalog_and_manifest_identity(self) -> None:
        unsafe_payloads = (
            {"value": []},
            self._installed_teams_apps_payload(
                catalog_id="ffffffff-ffff-ffff-ffff-ffffffffffff"
            ),
            self._installed_teams_apps_payload(
                external_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
            ),
            {
                "value": [
                    *self._installed_teams_apps_payload()["value"],
                    *self._installed_teams_apps_payload()["value"],
                ]
            },
        )
        for payload in unsafe_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

                def unsafe_readback(command: tuple[str, ...]) -> FakeResult:
                    if self._command_head(command) == ("request",):
                        return FakeResult(stdout=json.dumps(payload))
                    return self._existing_handler(command)

                runner = FakeRunner(unsafe_readback)
                evidence = run_spfx_site_deployment(plan, runner)

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertEqual(
                    self._command_head(runner.commands[-1]),
                    ("request",),
                )

    @staticmethod
    def _write_package_fixture(
        root: Path,
        *,
        skip_feature_deployment: bool = False,
        web_api_permission_requests: object = None,
        embedded_permission: bool = False,
    ) -> None:
        config_path = root / PACKAGE_CONFIG_RELATIVE_PATH
        package_path = root / PACKAGE_RELATIVE_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        package_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    "solution": {
                        "name": SOLUTION_TITLE,
                        "id": SOLUTION_PRODUCT_ID,
                        "skipFeatureDeployment": skip_feature_deployment,
                        "webApiPermissionRequests": (
                            [] if web_api_permission_requests is None else web_api_permission_requests
                        ),
                    },
                    "paths": {"zippedPackage": "solution/nac-bpmn-viewer.sppkg"},
                }
            ),
            encoding="utf-8",
        )
        permission_xml = (
            '<WebApiPermissionRequests>'
            '<WebApiPermissionRequest Resource="Microsoft Graph" Scope="Sites.Read.All" />'
            '</WebApiPermissionRequests>'
            if embedded_permission
            else ""
        )
        manifest = (
            f'<App Name="{SOLUTION_TITLE}" ProductID="{SOLUTION_PRODUCT_ID}" '
            f'IsClientSideSolution="true"><Properties />{permission_xml}</App>'
        )
        descriptor = (
            "ea9917ea-2860-45fb-89bd-121120178be3/"
            f"WebPart_{WEB_PART_ID}.xml"
        )
        with zipfile.ZipFile(package_path, "w") as package:
            package.writestr("AppManifest.xml", manifest)
            package.writestr(descriptor, "<Elements />")

    @staticmethod
    def _safe_app_record() -> dict[str, object]:
        return {
            "ID": APP_CATALOG_ID,
            "ProductId": SOLUTION_PRODUCT_ID,
            "IsValidAppPackage": True,
            "IsPackageDefaultSkipFeatureDeployment": False,
            "SkipDeploymentFeature": False,
            "ContainsTenantWideExtension": False,
            "AadPermissions": [],
        }

    def _create_handler(self, command: tuple[str, ...]) -> FakeResult:
        head = self._command_head(command)
        if head == ("spo", "app", "list"):
            return FakeResult(stdout="[]")
        if head == ("spo", "app", "get"):
            return FakeResult(stdout=json.dumps(self._safe_app_record()))
        if head == ("spo", "app", "instance", "list"):
            return FakeResult(stdout="[]")
        if head == ("spo", "page", "list"):
            return FakeResult(stdout="[]")
        if head == ("spo", "page", "get"):
            return FakeResult(stdout='{"controls":[]}')
        if head == ("spo", "app", "teamspackage", "download"):
            self._write_downloaded_teams_package(command)
            return FakeResult()
        if head == ("teams", "app", "list"):
            return FakeResult(stdout="[]")
        if head == ("teams", "app", "publish"):
            return FakeResult(stdout=json.dumps({"id": TEAMS_CATALOG_ID, "externalId": WEB_PART_ID}))
        if head == ("request",):
            return FakeResult(stdout=json.dumps(self._installed_teams_apps_payload()))
        return FakeResult()

    def _existing_handler(self, command: tuple[str, ...]) -> FakeResult:
        head = self._command_head(command)
        if head == ("spo", "app", "list"):
            return FakeResult(
                stdout=json.dumps([{"ProductId": SOLUTION_PRODUCT_ID, "Title": SOLUTION_TITLE}])
            )
        if head == ("spo", "app", "get"):
            return FakeResult(stdout=json.dumps(self._safe_app_record()))
        if head == ("spo", "app", "instance", "list"):
            return FakeResult(stdout=json.dumps([{"ProductId": SOLUTION_PRODUCT_ID}]))
        if head == ("spo", "page", "list"):
            return FakeResult(stdout=json.dumps([{"Name": PAGE_NAME}]))
        if head == ("spo", "page", "get"):
            return FakeResult(stdout=json.dumps({"controls": [{"webPartId": WEB_PART_ID}]}))
        if head == ("spo", "app", "teamspackage", "download"):
            self._write_downloaded_teams_package(command)
            return FakeResult()
        if head == ("teams", "app", "list"):
            return FakeResult(
                stdout=json.dumps(
                    [
                        {
                            "id": TEAMS_CATALOG_ID,
                            "externalId": TEAMS_EXTERNAL_ID,
                            "distributionMethod": "organization",
                        }
                    ]
                )
            )
        if head == ("teams", "app", "install"):
            return FakeResult(returncode=1, stderr="App is already installed in this team")
        if head == ("request",):
            return FakeResult(stdout=json.dumps(self._installed_teams_apps_payload()))
        return FakeResult()

    @staticmethod
    def _installed_teams_apps_payload(
        *,
        catalog_id: str = TEAMS_CATALOG_ID,
        external_id: str = TEAMS_EXTERNAL_ID,
    ) -> dict[str, object]:
        return {
            "value": [
                {
                    "id": "installed-app-instance",
                    "teamsApp": {
                        "id": catalog_id,
                        "externalId": external_id,
                    },
                }
            ]
        }

    def _write_downloaded_teams_package(self, command: Sequence[str]) -> None:
        path = Path(self._value(command, "--fileName"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as package:
            package.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "manifestVersion": "1.17",
                        "version": "0.1.0",
                        "id": TEAMS_EXTERNAL_ID,
                    }
                ),
            )

    def _assert_commands_are_strictly_scoped(
        self,
        commands: Sequence[tuple[str, ...]],
        *,
        include_teams: bool,
    ) -> None:
        serialized = " ".join(token for command in commands for token in command).lower()
        self.assertNotIn("skipfeaturedeployment", serialized)
        self.assertNotIn("tenant-wide", serialized)
        self.assertNotIn("notary_team_02", serialized)
        for command in commands:
            self.assertEqual(command[0], "m365")
            for option in ("--webUrl", "--siteUrl"):
                if option in command:
                    self.assertEqual(self._value(command, option), SITE_URL)
            if "--appCatalogScope" in command:
                self.assertEqual(self._value(command, "--appCatalogScope"), "tenant")
            if "--teamId" in command:
                self.assertTrue(include_teams)
                self.assertEqual(self._value(command, "--teamId"), TEAM_ID)
            if self._command_head(command) == ("request",):
                self.assertTrue(include_teams)
                self.assertEqual(self._value(command, "--url"), TEAMS_INSTALLED_APPS_URL)
                self.assertEqual(self._value(command, "--method"), "get")

    @staticmethod
    def _command_head(command: Sequence[str]) -> tuple[str, ...]:
        head: list[str] = []
        for token in command[1:]:
            if token.startswith("--"):
                break
            head.append(token)
        return tuple(head)

    @staticmethod
    def _value(command: Sequence[str], option: str) -> str:
        return command[command.index(option) + 1]


if __name__ == "__main__":
    unittest.main()
