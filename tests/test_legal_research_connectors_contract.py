from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "legal-research-connectors.contract.json"


class LegalResearchConnectorsContractTests(unittest.TestCase):
    def load_contract(self) -> dict:
        return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_records_candidate_sources_without_tracking_urls(self) -> None:
        payload = self.load_contract()
        candidates = {candidate["id"]: candidate for candidate in payload["candidates"]}

        self.assertEqual(payload["contract_id"], "workflow.legal_research_connectors")
        self.assertGreaterEqual(
            set(candidates),
            {
                "connector-reference-kloetzkette-claude-recht",
                "ansvar-german-law-mcp-lobehub",
                "ansvar-german-law-mcp-elasticflow",
                "beck-online-mcp-market",
                "deubner-recht-publisher-portal",
                "nvidia-nemotron-pretraining-legal-v1",
                "recht-bund-bgbl-data-access",
                "wikipedia-rechtsquelle-concept-reference",
            },
        )
        for candidate in candidates.values():
            parsed = urlparse(candidate["canonical_url"])
            self.assertIn(parsed.scheme, {"http", "https"})
            self.assertEqual(parsed.query, "", candidate["canonical_url"])
            self.assertNotIn("shem=", candidate["canonical_url"])

    def test_deubner_candidate_is_metadata_only_until_license_review(self) -> None:
        payload = self.load_contract()
        candidates = {candidate["id"]: candidate for candidate in payload["candidates"]}
        candidate = candidates["deubner-recht-publisher-portal"]

        self.assertEqual(candidate["provider"], "Deubner Recht & Steuern")
        self.assertEqual(candidate["integration_level"], "metadata_only")
        self.assertEqual(candidate["status"], "needs_license_review")
        self.assertTrue(candidate["credentials_required"])
        self.assertFalse(candidate["credentials_in_repo_allowed"])
        self.assertFalse(candidate["personal_data_allowed"])
        self.assertTrue(candidate["license_review_required"])
        self.assertIn("automated_provider_query_without_contract", candidate["blocked_actions"])
        self.assertIn("store_provider_full_text_in_product_repo", candidate["blocked_actions"])

    def test_legal_model_customization_candidates_are_blocked_until_review(self) -> None:
        payload = self.load_contract()
        candidates = {candidate["id"]: candidate for candidate in payload["candidates"]}
        nemotron = candidates["nvidia-nemotron-pretraining-legal-v1"]
        recht_bund = candidates["recht-bund-bgbl-data-access"]
        rechtsquelle = candidates["wikipedia-rechtsquelle-concept-reference"]

        self.assertEqual(nemotron["source_type"], "training_dataset_candidate")
        self.assertEqual(nemotron["integration_level"], "metadata_only")
        self.assertTrue(nemotron["license_review_required"])
        self.assertEqual(nemotron["ai_sbom_status"], "pending")
        self.assertIn("start_finetuning_without_owner_apply", nemotron["blocked_actions"])
        self.assertIn("treat_dataset_as_german_law_source", nemotron["blocked_actions"])

        self.assertEqual(recht_bund["source_type"], "official_publication_data_access")
        self.assertIn("bulk_crawl_without_terms_review", recht_bund["blocked_actions"])
        self.assertIn("train_on_pdf_full_text_without_normalization_and_review", recht_bund["blocked_actions"])

        self.assertEqual(rechtsquelle["source_type"], "concept_reference")
        self.assertEqual(rechtsquelle["status"], "concept_anchor_only")
        self.assertIn("treat_concept_reference_as_primary_legal_source", rechtsquelle["blocked_actions"])

    def test_contract_blocks_credentials_and_mandate_data_until_review(self) -> None:
        payload = self.load_contract()
        policy = payload["candidate_policy"]

        self.assertFalse(policy["credentials_allowed_in_repo"])
        self.assertFalse(policy["production_mandate_data_allowed"])
        self.assertTrue(policy["requires_terms_review"])
        self.assertTrue(policy["requires_avv_review_for_personal_data"])
        self.assertTrue(policy["requires_human_legal_review"])
        self.assertTrue(policy["requires_source_attribution"])

    def test_validator_accepts_contract(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_legal_research_connectors.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


if __name__ == "__main__":
    unittest.main()
