from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CHECKCARD_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-live-checkcard.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-live-checkcard.md",
}


def read_checkcards() -> dict[str, str]:
    for path in CHECKCARD_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing Notarkammer demo live checkcard: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in CHECKCARD_DOCS.items()}


class NotarkammerDemoLiveCheckcardTests(unittest.TestCase):
    def test_checkcard_exists_in_german_and_english(self) -> None:
        for path in CHECKCARD_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_checkcard_covers_current_live_route_and_decision_states(self) -> None:
        combined = "\n".join(read_checkcards().values())

        required_terms = [
            "https://notariat8.de/prozessmodell.html",
            "https://app.notariat8.de/login",
            "https://app.notariat8.de/workspace",
            "Immobilienkaufvertrag",
            "Portal-Start bereit",
            "role gate",
            "Rollengate",
            "Sitzung",
            "session",
            "XNP/SNP",
            "critical path",
            "kritischer Pfad",
            "Go",
            "Fallback",
            "Stop",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_checkcard_defines_good_enough_demo_success_without_full_workspace(self) -> None:
        combined = "\n".join(read_checkcards().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "metadata-only",
            "portal start",
            "portal-start",
            "no full workspace",
            "kein vollständiger arbeitsbereich",
            "no mandate data",
            "keine mandatsdaten",
            "no productive xnp action",
            "keine produktive xnp-handlung",
            "no productive filing",
            "keine produktive einreichung",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_checkcard_blocks_provider_and_sensitive_demo_language(self) -> None:
        combined = "\n".join(read_checkcards().values())
        combined_lower = combined.lower()

        blocked_terms = [
            "oracle cloud infrastructure",
            "oci console",
            "vault",
            "wallet",
            "client secret",
            "api key",
            "token value",
            "id token",
            "jwks",
            "issuer",
            "tenant ocid",
            "session id",
            "case id",
            "grundbuchblatt ",
            "flurstück ",
            "real mandate data",
            "produktive xnp-api ist angebunden",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined_lower)

    def test_checkcard_is_linked_from_demo_readmes(self) -> None:
        for language in ("de", "en"):
            readme = REPO_ROOT / "docs" / language / "demo" / "README.md"
            self.assertTrue(readme.is_file(), readme)
            self.assertIn(
                "notarkammer-2026-06-live-checkcard.md",
                readme.read_text(encoding="utf-8"),
                language,
            )


if __name__ == "__main__":
    unittest.main()
