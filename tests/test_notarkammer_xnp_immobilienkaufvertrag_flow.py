from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FLOW_DOCS = {
    "de": REPO_ROOT
    / "docs"
    / "de"
    / "demo"
    / "notarkammer-immobilienkaufvertrag-xnp-vollzug-map.md",
    "en": REPO_ROOT
    / "docs"
    / "en"
    / "demo"
    / "notarkammer-immobilienkaufvertrag-xnp-vollzug-map.md",
}


def combined_flow_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FLOW_DOCS.values())


class NotarkammerXnpImmobilienkaufvertragFlowTests(unittest.TestCase):
    def test_flow_map_exists_in_german_and_english(self) -> None:
        for path in FLOW_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_flow_map_names_repeated_xnp_xnotar_and_completion_gates(self) -> None:
        combined = combined_flow_text()

        required_terms = [
            "Immobilienkaufvertrag",
            "real estate purchase agreement",
            "XNP/SNP-Testzugang",
            "XNP/SNP test access",
            "XNotar",
            "Kartenleser",
            "card reader",
            "Grundbuch",
            "land register",
            "beN",
            "Vollzug",
            "closing",
            "Auflassungsvormerkung",
            "priority notice",
            "Vorkaufsrecht",
            "right of first refusal",
            "Unbedenklichkeitsbescheinigung",
            "tax clearance certificate",
            "Löschungsunterlagen",
            "deletion documents",
            "Eigentumsumschreibung",
            "transfer of title",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_flow_map_contains_duration_parallel_and_critical_path_contract(self) -> None:
        combined = combined_flow_text()

        required_terms = [
            "same_day_or_internal",
            "short_party_turnaround",
            "standard_external",
            "extended_external",
            "parallelGroup",
            "pre_notarization_due_diligence",
            "post_notarization_completion",
            "ownership_transfer",
            "criticalPath",
            "kritischer Pfad",
            "critical path",
            "2-8 Wochen",
            "2-8 weeks",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_flow_map_keeps_api_access_questions_explicit_and_safe(self) -> None:
        combined = combined_flow_text()

        required_terms = [
            "ISV-Frage",
            "ISV question",
            "Testumgebung",
            "test environment",
            "Status-Callback",
            "status callback",
            "Evidence-Feld",
            "evidence field",
            "keine produktive XNP-Handlung",
            "no productive XNP action",
            "keine Mandatsdaten",
            "no matter data",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

        forbidden_terms = [
            "NaC hat produktiven XNP/SNP-Zugriff",
            "NaC has productive XNP/SNP access",
            "NaC steuert XNP",
            "NaC controls XNP",
            "Grundbuchdaten werden automatisch übernommen",
            "land-register data is imported automatically",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
