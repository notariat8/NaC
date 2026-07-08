from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexAgentContextOperatingModelTests(unittest.TestCase):
    def test_agent_context_index_has_progressive_disclosure_layers(self) -> None:
        payload = _read_json("agent-context/index.json")

        self.assertEqual(payload["schema_version"], "nac.agent-context-index/v0.1")
        layer_ids = {item["id"] for item in payload["layers"]}
        self.assertEqual(layer_ids, {"always_on", "scoped", "on_demand", "runtime"})
        self.assertTrue(payload["guardrails"]["root_agents_md_is_router"])
        self.assertFalse(payload["guardrails"]["real_mandate_data_allowed"])
        self.assertFalse(payload["guardrails"]["secrets_allowed"])
        categories = {
            category["id"]
            for layer in payload["layers"]
            for category in layer.get("categories", [])
        }
        self.assertGreaterEqual(categories, {"maps", "history", "guardrails", "command_rules", "memory_hooks"})

    def test_verification_contract_declares_definition_of_done(self) -> None:
        payload = _read_json("workflows/verification-contracts/codex-agent-context.verification.json")

        self.assertEqual(payload["schema_version"], "nac.verification-contract/v0.1")
        for field in (
            "applies_when",
            "required_context",
            "checks",
            "invariants",
            "thresholds",
            "required_evidence",
            "pass_condition",
            "failure_behavior",
        ):
            self.assertIn(field, payload)
        self.assertTrue(payload["pass_condition"]["all_checks_pass"])
        self.assertEqual(payload["failure_behavior"]["quality_gate_failure"], "block_completion")
        self.assertEqual(payload["thresholds"]["max_agent_threads"], 6)
        self.assertEqual(payload["thresholds"]["max_agent_depth"], 1)

    def test_hooks_are_examples_not_live_config(self) -> None:
        config = (REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        self.assertNotIn("[[hooks.", config)
        self.assertNotIn("[hooks.", config)
        hook_example = (REPO_ROOT / ".codex" / "hooks" / "pre_tool_use_policy.example.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Branch cleanup is destructive", hook_example)
        self.assertNotIn("subprocess.run", hook_example)


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
