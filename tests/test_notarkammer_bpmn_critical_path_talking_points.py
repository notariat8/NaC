from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TALKING_POINT_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-bpmn-critical-path-talking-points.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-bpmn-critical-path-talking-points.md",
}
DEMO_SCRIPTS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-script.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-script.md",
}


class NotarkammerBpmnCriticalPathTalkingPointTests(unittest.TestCase):
    def test_talking_points_exist_in_german_and_english(self) -> None:
        for path in TALKING_POINT_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_talking_points_cover_the_public_notarial_critical_path(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in TALKING_POINT_DOCS.values())

        required_terms = [
            "Immobilienkaufvertrag",
            "Handelsregisteranmeldung",
            "Grundbuch",
            "Register",
            "BPMN",
            "critical path",
            "Kritischer Pfad",
            "XNotar/XJustiz",
            "Kartenleser",
            "Notariat",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_talking_points_include_duration_parallelism_and_blockers(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in TALKING_POINT_DOCS.values())

        required_terms = [
            "15-30 Minuten",
            "2-6 Stunden",
            "2-8 Wochen",
            "10-25 minutes",
            "45-120 minutes",
            "2 days to 3 weeks",
            "Parallele Vorarbeiten",
            "Parallel Preparation",
            "Blockierende Ereignisse",
            "Blocking Events",
            "fehlende oder widersprüchliche Unterlagen",
            "missing or inconsistent documents",
            "Registerrücklauf",
            "register response",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_talking_points_keep_the_demo_source_agnostic_and_notariat_only(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in TALKING_POINT_DOCS.values())

        forbidden_terms = [
            "Oracle Cloud",
            "OCI",
            "Cloud Infrastructure",
            "Mandatsdaten",
            "mandate data",
            "echte Akte",
            "real file",
            "Secret",
            "Token",
            "OCID",
            "Autonomous",
            "Tenancy",
            "Compartment",
            "produktive XNP-Integration",
            "production XNP integration",
            "XNP integration is live",
            "productive dispatch",
            "produktiven Versand",
        ]
        for term in forbidden_terms:
            self.assertNotIn(term, combined)

    def test_talking_points_have_matching_demo_beats(self) -> None:
        german = TALKING_POINT_DOCS["de"].read_text(encoding="utf-8")
        english = TALKING_POINT_DOCS["en"].read_text(encoding="utf-8")

        paired_beats = [
            ("Sprechspur", "Talk Track"),
            ("Prozess 1: Immobilienkaufvertrag", "Process 1: Immobilienkaufvertrag"),
            ("Prozess 2: Handelsregisteranmeldung", "Process 2: Handelsregisteranmeldung"),
            ("Parallele Vorarbeiten", "Parallel Preparation"),
            ("Blockierende Ereignisse", "Blocking Events"),
            ("Sichere Grenze", "Safe Boundary"),
            ("Nicht sagen", "Do Not Say"),
            ("Nachweisfrage", "Evidence Question"),
            ("Übergabe", "Handoff"),
        ]
        for de_term, en_term in paired_beats:
            self.assertIn(de_term, german)
            self.assertIn(en_term, english)

    def test_demo_scripts_link_to_the_talking_points(self) -> None:
        self.assertIn(
            "notarkammer-bpmn-critical-path-talking-points.md",
            DEMO_SCRIPTS["de"].read_text(encoding="utf-8"),
        )
        self.assertIn(
            "notarkammer-bpmn-critical-path-talking-points.md",
            DEMO_SCRIPTS["en"].read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
