from __future__ import annotations

import json
import os
import stat
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from src.notary_kg import business_case_type_migration_quarantine as quarantine_module
from src.notary_kg.business_case_type_migration_quarantine import (
    ArtifactWriteError,
    QuarantineStore,
    canonical_contained_path,
    write_redacted_output,
)


def _record(character: str = "a", *, classification: str = "conflict") -> dict[str, str]:
    return {
        "record_id": character * 64,
        "classification": classification,
        "record_ref_hash": "f" * 64,
    }


class QuarantineStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = self.root / "out" / "quarantine"

    def tearDown(self):
        self.temporary.cleanup()

    def test_retry_is_noop_and_index_is_stable(self):
        store = QuarantineStore(self.state)
        first = store.persist([_record()])
        record_path = self.state / "records" / f"{'a' * 64}.json"
        inode = record_path.stat().st_ino
        second = store.persist([_record()])
        self.assertEqual(first, second)
        self.assertEqual(inode, record_path.stat().st_ino)
        self.assertEqual(["a" * 64], [item["record_id"] for item in second["records"]])

    def test_two_store_instances_serialize_on_filesystem_lock(self):
        first = QuarantineStore(self.state)
        second = QuarantineStore(self.state)
        attempted = threading.Event()
        completed = threading.Event()
        errors = []

        with first._open_store():
            real_flock = __import__("fcntl").flock

            def observe_flock(descriptor, operation):
                attempted.set()
                return real_flock(descriptor, operation)

            def reconcile_second():
                try:
                    second.reconcile()
                except BaseException as error:
                    errors.append(error)
                finally:
                    completed.set()

            with mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.fcntl.flock",
                side_effect=observe_flock,
            ):
                worker = threading.Thread(target=reconcile_second)
                worker.start()
                self.assertTrue(attempted.wait(1))
                self.assertFalse(completed.wait(0.05))

        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual([], errors)

    def test_persist_locked_holds_filesystem_lock_across_yield(self):
        first = QuarantineStore(self.state)
        second = QuarantineStore(self.state)
        attempted = threading.Event()
        completed = threading.Event()
        errors = []

        with first.persist_locked([_record("a")]) as index:
            self.assertEqual("a" * 64, index["records"][0]["record_id"])
            real_flock = __import__("fcntl").flock

            def observe_flock(descriptor, operation):
                attempted.set()
                return real_flock(descriptor, operation)

            def reconcile_second():
                try:
                    second.reconcile()
                except BaseException as error:
                    errors.append(error)
                finally:
                    completed.set()

            with mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.fcntl.flock",
                side_effect=observe_flock,
            ):
                worker = threading.Thread(target=reconcile_second)
                worker.start()
                self.assertTrue(attempted.wait(1))
                self.assertFalse(completed.wait(0.05))

        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual([], errors)

    def test_lock_entry_must_be_a_regular_nonsymlink_file(self):
        self.state.mkdir(parents=True)
        external = self.root / "external.lock"
        external.write_text("external", encoding="utf-8")
        (self.state / ".quarantine.lock").symlink_to(external)
        with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
            QuarantineStore(self.state).reconcile()

        (self.state / ".quarantine.lock").unlink()
        (self.state / ".quarantine.lock").mkdir()
        with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
            QuarantineStore(self.state).reconcile()

    def test_divergent_collision_never_replaces_record(self):
        store = QuarantineStore(self.state)
        store.persist([_record()])
        path = self.state / "records" / f"{'a' * 64}.json"
        before = path.read_bytes()
        with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
            store.persist([_record(classification="unknown")])
        self.assertEqual(before, path.read_bytes())

    def test_reconcile_recovers_complete_orphan_after_index_failure(self):
        store = QuarantineStore(self.state)
        store.reconcile()
        real_replace = os.replace
        index_replacements = 0

        def fail_index(source, destination, **kwargs):
            nonlocal index_replacements
            if destination == "index.json":
                index_replacements += 1
                if index_replacements == 2:
                    raise OSError("injected")
            return real_replace(source, destination, **kwargs)

        with mock.patch(
            "src.notary_kg.business_case_type_migration_quarantine.os.replace",
            side_effect=fail_index,
        ):
            with self.assertRaises(ArtifactWriteError):
                store.persist([_record("b")])
        recovered = QuarantineStore(self.state).reconcile()
        self.assertEqual(["b" * 64], [item["record_id"] for item in recovered["records"]])

    def test_missing_indexed_record_blocks_without_replacing_index(self):
        store = QuarantineStore(self.state)
        store.persist([_record()])
        index_path = self.state / "index.json"
        prior_index = index_path.read_bytes()
        (self.state / "records" / f"{'a' * 64}.json").unlink()
        with self.assertRaises(ArtifactWriteError):
            store.reconcile()
        self.assertEqual(prior_index, index_path.read_bytes())

    def test_index_fsync_failure_restores_previous_index(self):
        store = QuarantineStore(self.state)
        store.persist([_record("a")])
        index_path = self.state / "index.json"
        prior = index_path.read_bytes()
        real_replace = os.replace
        real_fsync = os.fsync
        replaced_index = False
        failed = False

        def observe_replace(source, destination, **kwargs):
            nonlocal replaced_index
            result = real_replace(source, destination, **kwargs)
            if destination == "index.json" and str(source).startswith(".tmp-"):
                replaced_index = True
            return result

        def fail_post_replace_fsync(descriptor):
            nonlocal failed
            if replaced_index and not failed and stat.S_ISDIR(os.fstat(descriptor).st_mode):
                failed = True
                raise OSError("injected post-replace fsync failure")
            return real_fsync(descriptor)

        with (
            mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.os.replace",
                side_effect=observe_replace,
            ),
            mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.os.fsync",
                side_effect=fail_post_replace_fsync,
            ),
        ):
            with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                store.persist([_record("b")])

        self.assertTrue(failed)
        self.assertEqual(prior, index_path.read_bytes())

    def test_index_previous_marker_restores_missing_target_on_startup(self):
        store = QuarantineStore(self.state)
        expected = store.persist([_record("a")])
        index_path = self.state / "index.json"
        previous = self.state / ".index.json.previous"
        index_path.replace(previous)

        self.assertEqual(expected, store.reconcile())
        self.assertTrue(index_path.is_file())
        self.assertFalse(previous.exists())

    def test_corrupt_record_blocks_reconciliation(self):
        store = QuarantineStore(self.state)
        store.persist([_record()])
        path = self.state / "records" / f"{'a' * 64}.json"
        path.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
            store.reconcile()

    def test_fifo_record_is_rejected_without_blocking(self):
        store = QuarantineStore(self.state)
        store.persist([_record()])
        path = self.state / "records" / f"{'a' * 64}.json"
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
            store.reconcile()

    def test_oversized_index_and_record_are_rejected_before_read(self):
        store = QuarantineStore(self.state)
        store.persist([_record()])
        index_path = self.state / "index.json"
        record_path = self.state / "records" / f"{'a' * 64}.json"

        with mock.patch.object(quarantine_module, "_MAX_INDEX_BYTES", 1):
            with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                store.reconcile()

        with mock.patch.object(quarantine_module, "_MAX_RECORD_BYTES", 1):
            with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                store.reconcile()

        self.assertTrue(index_path.is_file())
        self.assertTrue(record_path.is_file())

    def test_directory_entry_limit_blocks_reconciliation(self):
        store = QuarantineStore(self.state)
        store.persist([_record("a"), _record("b")])
        with mock.patch.object(quarantine_module, "_MAX_DIRECTORY_ENTRIES", 1):
            with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                store.reconcile()

    def test_unpublished_temporary_file_is_ignored(self):
        store = QuarantineStore(self.state)
        store.reconcile()
        (self.state / "records" / ".tmp-interrupted").write_bytes(b"partial")
        self.assertEqual([], store.reconcile()["records"])

    def test_record_published_before_failure_is_recovered(self):
        store = QuarantineStore(self.state)
        store.reconcile()
        real_link = os.link

        def fail_after_publication(source, destination, **kwargs):
            result = real_link(source, destination, **kwargs)
            if destination == "c" * 64 + ".json":
                raise OSError("injected post-publication failure")
            return result

        with mock.patch(
            "src.notary_kg.business_case_type_migration_quarantine.os.link",
            side_effect=fail_after_publication,
        ):
            with self.assertRaises(ArtifactWriteError):
                store.persist([_record("c")])
        recovered = QuarantineStore(self.state).reconcile()
        self.assertEqual("c" * 64, recovered["records"][0]["record_id"])

    def test_records_directory_swap_cannot_redirect_record_publication(self):
        store = QuarantineStore(self.state)
        store.reconcile()
        external = self.root / "external"
        external.mkdir()
        displaced = self.state / "displaced-records"
        real_link = os.link
        swapped = False

        def swap_then_link(source, destination, **kwargs):
            nonlocal swapped
            if not swapped:
                swapped = True
                (self.state / "records").rename(displaced)
                (self.state / "records").symlink_to(external, target_is_directory=True)
            return real_link(source, destination, **kwargs)

        with mock.patch(
            "src.notary_kg.business_case_type_migration_quarantine.os.link",
            side_effect=swap_then_link,
        ):
            store.persist([_record("d")])

        name = f"{'d' * 64}.json"
        self.assertTrue((displaced / name).is_file())
        self.assertFalse((external / name).exists())

    def test_record_id_is_supplied_and_must_match_payload(self):
        store = QuarantineStore(self.state)
        with self.assertRaises(ArtifactWriteError):
            store.store_record("b" * 64, _record("a"))
        with self.assertRaises(ArtifactWriteError):
            store.persist([{"record_id": "not-content-addressed"}])

    def test_symlink_state_and_record_are_rejected(self):
        target = self.root / "target"
        target.mkdir()
        linked_state = self.root / "linked-state"
        linked_state.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ArtifactWriteError):
            QuarantineStore(linked_state).reconcile()

        store = QuarantineStore(self.state)
        store.reconcile()
        external = self.root / "external.json"
        external.write_text(json.dumps(_record()), encoding="utf-8")
        (self.state / "records" / f"{'a' * 64}.json").symlink_to(external)
        with self.assertRaises(ArtifactWriteError):
            store.reconcile()

    def test_containment_rejects_escape_and_symlink_component(self):
        allowed = self.root / "out"
        allowed.mkdir()
        self.assertEqual(
            allowed / "result.json",
            canonical_contained_path(allowed / "result.json", root=allowed),
        )
        with self.assertRaises(ArtifactWriteError):
            canonical_contained_path(allowed / ".." / "escape.json", root=allowed)
        target = self.root / "target"
        target.mkdir()
        (allowed / "link").symlink_to(target, target_is_directory=True)
        with self.assertRaises(ArtifactWriteError):
            canonical_contained_path(allowed / "link" / "result.json", root=allowed)
        final_link = allowed / "result-link.json"
        final_link.symlink_to(self.root / "outside.json")
        with self.assertRaises(ArtifactWriteError):
            canonical_contained_path(final_link, root=allowed)


class RedactedOutputTests(unittest.TestCase):
    def test_atomic_output_replaces_complete_previous_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            write_redacted_output(output, {"generation": 2}, allowed_root=root)
            self.assertEqual({"generation": 2}, json.loads(output.read_bytes()))

    def test_replace_failure_retains_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            prior = output.read_bytes()
            with mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.os.replace",
                side_effect=OSError("injected"),
            ):
                with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                    write_redacted_output(output, {"generation": 2}, allowed_root=root)
            self.assertEqual(prior, output.read_bytes())

    def test_post_replace_fsync_failure_restores_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            prior = output.read_bytes()
            real_replace = os.replace
            real_fsync = os.fsync
            replaced_output = False
            failed = False

            def observe_replace(source, destination, **kwargs):
                nonlocal replaced_output
                result = real_replace(source, destination, **kwargs)
                if destination == "output.json" and str(source).startswith(".tmp-"):
                    replaced_output = True
                return result

            def fail_post_replace_fsync(descriptor):
                nonlocal failed
                if replaced_output and not failed and stat.S_ISDIR(os.fstat(descriptor).st_mode):
                    failed = True
                    raise OSError("injected post-replace fsync failure")
                return real_fsync(descriptor)

            with (
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.os.replace",
                    side_effect=observe_replace,
                ),
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.os.fsync",
                    side_effect=fail_post_replace_fsync,
                ),
            ):
                with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                    write_redacted_output(output, {"generation": 2}, allowed_root=root)

            self.assertTrue(failed)
            self.assertEqual(prior, output.read_bytes())

    def test_previous_marker_cleanup_fsync_failure_keeps_committed_output_successful(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            real_fsync = os.fsync
            directory_fsyncs = 0

            def fail_cleanup_fsync(descriptor):
                nonlocal directory_fsyncs
                if stat.S_ISDIR(os.fstat(descriptor).st_mode):
                    directory_fsyncs += 1
                    if directory_fsyncs == 3:
                        raise OSError("injected previous-marker cleanup fsync failure")
                return real_fsync(descriptor)

            with mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.os.fsync",
                side_effect=fail_cleanup_fsync,
            ):
                write_redacted_output(output, {"generation": 2}, allowed_root=root)

            self.assertEqual(3, directory_fsyncs)
            self.assertEqual({"generation": 2}, json.loads(output.read_bytes()))

    def test_output_writers_serialize_on_sibling_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            entered = threading.Event()
            release = threading.Event()
            second_attempted = threading.Event()
            second_completed = threading.Event()
            errors = []
            real_atomic = quarantine_module._atomic_replace_json_at
            real_flock = __import__("fcntl").flock

            def hold_first_writer(parent_fd, name, value):
                if threading.current_thread().name == "first-output-writer":
                    entered.set()
                    if not release.wait(1):
                        raise AssertionError("first writer was not released")
                return real_atomic(parent_fd, name, value)

            def observe_flock(descriptor, operation):
                if threading.current_thread().name == "second-output-writer":
                    second_attempted.set()
                return real_flock(descriptor, operation)

            def write(generation, completed=None):
                try:
                    write_redacted_output(
                        output,
                        {"generation": generation},
                        allowed_root=root,
                    )
                except BaseException as error:
                    errors.append(error)
                finally:
                    if completed is not None:
                        completed.set()

            with (
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine._atomic_replace_json_at",
                    side_effect=hold_first_writer,
                ),
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.fcntl.flock",
                    side_effect=observe_flock,
                ),
            ):
                first = threading.Thread(
                    target=write,
                    args=(1,),
                    name="first-output-writer",
                )
                second = threading.Thread(
                    target=write,
                    args=(2, second_completed),
                    name="second-output-writer",
                )
                first.start()
                self.assertTrue(entered.wait(1))
                second.start()
                self.assertTrue(second_attempted.wait(1))
                self.assertFalse(second_completed.wait(0.05))
                release.set()
                first.join(1)
                second.join(1)

            self.assertFalse(first.is_alive())
            self.assertFalse(second.is_alive())
            self.assertEqual([], errors)
            self.assertEqual({"generation": 2}, json.loads(output.read_bytes()))

    def test_rollback_does_not_replace_destination_changed_by_another_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            previous = root / ".output.json.previous"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            prior = output.read_bytes()
            third_party = root / "third-party.json"
            third_party.write_bytes(b"{\"owner\":\"other\"}\n")
            real_replace = os.replace
            real_fsync = os.fsync
            replacement_visible = False
            swapped = False

            def observe_replace(source, destination, **kwargs):
                nonlocal replacement_visible
                result = real_replace(source, destination, **kwargs)
                if destination == "output.json" and str(source).startswith(".tmp-"):
                    replacement_visible = True
                return result

            def swap_before_failed_fsync(descriptor):
                nonlocal swapped
                if (
                    replacement_visible
                    and not swapped
                    and stat.S_ISDIR(os.fstat(descriptor).st_mode)
                ):
                    swapped = True
                    real_replace(third_party, output)
                    raise OSError("injected post-swap durability failure")
                return real_fsync(descriptor)

            with (
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.os.replace",
                    side_effect=observe_replace,
                ),
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.os.fsync",
                    side_effect=swap_before_failed_fsync,
                ),
            ):
                with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                    write_redacted_output(output, {"generation": 2}, allowed_root=root)

            self.assertTrue(swapped)
            self.assertEqual(b"{\"owner\":\"other\"}\n", output.read_bytes())
            self.assertEqual(prior, previous.read_bytes())

            write_redacted_output(output, {"generation": 3}, allowed_root=root)
            self.assertFalse(previous.exists())
            self.assertEqual({"generation": 3}, json.loads(output.read_bytes()))

    def test_missing_output_is_restored_from_declared_previous_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            previous = root / ".output.json.previous"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            prior = output.read_bytes()
            output.replace(previous)

            with mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine._atomic_replace_json_at",
                side_effect=OSError("stop after recovery"),
            ):
                with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                    write_redacted_output(output, {"generation": 2}, allowed_root=root)

            self.assertEqual(prior, output.read_bytes())
            self.assertFalse(previous.exists())

    def test_previous_marker_symlink_is_rejected_without_following(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            previous = root / ".output.json.previous"
            external = root / "external.json"
            write_redacted_output(output, {"generation": 1}, allowed_root=root)
            prior = output.read_bytes()
            external.write_text("external", encoding="utf-8")
            previous.symlink_to(external)

            with self.assertRaises(ArtifactWriteError):
                write_redacted_output(output, {"generation": 2}, allowed_root=root)

            self.assertEqual(prior, output.read_bytes())
            self.assertEqual("external", external.read_text(encoding="utf-8"))

    def test_output_lock_entry_must_be_regular_and_nofollow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "output.json"
            external = root / "external.lock"
            external.write_text("external", encoding="utf-8")
            (root / ".output.json.lock").symlink_to(external)

            with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                write_redacted_output(output, {"generation": 1}, allowed_root=root)
            self.assertEqual("external", external.read_text(encoding="utf-8"))

    def test_output_escape_and_existing_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / "outside-redacted.json"
            with self.assertRaises(ArtifactWriteError):
                write_redacted_output(outside, {}, allowed_root=root)
            target = root / "target.json"
            target.write_text("retained", encoding="utf-8")
            linked = root / "linked.json"
            linked.symlink_to(target)
            with self.assertRaises(ArtifactWriteError):
                write_redacted_output(linked, {}, allowed_root=root)
            self.assertEqual("retained", target.read_text(encoding="utf-8"))

    def test_symlink_inserted_during_directory_creation_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "external"
            external.mkdir()
            real_mkdir = os.mkdir

            def replace_nested_with_symlink(name, mode=0o777, *, dir_fd=None):
                if name == "nested":
                    os.symlink(external, name, target_is_directory=True, dir_fd=dir_fd)
                    return None
                return real_mkdir(name, mode=mode, dir_fd=dir_fd)

            with mock.patch(
                "src.notary_kg.business_case_type_migration_quarantine.os.mkdir",
                side_effect=replace_nested_with_symlink,
            ):
                with self.assertRaisesRegex(ArtifactWriteError, "^artifact_write_failed$"):
                    write_redacted_output(
                        root / "nested" / "output.json",
                        {"generation": 1},
                        allowed_root=root,
                    )
            self.assertFalse((external / "output.json").exists())

    def test_every_created_directory_is_followed_by_parent_fsync(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []
            real_mkdir = os.mkdir
            real_fsync = os.fsync

            def observe_mkdir(name, mode=0o777, *, dir_fd=None):
                result = real_mkdir(name, mode=mode, dir_fd=dir_fd)
                events.append(("mkdir", name, os.fstat(dir_fd).st_ino))
                return result

            def observe_fsync(descriptor):
                events.append(("fsync", None, os.fstat(descriptor).st_ino))
                return real_fsync(descriptor)

            with (
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.os.mkdir",
                    side_effect=observe_mkdir,
                ),
                mock.patch(
                    "src.notary_kg.business_case_type_migration_quarantine.os.fsync",
                    side_effect=observe_fsync,
                ),
            ):
                write_redacted_output(
                    root / "one" / "two" / "output.json",
                    {"generation": 1},
                    allowed_root=root,
                )

            mkdir_positions = [index for index, event in enumerate(events) if event[0] == "mkdir"]
            self.assertEqual(2, len(mkdir_positions))
            for index in mkdir_positions:
                self.assertEqual(("fsync", None, events[index][2]), events[index + 1])


if __name__ == "__main__":
    unittest.main()
