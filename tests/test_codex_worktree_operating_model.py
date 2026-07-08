from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli.cli import main  # noqa: E402
from nac_git.worktree_hygiene import build_worktree_audit  # noqa: E402


class CodexWorktreeOperatingModelTests(unittest.TestCase):
    def test_worktree_audit_reports_cleanup_candidates_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _sample_repo(Path(tmp))
            _git(repo, "branch", "feature/stale")
            _git(repo, "worktree", "add", "../NaC-feature-wt", "-b", "feature/wt")

            payload = build_worktree_audit(repo)

            self.assertEqual(payload["schema_version"], "nac.codex-worktree-audit/v0.1")
            self.assertEqual(payload["status"], "NEEDS_CLEANUP")
            self.assertFalse(payload["summary"]["destructive_actions_executed"])
            self.assertFalse(payload["summary"]["github_api_used"])
            self.assertFalse(payload["summary"]["network_used"])
            self.assertFalse(payload["summary"]["stores_secrets"])
            self.assertGreaterEqual(payload["summary"]["extra_worktree_count"], 1)
            candidate_targets = {item["target"] for item in payload["cleanup_candidates"]}
            self.assertIn("feature/stale", candidate_targets)
            self.assertTrue(any(target.endswith("NaC-feature-wt") for target in candidate_targets))
            for candidate in payload["cleanup_candidates"]:
                self.assertTrue(candidate["owner_gate_required"])
                self.assertFalse(candidate["destructive_action_executed"])

    def test_cli_worktree_audit_returns_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = _sample_repo(Path(tmp))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                rc = main(["--repo-root", str(repo), "git", "worktree-audit", "--format", "json"])

            self.assertEqual(rc, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["schema_version"], "nac.codex-worktree-audit/v0.1")
            self.assertEqual(payload["summary"]["repo_root"], str(repo))
            self.assertFalse(payload["summary"]["destructive_actions_executed"])


def _sample_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "codex@example.invalid")
    _git(repo, "config", "user.name", "Codex")
    (repo / "pyproject.toml").write_text("[project]\nname = \"sample\"\n", encoding="utf-8")
    (repo / "README.md").write_text("# Sample\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "Initial commit")
    return repo


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, text=True, capture_output=True)


if __name__ == "__main__":
    unittest.main()

