from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-preflight.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-preflight.md",
}


def read_preflight_docs() -> list[str]:
    for path in PREFLIGHT_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing preflight checklist: {path}")
    return [path.read_text(encoding="utf-8") for path in PREFLIGHT_DOCS.values()]


class NotarkammerDemoPreflightTests(unittest.TestCase):
    def test_preflight_checklist_exists_in_german_and_english(self) -> None:
        for path in PREFLIGHT_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_preflight_checklist_covers_live_browser_gates(self) -> None:
        for content in read_preflight_docs():
            self.assertIn("T-03:00", content)
            self.assertIn("1h", content)
            self.assertIn("CET", content)
            self.assertIn("CEST", content)
            self.assertIn("https://notariat8.de", content)
            self.assertIn("https://notariat8.de/prozessmodell.html", content)
            self.assertIn("https://app.notariat8.de/healthz", content)
            self.assertIn("https://app.notariat8.de/onboarding/readiness", content)
            self.assertIn("https://app.notariat8.de/onboarding/dns-check", content)
            self.assertIn("/onboarding/requests/", content)
            self.assertIn("https://app.notariat8.de/login", content)
            self.assertIn("https://app.notariat8.de/api/tenant/login-intent", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("Fallback", content)
            self.assertIn("Stop-Line", content)
            self.assertIn("Owner-Gate", content)

    def test_preflight_checklist_has_exact_read_only_demo_checks(self) -> None:
        for content in read_preflight_docs():
            heading = (
                "What Can Be Shown Today"
                if "What Can Be Shown Today" in content
                else "Was Heute Gezeigt Werden Kann"
            )
            self.assertIn(heading, content)
            self.assertIn("python scripts/nac.py tenant customer-plan", content)
            self.assertIn("python scripts/nac.py tenant dns-check", content)
            self.assertIn("python scripts/nac.py tenant apply-request", content)
            self.assertIn("--dry-run", content)
            self.assertIn("python scripts/nac.py bpmn validate", content)
            self.assertIn("python scripts/nac.py bpmn show immobilienkaufvertrag", content)
            self.assertIn("curl -fsS", content)
            self.assertIn("curl -i", content)
            self.assertIn("metadata", content.lower())
            self.assertIn("ATP", content)
            self.assertIn("healthcheck", content.lower())
            self.assertTrue("store gate" in content.lower() or "store-gate" in content.lower())

    def test_preflight_checklist_covers_xnp_reader_xnotar_xjustiz_gates(self) -> None:
        for content in read_preflight_docs():
            content_lower = content.lower()
            self.assertIn("XNP", content)
            self.assertTrue("card" in content_lower or "karte" in content_lower)
            self.assertTrue("reader" in content_lower or "leser" in content_lower)
            self.assertIn("SAK", content)
            self.assertIn("secureFramework", content)
            self.assertIn("12774", content)
            self.assertIn("12784", content)
            self.assertIn("XNotar", content)
            self.assertIn("XJustiz", content)
            self.assertIn("Audit", content)
            self.assertIn("Protected PR", content)
            self.assertIn("manual_review", content)
            self.assertIn("blocked", content)

    def test_preflight_checklist_stays_demo_safe(self) -> None:
        combined = "\n".join(read_preflight_docs())
        combined_lower = combined.lower()

        required_boundaries = [
            "synthetic",
            "no real mandate data",
            "no secrets",
            "no release",
            "no apply",
            "no runtime change",
            "no cloud change",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined_lower)

        blocked_terms = [
            "real client",
            "real property",
            "real identity document",
            "real deed",
            "Secret:",
            "Token:",
            "PIN 123",
            "API key:",
            "Login token:",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined)

    def test_preflight_scope_is_documentation_and_tests_only(self) -> None:
        combined = "\n".join(read_preflight_docs())

        self.assertIn("docs/de/demo/", combined)
        self.assertIn("docs/en/demo/", combined)
        self.assertIn("tests/", combined)
        self.assertIn("No OCI", combined)
        self.assertIn("runtime", combined.lower())
        self.assertIn("infrastructure", combined.lower())


if __name__ == "__main__":
    unittest.main()
