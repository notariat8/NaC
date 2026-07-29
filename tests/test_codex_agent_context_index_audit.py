from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import scoped_repo_glob
from scripts.validate_codex_agent_context_index_audit import (
    _path_or_glob_matches as index_glob_matches,
)
from scripts.validate_codex_agent_context_operating_model import (
    _path_or_glob_matches as context_glob_matches,
)
from scripts.validate_codex_memory_hooks_operating_model import (
    _path_or_glob_matches as memory_glob_matches,
)
from scripts.validate_codex_subagent_operating_gate import (
    _path_or_glob_matches as subagent_glob_matches,
)


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

    def test_glob_matching_does_not_scan_the_complete_repository_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()
            docs = root / "docs" / "de"
            docs.mkdir(parents=True)
            (docs / "context.md").write_text("context", encoding="utf-8")
            (root / "README-context.md").write_text("root", encoding="utf-8")
            recursive = root / "recursive" / "deep"
            recursive.mkdir(parents=True)
            (recursive / "contract.md").write_text("recursive", encoding="utf-8")
            shallow = root / "shallow"
            shallow.mkdir()
            (shallow / "context.md").write_text("shallow", encoding="utf-8")
            stress = root / "stress"
            for index in range(16):
                stress /= f"level-{index}"
            stress.mkdir(parents=True)
            (stress / "target.md").write_text("target", encoding="utf-8")
            unrelated = root / "ignored" / "deep"
            unrelated.mkdir(parents=True)
            (unrelated / "artifact.bin").write_bytes(b"artifact")

            original_rglob = Path.rglob
            original_scandir = scoped_repo_glob.scandir

            def reject_repository_root_scan(path: Path, pattern: str):
                if path == root:
                    raise AssertionError("repository-wide scan is prohibited")
                return original_rglob(path, pattern)

            def reject_excluded_tree_scan(path: Path):
                if Path(path).name in {".git", "out"}:
                    raise AssertionError("excluded tree traversal is prohibited")
                return original_scandir(path)

            with (
                patch.object(
                    Path,
                    "rglob",
                    autospec=True,
                    side_effect=reject_repository_root_scan,
                ),
                patch.object(
                    scoped_repo_glob,
                    "scandir",
                    side_effect=reject_excluded_tree_scan,
                ),
            ):
                for glob_matches in (
                    index_glob_matches,
                    context_glob_matches,
                    memory_glob_matches,
                    subagent_glob_matches,
                ):
                    with self.subTest(validator=glob_matches.__module__):
                        self.assertTrue(glob_matches("docs/*/*.md", root))
                        self.assertFalse(glob_matches("docs/*/*.json", root))
                        self.assertTrue(glob_matches("README*.md", root))
                        self.assertTrue(glob_matches("*/*.md", root))
                        self.assertTrue(glob_matches("recursive/**/contract.md", root))
                        repeated_recursive = "stress/" + "/".join(["**"] * 16) + "/target.md"
                        self.assertTrue(glob_matches(repeated_recursive, root))
                        self.assertFalse(glob_matches("ignored/empty/**", root))
                        self.assertFalse(glob_matches("../*.md", root))
                        self.assertFalse(glob_matches(str(root / "docs" / "*.md"), root))

                empty = root / "ignored" / "empty"
                empty.mkdir()
                self.assertFalse(index_glob_matches("ignored/empty/**", root))
                self.assertFalse(context_glob_matches("ignored/empty/*", root))
                (empty / "evidence.json").write_text("{}", encoding="utf-8")
                self.assertTrue(index_glob_matches("ignored/empty/**", root))

                outside = root.parent / "outside"
                outside.mkdir()
                (outside / "external.md").write_text("external", encoding="utf-8")
                (root / "link").symlink_to(outside, target_is_directory=True)
                for glob_matches in (
                    index_glob_matches,
                    context_glob_matches,
                    memory_glob_matches,
                    subagent_glob_matches,
                ):
                    with self.subTest(
                        validator=glob_matches.__module__,
                        boundary="outside_symlink",
                    ):
                        self.assertFalse(glob_matches("link/*.md", root))

                linked_file = docs / "linked.md"
                linked_file.symlink_to(outside / "external.md")
                depth = root / "depth" / "de" / "nested"
                depth.mkdir(parents=True)
                (depth / "context.md").write_text("nested", encoding="utf-8")
                generated = root / "out"
                generated.mkdir()
                (generated / "evidence.md").write_text("evidence", encoding="utf-8")
                internal_alias = root / "alias"
                internal_alias.symlink_to(generated, target_is_directory=True)
                git_dir = root / ".git"
                git_dir.mkdir()
                (git_dir / "hidden.md").write_text("hidden", encoding="utf-8")

                for glob_matches in (
                    index_glob_matches,
                    context_glob_matches,
                    memory_glob_matches,
                    subagent_glob_matches,
                ):
                    with self.subTest(
                        validator=glob_matches.__module__,
                        boundary="file_and_generated_filters",
                    ):
                        self.assertTrue(glob_matches("docs/de/context.md", root))
                        self.assertFalse(glob_matches("docs/linked*.md", root))
                        self.assertFalse(glob_matches("docs/linked.md", root))
                        self.assertFalse(glob_matches("alias/evidence.md", root))
                        self.assertFalse(glob_matches("ignored/empty", root))
                        self.assertFalse(glob_matches("depth/*/*.md", root))
                        self.assertTrue(glob_matches("depth/**", root))
                        self.assertFalse(glob_matches("out/*.md", root))
                        self.assertFalse(glob_matches(".git/*.md", root))


def _read_json(rel_path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / rel_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
