from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_MAP_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-first-route-smoke-map.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-first-route-smoke-map.md",
}
FIRST_MATTER_FIXTURE = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "demo"
    / "notarkammer-first-immobilienkaufvertrag.metadata.json"
)


def read_smoke_map_docs() -> dict[str, str]:
    for path in SMOKE_MAP_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing first-route smoke map: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in SMOKE_MAP_DOCS.items()}


class NotarkammerFirstRouteSmokeMapTests(unittest.TestCase):
    def test_first_route_smoke_map_exists_in_german_and_english(self) -> None:
        for path in SMOKE_MAP_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_smoke_map_connects_login_first_matter_bpmn_and_boundaries(self) -> None:
        combined = "\n".join(read_smoke_map_docs().values())

        required_terms = [
            "https://app.notariat8.de/login",
            "https://app.notariat8.de/workspace",
            "https://app.notariat8.de/workspace/immobilienkaufvertrag",
            "login_status",
            "workspace_fail_closed",
            "protected_first_matter_status",
            "DEMO-MATTER-IMMOBILIENKAUF-01",
            "tests/fixtures/demo/notarkammer-first-immobilienkaufvertrag.metadata.json",
            "bpmn/immobilienkaufvertrag.bpmn",
            "notarkammer-first-matter-metadata.md",
            "notarkammer-immobilienkaufvertrag-xnp-evidence-matrix.md",
            "XNP/SNP",
            "BPMN",
            "fail-closed",
            "no mandate data",
            "no secrets",
            "no productive XNP action",
            "no OCI writes",
            "approved session, role and binding",
            "bestätigter Sitzung, Rolle und Bindung",
        ]
        for term in required_terms:
            self.assertIn(term, combined)


    def test_smoke_map_documents_protected_first_matter_route(self) -> None:
        docs = read_smoke_map_docs()
        for language, content in docs.items():
            self.assertIn(
                "https://app.notariat8.de/workspace/immobilienkaufvertrag",
                content,
                language,
            )
            self.assertIn("protected_first_matter_status", content, language)
            if language == "de":
                self.assertRegex(content, r"Sitzung.*Rolle.*Bindung", language)
                self.assertRegex(content, r"(fail-closed|geschlossen)", language)
            else:
                self.assertRegex(
                    content,
                    re.compile(r"session.*role.*binding", re.IGNORECASE),
                    language,
                )
                self.assertIn("fail-closed", content, language)
            for boundary in (
                "no mandate data",
                "no secrets",
                "no productive XNP action",
                "no OCI writes",
            ):
                self.assertIn(boundary, content, language)

    def test_smoke_map_has_four_step_live_validation_route(self) -> None:
        docs = read_smoke_map_docs()
        for language, content in docs.items():
            step_markers = re.findall(r"^\| R[1-4] \|", content, flags=re.MULTILINE)
            self.assertEqual(4, len(step_markers), language)
            self.assertIn("R1", content)
            self.assertIn("R2", content)
            self.assertIn("R3", content)
            self.assertIn("R4", content)
            self.assertIn("Go", content)
            self.assertIn("Fallback", content)

    def test_smoke_map_matches_first_matter_fixture_metadata(self) -> None:
        fixture = json.loads(FIRST_MATTER_FIXTURE.read_text(encoding="utf-8"))
        combined = "\n".join(read_smoke_map_docs().values())

        self.assertEqual("DEMO-MATTER-IMMOBILIENKAUF-01", fixture["matter_demo_id"])
        self.assertEqual("immobilienkaufvertrag", fixture["usecase_slug"])
        self.assertEqual("bpmn/immobilienkaufvertrag.bpmn", fixture["bpmn_model"])
        self.assertEqual(["XNP", "SNP"], fixture["target_systems"])
        for key in (
            fixture["matter_demo_id"],
            fixture["usecase_slug"],
            fixture["bpmn_model"],
            fixture["entry_contract"],
            "xnp_snp_target_metadata_only",
        ):
            self.assertIn(key, combined)

    def test_smoke_map_blocks_sensitive_or_unsafe_claims(self) -> None:
        combined = "\n".join(read_smoke_map_docs().values())
        combined_lower = combined.lower()

        blocked_terms = [
            "productive XNP access",
            "production XNP integration",
            "real client",
            "real mandate data",
            "real property",
            "real deed",
            "real identity document",
            "mandatsdaten",
            "Grundbuchblatt ",
            "Flurstück ",
            "Oracle Cloud Infrastructure",
            "OCI apply",
            "API key:",
            "Login token:",
            "Secret:",
            "Password:",
            "PIN 123",
            "client id",
            "tenant id",
            "issuer",
            "jwks",
        ]
        for term in blocked_terms:
            self.assertNotIn(term.lower(), combined_lower)


if __name__ == "__main__":
    unittest.main()
