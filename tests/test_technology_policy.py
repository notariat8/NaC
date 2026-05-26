from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import validate_technology_policy


class TechnologyPolicyValidationTest(unittest.TestCase):
    def _write_required_sync_targets(self, root: Path) -> None:
        for rel_path in (
            ".cursor/rules",
            ".github/copilot-instructions.md",
            "docs/de/START_HERE.md",
            "docs/en/START_HERE.md",
            "docs/de/vscode-copilot-start.md",
            "docs/en/vscode-copilot-start.md",
            "policies/language-policy.yaml",
        ):
            path = root / rel_path
            if rel_path.endswith(".md") or rel_path.endswith(".yaml"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder\n", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)

    def _write_policy(self, root: Path, text: str | None = None) -> None:
        (root / "policies").mkdir(parents=True, exist_ok=True)
        (root / "policies" / "technology-policy.yaml").write_text(
            text if text is not None else self._valid_policy_text(),
            encoding="utf-8",
        )

    def _valid_policy_text(self) -> str:
        return "\n".join(
            (
                "version: 1",
                "status: mandatory",
                "approved_stack:",
                "  documentation:",
                "    canonical_format: markdown",
                "    export:",
                "      pdf: pandoc",
                "      assets: svg_png",
                "  process_logic:",
                "    execution_language: python",
                "    approach: model_first",
                "    operating_surface: nac_cli",
                "    cli_entrypoint: nac",
                "    cli_wrapper: scripts/nac.py",
                "  visualization:",
                "    canonical_business_model: bpmn_2_0",
                "    canonical_source_format: bpmn_xml",
                "    canonical_directory: bpmn/",
                "    visual_editor: bpmn_js",
                "    model_extension: bpmn/nac-moddle.json",
                "    validator: scripts/validate_bpmn_models.py",
                "    allowed_overview_format: mermaid",
                "    disallowed_for_bpmn_source:",
                "      - mermaid",
                "      - plantuml",
                "repository_constraints:",
                "  enforce_cross_ide_sync: true",
                "  required_sync_targets:",
                "    - .cursor/rules",
                "    - .github/copilot-instructions.md",
                "    - docs/de/START_HERE.md",
                "    - docs/en/START_HERE.md",
                "    - docs/de/vscode-copilot-start.md",
                "    - docs/en/vscode-copilot-start.md",
                "    - policies/language-policy.yaml",
            )
        )

    def test_valid_minimal_repository_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_policy(root)
            self._write_required_sync_targets(root)
            (root / "bpmn").mkdir()

            self.assertEqual(validate_technology_policy.validate(root), [])

    def test_policy_reports_missing_mandatory_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_required_sync_targets(root)
            self._write_policy(
                root,
                "\n".join(
                    (
                        "approved_stack:",
                        "  documentation:",
                        "    canonical_format: asciidoc",
                        "  visualization:",
                        "    disallowed_for_bpmn_source:",
                        "      - mermaid",
                        "repository_constraints:",
                        "  enforce_cross_ide_sync: false",
                        "  required_sync_targets:",
                        "    - .cursor/rules",
                    )
                ),
            )

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "approved_stack.documentation.canonical_format.markdown",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "approved_stack.process_logic.execution_language.python",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "repository_constraints.enforce_cross_ide_sync.true",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "approved_stack.visualization.disallowed_for_bpmn_source.plantuml",
            errors,
        )

    def test_missing_technology_policy_reports_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_required_sync_targets(root)

            errors = validate_technology_policy.validate(root)

        self.assertEqual(
            errors,
            ["Pflichtdatei fehlt: policies/technology-policy.yaml"],
        )

    def test_policy_requires_all_sync_targets_to_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_policy(root)
            self._write_required_sync_targets(root)
            (root / ".github" / "copilot-instructions.md").unlink()

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Pflichtziel fuer Cross-IDE-Sync fehlt: .github/copilot-instructions.md",
            errors,
        )

    def test_policy_added_sync_targets_are_checked_for_existence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = self._valid_policy_text() + "\n    - docs/de/custom-sync.md"
            self._write_policy(root, policy_text)
            self._write_required_sync_targets(root)

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Pflichtziel fuer Cross-IDE-Sync fehlt: docs/de/custom-sync.md",
            errors,
        )

    def test_sync_targets_must_stay_inside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            policy_text = "\n".join(
                (
                    self._valid_policy_text(),
                    "    - /etc/passwd",
                    "    - ../outside.md",
                )
            )
            self._write_policy(root, policy_text)
            self._write_required_sync_targets(root)

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Cross-IDE-Sync-Ziel muss relativer Repo-Pfad innerhalb des Repos sein: "
            "/etc/passwd",
            errors,
        )
        self.assertIn(
            "Cross-IDE-Sync-Ziel muss relativer Repo-Pfad innerhalb des Repos sein: "
            "../outside.md",
            errors,
        )

    def test_manually_maintained_asciidoc_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_policy(root)
            self._write_required_sync_targets(root)
            (root / "docs").mkdir(exist_ok=True)
            (root / "docs" / "manual.adoc").write_text("= Manual\n", encoding="utf-8")
            (root / "out" / "generated").mkdir(parents=True)
            (root / "out" / "generated" / "export.adoc").write_text(
                "= Generated\n",
                encoding="utf-8",
            )

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Manuell gepflegte AsciiDoc-Quelle ist nicht erlaubt: docs/manual.adoc",
            errors,
        )
        self.assertFalse(any("out/generated/export.adoc" in error for error in errors))

    def test_mermaid_and_plantuml_sources_under_bpmn_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_policy(root)
            self._write_required_sync_targets(root)
            (root / "bpmn" / "usecases").mkdir(parents=True)
            (root / "bpmn" / "usecases" / "flow.mmd").write_text(
                "flowchart TD\n",
                encoding="utf-8",
            )
            (root / "bpmn" / "architecture.puml").write_text(
                "@startuml\n@enduml\n",
                encoding="utf-8",
            )

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "BPMN-Quellen muessen BPMN XML bleiben, nicht Mermaid/PlantUML: "
            "bpmn/architecture.puml",
            errors,
        )
        self.assertIn(
            "BPMN-Quellen muessen BPMN XML bleiben, nicht Mermaid/PlantUML: "
            "bpmn/usecases/flow.mmd",
            errors,
        )

    def test_strict_quality_gate_includes_technology_policy_check(self) -> None:
        from scripts import quality_gate

        strict_check_ids = [
            check_id for check_id, _title, _command in quality_gate.build_checks("strict")
        ]

        self.assertIn("technology_policy", strict_check_ids)

    def test_ci_path_filters_include_asciidoc_sources(self) -> None:
        for rel_path in (
            ".github/workflows/technology-policy.yml",
            ".github/workflows/quality-gate.yml",
        ):
            workflow = (validate_technology_policy.REPO_ROOT / rel_path).read_text(
                encoding="utf-8"
            )
            with self.subTest(workflow=rel_path):
                self.assertIn('"**/*.adoc"', workflow)
                self.assertIn('"**/*.asciidoc"', workflow)


if __name__ == "__main__":
    unittest.main()
