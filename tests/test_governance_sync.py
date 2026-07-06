from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import validate_governance_sync


class GovernanceSyncValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_repo_root = validate_governance_sync.REPO_ROOT

    def tearDown(self) -> None:
        validate_governance_sync.REPO_ROOT = self.original_repo_root

    def _write_minimal_repo(self, root: Path, policy_text: str) -> None:
        (root / "policies").mkdir()
        (root / "docs" / "de").mkdir(parents=True)
        (root / "docs" / "en").mkdir(parents=True)
        (root / "policies" / "process-policy.yaml").write_text(
            policy_text,
            encoding="utf-8",
        )
        (root / "docs" / "de" / "regelarchitektur.md").write_text(
            "# Regelarchitektur\n",
            encoding="utf-8",
        )
        (root / "docs" / "en" / "regelarchitektur.md").write_text(
            "# Rule Architecture\n",
            encoding="utf-8",
        )
        (root / "policies" / "data-protection-policy.yaml").write_text(
            "\n".join(
                (
                    "github_surfaces:",
                    "  forbid_secrets_and_matter_data: true",
                    "  applies_to:",
                    "    - issues",
                    "    - pull_requests",
                    "    - projects",
                    "    - project_fields",
                    "    - comments",
                )
            ),
            encoding="utf-8",
        )

    def _minimal_valid_process_policy(self) -> str:
        return "\n".join(
            (
                "change_management:",
                "  delivery_modes:",
                "    protected_pr:",
                "    owner_direct_main:",
                "github_first_operating_model:",
                "  enabled: true",
                "  project_owner: notariat8",
                "  project_title: NaC Control Plane",
                "  project_scope: organization",
                "  project_required_for_nontrivial_work: true",
                "  require_leading_issue_for_nontrivial_work: true",
                "  require_project_fields_for_nontrivial_work: true",
                "  allow_owner_direct_with_issue_project_trail: true",
                "  completion_requires_remote_ci_checks: true",
                "  forbid_secrets_and_matter_data_in_github_surfaces: true",
                "  required_project_fields:",
                "    - Status",
                "    - Track",
                "    - Work Type",
                "    - Risk Gate",
                "    - Delivery Mode",
                "    - Priority",
                "    - Size",
                "    - Iteration",
                "    - Due Date",
                "  required_statuses:",
                "    - Inbox",
                "    - Ready",
                "    - In Progress",
                "    - Review",
                "    - Blocked",
                "    - Done",
                "  required_views:",
                "    - Owner Board",
                "    - Now",
                "    - Blocked",
                "    - Governance And Security",
                "    - Release Readiness",
                "    - My Agent Work",
                "  delivery_modes:",
                "    - Owner Direct",
                "    - Protected PR",
                "    - Sync PR",
                "  branch_prefixes:",
                '    agent: "agent/<issue-number>-<short-slug>"',
                '    sync: "sync/<issue-number>-<short-slug>"',
                '    hotfix: "hotfix/<issue-number>-<short-slug>"',
                "agent_workflows:",
                "  require_plan_review_fix_for_nontrivial_work: true",
                "  require_implementation_review_before_user_acceptance: true",
                "  require_final_response_next_step: true",
                "  require_diagnosis_before_fix_for_repeated_or_unclear_failures: true",
                "  require_full_pr_diff_review_before_merge: true",
                "  routine_read_only_github_oci_checks_do_not_need_owner_approval: true",
                "  parallel_gate_preparation_required_when_independent_inputs_known: true",
                "  codex_parallel_review_default_when_net_benefit_expected: true",
                "  codex_parallel_review_assessment_dimensions:",
                "    - layer_count",
                "    - risk_level",
                "    - independent_review_perspectives",
                "    - validation_surface",
                "    - coordination_cost",
                "  codex_parallel_review_preserve_single_owner_for:",
                "    - secrets",
                "    - oci_write_actions",
                "    - apply_gates",
                "    - release_gates",
                "    - destructive_operations",
                "  require_layer_sync_check_for_data_controller_view_changes: true",
                "  require_error_test_security_review_for_code_reviewer: true",
                "rule_architecture:",
                "  human_explanation_de: docs/de/regelarchitektur.md",
                "  human_explanation_en: docs/en/regelarchitektur.md",
            )
        )

    def test_process_policy_requires_delivery_modes_and_rule_architecture_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = self._minimal_valid_process_policy()
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            self.assertEqual(validate_governance_sync.validate_process_policy_file(), [])

    def test_process_policy_reports_missing_owner_direct_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "github_first_operating_model:",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn("Pflichtabschnitt fehlt in process-policy: owner_direct_main:", errors)

    def test_process_policy_reports_missing_github_first_operating_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "    owner_direct_main:",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn(
            "Pflichtabschnitt fehlt in process-policy: github_first_operating_model:",
            errors,
        )

    def test_process_policy_reports_incomplete_github_first_model_structurally(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "    owner_direct_main:",
                    "github_first_operating_model:",
                    "  enabled: true",
                    "  project_owner: notariat8",
                    "  project_title: NaC Control Plane",
                    "  project_required_for_nontrivial_work: true",
                    "  require_leading_issue_for_nontrivial_work: true",
                    "  allow_owner_direct_with_issue_project_trail: true",
                    "  completion_requires_remote_ci_checks: true",
                    "  forbid_secrets_and_matter_data_in_github_surfaces: true",
                    "  required_project_fields:",
                    "    - Status",
                    "  required_statuses:",
                    "    - Inbox",
                    "  required_views:",
                    "    - Owner Board",
                    "  delivery_modes:",
                    "    - Protected PR",
                    "  branch_prefixes:",
                    '    agent: "agent/<issue-number>-<short-slug>"',
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "github_first_operating_model.required_project_fields.Track",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "github_first_operating_model.required_statuses.Blocked",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "github_first_operating_model.delivery_modes.Owner Direct",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "github_first_operating_model.branch_prefixes.sync",
            errors,
        )

    def test_process_policy_reports_missing_agentic_change_discipline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "    owner_direct_main:",
                    "github_first_operating_model:",
                    "  enabled: true",
                    "  project_owner: notariat8",
                    "  project_title: NaC Control Plane",
                    "  project_scope: organization",
                    "  project_required_for_nontrivial_work: true",
                    "  require_leading_issue_for_nontrivial_work: true",
                    "  require_project_fields_for_nontrivial_work: true",
                    "  allow_owner_direct_with_issue_project_trail: true",
                    "  completion_requires_remote_ci_checks: true",
                    "  forbid_secrets_and_matter_data_in_github_surfaces: true",
                    "  required_project_fields:",
                    "    - Status",
                    "    - Track",
                    "    - Work Type",
                    "    - Risk Gate",
                    "    - Delivery Mode",
                    "    - Priority",
                    "    - Size",
                    "    - Iteration",
                    "    - Due Date",
                    "  required_statuses:",
                    "    - Inbox",
                    "    - Ready",
                    "    - In Progress",
                    "    - Review",
                    "    - Blocked",
                    "    - Done",
                    "  required_views:",
                    "    - Owner Board",
                    "    - Now",
                    "    - Blocked",
                    "    - Governance And Security",
                    "    - Release Readiness",
                    "    - My Agent Work",
                    "  delivery_modes:",
                    "    - Owner Direct",
                    "    - Protected PR",
                    "    - Sync PR",
                    "  branch_prefixes:",
                    '    agent: "agent/<issue-number>-<short-slug>"',
                    '    sync: "sync/<issue-number>-<short-slug>"',
                    '    hotfix: "hotfix/<issue-number>-<short-slug>"',
                    "agent_workflows:",
                    "  require_plan_review_fix_for_nontrivial_work: true",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "agent_workflows.require_implementation_review_before_user_acceptance.true",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "agent_workflows.require_diagnosis_before_fix_for_repeated_or_unclear_failures.true",
            errors,
        )

    def test_process_policy_reports_missing_full_pr_diff_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = self._minimal_valid_process_policy().replace(
                "  require_full_pr_diff_review_before_merge: true\n",
                "",
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn(
            "Pflichtwert fehlt in process-policy: "
            "agent_workflows.require_full_pr_diff_review_before_merge.true",
            errors,
        )

    def test_process_policy_reports_non_mapping_github_first_model(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "    owner_direct_main:",
                    "github_first_operating_model: true",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn(
            "Pflichtabschnitt fehlt in process-policy: "
            "github_first_operating_model must be a mapping",
            errors,
        )

    def test_process_policy_allows_inline_yaml_comments_in_github_first_model(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = self._minimal_valid_process_policy()
            policy_text = policy_text.replace(
                "github_first_operating_model:",
                "github_first_operating_model: # control-plane settings",
            ).replace(
                "  project_required_for_nontrivial_work: true",
                "  project_required_for_nontrivial_work: true # required",
            ).replace(
                "    - Status",
                "    - Status # required",
                1,
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            self.assertEqual(validate_governance_sync.validate_process_policy_file(), [])

    def test_simple_yaml_parser_preserves_quoted_hash_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "quoted-hash.yaml"
            path.write_text(
                "\n".join(
                    (
                        "example:",
                        '  double_quoted: "value # not a comment"',
                        "  single_quoted: 'value # not a comment'",
                    )
                ),
                encoding="utf-8",
            )

            parsed = validate_governance_sync.load_simple_yaml_mapping(path)

        self.assertEqual(
            parsed["example"],
            {
                "double_quoted": "value # not a comment",
                "single_quoted": "value # not a comment",
            },
        )

    def test_data_protection_policy_is_classified_as_policy_file(self) -> None:
        self.assertTrue(
            validate_governance_sync.is_policy_file(
                "policies/data-protection-policy.yaml"
            )
        )

    def test_data_protection_policy_reports_missing_github_surface_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_minimal_repo(root, self._minimal_valid_process_policy())
            (root / "policies" / "data-protection-policy.yaml").write_text(
                "\n".join(
                    (
                        "github_surfaces:",
                        "  forbid_secrets_and_matter_data: false",
                        "  applies_to:",
                        "    - issues",
                    )
                ),
                encoding="utf-8",
            )
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_data_protection_policy_file()

        self.assertIn(
            "Pflichtwert fehlt in data-protection-policy: "
            "github_surfaces.forbid_secrets_and_matter_data.true",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in data-protection-policy: github_surfaces.applies_to.projects",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
