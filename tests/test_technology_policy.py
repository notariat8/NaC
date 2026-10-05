from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import validate_technology_policy


class TechnologyPolicyValidationTest(unittest.TestCase):
    def _write_required_sync_targets(self, root: Path) -> None:
        for rel_path in (
            "AGENTS.md",
            ".codex/agents",
            "docs/de/START_HERE.md",
            "docs/en/START_HERE.md",
            "policies/language-policy.yaml",
        ):
            path = root / rel_path
            if rel_path.endswith(".md") or rel_path.endswith(".yaml"):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("placeholder\n", encoding="utf-8")
            else:
                path.mkdir(parents=True, exist_ok=True)
        mirrors = (
            "AGENTS.md", "docs/de/START_HERE.md", "docs/en/START_HERE.md",
            "docs/de/minimum-requirements.md", "docs/en/minimum-requirements.md",
            ".pi/README.md",
        ) + tuple(
            f"{directory}/nac-{name}.{extension}"
            for directory, extension in ((".codex/agents", "toml"), (".pi/agents", "md"))
            for name in (
                "scope-mapper", "policy-reviewer", "docs-parity-reviewer",
                "validation-reviewer", "kg-reviewer", "bpmn-reviewer",
            )
        )
        for rel_path in mirrors:
            path = root / rel_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "Apply policies/technology-policy.yaml python_runtime_selection; "
                "discover with load_workspace_dependencies in Codex Desktop.\n",
                encoding="utf-8",
            )

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
                "    python_runtime_selection:",
                "      scope: local_agent_checks",
                "      codex_desktop_preferred: tool_discovered_bundled_python",
                "      discovery_tool: load_workspace_dependencies",
                "      explicit_project_environment: takes_precedence",
                "      other_environments: verified_project_or_system_python",
                "      executable_binding: absolute_path",
                "      minimum_version: '3.11'",
                "      smoke_test: version_and_required_imports",
                "      keep_selected_runtime: true",
                "      preserve_dependency_constraints: true",
                "      retry_broken_path_python: false",
                "      mutate_global_python_or_path: false",
                "      auto_install_runtime_or_packages: false",
                "      change_ci_or_release_runtime: false",
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
                "  enforce_codex_agent_sync: true",
                "  active_ai_ide: codex",
                "  cursor_workspace_files_allowed: false",
                "  github_copilot_workspace_files_allowed: false",
                "  required_sync_targets:",
                "    - AGENTS.md",
                "    - .codex/agents",
                "    - docs/de/START_HERE.md",
                "    - docs/en/START_HERE.md",
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
                        "  enforce_codex_agent_sync: false",
                        "  required_sync_targets:",
                        "    - AGENTS.md",
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
            "repository_constraints.enforce_codex_agent_sync.true",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "repository_constraints.active_ai_ide.codex",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "repository_constraints.cursor_workspace_files_allowed.false",
            errors,
        )
        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "repository_constraints.github_copilot_workspace_files_allowed.false",
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

    def test_local_codex_checks_reject_path_python_as_preferred_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_required_sync_targets(root)
            self._write_policy(
                root,
                self._valid_policy_text().replace(
                    "codex_desktop_preferred: tool_discovered_bundled_python",
                    "codex_desktop_preferred: path_python",
                ),
            )
            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "approved_stack.process_logic.python_runtime_selection."
            "codex_desktop_preferred.tool_discovered_bundled_python",
            errors,
        )

    def test_missing_runtime_preference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_required_sync_targets(root)
            self._write_policy(
                root,
                self._valid_policy_text().replace(
                    "      discovery_tool: load_workspace_dependencies\n", ""
                ),
            )
            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Pflichtwert fehlt in technology-policy: "
            "approved_stack.process_logic.python_runtime_selection."
            "discovery_tool.load_workspace_dependencies",
            errors,
        )

    def test_runtime_selection_preserves_local_only_and_project_boundaries(self) -> None:
        cases = (
            ("scope", "local_agent_checks", "all_python_runs"),
            ("explicit_project_environment", "takes_precedence", "ignored"),
            ("executable_binding", "absolute_path", "path_alias"),
            ("minimum_version", "'3.11'", "'3.8'"),
            ("smoke_test", "version_and_required_imports", "version_only"),
            ("keep_selected_runtime", "true", "false"),
            ("preserve_dependency_constraints", "true", "false"),
            ("retry_broken_path_python", "false", "true"),
            ("mutate_global_python_or_path", "false", "true"),
            ("auto_install_runtime_or_packages", "false", "true"),
            ("change_ci_or_release_runtime", "false", "true"),
        )
        for key, expected, invalid in cases:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                self._write_required_sync_targets(root)
                self._write_policy(
                    root,
                    self._valid_policy_text().replace(
                        f"      {key}: {expected}", f"      {key}: {invalid}"
                    ),
                )
                errors = validate_technology_policy.validate(root)
                self.assertTrue(
                    any(f"python_runtime_selection.{key}." in error for error in errors),
                    errors,
                )

    def test_quality_gate_python_children_keep_selected_executable(self) -> None:
        import sys
        from scripts import quality_gate

        for check_id, _title, command in quality_gate.build_checks("strict"):
            if check_id == "unit_tests" or any(
                argument.endswith(".py") for argument in command
            ):
                with self.subTest(check_id=check_id):
                    self.assertEqual(command[0], sys.executable)

    def test_runtime_selection_boolean_strings_are_rejected(self) -> None:
        runtime_keys = validate_technology_policy.PYTHON_RUNTIME_POLICY
        for keys, expected in (
            *((keys, "true") for keys in validate_technology_policy.EXPECTED_TRUE_KEYS
              if keys[:len(runtime_keys)] == runtime_keys),
            *((keys, "false") for keys in validate_technology_policy.EXPECTED_FALSE_KEYS
              if keys[:len(runtime_keys)] == runtime_keys),
        ):
            for quote in ("'", '"'):
                with self.subTest(key=keys[-1], quote=quote), tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    self._write_required_sync_targets(root)
                    self._write_policy(
                        root,
                        self._valid_policy_text().replace(
                            f"{keys[-1]}: {expected}",
                            f"{keys[-1]}: {quote}{expected}{quote}",
                        ),
                    )
                    errors = validate_technology_policy.validate(root)
                    self.assertIn(
                        "Pflichtwert fehlt in technology-policy: "
                        f"{validate_technology_policy.dotted(keys)}.{expected}",
                        errors,
                    )

    def test_runtime_selection_mirrors_are_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_required_sync_targets(root)
            self._write_policy(root)
            (root / "AGENTS.md").write_text("placeholder\n", encoding="utf-8")
            errors = validate_technology_policy.validate_python_runtime_mirrors(root)

        self.assertIn("Python-Laufzeitregel fehlt im Spiegel: AGENTS.md", errors)

    def test_runtime_mirror_cannot_keep_only_policy_reference(self) -> None:
        for rel_path in validate_technology_policy.PYTHON_RUNTIME_MIRROR_FILES:
            for marker in (
                "policies/technology-policy.yaml", "python_runtime_selection",
                "load_workspace_dependencies",
            ):
                with self.subTest(path=rel_path, marker=marker), tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    self._write_required_sync_targets(root)
                    self._write_policy(root)
                    path = root / rel_path
                    path.write_text(
                        path.read_text(encoding="utf-8").replace(marker, "omitted"),
                        encoding="utf-8",
                    )
                    errors = validate_technology_policy.validate(root)
                    self.assertIn(
                        f"Python-Laufzeitregel fehlt im Spiegel: {rel_path}",
                        errors,
                    )

    def test_all_runtime_platform_mirrors_are_required(self) -> None:
        for rel_path in validate_technology_policy.PYTHON_RUNTIME_MIRROR_FILES:
            with self.subTest(path=rel_path), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                self._write_required_sync_targets(root)
                self._write_policy(root)
                (root / rel_path).unlink()
                errors = validate_technology_policy.validate(root)
                self.assertIn(f"Python-Laufzeitspiegel fehlt: {rel_path}", errors)

    def test_runtime_selection_ci_filters_cover_both_platforms(self) -> None:
        from scripts.validate_technology_policy import load_simple_yaml_mapping

        root = validate_technology_policy.REPO_ROOT
        technology = load_simple_yaml_mapping(
            root / ".github/workflows/technology-policy.yml"
        )
        quality = load_simple_yaml_mapping(root / ".github/workflows/quality-gate.yml")
        for workflow, event in (
            (technology, "pull_request"),
            (quality, "pull_request"),
            (quality, "push"),
        ):
            with self.subTest(event=event, workflow=workflow["name"]):
                self.assertIn(".pi/**", workflow["on"][event]["paths"])
        for language in ("de", "en"):
            self.assertIn(
                f"docs/{language}/minimum-requirements.md",
                technology["on"]["pull_request"]["paths"],
            )

    def test_policy_requires_all_sync_targets_to_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_policy(root)
            self._write_required_sync_targets(root)
            (root / "AGENTS.md").unlink()

            errors = validate_technology_policy.validate(root)

        self.assertIn(
            "Pflichtziel fuer Codex-Agent-Sync fehlt: AGENTS.md",
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
            "Pflichtziel fuer Codex-Agent-Sync fehlt: docs/de/custom-sync.md",
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
            "Codex-Agent-Sync-Ziel muss relativer Repo-Pfad innerhalb des Repos sein: "
            "/etc/passwd",
            errors,
        )
        self.assertIn(
            "Codex-Agent-Sync-Ziel muss relativer Repo-Pfad innerhalb des Repos sein: "
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

    def test_codex_only_workspace_rejects_cursor_and_github_copilot_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._write_policy(root)
            self._write_required_sync_targets(root)
            (root / ".cursor" / "rules").mkdir(parents=True)
            (root / ".github").mkdir()
            (root / ".github" / "copilot-instructions.md").write_text(
                "legacy instructions\n",
                encoding="utf-8",
            )

            errors = validate_technology_policy.validate(root)

        self.assertIn("Codex-only Workspace darf kein .cursor enthalten", errors)
        self.assertIn(
            "Codex-only Workspace darf kein .github/copilot-instructions.md enthalten",
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
