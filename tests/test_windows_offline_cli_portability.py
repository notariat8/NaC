from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
import urllib.request
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


PLATFORM_ERROR_CODE = "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"
LIVE_COMMANDS = (
    "bff-azure-activate-live",
    "bff-azure-activation-recovery",
    "bff-azure-activation-interruption-reconcile",
    "bff-azure-function-deployment-reconcile",
)
FORBIDDEN_SIDE_EFFECT_CATEGORIES = (
    "credential",
    "state",
    "lock",
    "subprocess",
    "network",
    "tenant",
    "provider",
)


class WindowsOfflineCliPortabilityTests(unittest.TestCase):
    def test_issue748_cli_surfaces_are_native_offline_and_fail_closed(self) -> None:
        for command in (
            "current-state-access-diagnostic-preflight",
            "current-state-access-diagnostic-run-read-only",
            "current-state-access-client-receipt-stage",
        ):
            with self.subTest(command=command):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(REPO_ROOT / "scripts" / "nac.py"),
                        "m365",
                        "teams-sharepoint",
                        command,
                        "--format",
                        "json",
                    ],
                    cwd=REPO_ROOT,
                    env={**os.environ, "PYTHONPATH": str(SRC_ROOT)},
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], "BLOCKED")
                self.assertEqual(payload.get("provider_ports_created", 0), 0)
                self.assertEqual(payload["network_reads"], 0)
                self.assertEqual(payload["credential_writes"], 0)

        for module in (
            "current_state_access_diagnostic.py",
            "current_state_access_gate.py",
            "current_state_access_ports.py",
            "current_state_access_adapters.py",
            "current_state_access_composition.py",
        ):
            source = (REPO_ROOT / "src" / "nac_bff" / module).read_text(
                encoding="utf-8"
            )
            self.assertNotIn("import fcntl", source)
            self.assertNotIn("/proc/", source)
            self.assertNotIn("issue746_reconciliation_gate", source)

    def _synthetic_environment(self, root: Path) -> dict[str, str]:
        return {
            "PATH": str(Path(sys.executable).parent),
            "PYTHONPATH": str(SRC_ROOT),
            "HOME": str(root / "home"),
            "USERPROFILE": str(root / "profile"),
            "APPDATA": str(root / "appdata"),
            "LOCALAPPDATA": str(root / "localappdata"),
            "NAC_TEST_FIXTURE_CLASSIFICATION": "synthetic-only",
        }

    def _install_child_guards(self, root: Path) -> Path:
        guard_root = root / "guards"
        guard_root.mkdir(parents=True)
        (guard_root / "sitecustomize.py").write_text(
            """import atexit
import builtins
import io
import json
import os
import socket
import subprocess
import urllib.request

_blocked_roots = tuple(
    os.path.normcase(os.path.abspath(value))
    for key in (\"HOME\", \"USERPROFILE\", \"APPDATA\", \"LOCALAPPDATA\")
    if (value := os.environ.get(key))
)
_real_open = builtins.open
_real_os_open = os.open
_real_import = builtins.__import__
_trace_path = os.environ.get("NAC_TEST_IMPORT_TRACE")

def _reject_private_path(path):
    try:
        candidate = os.path.normcase(os.path.abspath(os.fspath(path)))
    except TypeError:
        return
    if any(candidate == root or candidate.startswith(root + os.sep) for root in _blocked_roots):
        raise AssertionError(\"credential-or-state-access\")

def guarded_open(path, *args, **kwargs):
    _reject_private_path(path)
    return _real_open(path, *args, **kwargs)

def guarded_os_open(path, *args, **kwargs):
    _reject_private_path(path)
    return _real_os_open(path, *args, **kwargs)

def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
    if name in {\"nac_bff.azure_activation_runner\", \"nac_bff.azure_activation_composition\"}:
        raise AssertionError(\"live-backend-import\")
    return _real_import(name, globals, locals, fromlist, level)

def blocked(*args, **kwargs):
    raise AssertionError(\"network-or-subprocess-access\")

def write_import_trace():
    if _trace_path:
        with _real_open(_trace_path, \"w\", encoding=\"utf-8\") as stream:
            json.dump(sorted(sys.modules), stream)

builtins.open = guarded_open
io.open = guarded_open
os.open = guarded_os_open
builtins.__import__ = guarded_import
subprocess.run = blocked
subprocess.Popen = blocked
socket.create_connection = blocked
urllib.request.urlopen = blocked
import sys
atexit.register(write_import_trace)
""",
            encoding="utf-8",
        )
        return guard_root

    def _guarded_child_environment(self, root: Path) -> dict[str, str]:
        environment = self._synthetic_environment(root)
        guard_root = self._install_child_guards(root)
        sentinel_path = root / "sentinel-path"
        sentinel_path.mkdir()
        for executable in ("az.cmd", "gh.cmd", "m365.cmd"):
            (sentinel_path / executable).write_text(
                "@echo forbidden-executable-access 1>&2\r\n@exit /b 97\r\n",
                encoding="utf-8",
            )
        environment["PATH"] = str(sentinel_path)
        environment["PYTHONPATH"] = os.pathsep.join((str(guard_root), str(SRC_ROOT)))
        environment["NAC_TEST_IMPORT_TRACE"] = str(root / "import-trace.json")
        environment.update(
            {
                "AZURE_CONFIG_DIR": str(root / "home" / "azure"),
                "GH_CONFIG_DIR": str(root / "home" / "github"),
                "M365_CONFIG_DIR": str(root / "home" / "m365"),
                "NAC_PLATFORM": "linux",
                "NAC_OS_NAME": "posix",
                "NAC_PLATFORM_SECURITY_BACKEND": "enabled",
                "NAC_ALLOW_WINDOWS_LIVE": "1",
                "NAC_CONFIG_PLATFORM": "linux",
                "OS": "linux",
            }
        )
        return environment

    def _assert_child_import_trace_is_offline(self, environment: dict[str, str]) -> None:
        trace_path = Path(environment["NAC_TEST_IMPORT_TRACE"])
        imported_modules = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertNotIn("nac_bff.azure_activation_runner", imported_modules)
        self.assertNotIn("nac_bff.azure_activation_composition", imported_modules)
        self.assertNotIn("fcntl", imported_modules)
        self.assertNotIn("pwd", imported_modules)

    def test_portable_modules_import_without_posix_backend(self) -> None:
        probe = """
import sys
import nac_cli.cli
import nac_m365_graph.business_case_type_production_adapters
from nac_bff import azure_activation_contract, azure_activation_facade

assert "nac_bff.azure_activation_runner" not in sys.modules
assert azure_activation_contract.PLATFORM_SECURITY_BACKEND_UNAVAILABLE == "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"
assert callable(azure_activation_facade.platform_blocked_payload)
"""
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(SRC_ROOT)
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=REPO_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_platform_payload_is_exact_and_redacted(self) -> None:
        from nac_bff.azure_activation_facade import platform_blocked_payload

        payload = platform_blocked_payload()
        self.assertEqual(
            payload,
            {
                "schema_version": "nac.platform-security-boundary/v0.1",
                "status": "BLOCKED",
                "error": {"code": PLATFORM_ERROR_CODE},
                "writes_started": False,
            },
        )
        serialized = json.dumps(payload, sort_keys=True).lower()
        for unsafe_key in ("path", "sid", "login", "token", "environment", "provider"):
            self.assertNotIn(unsafe_key, serialized)

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_help_smokes_run_with_isolated_synthetic_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            synthetic_root = Path(temporary_directory)
            environment = self._guarded_child_environment(synthetic_root)
            for arguments in (
                ("--help",),
                ("m365", "--help"),
                ("m365", "teams-sharepoint", "--help"),
            ):
                with self.subTest(arguments=arguments):
                    result = subprocess.run(
                        [sys.executable, str(REPO_ROOT / "scripts" / "nac.py"), *arguments],
                        cwd=REPO_ROOT,
                        env=environment,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self._assert_child_import_trace_is_offline(environment)

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_child_guards_reject_pathlib_and_nested_python_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            synthetic_root = Path(temporary_directory)
            environment = self._guarded_child_environment(synthetic_root)
            probe = """
import os
from pathlib import Path
import subprocess
import sys

try:
    Path(os.environ["HOME"], "credential.json").read_text(encoding="utf-8")
except AssertionError:
    pass
else:
    raise AssertionError("pathlib-guard-bypassed")

try:
    subprocess.run([sys.executable, "-c", "print('nested')"], check=False)
except AssertionError:
    pass
else:
    raise AssertionError("subprocess-guard-bypassed")
"""
            result = subprocess.run(
                [sys.executable, "-c", probe],
                cwd=REPO_ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self._assert_child_import_trace_is_offline(environment)

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_offline_m365_commands_use_only_synthetic_repo_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            environment = self._guarded_child_environment(Path(temporary_directory))
            for command in ("validate", "plan", "bpmn-viewer-plan"):
                with self.subTest(command=command):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(REPO_ROOT / "scripts" / "nac.py"),
                            "m365",
                            "teams-sharepoint",
                            command,
                            "--format",
                            "json",
                        ],
                        cwd=REPO_ROOT,
                        env=environment,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)["status"], "PASSED")
                    self._assert_child_import_trace_is_offline(environment)

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_live_edges_require_bound_inputs_before_backends(self) -> None:
        windows_block_codes = {
            "bff-azure-activate-live": "ISSUE746_WINDOWS_LIVE_ACCESS_BLOCKED",
            "bff-azure-activation-recovery": "ISSUE746_WINDOWS_RECOVERY_ACCESS_BLOCKED",
        }
        for command in LIVE_COMMANDS:
            with self.subTest(command=command):
                stdout = StringIO()
                from nac_cli import cli
                if command in {
                    "bff-azure-activation-interruption-reconcile",
                    "bff-azure-function-deployment-reconcile",
                }:
                    with self.assertRaises(SystemExit):
                        with redirect_stdout(stdout):
                            cli.main(
                                ["m365", "teams-sharepoint", command, "--format", "json"]
                            )
                    continue
                with redirect_stdout(stdout):
                    result = cli.main(
                        ["m365", "teams-sharepoint", command, "--format", "json"]
                    )
                self.assertEqual(result, 2)
                self.assertEqual(
                    json.loads(stdout.getvalue())["error"],
                    {"code": windows_block_codes[command]},
                )

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_github_adapter_rejects_unbound_binary_before_process_access(self) -> None:
        from nac_m365_graph.business_case_type_production_adapters import (
            GhCliIssueCommentPort,
        )

        runner = unittest.mock.Mock(side_effect=AssertionError("subprocess"))
        with self.assertRaisesRegex(ValueError, "github_cli_binding_invalid"):
            GhCliIssueCommentPort(
                binary=Path("C:/synthetic/gh.exe"),
                expected_binary_sha256="0" * 64,
                runner=runner,
            )
        runner.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_python_live_facade_blocks_all_side_effect_categories(self) -> None:
        from nac_bff import azure_activation_facade as facade
        from nac_bff.azure_activation_contract import ActivationStepError

        edges = (
            facade.run_azure_bff_live_activation,
            facade.reconcile_azure_bff_live_activation_lock,
            facade.build_live_activation_execution_port,
            facade.build_interruption_reconciliation_ports,
            facade.build_function_deployment_reconciliation_ports,
        )
        guards = {
            category: unittest.mock.Mock(name=category)
            for category in FORBIDDEN_SIDE_EFFECT_CATEGORIES
        }

        def touch_all_side_effects(*args, **kwargs):
            for guard in guards.values():
                guard()
            return {"status": "SYNTHETIC"}

        fake_runner = types.ModuleType("nac_bff.azure_activation_runner")
        fake_runner.run_azure_bff_live_activation = touch_all_side_effects
        fake_runner.reconcile_azure_bff_live_activation_lock = touch_all_side_effects
        fake_composition = types.ModuleType("nac_bff.azure_activation_composition")
        fake_composition.build_live_activation_execution_port = touch_all_side_effects
        fake_composition.build_interruption_reconciliation_ports = touch_all_side_effects
        fake_composition.build_function_deployment_reconciliation_ports = touch_all_side_effects
        with patch.dict(
            sys.modules,
            {
                "nac_bff.azure_activation_runner": fake_runner,
                "nac_bff.azure_activation_composition": fake_composition,
            },
        ), patch.object(
            facade,
            "require_platform_security_backend",
            side_effect=ActivationStepError(PLATFORM_ERROR_CODE),
        ):
            for edge in edges:
                with self.subTest(edge=edge.__name__):
                    with self.assertRaisesRegex(
                        ActivationStepError, PLATFORM_ERROR_CODE
                    ):
                        edge()
        for guard in guards.values():
            guard.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_live_child_ignores_forged_platform_hints_before_all_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            synthetic_root = Path(temporary_directory)
            environment = self._guarded_child_environment(synthetic_root)
            for command in LIVE_COMMANDS[:2]:
                with self.subTest(command=command):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(REPO_ROOT / "scripts" / "nac.py"),
                            "m365",
                            "teams-sharepoint",
                            command,
                            "--platform",
                            "linux",
                            "--format",
                            "json",
                        ],
                        cwd=REPO_ROOT,
                        env=environment,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(
                        json.loads(result.stdout)["error"],
                        {
                            "code": (
                                "ISSUE746_WINDOWS_LIVE_ACCESS_BLOCKED"
                                if command == "bff-azure-activate-live"
                                else "ISSUE746_WINDOWS_RECOVERY_ACCESS_BLOCKED"
                            )
                        },
                    )
                    self._assert_child_import_trace_is_offline(environment)

    @unittest.skipUnless(os.name == "nt", "native Windows contract")
    def test_windows_execution_surfaces_fail_closed_on_unbound_inputs(self) -> None:
        from nac_bff.azure_activation_attestations import (
            build_activation_attestation_plan,
        )
        from nac_bff.azure_live_commands import run_azure_cli
        from nac_bff.azure_live_commands_win import launch_in_job_object
        from nac_bff.activation_security_backend import SecurityBoundaryError

        attestation = build_activation_attestation_plan(
            provisioner_certificate_path=Path("C:/synthetic/public.crt")
        )
        self.assertEqual(attestation["status"], "NOT_READY")
        self.assertNotEqual(attestation["error"], {"code": PLATFORM_ERROR_CODE})
        self.assertFalse(attestation["reads_private_key"])
        self.assertFalse(attestation["executes_provider_requests"])
        azure_result = run_azure_cli(("account", "show"))
        self.assertNotEqual(azure_result["code"], PLATFORM_ERROR_CODE)
        with self.assertRaisesRegex(
            SecurityBoundaryError, "^PROCESS_SPEC_REQUIRED$"
        ):
            launch_in_job_object()

    def test_contract_names_all_forbidden_side_effect_categories(self) -> None:
        self.assertEqual(
            FORBIDDEN_SIDE_EFFECT_CATEGORIES,
            (
                "credential",
                "state",
                "lock",
                "subprocess",
                "network",
                "tenant",
                "provider",
            ),
        )


if __name__ == "__main__":
    unittest.main()
