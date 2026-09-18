from __future__ import annotations

import os
import json
from pathlib import Path
import tempfile
import unittest

if os.name != "nt":
    raise unittest.SkipTest("native Windows security contract")

import ctypes
import shutil
import subprocess
import time
from contextlib import contextmanager
from ctypes import wintypes
from unittest.mock import patch

from nac_bff import activation_security_windows as security_windows
from nac_bff.activation_security_backend import ProcessSpec, SecurityBoundaryError
from nac_bff.activation_security_windows import WindowsActivationSecurityBackend
from nac_m365_graph.mvp_test_environment_deploy import M365CliCommandRunner
from nac_m365_graph.node_runtime_integrity import build_node_runtime_manifest
from nac_m365_graph.sealed_toolchain import sealed_payloads, sealed_toolchain


@contextmanager
def _private_test_directory(backend: WindowsActivationSecurityBackend):
    """Yield a backend-created owner-only directory below the host temp root."""

    directory = Path(tempfile.mkdtemp()).resolve()
    try:
        private = directory / "private"
        with backend.open_secure_directory(private, create=True):
            pass
        backend.validate_private_directory(private)
        yield private
    finally:
        for attempt in range(10):
            try:
                shutil.rmtree(directory)
                break
            except FileNotFoundError:
                break
            except PermissionError as error:
                if error.winerror != 32 or attempt == 9:
                    raise
                time.sleep(0.1 * (attempt + 1))


@contextmanager
def _private_node(backend: WindowsActivationSecurityBackend):
    """Copy Node into a backend-created private fixture before attestation."""

    resolved = shutil.which("node")
    if resolved is None:
        raise unittest.SkipTest("Node is unavailable")
    with _private_test_directory(backend) as directory:
        with backend.open_secure_directory(directory, create=False) as session:
            snapshot = session.create_exclusive(
                "node.exe", Path(resolved).resolve().read_bytes()
            )
        yield directory / "node.exe", snapshot.sha256, directory


def _create_private_file(
    backend: WindowsActivationSecurityBackend,
    directory: Path,
    name: str,
    payload: bytes,
) -> Path:
    with backend.open_secure_directory(directory, create=False) as session:
        session.create_exclusive(name, payload)
    return directory / name


def _create_private_directory(
    backend: WindowsActivationSecurityBackend,
    directory: Path,
    name: str,
) -> Path:
    with backend.open_secure_directory(directory, create=False) as session:
        with session.open_secure_child_directory(name, create=True):
            pass
    return directory / name


@unittest.skipUnless(os.name == "nt", "native Windows security contract")
class WindowsActivationSecurityBackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.backend = WindowsActivationSecurityBackend()

    def test_private_file_is_measured_from_bound_handle(self) -> None:
        with _private_test_directory(self.backend) as directory:
            payload = b'{"synthetic":true}\n'
            path = _create_private_file(
                self.backend, directory, "evidence.json", payload
            )

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

    def test_extended_final_path_forms_are_canonicalized_without_aliasing(self) -> None:
        self.assertEqual(
            security_windows._normalized_final_path(r"\\?\C:\Private\evidence.json"),
            r"C:\Private\evidence.json",
        )
        self.assertEqual(
            security_windows._normalized_final_path(
                r"\\?\UNC\server\share\evidence.json"
            ),
            r"\\server\share\evidence.json",
        )

    def test_requested_path_binding_accepts_case_but_rejects_other_target(self) -> None:
        requested = Path(r"C:\Private\Evidence.json")
        with (
            patch.object(
                security_windows,
                "_long_path_name",
                return_value=r"C:\Private\Evidence.json",
            ),
            patch.object(
                security_windows,
                "_final_path",
                return_value=r"\\?\c:\private\evidence.json",
            ),
        ):
            security_windows._require_requested_path_binding(42, requested)
        with (
            patch.object(
                security_windows,
                "_long_path_name",
                return_value=r"C:\Private\Evidence.json",
            ),
            patch.object(
                security_windows,
                "_final_path",
                return_value=r"\\?\C:\Elsewhere\evidence.json",
            ),
        ):
            with self.assertRaisesRegex(
                SecurityBoundaryError, "FINAL_PATH_BINDING_MISMATCH"
            ):
                security_windows._require_requested_path_binding(42, requested)

    def test_requested_path_binding_expands_dos_short_names(self) -> None:
        requested = Path(r"C:\Users\RUNNER~1\AppData\Local\Temp\sealed")
        with (
            patch.object(
                security_windows,
                "_long_path_name",
                return_value=(
                    r"C:\Users\runneradmin\AppData\Local\Temp\sealed"
                ),
            ),
            patch.object(
                security_windows,
                "_final_path",
                return_value=(
                    r"\\?\C:\Users\runneradmin\AppData\Local\Temp\sealed"
                ),
            ),
        ):
            security_windows._require_requested_path_binding(42, requested)

    def test_private_paths_are_bound_to_supported_fixed_local_volume(self) -> None:
        with _private_test_directory(self.backend) as root:
            path = _create_private_file(
                self.backend, root, "bound.txt", b"synthetic"
            )
            self.assertRegex(
                self.backend.validate_private_directory(root), r"^[0-9a-f]{64}$"
            )
            self.assertGreater(
                self.backend.inspect_private_path(path, purpose="test").volume_serial,
                0,
            )

    def test_non_fixed_volume_is_rejected_before_file_use(self) -> None:
        with _private_test_directory(self.backend) as directory:
            path = _create_private_file(
                self.backend, directory, "bound.txt", b"synthetic"
            )
            with patch(
                "nac_bff.activation_security_windows._drive_type",
                return_value=4,
            ):
                with self.assertRaisesRegex(
                    SecurityBoundaryError, "LOCAL_FIXED_VOLUME_REQUIRED"
                ):
                    self.backend.inspect_private_path(path, purpose="test")

    def test_secure_directory_session_rejects_unsafe_child_names(self) -> None:
        with _private_test_directory(self.backend) as directory:
            with self.backend.open_secure_directory(
                directory, create=False
            ) as session:
                for name in (
                    "",
                    ".",
                    "..",
                    "child/name",
                    "child\\name",
                    "evidence.json:stream",
                    "evidence.json.",
                    "evidence.json ",
                    "NUL",
                    "COM1.txt",
                    "*.json",
                ):
                    with self.subTest(name=name):
                        with self.assertRaisesRegex(
                            SecurityBoundaryError, "SECURE_CHILD_NAME_INVALID"
                        ):
                            session.canonical_child_path(name)

    def test_secure_directory_session_retains_components_and_binds_child(self) -> None:
        with _private_test_directory(self.backend) as root:
            private = root / "private"
            with self.backend.open_secure_directory(
                private, create=True
            ) as session:
                snapshot = session.atomic_write("evidence.json", b"synthetic")
                self.assertEqual(
                    snapshot.volume_serial, session.binding.volume_serial
                )
                self.assertEqual(
                    session.read_bounded("evidence.json", 9), b"synthetic"
                )
                moved = root / "replaced"
                with self.assertRaises(OSError):
                    private.rename(moved)
                self.assertFalse((private / "redirected.json").exists())
            private.rename(moved)

    def test_secure_directory_session_create_exclusive_rejects_replay(self) -> None:
        with _private_test_directory(self.backend) as directory:
            with self.backend.open_secure_directory(
                directory, create=False
            ) as session:
                snapshot = session.create_exclusive("claim.json", b"first")
                self.assertEqual(snapshot.size, 5)
                with self.assertRaisesRegex(
                    SecurityBoundaryError, "SECURE_CHILD_ALREADY_EXISTS"
                ):
                    session.create_exclusive("claim.json", b"second")
                self.assertEqual(session.read_bounded("claim.json", 5), b"first")

    def test_secure_child_directory_retains_parent_binding(self) -> None:
        with _private_test_directory(self.backend) as root:
            with self.backend.open_secure_directory(root, create=False) as parent:
                with parent.open_secure_child_directory(
                    "records", create=True
                ) as child:
                    child.create_exclusive("record.json", b"synthetic")
                    self.assertEqual(
                        child.binding.volume_serial, parent.binding.volume_serial
                    )
                    with self.assertRaises(PermissionError):
                        root.rename(root.with_name("redirected"))
                    self.assertEqual(
                        child.read_bounded("record.json", 9), b"synthetic"
                    )

    def test_secure_child_directory_rejects_file_reparse_and_binding_drift(self) -> None:
        with _private_test_directory(self.backend) as root:
            regular = _create_private_file(
                self.backend, root, "regular", b"synthetic"
            )
            target = root / "target"
            target.mkdir()
            junction = root / "junction"
            subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
            with self.backend.open_secure_directory(root, create=False) as parent:
                with self.assertRaisesRegex(SecurityBoundaryError, "DIRECTORY_REQUIRED"):
                    parent.open_secure_child_directory("regular", create=False)
                with self.assertRaisesRegex(
                    SecurityBoundaryError, "REPARSE_POINT_REJECTED"
                ):
                    parent.open_secure_child_directory("junction", create=False)
                plain = _create_private_directory(
                    self.backend, root, "plain"
                )
                with patch.object(
                    security_windows,
                    "_require_requested_path_binding",
                    side_effect=SecurityBoundaryError("FINAL_PATH_BINDING_MISMATCH"),
                ):
                    with self.assertRaisesRegex(
                        SecurityBoundaryError, "FINAL_PATH_BINDING_MISMATCH"
                    ):
                        parent.open_secure_child_directory("plain", create=False)

    def test_secure_directory_session_rejects_non_ntfs(self) -> None:
        with _private_test_directory(self.backend) as directory:
            with patch(
                "nac_bff.activation_security_windows.kernel32.GetVolumeInformationW",
                side_effect=lambda *_args: True,
            ), patch(
                "nac_bff.activation_security_windows._volume_root",
                return_value="C:\\\\",
            ):
                # The filesystem buffer cannot be populated by this synthetic
                # call, so the backend must fail closed as non-NTFS.
                with self.assertRaisesRegex(
                    SecurityBoundaryError, "SUPPORTED_LOCAL_FILESYSTEM_REQUIRED"
                ):
                    self.backend.open_secure_directory(
                        directory, create=False
                    )

    def test_secure_directory_session_rejects_renamed_ancestor(self) -> None:
        with _private_test_directory(self.backend) as root:
            ancestor = _create_private_directory(
                self.backend, root, "ancestor"
            )
            private = _create_private_directory(
                self.backend, ancestor, "private"
            )
            with self.backend.open_secure_directory(
                private, create=False
            ) as session:
                moved = root / "moved-ancestor"
                with self.assertRaises(PermissionError):
                    ancestor.rename(moved)
                self.assertTrue(private.is_dir())
                self.assertFalse(moved.exists())
                self.assertFalse((private / "evidence.json").exists())

    def test_reparse_point_is_rejected(self) -> None:
        with _private_test_directory(self.backend) as root:
            target = root / "target"
            link = root / "link"
            target.mkdir()
            subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                check=True,
                capture_output=True,
                text=True,
            )
            with self.assertRaisesRegex(SecurityBoundaryError, "REPARSE_POINT_REJECTED"):
                self.backend.validate_private_directory(link)

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
            with _private_test_directory(self.backend) as directory:
                path = _create_private_file(
                    self.backend, directory, "broad.txt", b"synthetic"
                )
                self.assertTrue(set_security(str(path), 0x00000004, descriptor))
                with self.assertRaisesRegex(SecurityBoundaryError, "FILE_DACL_TOO_BROAD"):
                    self.backend.inspect_private_path(path, purpose="test")
        finally:
            kernel32.LocalFree(descriptor)

    def test_binding_drift_is_rejected(self) -> None:
        with _private_test_directory(self.backend) as directory:
            path = _create_private_file(
                self.backend, directory, "evidence.json", b"first"
            )
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
        with _private_node(self.backend) as (executable, executable_hash, _root):
            result = self.backend.launch_attested_process(
                ProcessSpec(
                    executable=executable,
                    arguments=("-e", "console.log('synthetic')"),
                    cwd=Path.cwd().resolve(),
                    environment={
                        "SystemRoot": os.environ["SystemRoot"],
                        "TEMP": tempfile.gettempdir(),
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
        with _private_node(self.backend) as (executable, _hash, _root):
            with self.assertRaisesRegex(SecurityBoundaryError, "PROCESS_IMAGE_MISMATCH"):
                self.backend.launch_attested_process(
                    ProcessSpec(
                        executable=executable,
                        arguments=("-e", "process.exit(99)"),
                        cwd=Path.cwd().resolve(),
                        environment={"SystemRoot": os.environ["SystemRoot"]},
                        executable_sha256="0" * 64,
                    )
                )

    def test_credential_guard_blocks_profile_write_before_resume(self) -> None:
        with _private_node(self.backend) as (executable, executable_hash, directory):
            destination = directory / "credential-cache.json"
            script = (
                "const fs=require('node:fs');"
                f"try{{fs.writeFileSync({str(destination)!r},'forbidden');"
                "console.log('WRITTEN')}catch(e){console.log('BLOCKED')}"
            )
            result = self.backend.launch_attested_process(
                ProcessSpec(
                    executable=executable,
                    arguments=("-e", script),
                    cwd=Path.cwd().resolve(),
                    environment={
                        "SystemRoot": os.environ["SystemRoot"],
                        "TEMP": tempfile.gettempdir(),
                    },
                    executable_sha256=executable_hash,
                    credential_write_guard=True,
                )
            )
            self.assertEqual(result.stdout.strip(), b"BLOCKED")
            self.assertFalse(destination.exists())

    def test_loader_failure_is_redacted_without_interactive_error_mode(self) -> None:
        with _private_node(self.backend) as (executable, executable_hash, _root):
            with self.assertRaisesRegex(
                SecurityBoundaryError, "PROCESS_EXIT_CODE_REJECTED"
            ):
                self.backend.launch_attested_process(
                    ProcessSpec(
                        executable=executable,
                        arguments=("-e", "process.exit(17)"),
                        cwd=Path.cwd().resolve(),
                        environment={"SystemRoot": os.environ["SystemRoot"]},
                        executable_sha256=executable_hash,
                        allowed_exit_codes=(0,),
                    )
                )

    def test_node_permission_guard_blocks_cache_write(self) -> None:
        with _private_node(self.backend) as (executable, executable_hash, directory):
            destination = directory / "m365-cache.json"
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
        with _private_node(self.backend) as (executable, executable_hash, root):
            destination = root / "worker-cache.json"
            worker_source = (
                "const {parentPort}=require('node:worker_threads');"
                "const fs=require('node:fs');"
                f"try{{fs.writeFileSync({str(destination)!r},'forbidden');"
                "parentPort.postMessage('WRITTEN')}"
                "catch(e){parentPort.postMessage(e.code)}"
            )
            worker = _create_private_file(
                self.backend,
                root,
                "worker.cjs",
                worker_source.encode("utf-8"),
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
        with _private_node(self.backend) as (node, node_sha256, root):
            runtime = _create_private_directory(
                self.backend, root, "m365-runtime"
            )
            dist = _create_private_directory(
                self.backend, runtime, "dist"
            )
            home = _create_private_directory(
                self.backend, root, "m365-home"
            )
            cache = home / "refreshed-token.json"
            entrypoint_source = (
                "const fs=require('node:fs');"
                f"let blocked=false;try{{fs.writeFileSync({str(cache)!r},'x')}}"
                "catch(e){blocked=e.code==='ERR_ACCESS_DENIED'};"
                "console.log(JSON.stringify({"
                "connectedAs:'operator@example.com',"
                "appId:'11111111-1111-4111-8111-111111111111',"
                "appTenant:'22222222-2222-4222-8222-222222222222',"
                "cloudType:'Public',writeBlocked:blocked}));"
            )
            entrypoint = _create_private_file(
                self.backend,
                dist,
                "index.js",
                entrypoint_source.encode("utf-8"),
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
            runtime_payloads = runner._runtime_payloads()
            runtime_manifest = build_node_runtime_manifest(runtime)
            with self.subTest(sealing_phase="runtime-files"):
                with sealed_toolchain(
                    tuple(
                        (
                            runtime / item.relative_path,
                            False,
                            item.sha256,
                        )
                        for item in runtime_manifest.files
                    )
                ):
                    pass
            with self.subTest(sealing_phase="node-binary"):
                with sealed_toolchain(((node, True, node_sha256),)):
                    pass
            with self.subTest(sealing_phase="loader-payloads"):
                with sealed_payloads(
                    (
                        (
                            "node-runtime-manifest.json",
                            runtime_payloads.manifest,
                            False,
                        ),
                        (
                            "node-runtime-preloader.cjs",
                            runtime_payloads.commonjs_preloader,
                            False,
                        ),
                        (
                            "node-runtime-loader.mjs",
                            runtime_payloads.esm_loader,
                            False,
                        ),
                    )
                ):
                    pass
            result = runner.run(("m365", "status", "--output", "json"))
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(payload["writeBlocked"])
            with (
                patch(
                    "nac_m365_graph.mvp_test_environment_deploy.EXPECTED_M365_CLI_USER",
                    "operator@example.com",
                ),
                patch(
                    "nac_m365_graph.mvp_test_environment_deploy.EXPECTED_M365_CLI_APP_ID",
                    "11111111-1111-4111-8111-111111111111",
                ),
                patch(
                    "nac_m365_graph.mvp_test_environment_deploy.EXPECTED_M365_TENANT_ID",
                    "22222222-2222-4222-8222-222222222222",
                ),
            ):
                self.assertTrue(runner.check_readiness())
            self.assertFalse(cache.exists())


if __name__ == "__main__":
    unittest.main()
