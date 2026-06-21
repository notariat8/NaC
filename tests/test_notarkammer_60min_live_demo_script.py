from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-60-minute-live-demo-script.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-60-minute-live-demo-script.md",
}


def read_scripts() -> dict[str, str]:
    for path in SCRIPT_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing 60-minute live demo script: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in SCRIPT_DOCS.items()}


def headings(content: str) -> list[str]:
    return [line.strip() for line in content.splitlines() if line.startswith("## ")]


class Notarkammer60MinuteLiveDemoScriptTests(unittest.TestCase):
    def test_script_exists_in_german_and_english(self) -> None:
        for path in SCRIPT_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_german_and_english_have_matching_operational_sections(self) -> None:
        scripts = read_scripts()

        expected_heading_counts = {
            "Purpose": 2,
            "Safety Frame": 2,
            "Browser Start Points": 2,
            "60-Minute Live Order": 2,
            "Failover Cards": 2,
            "Boundaries And Access Points": 2,
            "Closing Evidence": 2,
        }
        combined_headings = "\n".join(
            heading for script in scripts.values() for heading in headings(script)
        )
        for section, expected_count in expected_heading_counts.items():
            self.assertEqual(
                expected_count,
                combined_headings.count(section),
                f"Section parity failed for {section}",
            )

    def test_script_names_browser_start_points_and_expected_visible_results(self) -> None:
        for content in read_scripts().values():
            for url in (
                "https://notariat8.de",
                "https://notariat8.de/prozessmodell.html",
                "https://app.notariat8.de/healthz",
                "https://app.notariat8.de/login",
                "https://app.notariat8.de/workspace",
            ):
                self.assertIn(url, content)

            self.assertIn("Expected visible result", content)
            self.assertIn("visible result", content.lower())
            self.assertIn("public start page", content.lower())
            self.assertIn("process model", content.lower())
            self.assertIn("protected workspace", content.lower())
            self.assertRegex(content, r"0-5")
            self.assertRegex(content, r"55-60")

    def test_script_covers_required_failovers_without_live_debugging(self) -> None:
        combined = "\n".join(read_scripts().values())
        required_failovers = (
            "www-n8 does not load",
            "app login only shows the OIDC interstitial",
            "XNP/card reader is unavailable",
            "BPMN viewer does not load",
            "do not debug live",
            "use a prepared screenshot",
            "fail-closed",
            "manual_review",
            "blocked",
        )
        for phrase in required_failovers:
            self.assertIn(phrase, combined)

    def test_script_treats_xnp_card_reader_register_and_land_register_as_boundaries(self) -> None:
        combined = "\n".join(read_scripts().values())
        required_boundaries = (
            "XNP is a local workstation boundary",
            "Kartenleser/card reader is an access point",
            "Register is an external destination",
            "Grundbuch/land register is an external destination",
            "XNP does not deliver land-register data to NaC",
            "no productive submission",
            "no real mandate data",
            "no secrets",
            "Protected PR only",
        )
        for phrase in required_boundaries:
            self.assertIn(phrase, combined)

    def test_script_keeps_provider_internals_and_sensitive_data_out(self) -> None:
        combined = "\n".join(read_scripts().values())
        combined_lower = combined.lower()

        forbidden_patterns = (
            r"\boci\b",
            r"oracle cloud",
            r"tenancy",
            r"ocid",
            r"api[_ -]?key",
            r"secret:",
            r"token:",
            r"pin\s*123",
            r"real client",
            r"real deed",
            r"real property",
            r"mandatsdaten\s+anzeigen",
            r"productive filing",
            r"productive register submission",
            r"productive land-register submission",
        )
        for pattern in forbidden_patterns:
            self.assertIsNone(re.search(pattern, combined_lower), pattern)


if __name__ == "__main__":
    unittest.main()
