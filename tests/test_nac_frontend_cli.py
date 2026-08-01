from __future__ import annotations

import argparse
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from nac_cli.cli import command_frontend


class FrontendCliTests(unittest.TestCase):
    def test_workbench_verify_runs_python_and_ast_gates(self) -> None:
        args = argparse.Namespace(repo_root=Path("/repo"), frontend_command="workbench-verify")
        completed = subprocess.CompletedProcess(["node"], 0)
        with (
            patch("nac_cli.cli.resolve_repo_root", return_value=Path("/repo")),
            patch("nac_cli.cli.run_script", return_value=0) as python_gate,
            patch("nac_cli.cli.shutil.which", return_value="/usr/bin/node"),
            patch("nac_cli.cli.subprocess.run", return_value=completed) as ast_gate,
        ):
            self.assertEqual(command_frontend(args), 0)
        python_gate.assert_called_once_with(
            Path("/repo"), "scripts/validate_generic_workbench_foundation.py", []
        )
        ast_gate.assert_called_once_with(
            ["/usr/bin/node", "scripts/validate-read-only-boundary.cjs"],
            cwd=Path("/repo/spfx/nac-bpmn-viewer"),
            check=False,
        )

    def test_workbench_verify_propagates_ast_failure(self) -> None:
        args = argparse.Namespace(repo_root=Path("/repo"), frontend_command="workbench-verify")
        with (
            patch("nac_cli.cli.resolve_repo_root", return_value=Path("/repo")),
            patch("nac_cli.cli.run_script", return_value=0),
            patch("nac_cli.cli.shutil.which", return_value="/usr/bin/node"),
            patch(
                "nac_cli.cli.subprocess.run",
                return_value=subprocess.CompletedProcess(["node"], 7),
            ),
        ):
            self.assertEqual(command_frontend(args), 7)


if __name__ == "__main__":
    unittest.main()
