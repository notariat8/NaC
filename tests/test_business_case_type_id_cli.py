from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402
from notary_kg import cli as notary_kg_cli  # noqa: E402
from notary_kg.cli import main as notary_kg_main  # noqa: E402


COMMAND_EXPECTATIONS = {
    "business-case-inventory": (
        "- canonical business-case types: 20",
        "- legacy aliases: 2",
        "- Vorgangsartenregister required: True",
        "- Prozessregister required: False",
        "- viewer required: False",
    ),
    "process-ontology-contract": (
        "- canonical business-case types: 20",
        "- legacy aliases: 2",
        "- type_validity_requires_vorgangsartenregister: True",
        "- type_validity_requires_process_register: False",
        "- type_validity_requires_viewer: False",
    ),
    "process-ontology-schema-gap": (
        "- canonical BusinessCaseTypeIds: 20",
        "- Vorgangsartenregister required projection: True",
        "- Prozessregister optional projection: True",
        "- legacy Akten.Vorgangstyp protected: True",
        "- legacy Akten.Vorgangstyp patch planned: False",
    ),
    "process-ontology-schema-apply-plan": (
        "- total steps: 33",
        "- legacy Akten.Vorgangstyp patch planned: False",
        "- live execution approval: BLOCKED_PENDING_S6_S7_APPROVAL",
    ),
    "process-ontology-schema-apply-readiness": (
        "- workspace apply units: 66",
        "- live apply readiness: OWNER_GATE_REQUIRED",
        "- live execution approval: BLOCKED_PENDING_S6_S7_APPROVAL",
    ),
    "process-ontology-schema-apply-execution-contract": (
        "- workspace apply units: 66",
        "- live apply contract: BLOCKED_PENDING_S6_S7_APPROVAL",
    ),
    "process-ontology-schema-apply-runner-dry-run": (
        "- dry-run steps: 66",
        "- executes Graph requests: False",
        "- writes SharePoint: False",
        "- live execution approval: BLOCKED_PENDING_S6_S7_APPROVAL",
    ),
}


class BusinessCaseTypeIdCliTests(unittest.TestCase):
    def test_nac_kg_text_commands_render_current_contracts_without_crashing(self) -> None:
        parser = nac_cli.build_parser()

        for command, expected_lines in COMMAND_EXPECTATIONS.items():
            with self.subTest(command=command):
                args = parser.parse_args(["--repo-root", str(REPO_ROOT), "kg", command])
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = args.func(args)

                self.assertEqual(exit_code, 0)
                for expected_line in expected_lines:
                    self.assertIn(expected_line, output.getvalue())

    def test_underlying_notary_kg_text_route_renders_inventory_v02(self) -> None:
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = notary_kg_main(
                ["--repo-root", str(REPO_ROOT), "--format", "text", "business-case-inventory"]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("- canonical business-case types: 20", output.getvalue())
        self.assertIn("- legacy aliases: 2", output.getvalue())

    def test_cli_help_describes_identity_and_legacy_boundaries(self) -> None:
        nac_help = _normalize_argparse_help(
            nac_cli.build_parser()._subparsers._group_actions[0].choices["kg"].format_help()
        )
        notary_help = _normalize_argparse_help(notary_kg_cli.build_parser().format_help())

        self.assertIn("kanonische Vorgangsarten-Inventar", nac_help)
        self.assertIn("Offline-S2-Plan ohne Patch des Legacy-Felds Akten.Vorgangstyp", nac_help)
        self.assertIn("canonical notarial business-case type inventory", notary_help)
        self.assertIn("without patching legacy Akten.Vorgangstyp", notary_help)


def _normalize_argparse_help(value: str) -> str:
    return " ".join(value.split()).replace("- ", "-")


if __name__ == "__main__":
    unittest.main()
