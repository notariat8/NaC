from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-script.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-script.md",
}


class NotarkammerDemoScriptTests(unittest.TestCase):
    def test_demo_script_exists_in_german_and_english(self) -> None:
        for path in DEMO_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_demo_script_covers_live_flow_fallbacks_and_stop_lines(self) -> None:
        german = DEMO_DOCS["de"].read_text(encoding="utf-8")
        english = DEMO_DOCS["en"].read_text(encoding="utf-8")

        for content in (german, english):
            self.assertIn("60", content)
            self.assertIn("5", content)
            self.assertIn("https://notariat8.de", content)
            self.assertIn("https://app.notariat8.de/login", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("Fallback", content)
            self.assertIn("Stop-Line", content)
            self.assertIn("Immobilienkaufvertrag", content)
            self.assertIn("Unterschriftsbeglaubigung", content)
        self.assertIn("kritischer pfad", german.lower())
        self.assertIn("critical path", english.lower())

    def test_demo_script_stays_customer_safe(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in DEMO_DOCS.values())

        blocked_terms = [
            "Oracle Cloud",
            "OCI",
            "Cloud Infrastructure",
            "Mandatsdaten anzeigen",
            "echte Akte",
            "Secret",
            "Token",
            "Nonce",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined)

    def test_demo_script_covers_xnp_xnotar_story_without_overclaiming(self) -> None:
        german = DEMO_DOCS["de"].read_text(encoding="utf-8")
        english = DEMO_DOCS["en"].read_text(encoding="utf-8")
        normalized_english = " ".join(english.split())

        for content in (german, english):
            self.assertIn("XNP", content)
            self.assertIn("XNotar", content)
            self.assertIn("XJustiz", content)
            self.assertIn("Kartenleser", content)
            lowered = content.lower()
            self.assertTrue("lokal" in lowered or "local" in lowered)
            self.assertTrue("Grundbuch" in content or "land-register" in content)

        self.assertIn("XNP liefert keine Grundbuchdaten an NaC", german)
        self.assertIn("XNP does not deliver land-register data to NaC", normalized_english)
        self.assertIn("keine produktiven Register- oder Grundbuchhandlungen", german)
        self.assertIn("productive register/land-register actions", normalized_english)


if __name__ == "__main__":
    unittest.main()
