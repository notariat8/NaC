from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.validate_notarial_application_interface_inventory import (
    CONTRACT_PATH,
    DOC_DE,
    DOC_EN,
    REQUIRED_INTERFACE_IDS,
    validate_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class NotarialApplicationInterfaceInventoryContractTests(unittest.TestCase):
    def test_contract_validates(self) -> None:
        self.assertEqual([], validate_contract())

    def test_strict_quality_gate_runs_inventory_validator(self) -> None:
        from scripts import quality_gate

        checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }

        self.assertIn("notarial_application_interface_inventory", checks)
        self.assertIn(
            "scripts/validate_notarial_application_interface_inventory.py",
            checks["notarial_application_interface_inventory"],
        )

    def test_contract_keeps_inventory_metadata_only(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        policy = payload["global_policy"]

        for key in (
            "source_fulltext_ingestion_allowed",
            "external_assets_in_repo_allowed",
            "raw_xsd_copy_in_repo_allowed_without_license_gate",
            "credentials_in_repo_allowed",
            "client_certificates_in_repo_allowed",
            "tokens_in_repo_allowed",
            "matter_data_in_repo_allowed",
            "message_payloads_in_repo_allowed",
            "live_connector_apply_allowed",
            "productive_specialist_system_write_allowed",
            "m365_mvp_data_plane_changed",
        ):
            self.assertIs(policy[key], False, key)

        self.assertIs(policy["read_only_mcp_contract_required_before_runtime"], False)
        self.assertIs(policy["private_operating_frame_required_before_live"], True)
        self.assertIs(policy["owner_apply_gate_required_before_live"], True)

    def test_contract_binds_inventory_tools_to_teams_sharepoint_mcp(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        binding = payload["runtime_binding"]

        self.assertEqual("teams-sharepoint-data-mcp", binding["server_id"])
        self.assertEqual(
            "workflows/contracts/teams-sharepoint-data-mcp.contract.json",
            binding["implemented_in_contract"],
        )
        self.assertTrue(binding["implemented_now"])
        self.assertFalse(binding["executes_graph_requests"])

        tools = {tool["name"]: tool for tool in payload["read_only_mcp_tools"]}
        self.assertEqual(
            set(tools),
            {"notarial_interface_inventory_list", "notarial_interface_boundary_check"},
        )
        for tool in tools.values():
            self.assertIn("external BNotK calls", tool["blocked_output"])

    def test_required_interface_ids_are_present(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        ids = {entry["id"] for entry in payload["interfaces"]}

        self.assertEqual(REQUIRED_INTERFACE_IDS, ids)

    def test_docs_exist_in_german_and_english_with_source_boundaries(self) -> None:
        for path in (DOC_DE, DOC_EN):
            self.assertTrue(path.is_file(), path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("https://onlinehilfe.bnotk.de/technischer-bereich/softwarehersteller/anwendungsschnittstellen.html", text)
            self.assertIn("https://onlinehilfe.bnotk.de/technischer-bereich/softwarehersteller/ben.html", text)
            self.assertIn("XJustiz 3.3.1", text)
            self.assertIn("66 XSD", text)
            self.assertIn("M365", text)
            self.assertIn("Microsoft Graph REST/MCP", text)

    def test_xjustiz_package_is_reference_only(self) -> None:
        payload = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        xjustiz = payload["source_documents"]["xjustiz_331_xsd"]

        self.assertEqual("3.3.1", xjustiz["package_version"])
        self.assertEqual(66, xjustiz["xsd_file_count"])
        self.assertEqual("metadata_only", xjustiz["repository_storage"])

    def test_no_source_archive_or_schema_copy_is_committed(self) -> None:
        forbidden_suffixes = {".zip"}
        forbidden_names = {
            "Anwendungsschnittstellen _ Onlinehilfe der Bundesnotarkammer.html",
            "beN _ Onlinehilfe der Bundesnotarkammer.html",
            "xjustiz_0000_grunddatensatz_3_3.xsd",
        }
        for path in REPO_ROOT.rglob("*"):
            if ".git" in path.parts:
                continue
            if path.suffix in forbidden_suffixes:
                self.fail(f"source archive must not be committed: {path.relative_to(REPO_ROOT)}")
            if path.name in forbidden_names:
                self.fail(f"source artifact must not be committed: {path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    unittest.main()
