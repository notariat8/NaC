from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

from nac_bff.approved_git_tree import ApprovedGitTreeError, GitApprovedTreeSource


class ApprovedGitTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self._git("init", "--quiet")
        self._git("config", "user.email", "nac-tests@example.invalid")
        self._git("config", "user.name", "NaC Tests")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *argv: str) -> str:
        result = subprocess.run(
            ["/usr/bin/git", "-C", str(self.root), *argv],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip().lower()

    def _commit(self) -> tuple[str, str]:
        self._git("add", "-A")
        self._git("commit", "--quiet", "-m", "approved")
        return self._git("rev-parse", "HEAD"), self._git("rev-parse", "HEAD^{tree}")

    def test_snapshot_reads_approved_blobs_not_dirty_checkout(self) -> None:
        source = self.root / "deploy/runtime/input.txt"
        source.parent.mkdir(parents=True)
        source.write_text("approved\n")
        commit, tree = self._commit()
        source.write_text("dirty-and-unapproved\n")

        first = GitApprovedTreeSource().materialize(
            self.root,
            Path(self.temporary.name) / "snapshot-1",
            approved_commit=commit,
            approved_tree=tree,
        )
        second = GitApprovedTreeSource().materialize(
            self.root,
            Path(self.temporary.name) / "snapshot-2",
            approved_commit=commit,
            approved_tree=tree,
        )

        self.assertEqual(
            (first.root / "deploy/runtime/input.txt").read_text(), "approved\n"
        )
        self.assertEqual(first.manifest_sha256, second.manifest_sha256)
        self.assertEqual(first.file_count, 1)
        self.assertEqual(
            hashlib.sha1(b"blob 9\0approved\n", usedforsecurity=False).hexdigest(),
            self._git("rev-parse", "HEAD:deploy/runtime/input.txt"),
        )

    def test_wrong_tree_is_rejected_before_target_creation(self) -> None:
        (self.root / "input.txt").write_text("approved\n")
        commit, _ = self._commit()
        target = Path(self.temporary.name) / "snapshot"
        with self.assertRaisesRegex(ApprovedGitTreeError, "TREE_MISMATCH"):
            GitApprovedTreeSource().materialize(
                self.root,
                target,
                approved_commit=commit,
                approved_tree="0" * 40,
            )
        self.assertFalse(target.exists())

    def test_symlink_in_approved_tree_is_rejected(self) -> None:
        (self.root / "target.txt").write_text("approved\n")
        (self.root / "link.txt").symlink_to("target.txt")
        commit, tree = self._commit()
        with self.assertRaisesRegex(ApprovedGitTreeError, "TREE_ENTRY_INVALID"):
            GitApprovedTreeSource().materialize(
                self.root,
                Path(self.temporary.name) / "snapshot",
                approved_commit=commit,
                approved_tree=tree,
            )


if __name__ == "__main__":
    unittest.main()
