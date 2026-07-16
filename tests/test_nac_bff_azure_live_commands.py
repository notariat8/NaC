from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

import nac_bff.azure_cli_sealed_runtime as azure_cli_sealed_runtime
import nac_bff.azure_live_commands as azure_live_commands
from nac_bff.azure_live_commands import (
    ALLOWED_COMMAND_PREFIXES,
    AZURE_CLI_CANDIDATES,
    AZURE_CLI_SHA256_ENV,
    EXPECTED_CLOUD_NAME,
    EXPECTED_SUBSCRIPTION_ID,
    EXPECTED_TENANT_ID,
    AzureCliAdapter,
    build_azure_cli_env,
    calculate_azure_cli_toolchain_sha256,
    check_azure_cli_readiness,
    resolve_azure_cli_binary,
    run_azure_cli,
)


class _IsolatedAzureConfigTestCase(unittest.TestCase):
    def setUp(self) -> None:
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="nac-azure-cli-test-")
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        environment = patch.dict(
            os.environ,
            {
                "HOME": str(home),
                "AZURE_CONFIG_DIR": str(home / ".azure"),
            },
        )
        environment.start()
        self.addCleanup(environment.stop)


class AzureLiveCommandTests(_IsolatedAzureConfigTestCase):
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

    def test_sealed_bootstrap_disables_all_azure_cli_extension_sources(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        for binding in (
            'AZURE_EXTENSION_DIR',
            'AZURE_EXTENSION_SYS_DIR',
            'AZURE_EXTENSION_DEV_SOURCES',
            'AZURE_EXTENSION_USE_DYNAMIC_INSTALL',
        ):
            self.assertIn(binding, source)
        self.assertIn('.nac-empty-extensions', source)
        self.assertIn('os.environ["AZURE_EXTENSION_USE_DYNAMIC_INSTALL"] = "no"', source)
        self.assertIn("copy_private_azure_config", source)
        self.assertIn("validate_private_azure_profile", source)
        self.assertIn('"environmentName") != "AzureCloud"', source)
        self.assertEqual(source.count('name == "clouds.config"'), 2)
        self.assertIn("expected_cloud_selection_sha256", source)
        self.assertIn("MAX_CLOUD_SELECTION_BYTES = 4096", source)
        self.assertIn("cloud_selection_seen = True", source)
        self.assertIn(
            'if (destination / "clouds.config").exists():',
            source,
        )
        self.assertIn('os.environ["AZURE_CONFIG_DIR"] = str(private_config)', source)

    def test_sealed_bootstrap_uses_parent_written_user_namespace_maps(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE

        self.assertIn("pid = os.fork()", source)
        self.assertIn("write_id_maps(pid, uid, gid)", source)
        self.assertIn("package_source = stage_verified_package(source_root, manifest)", source)
        self.assertIn("destination, private_config, libc = isolate(package_source)", source)
        self.assertIn('os.read(ready_read, 1) == b"R"', source)
        self.assertIn('os.read(continue_read, 1) != b"G"', source)
        self.assertNotIn("/proc/self/uid_map", source)
        self.assertNotIn("/proc/self/gid_map", source)

    def test_sealed_bootstrap_writes_exact_single_id_maps(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        write_id_maps = namespace["write_id_maps"]

        with tempfile.TemporaryDirectory() as tmp:
            process_root = Path(tmp) / "123"
            process_root.mkdir()
            for name in ("setgroups", "uid_map", "gid_map"):
                (process_root / name).touch()

            self.assertTrue(write_id_maps(123, 1000, 1001, Path(tmp)))
            self.assertEqual((process_root / "setgroups").read_bytes(), b"deny")
            self.assertEqual((process_root / "uid_map").read_bytes(), b"0 1000 1\n")
            self.assertEqual((process_root / "gid_map").read_bytes(), b"0 1001 1\n")

    def test_sealed_bootstrap_fails_closed_when_id_map_write_fails(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        write_id_maps = namespace["write_id_maps"]

        with tempfile.TemporaryDirectory() as tmp:
            process_root = Path(tmp) / "123"
            process_root.mkdir()
            (process_root / "setgroups").touch()
            (process_root / "uid_map").touch()

            self.assertFalse(write_id_maps(123, 1000, 1001, Path(tmp)))

    def test_sealed_bootstrap_stages_verified_package_before_isolation(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        stage_verified_package = namespace["stage_verified_package"]
        copy_staged_verified = namespace["copy_staged_verified"]
        cleanup_staging = namespace["cleanup_staging"]

        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            source_root.mkdir()
            nested = source_root / "azure" / "module"
            nested.mkdir(parents=True)
            payload = nested / "module.py"
            payload.write_text("VALUE = 1\n", encoding="utf-8")
            metadata = payload.stat()
            directory_records = []
            for directory in (source_root / "azure", nested):
                directory_metadata = directory.stat()
                directory_records.append(
                    {
                        "path": directory.relative_to(source_root).as_posix(),
                        "mode": directory_metadata.st_mode & 0o7777,
                    }
                )
            manifest = {
                "directories": directory_records,
                "files": [
                    {
                        "path": "azure/module/module.py",
                        "uid": metadata.st_uid,
                        "mode": metadata.st_mode & 0o7777,
                        "size": metadata.st_size,
                        "sha256": hashlib.sha256(payload.read_bytes()).hexdigest(),
                    }
                ],
            }

            staging = stage_verified_package(source_root, manifest)

            self.assertEqual(
                (staging / "azure" / "module" / "module.py").read_bytes(),
                payload.read_bytes(),
            )
            self.assertEqual(staging.stat().st_mode & 0o777, 0o700)
            destination = Path(tmp) / "destination.py"
            copy_staged_verified(
                staging / "azure" / "module" / "module.py",
                destination,
                manifest["files"][0],
            )
            self.assertEqual(destination.read_bytes(), payload.read_bytes())
            self.assertEqual(
                destination.stat().st_mode & 0o777,
                (metadata.st_mode & 0o777) & ~0o222,
            )
            self.assertTrue(cleanup_staging(staging))
            self.assertFalse(staging.exists())

    def test_sealed_bootstrap_child_dies_when_supervisor_is_killed(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        prefix = source.rsplit("\nmain()\n", 1)[0]
        helper = (
            "import ctypes, os, time\n"
            f"namespace = {{}}\nexec({prefix!r}, namespace)\n"
            "pid = os.fork()\n"
            "if pid == 0:\n"
            "    parent_pid = os.getppid()\n"
            "    libc = ctypes.CDLL(None, use_errno=True)\n"
            "    if not namespace['arm_parent_death_signal'](libc, parent_pid):\n"
            "        os._exit(90)\n"
            "    print(os.getpid(), flush=True)\n"
            "    time.sleep(30)\n"
            "    os._exit(91)\n"
            "time.sleep(30)\n"
        )
        supervisor = subprocess.Popen(
            [os.sys.executable, "-c", helper],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        child_pid = None
        try:
            assert supervisor.stdout is not None
            child_pid = int(supervisor.stdout.readline().strip())
            os.kill(supervisor.pid, signal.SIGKILL)
            supervisor.wait(timeout=5)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                status = Path(f"/proc/{child_pid}/stat")
                if not status.exists():
                    break
                fields = status.read_text(encoding="ascii").split()
                if len(fields) >= 3 and fields[2] == "Z":
                    break
                time.sleep(0.05)
            else:
                self.fail("mapped child survived supervisor SIGKILL")
        finally:
            if supervisor.poll() is None:
                supervisor.kill()
                supervisor.wait(timeout=5)
            if supervisor.stdout is not None:
                supervisor.stdout.close()
            if supervisor.stderr is not None:
                supervisor.stderr.close()
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_sealed_bootstrap_accepts_bom_prefixed_bound_azure_profile(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        validate_private_azure_profile = namespace[
            "validate_private_azure_profile"
        ]

        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "azureProfile.json"
            profile.write_text(
                json.dumps(
                    {
                        "subscriptions": [
                            {
                                "id": EXPECTED_SUBSCRIPTION_ID,
                                "tenantId": EXPECTED_TENANT_ID,
                                "environmentName": EXPECTED_CLOUD_NAME,
                                "isDefault": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8-sig",
            )

            validate_private_azure_profile(Path(tmp))

    def test_sealed_bootstrap_requires_dedicated_profile_when_restricted(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        validate_host_userns_profile = namespace["validate_host_userns_profile"]

        with tempfile.TemporaryDirectory() as tmp:
            restriction = Path(tmp) / "restriction"
            label = Path(tmp) / "label"
            restriction.write_text("1\n", encoding="ascii")
            label.write_text(
                "nac-azure-cli-sealed-runtime (unconfined)\n",
                encoding="ascii",
            )

            validate_host_userns_profile(restriction, label)
            label.write_text("unprivileged_userns (enforce)\n", encoding="ascii")
            with self.assertRaisesRegex(SystemExit, "87"):
                validate_host_userns_profile(restriction, label)

    def test_sealed_bootstrap_allows_host_without_apparmor_restriction(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        validate_host_userns_profile = namespace["validate_host_userns_profile"]

        with tempfile.TemporaryDirectory() as tmp:
            restriction = Path(tmp) / "restriction"
            restriction.write_text("0\n", encoding="ascii")

            validate_host_userns_profile(restriction, Path(tmp) / "missing-label")

    def test_sealed_bootstrap_omits_default_cloud_selection(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        copy_private_azure_config = namespace["copy_private_azure_config"]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_config = root / "source"
            destination = root / "destination"
            source_config.mkdir(mode=0o700)
            (source_config / "azureProfile.json").write_text(
                '{"subscriptions": []}',
                encoding="utf-8",
            )
            (source_config / "clouds.config").write_text(
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n",
                encoding="utf-8",
            )

            expected_digest = hashlib.sha256(
                (source_config / "clouds.config").read_bytes()
            ).hexdigest()
            copy_private_azure_config(
                source_config,
                destination,
                expected_digest,
            )

            self.assertTrue((destination / "azureProfile.json").is_file())
            self.assertFalse((destination / "clouds.config").exists())

    def test_sealed_bootstrap_rejects_cloud_selection_directory(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        copy_private_azure_config = namespace["copy_private_azure_config"]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_config = root / "source"
            destination = root / "destination"
            source_config.mkdir(mode=0o700)
            (source_config / "clouds.config").mkdir()

            with self.assertRaisesRegex(SystemExit, "86"):
                copy_private_azure_config(source_config, destination, None)

    def test_sealed_bootstrap_rejects_cloud_selection_digest_drift(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        copy_private_azure_config = namespace["copy_private_azure_config"]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_config = root / "source"
            destination = root / "destination"
            source_config.mkdir(mode=0o700)
            selection = source_config / "clouds.config"
            selection.write_text(
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n",
                encoding="utf-8",
            )
            expected_digest = hashlib.sha256(selection.read_bytes()).hexdigest()
            selection.write_text(
                "[CustomCloud]\nsubscription = attacker\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "86"):
                copy_private_azure_config(
                    source_config,
                    destination,
                    expected_digest,
                )

    def test_sealed_bootstrap_rejects_oversized_selection_drift(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        copy_private_azure_config = namespace["copy_private_azure_config"]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_config = root / "source"
            destination = root / "destination"
            source_config.mkdir(mode=0o700)
            selection = source_config / "clouds.config"
            expected = (
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n"
            ).encode("utf-8")
            expected_digest = hashlib.sha256(expected).hexdigest()
            selection.write_bytes(b"x" * 4097)

            with self.assertRaisesRegex(SystemExit, "86"):
                copy_private_azure_config(
                    source_config,
                    destination,
                    expected_digest,
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
                "/tmp/prepared/infra/main.json",
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
            self.assertRegex(argv[0], r"\A/proc/self/fd/[0-9]+\Z")
            self.assertEqual(argv[1:3], ["-I", "-B"])
            self.assertRegex(argv[3], r"\A/proc/self/fd/[0-9]+\Z")
            self.assertRegex(argv[4], r"\A/proc/self/fd/[0-9]+\Z")
            azure_argv = argv[5:]
            self.assertEqual(azure_argv[-3:], ["--output", "json", "--only-show-errors"])
            if azure_argv[:2] != ["account", "show"]:
                subscription_index = azure_argv.index("--subscription")
                self.assertEqual(
                    azure_argv[subscription_index + 1],
                    EXPECTED_SUBSCRIPTION_ID,
                )
            self.assertEqual(len(call.kwargs["pass_fds"]), 3)

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
                "PATH": f"{binary.parent}:/usr/bin:/bin",
                "LANG": "C.UTF-8",
                "AZURE_CONFIG_DIR": "/tmp/azure-config",
                "AZURE_EXTENSION_DIR": "/tmp/hostile-extension",
                "AZURE_EXTENSION_SYS_DIR": "/tmp/hostile-system-extension",
                "AZURE_EXTENSION_DEV_SOURCES": "/tmp/hostile-dev-extension",
                "AZURE_EXTENSION_USE_DYNAMIC_INSTALL": "yes_without_prompt",
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
        self.assertRegex(process_argv[0], r"\A/proc/self/fd/[0-9]+\Z")
        self.assertEqual(process_argv[1:3], ["-I", "-B"])
        self.assertRegex(process_argv[3], r"\A/proc/self/fd/[0-9]+\Z")
        self.assertRegex(process_argv[4], r"\A/proc/self/fd/[0-9]+\Z")
        self.assertEqual(
            process_argv[5:9],
            ["group", "show", "--name", "rg-nac-bff-test"],
        )
        self.assertNotIn(str(binary.resolve()), process_argv)
        self.assertFalse(
            any(key.startswith("AZURE_EXTENSION_") for key in process_kwargs["env"])
        )
        self.assertEqual(len(process_kwargs["pass_fds"]), 3)
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

    def test_sealed_runtime_tamper_exit_maps_to_stable_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=86,
                stdout="sensitive runtime output",
                stderr="sensitive tamper detail",
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

        self.assertEqual(result["code"], "AZURE_CLI_RUNTIME_TAMPERED")
        self.assertEqual(result["returncode"], 86)
        self.assertNotIn("sensitive", json.dumps(result))

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


    def test_bound_artifact_replaces_provider_path_with_sealed_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = _fake_binary(root)
            binary_digest = _binary_sha256(binary)
            artifact = root / "main.json"
            artifact.write_text("{}")
            artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            completed = subprocess.CompletedProcess([], 0, "{}", "")
            command = [
                "deployment", "group", "create",
                "--name", "nac-bff-012345abcdef",
                "--resource-group", "rg-nac-bff-test",
                "--template-file", str(artifact),
                "--parameters", "@/tmp/prepared/main.parameters.json",
                "--mode", "Incremental",
            ]
            observed: dict[str, object] = {}
            def inspect_provider_path(argv, **kwargs):
                provider_path = argv[argv.index("--template-file") + 1]
                observed["basename"] = Path(provider_path).name
                observed["payload"] = Path(os.path.realpath(provider_path)).read_text()
                return completed
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                side_effect=inspect_provider_path,
            ) as process:
                result = run_azure_cli(
                    command,
                    binary=binary,
                    expected_binary_sha256=binary_digest,
                    bound_artifacts={str(artifact): (artifact, artifact_digest)},
                )

        self.assertTrue(result["ok"])
        provider_argv = process.call_args.args[0]
        self.assertNotIn(str(artifact), provider_argv)
        template_path = provider_argv[provider_argv.index("--template-file") + 1]
        self.assertRegex(template_path, r"^/proc/self/fd/[0-9]+/main[.]json$")
        self.assertEqual(len(process.call_args.kwargs["pass_fds"]), 4)
        self.assertEqual(observed, {"basename": "main.json", "payload": "{}"})

    def test_bound_artifact_hash_mismatch_stops_before_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = _fake_binary(root)
            artifact = root / "package.zip"
            artifact.write_bytes(b"tampered")
            command = [
                "functionapp", "deployment", "source", "config-zip",
                "--resource-group", "rg-nac-bff-test",
                "--name", "func-nac-bff-test-funktion8",
                "--src", str(artifact),
                "--build-remote", "true",
            ]
            with patch("nac_bff.azure_live_commands.subprocess.run") as process:
                result = run_azure_cli(
                    command,
                    binary=binary,
                    expected_binary_sha256=_binary_sha256(binary),
                    bound_artifacts={str(artifact): (artifact, "0" * 64)},
                )
        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "AZURE_CLI_ARTIFACT_BINDING_FAILED")
        process.assert_not_called()


class AzureLiveReadinessTests(_IsolatedAzureConfigTestCase):
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

    def test_unchanged_bound_runtime_snapshot_verifies_without_azure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = _fake_binary(root)
            expected = _binary_sha256(binary)
            runtime = azure_live_commands._prepare_bound_runtime(
                binary,
                expected_sha256=expected,
                cloud_selection_sha256=None,
            )
            self.assertIsNotNone(runtime)
            assert runtime is not None
            destination = root / "verified-copy"
            destination.mkdir()
            with runtime:
                completed = subprocess.run(
                    runtime.command(
                        ["--nac-internal-verify-only", str(destination)]
                    ),
                    check=False,
                    capture_output=True,
                    text=True,
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    timeout=30,
                    env=build_azure_cli_env({"HOME": str(root)}),
                    pass_fds=runtime.pass_fds,
                )

            copied_entrypoint = (
                destination / "azure" / "cli" / "__main__.py"
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                copied_entrypoint.read_bytes(),
                _package_entrypoint(binary).read_bytes(),
            )

    def test_mutation_after_runtime_binding_is_blocked_by_sealed_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = _fake_binary(root)
            expected = _binary_sha256(binary)
            runtime = azure_live_commands._prepare_bound_runtime(
                binary,
                expected_sha256=expected,
                cloud_selection_sha256=None,
            )
            self.assertIsNotNone(runtime)
            assert runtime is not None
            _package_entrypoint(binary).write_text(
                "raise RuntimeError('attestation-to-exec tamper')\n",
                encoding="utf-8",
            )
            destination = root / "verified-copy"
            destination.mkdir()
            with runtime:
                completed = subprocess.run(
                    runtime.command(
                        ["--nac-internal-verify-only", str(destination)]
                    ),
                    check=False,
                    capture_output=True,
                    text=True,
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    timeout=30,
                    env=build_azure_cli_env({"HOME": str(root)}),
                    pass_fds=runtime.pass_fds,
                )

        self.assertEqual(completed.returncode, 86)
        self.assertEqual(
            azure_live_commands.sealed_runtime_failure_code(
                completed.returncode
            ),
            "AZURE_CLI_RUNTIME_TAMPERED",
        )

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

    def test_native_elf_az_candidate_is_rejected_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "az"
            binary.write_bytes(b"\x7fELF" + b"\0" * 60)
            binary.chmod(0o700)
            with patch("nac_bff.azure_live_commands.subprocess.run") as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=hashlib.sha256(
                        binary.read_bytes()
                    ).hexdigest(),
                    environ={"HOME": tmp},
                )

        self.assertEqual(result["code"], "AZURE_CLI_BINARY_UNTRUSTED")
        process.assert_not_called()

    def test_minimal_env_does_not_copy_credential_variables(self) -> None:
        env = build_azure_cli_env(
            {
                "HOME": "/tmp/home",
                "PATH": "/bin",
                "TMPDIR": "/tmp",
                "AZURE_CLIENT_ID": "client-id",
                "AZURE_CLIENT_SECRET": "secret",
                "AZURE_TENANT_ID": "tenant",
                "REQUESTS_CA_BUNDLE": "/tmp/hostile-ca.pem",
                "SSL_CERT_FILE": "/tmp/hostile-cert.pem",
            }
        )

        self.assertEqual(env["HOME"], "/tmp/home")
        self.assertEqual(env["TMPDIR"], "/tmp")
        self.assertNotIn("AZURE_CLIENT_ID", env)
        self.assertNotIn("AZURE_CLIENT_SECRET", env)
        self.assertNotIn("AZURE_TENANT_ID", env)
        self.assertNotIn("REQUESTS_CA_BUNDLE", env)
        self.assertNotIn("SSL_CERT_FILE", env)

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
                        "environmentName": EXPECTED_CLOUD_NAME,
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
                "cloud_name": EXPECTED_CLOUD_NAME,
                "tenant_id": EXPECTED_TENANT_ID,
                "subscription_id": EXPECTED_SUBSCRIPTION_ID,
            },
        )
        self.assertNotIn("user", json.dumps(readiness))
        self.assertEqual(process.call_count, 1)

    def test_custom_cloud_config_is_rejected_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "azure-config"
            config.mkdir(mode=0o700)
            (config / "clouds.config").write_text(
                "[cloud]\nname = hostile\n", encoding="utf-8"
            )
            binary = _fake_binary(root)
            with patch("nac_bff.azure_live_commands.subprocess.run") as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=_binary_sha256(binary),
                    environ={"AZURE_CONFIG_DIR": str(config), "HOME": str(root)},
                )

        self.assertEqual(
            result["code"], "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED"
        )
        process.assert_not_called()

    def test_exact_default_cloud_selection_is_accepted_before_subprocess(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "azure-config"
            config.mkdir(mode=0o700)
            (config / "clouds.config").write_text(
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n",
                encoding="utf-8",
            )
            binary = _fake_binary(root)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="{}",
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ) as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=_binary_sha256(binary),
                    environ={"AZURE_CONFIG_DIR": str(config), "HOME": str(root)},
                )

        self.assertTrue(result["ok"])
        process.assert_called_once()

    def test_cloud_selection_size_boundary_is_exactly_4096(self) -> None:
        exact = (
            f"[{EXPECTED_CLOUD_NAME}]\n"
            f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n"
        ).encode("utf-8")
        for size, expected_ok in ((4096, True), (4097, False)):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config = root / "azure-config"
                config.mkdir(mode=0o700)
                payload = exact + b"#" * (size - len(exact))
                (config / "clouds.config").write_bytes(payload)
                binary = _fake_binary(root)
                completed = subprocess.CompletedProcess(
                    args=[],
                    returncode=0,
                    stdout="{}",
                    stderr="",
                )
                with patch(
                    "nac_bff.azure_live_commands.subprocess.run",
                    return_value=completed,
                ) as process:
                    result = run_azure_cli(
                        ["account", "show"],
                        binary=binary,
                        expected_binary_sha256=_binary_sha256(binary),
                        environ={
                            "AZURE_CONFIG_DIR": str(config),
                            "HOME": str(root),
                        },
                    )
                self.assertEqual(result["ok"], expected_ok)
                if expected_ok:
                    process.assert_called_once()
                else:
                    self.assertEqual(
                        result["code"],
                        "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED",
                    )
                    process.assert_not_called()

    def test_non_exact_default_cloud_selections_are_rejected(self) -> None:
        exact = (
            f"[{EXPECTED_CLOUD_NAME}]\n"
            f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n"
        ).encode("utf-8")
        cases = {
            "wrong_subscription": (
                f"[{EXPECTED_CLOUD_NAME}]\n"
                "subscription = 00000000-0000-0000-0000-000000000000\n"
            ).encode("utf-8"),
            "uppercase_subscription": (
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"subscription = {EXPECTED_SUBSCRIPTION_ID.upper()}\n"
            ).encode("utf-8"),
            "wrong_key_case": (
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"Subscription = {EXPECTED_SUBSCRIPTION_ID}\n"
            ).encode("utf-8"),
            "extra_key": exact + b"region = germanywestcentral\n",
            "extra_section": exact + b"[Other]\nvalue = rejected\n",
            "default_section": (
                b"[DEFAULT]\nvalue = rejected\n" + exact
            ),
            "duplicate_section": exact + exact,
            "malformed": b"[AzureCloud\nsubscription = rejected\n",
            "non_utf8": b"[AzureCloud]\nsubscription = \xff\n",
            "oversized": exact + b"#" * 4096,
        }
        for name, payload in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config = root / "azure-config"
                config.mkdir(mode=0o700)
                (config / "clouds.config").write_bytes(payload)
                binary = _fake_binary(root)
                with patch(
                    "nac_bff.azure_live_commands.subprocess.run"
                ) as process:
                    result = run_azure_cli(
                        ["account", "show"],
                        binary=binary,
                        expected_binary_sha256=_binary_sha256(binary),
                        environ={
                            "AZURE_CONFIG_DIR": str(config),
                            "HOME": str(root),
                        },
                    )
                self.assertEqual(
                    result["code"],
                    "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED",
                )
                process.assert_not_called()

    def test_untrusted_default_cloud_selection_shapes_are_rejected(self) -> None:
        exact = (
            f"[{EXPECTED_CLOUD_NAME}]\n"
            f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n"
        )
        for name in (
            "symlink",
            "group_writable_file",
            "world_writable_file",
            "directory",
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                config = root / "azure-config"
                config.mkdir(mode=0o700)
                selection = config / "clouds.config"
                if name == "symlink":
                    target = root / "selection.ini"
                    target.write_text(exact, encoding="utf-8")
                    selection.symlink_to(target)
                elif name in {
                    "group_writable_file",
                    "world_writable_file",
                }:
                    selection.write_text(exact, encoding="utf-8")
                    selection.chmod(
                        0o660 if name == "group_writable_file" else 0o666
                    )
                else:
                    selection.mkdir()
                binary = _fake_binary(root)
                with patch(
                    "nac_bff.azure_live_commands.subprocess.run"
                ) as process:
                    result = run_azure_cli(
                        ["account", "show"],
                        binary=binary,
                        expected_binary_sha256=_binary_sha256(binary),
                        environ={
                            "AZURE_CONFIG_DIR": str(config),
                            "HOME": str(root),
                        },
                    )
                self.assertEqual(
                    result["code"],
                    "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED",
                )
                process.assert_not_called()

    def test_foreign_owned_cloud_selection_measurement_is_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            selection = Path(tmp) / "clouds.config"
            selection.write_text(
                f"[{EXPECTED_CLOUD_NAME}]\n"
                f"subscription = {EXPECTED_SUBSCRIPTION_ID}\n",
                encoding="utf-8",
            )
            metadata = selection.lstat()
            foreign = SimpleNamespace(
                st_mode=metadata.st_mode,
                st_uid=os.geteuid() + 1,
                st_gid=metadata.st_gid,
                st_dev=metadata.st_dev,
                st_ino=metadata.st_ino,
                st_size=metadata.st_size,
                st_mtime_ns=metadata.st_mtime_ns,
                st_ctime_ns=metadata.st_ctime_ns,
            )
            with patch(
                "nac_bff.azure_live_commands.os.fstat",
                return_value=foreign,
            ):
                digest = (
                    azure_live_commands
                    ._exact_default_cloud_selection_digest(selection)
                )

        self.assertIsNone(digest)

    def test_group_writable_azure_config_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "azure-config"
            config.mkdir(mode=0o700)
            config.chmod(0o770)
            binary = _fake_binary(root)
            with patch("nac_bff.azure_live_commands.subprocess.run") as process:
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=_binary_sha256(binary),
                    environ={"AZURE_CONFIG_DIR": str(config), "HOME": str(root)},
                )

        self.assertEqual(result["code"], "AZURE_CLI_CONFIG_UNTRUSTED")
        process.assert_not_called()

    def test_wrong_cloud_is_not_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(
                    {
                        "id": EXPECTED_SUBSCRIPTION_ID,
                        "tenantId": EXPECTED_TENANT_ID,
                        "environmentName": "AzureGermanCloud",
                    }
                ),
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ):
                readiness = check_azure_cli_readiness(
                    binary=binary,
                    expected_binary_sha256=_binary_sha256(binary),
                )

        self.assertEqual(readiness["status"], "NOT_READY")
        self.assertEqual(readiness["code"], "AZURE_CLI_CLOUD_MISMATCH")

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
                {
                    "id": subscription_id,
                    "tenantId": tenant_id,
                    "environmentName": EXPECTED_CLOUD_NAME,
                }
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
