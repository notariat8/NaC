from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-xnp-quellenmatrix.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-xnp-quellenmatrix.md",
}

PUBLIC_SOURCES = [
    "https://notarnet.de/produkte/xnp",
    "https://notarnet.de/produkte/xnotar",
    "https://onlinehilfe.bnotk.de/technischer-bereich/systembetreuer/xnp-die-basisanwendung-der-bnotk.html",
    "https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-eines-grundbuchantrags-auf-einen-blick.html",
    "https://onlinehilfe.bnotk.de/einrichtungen/notarnet/xnotar/einstiegshilfen/alle-schritte-einer-registeranmeldung-auf-einen-blick.html",
    "https://onlinehilfe.bnotk.de/einrichtungen/zertifizierungsstelle/hinweis-zu-kartenlesegeraeten.html",
]

REQUIRED_ROW_IDS = {
    "SRC-XNP-001",
    "SRC-XNOTAR-001",
    "SRC-XNP-BNOTK-001",
    "SRC-GRUNDBUCH-001",
    "SRC-REGISTER-001",
    "SRC-CARDREADER-001",
}


def read_doc(lang: str) -> str:
    return MATRIX_DOCS[lang].read_text(encoding="utf-8")


def matrix_row_ids(text: str) -> set[str]:
    return set(re.findall(r"\|\s*(SRC-[A-Z0-9-]+)\s*\|", text))


class NotarkammerXnpSourceMatrixTests(unittest.TestCase):
    def test_source_matrix_exists_in_german_and_english(self) -> None:
        for path in MATRIX_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_matrix_cites_exact_public_sources_in_both_languages(self) -> None:
        for lang in MATRIX_DOCS:
            content = read_doc(lang)
            for source in PUBLIC_SOURCES:
                self.assertIn(source, content, f"{source} missing in {lang}")

    def test_matrix_has_claim_source_allowed_forbidden_columns(self) -> None:
        german = read_doc("de")
        english = read_doc("en")

        for heading in [
            "| ID | Aussage | Quelle | Was NaC in der Demo zeigen darf | Was NaC nicht behaupten darf |",
            "| ID | Claim | Source | What NaC may show in the demo | What NaC must not claim |",
        ]:
            self.assertIn(heading, german + english)

    def test_german_and_english_matrix_rows_stay_in_parity(self) -> None:
        german_ids = matrix_row_ids(read_doc("de"))
        english_ids = matrix_row_ids(read_doc("en"))

        self.assertEqual(REQUIRED_ROW_IDS, german_ids)
        self.assertEqual(german_ids, english_ids)

    def test_guardrails_keep_demo_safe_and_provider_neutral(self) -> None:
        combined = "\n".join(read_doc(lang) for lang in MATRIX_DOCS)

        required_guardrails = [
            "keine Mandatsdaten",
            "no mandate data",
            "keine produktive XNP-Anbindung",
            "no production XNP connection",
            "keine direkte XNP-zu-NaC-Kopplung",
            "no direct XNP-to-NaC coupling",
            "BPMN",
            "external access point",
            "externer Zugriffspunkt",
        ]
        for term in required_guardrails:
            self.assertIn(term, combined)

        forbidden_terms = [
            "Mandant:",
            "Aktenzeichen:",
            "Urkundenrolle:",
            "production XNP integration",
            "productive XNP integration",
            "Produktivschnittstelle",
            "direkte produktive XNP-Schnittstelle",
            "provider",
            "internal",
            "OCI",
            "Oracle",
            "Cloud Infrastructure",
            "tenancy",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
