from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import nac_bff.azure_live_commands as azure_live_commands
from nac_bff.azure_live_commands import (
    ALLOWED_COMMAND_PREFIXES,
    AZURE_CLI_CANDIDATES,
    AZURE_CLI_SHA256_ENV,
    EXPECTED_SUBSCRIPTION_ID,
    EXPECTED_TENANT_ID,
    AzureCliAdapter,
    build_azure_cli_env,
    calculate_azure_cli_toolchain_sha256,
    check_azure_cli_readiness,
    resolve_azure_cli_binary,
    run_azure_cli,
)


class AzureLiveCommandTests(unittest.TestCase):
    def test_allowlist_contains_only_required_command_families(self) -> None:
        self.assertEqual(
            ALLOWED_COMMAND_PREFIXES,
            (
                ("account", "show"),
                ("provider", "show"),
                ("provider", "register"),
                ("group", "exists"),
                ("group", "show"),
                ("group", "create"),
                ("deployment", "group", "create"),
                ("deployment", "group", "show"),
                ("resource", "list"),
                ("functionapp", "deployment", "source", "config-zip"),
            ),
        )

    def test_blocked_argv_never_reaches_subprocess(self) -> None:
        blocked = (
            ["group", "delete", "--name", "rg-nac-bff-test"],
            ["account", "list"],
            ["az", "account", "show"],
            ["account", "show", "--output", "tsv"],
            ["account", "show", "--debug"],
            ["group", "show", "--subscription=wrong-subscription"],
            ["group", "show", "--name", "foreign-rg"],
            ["group", "show", "--name", "rg-nac-bff-test", "--query", "id"],
            ["group", "show", "--name", "rg-nac-bff-test", "--name", "rg-nac-bff-test"],
            ["group", "show", "--name"],
            ["group", "show", "rg-nac-bff-test"],
            ["provider", "show", "--namespace", "Microsoft.Authorization"],
            ["provider", "register", "--namespace", "Microsoft.Web"],
            ["resource", "list", "--resource-group", "foreign-rg"],
            [
                "deployment", "group", "create",
                "--name", "nac-bff-012345abcdef",
                "--resource-group", "rg-nac-bff-test",
                "--template-file", "/tmp/prepared/main.bicep",
                "--parameters", "location=germanywestcentral",
                "--mode", "Incremental",
            ],
            [
                "deployment", "group", "create",
                "--name", "nac-bff-012345abcdef",
                "--resource-group", "rg-nac-bff-test",
                "--template-file", "/tmp/prepared/main.bicep",
                "--parameters", "@relative/main.parameters.json",
                "--mode", "Incremental",
            ],
            [
                "functionapp", "deployment", "source", "config-zip",
                "--resource-group", "rg-nac-bff-test",
                "--name", "foreign-function",
                "--src", "/tmp/app.zip",
                "--build-remote", "true",
            ],
            [],
            "account show",
        )
        with patch("nac_bff.azure_live_commands.subprocess.run") as process:
            for argv in blocked:
                result = run_azure_cli(argv, binary="/does/not/matter")
                self.assertFalse(result["ok"])
                self.assertIn(
                    result["code"],
                    {"AZURE_CLI_ARGV_INVALID", "AZURE_CLI_COMMAND_BLOCKED"},
                )
        process.assert_not_called()

    def test_exact_command_schemas_accept_only_bounded_shapes(self) -> None:
        valid = (
            ["account", "show"],
            ["provider", "show", "--namespace", "Microsoft.Web"],
            [
                "provider",
                "register",
                "--namespace",
                "Microsoft.Storage",
                "--wait",
            ],
            ["group", "exists", "--name", "rg-nac-bff-test"],
            ["group", "show", "--name", "rg-nac-bff-test"],
            [
                "group",
                "create",
                "--name",
                "rg-nac-bff-test",
                "--location",
                "germanywestcentral",
                "--tags",
                "workload=nac-bff",
                "environment=test",
                "dataClassification=no-production-data",
            ],
            ["resource", "list", "--resource-group", "rg-nac-bff-test"],
            [
                "deployment",
                "group",
                "show",
                "--name",
                "nac-bff-012345abcdef",
                "--resource-group",
                "rg-nac-bff-test",
            ],
            [
                "deployment",
                "group",
                "create",
                "--name",
                "nac-bff-012345abcdef",
                "--resource-group",
                "rg-nac-bff-test",
                "--template-file",
                "/tmp/prepared/infra/main.bicep",
                "--parameters",
                "@/tmp/prepared/main.parameters.json",
                "--mode",
                "Incremental",
            ],
            [
                "functionapp",
                "deployment",
                "source",
                "config-zip",
                "--resource-group",
                "rg-nac-bff-test",
                "--name",
                "func-nac-bff-test-funktion8",
                "--src",
                "/tmp/prepared/function/nac-bff.zip",
                "--build-remote",
                "true",
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="{}", stderr=""
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ) as process:
                for argv in valid:
                    with self.subTest(argv=argv):
                        result = run_azure_cli(
                            argv,
                            binary=binary,
                            expected_binary_sha256=digest,
                        )
                        self.assertTrue(result["ok"])
        self.assertEqual(process.call_count, len(valid))
        for call in process.call_args_list:
            argv = call.args[0]
            self.assertEqual(argv[-3:], ["--output", "json", "--only-show-errors"])
            if argv[1:3] != ["account", "show"]:
                subscription_index = argv.index("--subscription")
                self.assertEqual(argv[subscription_index + 1], EXPECTED_SUBSCRIPTION_ID)

    def test_process_boundary_is_argv_only_shell_false_and_env_filtered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps({"name": "rg-nac-bff-test"}),
                stderr="raw stderr must not escape",
            )
            source_env = {
                "HOME": "/tmp/home",
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "AZURE_CONFIG_DIR": "/tmp/azure-config",
                "AZURE_CLIENT_SECRET": "must-not-reach-child",
                "ACCESS_TOKEN": "must-not-reach-child",
            }
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ) as process:
                result = run_azure_cli(
                    ["group", "show", "--name", "rg-nac-bff-test"],
                    binary=binary,
                    expected_binary_sha256=digest,
                    environ=source_env,
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["data"], {"name": "rg-nac-bff-test"})
        process_argv = process.call_args.args[0]
        process_kwargs = process.call_args.kwargs
        self.assertEqual(process_argv[0], str(binary.resolve()))
        self.assertEqual(
            process_argv[1:5],
            ["group", "show", "--name", "rg-nac-bff-test"],
        )
        self.assertIs(process_kwargs["shell"], False)
        self.assertIs(process_kwargs["check"], False)
        self.assertEqual(process_kwargs["stdin"], subprocess.DEVNULL)
        self.assertNotIn("AZURE_CLIENT_SECRET", process_kwargs["env"])
        self.assertNotIn("ACCESS_TOKEN", process_kwargs["env"])
        self.assertEqual(
            process_kwargs["env"],
            {
                "HOME": "/tmp/home",
                "PATH": "/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "AZURE_CONFIG_DIR": "/tmp/azure-config",
                "AZURE_CORE_COLLECT_TELEMETRY": "0",
                "AZURE_CORE_NO_COLOR": "true",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
        )

    def test_failures_expose_stable_codes_without_raw_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            secret_stdout = "raw-stdout-secret"
            secret_stderr = "raw-stderr-secret"
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=17,
                stdout=secret_stdout,
                stderr=secret_stderr,
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ):
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=digest,
                )

        serialized = json.dumps(result, sort_keys=True)
        self.assertEqual(result["code"], "AZURE_CLI_COMMAND_FAILED")
        self.assertEqual(result["returncode"], 17)
        self.assertNotIn("stdout", result)
        self.assertNotIn("stderr", result)
        self.assertNotIn(secret_stdout, serialized)
        self.assertNotIn(secret_stderr, serialized)

    def test_invalid_json_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="not-json-with-sensitive-content",
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ):
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=digest,
                )

        self.assertEqual(result["code"], "AZURE_CLI_OUTPUT_INVALID")
        self.assertNotIn("not-json", json.dumps(result))


class AzureLiveReadinessTests(unittest.TestCase):
    def test_resolves_only_trusted_absolute_binary_and_lists_tmp_candidate_first(self) -> None:
        self.assertEqual(
            AZURE_CLI_CANDIDATES[0],
            Path("/tmp/nac-azure-cli-venv/bin/az"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            self.assertIsNone(resolve_azure_cli_binary(binary))
            self.assertEqual(
                resolve_azure_cli_binary(binary, expected_sha256=digest),
                binary.resolve(),
            )
            self.assertIsNone(resolve_azure_cli_binary(Path(tmp) / "missing-az"))
            self.assertIsNone(resolve_azure_cli_binary("/bin/sh"))
            self.assertIsNone(resolve_azure_cli_binary(Path("az")))

    def test_rejects_symlink_and_world_writable_binary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = _fake_binary(root)
            digest = _binary_sha256(binary)
            symlink = root / "link" / "az"
            symlink.parent.mkdir()
            symlink.symlink_to(binary)
            self.assertIsNone(
                resolve_azure_cli_binary(symlink, expected_sha256=digest)
            )

            binary.chmod(0o707)
            self.assertIsNone(
                resolve_azure_cli_binary(binary, expected_sha256=digest)
            )

    def test_toolchain_attestation_digest_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            self.assertNotEqual(
                digest,
                hashlib.sha256(binary.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                resolve_azure_cli_binary(binary, expected_sha256=digest),
                binary,
            )
            self.assertEqual(
                resolve_azure_cli_binary(binary, expected_sha256=digest.upper()),
                binary,
            )
            self.assertIsNone(
                resolve_azure_cli_binary(binary, expected_sha256="0" * 64)
            )
            self.assertIsNone(
                resolve_azure_cli_binary(binary, expected_sha256="not-a-digest")
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run"
            ) as process:
                invalid_type = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=123,  # type: ignore[arg-type]
                )
            self.assertEqual(
                invalid_type["code"],
                "AZURE_CLI_BINARY_ATTESTATION_INVALID",
            )
            process.assert_not_called()

    def test_non_root_binary_returns_stable_blocked_codes_without_details(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            with patch("nac_bff.azure_live_commands.subprocess.run") as process:
                missing = run_azure_cli(["account", "show"], binary=binary)
                mismatch = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256="0" * 64,
                )
        process.assert_not_called()
        self.assertEqual(missing["status"], "BLOCKED")
        self.assertEqual(
            missing["code"],
            "AZURE_CLI_BINARY_ATTESTATION_REQUIRED",
        )
        self.assertEqual(mismatch["status"], "BLOCKED")
        self.assertEqual(
            mismatch["code"],
            "AZURE_CLI_BINARY_ATTESTATION_MISMATCH",
        )
        serialized = json.dumps({"missing": missing, "mismatch": mismatch})
        self.assertNotIn(str(binary), serialized)
        self.assertNotIn("0" * 64, serialized)

    def test_unchanged_wrapper_with_mutated_package_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            expected = _binary_sha256(binary)
            wrapper_before = binary.read_bytes()
            _package_entrypoint(binary).write_text(
                "raise RuntimeError('mutated')\n",
                encoding="utf-8",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run"
            ) as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=expected,
                )
            self.assertEqual(binary.read_bytes(), wrapper_before)

        self.assertEqual(
            result["code"],
            "AZURE_CLI_BINARY_ATTESTATION_MISMATCH",
        )
        process.assert_not_called()

    def test_interpreter_target_swap_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            expected = _binary_sha256(binary)
            interpreter = binary.parent / "python3"
            interpreter.unlink()
            interpreter.symlink_to("/usr/bin/false")
            with patch(
                "nac_bff.azure_live_commands.subprocess.run"
            ) as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=expected,
                )

        self.assertEqual(
            result["code"],
            "AZURE_CLI_BINARY_ATTESTATION_MISMATCH",
        )
        process.assert_not_called()

    def test_toolchain_is_rechecked_immediately_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            expected = _binary_sha256(binary)
            package = _package_entrypoint(binary)
            original = azure_live_commands._executable_path
            calls = 0

            def mutate_after_preflight(
                candidate: Path,
                *,
                expected_sha256: str | None = None,
            ) -> tuple[Path | None, str]:
                nonlocal calls
                result = original(
                    candidate,
                    expected_sha256=expected_sha256,
                )
                calls += 1
                if calls == 1:
                    package.write_text(
                        "raise RuntimeError('toctou')\n",
                        encoding="utf-8",
                    )
                return result

            with (
                patch(
                    "nac_bff.azure_live_commands._executable_path",
                    side_effect=mutate_after_preflight,
                ),
                patch(
                    "nac_bff.azure_live_commands.subprocess.run"
                ) as process,
            ):
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=expected,
                )

        self.assertEqual(calls, 2)
        self.assertEqual(
            result["code"],
            "AZURE_CLI_BINARY_ATTESTATION_MISMATCH",
        )
        process.assert_not_called()

    def test_package_tree_symlink_is_untrusted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            package_root = _package_entrypoint(binary).parents[2]
            (package_root / "injected.py").symlink_to("/etc/hosts")

            self.assertIsNone(
                calculate_azure_cli_toolchain_sha256(binary)
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run"
            ) as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256="0" * 64,
                )

        self.assertEqual(result["code"], "AZURE_CLI_BINARY_UNTRUSTED")
        process.assert_not_called()

    def test_symlinked_package_path_component_is_untrusted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            python_root = _package_entrypoint(binary).parents[3]
            relocated = binary.parent.parent / "relocated-python"
            python_root.rename(relocated)
            python_root.symlink_to("../relocated-python")

            self.assertIsNone(
                calculate_azure_cli_toolchain_sha256(binary)
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run"
            ) as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256="0" * 64,
                )

        self.assertEqual(result["code"], "AZURE_CLI_BINARY_UNTRUSTED")
        process.assert_not_called()

    def test_runtime_sha_boundary_is_used_but_not_forwarded_to_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[], returncode=0, stdout="{}", stderr=""
            )
            environ = {
                "HOME": "/tmp/home",
                AZURE_CLI_SHA256_ENV: digest,
            }
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ) as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    environ=environ,
                )
        self.assertTrue(result["ok"])
        self.assertNotIn(AZURE_CLI_SHA256_ENV, process.call_args.kwargs["env"])

    def test_path_lookup_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            with patch(
                "nac_bff.azure_live_commands.AZURE_CLI_CANDIDATES", ()
            ):
                self.assertIsNone(
                    resolve_azure_cli_binary(environ={"PATH": str(binary.parent)})
                )

    def test_minimal_env_does_not_copy_credential_variables(self) -> None:
        env = build_azure_cli_env(
            {
                "HOME": "/tmp/home",
                "PATH": "/bin",
                "TMPDIR": "/tmp",
                "AZURE_CLIENT_ID": "client-id",
                "AZURE_CLIENT_SECRET": "secret",
                "AZURE_TENANT_ID": "tenant",
            }
        )

        self.assertEqual(env["HOME"], "/tmp/home")
        self.assertEqual(env["TMPDIR"], "/tmp")
        self.assertNotIn("AZURE_CLIENT_ID", env)
        self.assertNotIn("AZURE_CLIENT_SECRET", env)
        self.assertNotIn("AZURE_TENANT_ID", env)

    def test_exact_account_is_ready_without_network_or_real_azure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "id": EXPECTED_SUBSCRIPTION_ID,
                        "tenantId": EXPECTED_TENANT_ID,
                        "state": "Enabled",
                        "user": {"name": "must-not-be-evidence"},
                    }
                ),
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ) as process:
                readiness = check_azure_cli_readiness(
                    binary=binary,
                    expected_binary_sha256=digest,
                )

        self.assertEqual(readiness["status"], "READY")
        self.assertEqual(readiness["code"], "AZURE_CLI_READY")
        self.assertTrue(readiness["ready"])
        self.assertEqual(
            readiness["bindings"],
            {
                "tenant_id": EXPECTED_TENANT_ID,
                "subscription_id": EXPECTED_SUBSCRIPTION_ID,
            },
        )
        self.assertNotIn("user", json.dumps(readiness))
        self.assertEqual(process.call_count, 1)

    def test_wrong_tenant_is_not_ready(self) -> None:
        readiness = _readiness_for_account(
            tenant_id="00000000-0000-0000-0000-000000000000",
            subscription_id=EXPECTED_SUBSCRIPTION_ID,
        )

        self.assertEqual(readiness["status"], "NOT_READY")
        self.assertEqual(readiness["code"], "AZURE_CLI_TENANT_MISMATCH")
        self.assertFalse(readiness["ready"])
        self.assertNotIn("00000000", json.dumps(readiness))

    def test_wrong_subscription_is_not_ready(self) -> None:
        readiness = _readiness_for_account(
            tenant_id=EXPECTED_TENANT_ID,
            subscription_id="00000000-0000-0000-0000-000000000000",
        )

        self.assertEqual(readiness["status"], "NOT_READY")
        self.assertEqual(
            readiness["code"],
            "AZURE_CLI_SUBSCRIPTION_MISMATCH",
        )
        self.assertFalse(readiness["ready"])
        self.assertNotIn("00000000", json.dumps(readiness))

    def test_missing_binary_is_not_ready_without_subprocess(self) -> None:
        with patch("nac_bff.azure_live_commands.subprocess.run") as process:
            readiness = check_azure_cli_readiness(binary="/missing/azure/az")

        self.assertEqual(readiness["code"], "AZURE_CLI_BINARY_NOT_FOUND")
        self.assertEqual(readiness["status"], "NOT_READY")
        process.assert_not_called()

    def test_adapter_wraps_same_bounded_contract(self) -> None:
        adapter = AzureCliAdapter(
            binary="/missing/azure/az",
            environ={"AZURE_CLIENT_SECRET": "excluded"},
            timeout_seconds=9,
        )

        result = adapter.run(["group", "delete"])
        readiness = adapter.check_readiness()

        self.assertEqual(result["code"], "AZURE_CLI_COMMAND_BLOCKED")
        self.assertEqual(readiness["code"], "AZURE_CLI_BINARY_NOT_FOUND")


def _fake_binary(root: Path) -> Path:
    venv = root / "azure-cli-venv"
    binary_directory = venv / "bin"
    package = (
        venv
        / "lib"
        / "python3.12"
        / "site-packages"
        / "azure"
        / "cli"
    )
    binary_directory.mkdir(parents=True)
    package.mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text(
        "home = /usr/bin\ninclude-system-site-packages = false\n",
        encoding="utf-8",
    )
    interpreter = binary_directory / "python3"
    interpreter.symlink_to("/usr/bin/python3")
    binary = binary_directory / "az"
    binary.write_text(
        f"#!{interpreter}\n"
        "import os, sys\n"
        "os.execl(sys.executable, sys.executable, '-m', 'azure.cli', *sys.argv[1:])\n",
        encoding="utf-8",
    )
    binary.chmod(0o700)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(
        "def main():\n    return 0\n",
        encoding="utf-8",
    )
    (package / "commands.py").write_text(
        "COMMANDS = ('account', 'group')\n",
        encoding="utf-8",
    )
    return binary


def _package_entrypoint(binary: Path) -> Path:
    venv = binary.parent.parent
    return (
        venv
        / "lib"
        / "python3.12"
        / "site-packages"
        / "azure"
        / "cli"
        / "__main__.py"
    )


def _binary_sha256(binary: Path) -> str:
    digest = calculate_azure_cli_toolchain_sha256(binary)
    if digest is None:
        raise AssertionError("fake Azure CLI toolchain is not attestable")
    return digest


def _readiness_for_account(
    *,
    tenant_id: str,
    subscription_id: str,
) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        binary = _fake_binary(Path(tmp))
        digest = _binary_sha256(binary)
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps(
                {"id": subscription_id, "tenantId": tenant_id}
            ),
            stderr="",
        )
        with patch(
            "nac_bff.azure_live_commands.subprocess.run",
            return_value=completed,
        ):
            return check_azure_cli_readiness(
                binary=binary,
                expected_binary_sha256=digest,
            )


if __name__ == "__main__":
    unittest.main()
