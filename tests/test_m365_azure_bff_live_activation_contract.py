from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import yaml

from scripts import validate_m365_azure_bff_live_activation as validator


REPO_ROOT = Path(__file__).resolve().parents[1]


class M365AzureBffLiveActivationContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()
        self.root = Path(self._temp.name)
        self._copy_contracts()
        self._write_valid_sources()

    def tearDown(self) -> None:
        self._temp.cleanup()

    def _write_bootstrap_source(
        self,
        path: Path,
        outer_source: str,
        bootstrap_source: str,
    ) -> None:
        tree = ast.parse(outer_source)
        assignments = [
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "_BOOTSTRAP_SOURCE"
                for target in node.targets
            )
        ]
        self.assertEqual(len(assignments), 1)
        assignment = assignments[0]
        self.assertIsNotNone(assignment.end_lineno)
        lines = outer_source.splitlines(keepends=True)
        lines[assignment.lineno - 1 : assignment.end_lineno] = [
            f"_BOOTSTRAP_SOURCE = {bootstrap_source!r}\n"
        ]
        path.write_text("".join(lines), encoding="utf-8")

    def test_structured_fixture_passes(self) -> None:
        self.assertEqual(validator.validate(self.root), [])

    def test_issue_and_acceptance_binding_mutation_fails(self) -> None:
        payload = self._domain()
        payload["leading_issue"] = validator.PARENT_ISSUE
        payload["acceptance_ids"] = payload["acceptance_ids"][:-1]
        self._write_domain(payload)
        errors = validator.validate(self.root)
        self.assertTrue(any("leading_issue" in error for error in errors))
        self.assertTrue(any("acceptance_ids" in error for error in errors))

    def test_toolchain_approval_binding_mutation_fails(self) -> None:
        payload = self._domain()
        payload["consolidated_owner_gate"][
            "approval_payload_fields_exact"
        ].remove("toolchain_attestations_sha256")
        payload["consolidated_owner_gate"][
            "toolchain_attestation_binding"
        ]["input_fields_exact"].pop()
        self._write_domain(payload)
        errors = validator.validate(self.root)
        self.assertTrue(any("approval payload fields" in error for error in errors))
        self.assertTrue(
            any("toolchain attestation fields" in error for error in errors)
        )

    def test_owner_association_contract_and_source_mutations_fail(self) -> None:
        payload = self._domain()
        payload["consolidated_owner_gate"]["immutable_approval_reference"][
            "owner_author_associations_exact"
        ] = ["OWNER", "COLLABORATOR"]
        self._write_domain(payload)
        verification = self._verification()
        verification["exact_bindings"]["owner_author_associations_exact"] = [
            "OWNER",
            "COLLABORATOR",
        ]
        verification["exact_bindings"][
            "missing_or_malformed_author_association_behavior"
        ] = "allow"
        self._write_verification(verification)
        composition = self.root / validator.COMPOSITION_PATH
        composition.write_text(
            composition.read_text(encoding="utf-8").replace(
                "(\"OWNER\", \"MEMBER\")",
                "(\"OWNER\", \"COLLABORATOR\")",
            ),
            encoding="utf-8",
        )

        errors = validator.validate(self.root)

        self.assertTrue(
            any("owner_author_associations_exact" in error for error in errors)
        )
        self.assertIn("verification owner associations differ", errors)
        self.assertIn(
            "verification malformed owner association behavior differs", errors
        )
        self.assertIn("composition owner association allowlist differs", errors)

    def test_runner_summary_schema_mutation_fails(self) -> None:
        path = self.root / validator.RUNNER_PATH
        source = path.read_text(encoding="utf-8")
        source = source.replace("'resume_enabled'", "'removed_resume_enabled'", 1)
        path.write_text(source, encoding="utf-8")
        self.assertIn(
            "runner _SUMMARY_EVIDENCE_KEYS must equal the contract field set",
            validator.validate(self.root),
        )

    def test_manifest_and_step_order_mutations_fail(self) -> None:
        payload = self._domain()
        payload["prebuilt_deployment_inputs"]["manifest_fields_exact"].pop()
        payload["steps"][0]["order"] = 2
        self._write_domain(payload)
        errors = validator.validate(self.root)
        self.assertTrue(any("prepared-input manifest" in error for error in errors))
        self.assertTrue(any("ordered twelve-step" in error for error in errors))

    def test_verification_threshold_and_negative_test_mutations_fail(self) -> None:
        payload = self._verification()
        payload["thresholds"]["required_summary_fields"] = 8
        payload["negative_tests"][0]["id"] = "wrong-contract"
        self._write_verification(payload)
        errors = validator.validate(self.root)
        self.assertTrue(any("thresholds" in error for error in errors))
        self.assertTrue(any("negative tests" in error for error in errors))

    def test_negative_production_classification_mutation_fails(self) -> None:
        payload = self._verification()
        payload["negative_tests"][0]["assert"]["stable_error_code"] = (
            "GENERIC_ERROR"
        )
        self._write_verification(payload)
        errors = validator.validate(self.root)
        self.assertTrue(
            any(
                "negative test wrong_hash assertion stable_error_code"
                in error
                for error in errors
            )
        )

    def test_resume_code_and_required_source_marker_mutations_fail(self) -> None:
        runner = self.root / validator.RUNNER_PATH
        runner.write_text(
            runner.read_text(encoding="utf-8").replace(
                "RESUME_DISABLED_FOR_MVP", "RESUME_UNSUPPORTED"
            ),
            encoding="utf-8",
        )
        composition = self.root / validator.COMPOSITION_PATH
        composition.write_text(
            composition.read_text(encoding="utf-8").replace(
                "bicep_parameters_snapshot_sha256", "bicep_snapshot_only"
            ),
            encoding="utf-8",
        )
        errors = validator.validate(self.root)
        self.assertTrue(any("RESUME_DISABLED_FOR_MVP" in error for error in errors))
        self.assertTrue(
            any("bicep_parameters_snapshot_sha256" in error for error in errors)
        )

    def test_sealed_runtime_and_bootstrap_source_digests_are_bound(
        self,
    ) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        path.write_text(source + "\n# unbound runtime mutation\n", encoding="utf-8")
        self.assertIn(
            "Azure CLI sealed runtime source digest differs",
            validator.validate(self.root),
        )

        path.write_text(source, encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        self._write_bootstrap_source(
            path,
            source,
            bootstrap + "\n# unbound bootstrap mutation\n",
        )
        errors = validator.validate(self.root)
        self.assertIn(
            "Azure CLI sealed runtime source digest differs",
            errors,
        )
        self.assertIn(
            "Azure CLI sealed bootstrap source digest differs",
            errors,
        )

    def test_sealed_account_binding_structure_mutations_fail(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap.replace(
            '    verify_write_account_binding(azure_argv)\n'
            '    sys.argv = ["az", *azure_argv]\n'
            '    runpy.run_module("azure.cli", run_name="__main__")\n',
            '    sys.argv = ["az", *azure_argv]\n'
            '    runpy.run_module("azure.cli", run_name="__main__")\n'
            '    verify_write_account_binding(azure_argv)\n',
            1,
        ).replace(
            '("provider", "register"),',
            '("provider", "show"),',
            1,
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any("WRITE_COMMAND_PREFIXES differs" in error for error in errors)
        )
        self.assertTrue(
            any("assert once" in error for error in errors)
        )

    def test_sealed_account_binding_shadow_assignments_fail(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap + "\nWRITE_COMMAND_PREFIXES = ()\n"
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any("WRITE_COMMAND_PREFIXES differs" in error for error in errors)
        )

    def test_sealed_account_binding_shadow_functions_fail(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = (
            bootstrap
            + "\ndef verify_write_account_binding(azure_argv):\n"
            + "    return None\n"
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any(
                "functions are missing or shadowed" in error
                and "verify_write_account_binding" in error
                for error in errors
            )
        )

    def test_sealed_account_binding_assignment_rebinds_fail(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutations = (
            bootstrap + "\nWRITE_COMMAND_PREFIXES *= 0\n",
            (
                bootstrap
                + "\nverify_write_account_binding = lambda argv: None\n"
            ),
            (
                bootstrap
                + "\nfrom builtins import id as verify_write_account_binding\n"
            ),
            (
                bootstrap
                + "\nglobals()['verify_write_account_binding'] = "
                + "lambda argv: None\n"
            ),
        )
        for mutated in mutations:
            with self.subTest(mutation=mutated.rsplit("\n", 2)[-2]):
                self._write_bootstrap_source(path, source, mutated)
                errors = validator.validate(self.root)
                self.assertTrue(
                    any(
                        "WRITE_COMMAND_PREFIXES differs" in error
                        or "functions are missing or shadowed" in error
                        or "mutate its namespace dynamically" in error
                        for error in errors
                    )
                )

    def test_sealed_account_binding_outer_bootstrap_rebind_fails(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\n_BOOTSTRAP_SOURCE = 'pass'\n",
            encoding="utf-8",
        )

        self.assertIn(
            "Azure CLI sealed account-binding bootstrap is unavailable",
            validator.validate(self.root),
        )

    def test_sealed_account_binding_pattern_capture_fails(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = (
            bootstrap
            + "\nmatch 1:\n"
            + "    case verify_write_account_binding:\n"
            + "        pass\n"
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any("top-level shape differs" in error for error in errors)
        )
        self.assertTrue(
            any("functions are missing or shadowed" in error for error in errors)
        )

    def test_sealed_account_binding_outer_dynamic_rebind_fails(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        path.write_text(
            path.read_text(encoding="utf-8")
            + "\nglobals()['_BOOTSTRAP_SOURCE'] = 'pass'\n",
            encoding="utf-8",
        )

        self.assertIn(
            "Azure CLI sealed account-binding bootstrap is unavailable",
            validator.validate(self.root),
        )

    def test_sealed_account_binding_function_attribute_mutation_fails(
        self,
    ) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap.replace(
            "    verify_write_account_binding(azure_argv)\n",
            "    verify_write_account_binding.__code__ = "
            "(lambda azure_argv: None).__code__\n"
            "    verify_write_account_binding(azure_argv)\n",
            1,
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any("attribute-write targets differ" in error for error in errors)
        )

    def test_sealed_account_binding_assertion_argv_mutation_fails(
        self,
    ) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap.replace(
            '                "az", "account", "show",\n',
            '                "az", "group", "create",\n',
            1,
        )
        self._write_bootstrap_source(path, source, mutated)

        self.assertIn(
            "Azure CLI sealed account assertion argv differs",
            validator.validate(self.root),
        )

    def test_sealed_account_binding_dead_branch_fails(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap.replace(
            "    verify_write_account_binding(azure_argv)\n",
            "    if False:\n"
            "        verify_write_account_binding(azure_argv)\n",
            1,
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(any("assert once" in error for error in errors))

    def test_sealed_account_binding_dead_cleanup_branch_fails(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap.replace(
            "    wait_child_exit_without_reap(pid, deadline)\n"
            "    kill_account_process_group(pid)\n"
            "    try:\n",
            "    wait_child_exit_without_reap(pid, deadline)\n"
            "    if False:\n"
            "        kill_account_process_group(pid)\n"
            "    try:\n",
            1,
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any("parent-pinned, bounded, reaped" in error for error in errors)
        )

    def test_sealed_account_binding_killpg_mutation_fails(self) -> None:
        path = self.root / validator.AZURE_CLI_SEALED_RUNTIME_PATH
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        bootstrap = validator._literal_assignment(tree, "_BOOTSTRAP_SOURCE")
        self.assertIsInstance(bootstrap, str)
        assert isinstance(bootstrap, str)
        mutated = bootstrap.replace(
            "        os.killpg(pid, signal.SIGKILL)\n",
            "        os.kill(pid, signal.SIGKILL)\n",
            1,
        )
        self._write_bootstrap_source(path, source, mutated)

        errors = validator.validate(self.root)

        self.assertTrue(
            any("kill the process group" in error for error in errors)
        )

    def test_cloud_selection_size_contract_binding_mutation_fails(
        self,
    ) -> None:
        source = self.root / validator.AZURE_LIVE_COMMANDS_PATH
        source.write_text(
            source.read_text(encoding="utf-8").replace(
                "_MAX_CLOUD_SELECTION_BYTES = 4096",
                "_MAX_CLOUD_SELECTION_BYTES = 1024",
            ),
            encoding="utf-8",
        )

        self.assertIn(
            "Azure CLI cloud selection size must equal contract value 4096",
            validator.validate(self.root),
        )

    def test_provider_readback_policy_contract_mutation_fails(self) -> None:
        payload = self._domain()
        payload["steps"][0]["readback_policy"]["attempts"] = 4
        self._write_domain(payload)

        self.assertIn(
            "domain provider readback policy differs",
            validator.validate(self.root),
        )

    def test_provider_readback_constant_mutations_fail(self) -> None:
        composition = self.root / validator.COMPOSITION_PATH
        source = composition.read_text(encoding="utf-8")
        source = source.replace(
            "_PROVIDER_READBACK_ATTEMPTS = 5",
            "_PROVIDER_READBACK_ATTEMPTS = 4",
        ).replace(
            "_PROVIDER_READBACK_DELAY_SECONDS = 12.0",
            "_PROVIDER_READBACK_DELAY_SECONDS = 10.0",
        ).replace(
            "_PROVIDER_READBACK_MAX_SECONDS = 60.0",
            "_PROVIDER_READBACK_MAX_SECONDS = 30.0",
        )
        composition.write_text(source, encoding="utf-8")

        errors = validator.validate(self.root)

        self.assertIn(
            "composition _PROVIDER_READBACK_ATTEMPTS differs from provider contract",
            errors,
        )
        self.assertIn(
            "composition _PROVIDER_READBACK_DELAY_SECONDS differs from provider contract",
            errors,
        )
        self.assertIn(
            "composition _PROVIDER_READBACK_MAX_SECONDS differs from provider contract",
            errors,
        )

    def test_provider_runtime_policy_mutations_fail(self) -> None:
        composition = self.root / validator.COMPOSITION_PATH
        source = composition.read_text(encoding="utf-8")
        replacements = {
            '_SAFE_PROVIDER_STATES = ("Registered", "Registering", "NotRegistered")': (
                '_SAFE_PROVIDER_STATES = ("Registered", "Registering", "Unknown")'
            ),
            '_PROVIDER_REGISTER_STATES = ("NotRegistered",)': (
                '_PROVIDER_REGISTER_STATES = ("Registering",)'
            ),
            '_PROVIDER_POLL_WITHOUT_REGISTER_STATES = ("Registering",)': (
                '_PROVIDER_POLL_WITHOUT_REGISTER_STATES = ("NotRegistered",)'
            ),
            '_PROVIDER_SUCCESS_STATE = "Registered"': (
                '_PROVIDER_SUCCESS_STATE = "Registering"'
            ),
            '_PROVIDER_TIMEOUT_ERROR = "AZURE_PROVIDER_NOT_REGISTERED"': (
                '_PROVIDER_TIMEOUT_ERROR = "AZURE_CLI_TIMEOUT"'
            ),
            '_PROVIDER_AMBIGUOUS_STATE_ERROR = "AZURE_PROVIDER_STATE_AMBIGUOUS"': (
                '_PROVIDER_AMBIGUOUS_STATE_ERROR = "AZURE_CLI_COMMAND_FAILED"'
            ),
            "_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE = 1": (
                "_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE = 2"
            ),
        }
        for current, mutated in replacements.items():
            source = source.replace(current, mutated)
        composition.write_text(source, encoding="utf-8")

        errors = validator.validate(self.root)

        for name in (
            "_SAFE_PROVIDER_STATES", "_PROVIDER_REGISTER_STATES",
            "_PROVIDER_POLL_WITHOUT_REGISTER_STATES", "_PROVIDER_SUCCESS_STATE",
            "_PROVIDER_TIMEOUT_ERROR", "_PROVIDER_AMBIGUOUS_STATE_ERROR",
            "_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE",
        ):
            self.assertIn(f"composition {name} differs from provider contract", errors)

    def test_provider_runtime_policy_duplicate_assignment_fails(self) -> None:
        composition = self.root / validator.COMPOSITION_PATH
        composition.write_text(
            composition.read_text(encoding="utf-8")
            + "\n_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE = 2\n",
            encoding="utf-8",
        )

        errors = validator.validate(self.root)

        self.assertIn(
            "composition _PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE differs "
            "from provider contract",
            errors,
        )

    def test_behavioral_verification_runs_exact_modules(self) -> None:
        completed = validator.subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr=""
        )
        with patch.object(
            validator.subprocess, "run", return_value=completed
        ) as process:
            self.assertEqual(validator._run_behavioral_tests(REPO_ROOT), [])
        argv = process.call_args.args[0]
        self.assertEqual(
            argv,
            [
                validator.sys.executable,
                "-m",
                "unittest",
                *validator.BEHAVIOR_TEST_MODULES,
            ],
        )
        self.assertFalse(process.call_args.kwargs["check"])
        self.assertEqual(process.call_args.kwargs["timeout"], 180)
        environment = process.call_args.kwargs["env"]
        self.assertNotEqual(environment["HOME"], os.environ.get("HOME"))
        self.assertEqual(
            Path(environment["AZURE_CONFIG_DIR"]).parent,
            Path(environment["HOME"]),
        )

    def test_behavioral_verification_fails_closed_without_raw_output(self) -> None:
        completed = validator.subprocess.CompletedProcess(
            args=[], returncode=1, stdout="NAC_SECRET_SENTINEL_632", stderr="token"
        )
        with patch.object(validator.subprocess, "run", return_value=completed):
            errors = validator._run_behavioral_tests(REPO_ROOT)
        self.assertEqual(len(errors), 1)
        self.assertNotIn("NAC_SECRET_SENTINEL_632", errors[0])
        self.assertNotIn("token", errors[0])

    def test_strict_quality_gate_registers_validator(self) -> None:
        from scripts import quality_gate

        checks = {
            check_id: command
            for check_id, _title, command in quality_gate.build_checks("strict")
        }
        self.assertEqual(
            checks["m365_azure_bff_live_activation"],
            [
                validator.sys.executable,
                "scripts/validate_m365_azure_bff_live_activation.py",
            ],
        )

    def _copy_contracts(self) -> None:
        for relative in (validator.DOMAIN_PATH, validator.VERIFICATION_PATH):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / relative, destination)

    def _write_valid_sources(self) -> None:
        runner = self.root / validator.RUNNER_PATH
        runner.parent.mkdir(parents=True, exist_ok=True)
        runner.write_text(
            "\n".join(
                (
                    f"_EVIDENCE_KEYS = {set(validator.TOP_LEVEL_FIELDS)!r}",
                    f"_STEP_EVIDENCE_KEYS = {set(validator.STEP_FIELDS)!r}",
                    f"_SUMMARY_EVIDENCE_KEYS = {set(validator.SUMMARY_FIELDS)!r}",
                    f"_SUMMARY_COUNT_KEYS = {set(validator.SUMMARY_COUNT_FIELDS)!r}",
                    (
                        "_HOST_STATE_RELATIVE_PATH = "
                        f"{validator.HOST_STATE_RELATIVE_PATH!r}"
                    ),
                    (
                        "_LEGACY_HOST_STATE_RELATIVE_PATH = "
                        f"{validator.LEGACY_HOST_STATE_RELATIVE_PATH!r}"
                    ),
                    'RESUME_ERROR = "RESUME_DISABLED_FOR_MVP"',
                    'TOOLCHAIN_ERROR = "TOOLCHAIN_ATTESTATION_INVALID"',
                    'RECOVERY_CALL = "reconcile_azure_bff_live_activation_lock"',
                    'RECOVERY_RESULT = "FINALIZATION_LOCK_RECONCILED"',
                    'LEGACY_LOCK = "LEGACY_ACTIVATION_LOCK_HELD"',
                    'LEGACY_HOST_ROOT = "_LEGACY_HOST_LOCK_ROOT"',
                    'LEGACY_HOST_LOCK = "LEGACY_HOST_ACTIVATION_LOCK_HELD"',
                    'ARM_AMBIGUOUS = "AZURE_DEPLOYMENT_STATE_AMBIGUOUS"',
                    'QUARANTINE = "preserve_quarantine"',
                    'LEGACY_HASH = "legacy_target_binding_sha256"',
                    'HOST_RESOLUTION = "pwd.getpwuid(os.geteuid()).pw_dir"',
                )
            )
            + "\n",
            encoding="utf-8",
        )
        ast.parse(runner.read_text(encoding="utf-8"))
        for relative, markers in validator.SOURCE_MARKERS.items():
            if relative == validator.RUNNER_PATH:
                continue
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative == validator.COMPOSITION_PATH:
                source = (
                    "_APPROVED_OWNER_ASSOCIATIONS = (\"OWNER\", \"MEMBER\")\n"
                    "_SAFE_PROVIDER_STATES = (\"Registered\", \"Registering\", \"NotRegistered\")\n"
                    "_PROVIDER_REGISTER_STATES = (\"NotRegistered\",)\n"
                    "_PROVIDER_POLL_WITHOUT_REGISTER_STATES = (\"Registering\",)\n"
                    "_PROVIDER_SUCCESS_STATE = \"Registered\"\n"
                    "_PROVIDER_TIMEOUT_ERROR = \"AZURE_PROVIDER_NOT_REGISTERED\"\n"
                    "_PROVIDER_AMBIGUOUS_STATE_ERROR = \"AZURE_PROVIDER_STATE_AMBIGUOUS\"\n"
                    "_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE = 1\n"
                    "_PROVIDER_READBACK_ATTEMPTS = 5\n"
                    "_PROVIDER_READBACK_DELAY_SECONDS = 12.0\n"
                    "_PROVIDER_READBACK_MAX_SECONDS = 60.0\n"
                    "_DEPLOYMENT_RECONCILIATION_ATTEMPTS = 5\n"
                    "_DEPLOYMENT_RECONCILIATION_DELAY_SECONDS = 2.0\n"
                    "_APPROVED_FAILED_BASELINE_TEMPLATE_HASHES = "
                    "(\"14963684813925800234\",)\n"
                    + "\n".join(f"# {marker}" for marker in markers)
                    + "\n"
                )
            elif relative == validator.AZURE_CLI_SEALED_RUNTIME_PATH:
                source = (REPO_ROOT / relative).read_text(encoding="utf-8")
            elif relative == validator.AZURE_LIVE_COMMANDS_PATH:
                source = (
                    "_MAX_CLOUD_SELECTION_BYTES = 4096\n"
                    + "\n".join(f"# {marker}" for marker in markers)
                    + "\n"
                )
            else:
                source = "\n".join(markers) + "\n"
            path.write_text(source, encoding="utf-8")
        marker_text = "# executable behavioral fixture\n"
        for relative in validator.TEST_PATHS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                path.write_text(
                    path.read_text(encoding="utf-8") + marker_text,
                    encoding="utf-8",
                )
            else:
                path.write_text(marker_text, encoding="utf-8")

    def _domain(self) -> dict:
        return json.loads(
            (self.root / validator.DOMAIN_PATH).read_text(encoding="utf-8")
        )

    def _write_domain(self, payload: dict) -> None:
        (self.root / validator.DOMAIN_PATH).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )

    def _verification(self) -> dict:
        return yaml.safe_load(
            (self.root / validator.VERIFICATION_PATH).read_text(encoding="utf-8")
        )

    def _write_verification(self, payload: dict) -> None:
        (self.root / validator.VERIFICATION_PATH).write_text(
            yaml.safe_dump(payload, sort_keys=False), encoding="utf-8"
        )


if __name__ == "__main__":
    unittest.main()
