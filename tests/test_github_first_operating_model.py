from __future__ import annotations

import unittest
from pathlib import Path

from scripts import validate_governance_sync


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class GitHubFirstOperatingModelGovernanceTest(unittest.TestCase):
    def assert_file_contains(self, relative_path: str, markers: tuple[str, ...]) -> None:
        text = read_repo_file(relative_path)

        for marker in markers:
            with self.subTest(file=relative_path, marker=marker):
                self.assertIn(marker, text)

    def test_process_policy_structurally_defines_github_first_operating_model(self) -> None:
        policy = validate_governance_sync.load_simple_yaml_mapping(
            REPO_ROOT / "policies" / "process-policy.yaml"
        )
        model = policy["github_first_operating_model"]

        self.assertEqual(model["project_owner"], "notariat8")
        self.assertEqual(model["project_title"], "NaC Control Plane")
        self.assertTrue(model["require_leading_issue_for_nontrivial_work"])
        self.assertTrue(model["project_required_for_nontrivial_work"])
        self.assertTrue(model["allow_owner_direct_with_issue_project_trail"])
        self.assertTrue(model["completion_requires_remote_ci_checks"])
        self.assertTrue(model["forbid_secrets_and_matter_data_in_github_surfaces"])

        self.assertEqual(
            model["required_project_fields"],
            [
                "Status",
                "Track",
                "Work Type",
                "Risk Gate",
                "Delivery Mode",
                "Priority",
                "Size",
                "Iteration",
                "Due Date",
            ],
        )
        self.assertEqual(
            model["required_statuses"],
            ["Inbox", "Ready", "In Progress", "Review", "Blocked", "Done"],
        )
        self.assertEqual(
            model["required_views"],
            [
                "Owner Board",
                "Now",
                "Blocked",
                "Governance And Security",
                "Release Readiness",
                "My Agent Work",
            ],
        )
        self.assertEqual(
            model["delivery_modes"],
            ["Owner Direct", "Protected PR", "Sync PR"],
        )
        self.assertEqual(
            model["branch_prefixes"],
            {
                "agent": "agent/<issue-number>-<short-slug>",
                "sync": "sync/<issue-number>-<short-slug>",
                "hotfix": "hotfix/<issue-number>-<short-slug>",
            },
        )

    def test_agent_instruction_surfaces_contain_github_first_markers(self) -> None:
        for relative_path in (
            "AGENTS.md",
        ):
            self.assert_file_contains(
                relative_path,
                (
                    "GitHub-first",
                    "NaC Control Plane",
                    "Issue",
                    "remote_ci_checks",
                ),
            )

    def test_operations_issue_docs_contain_project_field_markers(self) -> None:
        for relative_path in (
            "docs/de/issues/operations.md",
            "docs/en/issues/operations.md",
        ):
            self.assert_file_contains(
                relative_path,
                (
                    "NaC Control Plane",
                    "`Status`",
                    "`Track`",
                    "`Risk Gate`",
                    "`Delivery Mode`",
                    "`Owner Board`",
                    "`Blocked`",
                ),
            )

    def test_operations_issue_docs_document_autonomy_prerequisites_and_blocker_escalation(
        self,
    ) -> None:
        expectations = {
            "docs/en/issues/operations.md": (
                "Autonomy prerequisites",
                "`repo`, `workflow`, `project` and `read:org`",
                "Project owner: `notariat8`",
                "Project URL or number",
                "Delivery-mode rule",
                "Status `Blocked`",
                "missing decision",
                "no silent policy deviation",
            ),
            "docs/de/issues/operations.md": (
                "Autonomie-Voraussetzungen",
                "`repo`, `workflow`, `project` und `read:org`",
                "Project-Owner: `notariat8`",
                "Project-URL oder Project-Nummer",
                "Delivery-Mode-Regel",
                "Status `Blocked`",
                "fehlende Entscheidung",
                "kein stilles Abweichen",
            ),
        }

        for relative_path, markers in expectations.items():
            self.assert_file_contains(relative_path, markers)

    def test_issue_and_pull_request_templates_contain_github_first_markers(self) -> None:
        for relative_path in (
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/feature_request.md",
            ".github/ISSUE_TEMPLATE/compliance_change.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
        ):
            self.assert_file_contains(
                relative_path,
                (
                    "Project:",
                    "Delivery Mode",
                    "Risk Gate",
                    "Validierung",
                    "Secrets/Mandatsdaten",
                ),
            )

    def test_data_protection_policy_contains_github_surface_markers(self) -> None:
        policy = validate_governance_sync.load_simple_yaml_mapping(
            REPO_ROOT / "policies" / "data-protection-policy.yaml"
        )
        github_surfaces = policy["github_surfaces"]

        self.assertTrue(github_surfaces["forbid_secrets_and_matter_data"])
        self.assertEqual(
            github_surfaces["applies_to"],
            ["issues", "pull_requests", "projects", "project_fields", "comments"],
        )


if __name__ == "__main__":
    unittest.main()
