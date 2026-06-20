from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RESEARCH_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "research" / "notarkammer-demo-vollzug.md",
    "en": REPO_ROOT / "docs" / "en" / "research" / "notarkammer-demo-vollzug.md",
}


class NotarkammerDemoResearchTests(unittest.TestCase):
    def test_research_note_exists_in_german_and_english(self) -> None:
        for path in RESEARCH_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_research_note_covers_duration_parallelism_and_sources(self) -> None:
        german = RESEARCH_DOCS["de"].read_text(encoding="utf-8")
        english = RESEARCH_DOCS["en"].read_text(encoding="utf-8")

        for content in (german, english):
            self.assertIn("https://www.notar.de/themen/immobilien/kaufpreisfaelligkeit", content)
            self.assertIn("https://www.notar.de/themen/immobilien/eigentumsuebergang", content)
            self.assertIn("https://www.notar.de/themen/notarkosten", content)
            self.assertIn("https://www.notar.de/themen/notarkosten/gebuehrenrechner", content)
            self.assertIn("hours", content.lower())
            self.assertIn("days", content.lower())
            self.assertIn("weeks", content.lower())
            self.assertIn("months", content.lower())

        self.assertIn("kritischer pfad", german.lower())
        self.assertIn("critical path", english.lower())
        self.assertIn("keine amtlichen durchschnittswerte", german.lower())
        self.assertIn("not official averages", english.lower())

    def test_research_note_stays_demo_safe(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in RESEARCH_DOCS.values())

        blocked_terms = [
            "Mandatsdaten anzeigen",
            "echte Akte",
            "Secret",
            "Token",
            "Nonce",
            "Cloud Infrastructure",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
