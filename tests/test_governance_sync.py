from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import validate_governance_sync


class GovernanceSyncValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_repo_root = validate_governance_sync.REPO_ROOT

    def tearDown(self) -> None:
        validate_governance_sync.REPO_ROOT = self.original_repo_root

    def _write_minimal_repo(self, root: Path, policy_text: str) -> None:
        (root / "policies").mkdir()
        (root / "docs" / "de").mkdir(parents=True)
        (root / "docs" / "en").mkdir(parents=True)
        (root / "policies" / "process-policy.yaml").write_text(
            policy_text,
            encoding="utf-8",
        )
        (root / "docs" / "de" / "regelarchitektur.md").write_text(
            "# Regelarchitektur\n",
            encoding="utf-8",
        )
        (root / "docs" / "en" / "regelarchitektur.md").write_text(
            "# Rule Architecture\n",
            encoding="utf-8",
        )

    def test_process_policy_requires_delivery_modes_and_rule_architecture_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "    owner_direct_main:",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            self.assertEqual(validate_governance_sync.validate_process_policy_file(), [])

    def test_process_policy_reports_missing_owner_direct_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    "change_management:",
                    "  delivery_modes:",
                    "    protected_pr:",
                    "rule_architecture:",
                    "  human_explanation_de: docs/de/regelarchitektur.md",
                    "  human_explanation_en: docs/en/regelarchitektur.md",
                )
            )
            self._write_minimal_repo(root, policy_text)
            validate_governance_sync.REPO_ROOT = root

            errors = validate_governance_sync.validate_process_policy_file()

        self.assertIn("Pflichtabschnitt fehlt in process-policy: owner_direct_main:", errors)


if __name__ == "__main__":
    unittest.main()
