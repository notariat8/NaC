from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nac_m365_graph.business_case_type_production_composition import (
    LIVE_STATUS,
    S4G_STATUS,
    assess_production_composition,
    assess_synthetic_offline_composition,
    synthetic_identity_snapshot,
    synthetic_offline_bindings,
)
from nac_m365_graph.business_case_type_write_identity_inspection import (
    SnapshotIdentityInspectionPort,
)


class BusinessCaseTypeProductionCompositionTests(unittest.TestCase):
    def _runtime_root(self, parent: Path) -> Path:
        root = parent / "runtime"
        root.mkdir(mode=0o700)
        os.chmod(root, 0o700)
        return root

    def test_complete_edge_shape_is_verified_but_live_stays_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            result = assess_production_composition(
                synthetic_offline_bindings(ROOT, root),
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertEqual(result["status"], S4G_STATUS)
        self.assertEqual(result["live_status"], LIVE_STATUS)
        self.assertFalse(result["runtime_factory_constructed"])
        self.assertFalse(result["writer_credentials_read"])
        self.assertFalse(result["production_durability_claimed"])
        self.assertFalse(result["live_write_authorized"])
        self.assertEqual(result["summary"]["tenant_writes"], 0)
        self.assertIn(
            "central_postgresql_promotion_ack_retention_cleanup",
            result["remaining_blockers"],
        )

    def test_synthetic_composition_uses_identity_inspection_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            result = assess_synthetic_offline_composition(ROOT, root)

        self.assertEqual(result["status"], S4G_STATUS)
        self.assertTrue(result["checks"]["identity_inspection_exact"])
        self.assertTrue(
            result["checks"]["principal_bindings_pairwise_distinct"]
        )

    def test_principals_and_identity_snapshot_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            bindings = synthetic_offline_bindings(ROOT, root)
            result = assess_production_composition(
                replace(
                    bindings,
                    writer_principal_sha256=(
                        bindings.provisioner_principal_sha256
                    ),
                ),
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn(
            "principal_bindings_pairwise_distinct",
            result["failed_checks"],
        )
        self.assertIn("principal_bindings_exact", result["failed_checks"])

    def test_arbitrary_component_binding_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            bindings = synthetic_offline_bindings(ROOT, root)
            for field in (
                "identity_inspector_implementation_sha256",
                "owner_verifier_sha256",
            ):
                with self.subTest(field=field):
                    result = assess_production_composition(
                        replace(bindings, **{field: "f" * 64}),
                        identity_port=SnapshotIdentityInspectionPort(
                            synthetic_identity_snapshot()
                        ),
                        repository_root=ROOT,
                    )
                    self.assertEqual(result["status"], "BLOCKED")
                    self.assertIn(
                        "component_bindings_repository_exact",
                        result["failed_checks"],
                    )

    def test_non_snapshot_identity_port_is_never_called(self) -> None:
        class ExternalPort:
            called = False

            def readback(self):
                self.called = True
                return synthetic_identity_snapshot()

        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            port = ExternalPort()
            result = assess_production_composition(
                synthetic_offline_bindings(ROOT, root),
                identity_port=port,  # type: ignore[arg-type]
                repository_root=ROOT,
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(port.called)
        self.assertIn("identity_snapshot_valid", result["failed_checks"])

    def test_same_database_and_weak_root_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            bindings = synthetic_offline_bindings(ROOT, root)
            same = assess_production_composition(
                replace(
                    bindings,
                    evidence_database_path=bindings.mutation_database_path,
                ),
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )
            os.chmod(root, 0o755)
            weak = assess_production_composition(
                bindings,
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertIn("local_runtime_layout_exact", same["failed_checks"])
        self.assertIn("local_runtime_layout_exact", weak["failed_checks"])

    def test_synced_directory_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            synced = Path(directory) / "OneDrive"
            synced.mkdir(mode=0o700)
            result = assess_production_composition(
                synthetic_offline_bindings(ROOT, synced),
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertIn("local_runtime_layout_exact", result["failed_checks"])

    def test_wrong_database_names_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            bindings = synthetic_offline_bindings(ROOT, root)
            result = assess_production_composition(
                replace(
                    bindings,
                    mutation_database_path=root / "arbitrary-a.db",
                    evidence_database_path=root / "arbitrary-b.db",
                ),
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertIn(
            "local_runtime_layout_exact",
            result["failed_checks"],
        )

    def test_existing_databases_require_0600_and_distinct_inodes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            bindings = synthetic_offline_bindings(ROOT, root)
            bindings.mutation_database_path.touch(mode=0o600)
            bindings.evidence_database_path.touch(mode=0o600)
            os.chmod(bindings.evidence_database_path, 0o644)
            weak = assess_production_composition(
                bindings,
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )
            bindings.evidence_database_path.unlink()
            os.link(
                bindings.mutation_database_path,
                bindings.evidence_database_path,
            )
            hardlinked = assess_production_composition(
                bindings,
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertIn(
            "local_runtime_layout_exact", weak["failed_checks"]
        )
        self.assertIn(
            "local_runtime_layout_exact",
            hardlinked["failed_checks"],
        )

    def test_external_hardlink_aliases_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = self._runtime_root(parent)
            bindings = synthetic_offline_bindings(ROOT, root)
            first_source = parent / "outside-mutation.sqlite3"
            second_source = parent / "outside-evidence.sqlite3"
            first_source.touch(mode=0o600)
            second_source.touch(mode=0o600)
            os.link(first_source, bindings.mutation_database_path)
            os.link(second_source, bindings.evidence_database_path)
            result = assess_production_composition(
                bindings,
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn(
            "local_runtime_layout_exact", result["failed_checks"]
        )

    def test_unknown_or_remote_filesystem_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            with patch(
                "nac_m365_graph.business_case_type_production_composition."
                "_is_explicitly_local_filesystem",
                return_value=False,
            ):
                result = assess_synthetic_offline_composition(ROOT, root)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn(
            "local_runtime_layout_exact",
            result["failed_checks"],
        )

    def test_assessment_performs_no_network_or_credential_reads(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            with (
                patch.object(
                    socket,
                    "socket",
                    side_effect=AssertionError("socket used"),
                ),
                patch(
                    "os.getenv",
                    side_effect=AssertionError("environment read"),
                ),
            ):
                result = assess_production_composition(
                    synthetic_offline_bindings(ROOT, root),
                    identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                    repository_root=ROOT,
                )

        self.assertEqual(result["status"], S4G_STATUS)

    def test_output_contains_no_binding_or_path_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._runtime_root(Path(directory))
            result = assess_production_composition(
                synthetic_offline_bindings(ROOT, root),
                identity_port=SnapshotIdentityInspectionPort(
                    synthetic_identity_snapshot()
                ),
                repository_root=ROOT,
            )
            encoded = json.dumps(result, sort_keys=True)

        self.assertNotIn("1" * 64, encoded)
        self.assertNotIn(str(root), encoded)
        self.assertNotIn("access_token", encoded)
        self.assertNotIn("private_key", encoded)


if __name__ == "__main__":
    unittest.main()
