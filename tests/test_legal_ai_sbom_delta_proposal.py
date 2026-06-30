from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_legal_graph.ai_sbom import (  # noqa: E402
    legal_ai_sbom_delta_proposal_status,
    load_ai_sbom_delta_proposal,
)
from scripts.validate_legal_ai_sbom_delta_proposal import validate  # noqa: E402


class LegalAiSbomDeltaProposalTests(unittest.TestCase):
    def test_ai_sbom_delta_proposal_loads_without_runtime_or_checkpoint(self) -> None:
        proposal = load_ai_sbom_delta_proposal(REPO_ROOT)

        self.assertEqual(proposal["schema_version"], "nac.legal-ai-sbom-delta-proposal/v0.1")
        self.assertEqual(proposal["status"], "proposal_no_runtime_no_checkpoint")
        self.assertFalse(proposal["scope"]["runtime_activation_enabled"])
        self.assertFalse(proposal["scope"]["endpoint_enabled"])
        self.assertFalse(proposal["scope"]["checkpoint_publication_enabled"])
        self.assertFalse(proposal["scope"]["mandate_data_allowed"])
        self.assertTrue(proposal["attestations"]["no_mandate_data"])
        self.assertTrue(proposal["attestations"]["no_runtime_enabled"])
        self.assertIn("risk_controls", _component_ids(proposal))
        self.assertIn("recht-bund-bgbl-data-access", _candidate_ids(proposal))

    def test_ai_sbom_delta_status_exposes_review_boundary(self) -> None:
        status = legal_ai_sbom_delta_proposal_status(REPO_ROOT)
        component_ids = {item["id"] for item in status["delta_components"]}

        self.assertEqual(status["schema_version"], "nac.legal-ai-sbom-delta-proposal-status/v0.1")
        self.assertEqual(status["status"], "proposal_no_runtime_no_checkpoint")
        self.assertTrue(status["owner_apply_required_before_runtime_or_checkpoint"])
        self.assertTrue(status["no_mandate_data"])
        self.assertTrue(status["no_source_text_stored"])
        self.assertTrue(status["no_checkpoint_published"])
        self.assertTrue(status["no_runtime_enabled"])
        self.assertTrue(status["no_endpoint_enabled"])
        self.assertIn("training_or_evaluation_runtime", component_ids)
        self.assertIn("activate_model_endpoint_from_ai_sbom_delta", status["blocked_actions"])

    def test_ai_sbom_delta_validator_accepts_repository_artifact(self) -> None:
        self.assertEqual(validate(), [])

    def test_ai_sbom_delta_artifact_contains_no_prohibited_payload_keys(self) -> None:
        path = (
            REPO_ROOT
            / "workflows"
            / "legal-model"
            / "ai-sbom-deltas"
            / "legal-nemotron-metadata-only.ai-sbom-delta.json"
        )
        payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertFalse(_contains_key(payload, "value"))
        self.assertFalse(_contains_text(payload, "Max Mustermann"))


def _component_ids(proposal: dict) -> set[str]:
    return {
        item["id"]
        for item in proposal["delta_components"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }


def _candidate_ids(proposal: dict) -> set[str]:
    return {
        item["id"]
        for item in proposal["candidate_components"]
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
