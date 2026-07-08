from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexCommandRulesOperatingModelTests(unittest.TestCase):
    def test_policy_declares_green_yellow_red_profiles(self) -> None:
        payload = _read_json("policies/codex-command-rules-policy.json")

        self.assertEqual(payload["schema_version"], "nac.codex-command-rules-policy/v0.1")
        risk_decisions = {item["id"]: item["decision"] for item in payload["risk_levels"]}
        self.assertEqual(risk_decisions["GREEN"], "allow")
        self.assertEqual(risk_decisions["YELLOW"], "prompt")
        self.assertEqual(risk_decisions["RED"], "block")
        profile_ids = {item["id"] for item in payload["permission_profiles"]}
        self.assertIn("green_local_validation", profile_ids)
        self.assertIn("yellow_owner_merge_cleanup", profile_ids)
        self.assertIn("red_destructive_git_and_filesystem", profile_ids)
        self.assertFalse(payload["local_user_config_mutation_allowed_by_repo"])

    def test_default_rules_blocks_red_and_prompts_yellow(self) -> None:
        text = (REPO_ROOT / ".codex/rules/default.rules").read_text(encoding="utf-8")

        self.assertIn('pattern = ["git", "reset", "--hard"]', text)
        self.assertIn('pattern = ["rm", "-rf"]', text)
        self.assertIn('decision = "block"', text)
        self.assertIn('pattern = ["gh", "pr", "merge"]', text)
        self.assertIn('decision = "prompt"', text)
        self.assertIn('pattern = ["git", "status"]', text)
        self.assertIn('decision = "allow"', text)

    def test_verification_contract_requires_command_rule_evidence(self) -> None:
        payload = _read_json("workflows/verification-contracts/codex-command-rules.verification.json")

        self.assertEqual(payload["contract_id"], "verification.codex_command_rules")
        self.assertEqual(payload["thresholds"]["minimum_green_commands"], 8)
        self.assertEqual(payload["thresholds"]["minimum_yellow_commands"], 5)
        self.assertEqual(payload["thresholds"]["minimum_red_commands"], 6)
        self.assertTrue(payload["pass_condition"]["red_profiles_block"])
        self.assertTrue(payload["pass_condition"]["yellow_profiles_prompt"])
        self.assertIn("command_rules_policy", payload["required_evidence"])

    def test_agent_context_routes_command_rules(self) -> None:
        payload = _read_json("agent-context/index.json")

        self.assertIn(
            "workflows/verification-contracts/codex-command-rules.verification.json",
            payload["verification_contracts"],
        )
        categories = {
            category["id"]: category["paths"]
            for layer in payload["layers"]
            for category in layer.get("categories", [])
        }
        self.assertIn("command_rules", categories)
        self.assertIn("policies/codex-command-rules-policy.json", categories["command_rules"])
        self.assertIn(".codex/rules/default.rules", categories["command_rules"])


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
