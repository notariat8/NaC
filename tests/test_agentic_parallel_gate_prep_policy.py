from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class AgenticParallelGatePrepPolicyTests(unittest.TestCase):
    def test_process_policy_codifies_routine_read_only_without_owner_approval(self) -> None:
        policy = read_repo_text("policies/process-policy.yaml")

        self.assertIn(
            "routine_read_only_github_oci_checks_do_not_need_owner_approval: true",
            policy,
        )
        self.assertIn(
            "parallel_gate_preparation_required_when_independent_inputs_known: true",
            policy,
        )
        for gate in (
            "design_approval",
            "release_approval",
            "apply_approval",
            "secret_access",
            "destructive_operation",
        ):
            self.assertIn(gate, policy)

    def test_policy_validator_requires_agentic_read_only_and_parallel_gate_rules(self) -> None:
        validator = read_repo_text("scripts/validate_governance_sync.py")

        self.assertIn(
            '"routine_read_only_github_oci_checks_do_not_need_owner_approval"',
            validator,
        )
        self.assertIn(
            '"parallel_gate_preparation_required_when_independent_inputs_known"',
            validator,
        )

    def test_agent_mirrors_explain_when_not_to_request_owner_approval(self) -> None:
        mirror_paths = (
            "AGENTS.md",
            ".github/copilot-instructions.md",
            ".cursor/rules/02-agent-common-workflows.mdc",
        )

        for path in mirror_paths:
            with self.subTest(path=path):
                content = read_repo_text(path)
                self.assertIn("routine GitHub-/OCI-Read-only-Checks", content)
                self.assertIn("keine Owner-Freigabe", content)
                self.assertIn("unabhängige Gate-Vorbereitungen parallel", content)
                self.assertIn("Design/Release/Apply/Secret/destruktiv", content)


if __name__ == "__main__":
    unittest.main()
