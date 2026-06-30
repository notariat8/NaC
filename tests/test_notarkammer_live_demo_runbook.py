from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNBOOK_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-live-demo-runbook.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-live-demo-runbook.md",
}
DEMO_DNS_CHECK_URL = (
    "https://app.notariat8.de/onboarding/dns-check?"
    "audience=customer&domain=kanzlei-notariat.example&tenant_slug=kanzlei-notariat"
    "&admin_email=admin%40kanzlei-notariat.example"
)


def read_runbooks() -> dict[str, str]:
    for path in RUNBOOK_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing live demo runbook: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in RUNBOOK_DOCS.items()}


def markdown_section(content: str, heading: str) -> str:
    start = content.index(heading)
    rest = content[start + len(heading):]
    next_heading = rest.find("\n## ")
    if next_heading == -1:
        return rest
    return rest[:next_heading]


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
            "/home/ubuntu/.venvs/nac/bin/python scripts/nac.py tenant customer-plan",
            "/home/ubuntu/.venvs/nac/bin/python scripts/nac.py tenant dns-check",
            "/home/ubuntu/.venvs/nac/bin/python scripts/nac.py tenant apply-request",
            "--dry-run",
            "/home/ubuntu/.venvs/nac/bin/python scripts/nac.py bpmn validate",
            "/home/ubuntu/.venvs/nac/bin/python scripts/nac.py bpmn show immobilienkaufvertrag",
            "curl -fsS".lower(),
            "curl -i",
            "POST /onboarding/requests".lower(),
            "POST /admin/onboarding/review".lower(),
        ]
        for term in required_terms:
            self.assertIn(term.lower(), combined_lower)
        bare_python_commands = [
            line.strip()
            for line in combined.splitlines()
            if line.strip().startswith("python scripts/nac.py")
        ]
        self.assertEqual([], bare_python_commands)

    def test_runbook_uses_exact_synthetic_dns_demo_url(self) -> None:
        for content in read_runbooks().values():
            self.assertIn(DEMO_DNS_CHECK_URL, content)
            self.assertNotIn("https://app.notariat8.de/onboarding/dns-check?...", content)

    def test_runbook_has_fillable_t15_t03_evidence_capture_table(self) -> None:
        combined = "\n".join(read_runbooks().values())
        normalized = " ".join(combined.split())

        required_terms = [
            "T-15/T-03 Evidence Capture",
            "T-15/T-03 Evidenz-Erfassung",
            "Evidence-ID",
            "Command or view",
            "Befehl oder Sicht",
            "Expected result",
            "Erwartetes Ergebnis",
            "Actual result",
            "Tatsächliches Ergebnis",
            "Redaction status",
            "Redaktionsstatus",
            "Fallback decision",
            "Fallback-Entscheidung",
            "NK-EVID-001",
            "NK-EVID-002",
            "NK-EVID-003",
            "NK-EVID-004",
            "notarkammer_demo_smoke.py --timeout-seconds 20 --summary-only",
            "no response body preview",
            "keine Response-Body-Vorschau",
            "no secrets",
            "keine Secrets",
            "no mandate data",
            "keine Mandatsdaten",
        ]
        for term in required_terms:
            self.assertIn(term, normalized)

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

    def test_runbook_contains_redacted_login_triage_without_sensitive_values(self) -> None:
        combined = "\n".join(read_runbooks().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "login-triage",
            "token-austausch",
            "token exchange",
            "missing_id_token",
            "token_response_not_json",
            "id_token_verification_failed",
            "anmeldung technisch nicht verfügbar",
            "technically unavailable",
            "ungültig",
            "invalid",
            "keine tokens",
            "no tokens",
            "keine claims",
            "no claims",
            "keine provider-details",
            "no provider details",
            "keine callback-werte",
            "no callback values",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

        forbidden_terms = [
            "code=",
            "state=",
            "nonce=",
            "id_token=",
            "access_token=",
            "client_secret",
            "idcs-",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined_lower)

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

    def test_runbook_defines_show_mode_boundary(self) -> None:
        combined = "\n".join(read_runbooks().values())
        normalized = " ".join(combined.split())
        normalized_lower = normalized.lower()
        combined_lower = combined.lower()

        required_exact_terms = [
            "## Vorführmodus",
            "## Show Mode",
            "Adresszeile wird nicht vorgelesen",
            "Fallback-Evidence",
            "Tab schließen",
        ]
        required_lower_terms = [
            "one browser window",
            "einem browserfenster",
            "notariat8.de/prozessmodell.html",
            "app.notariat8.de/login",
            "app.notariat8.de/workspace",
            "browser address bar is not narrated",
            "no JSON endpoint is shown as a user interface",
            "kein JSON-Endpunkt als Benutzeroberfläche",
            "Login-Intent nur als redigierter CLI-/curl-Check",
            "Login intent as redacted CLI/curl check only",
            "not as a browser tab",
            "nicht als Browser-Tab",
            "fallback evidence",
            "close the tab",
        ]
        for term in required_exact_terms:
            self.assertIn(term, normalized)
        for term in required_lower_terms:
            self.assertIn(term.lower(), normalized_lower)

        forbidden_show_mode_terms = [
            "cloud console",
            "resource manager",
            "vault",
            "wallet",
            "secret value",
            "client secret",
            "callback code",
            "callback state",
        ]
        show_mode_sections = [
            section for section in combined_lower.split("## ") if section.startswith(("vorführmodus", "show mode"))
        ]
        self.assertEqual(2, len(show_mode_sections))
        for section in show_mode_sections:
            for term in forbidden_show_mode_terms:
                self.assertNotIn(term, section)

    def test_login_intent_is_not_visible_show_surface(self) -> None:
        german = RUNBOOK_DOCS["de"].read_text(encoding="utf-8")
        english = RUNBOOK_DOCS["en"].read_text(encoding="utf-8")
        normalized_german = " ".join(german.split())
        normalized_english = " ".join(english.split())

        self.assertIn("Login-Intent bleibt ein redigierter Read-only-Check", normalized_german)
        self.assertIn("keine sichtbare Nutzerfläche", normalized_german)
        self.assertIn("nicht als Browserfläche", normalized_german)
        self.assertIn("Login intent remains a redacted read-only check", normalized_english)
        self.assertIn("not a visible user surface", normalized_english)
        self.assertIn("not as a browser surface", normalized_english)

        visible_sections = [
            markdown_section(german, "## 60-Minuten Live-Folge"),
            markdown_section(german, "## 5-Minuten Kurzfolge"),
            markdown_section(english, "## 60-Minute Live Order"),
            markdown_section(english, "## 5-Minute Short Order"),
        ]
        for section in visible_sections:
            self.assertNotIn("api/tenant/login-intent", section)


if __name__ == "__main__":
    unittest.main()
