from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-script.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-script.md",
}


def markdown_section(content: str, heading: str) -> str:
    start = content.index(heading)
    rest = content[start + len(heading):]
    next_heading = rest.find("\n### ")
    if next_heading == -1:
        next_heading = rest.find("\n## ")
    if next_heading == -1:
        return rest
    return rest[:next_heading]


class NotarkammerDemoScriptTests(unittest.TestCase):
    def test_demo_script_exists_in_german_and_english(self) -> None:
        for path in DEMO_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_demo_script_covers_live_flow_fallbacks_and_stop_lines(self) -> None:
        german = DEMO_DOCS["de"].read_text(encoding="utf-8")
        english = DEMO_DOCS["en"].read_text(encoding="utf-8")

        for content in (german, english):
            self.assertIn("60", content)
            self.assertIn("20", content)
            self.assertIn("5", content)
            self.assertIn("https://notariat8.de", content)
            self.assertIn("https://notariat8.de/prozessmodell.html", content)
            self.assertIn("https://app.notariat8.de/login", content)
            self.assertIn("https://app.notariat8.de/onboarding/readiness", content)
            self.assertIn("https://app.notariat8.de/onboarding/dns-check", content)
            self.assertIn("https://app.notariat8.de/api/tenant/login-intent", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("Fallback", content)
            self.assertIn("Stop-Line", content)
            self.assertIn("Immobilienkaufvertrag", content)
            self.assertIn("Unterschriftsbeglaubigung", content)
            self.assertIn("CET", content)
            self.assertIn("CEST", content)
        self.assertIn("kritischer pfad", german.lower())
        self.assertIn("critical path", english.lower())
        self.assertIn("20-Minuten-Fallback", german)
        self.assertIn("20-Minute Fallback", english)

    def test_demo_script_covers_current_showable_readiness_tracks(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in DEMO_DOCS.values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "public onboarding",
            "Public Onboarding",
            "DNS",
            "Request-Status",
            "request status",
            "metadata-only",
            "ATP-Healthcheck",
            "ATP healthcheck",
            "Store-Gate",
            "store gate",
            "python scripts/nac.py tenant customer-plan",
            "python scripts/nac.py tenant dns-check",
            "python scripts/nac.py bpmn validate",
            "no forms",
            "keine neue Onboarding-Anfrage",
            "submit a new onboarding request",
        ]
        for term in required_terms:
            self.assertIn(term.lower(), combined_lower)

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
            "produktive XNP-Handlung ausführen",
            "productive XNP action is executed",
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
        self.assertIn("XNP, Kartenleser, SAK lite, secureFramework", german)
        self.assertIn("XNP, Kartenleser card reader, SAK lite, secureFramework", english)
        self.assertIn("Login-Flow wird nur fortgesetzt", german)
        self.assertIn("continue the login flow only when the demo session is approved", english)
        self.assertIn("fail-closed", german)
        self.assertIn("fail-closed", english)

    def test_login_intent_stays_redacted_preparation_evidence(self) -> None:
        german = DEMO_DOCS["de"].read_text(encoding="utf-8")
        english = DEMO_DOCS["en"].read_text(encoding="utf-8")
        normalized_german = " ".join(german.split())
        normalized_english = " ".join(english.split())

        self.assertIn("redigierter technischer Vorbereitungsnachweis", normalized_german)
        self.assertIn("keine Browserfläche", normalized_german)
        self.assertIn("redacted technical preparation evidence", normalized_english)
        self.assertIn("not a browser surface", normalized_english)

        visible_sections = [
            markdown_section(german, "### 43-52 Minuten: App-Einstieg und geschützter Arbeitsbereich"),
            markdown_section(english, "### 43-52 Minutes: App Entry And Protected Workspace"),
        ]
        for section in visible_sections:
            self.assertNotIn("api/tenant/login-intent", section)


if __name__ == "__main__":
    unittest.main()
