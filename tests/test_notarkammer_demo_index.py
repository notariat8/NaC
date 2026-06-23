from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_INDEX_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "README.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "README.md",
}


def read_demo_index_docs() -> list[str]:
    for path in DEMO_INDEX_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing demo index: {path}")
    return [path.read_text(encoding="utf-8") for path in DEMO_INDEX_DOCS.values()]


class NotarkammerDemoIndexTests(unittest.TestCase):
    def test_demo_index_exists_in_german_and_english(self) -> None:
        for path in DEMO_INDEX_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_demo_index_links_the_core_demo_route(self) -> None:
        combined = "\n".join(read_demo_index_docs())

        required_links = [
            "notarkammer-2026-06-demo-preflight.md",
            "notarkammer-2026-06-live-demo-runbook.md",
            "notarkammer-2026-06-60-minute-live-demo-script.md",
            "notarkammer-2026-06-demo-smoke-readiness.md",
            "notarkammer-2026-06-demo-gap-audit.md",
            "notarkammer-2026-06-demo-qa-objection-handling.md",
            "notarkammer-first-matter-metadata.md",
            "notarkammer-bpmn-critical-path-talking-points.md",
            "notarkammer-xnp-bpmn-demo-depth.md",
            "notarkammer-xnp-demo-contract.md",
            "notarkammer-xnp-quellenmatrix.md",
        ]
        for link in required_links:
            self.assertIn(link, combined)

    def test_demo_index_is_linked_from_localized_readmes(self) -> None:
        german_readme = (REPO_ROOT / "docs" / "de" / "README.md").read_text(encoding="utf-8")
        english_readme = (REPO_ROOT / "docs" / "en" / "README.md").read_text(encoding="utf-8")

        self.assertIn("[docs/de/demo/](demo/)", german_readme)
        self.assertIn("Notarkammer-Demo", german_readme)
        self.assertIn("[docs/en/demo/](demo/)", english_readme)
        self.assertIn("Notarkammer demo", english_readme)

    def test_demo_index_names_showable_path_and_boundaries(self) -> None:
        for content in read_demo_index_docs():
            content_lower = content.lower()
            self.assertIn("notariat8.de", content)
            self.assertIn("app.notariat8.de", content)
            self.assertIn("Immobilienkaufvertrag", content)
            self.assertIn("XNP", content)
            self.assertIn("Kartenleser", content)
            self.assertIn("BPMN", content)
            self.assertIn("ATP", content)
            self.assertIn("fail-closed", content_lower)
            self.assertIn("no mandate data", content_lower)
            self.assertIn("no secrets", content_lower)
            self.assertIn("no productive filing", content_lower)

    def test_demo_index_stays_public_demo_safe(self) -> None:
        combined = "\n".join(read_demo_index_docs())

        blocked_terms = [
            "real client data",
            "real mandate data",
            "production XNP integration",
            "productive XNP action is executed",
            "Secret:",
            "Token:",
            "API key:",
            "PIN 123",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined)


if __name__ == "__main__":
    unittest.main()
