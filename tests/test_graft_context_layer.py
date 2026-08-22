from __future__ import annotations

import shutil
import unittest
from pathlib import Path

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
            errors = graft_validator._validate_graft_check()
        finally:
            graft_validator.shutil.which = original
        self.assertEqual(len(errors), 1)
        self.assertIn("npm i -g @nanonets/graft", errors[0])

    def test_graft_check_passes_when_cli_available(self) -> None:
        if shutil.which("graft") is None:
            self.skipTest("graft-CLI in dieser Umgebung nicht installiert")
        self.assertEqual(graft_validator._validate_graft_check(), [])


if __name__ == "__main__":
    unittest.main()
