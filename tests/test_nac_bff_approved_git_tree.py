from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import nac_bff.approved_git_tree as approved_git_tree
from nac_bff.approved_git_tree import ApprovedGitTreeError, GitApprovedTreeSource


class ApprovedGitTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        self._git("init", "--quiet")
        self._git("config", "user.email", "nac-tests@example.invalid")
        self._git("config", "user.name", "NaC Tests")
        self._git("config", "core.autocrlf", "false")
        self._git("config", "core.eol", "lf")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *argv: str) -> str:
        result = subprocess.run(
            [str(approved_git_tree._GIT), "-C", str(self.root), *argv],
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
        source.write_bytes(b"approved\n")
        commit, tree = self._commit()
        source.write_bytes(b"dirty-and-unapproved\n")

        with patch.object(
            approved_git_tree.subprocess, "run", wraps=subprocess.run
        ) as git_run:
            inspection = GitApprovedTreeSource().inspect(
                self.root,
                approved_commit=commit,
                approved_tree=tree,
            )
        commands = [call.args[0] for call in git_run.call_args_list]
        if os.name != "nt":
            self.assertTrue(all("--no-replace-objects" in cmd for cmd in commands))
            self.assertIn(
                ["ls-tree", "-r", "-z", "--full-tree", tree],
                [cmd[cmd.index("-C") + 2:] for cmd in commands],
            )
            self.assertIn(
                ["archive", "--format=tar", tree],
                [cmd[cmd.index("-C") + 2:] for cmd in commands],
            )
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
        self.assertEqual(inspection.manifest_sha256, first.manifest_sha256)
        self.assertEqual(inspection.file_count, 1)
        self.assertEqual(
            inspection.file_sha256["deploy/runtime/input.txt"],
            hashlib.sha256(b"approved\n").hexdigest(),
        )
        self.assertEqual(first.file_count, 1)
        self.assertEqual(
            hashlib.sha1(b"blob 9\0approved\n", usedforsecurity=False).hexdigest(),
            self._git("rev-parse", "HEAD:deploy/runtime/input.txt"),
        )

    def test_archive_blob_bytes_must_match_listed_blob_ids(self) -> None:
        source = self.root / "input.txt"
        source.write_text("approved\n")
        commit, tree = self._commit()
        with patch.object(
            approved_git_tree,
            "_read_archive",
            return_value={"input.txt": b"different\n"},
        ), self.assertRaisesRegex(ApprovedGitTreeError, "BLOB_MISMATCH"):
            GitApprovedTreeSource().inspect(
                self.root,
                approved_commit=commit,
                approved_tree=tree,
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
        if os.name == "nt":
            link_payload = self.root / "link-payload.txt"
            link_payload.write_text("target.txt", encoding="utf-8")
            self._git("add", "target.txt")
            blob = self._git("hash-object", "-w", str(link_payload))
            self._git(
                "update-index",
                "--add",
                "--cacheinfo",
                f"120000,{blob},link.txt",
            )
            self._git("commit", "--quiet", "-m", "approved")
            commit = self._git("rev-parse", "HEAD")
            tree = self._git("rev-parse", "HEAD^{tree}")
        else:
            (self.root / "link.txt").symlink_to("target.txt")
            commit, tree = self._commit()
        with self.assertRaisesRegex(ApprovedGitTreeError, "TREE_ENTRY_INVALID"):
            GitApprovedTreeSource().materialize(
                self.root,
                Path(self.temporary.name) / "snapshot",
                approved_commit=commit,
                approved_tree=tree,
            )

    @unittest.skipUnless(os.name == "nt", "Windows junction contract")
    def test_materialization_rejects_junction_ancestor(self) -> None:
        (self.root / "input.txt").write_bytes(b"approved\n")
        commit, tree = self._commit()
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        junction = Path(self.temporary.name) / "junction"
        completed = subprocess.run(
            [
                "cmd.exe",
                "/d",
                "/c",
                "mklink",
                "/J",
                str(junction),
                str(outside),
            ],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        with self.assertRaisesRegex(
            ApprovedGitTreeError,
            "SNAPSHOT_WRITE_FAILED",
        ):
            GitApprovedTreeSource().materialize(
                self.root,
                junction / "snapshot",
                approved_commit=commit,
                approved_tree=tree,
            )
        self.assertFalse((outside / "snapshot").exists())


if __name__ == "__main__":
    unittest.main()
