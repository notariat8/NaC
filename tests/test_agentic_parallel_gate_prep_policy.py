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
        )

        for path in mirror_paths:
            with self.subTest(path=path):
                content = read_repo_text(path)
                self.assertIn("routine GitHub-/OCI-Read-only-Checks", content)
                self.assertIn("keine Owner-Freigabe", content)
                self.assertIn("unabhängige Gate-Vorbereitungen parallel", content)
                self.assertIn("Design/Release/Apply/Secret/destruktiv", content)

    def test_no_wait_batch_rule_is_visible_in_runbooks_and_agent_profiles(self) -> None:
        normalized_expectations = {
            "docs/de/operations/m365-mcp-batch-approval.md": (
                "mehrere unabhängige PRs",
                "statt nach jedem kleinen Schritt auf Owner-Input zu warten",
                "Der Agent darf mehrere PRs parallel vorbereiten",
                "Wenn noch ein agentisch ausführbarer Schritt offen ist, arbeitet der Agent weiter",
            ),
            "docs/en/operations/m365-mcp-batch-approval.md": (
                "several independent PRs",
                "instead of waiting for owner input after each small step",
                "The agent may prepare several PRs in parallel",
                "If another agent-executable step is still open, the agent keeps working",
            ),
            ".codex/agents/nac-scope-mapper.toml": (
                "if it does not and tools are available, treat it as work to continue",
                "not as a final waiting state",
            ),
            ".codex/agents/nac-policy-reviewer.toml": (
                "no owner input is needed while an agent-executable next technical step remains open",
            ),
            ".codex/agents/nac-validation-reviewer.toml": (
                "another agent-executable next step is still pending and no owner input is needed",
            ),
            ".codex/agents/nac-docs-parity-reviewer.toml": (
                "agents must continue agent-executable next steps when no owner input is needed",
            ),
        }

        for path, expected_fragments in normalized_expectations.items():
            with self.subTest(path=path):
                content = " ".join(read_repo_text(path).split())
                for fragment in expected_fragments:
                    self.assertIn(fragment, content)


if __name__ == "__main__":
    unittest.main()
