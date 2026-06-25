from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)
DE_DOC = REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-first-matter-metadata.md"
EN_DOC = REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-first-matter-metadata.md"


class NotarkammerFirstMatterMetadataTests(unittest.TestCase):
    def load_fixture(self) -> dict:
        self.assertTrue(FIXTURE.is_file(), FIXTURE)
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_metadata_only_and_references_public_demo_path(self) -> None:
        data = self.load_fixture()

        self.assertEqual(data["schema_version"], "nac.demo-matter-metadata/v0.1")
        self.assertEqual(data["demo_context"], "notarkammer-2026-06")
        self.assertEqual(data["tenant_demo_id"], "DEMO-TENANT-NOTARIAT-01")
        self.assertEqual(data["matter_demo_id"], "DEMO-MATTER-IMMOBILIENKAUF-01")
        self.assertEqual(data["usecase_slug"], "immobilienkaufvertrag")
        self.assertEqual(data["bpmn_model"], "bpmn/immobilienkaufvertrag.bpmn")
        self.assertEqual(data["kg_ref"], "usecases/immobilienkaufvertrag/knowledge-graph.md")
        self.assertEqual(data["scope"], "metadata_only")
        self.assertFalse(data["raw_mandate_content_loaded"])
        self.assertFalse(data["productive_xnp_action"])
        self.assertFalse(data["contains_credentials"])

    def test_fixture_contains_demo_safe_roles_gates_and_timing(self) -> None:
        data = self.load_fixture()

        self.assertEqual(
            data["party_roles"],
            ["DEMO-ROLLE-VERKAEUFER", "DEMO-ROLLE-KAEUFER", "DEMO-ROLLE-FINANZIERUNG"],
        )
        self.assertIn("gnotkg_review_required", data["gates"])
        self.assertIn("xnp_local_readiness_only", data["gates"])
        self.assertIn("grundbuch_external_boundary", data["external_boundaries"])
        self.assertIn("register_external_boundary", data["external_boundaries"])
        self.assertIn("post_beurkundung_parallel", data["parallel_groups"])
        self.assertIn("kaufpreisfaelligkeit", data["critical_path"])
        self.assertEqual(data["duration_bands"]["internal_review"], "hours_to_days")
        self.assertEqual(data["duration_bands"]["external_responses"], "weeks")
        self.assertEqual(data["duration_bands"]["complex_completion"], "weeks_to_months")

    def test_fixture_declares_first_entry_contract_without_sensitive_actions(self) -> None:
        data = self.load_fixture()

        self.assertIn("entry_contract", data)
        self.assertEqual(data["entry_contract"], "notarkammer-first-matter-demo/v0.1")
        self.assertEqual(data["primary_matter_type"], "immobilienkaufvertrag")
        self.assertEqual(data["target_systems"], ["XNP", "SNP"])
        self.assertFalse(data["mandate_data_present"])
        self.assertFalse(data["real_register_data_present"])
        self.assertFalse(data["oci_apply_permitted"])
        self.assertFalse(data["secret_material_present"])
        self.assertIn("no_oci_apply", data["demo_boundaries"])
        self.assertIn("no_secret_material", data["demo_boundaries"])
        self.assertIn("xnp_snp_target_metadata_only", data["gates"])

    def test_fixture_does_not_contain_realistic_personal_or_case_values(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
        blocked_patterns = [
            r"\b[A-ZÄÖÜ][a-zäöüß]+ [A-ZÄÖÜ][a-zäöüß]+\b",
            r"\b\d{5}\s+[A-ZÄÖÜ][A-Za-zÄÖÜäöüß-]+\b",
            r"\b\d{1,3}[.,]\d{3}[.,]\d{2}\b",
            r"\b\d{1,3}[.,]\d{3}\s*EUR\b",
            r"Grundbuchblatt\s+\d+",
            r"Flurstück\s+\d+",
            r"Token|Secret|API key|Password|Passwort|Oracle|OCI|Vault|Wallet|IdP",
            r"ofunk@|myjur\.de",
        ]
        for pattern in blocked_patterns:
            self.assertIsNone(re.search(pattern, text), pattern)

    def test_fixture_references_existing_model_artifacts(self) -> None:
        data = self.load_fixture()

        self.assertTrue((REPO_ROOT / data["bpmn_model"]).is_file())
        self.assertTrue((REPO_ROOT / data["kg_ref"]).is_file())
        self.assertTrue((REPO_ROOT / "src" / "nac_gnotkg" / "costs.py").is_file())

    def test_docs_explain_the_fixture_as_demo_metadata_not_a_real_matter(self) -> None:
        for path in (DE_DOC, EN_DOC):
            self.assertTrue(path.is_file(), path)
            content = path.read_text(encoding="utf-8")
            self.assertIn("notariat8", content)
            self.assertIn("metadata-only", content)
            self.assertIn("Immobilienkaufvertrag", content)
            self.assertIn("XNP/SNP", content)
            self.assertIn("no mandate data", content.lower())
            self.assertIn("no OCI Apply", content)
            self.assertIn("no secret", content.lower())
            self.assertIn(FIXTURE.relative_to(REPO_ROOT).as_posix(), content)
            self.assertNotIn("Oracle Cloud Infrastructure", content)


if __name__ == "__main__":
    unittest.main()
