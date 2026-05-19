from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli.cli import main  # noqa: E402


def run_cli(*argv: str) -> tuple[int, str]:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        rc = main(["--repo-root", str(REPO_ROOT), *argv])
    return rc, buffer.getvalue()


class NaCCliTests(unittest.TestCase):
    def test_status_shows_single_entrypoint(self) -> None:
        rc, output = run_cli("status")

        self.assertEqual(rc, 0)
        self.assertIn("NaC Status", output)
        self.assertIn("nac doctor --profile strict", output)
        self.assertIn("nac web", output)
        self.assertIn("nac operator --open", output)

    def test_config_list_includes_language_policy(self) -> None:
        rc, output = run_cli("config", "list")

        self.assertEqual(rc, 0)
        self.assertIn("language-policy", output)
        self.assertIn("policies/language-policy.yaml", output)

    def test_bpmn_list_includes_immobilienkaufvertrag(self) -> None:
        rc, output = run_cli("bpmn", "list")

        self.assertEqual(rc, 0)
        self.assertIn("immobilienkaufvertrag", output)

    def test_bpmn_show_can_emit_svg(self) -> None:
        rc, output = run_cli("bpmn", "show", "immobilienkaufvertrag", "--format", "svg")

        self.assertEqual(rc, 0)
        self.assertIn("<svg", output)
        self.assertIn("Auftrag und Beteiligte", output)
        self.assertIn("xnp_local", output)

    def test_kg_status_is_available_through_nac_cli(self) -> None:
        rc, output = run_cli("kg", "status")

        self.assertEqual(rc, 0)
        self.assertIn("NaC KG development status", output)

    def test_plugin_actions_are_listed(self) -> None:
        rc, output = run_cli("plugins", "actions")

        self.assertEqual(rc, 0)
        self.assertIn("nac plugins card-readiness", output)
        self.assertIn("nac plugins xnp-reader-prompt", output)
        self.assertIn("nac plugins pkcs7-inspect", output)

    def test_pkcs7_plugin_action_is_reachable_through_nac_cli(self) -> None:
        rc, output = run_cli("plugins", "pkcs7-inspect", "--json")

        self.assertEqual(rc, 0)
        self.assertIn('"plugin": "nac-pkcs7-certbundle"', output)
        self.assertIn('"overall_status": "manual_review"', output)

    def test_tenant_init_status_and_write_demo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tenant_repo = Path(temp_dir) / "demo8notariat"

            rc, output = run_cli(
                "tenant",
                "init",
                "--repo",
                str(tenant_repo),
                "--name",
                "demo8notariat",
                "--remote-url",
                "https://github.com/ofunk/demo8notariat.git",
            )
            self.assertEqual(rc, 0)
            self.assertIn("NaC-Datenrepo initialisiert", output)
            self.assertTrue((tenant_repo / ".nac-tenant.json").is_file())

            rc, output = run_cli("tenant", "status", "--repo", str(tenant_repo))
            self.assertEqual(rc, 0)
            self.assertIn("Demo-Vorgänge: 0", output)
            self.assertIn("https://github.com/ofunk/demo8notariat.git", output)

            rc, output = run_cli(
                "tenant",
                "write-demo",
                "immobilienkaufvertrag",
                "--repo",
                str(tenant_repo),
                "--case-id",
                "DEMO-2026-0001",
            )
            self.assertEqual(rc, 0)
            self.assertIn("NaC-Demo-Vorgang geschrieben", output)

            case_file = tenant_repo / "daten" / "demo" / "DEMO-2026-0001" / "case.json"
            self.assertTrue(case_file.is_file())
            case_text = case_file.read_text(encoding="utf-8")
            self.assertIn('"data_classification": "synthetic_demo_only"', case_text)
            self.assertIn('"real_mandate_data_allowed": false', case_text)


if __name__ == "__main__":
    unittest.main()
