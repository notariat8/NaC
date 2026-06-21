from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-live-demo-runbook.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-live-demo-runbook.md",
}


def read_runbooks() -> dict[str, str]:
    for path in RUNBOOK_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing live demo runbook: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in RUNBOOK_DOCS.items()}


class NotarkammerLiveDemoRunbookTests(unittest.TestCase):
    def test_runbook_exists_in_german_and_english(self) -> None:
        for path in RUNBOOK_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_runbook_merges_contract_script_and_preflight_into_ordered_checklist(self) -> None:
        for content in read_runbooks().values():
            self.assertIn("Live-Test", content)
            self.assertIn("Fallback", content)
            self.assertIn("Stop-Line", content)
            self.assertIn("T-03:00", content)
            self.assertIn("60", content)
            self.assertIn("5-Minuten", content)
            self.assertIn("https://notariat8.de", content)
            self.assertIn("https://notariat8.de/prozessmodell.html", content)
            self.assertIn("https://app.notariat8.de/healthz", content)
            self.assertIn("https://app.notariat8.de/login", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("notarkammer-xnp-demo-contract.md", content)
            self.assertIn("notarkammer-2026-06-demo-script.md", content)
            self.assertIn("notarkammer-2026-06-demo-preflight.md", content)

    def test_runbook_states_xnp_xnotar_xjustiz_and_nac_gate_boundary(self) -> None:
        combined = "\n".join(read_runbooks().values())

        required_terms = [
            "XNP lokal",
            "XNP local",
            "XNotar/XJustiz",
            "Übergabe",
            "handoff",
            "NaC BPMN",
            "Evidence",
            "Gate",
            "XNP liefert keine Grundbuchdaten an NaC",
            "XNP does not deliver land-register data to NaC",
            "kein automatisierter externer XNotar-Import-Trigger",
            "no automated external XNotar import trigger",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_runbook_keeps_protected_pr_scope_and_demo_safety(self) -> None:
        combined = "\n".join(read_runbooks().values())
        combined_lower = combined.lower()

        required_boundaries = [
            "docs/de",
            "docs/en",
            "tests",
            "protected pr",
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

        forbidden_terms = [
            "real client",
            "real property",
            "real identity document",
            "real deed",
            "Secret:",
            "Token:",
            "PIN 123",
            "API key:",
            "Login token:",
            "Oracle Cloud Infrastructure",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
