from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOGIN_CHECKLIST_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-demo-login-checklist.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-demo-login-checklist.md",
}


def read_login_checklists() -> dict[str, str]:
    for path in LOGIN_CHECKLIST_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing Notarkammer demo login checklist: {path}")
    return {
        language: path.read_text(encoding="utf-8")
        for language, path in LOGIN_CHECKLIST_DOCS.items()
    }


class NotarkammerDemoLoginChecklistTests(unittest.TestCase):
    def test_login_checklist_exists_in_german_and_english(self) -> None:
        for path in LOGIN_CHECKLIST_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_login_checklist_names_entrypoint_and_required_status_points(self) -> None:
        combined_lower = "\n".join(read_login_checklists().values()).lower()

        required_terms = [
            "https://app.notariat8.de/login",
            "token-austausch",
            "token exchange",
            "token-prüfung",
            "token verification",
            "rollengate",
            "role gate",
            "sitzung",
            "session",
            "redaktiert",
            "redacted",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_login_checklist_keeps_demo_scope_closed(self) -> None:
        combined_lower = "\n".join(read_login_checklists().values()).lower()

        required_boundaries = [
            "kein zugriff auf mandate",
            "no mandate data access",
            "keine callbacks",
            "no callbacks",
            "keine parameter",
            "no parameters",
            "keine providerdetails",
            "no provider details",
            "keine secrets",
            "no secrets",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined_lower)

    def test_login_checklist_blocks_sensitive_protocol_cloud_and_mandate_terms(self) -> None:
        combined = "\n".join(read_login_checklists().values())
        combined_lower = combined.lower()

        blocked_terms = [
            "code=",
            "state=",
            "oracle",
            "oci",
            "identity provider",
            "openid",
            "oauth",
            "jwks",
            "issuer",
            "tenant id",
            "client id",
            "mandatsdaten",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined_lower)


if __name__ == "__main__":
    unittest.main()
