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

from nac_m365_graph import spfx_site_deployment as deployment_module  # noqa: E402
from nac_m365_graph.spfx_site_deployment import (  # noqa: E402
    INITIAL_PAGE_CONTENT,
    PACKAGE_CONFIG_RELATIVE_PATH,
    PACKAGE_NAME,
    PACKAGE_RELATIVE_PATH,
    PAGE_LAYOUT,
    PAGE_NAME,
    SITE_URL,
    SOLUTION_PRODUCT_ID,
    SOLUTION_TITLE,
    TEAM_ID,
    WEB_PART_ID,
    WORKSPACE_ID,
    DeploymentPlanError,
    ReadbackPolicy,
    build_spfx_site_deployment_plan,
    run_spfx_site_deployment,
    summarize_teams_catalog_versions,
)


APP_CATALOG_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TEAMS_CATALOG_ID = "11111111-2222-3333-4444-555555555555"
TEAMS_EXTERNAL_ID = "66666666-7777-8888-9999-aaaaaaaaaaaa"
TEAMS_INSTALLED_APPS_URL = deployment_module._teams_installed_apps_url(TEAMS_EXTERNAL_ID)
TEAMS_VERSION = "0.1.0"
TEAMS_CATALOG_DETAIL_URL = (
    f"https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/{TEAMS_CATALOG_ID}"
    "?$expand=appDefinitions"
)
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
        self.bound_commands: list[tuple[tuple[str, ...], dict[str, tuple[Path, str]]]] = []

    def run(self, argv: Sequence[str]) -> FakeResult:
        command = tuple(argv)
        self.commands.append(command)
        return self.handler(command)

    def run_bound(
        self,
        argv: Sequence[str],
        bound_artifacts: dict[str, tuple[Path, str]],
    ) -> FakeResult:
        command = tuple(argv)
        self.commands.append(command)
        self.bound_commands.append((command, dict(bound_artifacts)))
        return self.handler(command)


class M365SpfxSiteDeploymentTests(unittest.TestCase):
    def test_page_publish_readback_requires_explicit_published_signal(self) -> None:
        published_payloads = (
            {"controls": [], "Published": True},
            {"controls": [], "IsPublished": True},
            {"controls": [], "Level": "published"},
            {"controls": [], "Level": " Published "},
        )

        for payload in published_payloads:
            with self.subTest(payload=payload):
                self.assertTrue(
                    deployment_module._page_publish_readback_is_ready(payload)
                )

    def test_page_publish_readback_fails_closed_without_explicit_published_signal(self) -> None:
        unpublished_payloads = (
            {"controls": []},
            {"controls": [], "Published": False},
            {"controls": [], "IsPublished": False},
            {"controls": [], "Level": "draft"},
            {"controls": [], "Level": None},
            {"controls": [], "Level": True},
            {"Published": True},
        )

        for payload in unpublished_payloads:
            with self.subTest(payload=payload):
                self.assertFalse(
                    deployment_module._page_publish_readback_is_ready(payload)
                )

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

    def test_plan_rejects_unapproved_or_malformed_api_permission_requests(self) -> None:
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
                    ("spo", "app", "get"),
                    ("spo", "app", "instance", "list"),
                    ("spo", "app", "install"),
                    ("spo", "app", "instance", "list"),
                    ("spo", "page", "list"),
                    ("spo", "page", "add"),
                    ("spo", "page", "get"),
                    ("spo", "page", "clientsidewebpart", "add"),
                    ("spo", "page", "get"),
                    ("spo", "page", "set"),
                    ("spo", "page", "get"),
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
            page_add = runner.commands[9]
            self.assertEqual(self._value(page_add, "--layoutType"), "Article")
            web_part_add = runner.commands[11]
            self.assertEqual(self._value(web_part_add, "--webPartId"), WEB_PART_ID)

    def test_empty_page_canvas_is_initialized_and_verified_before_web_part_add(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)
            page_get_count = 0

            def empty_canvas_handler(command: tuple[str, ...]) -> FakeResult:
                nonlocal page_get_count
                if self._command_head(command) == ("spo", "page", "get"):
                    page_get_count += 1
                    content = "[]" if page_get_count == 1 else INITIAL_PAGE_CONTENT
                    controls = [{"webPartId": WEB_PART_ID}] if page_get_count >= 3 else []
                    return FakeResult(
                        stdout=json.dumps(
                            {
                                "canvasContentJson": content,
                                "controls": controls,
                                "Published": True,
                            }
                        )
                    )
                return self._create_handler(command)

            runner = FakeRunner(empty_canvas_handler)
            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(evidence["classifications"]["initialize_page_canvas_if_empty"], "update")
            self.assertEqual(page_get_count, 4)
            content_command = next(
                command
                for command in runner.commands
                if self._command_head(command) == ("spo", "page", "set")
                and "--content" in command
            )
            self.assertEqual(self._value(content_command, "--name"), PAGE_NAME)
            self.assertEqual(self._value(content_command, "--webUrl"), SITE_URL)
            self.assertEqual(self._value(content_command, "--content"), INITIAL_PAGE_CONTENT)
            heads = [self._command_head(command) for command in runner.commands]
            self.assertLess(
                heads.index(("spo", "page", "set")),
                heads.index(("spo", "page", "clientsidewebpart", "add")),
            )

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
                "reuse",
            )
            self.assertEqual(
                evidence["classifications"]["install_or_reuse_teams_app_on_target_team"],
                "reuse",
            )
            heads = [self._command_head(command) for command in runner.commands]
            self.assertIn(("spo", "app", "upgrade"), heads)
            self.assertIn(("request",), heads)
            self.assertNotIn(("teams", "app", "update"), heads)
            app_add = next(
                command
                for command in runner.commands
                if self._command_head(command) == ("spo", "app", "add")
            )
            self.assertIn("--overwrite", app_add)
            self.assertNotIn(("spo", "app", "install"), heads)
            self.assertNotIn(("spo", "page", "add"), heads)
            self.assertNotIn(("spo", "page", "clientsidewebpart", "add"), heads)
            self.assertNotIn(("teams", "app", "install"), heads)
            self._assert_commands_are_strictly_scoped(runner.commands, include_teams=True)
            request_urls = [
                self._value(command, "--url")
                for command in runner.commands
                if self._command_head(command) == ("request",)
            ]
            self.assertEqual(
                request_urls,
                [TEAMS_CATALOG_DETAIL_URL, TEAMS_INSTALLED_APPS_URL],
            )

    def test_no_teams_catalog_match_preserves_publish_install_and_readback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            installed = False

            def create_then_install_handler(command: tuple[str, ...]) -> FakeResult:
                nonlocal installed
                head = self._command_head(command)
                if head == ("teams", "app", "install"):
                    installed = True
                    return FakeResult()
                if (
                    head == ("request",)
                    and self._value(command, "--url") == TEAMS_INSTALLED_APPS_URL
                ):
                    payload = (
                        self._installed_teams_apps_payload() if installed else {"value": []}
                    )
                    return FakeResult(stdout=json.dumps(payload))
                return self._create_handler(command)

            runner = FakeRunner(create_then_install_handler)

            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]
            request_urls = [
                self._value(command, "--url")
                for command in runner.commands
                if self._command_head(command) == ("request",)
            ]

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(
                evidence["classifications"]["publish_or_update_teams_catalog_app"],
                "create",
            )
            self.assertIn(("teams", "app", "publish"), heads)
            self.assertIn(("teams", "app", "install"), heads)
            self.assertNotIn(("teams", "app", "update"), heads)
            self.assertEqual(
                request_urls,
                [
                    TEAMS_CATALOG_DETAIL_URL,
                    TEAMS_INSTALLED_APPS_URL,
                    TEAMS_INSTALLED_APPS_URL,
                ],
            )

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

    def test_catalog_must_explicitly_prove_exact_bff_aad_permission(self) -> None:
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

    def test_teams_download_is_replaceable_and_published_manifest_version_is_reused(self) -> None:
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
            self.assertEqual(updates, [])
            detail_requests = [
                command
                for command in runner.commands
                if self._command_head(command) == ("request",)
                and self._value(command, "--url") == TEAMS_CATALOG_DETAIL_URL
            ]
            self.assertEqual(len(detail_requests), 2)

    def test_spfx_post_write_readbacks_poll_until_visible_without_write_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)
            state: dict[str, int | bool] = {}
            sleeps: list[float] = []

            def delayed_handler(command: tuple[str, ...]) -> FakeResult:
                head = self._command_head(command)
                if head == ("spo", "app", "add"):
                    state["app_added"] = True
                    return FakeResult()
                if head == ("spo", "app", "deploy"):
                    state["deployed"] = True
                    return FakeResult()
                if head == ("spo", "app", "get"):
                    key = "deploy_reads" if state.get("deployed") else "add_reads"
                    state[key] = int(state.get(key, 0)) + 1
                    if key == "add_reads" and state[key] == 1:
                        return FakeResult(returncode=1, stderr="not visible")
                    record = self._safe_app_record()
                    record["Deployed"] = key == "deploy_reads" and state[key] >= 2
                    return FakeResult(stdout=json.dumps(record))
                if head == ("spo", "app", "install"):
                    state["installed"] = True
                    return FakeResult()
                if head == ("spo", "app", "instance", "list"):
                    if not state.get("installed"):
                        return FakeResult(stdout="[]")
                    state["site_reads"] = int(state.get("site_reads", 0)) + 1
                    payload = (
                        [{"ProductId": SOLUTION_PRODUCT_ID}]
                        if state["site_reads"] >= 2
                        else []
                    )
                    return FakeResult(stdout=json.dumps(payload))
                if head == ("spo", "page", "add"):
                    state["page_added"] = True
                    return FakeResult()
                if head == ("spo", "page", "clientsidewebpart", "add"):
                    state["webpart_added"] = True
                    return FakeResult()
                if head == ("spo", "page", "set") and "--publish" in command:
                    state["published"] = True
                    return FakeResult()
                if head == ("spo", "page", "get"):
                    if state.get("published"):
                        key = "publish_reads"
                    elif state.get("webpart_added"):
                        key = "webpart_reads"
                    else:
                        key = "page_reads"
                    state[key] = int(state.get(key, 0)) + 1
                    if key == "page_reads" and state[key] == 1:
                        return FakeResult(returncode=1, stderr="not visible")
                    controls = (
                        [{"webPartId": WEB_PART_ID}]
                        if key in {"webpart_reads", "publish_reads"} and state[key] >= 2
                        else []
                    )
                    published = key == "publish_reads" and state[key] >= 2
                    return FakeResult(
                        stdout=json.dumps({"controls": controls, "Published": published})
                    )
                return self._create_handler(command)

            runner = FakeRunner(delayed_handler)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(3, 0, sleeps.append),
            )

            self.assertEqual(evidence["status"], "PASSED")
            for head in (
                ("spo", "app", "add"),
                ("spo", "app", "deploy"),
                ("spo", "app", "install"),
                ("spo", "page", "add"),
                ("spo", "page", "clientsidewebpart", "add"),
            ):
                self.assertEqual(
                    sum(self._command_head(command) == head for command in runner.commands),
                    1,
                )
            self.assertEqual(
                sum(
                    self._command_head(command) == ("spo", "page", "set")
                    and "--publish" in command
                    for command in runner.commands
                ),
                1,
            )
            self.assertGreaterEqual(len(sleeps), 6)

    def test_site_app_upgrade_readback_polls_without_retrying_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root)
            upgraded = False
            upgrade_reads = 0
            sleeps: list[float] = []

            def delayed_upgrade(command: tuple[str, ...]) -> FakeResult:
                nonlocal upgraded, upgrade_reads
                head = self._command_head(command)
                if head == ("spo", "app", "upgrade"):
                    upgraded = True
                    return FakeResult()
                if head == ("spo", "app", "instance", "list") and upgraded:
                    upgrade_reads += 1
                    payload = (
                        [{"ProductId": SOLUTION_PRODUCT_ID}]
                        if upgrade_reads >= 2
                        else []
                    )
                    return FakeResult(stdout=json.dumps(payload))
                return self._existing_handler(command)

            runner = FakeRunner(delayed_upgrade)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(3, 0, sleeps.append),
            )

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(upgrade_reads, 2)
            self.assertEqual(
                sum(
                    self._command_head(command) == ("spo", "app", "upgrade")
                    for command in runner.commands
                ),
                1,
            )
            self.assertIn(0, sleeps)

    def test_spfx_post_write_readback_timeouts_are_stable_and_do_not_retry_writes(self) -> None:
        scenarios = (
            ("catalog_add", "app_catalog_add_readback_timeout", ("spo", "app", "add")),
            ("catalog_deploy", "app_catalog_deploy_readback_timeout", ("spo", "app", "deploy")),
            ("site_install", "site_app_install_readback_timeout", ("spo", "app", "install")),
            ("page_create", "page_create_readback_timeout", ("spo", "page", "add")),
            ("webpart", "web_part_add_readback_timeout", ("spo", "page", "clientsidewebpart", "add")),
            ("publish", "page_publish_readback_timeout", ("spo", "page", "set")),
        )
        for target, category, write_head in scenarios:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root)
                state: dict[str, bool] = {}

                def timeout_handler(command: tuple[str, ...]) -> FakeResult:
                    head = self._command_head(command)
                    if head == ("spo", "app", "add"):
                        state["added"] = True
                    elif head == ("spo", "app", "deploy"):
                        state["deployed"] = True
                    elif head == ("spo", "app", "install"):
                        state["installed"] = True
                    elif head == ("spo", "page", "add"):
                        state["page"] = True
                    elif head == ("spo", "page", "clientsidewebpart", "add"):
                        state["webpart"] = True
                    elif head == ("spo", "page", "set") and "--publish" in command:
                        state["published"] = True

                    if head == ("spo", "app", "get"):
                        if target == "catalog_add" and not state.get("deployed"):
                            return FakeResult(returncode=1, stderr="not visible")
                        record = self._safe_app_record()
                        record["Deployed"] = not (
                            target == "catalog_deploy" and state.get("deployed")
                        )
                        return FakeResult(stdout=json.dumps(record))
                    if head == ("spo", "app", "instance", "list"):
                        if not state.get("installed") or target == "site_install":
                            return FakeResult(stdout="[]")
                        return FakeResult(
                            stdout=json.dumps([{"ProductId": SOLUTION_PRODUCT_ID}])
                        )
                    if head == ("spo", "page", "get"):
                        if target == "page_create" and state.get("page"):
                            return FakeResult(returncode=1, stderr="not visible")
                        controls = (
                            []
                            if target == "webpart" and state.get("webpart")
                            else ([{"webPartId": WEB_PART_ID}] if state.get("webpart") else [])
                        )
                        published = not (
                            target == "publish" and state.get("published")
                        )
                        return FakeResult(
                            stdout=json.dumps(
                                {"controls": controls, "Published": published}
                            )
                        )
                    return self._create_handler(command)

                runner = FakeRunner(timeout_handler)
                evidence = run_spfx_site_deployment(
                    plan,
                    runner,
                    readback_policy=ReadbackPolicy(2, 0, lambda _delay: None),
                )

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(evidence["steps"][-1]["error"]["category"], category)
                matching_writes = [
                    command
                    for command in runner.commands
                    if self._command_head(command) == write_head
                    and (target != "publish" or "--publish" in command)
                ]
                self.assertEqual(len(matching_writes), 1)

    def test_upgrade_page_update_and_canvas_timeouts_are_stable(self) -> None:
        cases = (
            ("upgrade", "site_app_upgrade_readback_timeout"),
            ("page_update", "page_update_readback_timeout"),
            ("canvas", "page_canvas_readback_timeout"),
        )
        for target, category in cases:
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root)
                state: dict[str, bool] = {}

                def handler(command: tuple[str, ...]) -> FakeResult:
                    head = self._command_head(command)
                    if head == ("spo", "app", "upgrade"):
                        state["upgraded"] = True
                    if (
                        head == ("spo", "app", "instance", "list")
                        and target == "upgrade"
                        and state.get("upgraded")
                    ):
                        return FakeResult(stdout="[]")
                    if (
                        head == ("spo", "page", "set")
                        and "--layoutType" in command
                    ):
                        state["page_updated"] = True
                    if (
                        head == ("spo", "page", "get")
                        and target == "page_update"
                        and state.get("page_updated")
                    ):
                        return FakeResult(returncode=1, stderr="not visible")
                    if head == ("spo", "page", "get") and target == "canvas":
                        return FakeResult(
                            stdout=json.dumps(
                                {
                                    "canvasContentJson": "[]",
                                    "controls": [],
                                    "Published": True,
                                }
                            )
                        )
                    return self._existing_handler(command)

                runner = FakeRunner(handler)
                evidence = run_spfx_site_deployment(
                    plan,
                    runner,
                    readback_policy=ReadbackPolicy(2, 0, lambda _delay: None),
                )

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(evidence["steps"][-1]["error"]["category"], category)
                if target == "upgrade":
                    writes = [
                        command
                        for command in runner.commands
                        if self._command_head(command) == ("spo", "app", "upgrade")
                    ]
                elif target == "page_update":
                    writes = [
                        command
                        for command in runner.commands
                        if self._command_head(command) == ("spo", "page", "set")
                        and "--layoutType" in command
                    ]
                else:
                    writes = [
                        command
                        for command in runner.commands
                        if self._command_head(command) == ("spo", "page", "set")
                        and "--content" in command
                    ]
                self.assertEqual(len(writes), 1)

    def test_newer_approved_teams_version_polls_until_visible_and_updates_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            detail_reads = 0
            sleeps: list[float] = []

            def catalog_detail(*definitions: dict[str, str]) -> dict[str, object]:
                return {
                    "id": TEAMS_CATALOG_ID,
                    "externalId": TEAMS_EXTERNAL_ID,
                    "appDefinitions": list(definitions),
                }

            def upgrade_handler(command: tuple[str, ...]) -> FakeResult:
                nonlocal detail_reads
                if self._command_head(command) == (
                    "spo",
                    "app",
                    "teamspackage",
                    "download",
                ):
                    self._write_downloaded_teams_package(command, version="0.2.0")
                    return FakeResult()
                if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                    detail_reads += 1
                    historical = {"version": TEAMS_VERSION, "publishingState": "published"}
                    if detail_reads <= 2:
                        payload = catalog_detail(historical)
                    elif detail_reads == 3:
                        payload = catalog_detail(
                            historical,
                            {"version": "0.2.0", "publishingState": "submitted"},
                        )
                    else:
                        payload = catalog_detail(
                            historical,
                            {"version": "0.2.0", "publishingState": "published"},
                        )
                    return FakeResult(stdout=json.dumps(payload))
                if self._command_head(command) == ("teams", "app", "update"):
                    return FakeResult()
                return self._existing_handler(command)

            runner = FakeRunner(upgrade_handler)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(4, 0.25, sleeps.append),
            )
            updates = [
                command
                for command in runner.commands
                if self._command_head(command) == ("teams", "app", "update")
            ]

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(
                evidence["classifications"]["publish_or_update_teams_catalog_app"],
                "update",
            )
            self.assertEqual(len(updates), 1)
            self.assertEqual(detail_reads, 4)
            self.assertEqual(sleeps, [0.25, 0.25])
            self.assertEqual(
                evidence["teams_catalog_version_readback"],
                {
                    "schema_version": "nac.m365-teams-catalog-version-readback/v0.1",
                    "expected_version": "0.2.0",
                    "highest_version": "0.2.0",
                    "expected_publishing_state": "published",
                    "historical_published_versions": [TEAMS_VERSION],
                    "published_versions": [TEAMS_VERSION, "0.2.0"],
                    "definition_count": 2,
                    "required_action": "reuse",
                    "expected_is_unique_highest_published": True,
                },
            )
            self._assert_commands_are_strictly_scoped(runner.commands, include_teams=True)

    def test_teams_publish_polls_until_catalog_version_is_visible_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            detail_reads = 0
            sleeps: list[float] = []

            def delayed_publish(command: tuple[str, ...]) -> FakeResult:
                nonlocal detail_reads
                if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                    detail_reads += 1
                    if detail_reads == 1:
                        return FakeResult(returncode=1, stderr="not visible")
                    if detail_reads == 2:
                        pending = self._teams_catalog_detail()
                        pending["appDefinitions"] = []
                        return FakeResult(stdout=json.dumps(pending))
                    state = "submitted" if detail_reads == 3 else "published"
                    return FakeResult(
                        stdout=json.dumps(
                            self._teams_catalog_detail(publishing_state=state)
                        )
                    )
                return self._create_handler(command)

            runner = FakeRunner(delayed_publish)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(4, 0.2, sleeps.append),
            )

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(detail_reads, 4)
            self.assertEqual(sleeps, [0.2, 0.2, 0.2])
            self.assertEqual(
                sum(
                    self._command_head(command) == ("teams", "app", "publish")
                    for command in runner.commands
                ),
                1,
            )
            self.assertTrue(
                evidence["teams_catalog_version_readback"][
                    "expected_is_unique_highest_published"
                ]
            )

    def test_teams_publish_readback_timeout_is_stable_and_does_not_retry_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            sleeps: list[float] = []

            def invisible_publish(command: tuple[str, ...]) -> FakeResult:
                if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                    return FakeResult(returncode=1, stderr="not visible")
                return self._create_handler(command)

            runner = FakeRunner(invisible_publish)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(3, 0.4, sleeps.append),
            )

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "teams_catalog_publish_readback_timeout",
            )
            self.assertEqual(sleeps, [0.4, 0.4])
            self.assertEqual(
                sum(
                    self._command_head(command) == ("teams", "app", "publish")
                    for command in runner.commands
                ),
                1,
            )
            self.assertNotIn(
                ("teams", "app", "install"),
                [self._command_head(command) for command in runner.commands],
            )

    def test_teams_install_polls_until_visible_without_retrying_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            installation_reads = 0
            sleeps: list[float] = []

            def delayed_install(command: tuple[str, ...]) -> FakeResult:
                nonlocal installation_reads
                if self._is_request_for(command, TEAMS_INSTALLED_APPS_URL):
                    installation_reads += 1
                    payload = (
                        self._installed_teams_apps_payload()
                        if installation_reads >= 4
                        else {"value": []}
                    )
                    return FakeResult(stdout=json.dumps(payload))
                return self._existing_handler(command)

            runner = FakeRunner(delayed_install)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(4, 0.3, sleeps.append),
            )

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(installation_reads, 4)
            self.assertEqual(sleeps, [0.3, 0.3])
            self.assertEqual(
                sum(
                    self._command_head(command) == ("teams", "app", "install")
                    for command in runner.commands
                ),
                1,
            )

    def test_catalog_version_summary_accepts_history_and_blocks_duplicate_or_higher(self) -> None:
        valid = {
            "id": TEAMS_CATALOG_ID,
            "externalId": TEAMS_EXTERNAL_ID,
            "appDefinitions": [
                {"version": "0.1.0", "publishingState": "published"},
                {"version": "0.2.0", "publishingState": "published"},
            ],
        }
        summary = summarize_teams_catalog_versions(
            valid,
            teams_catalog_id=TEAMS_CATALOG_ID,
            teams_manifest_app_id=TEAMS_EXTERNAL_ID,
            teams_manifest_version="0.2.0",
        )
        self.assertTrue(summary.expected_is_unique_highest_published)
        self.assertEqual(summary.historical_published_versions, ("0.1.0",))
        self.assertEqual(summary.published_versions, ("0.1.0", "0.2.0"))

        duplicate_expected = {
            **valid,
            "appDefinitions": [
                *valid["appDefinitions"],
                {"version": "0.2.0", "publishingState": "published"},
            ],
        }
        higher = {
            **valid,
            "appDefinitions": [
                *valid["appDefinitions"],
                {"version": "0.3.0", "publishingState": "published"},
            ],
        }
        for payload in (duplicate_expected, higher):
            with self.subTest(payload=payload), self.assertRaises(DeploymentPlanError):
                summarize_teams_catalog_versions(
                    payload,
                    teams_catalog_id=TEAMS_CATALOG_ID,
                    teams_manifest_app_id=TEAMS_EXTERNAL_ID,
                    teams_manifest_version="0.2.0",
                )

    def test_teams_catalog_downgrade_and_version_conflicts_block_before_update(self) -> None:
        unsafe_details = (
            self._teams_catalog_detail(version="0.2.0"),
            self._teams_catalog_detail(version="0.0.9", publishing_state="submitted"),
            {
                **self._teams_catalog_detail(version="0.0.9"),
                "appDefinitions": [
                    {"version": "0.0.9", "publishingState": "published"},
                    {"version": "0.0.9", "publishingState": "published"},
                ],
            },
        )
        for detail in unsafe_details:
            with self.subTest(detail=detail), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

                def unsafe_handler(command: tuple[str, ...]) -> FakeResult:
                    if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                        return FakeResult(stdout=json.dumps(detail))
                    return self._existing_handler(command)

                runner = FakeRunner(unsafe_handler)
                evidence = run_spfx_site_deployment(plan, runner)
                heads = [self._command_head(command) for command in runner.commands]

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertNotIn(("teams", "app", "update"), heads)
                self.assertNotIn(("teams", "app", "install"), heads)

    def test_teams_catalog_update_requires_published_exact_readback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def stale_readback_handler(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == (
                    "spo",
                    "app",
                    "teamspackage",
                    "download",
                ):
                    self._write_downloaded_teams_package(command, version="0.2.0")
                    return FakeResult()
                if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                    return FakeResult(
                        stdout=json.dumps(self._teams_catalog_detail(version=TEAMS_VERSION))
                    )
                return self._existing_handler(command)

            runner = FakeRunner(stale_readback_handler)
            sleeps: list[float] = []
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(3, 0.5, sleeps.append),
            )
            updates = [
                command
                for command in runner.commands
                if self._command_head(command) == ("teams", "app", "update")
            ]

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "teams_catalog_update_readback_timeout",
            )
            self.assertEqual(len(updates), 1)
            self.assertEqual(sleeps, [0.5, 0.5])
            self.assertNotIn(
                ("teams", "app", "install"),
                [self._command_head(command) for command in runner.commands],
            )

    def test_duplicate_teams_external_ids_fail_before_detail_or_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def duplicate_handler(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == ("teams", "app", "list"):
                    return FakeResult(
                        stdout=json.dumps(
                            [
                                self._teams_catalog_app(),
                                self._teams_catalog_app(
                                    catalog_id="22222222-3333-4444-5555-666666666666"
                                ),
                            ]
                        )
                    )
                return self._existing_handler(command)

            runner = FakeRunner(duplicate_handler)
            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "unsafe_control_plane_response",
            )
            self.assertNotIn(("request",), heads)
            self.assertNotIn(("teams", "app", "update"), heads)
            self.assertNotIn(("teams", "app", "install"), heads)

    def test_malformed_or_mixed_teams_catalog_payloads_fail_before_publish(self) -> None:
        unsafe_payloads = (
            None,
            {},
            {"items": []},
            {"value": {}},
            [self._teams_catalog_app(), None],
            {"value": [self._teams_catalog_app(), "not-an-object"]},
        )
        for payload in unsafe_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(
                    repo_root=root,
                    include_teams=True,
                )

                def malformed_catalog(command: tuple[str, ...]) -> FakeResult:
                    if self._command_head(command) == ("teams", "app", "list"):
                        return FakeResult(stdout=json.dumps(payload))
                    return self._create_handler(command)

                runner = FakeRunner(malformed_catalog)
                evidence = run_spfx_site_deployment(plan, runner)
                heads = [self._command_head(command) for command in runner.commands]

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertNotIn(("teams", "app", "publish"), heads)
                self.assertNotIn(("teams", "app", "install"), heads)
                self.assertNotIn(("request",), heads)

    def test_malformed_catalog_id_never_reaches_request_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def malformed_id_handler(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == ("teams", "app", "list"):
                    return FakeResult(
                        stdout=json.dumps(
                            [self._teams_catalog_app(catalog_id="not-a-guid")]
                        )
                    )
                return self._existing_handler(command)

            runner = FakeRunner(malformed_id_handler)
            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "unsafe_control_plane_response",
            )
            self.assertNotIn(("request",), heads)
            self.assertNotIn(("teams", "app", "install"), heads)

    def test_catalog_detail_request_rejects_every_nonexact_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            exact = (
                "m365",
                "request",
                "--url",
                TEAMS_CATALOG_DETAIL_URL,
                "--method",
                "get",
                "--output",
                "json",
            )
            deployment_module._validate_command(
                plan,
                exact,
                allowed_teams_catalog_detail_id=TEAMS_CATALOG_ID,
            )

            unsafe_commands = {
                "beta": (
                    *exact[:3],
                    TEAMS_CATALOG_DETAIL_URL.replace("/v1.0/", "/beta/"),
                    *exact[4:],
                ),
                "alternate_query": (
                    *exact[:3],
                    TEAMS_CATALOG_DETAIL_URL + "&$select=id",
                    *exact[4:],
                ),
                "post": (*exact[:5], "post", *exact[6:]),
                "body": (*exact, "--body", "{}"),
                "resource": (*exact, "--resource", "graph"),
                "file_path": (*exact, "--filePath", str(plan.teams_package_path)),
                "extra_option": (*exact, "--headers", "{}"),
            }
            for variant, command in unsafe_commands.items():
                with self.subTest(variant=variant):
                    with self.assertRaises(deployment_module._StepFailure):
                        deployment_module._validate_command(
                            plan,
                            command,
                            allowed_teams_catalog_detail_id=TEAMS_CATALOG_ID,
                        )

    def test_teams_catalog_update_command_rejects_every_nonexact_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            exact = (
                "m365",
                "teams",
                "app",
                "update",
                "--id",
                TEAMS_CATALOG_ID,
                "--filePath",
                str(plan.teams_package_path),
                "--output",
                "none",
            )
            deployment_module._validate_command(
                plan,
                exact,
                allowed_teams_catalog_detail_id=TEAMS_CATALOG_ID,
            )

            unsafe_commands = {
                "wrong_catalog_id": (
                    *exact[:5],
                    "ffffffff-ffff-ffff-ffff-ffffffffffff",
                    *exact[6:],
                ),
                "wrong_package": (*exact[:7], str(root / "other.zip"), *exact[8:]),
                "json_output": (*exact[:-1], "json"),
                "missing_output": exact[:-2],
                "extra_team": (*exact, "--teamId", TEAM_ID),
            }
            for variant, command in unsafe_commands.items():
                with self.subTest(variant=variant):
                    with self.assertRaises(deployment_module._StepFailure):
                        deployment_module._validate_command(
                            plan,
                            command,
                            allowed_teams_catalog_detail_id=TEAMS_CATALOG_ID,
                        )

    def test_downloaded_teams_manifest_requires_exact_id_and_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def malformed_manifest_handler(command: tuple[str, ...]) -> FakeResult:
                if self._command_head(command) == (
                    "spo",
                    "app",
                    "teamspackage",
                    "download",
                ):
                    path = Path(self._value(command, "--fileName"))
                    path.parent.mkdir(parents=True, exist_ok=True)
                    with zipfile.ZipFile(path, "w") as package:
                        package.writestr(
                            "manifest.json",
                            json.dumps(
                                {
                                    "id": TEAMS_EXTERNAL_ID,
                                    "version": "not-a-version",
                                }
                            ),
                        )
                    return FakeResult()
                return self._existing_handler(command)

            runner = FakeRunner(malformed_manifest_handler)
            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "unsafe_control_plane_response",
            )
            self.assertNotIn(("teams", "app", "list"), heads)
            self.assertNotIn(("request",), heads)

    def test_downloaded_teams_package_rejects_extra_files_and_capabilities(self) -> None:
        cases = (
            ({"manifestVersion": "1.17", "version": TEAMS_VERSION, "id": TEAMS_EXTERNAL_ID}, {"script.js": b"alert(1)"}),
            ({"manifestVersion": "1.17", "version": TEAMS_VERSION, "id": TEAMS_EXTERNAL_ID, "permissions": ["identity"]}, {}),
            ({"manifestVersion": "1.17", "version": TEAMS_VERSION, "id": TEAMS_EXTERNAL_ID, "staticTabs": [{"scopes": ["team"]}]}, {}),
            ({"manifestVersion": "1.17", "version": TEAMS_VERSION, "id": TEAMS_EXTERNAL_ID, "validDomains": ["evil.example"]}, {}),
            ({"manifestVersion": "1.17", "version": TEAMS_VERSION, "id": TEAMS_EXTERNAL_ID, "unknownField": "value"}, {}),
            ({"manifestVersion": "1.17", "version": TEAMS_VERSION, "id": TEAMS_EXTERNAL_ID}, {"a/./b": b"collision"}),
        )
        for manifest, extras in cases:
            with self.subTest(manifest=manifest, extras=extras), tempfile.TemporaryDirectory() as tmp:
                package_path = Path(tmp) / "teams.zip"
                with zipfile.ZipFile(package_path, "w") as package:
                    package.writestr("manifest.json", json.dumps(manifest))
                    for name, payload in extras.items():
                        package.writestr(name, payload)
                with self.assertRaises(DeploymentPlanError):
                    deployment_module._read_teams_manifest_identity(package_path)

    def test_downloaded_teams_package_is_hash_bound_for_publish(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            runner = FakeRunner(self._create_handler)

            evidence = run_spfx_site_deployment(plan, runner)

            self.assertEqual(evidence["status"], "PASSED")
            teams_bindings = [
                bindings
                for command, bindings in runner.bound_commands
                if self._command_head(command) in {
                    ("teams", "app", "publish"),
                    ("teams", "app", "update"),
                }
            ]
            self.assertEqual(len(teams_bindings), 1)
            binding = teams_bindings[0][str(plan.teams_package_path)]
            self.assertEqual(binding[0], plan.teams_package_path)
            self.assertEqual(binding[1], deployment_module._sha256(plan.teams_package_path))

    def test_submitted_matching_version_stops_with_review_pending_category(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def submitted_handler(command: tuple[str, ...]) -> FakeResult:
                if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                    return FakeResult(
                        stdout=json.dumps(
                            self._teams_catalog_detail(publishing_state="submitted")
                        )
                    )
                return self._existing_handler(command)

            runner = FakeRunner(submitted_handler)
            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "teams_catalog_review_pending",
            )
            self.assertEqual(runner.commands[-1][0:2], ("m365", "request"))
            self.assertEqual(
                self._value(runner.commands[-1], "--url"),
                TEAMS_CATALOG_DETAIL_URL,
            )
            self.assertNotIn(("teams", "app", "update"), heads)
            self.assertNotIn(("teams", "app", "install"), heads)

    def test_ambiguous_matching_version_definitions_fail_before_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def ambiguous_handler(command: tuple[str, ...]) -> FakeResult:
                if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                    detail = self._teams_catalog_detail()
                    definitions = detail["appDefinitions"]
                    assert isinstance(definitions, list)
                    definitions.append(
                        {"version": TEAMS_VERSION, "publishingState": "published"}
                    )
                    return FakeResult(stdout=json.dumps(detail))
                return self._existing_handler(command)

            runner = FakeRunner(ambiguous_handler)
            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "unsafe_control_plane_response",
            )
            self.assertNotIn(("teams", "app", "update"), heads)
            self.assertNotIn(("teams", "app", "install"), heads)

    def test_generic_teams_conflict_is_not_accepted_as_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

            def generic_conflict(command: tuple[str, ...]) -> FakeResult:
                if self._is_request_for(command, TEAMS_INSTALLED_APPS_URL):
                    return FakeResult(stdout='{"value":[]}')
                if self._command_head(command) == ("teams", "app", "install"):
                    return FakeResult(returncode=1, stderr="Conflict")
                return self._existing_handler(command)

            runner = FakeRunner(generic_conflict)
            evidence = run_spfx_site_deployment(
                plan,
                runner,
                readback_policy=ReadbackPolicy(3, 0, lambda _delay: None),
            )

            self.assertEqual(evidence["status"], "FAILED")
            self.assertEqual(
                evidence["steps"][-1]["error"]["category"],
                "teams_app_install_readback_timeout",
            )
            self.assertEqual(
                self._command_head(runner.commands[-1]),
                ("request",),
            )
            request_urls = [
                self._value(command, "--url")
                for command in runner.commands
                if self._command_head(command) == ("request",)
            ]
            self.assertEqual(
                request_urls,
                [
                    TEAMS_CATALOG_DETAIL_URL,
                    TEAMS_INSTALLED_APPS_URL,
                    TEAMS_INSTALLED_APPS_URL,
                    TEAMS_INSTALLED_APPS_URL,
                    TEAMS_INSTALLED_APPS_URL,
                ],
            )

    def test_install_error_survives_failed_reconciliation_readback(self) -> None:
        readback_failures = (
            FakeResult(returncode=2, stderr="Graph unavailable"),
            FakeResult(stdout="{not-json"),
        )
        for readback_failure in readback_failures:
            with (
                self.subTest(readback_failure=readback_failure),
                tempfile.TemporaryDirectory() as tmp,
            ):
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
                readback_count = 0

                def failed_reconciliation(command: tuple[str, ...]) -> FakeResult:
                    nonlocal readback_count
                    if self._is_request_for(command, TEAMS_INSTALLED_APPS_URL):
                        readback_count += 1
                        if readback_count == 1:
                            return FakeResult(stdout='{"value":[]}')
                        return readback_failure
                    if self._command_head(command) == ("teams", "app", "install"):
                        return FakeResult(returncode=1)
                    return self._existing_handler(command)

                runner = FakeRunner(failed_reconciliation)
                evidence = run_spfx_site_deployment(
                    plan,
                    runner,
                    readback_policy=ReadbackPolicy(3, 0, lambda _delay: None),
                )

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["name"],
                    "verify_teams_app_installed_on_target_team",
                )
                expected_category = (
                    "teams_app_install_readback_timeout"
                    if readback_failure.returncode
                    else "invalid_control_plane_response"
                )
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    expected_category,
                )
                self.assertEqual(
                    sum(
                        self._command_head(command) == ("teams", "app", "install")
                        for command in runner.commands
                    ),
                    1,
                )

    def test_parallel_install_race_is_reconciled_by_exact_readback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_package_fixture(root)
            plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)
            readback_count = 0

            def raced_install(command: tuple[str, ...]) -> FakeResult:
                nonlocal readback_count
                if self._is_request_for(command, TEAMS_INSTALLED_APPS_URL):
                    readback_count += 1
                    payload = (
                        {"value": []}
                        if readback_count == 1
                        else self._installed_teams_apps_payload()
                    )
                    return FakeResult(stdout=json.dumps(payload))
                if self._command_head(command) == ("teams", "app", "install"):
                    return FakeResult(returncode=1)
                return self._existing_handler(command)

            runner = FakeRunner(raced_install)
            evidence = run_spfx_site_deployment(plan, runner)
            heads = [self._command_head(command) for command in runner.commands]
            request_urls = [
                self._value(command, "--url")
                for command in runner.commands
                if self._command_head(command) == ("request",)
            ]

            self.assertEqual(evidence["status"], "PASSED")
            self.assertEqual(
                evidence["classifications"]["install_or_reuse_teams_app_on_target_team"],
                "reuse",
            )
            self.assertIn(("teams", "app", "install"), heads)
            self.assertEqual(
                request_urls,
                [
                    TEAMS_CATALOG_DETAIL_URL,
                    TEAMS_INSTALLED_APPS_URL,
                    TEAMS_INSTALLED_APPS_URL,
                ],
            )

    def test_rejected_missing_or_malformed_catalog_detail_fails_closed(self) -> None:
        malformed = self._teams_catalog_detail()
        malformed["appDefinitions"] = [None]
        unsafe_payloads = (
            self._teams_catalog_detail(publishing_state="rejected"),
            self._teams_catalog_detail(version="9.9.9"),
            malformed,
            self._teams_catalog_detail(
                catalog_id="ffffffff-ffff-ffff-ffff-ffffffffffff"
            ),
            self._teams_catalog_detail(
                external_id="eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"
            ),
        )
        for payload in unsafe_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(
                    repo_root=root,
                    include_teams=True,
                )

                def unsafe_detail(command: tuple[str, ...]) -> FakeResult:
                    if self._is_request_for(command, TEAMS_CATALOG_DETAIL_URL):
                        return FakeResult(stdout=json.dumps(payload))
                    return self._existing_handler(command)

                runner = FakeRunner(unsafe_detail)
                evidence = run_spfx_site_deployment(plan, runner)
                heads = [self._command_head(command) for command in runner.commands]

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertNotIn(("teams", "app", "update"), heads)
                self.assertNotIn(("teams", "app", "install"), heads)

    def test_teams_install_preflight_fails_closed_before_write(self) -> None:
        unsafe_payloads = (
            {"value": "not-a-list"},
            {"value": [None]},
            {"value": [{"id": "missing-teams-app"}]},
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
            {
                **self._installed_teams_apps_payload(),
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/next-page",
            },
        )
        for payload in unsafe_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self._write_package_fixture(root)
                plan = build_spfx_site_deployment_plan(repo_root=root, include_teams=True)

                def unsafe_preflight(command: tuple[str, ...]) -> FakeResult:
                    if self._is_request_for(command, TEAMS_INSTALLED_APPS_URL):
                        return FakeResult(stdout=json.dumps(payload))
                    return self._existing_handler(command)

                runner = FakeRunner(unsafe_preflight)
                evidence = run_spfx_site_deployment(plan, runner)
                heads = [self._command_head(command) for command in runner.commands]

                self.assertEqual(evidence["status"], "FAILED")
                self.assertEqual(
                    evidence["steps"][-1]["name"],
                    "inspect_teams_app_installation_on_target_team",
                )
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    "unsafe_control_plane_response",
                )
                self.assertNotIn(("teams", "app", "install"), heads)

    def test_teams_install_readback_requires_exact_catalog_and_manifest_identity(self) -> None:
        unsafe_payloads = (
            {"value": []},
            {"value": "not-a-list"},
            {"value": [None]},
            {"value": [{"id": "missing-teams-app"}]},
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

                readback_count = 0

                def unsafe_readback(command: tuple[str, ...]) -> FakeResult:
                    nonlocal readback_count
                    if self._is_request_for(command, TEAMS_INSTALLED_APPS_URL):
                        readback_count += 1
                        response = {"value": []} if readback_count == 1 else payload
                        return FakeResult(stdout=json.dumps(response))
                    if self._command_head(command) == ("teams", "app", "install"):
                        return FakeResult()
                    return self._existing_handler(command)

                runner = FakeRunner(unsafe_readback)
                evidence = run_spfx_site_deployment(
                    plan,
                    runner,
                    readback_policy=ReadbackPolicy(2, 0, lambda _delay: None),
                )

                self.assertEqual(evidence["status"], "FAILED")
                expected_category = (
                    "teams_app_install_readback_timeout"
                    if payload == {"value": []}
                    else "unsafe_control_plane_response"
                )
                self.assertEqual(
                    evidence["steps"][-1]["error"]["category"],
                    expected_category,
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
                            [{"resource": "NaC M365 BFF", "scope": "Matter.Read"}]
                            if web_api_permission_requests is None
                            else web_api_permission_requests
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
            else (
                '<WebApiPermissionRequests>'
                '<WebApiPermissionRequest Resource="NaC M365 BFF" Scope="Matter.Read" />'
                '</WebApiPermissionRequests>'
            )
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
            "Deployed": True,
            "AadPermissions": [
                {"Resource": "NaC M365 BFF", "Scope": "Matter.Read"}
            ],
        }

    def _create_handler(self, command: tuple[str, ...]) -> FakeResult:
        head = self._command_head(command)
        if head == ("spo", "app", "list"):
            return FakeResult(stdout="[]")
        if head == ("spo", "app", "get"):
            return FakeResult(stdout=json.dumps(self._safe_app_record()))
        if head == ("spo", "app", "install"):
            self._create_site_app_installed = True
            return FakeResult()
        if head == ("spo", "app", "instance", "list"):
            payload = (
                [{"ProductId": SOLUTION_PRODUCT_ID}]
                if getattr(self, "_create_site_app_installed", False)
                else []
            )
            return FakeResult(stdout=json.dumps(payload))
        if head == ("spo", "page", "list"):
            return FakeResult(stdout="[]")
        if head == ("spo", "page", "clientsidewebpart", "add"):
            self._create_web_part_added = True
            return FakeResult()
        if head == ("spo", "page", "get"):
            controls = (
                [{"webPartId": WEB_PART_ID}]
                if getattr(self, "_create_web_part_added", False)
                else []
            )
            return FakeResult(stdout=json.dumps({"controls": controls, "Published": True}))
        if head == ("spo", "app", "teamspackage", "download"):
            self._write_downloaded_teams_package(command)
            return FakeResult()
        if head == ("teams", "app", "list"):
            return FakeResult(stdout='{"value":[]}')
        if head == ("teams", "app", "publish"):
            return FakeResult(
                stdout=json.dumps({"id": TEAMS_CATALOG_ID, "externalId": TEAMS_EXTERNAL_ID})
            )
        if head == ("request",):
            if self._value(command, "--url") == TEAMS_CATALOG_DETAIL_URL:
                return FakeResult(stdout=json.dumps(self._teams_catalog_detail()))
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
            return FakeResult(
                stdout=json.dumps(
                    {"controls": [{"webPartId": WEB_PART_ID}], "Published": True}
                )
            )
        if head == ("spo", "app", "teamspackage", "download"):
            self._write_downloaded_teams_package(command)
            return FakeResult()
        if head == ("teams", "app", "list"):
            return FakeResult(stdout=json.dumps([self._teams_catalog_app()]))
        if head == ("teams", "app", "install"):
            return FakeResult(returncode=1, stderr="App is already installed in this team")
        if head == ("request",):
            if self._value(command, "--url") == TEAMS_CATALOG_DETAIL_URL:
                return FakeResult(stdout=json.dumps(self._teams_catalog_detail()))
            return FakeResult(stdout=json.dumps(self._installed_teams_apps_payload()))
        return FakeResult()

    @staticmethod
    def _teams_catalog_app(
        *,
        catalog_id: str = TEAMS_CATALOG_ID,
        external_id: str = TEAMS_EXTERNAL_ID,
    ) -> dict[str, object]:
        return {
            "id": catalog_id,
            "externalId": external_id,
            "distributionMethod": "organization",
        }

    @staticmethod
    def _teams_catalog_detail(
        *,
        catalog_id: str = TEAMS_CATALOG_ID,
        external_id: str = TEAMS_EXTERNAL_ID,
        version: str = TEAMS_VERSION,
        publishing_state: str = "published",
    ) -> dict[str, object]:
        return {
            "id": catalog_id,
            "externalId": external_id,
            "appDefinitions": [
                {"version": version, "publishingState": publishing_state}
            ],
        }

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

    def _write_downloaded_teams_package(
        self,
        command: Sequence[str],
        *,
        version: str = TEAMS_VERSION,
    ) -> None:
        path = Path(self._value(command, "--fileName"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w") as package:
            package.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "manifestVersion": "1.17",
                        "version": version,
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
                self.assertIn(
                    self._value(command, "--url"),
                    {TEAMS_CATALOG_DETAIL_URL, TEAMS_INSTALLED_APPS_URL},
                )
                self.assertEqual(self._value(command, "--method"), "get")

    def _is_request_for(self, command: Sequence[str], url: str) -> bool:
        return (
            self._command_head(command) == ("request",)
            and self._value(command, "--url") == url
        )

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
