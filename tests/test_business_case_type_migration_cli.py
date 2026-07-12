from __future__ import annotations

from copy import deepcopy
import fcntl
import os
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli
from notary_kg import business_case_type_migration_runner as runner
from notary_kg.business_case_type_migration_runner import (
    MigrationContractError,
    RepositoryStateError,
    read_repository_head,
    run_offline_migration,
)
from notary_kg.cli import main

SUMMARY_KEYS = {
    "status",
    "readiness_scope",
    "live_cutover_status",
    "allowed_live_calls",
    "allowed_tenant_writes",
    "reason_codes",
    "class_counts",
    "top_level_hashes",
}



class RepositoryHeadTests(unittest.TestCase):
    def assert_unavailable(self, root: Path) -> None:
        with self.assertRaisesRegex(RepositoryStateError, "repository_state_unavailable"):
            read_repository_head(root)

    def test_reads_main_loose_packed_and_detached_heads(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git_dir = root / ".git"
            (git_dir / "refs/heads").mkdir(parents=True)
            loose = "a" * 40
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (git_dir / "refs/heads/main").write_text(loose + "\n", encoding="ascii")
            self.assertEqual(read_repository_head(root), loose)

            (git_dir / "refs/heads/main").unlink()
            packed = "b" * 40
            (git_dir / "packed-refs").write_text(
                f"# pack-refs with: peeled fully-peeled\n{packed} refs/heads/main\n",
                encoding="ascii",
            )
            self.assertEqual(read_repository_head(root), packed)

            detached = "c" * 40
            (git_dir / "HEAD").write_text(detached + "\n", encoding="ascii")
            self.assertEqual(read_repository_head(root), detached)

    def test_fixture_reader_stays_bound_to_open_directory_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture_dir = root / runner.FIXTURE_ROOT
            fixture_dir.mkdir(parents=True)
            fixture = fixture_dir / "fixture.json"
            fixture.write_text('{"source":"inside"}', encoding="utf-8")
            outside = root / "outside"
            outside.mkdir()
            (outside / "fixture.json").write_text('{"source":"outside"}', encoding="utf-8")
            original_read = runner._read_file_at
            swapped = False

            def swap_then_read(
                directory_fd: int,
                name: str,
                *,
                encoding: str,
                max_bytes: int = runner._MAX_ADMIN_FILE_BYTES,
            ) -> str:
                nonlocal swapped
                if name == "fixture.json" and not swapped:
                    moved = root / "opened-fixture-dir"
                    fixture_dir.rename(moved)
                    fixture_dir.symlink_to(outside, target_is_directory=True)
                    swapped = True
                return original_read(
                    directory_fd,
                    name,
                    encoding=encoding,
                    max_bytes=max_bytes,
                )

            with patch.object(runner, "_read_file_at", side_effect=swap_then_read):
                payload = runner._read_fixture_object(
                    root,
                    runner.FIXTURE_ROOT / "fixture.json",
                )

            self.assertTrue(swapped)
            self.assertEqual(payload, {"source": "inside"})

    def test_fixture_and_git_metadata_reads_are_bounded_before_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture_dir = root / runner.FIXTURE_ROOT
            fixture_dir.mkdir(parents=True)
            fixture = fixture_dir / "oversized.json"
            fixture.write_bytes(b"x" * (runner._MAX_FIXTURE_BYTES + 1))
            with self.assertRaisesRegex(runner.MigrationValidationError, "fixture_invalid"):
                runner._read_fixture_object(root, runner.FIXTURE_ROOT / fixture.name)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            (root / ".git/HEAD").write_bytes(
                b"x" * (runner._MAX_ADMIN_FILE_BYTES + 1)
            )
            self.assert_unavailable(root)

    def test_reads_valid_linked_worktree_packed_ref(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "worktree"
            root.mkdir()
            common = Path(temp_dir) / "repository/.git"
            worktree_git = common / "worktrees/wt"
            worktree_git.mkdir(parents=True)
            commit = "d" * 40
            (root / ".git").write_text(f"gitdir: {worktree_git}\n", encoding="utf-8")
            (worktree_git / "gitdir").write_text(str(root / ".git") + "\n", encoding="utf-8")
            (worktree_git / "HEAD").write_text("ref: refs/heads/feature\n", encoding="ascii")
            (worktree_git / "commondir").write_text("../..\n", encoding="ascii")
            (common / "packed-refs").write_text(
                f"{commit} refs/heads/feature\n", encoding="ascii"
            )
            self.assertEqual(read_repository_head(root), commit)

    def test_rejects_symlinked_git_head_ref_and_packed_refs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            target = base / "target"
            (target / "refs/heads").mkdir(parents=True)
            (target / "HEAD").write_text("a" * 40 + "\n", encoding="ascii")
            root = base / "dot-git-link"
            root.mkdir()
            (root / ".git").symlink_to(target, target_is_directory=True)
            self.assert_unavailable(root)

            for metadata in ("HEAD", "refs", "packed-refs"):
                with self.subTest(metadata=metadata):
                    repo = base / metadata
                    git_dir = repo / ".git"
                    git_dir.mkdir(parents=True)
                    outside = base / f"outside-{metadata.replace('/', '-')}"
                    if metadata == "HEAD":
                        outside.write_text("b" * 40 + "\n", encoding="ascii")
                        (git_dir / "HEAD").symlink_to(outside)
                    elif metadata == "refs":
                        (outside / "heads").mkdir(parents=True)
                        (outside / "heads/main").write_text("c" * 40 + "\n", encoding="ascii")
                        (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
                        (git_dir / "refs").symlink_to(outside, target_is_directory=True)
                    else:
                        outside.write_text("d" * 40 + " refs/heads/main\n", encoding="ascii")
                        (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
                        (git_dir / "packed-refs").symlink_to(outside)
                    self.assert_unavailable(repo)

    def test_loose_ref_read_stays_bound_to_opened_directory_components(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            git_dir = root / ".git"
            refs = git_dir / "refs"
            (refs / "heads").mkdir(parents=True)
            expected = "a" * 40
            substituted = "b" * 40
            (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (refs / "heads/main").write_text(expected + "\n", encoding="ascii")

            original_open = runner.os.open
            replaced = False

            def substitute_refs(path: object, flags: int, *args: object, **kwargs: object) -> int:
                nonlocal replaced
                if path == "main" and not replaced:
                    replaced = True
                    refs.rename(git_dir / "refs-original")
                    (refs / "heads").mkdir(parents=True)
                    (refs / "heads/main").write_text(substituted + "\n", encoding="ascii")
                return original_open(path, flags, *args, **kwargs)

            with patch.object(runner.os, "open", side_effect=substitute_refs):
                self.assertEqual(read_repository_head(root), expected)
            self.assertTrue(replaced)

    def test_rejects_linked_worktree_spoofed_layout_and_relationships(self) -> None:
        def linked_layout(base: Path) -> tuple[Path, Path, Path]:
            root = base / "worktree"
            root.mkdir()
            common = base / "repository/.git"
            admin = common / "worktrees/wt"
            admin.mkdir(parents=True)
            (root / ".git").write_text(f"gitdir: {admin}\n", encoding="utf-8")
            (admin / "gitdir").write_text(str(root / ".git") + "\n", encoding="utf-8")
            (admin / "commondir").write_text("../..\n", encoding="ascii")
            (admin / "HEAD").write_text("e" * 40 + "\n", encoding="ascii")
            return root, common, admin

        for spoof in (
            "outside-worktrees",
            "wrong-backlink",
            "wrong-commondir",
            "symlink-backlink",
            "symlink-commondir",
            "symlink-common-dir",
            "symlink-admin-dir",
        ):
            with self.subTest(spoof=spoof), tempfile.TemporaryDirectory() as temp_dir:
                root, common, admin = linked_layout(Path(temp_dir))
                if spoof == "outside-worktrees":
                    outside = common / "admin/wt"
                    outside.parent.mkdir(parents=True)
                    admin.rename(outside)
                    (root / ".git").write_text(f"gitdir: {outside}\n", encoding="utf-8")
                elif spoof == "wrong-backlink":
                    (admin / "gitdir").write_text(str(root / "spoof") + "\n", encoding="utf-8")
                elif spoof == "wrong-commondir":
                    (admin / "commondir").write_text("..\n", encoding="ascii")
                elif spoof == "symlink-common-dir":
                    real_common = common.parent / "real.git"
                    common.rename(real_common)
                    common.symlink_to(real_common, target_is_directory=True)
                elif spoof == "symlink-admin-dir":
                    real_admin = admin.parent / "real-wt"
                    admin.rename(real_admin)
                    admin.symlink_to(real_admin, target_is_directory=True)
                else:
                    metadata = "gitdir" if spoof == "symlink-backlink" else "commondir"
                    outside = Path(temp_dir) / f"spoof-{metadata}"
                    outside.write_text(
                        (str(root / ".git") if metadata == "gitdir" else "../..") + "\n",
                        encoding="utf-8",
                    )
                    (admin / metadata).unlink()
                    (admin / metadata).symlink_to(outside)
                self.assert_unavailable(root)

    def test_rejects_unsafe_refs_unborn_and_malformed_packed_metadata(self) -> None:
        unsafe_refs = (
            "refs/heads/../escape",
            "refs/heads/.hidden",
            "refs/heads/main.lock",
            "refs/heads/has space",
            "refs/heads/name@{1}",
        )
        for ref in unsafe_refs:
            with self.subTest(ref=ref), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                (root / ".git").mkdir()
                (root / ".git/HEAD").write_text(f"ref: {ref}\n", encoding="ascii")
                self.assert_unavailable(root)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            (root / ".git/HEAD").write_text("ref: refs/heads/main\n", encoding="ascii")
            (root / ".git/packed-refs").write_text(
                "f" * 40 + " refs/heads/main extra\n", encoding="ascii"
            )
            self.assert_unavailable(root)


class MigrationCliTests(unittest.TestCase):
    def test_ready_and_blocked_fixtures_run_with_temp_isolated_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ready_rc, ready = run_offline_migration(
                REPO_ROOT,
                fixture=Path("tests/fixtures/business-case-type-migration/clean-ready.fixture.json"),
                quarantine_state=root / "quarantine",
                output=root / "ready.json",
                artifact_root=root,
            )
            blocked_rc, blocked = run_offline_migration(
                REPO_ROOT,
                fixture=Path("tests/fixtures/business-case-type-migration/all-classes-blocked.fixture.json"),
                quarantine_state=root / "quarantine",
                output=root / "blocked.json",
                artifact_root=root,
            )
            self.assertEqual((ready_rc, ready["status"]), (0, "READY"))
            self.assertEqual((blocked_rc, blocked["status"]), (2, "BLOCKED"))
            self.assertEqual(set(blocked), SUMMARY_KEYS)
            self.assertEqual(set(blocked["class_counts"].values()), {1})
            self.assertEqual(
                set(blocked["top_level_hashes"]),
                {
                    "manifest_hash",
                    "mapping_hash",
                    "profile_evaluation_hash",
                    "readiness_evidence_hash",
                },
            )
            self.assertEqual(len(list((root / "quarantine/records").glob("*.json"))), 5)
            ready_artifact = json.loads((root / "ready.json").read_text(encoding="utf-8"))
            self.assertEqual(
                ready["top_level_hashes"]["readiness_evidence_hash"],
                ready_artifact["readiness_evidence_anchor"]["readiness_evidence_hash"],
            )
            self.assertEqual(
                ready_artifact["readiness"]["readiness_evidence_hash"],
                ready_artifact["readiness_evidence_anchor"]["readiness_evidence_hash"],
            )

    def test_runner_holds_quarantine_flock_through_output_commit(self) -> None:
        real_write = runner.write_redacted_output
        lock_was_held = False

        def assert_locked_then_write(output_path, payload, *, allowed_root):
            nonlocal lock_was_held
            lock_path = artifact_root / "quarantine/.quarantine.lock"
            descriptor = os.open(lock_path, os.O_RDONLY)
            try:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_was_held = True
            finally:
                os.close(descriptor)
            return real_write(output_path, payload, allowed_root=allowed_root)

        with tempfile.TemporaryDirectory() as temp_dir:
            artifact_root = Path(temp_dir)
            with patch.object(
                runner,
                "write_redacted_output",
                side_effect=assert_locked_then_write,
            ):
                rc, _summary = run_offline_migration(
                    REPO_ROOT,
                    fixture=Path(
                        "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
                    ),
                    quarantine_state=artifact_root / "quarantine",
                    output=artifact_root / "result.json",
                    artifact_root=artifact_root,
                )

        self.assertEqual(rc, 0)
        self.assertTrue(lock_was_held)

    def test_existing_append_only_quarantine_blocks_later_clean_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            blocked_rc, _blocked = run_offline_migration(
                REPO_ROOT,
                fixture=Path("tests/fixtures/business-case-type-migration/all-classes-blocked.fixture.json"),
                quarantine_state=root / "quarantine",
                output=root / "blocked.json",
                artifact_root=root,
            )
            clean_rc, clean = run_offline_migration(
                REPO_ROOT,
                fixture=Path("tests/fixtures/business-case-type-migration/clean-ready.fixture.json"),
                quarantine_state=root / "quarantine",
                output=root / "clean-after-blocked.json",
                artifact_root=root,
            )

        self.assertEqual(blocked_rc, 2)
        self.assertEqual(clean_rc, 2)
        self.assertEqual(clean["status"], "BLOCKED")
        self.assertIn("quarantine_not_empty", clean["reason_codes"])

    def test_readiness_uses_independent_post_scan_snapshots(self) -> None:
        fixture_path = (
            REPO_ROOT / "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
        )
        changed_bundle = deepcopy(json.loads(fixture_path.read_text(encoding="utf-8")))
        changed_bundle["post_scan_registry_snapshot"]["rows"][0]["selectable"] = False

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            runner, "_read_fixture_object", return_value=changed_bundle
        ):
            root = Path(temp_dir)
            rc, summary = run_offline_migration(
                REPO_ROOT,
                fixture=Path(
                    "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
                ),
                quarantine_state=root / "quarantine",
                output=root / "result.json",
                artifact_root=root,
            )

        self.assertEqual(rc, 2)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertEqual(summary["reason_codes"], ["scan_unstable"])

    def test_stale_fixture_catalog_fails_before_artifact_persistence(self) -> None:
        fixture_path = (
            REPO_ROOT / "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
        )
        stale_fixture = deepcopy(json.loads(fixture_path.read_text(encoding="utf-8")))
        stale_fixture["catalog_version"] = "stale-catalog"

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            runner, "_read_fixture_object", return_value=stale_fixture
        ):
            artifact_root = Path(temp_dir)
            with self.assertRaisesRegex(runner.MigrationValidationError, "fixture_invalid"):
                run_offline_migration(
                    REPO_ROOT,
                    fixture=Path(
                        "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
                    ),
                    quarantine_state=artifact_root / "quarantine",
                    output=artifact_root / "result.json",
                    artifact_root=artifact_root,
                )
            self.assertEqual(list(artifact_root.rglob("*")), [])

    def test_candidate_binding_drift_fails_before_artifact_persistence(self) -> None:
        original_read = runner._read_object
        registry_path = REPO_ROOT / runner.CANDIDATES_PATH
        baseline = original_read(registry_path)

        for defect in ("ids", "versions"):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as temp_dir:
                candidate_registry = deepcopy(baseline)
                if defect == "ids":
                    candidate_registry["candidates"][0]["candidate_id"] = "arbitrary-current"
                else:
                    candidate_registry["candidates"][1]["contract_version"] = "v9"

                def read_object(path: Path) -> dict[str, object]:
                    if path == registry_path:
                        return candidate_registry
                    return original_read(path)

                artifact_root = Path(temp_dir)
                with patch.object(runner, "_read_object", side_effect=read_object):
                    with self.assertRaisesRegex(MigrationContractError, "contract_invalid"):
                        run_offline_migration(
                            REPO_ROOT,
                            fixture=Path(
                                "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
                            ),
                            quarantine_state=artifact_root / "quarantine",
                            output=artifact_root / "result.json",
                            artifact_root=artifact_root,
                        )
                self.assertEqual(list(artifact_root.rglob("*")), [])

    def test_candidate_shape_fails_before_any_artifact_is_persisted(self) -> None:
        original_read = runner._read_object
        candidate_registry = deepcopy(original_read(REPO_ROOT / runner.CANDIDATES_PATH))
        del candidate_registry["candidates"][0]["profile_sha256"]

        def read_object(path: Path) -> dict[str, object]:
            if path == REPO_ROOT / runner.CANDIDATES_PATH:
                return candidate_registry
            return original_read(path)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.object(runner, "_read_object", side_effect=read_object):
                with self.assertRaisesRegex(MigrationContractError, "contract_invalid"):
                    run_offline_migration(
                        REPO_ROOT,
                        fixture=Path(
                            "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
                        ),
                        quarantine_state=root / "quarantine",
                        output=root / "result.json",
                        artifact_root=root,
                    )
            self.assertEqual(list(root.rglob("*")), [])

    def test_candidate_profile_hash_drift_is_evaluated_as_blocked(self) -> None:
        original_read = runner._read_object
        candidate_registry = deepcopy(original_read(REPO_ROOT / runner.CANDIDATES_PATH))
        candidate_registry["candidates"][0]["profile_sha256"] = "0" * 64

        def read_object(path: Path) -> dict[str, object]:
            if path == REPO_ROOT / runner.CANDIDATES_PATH:
                return candidate_registry
            return original_read(path)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with patch.object(runner, "_read_object", side_effect=read_object):
                rc, summary = run_offline_migration(
                    REPO_ROOT,
                    fixture=Path(
                        "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"
                    ),
                    quarantine_state=root / "quarantine",
                    output=root / "result.json",
                    artifact_root=root,
                )
            artifact = json.loads((root / "result.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 2)
        self.assertEqual(summary["status"], "BLOCKED")
        self.assertIn("profile_evaluation_failed", summary["reason_codes"])
        self.assertEqual(artifact["profile_evaluation"]["status"], "BLOCKED")


    def test_invalid_fixture_is_redacted_and_returns_one(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            rc = main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "business-case-type-migration-dry-run",
                    "--fixture",
                    "outside.json",
                    "--quarantine-state",
                    "out/notary-kg/test-quarantine",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(rc, 1)
        self.assertEqual(set(payload), SUMMARY_KEYS)
        self.assertEqual(payload["reason_codes"], ["fixture_invalid"])
        self.assertNotIn(str(REPO_ROOT), output.getvalue())

    def test_contract_failure_and_blocked_status_keep_distinct_exit_codes(self) -> None:
        argv = [
            "--repo-root", str(REPO_ROOT), "--format", "json",
            "business-case-type-migration-dry-run",
            "--fixture", "tests/fixtures/business-case-type-migration/clean-ready.fixture.json",
            "--quarantine-state", "out/notary-kg/test-quarantine",
        ]
        with patch(
            "notary_kg.cli.run_offline_migration",
            side_effect=MigrationContractError("contract_invalid"),
        ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(argv), 1)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["reason_codes"], ["contract_invalid"])
            self.assertEqual(set(payload), SUMMARY_KEYS)
        blocked = {
            "status": "BLOCKED",
            "readiness_scope": "S5_OFFLINE_ONLY",
            "live_cutover_status": "BLOCKED_PENDING_S6_S7_APPROVAL",
            "allowed_live_calls": 0,
            "allowed_tenant_writes": 0,
            "reason_codes": ["mappable"],
            "class_counts": {},
            "top_level_hashes": {},
        }
        with patch(
            "notary_kg.cli.run_offline_migration",
            return_value=(2, blocked),
        ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(argv), 2)
            self.assertEqual(json.loads(output.getvalue()), blocked)

    def test_default_text_output_is_redacted_and_complete(self) -> None:
        payload = {
            "status": "READY",
            "readiness_scope": "S5_OFFLINE_ONLY",
            "live_cutover_status": "BLOCKED_PENDING_S6_S7_APPROVAL",
            "allowed_live_calls": 0,
            "allowed_tenant_writes": 0,
            "reason_codes": [],
            "class_counts": {"already_canonical": 1},
            "top_level_hashes": {"manifest_hash": "a" * 64},
        }
        argv = [
            "--repo-root",
            str(REPO_ROOT),
            "business-case-type-migration-dry-run",
            "--fixture",
            "tests/fixtures/business-case-type-migration/clean-ready.fixture.json",
            "--quarantine-state",
            "out/notary-kg/test-quarantine",
        ]
        with patch(
            "notary_kg.cli.run_offline_migration",
            return_value=(0, payload),
        ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(argv), 0)

        rendered = output.getvalue()
        self.assertIn("BusinessCaseType migration S5 offline dry-run", rendered)
        self.assertIn("- status: READY", rendered)
        self.assertIn("- readiness scope: S5_OFFLINE_ONLY", rendered)
        self.assertIn("- live cutover status: BLOCKED_PENDING_S6_S7_APPROVAL", rendered)
        self.assertIn("- allowed live calls: 0", rendered)
        self.assertIn("- allowed tenant writes: 0", rendered)
        self.assertIn("- reason codes: none", rendered)
        self.assertIn("  - already_canonical: 1", rendered)
        self.assertIn("  - manifest_hash: " + "a" * 64, rendered)
        self.assertNotIn(str(REPO_ROOT), rendered)

    def test_central_cli_forwards_migration_arguments_and_return_code(self) -> None:
        central_argv = [
            "--repo-root", str(REPO_ROOT),
            "kg", "business-case-type-migration-dry-run",
            "--fixture", "tests/fixtures/business-case-type-migration/clean-ready.fixture.json",
            "--quarantine-state", "out/notary-kg/quarantine",
            "--output", "out/notary-kg/result.json",
            "--format", "json",
        ]
        with patch.object(nac_cli, "notary_kg_main", return_value=2) as delegated:
            self.assertEqual(nac_cli.main(central_argv), 2)
        forwarded = delegated.call_args.args[0]
        self.assertEqual(forwarded[:5], [
            "--repo-root", str(REPO_ROOT.resolve()), "--format", "json",
            "business-case-type-migration-dry-run",
        ])
        for flag, value in (
            ("--fixture", "tests/fixtures/business-case-type-migration/clean-ready.fixture.json"),
            ("--quarantine-state", "out/notary-kg/quarantine"),
            ("--output", "out/notary-kg/result.json"),
        ):
            self.assertEqual(forwarded[forwarded.index(flag) + 1], value)


if __name__ == "__main__":
    unittest.main()
