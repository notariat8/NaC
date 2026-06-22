from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "de": REPO_ROOT
    / "docs"
    / "de"
    / "demo"
    / "notarkammer-2026-06-login-portal-diagnostics-runbook.md",
    "en": REPO_ROOT
    / "docs"
    / "en"
    / "demo"
    / "notarkammer-2026-06-login-portal-diagnostics-runbook.md",
}
README_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "README.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "README.md",
}


def read_docs() -> dict[str, str]:
    for path in DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing login/portal diagnostics runbook: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in DOCS.items()}


class NotarkammerLoginPortalDiagnosticsRunbookTests(unittest.TestCase):
    def test_diagnostics_runbook_exists_in_german_and_english_and_is_linked(self) -> None:
        for language, path in DOCS.items():
            self.assertTrue(path.is_file(), path)
            self.assertIn(path.name, README_DOCS[language].read_text(encoding="utf-8"))

    def test_runbook_defines_red_yellow_green_status_classes(self) -> None:
        combined = "\n".join(read_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "green",
            "yellow",
            "red",
            "grün",
            "gelb",
            "rot",
            "showable",
            "vorführbar",
            "fallback",
            "stopper",
            "token-austausch",
            "token exchange",
            "token-prüfung",
            "token validation",
            "rollenprüfung",
            "role check",
            "sitzung",
            "session",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_runbook_covers_current_live_browser_diagnostics(self) -> None:
        combined = "\n".join(read_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "anmeldung empfangen",
            "sign-in received",
            "rollenprüfung offen",
            "role check open",
            "sitzung offen",
            "session open",
            "token-austausch: ungültig",
            "token exchange: invalid",
            "token-austausch: technisch nicht verfügbar",
            "token exchange: technically unavailable",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_runbook_sets_fallback_criteria_for_each_login_gate(self) -> None:
        combined = "\n".join(read_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "process model fallback",
            "prozessmodell-fallback",
            "workspace boundary fallback",
            "workspace-grenzen-fallback",
            "readiness fallback",
            "readiness-fallback",
            "go to fallback",
            "in fallback wechseln",
            "do not debug live",
            "nicht live debuggen",
            "continue only when token exchange, token validation, role check and session are green",
            "nur fortsetzen, wenn token-austausch, token-prüfung, rollenprüfung und sitzung grün sind",
            "stop the live login path",
            "live-login-pfad stoppen",
            "show /workspace only as fail-closed or metadata-only boundary",
            "/workspace nur als fail-closed- oder metadata-only-grenze zeigen",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_runbook_keeps_public_output_redacted_and_scope_protected(self) -> None:
        combined = "\n".join(read_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_boundaries = [
            "no secrets",
            "keine secrets",
            "no tokens",
            "keine tokens",
            "no claims",
            "keine claims",
            "no provider details",
            "keine provider-details",
            "no callback values",
            "keine callback-werte",
            "no mandate data",
            "keine mandatsdaten",
            "docs/de/demo",
            "docs/en/demo",
            "tests/test_notarkammer_",
            "no runtime change",
            "keine runtime-änderung",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined_lower)

        forbidden_terms = [
            "code=",
            "state=",
            "nonce=",
            "id_token=",
            "access_token=",
            "refresh_token=",
            "client_secret",
            "client id:",
            "issuer:",
            "jwks",
            "ocid1.",
            "idcs-",
            "oracle cloud infrastructure",
            "real client",
            "real deed",
            "real identity document",
            "real property",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined_lower)


if __name__ == "__main__":
    unittest.main()
