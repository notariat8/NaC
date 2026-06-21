from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GAP_AUDIT_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-gap-audit.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-gap-audit.md",
}


def read_audits() -> dict[str, str]:
    for path in GAP_AUDIT_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing Notarkammer demo gap audit: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in GAP_AUDIT_DOCS.items()}


class NotarkammerDemoGapAuditTests(unittest.TestCase):
    def test_gap_audit_exists_in_german_and_english(self) -> None:
        for path in GAP_AUDIT_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_gap_audit_covers_required_categories_and_fields(self) -> None:
        audits = read_audits()

        expected_terms = {
            "de": [
                "XNP Zugriff",
                "BPMN Editor/Viewer",
                "Workspace/Auth",
                "ATP/Onboarding",
                "Gebühren/GNotKG",
                "Notariat-only Guardrails",
                "Stand",
                "Demo-Aussage",
                "Grenze",
                "Nächster realer Integrationsschritt",
            ],
            "en": [
                "XNP Access",
                "BPMN Editor/Viewer",
                "Workspace/Auth",
                "ATP/Onboarding",
                "Fees/GNotKG",
                "Notariat-only Guardrails",
                "Current State",
                "Demo Statement",
                "Boundary",
                "Next Real Integration Step",
            ],
        }

        for language, terms in expected_terms.items():
            with self.subTest(language=language):
                for term in terms:
                    self.assertIn(term, audits[language])

    def test_gap_audit_prioritizes_demo_vs_fallback_vs_post_demo(self) -> None:
        combined = "\n".join(read_audits().values())

        required_priority_terms = [
            "Demo in 4 Tagen",
            "Demo in 4 Days",
            "Zeigbar",
            "Showable",
            "Bewusster Fallback",
            "Intentional Fallback",
            "Nach der Demo",
            "After the Demo",
            "P0",
            "P1",
            "P2",
        ]
        for term in required_priority_terms:
            self.assertIn(term, combined)

    def test_gap_audit_marks_gnotkg_status_without_overclaiming(self) -> None:
        combined = "\n".join(read_audits().values())

        self.assertIn("src/nac_gnotkg/costs.py", combined)
        self.assertIn("tests/test_gnotkg_costs.py", combined)
        self.assertIn("Demo-Verknüpfung", combined)
        self.assertIn("Demo Link", combined)
        self.assertIn("keine produktive Gebührenabrechnung", combined)
        self.assertIn("not production fee billing", combined)

    def test_gap_audit_enforces_notariat_guardrails_and_no_sensitive_data(self) -> None:
        combined = "\n".join(read_audits().values())
        lowered = combined.lower()

        required_guardrails = [
            "ausschließlich für Notariate",
            "notariats-only",
            "keine Mandatsdaten",
            "no mandate data",
            "keine OCI writes",
            "no OCI writes",
            "keine Secrets",
            "no secrets",
            "keine produktive XNP-Aktion",
            "no production XNP action",
        ]
        for guardrail in required_guardrails:
            self.assertIn(guardrail.lower(), lowered)

        forbidden_claims = [
            "produktive XNP-Integration ist fertig",
            "production XNP integration is complete",
            "NaC steuert XNP in der Cloud",
            "NaC controls XNP from the cloud",
            "Mandatsdaten anzeigen",
            "display mandate data",
            "Secret value",
            "OCI apply",
            "ATP credentials",
            "echte Akte",
            "real client file",
        ]
        for claim in forbidden_claims:
            self.assertNotIn(claim.lower(), lowered)

    def test_gap_audit_uses_compact_table_rows_for_each_gap(self) -> None:
        audits = read_audits()

        row_pattern = re.compile(r"^\| P[0-2] \|", re.MULTILINE)
        for language, content in audits.items():
            with self.subTest(language=language):
                self.assertGreaterEqual(len(row_pattern.findall(content)), 6)


if __name__ == "__main__":
    unittest.main()
