from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class CodexMemoryHooksOperatingModelTests(unittest.TestCase):
    def test_docs_separate_memory_sources_and_shared_truth(self) -> None:
        expectations = {
            "docs/de/operations/codex-memory-hooks-operating-model.md": (
                "Codex Memory",
                "GitHub",
                "Suchindex oder MCP",
                "nicht speichern",
            ),
            "docs/en/operations/codex-memory-hooks-operating-model.md": (
                "Codex Memory",
                "GitHub",
                "Search index or MCP",
                "do not store",
            ),
        }
        for rel_path, markers in expectations.items():
            text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, text)
            self.assertIn("codex-memory-hooks.verification.json", text)
            self.assertIn("validate_codex_memory_hooks_operating_model.py", text)

    def test_hooks_are_opt_in_examples_not_live_config(self) -> None:
        config = (REPO_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        readme = (REPO_ROOT / ".codex" / "hooks" / "README.md").read_text(encoding="utf-8")

        self.assertNotIn("[[hooks.", config)
        self.assertNotIn("[hooks.", config)
        self.assertIn("opt-in", readme)
        self.assertIn("does not activate", readme)
        self.assertIn("validate_codex_memory_hooks_operating_model.py", readme)

    def test_hook_example_is_local_hint_only(self) -> None:
        hook = REPO_ROOT / ".codex" / "hooks" / "pre_tool_use_policy.example.py"
        text = hook.read_text(encoding="utf-8")

        self.assertIn("sys.stdin.read", text)
        self.assertIn("json.dumps", text)
        self.assertNotIn("import subprocess", text)
        self.assertNotIn("import requests", text)
        result = subprocess.run(
            [sys.executable, str(hook)],
            cwd=REPO_ROOT,
            input=json.dumps({"command": "gh pr merge 123"}),
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(any("owner approval" in hint for hint in payload["hints"]))

    def test_agent_context_routes_memory_hooks_verification(self) -> None:
        payload = _read_json("agent-context/index.json")
        categories = {
            category["id"]: category["paths"]
            for layer in payload["layers"]
            for category in layer.get("categories", [])
        }

        self.assertIn("memory_hooks", categories)
        self.assertIn(
            "workflows/verification-contracts/codex-memory-hooks.verification.json",
            categories["memory_hooks"],
        )
        self.assertIn(
            "workflows/verification-contracts/codex-memory-hooks.verification.json",
            payload["verification_contracts"],
        )


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
