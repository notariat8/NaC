from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_graft_context_layer as graft_validator


REPO_ROOT = Path(__file__).resolve().parents[1]


class GraftContextLayerWiringTests(unittest.TestCase):
    """Die Verdrahtung des Graft Context Layer gegen das echte Repo pruefen."""

    def test_policy_is_present_and_mandatory(self) -> None:
        self.assertEqual(graft_validator._validate_policy(), [])

    def test_pi_settings_bind_skill_not_mcp(self) -> None:
        self.assertEqual(graft_validator._validate_settings(), [])

    def test_agents_md_has_graft_block(self) -> None:
        self.assertEqual(graft_validator._validate_agents_block(), [])

    def test_startup_check_integrates_graft(self) -> None:
        self.assertEqual(graft_validator._validate_startup(), [])

    def test_quality_gate_binds_graft_validator(self) -> None:
        self.assertEqual(graft_validator._validate_quality_gate(), [])

    def test_pi_skill_present(self) -> None:
        self.assertEqual(graft_validator._validate_skill(), [])

    def test_verification_contract_present(self) -> None:
        self.assertEqual(graft_validator._validate_contract(), [])


class GraftCheckBehaviourTests(unittest.TestCase):
    def test_missing_graft_cli_reports_clear_error(self) -> None:
        original = graft_validator.shutil.which
        graft_validator.shutil.which = lambda _command: None
        try:
            with patch.dict(
                graft_validator.os.environ,
                {
                    "APPDATA": "Z:/missing",
                    "USERPROFILE": "Z:/missing",
                    "ProgramFiles": "Z:/missing",
                },
            ):
                errors = graft_validator._validate_graft_check()
        finally:
            graft_validator.shutil.which = original
        self.assertEqual(len(errors), 1)
        self.assertIn("npm i -g @nanonets/graft", errors[0])

    def test_graft_check_passes_when_cli_available(self) -> None:
        if shutil.which("graft") is None:
            self.skipTest("graft-CLI in dieser Umgebung nicht installiert")
        self.assertEqual(graft_validator._validate_graft_check(), [])

    def test_windows_cmd_wrapper_resolves_to_bound_node_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            wrapper = root / "graft.cmd"
            node = root / "node.exe"
            cli = root / "node_modules" / "@nanonets" / "graft" / "dist" / "cli.js"
            cli.parent.mkdir(parents=True)
            for path in (wrapper, node, cli):
                path.write_text("fixture", encoding="utf-8")

            def which(command: str) -> str | None:
                return str(wrapper) if command == "graft" else None

            with (
                patch.object(
                    graft_validator, "_is_windows_runtime", return_value=True
                ),
                patch.object(graft_validator.shutil, "which", side_effect=which),
                patch.dict(
                    graft_validator.os.environ,
                    {"APPDATA": "Z:/missing", "USERPROFILE": "Z:/missing"},
                ),
            ):
                command = graft_validator._resolve_graft_check_command()

        self.assertEqual(command, [str(node.resolve()), str(cli.resolve()), "check"])

    def test_windows_standard_npm_location_does_not_require_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            appdata = root / "appdata"
            program_files = root / "program-files"
            wrapper = appdata / "npm" / "graft.cmd"
            cli = (
                appdata
                / "npm"
                / "node_modules"
                / "@nanonets"
                / "graft"
                / "dist"
                / "cli.js"
            )
            node = program_files / "nodejs" / "node.exe"
            cli.parent.mkdir(parents=True)
            node.parent.mkdir(parents=True)
            wrapper.write_text("fixture", encoding="utf-8")
            cli.write_text("fixture", encoding="utf-8")
            node.write_text("fixture", encoding="utf-8")
            with (
                patch.object(
                    graft_validator, "_is_windows_runtime", return_value=True
                ),
                patch.object(graft_validator.shutil, "which", return_value=None),
                patch.dict(
                    graft_validator.os.environ,
                    {
                        "APPDATA": str(appdata),
                        "USERPROFILE": str(root / "missing-user"),
                        "ProgramFiles": str(program_files),
                    },
                ),
            ):
                command = graft_validator._resolve_graft_check_command()
        self.assertEqual(command, [str(node.resolve()), str(cli.resolve()), "check"])


if __name__ == "__main__":
    unittest.main()
