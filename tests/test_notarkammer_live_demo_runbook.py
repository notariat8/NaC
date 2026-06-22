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
        runbooks = read_runbooks()
        for language, content in runbooks.items():
            self.assertIn("Live-Test", content)
            self.assertIn("Fallback", content)
            self.assertIn("Browser-Tabs vorab öffnen" if language == "de" else "Open Browser Tabs Beforehand", content)
            self.assertIn("Stop-Line", content)
            self.assertIn("T-03:00", content)
            self.assertIn("CET", content)
            self.assertIn("CEST", content)
            self.assertIn("60", content)
            self.assertIn("20", content)
            self.assertIn("5-Minuten" if language == "de" else "5-Minute", content)
            self.assertIn("https://notariat8.de", content)
            self.assertIn("https://notariat8.de/prozessmodell.html", content)
            self.assertIn("https://app.notariat8.de/healthz", content)
            self.assertIn("https://app.notariat8.de/onboarding/readiness", content)
            self.assertIn("https://app.notariat8.de/onboarding/dns-check", content)
            self.assertIn("/onboarding/requests/", content)
            self.assertIn("https://app.notariat8.de/login", content)
            self.assertIn("https://app.notariat8.de/api/tenant/login-intent", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("notarkammer-xnp-demo-contract.md", content)
            self.assertIn("notarkammer-2026-06-demo-script.md", content)
            self.assertIn("notarkammer-2026-06-demo-preflight.md", content)
            self.assertIn("Callback-URL" if language == "de" else "callback URL", content)
            self.assertIn("code" if language == "de" else "code", content)
            self.assertIn("state" if language == "de" else "state", content)

    def test_runbook_names_safe_browser_tab_order_for_demo(self) -> None:
        combined = "\n".join(read_runbooks().values())
        normalized = " ".join(combined.split())

        required_terms = [
            "Tab 1",
            "Tab 2",
            "Tab 3",
            "Tab 4",
            "Tab 5",
            "Tab 6",
            "notariat8.de",
            "prozessmodell.html",
            "onboarding/dns-check",
            "onboarding/requests/",
            "app.notariat8.de/login",
            "app.notariat8.de/workspace",
            "Keine Live-Suche",
            "No live searching",
            "keine Browser-Historie",
            "no browser history",
        ]
        for term in required_terms:
            self.assertIn(term, normalized)

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
            "Demo-Gate",
            "Demo Gate",
            "fail-closed",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_runbook_covers_current_readiness_surfaces_and_read_only_checks(self) -> None:
        combined = "\n".join(read_runbooks().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "public-onboarding",
            "public onboarding",
            "dns-check",
            "request-status",
            "request status",
            "login-intent",
            "metadata-only",
            "metadata status",
            "atp-healthcheck",
            "atp healthcheck",
            "store-gate",
            "store gate",
            "python scripts/nac.py tenant customer-plan",
            "python scripts/nac.py tenant dns-check",
            "python scripts/nac.py tenant apply-request",
            "--dry-run",
            "python scripts/nac.py bpmn validate",
            "python scripts/nac.py bpmn show immobilienkaufvertrag",
            "curl -fsS".lower(),
            "curl -i",
            "POST /onboarding/requests".lower(),
            "POST /admin/onboarding/review".lower(),
        ]
        for term in required_terms:
            self.assertIn(term.lower(), combined_lower)

    def test_runbook_has_20_minute_fallback_and_login_gate(self) -> None:
        german = RUNBOOK_DOCS["de"].read_text(encoding="utf-8")
        english = RUNBOOK_DOCS["en"].read_text(encoding="utf-8")
        normalized_german = " ".join(german.split())
        normalized_english = " ".join(english.split())

        self.assertIn("## 20-Minuten Fallback", german)
        self.assertIn("## 20-Minute Fallback", english)
        self.assertIn("Login-Flow nur bei", normalized_german)
        self.assertIn("Continue the login flow only with explicit approval", normalized_english)
        self.assertIn("fail-closed", german)
        self.assertIn("fail-closed", english)
        self.assertIn("Keine produktive XNP-Aktion", normalized_german)
        self.assertIn("Start no productive XNP action", english)

    def test_runbook_keeps_protected_pr_scope_and_demo_safety(self) -> None:
        combined = "\n".join(read_runbooks().values())
        combined_lower = " ".join(combined.lower().split())

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
            "no productive claim",
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

    def test_runbook_hides_callback_code_and_state_values_during_demo(self) -> None:
        combined = "\n".join(read_runbooks().values())
        normalized = " ".join(combined.split())

        required_terms = [
            "Callback-URL nicht vorlesen",
            "keine Werte aus `code` oder `state`",
            "Do not read the callback URL aloud",
            "no values from `code` or `state`",
            "Tab schließen oder auf `/workspace` wechseln",
            "close the tab or switch to `/workspace`",
        ]
        for term in required_terms:
            self.assertIn(term, normalized)


if __name__ == "__main__":
    unittest.main()
