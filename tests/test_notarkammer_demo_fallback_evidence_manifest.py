import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NotarkammerDemoFallbackEvidenceManifestTests(unittest.TestCase):
    def test_manifest_exists_in_german_and_english(self):
        german = ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
        english = ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"

        self.assertTrue(german.exists())
        self.assertTrue(english.exists())

    def test_manifest_defines_allowed_prepared_evidence(self):
        german = (
            ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
        ).read_text(encoding="utf-8")
        english = (
            ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
        ).read_text(encoding="utf-8")

        for text in [german, english]:
            self.assertIn("notariat8.de", text)
            self.assertIn("prozessmodell", text)
            self.assertIn("app.notariat8.de/workspace", text)
            self.assertIn("fail-closed", text)
            self.assertIn("XNP", text)
            self.assertIn("card reader", text)
            self.assertIn("Protected PR", text)

    def test_manifest_blocks_sensitive_or_productive_evidence(self):
        combined = "\n".join(
            [
                (
                    ROOT
                    / "docs"
                    / locale
                    / "demo"
                    / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
                ).read_text(encoding="utf-8")
                for locale in ["de", "en"]
            ]
        )

        required_boundaries = [
            "keine echten Mandatsdaten",
            "keine Ausweise",
            "keine Urkunden",
            "keine Zugangsdaten",
            "keine PINs",
            "no real mandate data",
            "no identity documents",
            "no deeds",
            "no credentials",
            "no PINs",
            "no productive submission",
        ]
        for boundary in required_boundaries:
            self.assertIn(boundary, combined)

    def test_60_minute_script_links_manifest(self):
        german = (
            ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-60-minute-live-demo-script.md"
        ).read_text(encoding="utf-8")
        english = (
            ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-60-minute-live-demo-script.md"
        ).read_text(encoding="utf-8")

        self.assertIn("notarkammer-2026-06-demo-fallback-evidence-manifest.md", german)
        self.assertIn("notarkammer-2026-06-demo-fallback-evidence-manifest.md", english)

    def test_manifest_defines_prepared_evidence_package_rules(self):
        german = (
            ROOT / "docs" / "de" / "demo" / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
        ).read_text(encoding="utf-8")
        english = (
            ROOT / "docs" / "en" / "demo" / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
        ).read_text(encoding="utf-8")

        for text in [german, english]:
            self.assertIn("NK-EVIDENCE-001-public-home", text)
            self.assertIn("NK-EVIDENCE-002-process-model", text)
            self.assertIn("NK-EVIDENCE-003-workspace-boundary", text)
            self.assertIn("NK-EVIDENCE-004-local-xnp-readiness", text)
            self.assertIn("NK-EVIDENCE-005-protected-pr", text)
            self.assertIn("redacted", text)
            self.assertIn("reviewed", text)
            self.assertIn("delete-after-demo", text)

    def test_manifest_blocks_unsafe_evidence_categories(self):
        combined = "\n".join(
            [
                (
                    ROOT
                    / "docs"
                    / locale
                    / "demo"
                    / "notarkammer-2026-06-demo-fallback-evidence-manifest.md"
                ).read_text(encoding="utf-8")
                for locale in ["de", "en"]
            ]
        )

        forbidden_evidence_classes = [
            "login fields",
            "callback values",
            "authorization code",
            "state value",
            "session cookie",
            "provider details",
            "real names",
            "XNP payload",
            "register payload",
            "land-register payload",
            "Login-Felder",
            "Callback-Werte",
            "Autorisierungscode",
            "State-Wert",
            "Session-Cookie",
            "Anbieterdetails",
            "echten Namen",
            "XNP-Payload",
            "Register-Payload",
            "Grundbuch-Payload",
        ]
        for forbidden in forbidden_evidence_classes:
            self.assertIn(forbidden, combined)


if __name__ == "__main__":
    unittest.main()
