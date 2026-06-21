from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPTH_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-xnp-bpmn-demo-depth.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-xnp-bpmn-demo-depth.md",
}


def read_depth_docs() -> dict[str, str]:
    for path in DEPTH_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing XNP/BPMN demo depth artifact: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in DEPTH_DOCS.items()}


class NotarkammerXnpBpmnDemoDepthTests(unittest.TestCase):
    def test_depth_artifact_exists_in_german_and_english(self) -> None:
        for path in DEPTH_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_artifact_maps_notarial_boundaries_to_bpmn_task_types(self) -> None:
        combined = "\n".join(read_depth_docs().values())

        required_terms = [
            "Service Task",
            "User Task",
            "Manual Task",
            "XNP",
            "XNotar/XJustiz",
            "Grundbuch",
            "Register",
            "Kartenleser",
            "card reader",
            "Signatur",
            "signature",
            "externe Nachweise",
            "external evidence",
            "externe Systemgrenze",
            "external system boundary",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_artifact_keeps_xnp_external_and_avoids_live_api_claims(self) -> None:
        combined = "\n".join(read_depth_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_boundaries = [
            "XNP bleibt eine externe notarielle Arbeitsumgebung",
            "XNP remains an external notarial work environment",
            "keine Live-XNP-API-Zugriffe",
            "no live XNP API access",
            "keine produktive XNP-Handlung",
            "no productive XNP action",
            "keine direkte XNP-zu-NaC-Grundbuchdatenlieferung",
            "no direct XNP-to-NaC land-register data delivery",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary.lower(), combined_lower)

        forbidden_claims = [
            "XNP API is live",
            "live XNP integration",
            "productive XNP integration",
            "NaC steuert XNP produktiv",
            "NaC ruft XNP live auf",
            "XNP liefert Grundbuchdaten an NaC",
            "XNP returns land-register data to NaC",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim.lower(), combined_lower)

    def test_artifact_mentions_duration_critical_path_and_parallelism(self) -> None:
        combined = "\n".join(read_depth_docs().values())

        required_terms = [
            "Dauerband",
            "duration band",
            "Kritischer Pfad",
            "critical path",
            "Parallelität",
            "parallelism",
            "2-8 Wochen",
            "2-8 weeks",
            "fail-closed",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_artifact_is_notariat_only_and_excludes_sensitive_raw_data(self) -> None:
        combined = "\n".join(read_depth_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_guardrails = [
            "Notariat-only",
            "notary-only",
            "keine Rohdaten",
            "no raw data",
            "keine Mandatsdaten",
            "no mandate data",
            "nur redigierte Evidence",
            "redacted evidence only",
        ]
        for guardrail in required_guardrails:
            self.assertIn(guardrail.lower(), combined_lower)

        forbidden_patterns = [
            r"steuerb[uü]ro",
            r"tax office",
            r"softwareunternehmen",
            r"software company",
            r"\boci\b",
            r"oracle cloud",
            r"tenancy",
            r"ocid",
            r"secret:",
            r"token:",
            r"api[_ -]?key:",
            r"pin\s*123",
            r"mandant:",
            r"aktenzeichen:",
            r"urkundennummer:",
            r"real client",
            r"real deed",
            r"real property",
        ]
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, combined_lower), pattern)


if __name__ == "__main__":
    unittest.main()
