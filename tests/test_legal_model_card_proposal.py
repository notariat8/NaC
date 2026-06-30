from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_legal_graph.model_card import (  # noqa: E402
    legal_model_card_proposal_status,
    load_model_card_proposal,
)
from scripts.validate_legal_model_card_proposal import validate  # noqa: E402


class LegalModelCardProposalTests(unittest.TestCase):
    def test_model_card_proposal_loads_without_runtime_or_checkpoint(self) -> None:
        proposal = load_model_card_proposal(REPO_ROOT)

        self.assertEqual(proposal["schema_version"], "nac.legal-model-card-proposal/v0.1")
        self.assertEqual(proposal["status"], "proposal_no_checkpoint_no_training")
        self.assertFalse(proposal["scope"]["training_enabled"])
        self.assertFalse(proposal["scope"]["checkpoint_publication_enabled"])
        self.assertFalse(proposal["scope"]["mandate_data_allowed"])
        self.assertTrue(proposal["attestations"]["no_mandate_data"])
        self.assertTrue(proposal["attestations"]["no_checkpoint_published"])
        self.assertIn("base_model_or_checkpoint", proposal["model_card_sections"])
        self.assertIn("nvidia-nemotron-pretraining-legal-v1", _candidate_ids(proposal))

    def test_model_card_status_exposes_review_boundary(self) -> None:
        status = legal_model_card_proposal_status(REPO_ROOT)

        self.assertEqual(status["schema_version"], "nac.legal-model-card-proposal-status/v0.1")
        self.assertEqual(status["status"], "proposal_no_checkpoint_no_training")
        self.assertTrue(status["owner_apply_required_before_use"])
        self.assertTrue(status["no_mandate_data"])
        self.assertTrue(status["no_checkpoint_published"])
        self.assertIn("claim_legal_answer_quality", status["blocked_actions"])

    def test_model_card_validator_accepts_repository_artifact(self) -> None:
        self.assertEqual(validate(), [])

    def test_model_card_artifact_contains_no_prohibited_payload_keys(self) -> None:
        path = (
            REPO_ROOT
            / "workflows"
            / "legal-model"
            / "model-card-proposals"
            / "legal-nemotron-metadata-only.model-card.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertFalse(_contains_key(payload, "value"))
        self.assertFalse(_contains_text(payload, "Max Mustermann"))


def _candidate_ids(proposal: dict) -> set[str]:
    return {
        item["id"]
        for item in proposal["candidate_references"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _contains_key(value: object, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


def _contains_text(value: object, text: str) -> bool:
    if isinstance(value, str):
        return text in value
    if isinstance(value, dict):
        return any(_contains_text(item, text) for item in value.values())
    if isinstance(value, list):
        return any(_contains_text(item, text) for item in value)
    return False


if __name__ == "__main__":
    unittest.main()
