from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_DOCS = {
    "de": REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-smoke-readiness.md",
    "en": REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-smoke-readiness.md",
}


def read_smoke_docs() -> dict[str, str]:
    for path in SMOKE_DOCS.values():
        if not path.is_file():
            raise AssertionError(f"Missing demo smoke readiness runbook: {path}")
    return {language: path.read_text(encoding="utf-8") for language, path in SMOKE_DOCS.items()}


class NotarkammerDemoSmokeReadinessTests(unittest.TestCase):
    def test_smoke_runbook_exists_in_german_and_english(self) -> None:
        for path in SMOKE_DOCS.values():
            self.assertTrue(path.is_file(), path)

    def test_smoke_runbook_names_exact_demo_surfaces_without_live_network_tests(self) -> None:
        for language, content in read_smoke_docs().items():
            self.assertIn("Smoke-ID", content)
            self.assertIn("Version", content)
            self.assertIn("www-n8", content)
            self.assertIn("https://notariat8.de/prozessmodell.html", content)
            self.assertIn("https://app.notariat8.de/healthz", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("https://app.notariat8.de/login", content)
            self.assertIn("Anmeldung" if language == "de" else "sign-in", content)
            self.assertIn("test user", content.lower())
            self.assertIn("no live network test", content.lower())
            self.assertIn("scripts/notarkammer_demo_smoke.py", content)
            self.assertIn("no OCI apply", content)

    def test_smoke_runbook_requires_workspace_fail_closed_without_session(self) -> None:
        combined = "\n".join(read_smoke_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "fail-closed",
            "without session",
            "without a session",
            "401",
            "403",
            "no workspace content",
            "keine workspace-inhalte",
            "no matter data",
            "keine mandatsdaten",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

    def test_smoke_runbook_has_cold_oci_and_idp_fallback(self) -> None:
        combined = "\n".join(read_smoke_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_terms = [
            "cold or slow",
            "kalt oder langsam",
            "cached screenshot",
            "bereits geladenen tab",
            "do not debug live",
            "nicht live debuggen",
            "process model",
            "prozessmodell",
            "workspace boundary",
            "workspace-grenze",
        ]
        for term in required_terms:
            self.assertIn(term, combined_lower)

        self.assertNotIn("If OCI or IdP", combined)
        self.assertNotIn("Wenn OCI oder IdP", combined)

    def test_smoke_runbook_uses_calibrated_twenty_second_timeout(self) -> None:
        combined = "\n".join(read_smoke_docs().values())
        combined_lower = " ".join(combined.lower().split())

        self.assertIn("scripts/notarkammer_demo_smoke.py --timeout-seconds 20", combined)
        self.assertIn("10s", combined_lower)
        self.assertIn("20s", combined_lower)
        self.assertIn("cold-start tolerance", combined_lower)
        self.assertIn("slow_fail_closed_response", combined)

    def test_customer_speaker_lines_do_not_expose_provider_or_matter_terms(self) -> None:
        forbidden_terms = [
            "OCI",
            "IdP",
            "Provider",
            "ATP",
            "Vault",
            "Wallet",
            "Tenant",
            "Secret",
            "Mandatsdaten",
            "matter data",
            "client file",
        ]

        for language, content in read_smoke_docs().items():
            speaker_lines = [
                line for line in content.splitlines() if line.startswith("- Speaker line:")
            ]
            self.assertGreaterEqual(len(speaker_lines), 3, language)
            for line in speaker_lines:
                for term in forbidden_terms:
                    self.assertNotIn(term, line, f"{language}: {line}")

    def test_smoke_runbook_keeps_scope_to_docs_tests_and_synthetic_demo_data(self) -> None:
        combined = "\n".join(read_smoke_docs().values())
        combined_lower = " ".join(combined.lower().split())

        required_boundaries = [
            "docs/de/demo/",
            "docs/en/demo/",
            "src/nac_observability/",
            "scripts/notarkammer_demo_smoke.py",
            "tests/",
            "protected pr",
            "review/merge gate",
            "no secrets",
            "no mandate data",
            "synthetic",
            "testnutzer",
            "test user",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined_lower)

        blocked_terms = [
            "real client",
            "real property",
            "real deed",
            "real identity document",
            "PIN 123",
            "API key:",
            "Login token:",
        ]
        for term in blocked_terms:
            self.assertNotIn(term, combined)

    def test_smoke_runbook_uses_summary_only_evidence_output(self) -> None:
        docs = read_smoke_docs()
        for language, content in docs.items():
            self.assertIn(
                "python scripts/notarkammer_demo_smoke.py --timeout-seconds 20 --summary-only",
                content,
                language,
            )
            self.assertIn("--summary-only", content, language)
            self.assertIn("body preview", content.lower(), language)

        self.assertIn("keine Response-Body-Vorschau", docs["de"])
        self.assertIn("no response body preview", docs["en"])

    def test_smoke_runbook_has_quick_decision_block_for_live_start(self) -> None:
        docs = read_smoke_docs()
        for language, content in docs.items():
            self.assertIn("Quick decision" if language == "en" else "Schnellentscheidung", content)
            self.assertIn("https://notariat8.de/prozessmodell.html", content)
            self.assertIn("https://app.notariat8.de/healthz", content)
            self.assertIn("https://app.notariat8.de/workspace", content)
            self.assertIn("Go", content)
            self.assertIn("Fallback", content)
            self.assertIn("do not debug live" if language == "en" else "nicht live debuggen", content)
            self.assertIn("summary-only", content)


if __name__ == "__main__":
    unittest.main()
