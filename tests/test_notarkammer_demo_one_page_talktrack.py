from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TALKTRACK_DOCS = {
    "de": REPO_ROOT
    / "docs"
    / "de"
    / "demo"
    / "notarkammer-2026-06-one-page-talktrack.md",
    "en": REPO_ROOT
    / "docs"
    / "en"
    / "demo"
    / "notarkammer-2026-06-one-page-talktrack.md",
}


def combined_talktrack_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in TALKTRACK_DOCS.values()
        if path.is_file()
    )


class NotarkammerDemoOnePageTalktrackTests(unittest.TestCase):
    def test_one_page_talktrack_exists_in_german_and_english(self) -> None:
        for path in TALKTRACK_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_talktrack_states_demo_goal_and_primary_flow(self) -> None:
        combined = combined_talktrack_text()

        required_terms = [
            "XNP/SNP-Testzugang",
            "XNP/SNP test access",
            "ISV-Listung",
            "ISV listing",
            "Immobilienkaufvertrag",
            "real estate purchase agreement",
            "Primärvorgang",
            "primary proceeding",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_talktrack_covers_bpmn_boundaries(self) -> None:
        combined = combined_talktrack_text()

        required_terms = [
            "BPMN",
            "XNP",
            "XNotar",
            "Kartenleser",
            "card reader",
            "Register",
            "register",
            "Grundbuch",
            "land register",
            "Vollzug",
            "closing",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_talktrack_keeps_demo_non_claims_explicit(self) -> None:
        combined = combined_talktrack_text()

        required_terms = [
            "keine produktive XNP-Aktion",
            "no productive XNP action",
            "keine Mandatsdaten",
            "no matter data",
            "keine echten Register-/Grundbuchabfragen",
            "no real register or land-register queries",
            "keine OCI-Aktionen",
            "no OCI actions",
            "keine Secrets",
            "no secrets",
            "keine Live-Calls",
            "no live calls",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

        forbidden_terms = [
            "NaC hat produktiven XNP/SNP-Zugriff",
            "NaC has productive XNP/SNP access",
            "NaC steuert XNP produktiv",
            "NaC controls XNP productively",
            "echte Grundbuchabfrage",
            "real land-register query",
            "Mandatsdaten anzeigen",
            "display matter data",
            "OCI apply",
            "Live API call",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)

    def test_talktrack_is_compact_one_page_format(self) -> None:
        for path in TALKTRACK_DOCS.values():
            self.assertTrue(path.is_file(), path)
            lines = [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertLessEqual(len(lines), 45, path)


if __name__ == "__main__":
    unittest.main()
