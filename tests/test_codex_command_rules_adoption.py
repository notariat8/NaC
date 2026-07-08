from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexCommandRulesAdoptionTests(unittest.TestCase):
    def test_adoption_policy_lists_batch_docs_and_agent_profiles(self) -> None:
        payload = _read_json("policies/codex-command-rules-policy.json")
        adoption = payload["adoption_smoke"]

        self.assertIn("docs/de/operations/m365-mcp-batch-approval.md", adoption["required_docs"])
        self.assertIn("docs/en/operations/m365-mcp-batch-approval.md", adoption["required_docs"])
        self.assertIn("docs/de/runbooks/m365-cli-admin-accelerator.md", adoption["required_docs"])
        self.assertIn("docs/en/runbooks/m365-cli-admin-accelerator.md", adoption["required_docs"])
        self.assertIn(".codex/agents/nac-validation-reviewer.toml", adoption["required_agent_profiles"])
        self.assertIn(".codex/agents/nac-policy-reviewer.toml", adoption["required_agent_profiles"])
        self.assertGreaterEqual(set(adoption["required_markers"]), {"GREEN", "YELLOW", "RED"})

    def test_batch_docs_reference_command_rules_and_owner_gates(self) -> None:
        for rel_path in (
            "docs/de/operations/m365-mcp-batch-approval.md",
            "docs/en/operations/m365-mcp-batch-approval.md",
            "docs/de/runbooks/m365-cli-admin-accelerator.md",
            "docs/en/runbooks/m365-cli-admin-accelerator.md",
        ):
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            self.assertIn("codex-command-rules-policy.json", text)
            self.assertIn(".codex/rules/default.rules", text)
            self.assertIn("GREEN", text)
            self.assertIn("YELLOW", text)
            self.assertIn("RED", text)
            self.assertIn("owner", text.lower())

    def test_agent_profiles_reference_command_rule_boundary(self) -> None:
        for profile in (REPO_ROOT / ".codex/agents").glob("*.toml"):
            text = profile.read_text(encoding="utf-8")
            self.assertIn("sandbox_mode = \"read-only\"", text)
            self.assertIn("policies/codex-command-rules-policy.json", text)
            self.assertIn(".codex/rules/default.rules", text)
            self.assertIn("GREEN", text)
            self.assertIn("YELLOW", text)
            self.assertIn("RED", text)


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
