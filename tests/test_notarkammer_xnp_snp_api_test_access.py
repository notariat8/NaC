from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-xnp-snp-api-testzugang.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-xnp-snp-api-testzugang.md",
}


def combined_api_docs() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in API_DOCS.values())


class NotarkammerXnpSnpApiTestAccessTests(unittest.TestCase):
    def test_api_test_access_docs_exist_in_german_and_english(self) -> None:
        for path in API_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_api_test_access_names_decision_pack_for_isv_listing(self) -> None:
        combined = combined_api_docs()

        required_terms = [
            "ISV-Freigabepaket",
            "ISV approval package",
            "technischer Ansprechpartner",
            "technical contact",
            "Sandbox",
            "test tenant",
            "Callback-Beispiele",
            "callback examples",
            "Fehlerklassen",
            "error classes",
            "Zertifizierungsweg",
            "certification path",
            "Pilotnotariat",
            "pilot notary office",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_api_test_access_keeps_demo_safe_boundaries(self) -> None:
        combined = combined_api_docs()

        required_terms = [
            "keine produktive XNP-Handlung",
            "no productive XNP action",
            "keine Mandatsdaten",
            "no matter data",
            "keine Rohdokumente",
            "no raw documents",
            "keine PINs",
            "no PINs",
        ]
        for term in required_terms:
            self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
