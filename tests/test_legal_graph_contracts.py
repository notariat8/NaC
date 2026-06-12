from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGAL_GRAPH_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-graph.contract.json"
COMMENTARY_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "legal-commentary-connectors.contract.json"


class LegalGraphContractTests(unittest.TestCase):
    def test_legal_graph_contract_blocks_unreviewed_merges(self) -> None:
        payload = json.loads(LEGAL_GRAPH_CONTRACT.read_text(encoding="utf-8"))
        domains = {domain["id"] for domain in payload["domains"]}

        self.assertEqual(payload["contract_id"], "workflow.legal_graph")
        self.assertEqual(payload["status"], "planned_mvp")
        self.assertFalse(payload["automation_policy"]["auto_merge_allowed"])
        self.assertTrue(payload["automation_policy"]["human_review_required"])
        self.assertGreaterEqual(domains, {"erbrecht", "familienrecht", "gesellschaftsrecht"})
        self.assertIn("source_document", payload["required_node_types"])
        self.assertIn("graph_patch", payload["required_node_types"])

    def test_commentary_contract_requires_mcp_or_api_and_blocks_full_text(self) -> None:
        payload = json.loads(COMMENTARY_CONTRACT.read_text(encoding="utf-8"))
        providers = {provider["id"]: provider for provider in payload["candidate_providers"]}

        self.assertEqual(payload["contract_id"], "workflow.legal_commentary_connectors")
        self.assertFalse(payload["policy"]["credentials_allowed_in_repo"])
        self.assertFalse(payload["policy"]["commentary_full_text_allowed_in_repo"])
        self.assertTrue(payload["policy"]["requires_license_review"])
        self.assertTrue(payload["policy"]["requires_human_notarial_review"])
        self.assertEqual(set(payload["allowed_connection_modes"]), {"mcp", "api"})
        self.assertGreaterEqual(set(providers), {"beck-online", "juris", "wolters-kluwer"})
        for provider in providers.values():
            self.assertEqual(provider["license_status"], "license_review_required")
            self.assertEqual(provider["activation_gate"], "blocked_until_license_api_and_review")
            self.assertEqual(provider["license_basis"], "not_reviewed")
            self.assertEqual(provider["terms_review_status"], "pending_contract_review")
            self.assertEqual(provider["dpa_status"], "pending_applicability_review")
            self.assertEqual(provider["professional_secrecy_status"], "pending_review")
            self.assertEqual(provider["ai_sbom_status"], "pending_decision")
            self.assertEqual(provider["security_boundary_status"], "pending_architecture_review")
            self.assertEqual(provider["credential_operating_model"], "external_secret_store_required")
            self.assertIn("citation_metadata", provider["permitted_data_classes"])
            self.assertIn("commentary_full_text", provider["prohibited_data_classes"])
            self.assertIn("citation", provider["allowed_evidence_fields"])
            self.assertIn("answer_metadata", provider["permitted_outputs"])
            self.assertIn("store_commentary_full_text", provider["blocked_actions"])

    def test_validator_accepts_contracts(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_legal_graph_contracts.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)

    def test_strict_quality_gate_runs_legal_graph_contract_validator(self) -> None:
        from scripts import quality_gate

        checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }

        self.assertIn("legal_graph_contracts", checks)
        self.assertIn("scripts/validate_legal_graph_contracts.py", checks["legal_graph_contracts"])

    def test_artifact_validator_rejects_fixture_mandate_values(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            domain_dir = repo_root / "workflows" / "legal-graph" / "domains"
            fixture_dir = repo_root / "workflows" / "legal-graph" / "fixtures"
            domain_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "domains" / "erbrecht.graph.json",
                domain_dir / "erbrecht.graph.json",
            )
            fixture = json.loads(
                (REPO_ROOT / "workflows" / "legal-graph" / "fixtures" / "erbrecht-source-update.json").read_text(
                    encoding="utf-8"
                )
            )
            fixture["candidate_nodes"][0]["value"] = "UVZ-2026-0001"
            (fixture_dir / "erbrecht-source-update.json").write_text(
                json.dumps(fixture, ensure_ascii=False),
                encoding="utf-8",
            )

            errors = validator.validate_legal_graph_artifacts(repo_root)

        self.assertTrue(errors)
        self.assertIn("must not contain mandate values", "\n".join(errors))

    def test_artifact_validator_rejects_commentary_access_for_primary_source(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source_dir = repo_root / "workflows" / "legal-graph" / "sources"
            source_dir.mkdir(parents=True)
            manifest = {
                "schema_version": "nac.legal-graph-source/v0.1",
                "source_id": "primary.gesetze-im-internet.bgb.erbrecht",
                "domain": "erbrecht",
                "source_type": "primary_law",
                "retrieval_mode": "metadata_only_fixture",
                "canonical_url": "https://www.gesetze-im-internet.de/bgb/",
                "update_fixture": "workflows/legal-graph/fixtures/erbrecht-source-update.json",
                "commentary_access_allowed": True,
                "credentials_required": False,
                "provider_query_allowed": False,
                "allowed_outputs": ["candidate_node_metadata"],
                "blocked_actions": ["store_source_full_text"],
                "review_required": True,
            }
            (source_dir / "erbrecht-primary-source.json").write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            errors = validator.validate_legal_graph_artifacts(repo_root)

        self.assertTrue(errors)
        self.assertIn("commentary_access_allowed muss false sein", "\n".join(errors))

    def test_artifact_validator_rejects_primary_source_fixture_outside_update_area(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source_dir = repo_root / "workflows" / "legal-graph" / "sources"
            source_dir.mkdir(parents=True)
            manifest = {
                "schema_version": "nac.legal-graph-source/v0.1",
                "source_id": "primary.gesetze-im-internet.bgb.erbrecht",
                "domain": "erbrecht",
                "source_type": "primary_law",
                "retrieval_mode": "metadata_only_fixture",
                "canonical_url": "https://www.gesetze-im-internet.de/bgb/",
                "update_fixture": "../outside.json",
                "commentary_access_allowed": False,
                "credentials_required": False,
                "provider_query_allowed": False,
                "allowed_outputs": [
                    "source_url",
                    "retrieved_at",
                    "citation",
                    "candidate_node_metadata",
                    "candidate_edge_metadata",
                ],
                "blocked_actions": [
                    "query_commentary_connector",
                    "store_source_full_text",
                    "store_commentary_full_text",
                    "store_credentials",
                    "send_mandate_data",
                    "auto_merge_graph_patch",
                ],
                "review_required": True,
            }
            (source_dir / "erbrecht-primary-source.json").write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            errors = validator.validate_legal_graph_artifacts(repo_root)

        self.assertTrue(errors)
        self.assertIn("update_fixture muss unter workflows/legal-graph/fixtures liegen", "\n".join(errors))

    def test_commentary_contract_validator_rejects_missing_professional_gate(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        payload = json.loads(COMMENTARY_CONTRACT.read_text(encoding="utf-8"))
        payload["candidate_providers"][0].pop("dpa_status", None)

        errors = validator._validate_commentary_contract(payload)

        self.assertTrue(errors)
        self.assertIn("beck-online Pflichtfeld fehlt dpa_status", "\n".join(errors))

    def test_commentary_contract_validator_rejects_active_provider_status(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        payload = json.loads(COMMENTARY_CONTRACT.read_text(encoding="utf-8"))
        payload["candidate_providers"][0]["status"] = "active"

        errors = validator._validate_commentary_contract(payload)

        self.assertTrue(errors)
        self.assertIn("beck-online.status muss license_review_required sein", "\n".join(errors))

    def test_commentary_contract_validator_rejects_outputs_outside_allowlist(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        payload = json.loads(COMMENTARY_CONTRACT.read_text(encoding="utf-8"))
        payload["candidate_providers"][0]["permitted_outputs"].append("commentary_full_text")
        payload["candidate_providers"][0]["permitted_data_classes"].append("mandate_contact_email")

        errors = validator._validate_commentary_contract(payload)

        self.assertTrue(errors)
        joined_errors = "\n".join(errors)
        self.assertIn("beck-online.permitted_outputs enthaelt unzulaessigen Wert commentary_full_text", joined_errors)
        self.assertIn("beck-online.permitted_data_classes enthaelt unzulaessigen Wert mandate_contact_email", joined_errors)

    def test_artifact_validator_rejects_missing_primary_source_fixture(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            source_dir = repo_root / "workflows" / "legal-graph" / "sources"
            source_dir.mkdir(parents=True)
            manifest = json.loads(
                (REPO_ROOT / "workflows" / "legal-graph" / "sources" / "erbrecht-primary-source.json").read_text(
                    encoding="utf-8"
                )
            )
            manifest["update_fixture"] = "workflows/legal-graph/fixtures/missing-source-update.json"
            (source_dir / "erbrecht-primary-source.json").write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            errors = validator.validate_legal_graph_artifacts(repo_root)

        self.assertTrue(errors)
        self.assertIn("update_fixture muss existieren", "\n".join(errors))

    def test_artifact_validator_rejects_unknown_source_document_refs(self) -> None:
        from scripts import validate_legal_graph_contracts as validator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            domain_dir = repo_root / "workflows" / "legal-graph" / "domains"
            fixture_dir = repo_root / "workflows" / "legal-graph" / "fixtures"
            source_dir = repo_root / "workflows" / "legal-graph" / "sources"
            domain_dir.mkdir(parents=True)
            fixture_dir.mkdir(parents=True)
            source_dir.mkdir(parents=True)
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "domains" / "erbrecht.graph.json",
                domain_dir / "erbrecht.graph.json",
            )
            shutil.copyfile(
                REPO_ROOT / "workflows" / "legal-graph" / "fixtures" / "erbrecht-source-update.json",
                fixture_dir / "erbrecht-source-update.json",
            )
            manifest = json.loads(
                (REPO_ROOT / "workflows" / "legal-graph" / "sources" / "erbrecht-primary-source.json").read_text(
                    encoding="utf-8"
                )
            )
            manifest["source_document_refs"] = ["source.gesetze-im-internet.unknown"]
            (source_dir / "erbrecht-primary-source.json").write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )

            errors = validator.validate_legal_graph_artifacts(repo_root)

        self.assertTrue(errors)
        self.assertIn("source_document_refs verweist auf unbekannten Knoten", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
