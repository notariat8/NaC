from __future__ import annotations

import copy
from datetime import UTC, datetime
import hashlib
import inspect
import json
import os
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import nac_bff.azure_cli_sealed_runtime as azure_cli_sealed_runtime
import nac_bff.azure_live_commands as azure_live_commands
from nac_bff.azure_performance_monitor import build_metrics_url, monitor_policy_sha256
from nac_bff.azure_performance_authorization import MONITOR_READ
from nac_bff.azure_live_commands import (
    ALLOWED_COMMAND_PREFIXES,
    AZURE_CLI_CANDIDATES,
    AZURE_CLI_SHA256_ENV,
    EXPECTED_CLOUD_NAME,
    EXPECTED_SUBSCRIPTION_ID,
    EXPECTED_TENANT_ID,
    FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS,
    FUNCTION_DEPLOYMENT_PROCESS_TIMEOUT_SECONDS,
    AzureCliAdapter,
    AzureCliInterruptionObservationPort,
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
                ("deployment", "operation", "group", "list"),
                ("identity", "show"),
                ("functionapp", "identity", "show"),
                ("functionapp", "config", "appsettings", "set"),
                ("functionapp", "config", "appsettings", "list"),
                ("resource", "list"),
                ("resource", "show"),
                ("rest",),
                ("functionapp", "deployment", "source", "config-zip"),
            ),
        )

    def test_resource_graph_rest_command_is_exactly_bounded(self) -> None:
        valid = [
            "rest",
            "--method",
            "post",
            "--url",
            azure_live_commands._RESOURCE_GRAPH_URL,
            "--body",
            azure_live_commands._RESOURCE_GRAPH_BODY,
        ]
        command, family, code = azure_live_commands._validated_command(valid)
        self.assertEqual(command, valid)
        self.assertEqual(family, ("rest",))
        self.assertEqual(code, "AZURE_CLI_OK")
        for option, replacement in (
            ("--method", "get"),
            ("--url", "https://management.azure.com/foreign"),
            ("--body", "{}"),
        ):
            drifted = list(valid)
            drifted[drifted.index(option) + 1] = replacement
            self.assertEqual(
                azure_live_commands._validated_command(drifted)[2],
                "AZURE_CLI_COMMAND_BLOCKED",
            )

        app_settings = [
            "rest", "--method", "post",
            "--url", azure_live_commands._APP_SETTINGS_URL,
        ]
        command, family, code = azure_live_commands._validated_command(
            app_settings
        )
        self.assertEqual(command, app_settings)
        self.assertEqual(family, ("rest",))
        self.assertEqual(code, "AZURE_CLI_OK")
        self.assertEqual(
            azure_live_commands._validated_command(valid[:-2])[2],
            "AZURE_CLI_COMMAND_BLOCKED",
        )
        self.assertEqual(
            azure_live_commands._validated_command(
                [*app_settings, "--body", azure_live_commands._RESOURCE_GRAPH_BODY]
            )[2],
            "AZURE_CLI_COMMAND_BLOCKED",
        )

    def test_monitor_get_is_limited_to_exact_adapter_url_shape(self) -> None:
        url = build_metrics_url(
            datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
            datetime(2026, 8, 3, 12, 2, tzinfo=UTC),
        )
        valid = ["rest", "--method", "get", "--url", url]
        command, family, code = azure_live_commands._validated_command(valid)
        self.assertEqual(command, valid)
        self.assertEqual(family, ("rest",))
        self.assertEqual(code, "AZURE_CLI_OK")

        query_parts = url.split("?", 1)[1].split("&")
        reordered = (
            f"{url.split('?', 1)[0]}?{query_parts[1]}&{query_parts[0]}&"
            + "&".join(query_parts[2:])
        )
        blocked_urls = (
            "https://management.azure.com/",
            azure_live_commands._RESOURCE_GRAPH_URL,
            url.replace("aggregation=Total", "aggregation=Average"),
            url.replace("Microsoft.Web%2Fsites", "Microsoft.Web%2Fserverfarms"),
            f"{url}&top=1",
            reordered,
        )
        for blocked_url in blocked_urls:
            with self.subTest(url=blocked_url):
                self.assertEqual(
                    azure_live_commands._validated_command(
                        ["rest", "--method", "get", "--url", blocked_url]
                    )[2],
                    "AZURE_CLI_COMMAND_BLOCKED",
                )

    def test_generic_adapter_rejects_monitor_url_before_process_resolution(self) -> None:
        url = build_metrics_url(
            datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
            datetime(2026, 8, 3, 12, 2, tzinfo=UTC),
        )
        adapter = AzureCliAdapter(binary="/must/not/be-resolved")

        result = adapter.run(["rest", "--method", "get", "--url", url])

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "AZURE_CLI_COMMAND_BLOCKED")

    def test_all_generic_adapter_entries_reject_reordered_monitor_options(self) -> None:
        url = build_metrics_url(
            datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
            datetime(2026, 8, 3, 12, 2, tzinfo=UTC),
        )
        adapter = AzureCliAdapter(binary="/must/not/be-resolved")
        command = ["rest", "--url", url, "--method", "get"]
        calls = (
            lambda: run_azure_cli(command, binary="/must/not/be-resolved"),
            lambda: adapter.run(command),
            lambda: adapter.run_with_timeout(command, timeout_seconds=1),
            lambda: adapter.run_bound(command, {}),
            lambda: adapter.run_bound_with_timeout(
                command, {}, timeout_seconds=1
            ),
        )

        for call in calls:
            with self.subTest(call=call):
                result = call()
                self.assertFalse(result["ok"])
                self.assertEqual(result["code"], "AZURE_CLI_COMMAND_BLOCKED")

    def test_dedicated_monitor_method_consumes_exact_bound_capability(self) -> None:
        url = build_metrics_url(
            datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
            datetime(2026, 8, 3, 12, 2, tzinfo=UTC),
        )
        capability = object()
        target = "a" * 64
        expected = {"ok": True, "data": {}}
        adapter = AzureCliAdapter(binary="/sealed/az")

        with patch(
            "nac_bff.azure_performance_authorization._authorize_live_action"
        ) as authorize, patch.object(
            azure_live_commands, "_run_azure_cli", return_value=expected
        ) as execute:
            result = adapter.run_monitor_metrics(
                ["rest", "--method", "get", "--url", url],
                live_action_capability=capability,  # type: ignore[arg-type]
                target_binding_sha256=target,
            )

        self.assertIs(result, expected)
        authorize.assert_called_once_with(
            capability,
            action=MONITOR_READ,
            target_binding_sha256=target,
            binding_sha256=monitor_policy_sha256(),
            consume=True,
        )
        self.assertIs(
            execute.call_args.kwargs["_monitor_execution_authority"],
            azure_live_commands._MONITOR_EXECUTION_AUTHORITY,
        )

        blocked_commands = (
            ["rest", "--method", "post", "--url", url],
            [
                "rest",
                "--method",
                "get",
                "--url",
                url,
                "--body",
                azure_live_commands._RESOURCE_GRAPH_BODY,
            ],
            [
                "rest",
                "--method",
                "get",
                "--url",
                azure_live_commands._APP_SETTINGS_URL,
            ],
        )
        for blocked in blocked_commands:
            with self.subTest(command=blocked):
                self.assertEqual(
                    azure_live_commands._validated_command(blocked)[2],
                    "AZURE_CLI_COMMAND_BLOCKED",
                )

    def test_resource_graph_projection_rejects_paging_and_count_drift(self) -> None:
        complete = {
            "count": 0,
            "data": [],
            "resultTruncated": "false",
            "totalRecords": 0,
        }
        self.assertEqual(
            azure_live_commands._resource_graph_projection(complete), []
        )
        drifted_responses = (
            {**complete, "resultTruncated": "true"},
            {**complete, "resultTruncated": True},
            {**complete, "count": 1},
            {**complete, "totalRecords": 1},
            {**complete, "skipToken": "next-page"},
            {key: value for key, value in complete.items() if key != "count"},
            {
                key: value
                for key, value in complete.items()
                if key != "totalRecords"
            },
        )
        for response in drifted_responses:
            with self.subTest(response=response), self.assertRaisesRegex(
                ValueError, "AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID"
            ):
                azure_live_commands._resource_graph_projection(response)

    def test_security_projection_allows_provider_metadata_but_rejects_security_drift(self) -> None:
        expected = {
            "allowSharedKeyAccess": False,
            "networkAcls": {"bypass": "None"},
        }
        actual = {
            **expected,
            "primaryEndpoints": {"blob": "https://provider-managed"},
            "networkAcls": {
                "bypass": "None",
                "resourceAccessRules": [],
            },
        }

        self.assertTrue(
            azure_live_commands._security_projection_matches(actual, expected)
        )
        drifted = copy.deepcopy(actual)
        drifted["allowSharedKeyAccess"] = True
        self.assertFalse(
            azure_live_commands._security_projection_matches(drifted, expected)
        )

    def test_performance_network_readback_rejects_security_drift(self) -> None:
        virtual_network_id = (
            "/subscriptions/11111111-1111-1111-1111-111111111111"
            "/resourceGroups/rg-nac-test"
            "/providers/Microsoft.Network/virtualNetworks/vnet-nac-test"
        )
        virtual_network = {
            "addressSpace": {"addressPrefixes": ["10.42.0.0/24"]},
            "subnets": [
                {"id": f"{virtual_network_id}/subnets/snet-flex-integration"},
                {"id": f"{virtual_network_id}/subnets/snet-private-endpoints"},
            ],
            "provisioningState": "Succeeded",
        }
        subnet = {
            "addressPrefix": "10.42.0.0/27",
            "delegations": [{
                "properties": {"serviceName": "Microsoft.App/environments"}
            }],
            "privateEndpointNetworkPolicies": "Enabled",
            "privateLinkServiceNetworkPolicies": "Enabled",
            "provisioningState": "Succeeded",
        }

        self.assertTrue(
            azure_live_commands._virtual_network_state_matches(
                virtual_network, virtual_network_id
            )
        )
        self.assertTrue(
            azure_live_commands._subnet_state_matches(
                subnet,
                address_prefix="10.42.0.0/27",
                delegation_services=["Microsoft.App/environments"],
                private_endpoint_network_policies="Enabled",
            )
        )
        for field, value in (
            ("networkSecurityGroup", {"id": "unexpected"}),
            ("routeTable", {"id": "unexpected"}),
            ("natGateway", {"id": "unexpected"}),
            ("serviceEndpoints", [{"service": "Microsoft.Storage"}]),
            ("serviceEndpointPolicies", [{"id": "unexpected"}]),
        ):
            with self.subTest(field=field):
                drifted = copy.deepcopy(subnet)
                drifted[field] = value
                self.assertFalse(
                    azure_live_commands._subnet_state_matches(
                        drifted,
                        address_prefix="10.42.0.0/27",
                        delegation_services=["Microsoft.App/environments"],
                        private_endpoint_network_policies="Enabled",
                    )
                )

        drifted_vnet = copy.deepcopy(virtual_network)
        drifted_vnet["subnets"].append({
            "id": f"{virtual_network_id}/subnets/unexpected"
        })
        self.assertFalse(
            azure_live_commands._virtual_network_state_matches(
                drifted_vnet, virtual_network_id
            )
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
        self.assertIn("install_private_azure_cloud_config", source)
        self.assertIn("verify_write_account_binding", source)
        self.assertNotIn("validate_private_azure_profile", source)
        self.assertIn('account.get("environmentName") != EXPECTED_CLOUD_NAME', source)
        self.assertIn('account.get("state") != "Enabled"', source)
        self.assertIn("MAX_ACCOUNT_ASSERTION_BYTES = 16384", source)
        self.assertIn("os.pipe2(os.O_CLOEXEC)", source)
        self.assertIn("os.setsid()", source)
        self.assertIn("os.waitid(", source)
        self.assertIn("os.WNOWAIT", source)
        self.assertIn("kill_account_process_group", source)
        self.assertIn("len(payload) > MAX_ACCOUNT_ASSERTION_BYTES", source)
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
        self.assertIn("zipfile.ZipFile(package_archive_path", source)
        self.assertNotIn("stage_verified_package", source)
        self.assertIn("destination, private_config, libc = isolate()", source)
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

    def test_sealed_runtime_binds_package_archive_before_isolation(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        validate_package_archive = namespace["validate_package_archive"]
        copy_archived_verified = namespace["copy_archived_verified"]

        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            source_root.mkdir()
            nested = source_root / "azure" / "module"
            nested.mkdir(parents=True)
            source_file = nested / "module.py"
            source_file.write_text("VALUE = 1\n", encoding="utf-8")
            metadata = source_file.stat()
            manifest = azure_cli_sealed_runtime._package_manifest(
                source_root,
                allowed_uids={os.getuid()},
            )
            self.assertIsNotNone(manifest)
            assert manifest is not None
            tree_digest, manifest_payload = manifest

            package_fd = azure_cli_sealed_runtime._sealed_package_memfd(
                source_root,
                manifest_payload,
                tree_digest=tree_digest,
                allowed_uids={os.getuid()},
            )
            self.assertIsNotNone(package_fd)
            assert package_fd is not None
            try:
                with os.fdopen(os.dup(package_fd), "rb") as stream:
                    with zipfile.ZipFile(stream, mode="r") as archive:
                        validate_package_archive(
                            archive,
                            manifest_payload["files"],
                        )
                        destination = Path(tmp) / "destination.py"
                        copy_archived_verified(
                            archive,
                            destination,
                            manifest_payload["files"][0],
                        )
                self.assertEqual(
                    destination.read_bytes(),
                    source_file.read_bytes(),
                )
                self.assertEqual(
                    destination.stat().st_mode & 0o777,
                    (metadata.st_mode & 0o777) & ~0o222,
                )
                os.lseek(package_fd, 0, os.SEEK_END)
                with self.assertRaises(OSError):
                    os.write(package_fd, b"tamper")
            finally:
                os.close(package_fd)

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
                try:
                    fields = status.read_text(encoding="ascii").split()
                except OSError:
                    # The child (or its /proc entry) vanished between the
                    # exists() check and the read.  /proc/{pid}/stat removal
                    # surfaces as either FileNotFoundError (ENOENT) or
                    # ProcessLookupError (ESRCH) depending on timing; either
                    # way the child did not survive the supervisor kill, which
                    # is the success condition.
                    break
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

    def test_sealed_bootstrap_keeps_cli_profile_state_opaque_and_pins_cloud(
        self,
    ) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        install_private_azure_cloud_config = namespace[
            "install_private_azure_cloud_config"
        ]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "azureProfile.json"
            profile_payload = {"installationId": "opaque-cli-state"}
            profile.write_text(
                json.dumps(profile_payload),
                encoding="utf-8-sig",
            )
            (root / "config").write_text(
                "[cloud]\nname = AzureGermanCloud\n",
                encoding="utf-8",
            )

            install_private_azure_cloud_config(root)

            self.assertEqual(
                json.loads(profile.read_text(encoding="utf-8-sig")),
                profile_payload,
            )
            self.assertEqual(
                (root / "config").read_text(encoding="utf-8"),
                "[cloud]\nname = AzureCloud\n",
            )

    def test_sealed_bootstrap_account_binding_payload_is_exact(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        validate = namespace["validate_account_binding_payload"]
        self.assertEqual(namespace["MAX_ACCOUNT_ASSERTION_BYTES"], 16384)
        self.assertEqual(
            namespace["ACCOUNT_ASSERTION_FIELDS"],
            frozenset({"id", "tenantId", "environmentName", "state"}),
        )
        self.assertEqual(
            namespace["WRITE_COMMAND_PREFIXES"],
            (
                ("provider", "register"),
                ("group", "create"),
                ("deployment", "group", "create"),
                ("functionapp", "deployment", "source", "config-zip"),
            ),
        )
        valid = {
            "id": EXPECTED_SUBSCRIPTION_ID,
            "tenantId": EXPECTED_TENANT_ID,
            "environmentName": EXPECTED_CLOUD_NAME,
            "state": "Enabled",
        }

        validate(json.dumps(valid).encode("utf-8"))

        invalid = (
            {**valid, "state": "Disabled"},
            {**valid, "tenantId": "00000000-0000-0000-0000-000000000000"},
            {**valid, "id": "00000000-0000-0000-0000-000000000000"},
            {**valid, "environmentName": "AzureGermanCloud"},
            {**valid, "extra": "ambiguous"},
        )
        for account in invalid:
            with self.subTest(account_keys=sorted(account)):
                with self.assertRaisesRegex(SystemExit, "86"):
                    validate(json.dumps(account).encode("utf-8"))
        duplicate_key = (
            b'{"id":"first","id":"second","tenantId":"tenant",'
            b'"environmentName":"AzureCloud","state":"Enabled"}'
        )
        for payload in (b"", b"[]", b"not-json", b"\xff", duplicate_key):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(SystemExit, "86"):
                    validate(payload)

    def test_sealed_bootstrap_asserts_account_once_before_each_write(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        verify = namespace["verify_write_account_binding"]
        valid = {
            "id": EXPECTED_SUBSCRIPTION_ID,
            "tenantId": EXPECTED_TENANT_ID,
            "environmentName": EXPECTED_CLOUD_NAME,
            "state": "Enabled",
        }

        with tempfile.TemporaryDirectory() as tmp:
            calls = Path(tmp) / "calls"
            snapshot = Path(tmp) / "private-azure-config"
            snapshot.mkdir()

            def fake_run_module(*_args: object, **_kwargs: object) -> None:
                with calls.open("a", encoding="utf-8") as stream:
                    stream.write(
                        json.dumps(
                            {
                                "config": os.environ["AZURE_CONFIG_DIR"],
                                "argv": list(namespace["sys"].argv),
                            }
                        )
                        + "\n"
                    )
                os.write(1, (json.dumps(valid) + "\n").encode("utf-8"))

            with (
                patch.dict(
                    os.environ,
                    {"AZURE_CONFIG_DIR": str(snapshot)},
                ),
                patch.object(
                    namespace["runpy"],
                    "run_module",
                    side_effect=fake_run_module,
                ),
            ):
                for prefix in namespace["WRITE_COMMAND_PREFIXES"]:
                    calls.write_bytes(b"")
                    verify([*prefix, "--synthetic-test-option", "value"])
                    records = [
                        json.loads(line)
                        for line in calls.read_text(encoding="utf-8").splitlines()
                    ]
                    self.assertEqual(
                        records,
                        [
                            {
                                "config": str(snapshot),
                                "argv": [
                                    "az", "account", "show",
                                    "--subscription",
                                    EXPECTED_SUBSCRIPTION_ID,
                                    "--query",
                                    (
                                        "{id:id,tenantId:tenantId,"
                                        "environmentName:environmentName,"
                                        "state:state}"
                                    ),
                                    "--output", "json", "--only-show-errors",
                                ],
                            }
                        ],
                    )

                calls.write_bytes(b"")
                verify(["provider", "show", "--namespace", "Microsoft.Web"])
                self.assertEqual(calls.read_bytes(), b"")

    def test_sealed_account_child_does_not_flush_parent_stdout_buffer(
        self,
    ) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        prefix = source.rsplit("\nmain()\n", 1)[0]
        valid = {
            "id": EXPECTED_SUBSCRIPTION_ID,
            "tenantId": EXPECTED_TENANT_ID,
            "environmentName": EXPECTED_CLOUD_NAME,
            "state": "Enabled",
        }
        helper = (
            "import io, json, sys\n"
            "namespace = {}\n"
            f"exec({prefix!r}, namespace)\n"
            "raw = io.FileIO(1, mode='wb', closefd=False)\n"
            "buffer = io.BufferedWriter(raw, buffer_size=8192)\n"
            "sys.stdout = io.TextIOWrapper(\n"
            "    buffer,\n"
            "    encoding='utf-8',\n"
            "    line_buffering=False,\n"
            "    write_through=False,\n"
            ")\n"
            "sys.stdout.write('parent-buffered-output\\n')\n"
            "sys.__stdout__ = sys.stdout\n"
            f"valid = {valid!r}\n"
            "def fake_run_module(*_args, **_kwargs):\n"
            "    print(json.dumps(valid), file=sys.__stdout__)\n"
            "namespace['runpy'].run_module = fake_run_module\n"
            "namespace['verify_write_account_binding'](\n"
            "    ['group', 'create', '--name', 'nac-test']\n"
            ")\n"
            "sys.stdout.flush()\n"
        )

        completed = subprocess.run(
            [os.sys.executable, "-c", helper],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "parent-buffered-output\n")

    def test_sealed_bootstrap_account_assertion_fails_closed(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        verify = namespace["verify_write_account_binding"]

        def run_with_payload(payload: bytes) -> None:
            def fake_run_module(*_args: object, **_kwargs: object) -> None:
                os.write(1, payload)

            with patch.object(
                namespace["runpy"],
                "run_module",
                side_effect=fake_run_module,
            ):
                verify(["group", "create", "--name", "nac-test"])

        wrong_state = json.dumps(
            {
                "id": EXPECTED_SUBSCRIPTION_ID,
                "tenantId": EXPECTED_TENANT_ID,
                "environmentName": EXPECTED_CLOUD_NAME,
                "state": "Disabled",
            }
        ).encode("utf-8")
        with self.assertRaisesRegex(SystemExit, "86"):
            run_with_payload(wrong_state)
        with self.assertRaisesRegex(SystemExit, "86"):
            run_with_payload(b"x" * 16385)

    def test_sealed_bootstrap_account_child_closes_fds_and_times_out(self) -> None:
        source = azure_cli_sealed_runtime._BOOTSTRAP_SOURCE
        namespace: dict[str, object] = {}
        exec(source.rsplit("\nmain()\n", 1)[0], namespace)
        verify = namespace["verify_write_account_binding"]
        valid = {
            "id": EXPECTED_SUBSCRIPTION_ID,
            "tenantId": EXPECTED_TENANT_ID,
            "environmentName": EXPECTED_CLOUD_NAME,
            "state": "Enabled",
        }

        with tempfile.TemporaryDirectory() as tmp:
            inherited_fd = os.open(Path(tmp) / "inherited", os.O_CREAT | os.O_RDWR)
            try:
                def assert_fd_closed(*_args: object, **_kwargs: object) -> None:
                    try:
                        os.fstat(inherited_fd)
                    except OSError:
                        os.write(1, (json.dumps(valid) + "\n").encode("utf-8"))
                    else:
                        os.write(1, b"{}\n")

                with patch.object(
                    namespace["runpy"],
                    "run_module",
                    side_effect=assert_fd_closed,
                ):
                    verify(["provider", "register", "--namespace", "Microsoft.Web"])
            finally:
                os.close(inherited_fd)

        namespace["ACCOUNT_ASSERTION_TIMEOUT_SECONDS"] = 0.05

        def hang(*_args: object, **_kwargs: object) -> None:
            time.sleep(5)

        started = time.monotonic()
        with (
            patch.object(namespace["runpy"], "run_module", side_effect=hang),
            self.assertRaisesRegex(SystemExit, "86"),
        ):
            verify(["group", "create", "--name", "nac-test"])
        self.assertLess(time.monotonic() - started, 1.0)

        with tempfile.TemporaryDirectory() as tmp:
            descendant_pid_path = Path(tmp) / "descendant-pid"

            def fork_descendant(
                *_args: object,
                **_kwargs: object,
            ) -> None:
                descendant_pid = os.fork()
                if descendant_pid == 0:
                    os.close(1)
                    time.sleep(5)
                    os._exit(0)
                descendant_pid_path.write_text(
                    str(descendant_pid),
                    encoding="ascii",
                )
                os.write(1, (json.dumps(valid) + "\n").encode("utf-8"))

            with patch.object(
                namespace["runpy"],
                "run_module",
                side_effect=fork_descendant,
            ):
                verify(["group", "create", "--name", "nac-test"])

            descendant_pid = int(
                descendant_pid_path.read_text(encoding="ascii")
            )
            deadline = time.monotonic() + 1.0
            state = ""
            while time.monotonic() < deadline:
                try:
                    state = (
                        Path(f"/proc/{descendant_pid}/stat")
                        .read_text(encoding="ascii")
                        .split()[2]
                    )
                except (FileNotFoundError, IndexError, OSError):
                    state = "gone"
                    break
                if state == "Z":
                    break
                time.sleep(0.01)
            self.assertIn(state, {"gone", "Z"})

        def delayed_setsid() -> None:
            time.sleep(5)

        started = time.monotonic()
        with (
            patch.object(namespace["os"], "setsid", side_effect=delayed_setsid),
            self.assertRaisesRegex(SystemExit, "86"),
        ):
            verify(["group", "create", "--name", "nac-test"])
        self.assertLess(time.monotonic() - started, 1.0)

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
                "identity", "show",
                "--name", "id-nac-bff-prod-foreign",
                "--resource-group", "rg-nac-bff-test",
            ],
            [
                "functionapp", "identity", "show",
                "--name", "foreign-function",
                "--resource-group", "rg-nac-bff-test",
            ],
            [
                "resource", "show",
                "--resource-group", "rg-nac-bff-test",
                "--resource-type", "Microsoft.Insights/ActionGroups",
                "--name", "Foreign Action Group",
                "--api-version", "2021-09-01",
            ],
            [
                "resource", "show",
                "--resource-group", "rg-nac-bff-test",
                "--resource-type", "Microsoft.Insights/components",
                "--name", "Application Insights Smart Detection",
                "--api-version", "2021-09-01",
            ],
            [
                "resource", "show",
                "--resource-group", "foreign-rg",
                "--resource-type", "Microsoft.Insights/ActionGroups",
                "--name", "Application Insights Smart Detection",
                "--api-version", "2021-09-01",
            ],
            [
                "resource", "show",
                "--resource-group", "rg-nac-bff-test",
                "--resource-type", "Microsoft.Insights/ActionGroups",
                "--name", "Application Insights Smart Detection",
                "--api-version", "2020-01-01",
            ],
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
            [
                "functionapp", "deployment", "source", "config-zip",
                "--resource-group", "rg-nac-bff-test",
                "--name", "func-nac-bff-test-funktion8",
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

    def test_function_deploy_timeout_must_be_exact_and_single(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "nac-bff.zip"
            artifact.write_bytes(b"package")
            base = [
                "functionapp",
                "deployment",
                "source",
                "config-zip",
                "--resource-group",
                "rg-nac-bff-test",
                "--name",
                "func-nac-bff-test-funktion8",
                "--src",
                str(artifact),
                "--build-remote",
                "true",
            ]
            blocked = (
                [*base, "--timeout", "899"],
                [
                    *base,
                    "--timeout",
                    str(FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS),
                    "--timeout",
                    str(FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS),
                ],
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run"
            ) as process:
                for argv in blocked:
                    with self.subTest(argv=argv):
                        result = run_azure_cli(
                            argv, binary="/does/not/matter"
                        )
                        self.assertFalse(result["ok"])
                        self.assertIn(
                            result["code"],
                            {
                                "AZURE_CLI_ARGV_INVALID",
                                "AZURE_CLI_COMMAND_BLOCKED",
                            },
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
                "resource",
                "show",
                "--resource-group",
                "rg-nac-bff-test",
                "--resource-type",
                "Microsoft.Insights/ActionGroups",
                "--name",
                "Application Insights Smart Detection",
                "--api-version",
                "2021-09-01",
            ],
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
                "--timeout",
                str(FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS),
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
            self.assertRegex(argv[5], r"\A/proc/self/fd/[0-9]+\Z")
            azure_argv = argv[6:]
            self.assertEqual(azure_argv[-3:], ["--output", "json", "--only-show-errors"])
            subscription_index = azure_argv.index("--subscription")
            self.assertEqual(
                azure_argv[subscription_index + 1],
                EXPECTED_SUBSCRIPTION_ID,
            )
            self.assertEqual(azure_argv.count("--subscription"), 1)
            self.assertEqual(len(call.kwargs["pass_fds"]), 4)

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
        self.assertRegex(process_argv[5], r"\A/proc/self/fd/[0-9]+\Z")
        self.assertEqual(
            process_argv[6:10],
            ["group", "show", "--name", "rg-nac-bff-test"],
        )
        self.assertNotIn(str(binary.resolve()), process_argv)
        self.assertFalse(
            any(key.startswith("AZURE_EXTENSION_") for key in process_kwargs["env"])
        )
        self.assertEqual(len(process_kwargs["pass_fds"]), 4)
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

    def test_duplicate_json_keys_are_rejected_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout='{"provisioningState":"Running",'
                '"provisioningState":"Succeeded"}',
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
        self.assertNotIn("provisioningState", json.dumps(result))

    def test_provider_register_accepts_empty_success_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="\n",
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ):
                result = run_azure_cli(
                    [
                        "provider",
                        "register",
                        "--namespace",
                        "Microsoft.Web",
                        "--wait",
                    ],
                    binary=binary,
                    expected_binary_sha256=digest,
                )

        self.assertTrue(result["ok"])
        self.assertEqual(result["code"], "AZURE_CLI_OK")
        self.assertEqual(result["data"], {})

    def test_provider_register_rejects_nonempty_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="not-json",
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ):
                result = run_azure_cli(
                    [
                        "provider",
                        "register",
                        "--namespace",
                        "Microsoft.Web",
                        "--wait",
                    ],
                    binary=binary,
                    expected_binary_sha256=digest,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "AZURE_CLI_OUTPUT_INVALID")

    def test_read_command_rejects_empty_success_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
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

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "AZURE_CLI_OUTPUT_INVALID")

    def test_other_write_command_rejects_empty_success_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            digest = _binary_sha256(binary)
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="",
                stderr="",
            )
            with patch(
                "nac_bff.azure_live_commands.subprocess.run",
                return_value=completed,
            ):
                result = run_azure_cli(
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
                    binary=binary,
                    expected_binary_sha256=digest,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(result["code"], "AZURE_CLI_OUTPUT_INVALID")


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
        self.assertEqual(len(process.call_args.kwargs["pass_fds"]), 5)
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
                "--timeout",
                str(FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS),
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

    def test_runtime_uses_bound_snapshot_after_original_package_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = _fake_binary(root)
            expected = _binary_sha256(binary)
            original = _package_entrypoint(binary).read_bytes()
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

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                (destination / "azure" / "cli" / "__main__.py").read_bytes(),
                original,
            )

    def test_bound_package_memfd_is_immutable_and_still_verifies(self) -> None:
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
            os.lseek(runtime.package_fd, 0, os.SEEK_END)
            with self.assertRaises(OSError):
                os.write(runtime.package_fd, b"bound package tamper")
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

            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_run_azure_cli_timeout_closes_all_bound_memfds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            expected = _binary_sha256(binary)
            original_prepare = azure_live_commands._prepare_bound_runtime
            captured: list[azure_cli_sealed_runtime.SealedAzureCliRuntime] = []

            def capture_runtime(*args: object, **kwargs: object):
                runtime = original_prepare(*args, **kwargs)
                if runtime is not None:
                    captured.append(runtime)
                return runtime

            with (
                patch(
                    "nac_bff.azure_live_commands._prepare_bound_runtime",
                    side_effect=capture_runtime,
                ),
                patch(
                    "nac_bff.azure_live_commands.subprocess.run",
                    side_effect=subprocess.TimeoutExpired(
                        cmd=["az"],
                        timeout=0.01,
                    ),
                ),
            ):
                result = run_azure_cli(
                    ["account", "show"],
                    binary=binary,
                    expected_binary_sha256=expected,
                    timeout_seconds=0.01,
                )

        self.assertEqual(result["code"], "AZURE_CLI_TIMEOUT")
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0].pass_fds, (-1, -1, -1, -1))

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

        self.assertEqual(result["code"], "AZURE_CLI_RUNTIME_BINDING_FAILED")
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
        account_argv = process.call_args.args[0][6:]
        self.assertEqual(
            account_argv,
            [
                "account",
                "show",
                "--subscription",
                EXPECTED_SUBSCRIPTION_ID,
                "--output",
                "json",
                "--only-show-errors",
            ],
        )

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

    def test_unauthenticated_cli_state_fails_closed_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            binary = _fake_binary(Path(tmp))
            completed = subprocess.CompletedProcess(
                args=[],
                returncode=86,
                stdout="profile-secret-must-not-escape",
                stderr="token-secret-must-not-escape",
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
        self.assertEqual(readiness["code"], "AZURE_CLI_RUNTIME_TAMPERED")
        self.assertFalse(readiness["ready"])
        self.assertNotIn("secret", json.dumps(readiness))

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

    def test_disabled_subscription_is_not_ready(self) -> None:
        readiness = _readiness_for_account(
            tenant_id=EXPECTED_TENANT_ID,
            subscription_id=EXPECTED_SUBSCRIPTION_ID,
            state="Disabled",
        )

        self.assertEqual(readiness["status"], "NOT_READY")
        self.assertEqual(
            readiness["code"],
            "AZURE_CLI_SUBSCRIPTION_STATE_INVALID",
        )
        self.assertFalse(readiness["ready"])
        self.assertNotIn("Disabled", json.dumps(readiness))

    def test_missing_subscription_state_is_not_ready(self) -> None:
        readiness = _readiness_for_account(
            tenant_id=EXPECTED_TENANT_ID,
            subscription_id=EXPECTED_SUBSCRIPTION_ID,
            state=None,
        )

        self.assertEqual(readiness["status"], "NOT_READY")
        self.assertEqual(
            readiness["code"],
            "AZURE_CLI_SUBSCRIPTION_STATE_INVALID",
        )

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

    def test_adapter_forwards_per_call_timeout(self) -> None:
        adapter = AzureCliAdapter(
            binary="/trusted/azure/az",
            expected_binary_sha256="a" * 64,
            environ={},
        )
        expected = {"ok": True, "code": "AZURE_CLI_COMMAND_PASSED", "data": {}}

        with patch(
            "nac_bff.azure_live_commands.run_azure_cli",
            return_value=expected,
        ) as run:
            result = adapter.run_with_timeout(
                ["provider", "show", "--namespace", "Microsoft.Storage"],
                timeout_seconds=17.5,
            )

        self.assertEqual(result, expected)
        self.assertEqual(run.call_args.kwargs["timeout_seconds"], 17.5)

    def test_adapter_forwards_bound_artifacts_with_per_call_timeout(self) -> None:
        adapter = AzureCliAdapter(
            binary="/trusted/azure/az",
            expected_binary_sha256="a" * 64,
            environ={},
        )
        artifact = Path("/tmp/prepared/function/nac-bff.zip")
        bindings = {str(artifact): (artifact, "b" * 64)}
        expected = {"ok": True, "code": "AZURE_CLI_COMMAND_PASSED", "data": {}}

        with patch(
            "nac_bff.azure_live_commands.run_azure_cli",
            return_value=expected,
        ) as run:
            result = adapter.run_bound_with_timeout(
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
                    str(artifact),
                    "--build-remote",
                    "true",
                    "--timeout",
                    str(FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS),
                ],
                bindings,
                timeout_seconds=FUNCTION_DEPLOYMENT_PROCESS_TIMEOUT_SECONDS,
            )

        self.assertEqual(result, expected)
        self.assertEqual(
            run.call_args.kwargs["timeout_seconds"],
            FUNCTION_DEPLOYMENT_PROCESS_TIMEOUT_SECONDS,
        )
        self.assertEqual(run.call_args.kwargs["bound_artifacts"], bindings)


    def test_legacy_nonempty_interruption_observation_remains_reconcilable(self) -> None:
        self._assert_nonempty_interruption_observation(current=False)

    def test_nonempty_interruption_observation_uses_dynamic_audience_and_app_settings_rest(self) -> None:
        self._assert_nonempty_interruption_observation(current=True)

    def _assert_nonempty_interruption_observation(self, *, current: bool) -> None:
        from tests.test_nac_bff_azure_interruption_baseline import (
            ACTIVATION_HASH,
            CLIENT_ID,
            COMMIT,
            CURRENT_AZURE_TEMPLATE_HASH,
            LEGACY_AZURE_TEMPLATE_HASH,
            PRINCIPAL_ID,
            SYSTEM_PRINCIPAL_ID,
            TREE,
            _deployment,
            _identity_binding,
            _inventory,
            _load_expectation,
            _operations,
            _prepared,
        )
        from nac_bff.azure_interruption_baseline import (
            EXPECTED_DEPLOYMENT_TYPE_COUNTS,
            LEGACY_DEPLOYMENT_TYPE_COUNTS,
        )

        with tempfile.TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            _prepared(run_dir, legacy=not current)
            request = SimpleNamespace(
                expected_activation_hash=ACTIVATION_HASH,
                approved_commit=COMMIT,
                approved_tree=TREE,
            )
            expectation, error = _load_expectation(
                run_dir, {"activation_hash": ACTIVATION_HASH}, request
            )
            self.assertIsNone(error)
            assert expectation is not None
            inventory = _inventory(current=current)
            by_type = {item["type"]: item for item in inventory}
            operations = _operations(current=current)
            deployment = _deployment(expectation)
            identity = _identity_binding()
            self.assertEqual(
                expectation["deployment_type_counts"],
                (
                    EXPECTED_DEPLOYMENT_TYPE_COUNTS
                    if current
                    else LEGACY_DEPLOYMENT_TYPE_COUNTS
                ),
            )
            self.assertEqual(
                expectation["azure_template_hash"],
                (
                    CURRENT_AZURE_TEMPLATE_HASH
                    if current
                    else LEGACY_AZURE_TEMPLATE_HASH
                ),
            )
            self.assertEqual(len(operations), 15 if current else 12)
            self.assertEqual(
                deployment["template_hash"],
                (
                    CURRENT_AZURE_TEMPLATE_HASH
                    if current
                    else LEGACY_AZURE_TEMPLATE_HASH
                ),
            )
            self.assertEqual(deployment["mode"], "Incremental")
            raw_inventory = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "type": item["type"],
                    "resourceGroup": item["resource_group"],
                    "location": item["location"],
                    "kind": item["kind"],
                    "sku": item["sku"],
                    "tags": item["tags"],
                    "managedBy": item["managed_by"],
                }
                for item in inventory
            ]
            smart = by_type["microsoft.insights/actiongroups"]
            smart_detail = {
                **next(
                    item for item in raw_inventory
                    if item["type"] == "microsoft.insights/actiongroups"
                ),
                "properties": smart["properties"],
            }
            parameters = json.loads(
                (run_dir / "prepared/main.parameters.json").read_text()
            )["parameters"]
            raw_deployment = {
                "name": deployment["name"],
                "resourceGroup": deployment["resource_group"],
                "properties": {
                    "provisioningState": "Succeeded",
                    "mode": "Incremental",
                    "templateHash": deployment["template_hash"],
                    "parameters": parameters,
                    "outputs": {
                        "functionAppResourceId": {
                            "type": "String",
                            "value": deployment["outputs"]["function_app_resource_id"],
                        },
                        "functionAppHostName": {
                            "type": "String",
                            "value": deployment["outputs"]["function_app_host_name"],
                        },
                        "functionAppSystemAssignedPrincipalId": {
                            "type": "String",
                            "value": SYSTEM_PRINCIPAL_ID,
                        },
                        **(
                            {
                                "virtualNetworkResourceId": {
                                    "type": "String",
                                    "value": deployment["outputs"][
                                        "virtual_network_resource_id"
                                    ],
                                },
                                "functionIntegrationSubnetResourceId": {
                                    "type": "String",
                                    "value": deployment["outputs"][
                                        "function_integration_subnet_resource_id"
                                    ],
                                },
                                "privateEndpointSubnetResourceId": {
                                    "type": "String",
                                    "value": deployment["outputs"][
                                        "private_endpoint_subnet_resource_id"
                                    ],
                                },
                            }
                            if current
                            else {}
                        ),
                        "managedIdentityResourceId": {
                            "type": "String",
                            "value": deployment["outputs"]["managed_identity_resource_id"],
                        },
                        "managedIdentityClientId": {
                            "type": "String",
                            "value": CLIENT_ID,
                        },
                        "managedIdentityPrincipalId": {
                            "type": "String",
                            "value": PRINCIPAL_ID,
                        },
                    },
                },
            }
            raw_operations = [
                {
                    "properties": {
                        "provisioningState": "Succeeded",
                        "targetResource": {
                            "id": item["id"],
                            "resourceType": item["type"],
                        },
                    }
                }
                for item in operations
            ]
            raw_operations.extend([
                *(copy.deepcopy(raw_operations[index]) for index in range(4)),
                {
                    "properties": {
                        "provisioningOperation": "EvaluateDeploymentOutput",
                        "provisioningState": "Succeeded",
                        "statusCode": "OK",
                        "targetResource": None,
                    }
                },
            ])
            managed = identity["managed_identity"]
            raw_managed = {
                "id": managed["id"],
                "name": managed["name"],
                "clientId": CLIENT_ID,
                "principalId": PRINCIPAL_ID,
                "tenantId": managed["tenant_id"],
            }
            raw_function_identity = {
                "type": "SystemAssigned, UserAssigned",
                "principalId": SYSTEM_PRINCIPAL_ID,
                "userAssignedIdentities": {
                    managed["id"]: {
                        "clientId": CLIENT_ID,
                        "principalId": PRINCIPAL_ID,
                    }
                },
            }
            storage = by_type["microsoft.storage/storageaccounts"]
            workspace = by_type["microsoft.operationalinsights/workspaces"]
            component = by_type["microsoft.insights/components"]
            plan = by_type["microsoft.web/serverfarms"]
            connection = "InstrumentationKey=synthetic"
            virtual_network = by_type.get("microsoft.network/virtualnetworks")
            properties = {
                "microsoft.managedidentity/userassignedidentities": {
                    "clientId": CLIENT_ID,
                    "principalId": PRINCIPAL_ID,
                    "tenantId": managed["tenant_id"],
                    "providerMetadata": "allowed",
                },
                **(
                    {
                        "microsoft.network/virtualnetworks": {
                            "addressSpace": {
                                "addressPrefixes": ["10.42.0.0/24"]
                            },
                            "subnets": [
                                {
                                    "id": (
                                        f"{virtual_network['id']}"
                                        "/subnets/snet-flex-integration"
                                    )
                                },
                                {
                                    "id": (
                                        f"{virtual_network['id']}"
                                        "/subnets/snet-private-endpoints"
                                    )
                                },
                            ],
                            "provisioningState": "Succeeded",
                        },
                        "microsoft.network/virtualnetworks/subnets": None,
                    }
                    if current and virtual_network is not None
                    else {}
                ),
                "microsoft.storage/storageaccounts": {
                    "accessTier": "Hot",
                    "allowBlobPublicAccess": False,
                    "allowCrossTenantReplication": False,
                    "allowSharedKeyAccess": False,
                    "defaultToOAuthAuthentication": True,
                    "minimumTlsVersion": "TLS1_2",
                    "publicNetworkAccess": "Enabled",
                    "supportsHttpsTrafficOnly": True,
                    "networkAcls": {
                        "bypass": "None", "defaultAction": "Allow",
                        "ipRules": [], "virtualNetworkRules": [],
                    },
                },
                "microsoft.storage/storageaccounts/blobservices": {
                    "deleteRetentionPolicy": {"enabled": False}
                },
                "microsoft.storage/storageaccounts/blobservices/containers": {
                    "publicAccess": "None"
                },
                "microsoft.operationalinsights/workspaces": {
                    "features": {
                        "disableLocalAuth": True,
                        "enableLogAccessUsingOnlyResourcePermissions": True,
                        "immediatePurgeDataOn30Days": True,
                    },
                    "publicNetworkAccessForIngestion": "Enabled",
                    "publicNetworkAccessForQuery": "Enabled",
                    "retentionInDays": 30,
                    "sku": {"name": "PerGB2018"},
                    "workspaceCapping": {"dailyQuotaGb": 1},
                },
                "microsoft.insights/components": {
                    "Application_Type": "web",
                    "ConnectionString": connection,
                    "DisableLocalAuth": True,
                    "IngestionMode": "LogAnalytics",
                    "RetentionInDays": 30,
                    "WorkspaceResourceId": workspace["id"],
                    "publicNetworkAccessForIngestion": "Enabled",
                    "publicNetworkAccessForQuery": "Enabled",
                },
                "microsoft.insights/components/currentbillingfeatures": {
                    "CurrentBillingFeatures": ["Basic"],
                    "DataVolumeCap": {
                        "Cap": 0.1,
                        "StopSendNotificationWhenHitCap": False,
                    },
                },
                "microsoft.web/serverfarms": {
                    "reserved": True, "zoneRedundant": False
                },
                "microsoft.web/sites": {
                    "clientAffinityEnabled": False,
                    "httpsOnly": True,
                    "publicNetworkAccess": "Enabled",
                    "serverFarmId": plan["id"],
                    "siteConfig": {
                        "alwaysOn": False,
                        "cors": {
                            "allowedOrigins": azure_live_commands._CORS_ALLOWED_ORIGINS,
                            "supportCredentials": False,
                        },
                        "ftpsState": "Disabled",
                        "healthCheckPath": "/healthz",
                        "http20Enabled": True,
                        "minTlsVersion": "1.2",
                        "remoteDebuggingEnabled": False,
                    },
                    "functionAppConfig": {
                        "deployment": {"storage": {
                            "authentication": {
                                "type": "UserAssignedIdentity",
                                "userAssignedIdentityResourceId": managed["id"],
                            },
                            "type": "blobContainer",
                            "value": (
                                f"https://{storage['name']}.blob.core.windows.net/"
                                "function-releases"
                            ),
                        }},
                        "runtime": {"name": "python", "version": "3.12"},
                        "scaleAndConcurrency": {
                            "instanceMemoryMB": 2048,
                            "maximumInstanceCount": 4,
                            "triggers": {"http": {"perInstanceConcurrency": 16}},
                        },
                    },
                },
                "microsoft.web/sites/config": {
                    "APPLICATIONINSIGHTS_AUTHENTICATION_STRING": (
                        f"ClientId={CLIENT_ID};Authorization=AAD"
                    ),
                    "APPLICATIONINSIGHTS_CONNECTION_STRING": connection,
                    "AzureWebJobsStorage__accountName": storage["name"],
                    "AzureWebJobsStorage__clientId": CLIENT_ID,
                    "AzureWebJobsStorage__credential": "managedidentity",
                    "M365_TENANT_ID": managed["tenant_id"],
                    "NAC_BFF_TENANT_ID": managed["tenant_id"],
                    "NAC_BFF_AUDIENCE": expectation["bff_api_audience"],
                    "NAC_BFF_REQUIRED_SCOPE": "Matter.Read",
                    "M365_RUNTIME_CLIENT_ID": CLIENT_ID,
                    "AZURE_CLIENT_ID": CLIENT_ID,
                },
            }
            details = []
            for operation in operations:
                resource_type = operation["type"]
                if resource_type == "microsoft.authorization/roleassignments":
                    role_id = (
                        azure_live_commands._STORAGE_BLOB_DATA_OWNER_ROLE_ID
                        if operation["id"].startswith(storage["id"].lower())
                        else azure_live_commands._MONITORING_METRICS_PUBLISHER_ROLE_ID
                    )
                    detail_properties = {
                        "principalId": PRINCIPAL_ID,
                        "principalType": "ServicePrincipal",
                        "roleDefinitionId": (
                            f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}/providers/"
                            f"Microsoft.Authorization/roleDefinitions/{role_id}"
                        ),
                    }
                else:
                    if resource_type == "microsoft.network/virtualnetworks/subnets":
                        is_integration = operation["id"].endswith(
                            "/subnets/snet-flex-integration"
                        )
                        detail_properties = {
                            "addressPrefix": (
                                "10.42.0.0/27"
                                if is_integration
                                else "10.42.0.32/27"
                            ),
                            "delegations": (
                                [{
                                    "name": "flex-consumption",
                                    "properties": {
                                        "serviceName": "Microsoft.App/environments"
                                    },
                                }]
                                if is_integration
                                else []
                            ),
                            "privateEndpointNetworkPolicies": (
                                "Enabled" if is_integration else "Disabled"
                            ),
                            "privateLinkServiceNetworkPolicies": "Enabled",
                            "provisioningState": "Succeeded",
                        }
                    else:
                        detail_properties = properties[resource_type]
                details.append({
                    "id": operation["id"],
                    "type": resource_type,
                    "properties": detail_properties,
                })
            from nac_bff.azure_interruption_contract import (
                resource_graph_visible_targets,
            )

            graph_rows = resource_graph_visible_targets(inventory, operations)
            assert graph_rows is not None
            graph = {
                "count": len(graph_rows),
                "data": graph_rows,
                "resultTruncated": "false",
                "totalRecords": len(graph_rows),
            }
            group_id = (
                f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}"
                "/resourceGroups/rg-nac-bff-test"
            )
            expected = [
                (("account", "show"), {
                    "environmentName": EXPECTED_CLOUD_NAME,
                    "tenantId": EXPECTED_TENANT_ID,
                    "id": EXPECTED_SUBSCRIPTION_ID,
                    "state": "Enabled",
                }),
                *[
                    (("provider", "show", "--namespace", namespace), {
                        "namespace": namespace,
                        "registrationState": "Registered",
                    })
                    for namespace in sorted(azure_live_commands._PROVIDER_NAMESPACES)
                ],
                (("group", "exists", "--name", "rg-nac-bff-test"), True),
                (("group", "show", "--name", "rg-nac-bff-test"), {
                    "id": group_id,
                    "name": "rg-nac-bff-test",
                    "location": "germanywestcentral",
                    "tags": {
                        "dataClassification": "no-production-data",
                        "environment": "test", "workload": "nac-bff",
                    },
                    "properties": {"provisioningState": "Succeeded"},
                }),
                (("resource", "list", "--resource-group", "rg-nac-bff-test"), raw_inventory),
                (("deployment", "group", "show", "--name", expectation["deployment_name"], "--resource-group", "rg-nac-bff-test"), raw_deployment),
                (("deployment", "operation", "group", "list", "--name", expectation["deployment_name"], "--resource-group", "rg-nac-bff-test"), raw_operations),
                (("resource", "show", "--resource-group", "rg-nac-bff-test", "--resource-type", azure_live_commands._SMART_DETECTION_ACTION_GROUP_TYPE, "--name", azure_live_commands._SMART_DETECTION_ACTION_GROUP_NAME, "--api-version", azure_live_commands._SMART_DETECTION_ACTION_GROUP_API_VERSION), smart_detail),
                (("identity", "show", "--name", managed["name"], "--resource-group", "rg-nac-bff-test"), raw_managed),
                (("functionapp", "identity", "show", "--name", azure_live_commands.FUNCTION_APP, "--resource-group", "rg-nac-bff-test"), raw_function_identity),
            ]
            for operation, detail in zip(operations, details, strict=True):
                command = azure_live_commands._resource_detail_read_command(operation)
                if operation["type"] == "microsoft.web/sites/config":
                    self.assertEqual(command, (
                        "rest", "--method", "post", "--url",
                        azure_live_commands._APP_SETTINGS_URL,
                    ))
                response = (
                    {"properties": detail["properties"]}
                    if operation["type"] == "microsoft.web/sites/config"
                    else detail
                )
                expected.append((command, response))
            expected.extend([
                (("rest", "--method", "post", "--url", azure_live_commands._RESOURCE_GRAPH_URL, "--body", azure_live_commands._RESOURCE_GRAPH_BODY), graph),
                (("resource", "list", "--resource-group", "rg-nac-bff-test"), raw_inventory),
                (("resource", "show", "--resource-group", "rg-nac-bff-test", "--resource-type", azure_live_commands._SMART_DETECTION_ACTION_GROUP_TYPE, "--name", azure_live_commands._SMART_DETECTION_ACTION_GROUP_NAME, "--api-version", azure_live_commands._SMART_DETECTION_ACTION_GROUP_API_VERSION), smart_detail),
            ])

            class FakeAzure:
                def __init__(self, calls):
                    self.calls = list(calls)

                def run(self, argv):
                    expected_command, response = self.calls.pop(0)
                    if tuple(argv) != expected_command:
                        raise AssertionError((tuple(argv), expected_command))
                    command, _family, code = azure_live_commands._validated_command(argv)
                    if command is None or code != "AZURE_CLI_OK":
                        raise AssertionError((argv, code))
                    return {"ok": True, "code": "AZURE_CLI_OK", "data": response}

            azure = FakeAzure(expected)
            result = AzureCliInterruptionObservationPort(
                azure, preflight=lambda: None
            ).observe_ensure_resource_group(
                tenant_id=EXPECTED_TENANT_ID,
                subscription_id=EXPECTED_SUBSCRIPTION_ID,
                resource_group="rg-nac-bff-test",
                baseline_expectation=expectation,
            )

            self.assertEqual(azure.calls, [])
            self.assertEqual(
                result["deployment"]["bff_api_audience"],
                "33333333-3333-4333-8333-333333333333",
            )
            self.assertNotEqual(
                result["deployment"]["bff_api_audience"], CLIENT_ID
            )
            self.assertEqual(
                result["deployment"]["template_hash"],
                (
                    CURRENT_AZURE_TEMPLATE_HASH
                    if current
                    else LEGACY_AZURE_TEMPLATE_HASH
                ),
            )
            self.assertEqual(result["deployment"]["mode"], "Incremental")
            self.assertEqual(
                set(result["deployment"]["outputs"]),
                ({
                    "function_app_resource_id",
                    "function_app_host_name",
                    "function_app_system_assigned_principal_id",
                    "virtual_network_resource_id",
                    "function_integration_subnet_resource_id",
                    "private_endpoint_subnet_resource_id",
                    "managed_identity_resource_id",
                    "managed_identity_client_id",
                    "managed_identity_principal_id",
                } if current else {
                    "function_app_resource_id",
                    "function_app_host_name",
                    "function_app_system_assigned_principal_id",
                    "managed_identity_resource_id",
                    "managed_identity_client_id",
                    "managed_identity_principal_id",
                }),
            )
            self.assertTrue(result["live_resource_state"]["security_properties_exact"])

    def test_exact_resource_graph_rejects_visible_target_drift(self) -> None:
        from nac_bff.azure_interruption_contract import (
            resource_graph_visible_targets,
        )
        from tests.test_nac_bff_azure_interruption_baseline import (
            _inventory,
            _operations,
        )

        inventory = _inventory()
        operations = _operations()
        expected = resource_graph_visible_targets(inventory, operations)
        assert expected is not None
        azure_live_commands._require_exact_resource_graph(
            expected, inventory, operations
        )

        for drifted in (
            expected[:-1],
            [
                *expected,
                {
                    "id": (
                        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c"
                        "/resourcegroups/rg-nac-bff-test/providers/test/extra/one"
                    ),
                    "type": "test/extra",
                },
            ],
            [*expected, copy.deepcopy(expected[0])],
            [
                {**expected[0], "type": "test/drifted"},
                *expected[1:],
            ],
        ):
            with self.assertRaisesRegex(
                ValueError,
                "AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID",
            ):
                azure_live_commands._require_exact_resource_graph(
                    drifted, inventory, operations
                )

    def test_interruption_operation_projection_rejects_unsafe_metadata(self) -> None:
        valid = {
            "properties": {
                "provisioningOperation": "EvaluateDeploymentOutput",
                "provisioningState": "Succeeded",
                "statusCode": "OK",
                "targetResource": None,
            }
        }
        invalid_rows = (
            {"properties": {**valid["properties"], "provisioningState": "Failed"}},
            {"properties": {**valid["properties"], "provisioningOperation": "Create"}},
            {"properties": {**valid["properties"], "statusCode": "Accepted"}},
        )
        for row in invalid_rows:
            with self.subTest(row=row):
                with self.assertRaisesRegex(
                    ValueError,
                    "AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID",
                ):
                    azure_live_commands._interruption_operation_projection([row])
        with self.assertRaisesRegex(
            ValueError,
            "AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID",
        ):
            azure_live_commands._interruption_operation_projection([valid, valid])

        targeted = {
            "properties": {
                "provisioningState": "Succeeded",
                "targetResource": {
                    "id": "/subscriptions/test/providers/Test/items/one",
                    "resourceType": "Test/items",
                },
            }
        }
        for field, value in (("id", None), ("id", 1), ("resourceType", [])):
            malformed = copy.deepcopy(targeted)
            malformed["properties"]["targetResource"][field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    "AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID",
                ):
                    azure_live_commands._interruption_operation_projection([
                        malformed
                    ])

    def test_interruption_operation_projection_deduplicates_only_exact_targets(self) -> None:
        operation = {
            "properties": {
                "provisioningState": "Succeeded",
                "targetResource": {
                    "id": "/subscriptions/test/resourceGroups/test/providers/Test/items/one",
                    "resourceType": "Test/items",
                },
            }
        }
        self.assertEqual(
            azure_live_commands._interruption_operation_projection([
                operation,
                copy.deepcopy(operation),
            ]),
            [{
                "id": operation["properties"]["targetResource"]["id"].lower(),
                "type": "test/items",
                "provisioning_state": "Succeeded",
            }],
        )
        conflicting = copy.deepcopy(operation)
        conflicting["properties"]["targetResource"]["resourceType"] = (
            "Test/otherItems"
        )
        projected = azure_live_commands._interruption_operation_projection([
            operation,
            conflicting,
        ])
        self.assertEqual(len(projected), 2)

        failed = copy.deepcopy(operation)
        failed["properties"]["provisioningState"] = "Failed"
        with self.assertRaisesRegex(
            ValueError,
            "AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID",
        ):
            azure_live_commands._interruption_operation_projection([
                operation,
                failed,
            ])

    def test_interruption_observation_uses_only_exact_read_commands(self) -> None:
        calls: list[tuple[str, ...]] = []
        preflight = Mock()
        group_id = (
            f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}"
            "/resourceGroups/rg-nac-bff-test"
        )

        class FakeAzure:
            def run(self, argv):
                command = tuple(argv)
                calls.append(command)
                if command == ("account", "show"):
                    data = {
                        "environmentName": EXPECTED_CLOUD_NAME,
                        "tenantId": EXPECTED_TENANT_ID,
                        "id": EXPECTED_SUBSCRIPTION_ID,
                        "state": "Enabled",
                    }
                elif command[:2] == ("provider", "show"):
                    data = {
                        "namespace": command[-1],
                        "registrationState": "Registered",
                    }
                elif command[:2] == ("group", "exists"):
                    data = True
                elif command[:2] == ("group", "show"):
                    data = {
                        "id": group_id,
                        "name": "rg-nac-bff-test",
                        "location": "germanywestcentral",
                        "tags": {
                            "workload": "nac-bff",
                            "environment": "test",
                            "dataClassification": "no-production-data",
                        },
                        "properties": {"provisioningState": "Succeeded"},
                    }
                else:
                    data = []
                return {"ok": True, "code": "AZURE_CLI_OK", "data": data}

        result = AzureCliInterruptionObservationPort(
            FakeAzure(), preflight=preflight
        ).observe_ensure_resource_group(
            tenant_id=EXPECTED_TENANT_ID,
            subscription_id=EXPECTED_SUBSCRIPTION_ID,
            resource_group="rg-nac-bff-test",
        )

        self.assertEqual(
            calls,
            [
                ("account", "show"),
                ("provider", "show", "--namespace", "Microsoft.OperationalInsights"),
                ("provider", "show", "--namespace", "Microsoft.Storage"),
                ("provider", "show", "--namespace", "Microsoft.Web"),
                ("group", "exists", "--name", "rg-nac-bff-test"),
                ("group", "show", "--name", "rg-nac-bff-test"),
                ("resource", "list", "--resource-group", "rg-nac-bff-test"),
            ],
        )
        self.assertEqual(preflight.call_count, len(calls))
        self.assertEqual(preflight.call_count, 7)
        self.assertEqual(result["tenant_id"], EXPECTED_TENANT_ID)
        self.assertEqual(
            result["providers"],
            {
                "Microsoft.OperationalInsights": "Registered",
                "Microsoft.Storage": "Registered",
                "Microsoft.Web": "Registered",
            },
        )
        self.assertEqual(result["resource_groups"][0]["provisioning_state"], "Succeeded")
        self.assertEqual(result["resource_inventory"], [])
        self.assertEqual(
            set(result),
            {
                "tenant_id", "subscription_id", "providers",
                "resource_groups", "resource_inventory",
            },
        )
        self.assertNotIn("secret", json.dumps(result))
        from nac_bff.azure_activation_runner import _sha256_json
        self.assertEqual(
            _sha256_json(result),
            "6f34f2ec265462edf25a295c9dbab5363a0252b1d7a50e5c1e81459c8d9db850",
        )

    def test_interruption_observation_rejects_write_command_before_adapter(self) -> None:
        azure = Mock()
        preflight = Mock()
        port = AzureCliInterruptionObservationPort(azure, preflight=preflight)

        with self.assertRaisesRegex(
            ValueError, "AZURE_INTERRUPTION_READ_COMMAND_FORBIDDEN"
        ):
            port._read(
                ("deployment", "group", "create"), dict
            )

        azure.run.assert_not_called()
        preflight.assert_not_called()

    def test_interruption_resource_detail_reads_are_target_and_api_bound(self) -> None:
        resource_id = (
            f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}"
            "/resourceGroups/rg-nac-bff-test/providers/"
            "Microsoft.Storage/storageAccounts/stnacbff43o765p7uslni"
            "/blobServices/default/containers/function-releases"
        )
        command, family, code = azure_live_commands._validated_command((
            "resource", "show", "--ids", resource_id,
            "--api-version", "2023-05-01",
        ))
        self.assertEqual(code, "AZURE_CLI_OK")
        self.assertEqual(family, ("resource", "show"))
        self.assertIsNotNone(command)
        for candidate in (
            (
                "resource", "show", "--ids",
                resource_id.replace("rg-nac-bff-test", "foreign"),
                "--api-version", "2023-05-01",
            ),
            (
                "resource", "show", "--ids", resource_id,
                "--api-version", "2024-04-01",
            ),
        ):
            blocked, _family, blocked_code = (
                azure_live_commands._validated_command(candidate)
            )
            self.assertIsNone(blocked)
            self.assertEqual(blocked_code, "AZURE_CLI_COMMAND_BLOCKED")

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
    state: str | None = "Enabled",
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
                    **({"state": state} if state is not None else {}),
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
