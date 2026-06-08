from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_web.server import NaCLocalWebApp  # noqa: E402


class PublicOnboardingCopyTests(unittest.TestCase):
    def test_customer_dns_check_copy_names_notariat8_without_provider_terms(self) -> None:
        record_name = "_nac.myjur.de"

        def fake_resolver(name: str) -> dict[str, object]:
            self.assertEqual(name, record_name)
            return {
                "name": record_name,
                "values": ["nac-domain-verification=e6b96f425ef94064ae897decf6a57da5"],
                "resolver_error": "",
            }

        app = NaCLocalWebApp(REPO_ROOT, dns_resolver=fake_resolver)

        status, _, body = app.handle(
            "/onboarding/dns-check"
            "?audience=customer"
            "&domain=myjur.de"
            "&tenant_slug=myjur"
            "&admin_email=ofunk@myjur.de"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("notariat8 Domain-Check", html)
        self.assertIn("E-Mail-Adresse der verantwortlichen Person", html)
        self.assertIn("notariat8 führt Sie anschließend durch die nächsten Schritte", html)
        self.assertNotIn("Oracle", html)
        self.assertNotIn("Oracle Cloud", html)
        self.assertNotIn("OCI", html)
        self.assertNotIn("NaC", html)
        self.assertNotIn("Administrations-E-Mail", html)
        self.assertNotIn("notariat8-Zugang", html)
        self.assertNotIn("NaC-Zugang", html)
        self.assertNotIn("für NaC bestätigt", html)
        self.assertNotIn("technische Einrichtung", html)

    def test_customer_readiness_copy_names_notariat8_not_nac_product(self) -> None:
        app = NaCLocalWebApp(REPO_ROOT)

        status, _, body = app.handle(
            "/onboarding/readiness"
            "?audience=customer"
            "&domain_hint=myjur.de"
            "&tenant_slug=myjur"
            "&admin_email=ofunk@myjur.de"
        )
        html = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("für notariat8 vorbereitet", html)
        self.assertIn("notariat8-Referenz", html)
        self.assertIn("E-Mail-Adresse der verantwortlichen Person", html)
        self.assertNotIn("für NaC vorbereitet", html)
        self.assertNotIn("NaC-Kennung", html)
        self.assertNotIn("Administrations-E-Mail", html)
        self.assertNotIn("notariat8-Zugang", html)


if __name__ == "__main__":
    unittest.main()
