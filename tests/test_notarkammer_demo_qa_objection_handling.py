from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QA_DOCS = {
    "de": REPO_ROOT
    / "docs"
    / "de"
    / "demo"
    / "notarkammer-2026-06-demo-qa-objection-handling.md",
    "en": REPO_ROOT
    / "docs"
    / "en"
    / "demo"
    / "notarkammer-2026-06-demo-qa-objection-handling.md",
}


def read_qa_docs() -> dict[str, str]:
    for path in QA_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing Notarkammer demo Q&A: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in QA_DOCS.items()}


class NotarkammerDemoQaObjectionHandlingTests(unittest.TestCase):
    def test_qa_exists_in_german_and_english(self) -> None:
        for path in QA_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_qa_links_existing_demo_runbooks_and_source_matrix(self) -> None:
        docs = read_qa_docs()
        combined = "\n".join(docs.values())

        required_links = [
            "notarkammer-2026-06-live-demo-runbook.md",
            "notarkammer-2026-06-demo-script.md",
            "notarkammer-2026-06-demo-preflight.md",
            "notarkammer-xnp-demo-contract.md",
            "../research/notarkammer-demo-vollzug.md",
        ]
        for link in required_links:
            self.assertIn(link, combined)

        for language, path in QA_DOCS.items():
            content = docs[language]
            for link in required_links:
                self.assertIn(link, content)
                self.assertTrue((path.parent / link).resolve().is_file(), link)

    def test_qa_answers_expected_notarkammer_questions(self) -> None:
        combined = "\n".join(read_qa_docs().values())

        required_terms = [
            "2-Minuten-Auftakt",
            "2-Minute Opening",
            "notariat8 zeigt nicht eine weitere Maske",
            "notariat8 does not show yet another screen",
            "BPMN, Dauer, Parallelität und kritischer Pfad",
            "BPMN, duration, parallel work and critical path",
            "Was zeigt NaC live?",
            "What does NaC show live?",
            "Was macht XNP",
            "What does XNP do",
            "Wird produktiv eingereicht?",
            "Is anything filed productively?",
            "Wo läuft der Kartenleser?",
            "Where does the card reader run?",
            "Grundbuch- und Register-Rückläufe",
            "land-register and register responses",
            "kritische Pfad",
            "critical path",
            "Was ist noch nicht produktiv?",
            "What is not productive yet?",
            "Wie bleiben Mandatsdaten geschützt?",
            "How is mandate data protected?",
            "wenn Login nicht klappt",
            "if login fails",
            "wenn XNP oder Kartenleser nicht verfügbar",
            "if XNP or the card reader is unavailable",
            "wenn die Website nicht erreichbar",
            "if the website is unavailable",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_qa_states_demo_boundaries_without_productive_claims(self) -> None:
        combined = "\n".join(read_qa_docs().values())
        normalized = " ".join(combined.split())

        required_boundaries = [
            "keine produktive Einreichung",
            "no productive filing",
            "keine Anbieter- oder Betreiberdetails",
            "no provider or operator details",
            "keine Secrets",
            "no secrets",
            "keine Mandatsdaten",
            "no mandate data",
            "keine Rechtsberatung",
            "not legal advice",
            "XNP liefert keine Grundbuchdaten an NaC",
            "XNP does not deliver land-register data to NaC",
            "Kartenleser läuft am freigegebenen lokalen Arbeitsplatz",
            "card reader runs on the approved local workstation",
            "fail-closed",
            "manual_review",
            "blocked",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, normalized)

        forbidden_claims = [
            "produktive XNP-Automation ist freigegeben",
            "productive XNP automation is approved",
            "direkte Grundbuchdatenübernahme ist live",
            "direct land-register data intake is live",
            "XNP liefert Grundbuchdaten",
            "XNP returns land-register data",
            "Cloud steuert XNP",
            "cloud controls XNP",
            "automated XNotar import trigger",
            "automatisierter XNotar-Import-Trigger",
            "echte Mandatsdaten",
            "real mandate data",
            "API key:",
            "Token:",
            "PIN 123",
            "Oracle Cloud",
            "OCI",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim, combined)


if __name__ == "__main__":
    unittest.main()
