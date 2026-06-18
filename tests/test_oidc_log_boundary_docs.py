from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read_repo_text(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


class OidcLogBoundaryDocsTests(unittest.TestCase):
    def test_oidc_log_boundary_docs_record_current_functions_invoke_evidence(self) -> None:
        german = read_repo_text("docs/de/operations/oidc-state-log-boundary.md")
        english = read_repo_text("docs/en/operations/oidc-state-log-boundary.md")

        for content in (german, english):
            self.assertIn("2026-06-18", content)
            self.assertIn("nac-dev-functions-invoke", content)
            self.assertIn("nac-dev-nac-app", content)
            self.assertIn("Received function invocation request", content)
            self.assertIn("Served function invocation request", content)
            self.assertIn("code", content)
            self.assertIn("state", content)
            self.assertIn("nonce", content)
            self.assertIn("token", content)
            self.assertIn("claim", content)

    def test_oidc_log_boundary_docs_define_repeatable_proof_without_oci_apply(self) -> None:
        german = read_repo_text("docs/de/operations/oidc-state-log-boundary.md")
        english = read_repo_text("docs/en/operations/oidc-state-log-boundary.md")

        self.assertIn("Kein OCI Apply", german)
        self.assertIn("No OCI apply", english)
        for content in (german, english):
            self.assertIn("Logging Search", content)
            self.assertIn("Functions invoke", content)
            self.assertIn("callback query", content.lower())
            self.assertIn("Protected PR", content)


if __name__ == "__main__":
    unittest.main()
