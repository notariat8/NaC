from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexAgentContextIndexAuditTests(unittest.TestCase):
    def test_index_crosslinks_all_codex_operating_gates(self) -> None:
        payload = _read_json("agent-context/index.json")
        categories = {
            category["id"]: set(category["paths"])
            for layer in payload["layers"]
            for category in layer.get("categories", [])
        }

        expected = {
            "worktree_operating_model": {
                "docs/de/operations/codex-worktree-operating-model.md",
                "docs/en/operations/codex-worktree-operating-model.md",
                "scripts/validate_codex_worktree_operating_model.py",
                "tests/test_codex_worktree_operating_model.py",
                "workflows/verification-contracts/codex-worktree-operating-model.verification.json",
            },
            "subagent_operating_gate": {
                "agent-context/subagent-registry.json",
                "scripts/validate_codex_subagent_operating_gate.py",
                "tests/test_codex_subagent_operating_gate.py",
                "workflows/verification-contracts/codex-subagent-operating-gate.verification.json",
            },
            "memory_hooks": {
                ".codex/hooks/README.md",
                "scripts/validate_codex_memory_hooks_operating_model.py",
                "tests/test_codex_memory_hooks_operating_model.py",
                "workflows/verification-contracts/codex-memory-hooks.verification.json",
            },
            "command_rules": {
                ".codex/rules/default.rules",
                "scripts/validate_codex_command_rules_operating_model.py",
                "scripts/validate_codex_command_rules_adoption.py",
                "workflows/verification-contracts/codex-command-rules.verification.json",
            },
            "codex_5h_batch_run_envelope": {
                "docs/de/operations/codex-5h-batch-run-envelope.md",
                "docs/en/operations/codex-5h-batch-run-envelope.md",
                "scripts/validate_codex_5h_batch_run_envelope.py",
                "tests/test_codex_5h_batch_run_envelope.py",
                "workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json",
            },
        }
        for category_id, required_paths in expected.items():
            self.assertIn(category_id, categories)
            self.assertGreaterEqual(categories[category_id], required_paths)

    def test_index_lists_verification_contracts_for_crosslinked_gates(self) -> None:
        payload = _read_json("agent-context/index.json")
        contracts = set(payload["verification_contracts"])

        self.assertGreaterEqual(
            contracts,
            {
                "workflows/verification-contracts/codex-agent-context-index-audit.verification.json",
                "workflows/verification-contracts/codex-worktree-operating-model.verification.json",
                "workflows/verification-contracts/codex-subagent-operating-gate.verification.json",
                "workflows/verification-contracts/codex-memory-hooks.verification.json",
                "workflows/verification-contracts/codex-command-rules.verification.json",
                "workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json",
            },
        )

    def test_contracts_verify_includes_compact_index_audit(self) -> None:
        text = (REPO_ROOT / "src/nac_cli/cli.py").read_text(encoding="utf-8")

        self.assertIn("Codex Agent Context Index Audit", text)
        self.assertIn("scripts/validate_codex_agent_context_index_audit.py", text)
        self.assertIn("scripts/validate_codex_worktree_operating_model.py", text)
        self.assertIn("scripts/validate_codex_5h_batch_run_envelope.py", text)


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
