from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import validate_spec_traceability


REPO_ROOT = Path(__file__).resolve().parents[1]


class SpecTraceabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.original_repo_root = validate_spec_traceability.REPO_ROOT

    def tearDown(self) -> None:
        validate_spec_traceability.REPO_ROOT = self.original_repo_root

    def run_git(self, root: Path, args: list[str]) -> None:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def init_git_repo(self, root: Path) -> None:
        self.run_git(root, ["init"])
        self.run_git(root, ["config", "user.email", "codex@example.invalid"])
        self.run_git(root, ["config", "user.name", "Codex Test"])

    def commit_all(self, root: Path, message: str = "baseline") -> None:
        self.run_git(root, ["add", "."])
        self.run_git(root, ["commit", "-m", message])

    def commit_empty(self, root: Path, message: str = "baseline") -> None:
        self.run_git(root, ["commit", "--allow-empty", "-m", message])

    def test_contract_declares_required_spec_manifest_fields(self) -> None:
        contract = json.loads(
            (REPO_ROOT / "workflows/contracts/spec-traceability.contract.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(contract["schema_version"], "nac.spec-traceability/v0.1")
        self.assertEqual(
            contract["required_manifest_fields"],
            [
                "schema_version",
                "spec_id",
                "leading_issue",
                "risk_gate",
                "delivery_mode",
                "acceptance_ids",
                "validation_commands",
            ],
        )
        self.assertIn("AC-001", contract["acceptance_id_pattern_examples"])

    def test_process_policy_enables_spec_traceability(self) -> None:
        policy = validate_spec_traceability.load_simple_yaml_mapping(
            REPO_ROOT / "policies/process-policy.yaml"
        )
        spec_traceability = policy["spec_traceability"]

        self.assertTrue(spec_traceability["enabled"])
        self.assertTrue(spec_traceability["require_acceptance_ids_for_nontrivial_specs"])
        self.assertEqual(
            spec_traceability["contract"],
            "workflows/contracts/spec-traceability.contract.json",
        )
        self.assertIn("scripts/validate_spec_traceability.py", spec_traceability["enforced_by"])

    def test_issue_and_pr_templates_expose_spec_traceability_fields(self) -> None:
        required_markers = (
            "## Spec-Traceability",
            "Spec:",
            "Plan:",
            "Akzeptanzkriterien:",
            "AC-IDs:",
            "Test-/Validator-Nachweis:",
        )
        for relative_path in (
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/compliance_change.md",
            ".github/ISSUE_TEMPLATE/feature_request.md",
            ".github/ISSUE_TEMPLATE/process_release.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
        ):
            text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
            with self.subTest(path=relative_path):
                for marker in required_markers:
                    self.assertIn(marker, text)

    def test_strict_quality_gate_runs_spec_traceability_validator(self) -> None:
        quality_gate = (REPO_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")

        self.assertIn("spec_traceability", quality_gate)
        self.assertIn("scripts/validate_spec_traceability.py", quality_gate)

    def test_validator_accepts_well_formed_manifest_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/de/superpowers/specs").mkdir(parents=True)
            spec = root / "docs/de/superpowers/specs/example.md"
            spec.write_text(
                "\n".join(
                    (
                        "# Example Spec",
                        "",
                        "```nac-spec-traceability",
                        "schema_version: nac.spec-traceability/v0.1",
                        "spec_id: example-spec",
                        "leading_issue: https://github.com/notariat8/NaC/issues/1",
                        "risk_gate: Policy",
                        "delivery_mode: Owner Direct",
                        "acceptance_ids:",
                        "  - AC-001",
                        "validation_commands:",
                        "  - python scripts/validate_spec_traceability.py",
                        "```",
                        "",
                        "## Akzeptanz",
                        "",
                        "- AC-001: Beispielkriterium.",
                    )
                ),
                encoding="utf-8",
            )
            validate_spec_traceability.REPO_ROOT = root

            self.assertEqual(validate_spec_traceability.validate_manifest_blocks(), [])

    def test_validator_reports_missing_acceptance_id_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/de/superpowers/specs").mkdir(parents=True)
            spec = root / "docs/de/superpowers/specs/example.md"
            spec.write_text(
                "\n".join(
                    (
                        "# Example Spec",
                        "",
                        "```nac-spec-traceability",
                        "schema_version: nac.spec-traceability/v0.1",
                        "spec_id: example-spec",
                        "leading_issue: https://github.com/notariat8/NaC/issues/1",
                        "risk_gate: Policy",
                        "delivery_mode: Owner Direct",
                        "acceptance_ids:",
                        "  - AC-404",
                        "validation_commands:",
                        "  - python scripts/validate_spec_traceability.py",
                        "```",
                        "",
                        "## Akzeptanz",
                        "",
                        "- AC-001: Beispielkriterium.",
                    )
                ),
                encoding="utf-8",
            )
            validate_spec_traceability.REPO_ROOT = root

            errors = validate_spec_traceability.validate_manifest_blocks()

        self.assertIn(
            "Akzeptanz-ID aus Manifest fehlt im Spec-Text: docs/de/superpowers/specs/example.md AC-404",
            errors,
        )

    def test_changed_files_reports_tracked_and_untracked_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_git_repo(root)
            specs_root = root / "docs/de/superpowers/specs"
            specs_root.mkdir(parents=True)
            existing_spec = specs_root / "existing.md"
            existing_spec.write_text("# Existing\n", encoding="utf-8")
            self.commit_all(root)

            existing_spec.write_text("# Existing\n\nChanged.\n", encoding="utf-8")
            (specs_root / "new.md").write_text("# New\n", encoding="utf-8")

            validate_spec_traceability.REPO_ROOT = root

            with patch.dict("os.environ", {}, clear=True):
                files = validate_spec_traceability.changed_files()

        self.assertEqual(
            files,
            [
                "docs/de/superpowers/specs/existing.md",
                "docs/de/superpowers/specs/new.md",
            ],
        )

    def test_changed_spec_without_manifest_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_git_repo(root)
            specs_root = root / "docs/de/superpowers/specs"
            specs_root.mkdir(parents=True)
            spec = specs_root / "existing.md"
            spec.write_text("# Existing\n", encoding="utf-8")
            self.commit_all(root)
            spec.write_text("# Existing\n\nFachlich geändert.\n", encoding="utf-8")
            validate_spec_traceability.REPO_ROOT = root

            with patch.dict("os.environ", {}, clear=True):
                errors = validate_spec_traceability.validate_changed_spec_manifests()

        self.assertIn(
            "Spec-Datei ohne nac-spec-traceability-Manifest geändert: docs/de/superpowers/specs/existing.md",
            errors,
        )

    def test_new_spec_without_manifest_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_git_repo(root)
            self.commit_empty(root)
            specs_root = root / "docs/de/superpowers/specs"
            specs_root.mkdir(parents=True)
            spec = specs_root / "new.md"
            spec.write_text("# New Spec\n", encoding="utf-8")
            validate_spec_traceability.REPO_ROOT = root

            with patch.dict("os.environ", {}, clear=True):
                errors = validate_spec_traceability.validate_changed_spec_manifests()

        self.assertIn(
            "Spec-Datei ohne nac-spec-traceability-Manifest geändert: docs/de/superpowers/specs/new.md",
            errors,
        )

    def test_unchanged_historical_spec_without_manifest_is_not_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_git_repo(root)
            specs_root = root / "docs/de/superpowers/specs"
            specs_root.mkdir(parents=True)
            spec = specs_root / "historical.md"
            spec.write_text("# Historical Spec\n", encoding="utf-8")
            self.commit_all(root)
            validate_spec_traceability.REPO_ROOT = root

            with patch.dict("os.environ", {}, clear=True):
                errors = validate_spec_traceability.validate_changed_spec_manifests()

        self.assertEqual(errors, [])

    def test_non_spec_markdown_change_does_not_require_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.init_git_repo(root)
            self.commit_empty(root)
            docs_root = root / "docs/de"
            docs_root.mkdir(parents=True)
            (docs_root / "notes.md").write_text("# Notes\n", encoding="utf-8")
            validate_spec_traceability.REPO_ROOT = root

            with patch.dict("os.environ", {}, clear=True):
                errors = validate_spec_traceability.validate_changed_spec_manifests()

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
