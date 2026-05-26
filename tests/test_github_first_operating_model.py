from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo_file(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


class GitHubFirstOperatingModelGovernanceTest(unittest.TestCase):
    def assert_file_contains(self, relative_path: str, markers: tuple[str, ...]) -> None:
        text = read_repo_file(relative_path)

        for marker in markers:
            with self.subTest(file=relative_path, marker=marker):
                self.assertIn(marker, text)

    def test_process_policy_contains_github_first_operating_model_markers(self) -> None:
        self.assert_file_contains(
            "policies/process-policy.yaml",
            (
                "github_first_operating_model:",
                "project_owner: notariat8",
                "project_title: NaC Control Plane",
                "require_leading_issue_for_nontrivial_work: true",
                "project_required_for_nontrivial_work: true",
                "allow_owner_direct_with_issue_project_trail: true",
                "completion_requires_remote_ci_checks: true",
                "forbid_secrets_and_matter_data_in_github_surfaces: true",
                "- Status",
                "- Track",
                "- Work Type",
                "- Risk Gate",
                "- Delivery Mode",
            ),
        )

    def test_agent_instruction_surfaces_contain_github_first_markers(self) -> None:
        for relative_path in (
            "AGENTS.md",
            ".github/copilot-instructions.md",
            ".cursor/rules/00-core-governance.mdc",
            ".cursor/rules/02-agent-common-workflows.mdc",
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
        self.assert_file_contains(
            "policies/data-protection-policy.yaml",
            (
                "github_surfaces:",
                "forbid_secrets_and_matter_data: true",
                "- issues",
                "- pull_requests",
                "- projects",
            ),
        )


if __name__ == "__main__":
    unittest.main()
