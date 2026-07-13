from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "workflows/contracts/m365-mvp-test-environment.verification.contract.json"
)
DE_SPEC = (
    ROOT
    / "docs/de/superpowers/specs/2026-07-13-m365-mvp-test-environment-design.md"
)
EN_SPEC = (
    ROOT
    / "docs/en/superpowers/specs/2026-07-13-m365-mvp-test-environment-design.md"
)
DE_PLAN = (
    ROOT
    / "docs/de/superpowers/plans/2026-07-13-m365-mvp-test-environment.md"
)
EN_PLAN = (
    ROOT
    / "docs/en/superpowers/plans/2026-07-13-m365-mvp-test-environment.md"
)
ACCEPTANCE_IDS = [f"AC-620-{number:02d}" for number in range(1, 8)]


class M365MvpTestEnvironmentVerificationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_binds_issue_scope_and_all_acceptance_ids(self) -> None:
        self.assertEqual(
            self.contract["leading_issue"],
            "https://github.com/notariat8/NaC/issues/620",
        )
        self.assertEqual(self.contract["spec_id"], "m365-mvp-test-environment")
        self.assertEqual(self.contract["acceptance_ids"], ACCEPTANCE_IDS)
        self.assertEqual(
            [item["id"] for item in self.contract["acceptance_criteria"]],
            ACCEPTANCE_IDS,
        )
        self.assertEqual(
            self.contract["target_boundary"]["workspace_id_exact"],
            "notary_team_01",
        )
        self.assertFalse(
            self.contract["target_boundary"]["other_workspaces_allowed"]
        )
        self.assertFalse(
            self.contract["target_boundary"]["production_data_allowed"]
        )

    def test_acceptance_requirements_match_issue_620_semantics(self) -> None:
        requirements = {
            item["id"]: item["requirement"]
            for item in self.contract["acceptance_criteria"]
        }
        essential_phrases = {
            "AC-620-01": (
                "site-scoped and installable SPFx package",
                "SharePointWebPart and TeamsTab",
                "skipFeatureDeployment=false",
            ),
            "AC-620-02": (
                "never requests Microsoft Graph permissions",
                "delegated NaC BFF scope",
                "activation remains DEFERRED",
            ),
            "AC-620-03": (
                "validated Entra access token",
                "server-side allowlist",
                "live token validation remains DEFERRED",
            ),
            "AC-620-04": (
                "assigned user",
                "redacted projection",
                "status, tasks, due date and BPMN",
                "live BFF delivery path remains DEFERRED",
            ),
            "AC-620-05": (
                "Unassigned users",
                "workspace, matter, purpose or filter",
                "fail closed",
                "without revealing whether the matter exists",
            ),
            "AC-620-06": (
                "Site-scoped SharePoint and optional Teams deployment",
                "Graph REST v1.0 write/readback",
                "run-owned cleanup",
                "reproducible and redacted",
            ),
            "AC-620-07": (
                "no credential or permission",
                "no production data",
                "no operation in any workspace other than notary_team_01",
            ),
        }
        for acceptance_id, phrases in essential_phrases.items():
            with self.subTest(acceptance_id=acceptance_id):
                for phrase in phrases:
                    self.assertIn(phrase, requirements[acceptance_id])

    def test_contract_checks_cover_one_shot_deploy_and_runtime_bootstrap(self) -> None:
        checks = "\n".join(self.contract["checks"])
        self.assertIn("tests.test_m365_mvp_test_environment_deploy", checks)
        self.assertIn("tests.test_m365_runtime_env_bootstrap", checks)

    def test_spfx_is_site_scoped_graph_free_and_teams_capable(self) -> None:
        package = self.contract["ui_package"]
        self.assertEqual(package["framework_version_exact"], "1.23.2")
        self.assertEqual(package["deployment_scope_exact"], "site")
        self.assertFalse(package["skip_feature_deployment_exact"])
        self.assertEqual(package["graph_permission_requests_exact"], 0)
        self.assertFalse(package["direct_graph_from_spfx_allowed"])
        self.assertEqual(package["delegated_api_target_exact"], "NaC BFF")
        self.assertEqual(
            package["delegated_api_activation_status_exact"], "DEFERRED"
        )
        self.assertFalse(package["legacy_sharepoint_api_or_sdk_allowed"])
        self.assertEqual(
            set(package["hosts_required"]),
            {
                "SharePointWebPart",
                "SharePointFullPage",
                "TeamsTab",
                "TeamsPersonalApp",
            },
        )

    def test_graph_data_plane_fixture_and_cleanup_are_exact(self) -> None:
        data_plane = self.contract["data_plane"]
        fixture = self.contract["synthetic_fixture"]
        self.assertFalse(data_plane["browser_graph_calls_allowed"])
        self.assertEqual(
            data_plane["data_api_exact"],
            "raw Microsoft Graph REST v1.0",
        )
        self.assertFalse(data_plane["graph_beta_allowed"])
        self.assertFalse(data_plane["legacy_api_allowed"])
        self.assertTrue(data_plane["targeted_readback_required"])
        self.assertTrue(data_plane["run_owned_cleanup_required"])
        self.assertFalse(data_plane["foreign_or_preexisting_item_deletion_allowed"])
        deployment = self.contract["deployment_control_plane"]
        self.assertEqual(deployment["tool_exact"], "Microsoft 365 CLI")
        self.assertEqual(
            deployment["allowed_operations_exact"],
            [
                "deploy_spfx_package_to_app_catalog",
                "install_or_upgrade_app_on_exact_site",
                "publish_dedicated_page_and_webpart",
                "publish_or_install_teams_package_in_exact_team",
            ],
        )
        self.assertFalse(
            deployment["sharepoint_list_or_item_data_operations_allowed"]
        )
        self.assertFalse(
            deployment["permission_scope_or_credential_changes_allowed"]
        )
        self.assertFalse(deployment["tenant_wide_deployment_allowed"])
        self.assertEqual(fixture["task_count_exact"], 2)
        self.assertGreaterEqual(fixture["minimum_explicit_due_dates"], 1)
        self.assertEqual(
            fixture["role_scenarios_exact"],
            [
                "assigned_allow",
                "valid_deputy_allow",
                "unauthorized_deny_without_existence_leak",
            ],
        )

    def test_bff_activation_is_deferred_without_permission_changes(self) -> None:
        bff = self.contract["bff_boundary"]
        self.assertEqual(
            bff["dynamic_path_exact"],
            "SPFx/Teams -> NaC BFF -> Microsoft Graph REST v1.0",
        )
        self.assertEqual(bff["live_activation_status_exact"], "DEFERRED")
        self.assertEqual(
            bff["identity_source_exact"], "validated Entra access token claims"
        )
        self.assertEqual(
            bff["workspace_site_list_resolution_exact"],
            "server-side allowlist",
        )
        self.assertEqual(
            bff["activation_prerequisites"],
            [
                "existing_public_https_endpoint",
                "existing_delegated_entra_scope",
            ],
        )
        self.assertFalse(
            bff["new_permission_scope_or_credential_change_allowed_in_slice"]
        )

    def test_bilingual_specs_and_plans_share_traceability(self) -> None:
        for path in (DE_SPEC, EN_SPEC, DE_PLAN, EN_PLAN):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                self.assertIn("https://github.com/notariat8/NaC/issues/620", text)
                self.assertIn("notary_team_01", text)
                for acceptance_id in ACCEPTANCE_IDS:
                    self.assertIn(acceptance_id, text)

        for path in (DE_SPEC, EN_SPEC):
            text = path.read_text(encoding="utf-8")
            block = re.search(
                r"```nac-spec-traceability\n(?P<body>.*?)\n```",
                text,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(block)
            assert block is not None
            self.assertIn("spec_id: m365-mvp-test-environment", block.group("body"))
            self.assertIn("delivery_mode: Protected PR", block.group("body"))


if __name__ == "__main__":
    unittest.main()
