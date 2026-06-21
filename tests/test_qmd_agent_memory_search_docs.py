from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "operations" / "agent-memory-search-qmd.md",
    "en": REPO_ROOT / "docs" / "en" / "operations" / "agent-memory-search-qmd.md",
}
READMES = {
    "de": REPO_ROOT / "docs" / "de" / "operations" / "README.md",
    "en": REPO_ROOT / "docs" / "en" / "operations" / "README.md",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class QmdAgentMemorySearchDocsTests(unittest.TestCase):
    def test_qmd_agent_memory_docs_exist_in_german_and_english(self) -> None:
        for path in DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_docs_define_qmd_as_optional_agent_memory_search(self) -> None:
        combined = "\n".join(read(path) for path in DOCS.values())

        required_terms = [
            "optional",
            "Agent Memory Search",
            "qmd search",
            "qmd query --no-rerank",
            "BM25",
            "Embeddings",
            "MCP",
            "Reranking",
        ]
        for term in required_terms:
            self.assertIn(term, combined)

    def test_docs_limit_index_scope_and_forbid_sensitive_material(self) -> None:
        combined = "\n".join(read(path) for path in DOCS.values())

        allowed_scope_terms = [
            "docs/de/operations",
            "docs/de/superpowers",
            "oci-landing-zone/runbooks",
            "AGENTS.md",
        ]
        for term in allowed_scope_terms:
            self.assertIn(term, combined)

        forbidden_scope_terms = [
            ".terraform",
            "out/",
            "attachments",
            "wallet",
            "Secret",
            "private key",
            "Mandatsdaten",
            "mandate data",
            "repo root",
        ]
        for term in forbidden_scope_terms:
            self.assertIn(term, combined)

    def test_docs_reject_default_mcp_daemon_and_reranking(self) -> None:
        german = read(DOCS["de"])
        english = read(DOCS["en"])

        self.assertIn("Kein MCP/HTTP-Daemon als Standard", german)
        self.assertIn("Kein Reranking als Standard", german)
        self.assertIn("No MCP/HTTP daemon by default", english)
        self.assertIn("No reranking by default", english)

    def test_operations_readmes_link_the_qmd_runbook(self) -> None:
        for lang, path in READMES.items():
            content = read(path)
            self.assertIn("agent-memory-search-qmd.md", content, lang)


if __name__ == "__main__":
    unittest.main()
