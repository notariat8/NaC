from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MATRIX_DOCS = {
    "de": REPO_ROOT
    / "docs"
    / "de"
    / "demo"
    / "notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md",
    "en": REPO_ROOT
    / "docs"
    / "en"
    / "demo"
    / "notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md",
}


def read_matrix_text() -> dict[str, str]:
    return {
        language: path.read_text(encoding="utf-8")
        for language, path in MATRIX_DOCS.items()
    }


class NotarkammerXnpEvidenceMatrixTests(unittest.TestCase):
    def test_matrix_exists_in_german_and_english(self) -> None:
        for path in MATRIX_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_matrix_uses_required_columns_in_both_languages(self) -> None:
        texts = read_matrix_text()

        self.assertIn(
            "| BPMN-Gate | externe Umgebung | erwarteter Nachweis | Parallelität | kritischer-Pfad-Relevanz | Demo-Aussage |",
            texts["de"],
        )
        self.assertIn(
            "| BPMN gate | external environment | expected evidence | parallelism | critical-path relevance | demo statement |",
            texts["en"],
        )

    def test_matrix_covers_xnp_centered_real_estate_purchase_terms(self) -> None:
        combined = "\n".join(read_matrix_text().values())

        required_terms = [
            "Immobilienkaufvertrag",
            "real estate purchase agreement",
            "XNP/SNP",
            "XNotar",
            "Kartenleser",
            "card reader",
            "Signatur",
            "signature",
            "Register",
            "register",
            "Grundbuch",
            "land register",
            "Vollzug",
            "closing",
            "parallel",
            "kritischer Pfad",
            "critical path",
            "keine produktive XNP-Aktion",
            "no productive XNP action",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_matrix_names_repeated_evidence_gates_and_parallel_groups(self) -> None:
        combined = "\n".join(read_matrix_text().values())

        required_terms = [
            "pre_notarization_due_diligence",
            "post_notarization_completion",
            "ownership_transfer",
            "Readiness-Nachweis",
            "readiness evidence",
            "Versandnachweis",
            "dispatch evidence",
            "Rücklaufnachweis",
            "response evidence",
            "Audit-Metadaten",
            "audit metadata",
            "kritisch",
            "critical",
            "blockierend",
            "blocking",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_matrix_remains_a_demo_modeling_artifact_only(self) -> None:
        combined = "\n".join(read_matrix_text().values())

        required_terms = [
            "Demo-/Modellierungsartefakt",
            "demo/modeling artifact",
            "keine Mandatsdaten",
            "no matter data",
            "keine Secrets",
            "no secrets",
            "keine API-Credentials",
            "no API credentials",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

        forbidden_terms = [
            "NaC hat produktiven XNP/SNP-Zugriff",
            "NaC has productive XNP/SNP access",
            "NaC löst produktive XNP-Aktionen aus",
            "NaC triggers productive XNP actions",
            "echte Mandatsdaten",
            "real matter data",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
