from __future__ import annotations

import os
import json
from pathlib import Path
import sys
import tempfile
import unittest
import ctypes
import shutil
from ctypes import wintypes

from nac_bff.activation_security_backend import ProcessSpec, SecurityBoundaryError
from nac_bff.activation_security_windows import WindowsActivationSecurityBackend
from nac_m365_graph.mvp_test_environment_deploy import M365CliCommandRunner
from nac_m365_graph.node_runtime_integrity import build_node_runtime_manifest


@unittest.skipUnless(os.name == "nt", "native Windows security contract")
class WindowsActivationSecurityBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = WindowsActivationSecurityBackend()

    def test_private_file_is_measured_from_bound_handle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            payload = b'{"synthetic":true}\n'
            path.write_bytes(payload)

            snapshot = self.backend.inspect_private_path(path, purpose="test")

            self.assertEqual(snapshot.size, len(payload))
            self.assertFalse(snapshot.reparse_point)
            self.assertRegex(snapshot.sha256, r"^[0-9a-f]{64}$")
            self.assertRegex(snapshot.path_sha256, r"^[0-9a-f]{64}$")
            self.assertRegex(snapshot.owner_sid_sha256, r"^[0-9a-f]{64}$")
            self.assertRegex(snapshot.dacl_sha256, r"^[0-9a-f]{64}$")
            self.assertGreater(snapshot.file_id, 0)
            self.assertGreater(snapshot.volume_serial, 0)

            with self.backend.open_bound_read(path, snapshot) as stream:
                self.assertEqual(stream.read(), payload)

    def test_relative_path_is_rejected_before_open(self) -> None:
        with self.assertRaisesRegex(SecurityBoundaryError, "PATH_NOT_ABSOLUTE"):
            self.backend.inspect_private_path(Path("relative.txt"), purpose="test")

    def test_reparse_point_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.txt"
            link = root / "link.txt"
            target.write_text("synthetic", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as error:
                self.skipTest(f"symlink creation unavailable: {error.winerror}")
            with self.assertRaisesRegex(SecurityBoundaryError, "REPARSE_POINT_REJECTED"):
                self.backend.inspect_private_path(link, purpose="test")

    def test_broad_write_dacl_is_rejected(self) -> None:
        advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        convert = advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
        convert.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.LPVOID),
            ctypes.POINTER(wintypes.DWORD),
        )
        convert.restype = wintypes.BOOL
        set_security = advapi32.SetFileSecurityW
        set_security.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.LPVOID)
        set_security.restype = wintypes.BOOL
        descriptor = wintypes.LPVOID()
        size = wintypes.DWORD()
        self.assertTrue(
            convert("D:P(A;;GA;;;WD)", 1, ctypes.byref(descriptor), ctypes.byref(size))
        )
        try:
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "broad.txt"
                path.write_text("synthetic", encoding="utf-8")
                self.assertTrue(set_security(str(path), 0x00000004, descriptor))
                with self.assertRaisesRegex(SecurityBoundaryError, "FILE_DACL_TOO_BROAD"):
                    self.backend.inspect_private_path(path, purpose="test")
        finally:
            kernel32.LocalFree(descriptor)

    def test_binding_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text("first", encoding="utf-8")
            snapshot = self.backend.inspect_private_path(path, purpose="test")
            path.write_text("second", encoding="utf-8")
            with self.assertRaisesRegex(SecurityBoundaryError, "FILE_BINDING_MISMATCH"):
                with self.backend.open_bound_read(path, snapshot):
                    self.fail("drifted binding must not be readable")

    def test_named_mutex_retains_handle_and_detects_contention(self) -> None:
        target = "0" * 64
        first = self.backend.acquire_run_lock(target)
        self.assertEqual(first.status, "normal")
        try:
            with self.assertRaisesRegex(SecurityBoundaryError, "RUN_LOCK_HELD"):
                self.backend.acquire_run_lock(target)
        finally:
            first.close()

    def test_attested_process_is_assigned_before_resume(self) -> None:
        executable = Path(sys.executable).resolve()
        executable_hash = self.backend.inspect_private_path(
            executable, purpose="test-executable"
        ).sha256
        result = self.backend.launch_attested_process(
            ProcessSpec(
                executable=executable,
                arguments=("-c", "print('synthetic')"),
                cwd=Path.cwd().resolve(),
                environment={
                    "SystemRoot": os.environ["SystemRoot"],
                    "TEMP": tempfile.gettempdir(),
                    "PYTHONUTF8": "1",
                },
                executable_sha256=executable_hash,
            )
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout.strip(), b"synthetic")
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.image_sha256, executable_hash)
        self.assertTrue(result.job_object_assigned)

    def test_process_hash_drift_blocks_before_launch(self) -> None:
        with self.assertRaisesRegex(SecurityBoundaryError, "PROCESS_IMAGE_MISMATCH"):
            self.backend.launch_attested_process(
                ProcessSpec(
                    executable=Path(sys.executable).resolve(),
                    arguments=("-c", "raise SystemExit(99)"),
                    cwd=Path.cwd().resolve(),
                    environment={"SystemRoot": os.environ["SystemRoot"]},
                    executable_sha256="0" * 64,
                )
            )

    def test_credential_guard_blocks_profile_write_before_resume(self) -> None:
        executable = Path(sys.executable).resolve()
        executable_hash = self.backend.inspect_private_path(
            executable, purpose="test-executable"
        ).sha256
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "credential-cache.json"
            script = (
                "from pathlib import Path\n"
                f"p = Path({str(destination)!r})\n"
                "try:\n"
                "    p.write_text('forbidden', encoding='utf-8')\n"
                "except PermissionError:\n"
                "    print('BLOCKED')\n"
                "else:\n"
                "    print('WRITTEN')\n"
            )
            result = self.backend.launch_attested_process(
                ProcessSpec(
                    executable=executable,
                    arguments=("-c", script),
                    cwd=Path.cwd().resolve(),
                    environment={
                        "SystemRoot": os.environ["SystemRoot"],
                        "TEMP": tempfile.gettempdir(),
                        "PYTHONUTF8": "1",
                    },
                    executable_sha256=executable_hash,
                    credential_write_guard=True,
                )
            )
            self.assertEqual(result.stdout.strip(), b"BLOCKED")
            self.assertFalse(destination.exists())

    def test_loader_failure_is_redacted_without_interactive_error_mode(self) -> None:
        executable = Path(sys.executable).resolve()
        executable_hash = self.backend.inspect_private_path(
            executable, purpose="test-executable"
        ).sha256
        with self.assertRaisesRegex(
            SecurityBoundaryError, "PROCESS_EXIT_CODE_REJECTED"
        ):
            self.backend.launch_attested_process(
                ProcessSpec(
                    executable=executable,
                    arguments=("-c", "raise SystemExit(17)"),
                    cwd=Path.cwd().resolve(),
                    environment={"SystemRoot": os.environ["SystemRoot"]},
                    executable_sha256=executable_hash,
                    allowed_exit_codes=(0,),
                )
            )

    def test_node_permission_guard_blocks_cache_write(self) -> None:
        resolved = shutil.which("node")
        if resolved is None:
            self.skipTest("Node is unavailable")
        executable = Path(resolved).resolve()
        executable_hash = self.backend.inspect_private_path(
            executable, purpose="toolchain-executable"
        ).sha256
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "m365-cache.json"
            script = (
                "const fs=require('node:fs');"
                f"try{{fs.writeFileSync({str(destination)!r},'forbidden');"
                "console.log('WRITTEN')}catch(e){console.log(e.code)}"
            )
            result = self.backend.launch_attested_process(
                ProcessSpec(
                    executable=executable,
                    arguments=(
                        "--permission",
                        "--allow-fs-read=*",
                        "-e",
                        script,
                    ),
                    cwd=Path.cwd().resolve(),
                    environment={"SystemRoot": os.environ["SystemRoot"]},
                    executable_sha256=executable_hash,
                    allowed_exit_codes=(0,),
                )
            )
            self.assertEqual(result.exit_code, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), b"ERR_ACCESS_DENIED")
            self.assertFalse(destination.exists())

    def test_node_permission_guard_is_inherited_by_allowed_worker(self) -> None:
        resolved = shutil.which("node")
        if resolved is None:
            self.skipTest("Node is unavailable")
        executable = Path(resolved).resolve()
        executable_hash = self.backend.inspect_private_path(
            executable, purpose="toolchain-executable"
        ).sha256
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            destination = root / "worker-cache.json"
            worker = root / "worker.cjs"
            worker.write_text(
                "const {parentPort}=require('node:worker_threads');"
                "const fs=require('node:fs');"
                f"try{{fs.writeFileSync({str(destination)!r},'forbidden');"
                "parentPort.postMessage('WRITTEN')}"
                "catch(e){parentPort.postMessage(e.code)}",
                encoding="utf-8",
            )
            script = (
                "const {Worker}=require('node:worker_threads');"
                f"const worker=new Worker({str(worker)!r});"
                "worker.once('message',value=>console.log(value));"
                "worker.once('error',error=>{console.error(error.code||error.message);"
                "process.exitCode=2});"
            )
            result = self.backend.launch_attested_process(
                ProcessSpec(
                    executable=executable,
                    arguments=(
                        "--permission",
                        "--allow-fs-read=*",
                        "--allow-worker",
                        "-e",
                        script,
                    ),
                    cwd=Path.cwd().resolve(),
                    environment={"SystemRoot": os.environ["SystemRoot"]},
                    executable_sha256=executable_hash,
                    allowed_exit_codes=(0,),
                )
            )
            self.assertEqual(result.exit_code, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), b"ERR_ACCESS_DENIED")
            self.assertFalse(destination.exists())

    def test_m365_runner_is_windows_native_and_credential_write_free(self) -> None:
        resolved = shutil.which("node")
        if resolved is None:
            self.skipTest("Node is unavailable")
        node = Path(resolved).resolve()
        node_sha256 = self.backend.inspect_private_path(
            node, purpose="toolchain-executable"
        ).sha256
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "m365-runtime"
            entrypoint = runtime / "dist" / "index.js"
            entrypoint.parent.mkdir(parents=True)
            home = root / "m365-home"
            home.mkdir()
            cache = home / "refreshed-token.json"
            entrypoint.write_text(
                "const fs=require('node:fs');"
                f"let blocked=false;try{{fs.writeFileSync({str(cache)!r},'x')}}"
                "catch(e){blocked=e.code==='ERR_ACCESS_DENIED'};"
                "console.log(JSON.stringify({"
                "connectedAs:'ofunk@funktion8.de',"
                "appId:'c86dded6-9723-4b8d-91f2-e0fd70e25839',"
                "appTenant:'870c862b-56f7-4c9b-b0d9-f1f7d32c835c',"
                "cloudType:'Public',writeBlocked:blocked}));",
                encoding="utf-8",
            )
            runtime_sha256 = build_node_runtime_manifest(runtime).digest
            runner = M365CliCommandRunner(
                binary=entrypoint,
                home=home,
                node_bin=node,
                expected_binary_sha256=runtime_sha256,
                expected_node_sha256=node_sha256,
                environ={},
            )
            result = runner.run(("m365", "status", "--output", "json"))
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["writeBlocked"])
            self.assertTrue(runner.check_readiness())
            self.assertFalse(cache.exists())


if __name__ == "__main__":
    unittest.main()
