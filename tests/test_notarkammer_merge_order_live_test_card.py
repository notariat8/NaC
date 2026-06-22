from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "de": REPO_ROOT
    / "docs"
    / "de"
    / "demo"
    / "notarkammer-2026-06-merge-order-live-test-card.md",
    "en": REPO_ROOT
    / "docs"
    / "en"
    / "demo"
    / "notarkammer-2026-06-merge-order-live-test-card.md",
}
README_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "README.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "README.md",
}


def read_docs() -> dict[str, str]:
    for path in DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing merge/live-test card: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in DOCS.items()}


class NotarkammerMergeOrderLiveTestCardTests(unittest.TestCase):
    def test_docs_exist_and_are_linked(self) -> None:
        for language, path in DOCS.items():
            self.assertTrue(path.is_file(), path)
            self.assertIn(path.name, README_DOCS[language].read_text(encoding="utf-8"))

    def test_card_defines_merge_order_and_live_test_sequence(self) -> None:
        combined = "\n".join(read_docs().values()).lower()

        required_terms = [
            "merge order",
            "merge-reihenfolge",
            "www-n8",
            "nac",
            "xnp/snp",
            "isv",
            "prozessmodell",
            "process model",
            "immobilienkaufvertrag",
            "real estate purchase agreement",
            "login diagnostics",
            "login-diagnose",
            "evidence matrix",
            "evidence-matrix",
            "smoke",
            "live test",
            "live-test",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_card_keeps_demo_safe_and_non_productive(self) -> None:
        combined = "\n".join(read_docs().values()).lower()

        required_boundaries = [
            "keine produktive xnp-aktion",
            "no productive xnp action",
            "keine mandatsdaten",
            "no mandate data",
            "keine secrets",
            "no secrets",
            "keine live-reparatur",
            "no live repair",
            "fail-closed",
            "metadata-only",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined)

        forbidden_terms = [
            "productive xnp access confirmed",
            "produktiver xnp-zugriff bestätigt",
            "real land-register query",
            "echte grundbuchabfrage",
            "client_secret",
            "id_token",
            "access_token",
            "ocid1.",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
