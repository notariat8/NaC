from __future__ import annotations

import contextlib
import io
import sys
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
        self.assertIn("Offene Angaben", output)

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


if __name__ == "__main__":
    unittest.main()
