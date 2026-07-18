from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validate_xnotar_xjustiz_package_boundary import (  # noqa: E402
    CONTRACT_PATH,
    FIXTURE_PATH,
    GIT_EXECUTABLE,
    INTERFACE_ID,
    MODULE_TARGET,
    VERSION_PIN,
    _tracked_repository_files,
    validate_contract,
    validate_package_manifest,
)


class XNotarXJustizPackageBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_contract_validator_accepts_repository_contract(self) -> None:
        self.assertEqual([], validate_contract())

    def test_fixture_manifest_validates(self) -> None:
        self.assertEqual([], validate_package_manifest(FIXTURE_PATH))

    def test_contract_declares_metadata_only_non_goals(self) -> None:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        policy = contract["repository_policy"]
        for key in (
            "xnotar_import_allowed",
            "ben_dispatch_allowed",
            "xsd_ingestion_allowed",
            "wsdl_ingestion_allowed",
            "xml_payload_ingestion_allowed",
            "package_archive_storage_allowed",
            "matter_data_storage_allowed",
            "document_fulltext_storage_allowed",
            "absolute_paths_allowed",
            "live_connector_apply_allowed",
        ):
            self.assertIs(policy[key], False, key)
        self.assertIs(policy["metadata_only"], True)
        self.assertIs(policy["redacted_evidence_only"], True)

    def test_manifest_checks_expected_folder_message_references_and_counts(self) -> None:
        self.assertEqual("attachments/", self.fixture["folders"][0]["path"])
        self.assertEqual("xjustiz_nachricht.xml", self.fixture["message_file"]["name"])
        self.assertEqual("xjustiz_nachricht.xml", self.fixture["message_file"]["pointer"])

        attachment_names = {entry["name"] for entry in self.fixture["attachments"]}
        reference_names = {entry["name"] for entry in self.fixture["referenced_attachments"]}
        self.assertEqual(attachment_names, reference_names)
        self.assertEqual(
            {
                "message_file_count": 1,
                "attachment_file_count": 2,
                "referenced_attachment_count": 2,
                "total_file_count": 3,
            },
            self.fixture["counts"],
        )

    def test_evidence_is_redacted_and_pinned(self) -> None:
        evidence = self.fixture["evidence"]

        self.assertEqual("READY_METADATA_ONLY", evidence["status"])
        self.assertEqual(INTERFACE_ID, evidence["interface_id"])
        self.assertEqual(MODULE_TARGET, evidence["module_target"])
        self.assertEqual(VERSION_PIN, evidence["version_pin"])
        self.assertEqual("relative_pointers_only", evidence["pointer_status"])
        self.assertTrue(evidence["no_secret_attestation"])
        self.assertTrue(evidence["no_matter_data_attestation"])

        for blocked in ("xml_payload", "document_full_text", "register_data", "secret", "token"):
            self.assertNotIn(blocked, evidence)

    def test_rejects_absolute_paths(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["attachments"][0]["pointer"] = "/tmp/real-package/anlage-001.pdf"

        errors = validate_package_manifest(manifest)

        self.assertTrue(any("relativer" in error for error in errors), errors)

    def test_rejects_missing_attachments_folder(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["folders"] = []

        errors = validate_package_manifest(manifest)

        self.assertIn("folders muss attachments/ als directory enthalten", errors)

    def test_rejects_raw_xml_or_content_fields(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["message_file"]["xml_payload"] = "<?xml version='1.0'?><xjustiz/>"

        errors = validate_package_manifest(manifest)

        self.assertTrue(any("xml_payload" in error for error in errors), errors)
        self.assertTrue(any("unzulässigen Marker" in error for error in errors), errors)

    def test_rejects_missing_referenced_attachment(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["referenced_attachments"].append(
            {"name": "fehlende-anlage.pdf", "pointer": "attachments/fehlende-anlage.pdf"}
        )
        manifest["counts"]["referenced_attachment_count"] = 3

        errors = validate_package_manifest(manifest)

        self.assertTrue(any("unbekannte Anlagen" in error for error in errors), errors)

    def test_rejects_raw_package_file_types(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["attachments"][0]["name"] = "schema.xsd"
        manifest["attachments"][0]["pointer"] = "attachments/schema.xsd"
        manifest["attachments"][0]["media_type"] = "application/xml"
        manifest["referenced_attachments"][0]["name"] = "schema.xsd"
        manifest["referenced_attachments"][0]["pointer"] = "attachments/schema.xsd"

        errors = validate_package_manifest(manifest)

        self.assertTrue(any("unzulässigen Dateityp" in error for error in errors), errors)
        self.assertTrue(any("media_type ist unzulässig" in error for error in errors), errors)

    def test_rejects_count_mismatches(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["counts"]["attachment_file_count"] = 99

        errors = validate_package_manifest(manifest)

        self.assertIn("counts.attachment_file_count muss 2 sein", errors)

    def test_rejects_unredacted_evidence_fields(self) -> None:
        manifest = copy.deepcopy(self.fixture)
        manifest["evidence"]["document_full_text"] = "synthetischer Volltext"

        errors = validate_package_manifest(manifest)

        self.assertTrue(any("document_full_text" in error for error in errors), errors)

    def test_strict_quality_gate_runs_package_boundary_validator(self) -> None:
        from scripts import quality_gate

        checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }

        self.assertIn("xnotar_xjustiz_package_boundary", checks)
        self.assertIn(
            "scripts/validate_xnotar_xjustiz_package_boundary.py",
            checks["xnotar_xjustiz_package_boundary"],
        )

    def test_central_contracts_cli_includes_validator(self) -> None:
        cli_source = (REPO_ROOT / "src" / "nac_cli" / "cli.py").read_text(encoding="utf-8")

        self.assertIn("validate_xnotar_xjustiz_package_boundary.py", cli_source)

    def test_notarial_interface_inventory_binds_boundary_row(self) -> None:
        inventory_path = REPO_ROOT / "workflows" / "contracts" / "notarial-application-interface-inventory.contract.json"
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        rows = {entry["id"]: entry for entry in inventory["interfaces"]}

        self.assertIn(INTERFACE_ID, rows)
        row = rows[INTERFACE_ID]
        self.assertEqual("xnotar_xjustiz_package_boundary_contract", row["source"])
        self.assertEqual("package_boundary_metadata_only_no_import", row["mvp_boundary"])
        self.assertIn("xjustiz_message_pointer", row["families"])

    def test_tracked_file_scan_uses_bound_git_binary(self) -> None:
        self.assertEqual(GIT_EXECUTABLE, Path("/usr/bin/git"))
        self.assertTrue(GIT_EXECUTABLE.is_file())

    def test_no_raw_exchange_artifacts_are_committed(self) -> None:
        forbidden_suffixes = {".zip", ".xsd", ".wsdl", ".xml"}
        forbidden_names = {
            "Anwendungsschnittstellen _ Onlinehilfe der Bundesnotarkammer.html",
            "beN _ Onlinehilfe der Bundesnotarkammer.html",
            "xjustiz_nachricht.xml",
        }
        for path in _tracked_repository_files():
            if path.suffix.lower() in forbidden_suffixes:
                self.fail(f"raw package artifact must not be committed: {path.relative_to(REPO_ROOT)}")
            if path.name in forbidden_names:
                self.fail(f"raw source or payload artifact must not be committed: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    unittest.main()
