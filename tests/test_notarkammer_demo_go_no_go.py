from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-go-no-go.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-go-no-go.md",
}
README_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "README.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "README.md",
}


def read_docs() -> dict[str, str]:
    for path in DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing Go/No-Go demo doc: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in DOCS.items()}


class NotarkammerDemoGoNoGoTests(unittest.TestCase):
    def test_go_no_go_docs_exist_and_are_linked(self) -> None:
        for language, path in DOCS.items():
            self.assertTrue(path.is_file(), path)
            readme = README_DOCS[language].read_text(encoding="utf-8")
            self.assertIn(path.name, readme)

    def test_matrix_covers_demo_surfaces_and_decisions(self) -> None:
        combined = "\n".join(read_docs().values())
        combined_lower = combined.lower()

        required_terms = [
            "go",
            "warn",
            "stop",
            "warn-go",
            "no-go",
            "notariat8.de",
            "prozessmodell",
            "process model",
            "/healthz",
            "login",
            "workspace",
            "xnp",
            "kartenleser",
            "card reader",
            "evidence",
            "summary-only",
            "cet/cest",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_matrix_blocks_sensitive_or_productive_demo_paths(self) -> None:
        combined = "\n".join(read_docs().values())
        combined_lower = combined.lower()

        required_boundaries = [
            "keine echten mandatsdaten",
            "no real mandate data",
            "keine tokens",
            "no tokens",
            "keine produktive xnp",
            "no productive xnp",
            "keine anbieter",
            "no provider",
            "kein json-endpunkt als benutzeroberfläche",
            "no json endpoint as a user interface",
            "callback-werte",
            "callback values",
            "wallets",
            "dsn",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined_lower)


if __name__ == "__main__":
    unittest.main()
