from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import validate_agent_authentication_boundary


REPO_ROOT = Path(__file__).resolve().parents[1]


class AgentAuthenticationBoundaryTest(unittest.TestCase):
    def test_repository_authentication_boundary_is_valid(self) -> None:
        self.assertEqual(validate_agent_authentication_boundary.validate(REPO_ROOT), [])

    def test_prior_login_authorization_cannot_be_reused(self) -> None:
        policy_text = (REPO_ROOT / "policies" / "process-policy.yaml").read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "policies").mkdir()
            (root / "docs" / "en" / "superpowers" / "specs").mkdir(parents=True)
            (root / "AGENTS.md").write_text(
                (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "policies" / "process-policy.yaml").write_text(
                policy_text.replace(
                    "prior_login_authorization_reusable: false",
                    "prior_login_authorization_reusable: true",
                ),
                encoding="utf-8",
            )
            spec_target = (
                root
                / "docs"
                / "en"
                / "superpowers"
                / "specs"
                / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md"
            )
            spec_target.write_text(
                (
                    REPO_ROOT
                    / "docs"
                    / "en"
                    / "superpowers"
                    / "specs"
                    / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            errors = validate_agent_authentication_boundary.validate(root)

        self.assertIn(
            "process-policy github_authentication_boundary."
            "prior_login_authorization_reusable must equal False",
            errors,
        )

    def test_function8_login_request_must_name_exact_account(self) -> None:
        policy_text = (REPO_ROOT / "policies" / "process-policy.yaml").read_text(
            encoding="utf-8"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "policies").mkdir()
            (root / "docs" / "en" / "superpowers" / "specs").mkdir(parents=True)
            (root / "AGENTS.md").write_text(
                (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "policies" / "process-policy.yaml").write_text(
                policy_text.replace(
                    "function8_login_request_must_name_account: true",
                    "function8_login_request_must_name_account: false",
                ),
                encoding="utf-8",
            )
            spec_target = (
                root
                / "docs"
                / "en"
                / "superpowers"
                / "specs"
                / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md"
            )
            spec_target.write_text(
                (
                    REPO_ROOT
                    / "docs"
                    / "en"
                    / "superpowers"
                    / "specs"
                    / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md"
                ).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            errors = validate_agent_authentication_boundary.validate(root)

        self.assertIn(
            "process-policy github_authentication_boundary."
            "function8_login_request_must_name_account must equal True",
            errors,
        )

    def test_issue746_runtime_rejects_reintroduced_gh_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in (
                Path("policies/process-policy.yaml"),
                Path("docs/en/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md"),
                Path("src/nac_cli/cli.py"),
                Path("src/nac_bff/issue746_reconciliation_gate.py"),
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                if relative == Path("src/nac_cli/cli.py"):
                    text += "\nissue746_github_reader = GitHubApprovalVerifier(\n"
                target.write_text(text, encoding="utf-8")
            (root / "AGENTS.md").write_text(
                (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )

            errors = validate_agent_authentication_boundary.validate(root)

        self.assertTrue(
            any("forbidden marker found" in error for error in errors), errors
        )


if __name__ == "__main__":
    unittest.main()
