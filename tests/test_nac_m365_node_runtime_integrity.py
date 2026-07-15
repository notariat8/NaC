from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from nac_m365_graph.node_runtime_integrity import (
    MANIFEST_ENV,
    NodeRuntimeIntegrityError,
    build_node_runtime_integrity_payloads,
    build_node_runtime_manifest,
    verify_node_runtime_manifest,
)


class NodeRuntimeIntegrityTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, payload: bytes) -> Path:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        target.chmod(0o600)
        return target

    def test_digest_is_deterministic_and_independent_of_root(self) -> None:
        with tempfile.TemporaryDirectory() as first_temporary, tempfile.TemporaryDirectory() as second_temporary:
            first = Path(first_temporary)
            second = Path(second_temporary)
            self._write(first, "node_modules/pkg/index.js", b"module.exports = 7;\n")
            self._write(first, "entry.cjs", b"require('pkg');\n")
            self._write(second, "entry.cjs", b"require('pkg');\n")
            self._write(second, "node_modules/pkg/index.js", b"module.exports = 7;\n")

            first_manifest = build_node_runtime_manifest(first)
            repeated_manifest = build_node_runtime_manifest(first)
            second_manifest = build_node_runtime_manifest(second)

        self.assertEqual(first_manifest.digest, repeated_manifest.digest)
        self.assertEqual(first_manifest.digest, second_manifest.digest)
        self.assertEqual(
            [item.relative_path for item in first_manifest.files],
            ["entry.cjs", "node_modules/pkg/index.js"],
        )

    def test_expected_digest_is_required_and_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write(root, "entry.js", b"console.log('ok');\n")
            digest = build_node_runtime_manifest(root).digest

            with self.assertRaisesRegex(
                NodeRuntimeIntegrityError,
                "^NODE_RUNTIME_EXPECTED_DIGEST_INVALID$",
            ):
                verify_node_runtime_manifest(root, expected_digest="")
            with self.assertRaisesRegex(
                NodeRuntimeIntegrityError,
                "^NODE_RUNTIME_DIGEST_MISMATCH$",
            ):
                verify_node_runtime_manifest(root, expected_digest="0" * 64)

            payloads = build_node_runtime_integrity_payloads(
                root,
                expected_digest=digest,
            )
            parsed = json.loads(payloads.manifest)

        self.assertEqual(payloads.digest, digest)
        manifest_sha256 = hashlib.sha256(payloads.manifest).hexdigest()
        self.assertIn(
            manifest_sha256.encode("ascii"), payloads.commonjs_preloader
        )
        self.assertIn(manifest_sha256.encode("ascii"), payloads.esm_loader)
        self.assertEqual(parsed["digest"], digest)
        self.assertEqual(set(parsed["files"]), {"entry.js"})
        self.assertIn(digest.encode("ascii"), payloads.commonjs_preloader)
        self.assertIn(digest.encode("ascii"), payloads.esm_loader)

    def test_scan_rejects_symlinks_native_addons_and_untrusted_modes(self) -> None:
        cases = (
            ("symlink", "NODE_RUNTIME_SYMLINK_REJECTED"),
            ("native", "NODE_RUNTIME_NATIVE_ADDON_REJECTED"),
            ("mode", "NODE_RUNTIME_FILE_UNTRUSTED"),
        )
        for case, code in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = self._write(root, "target.js", b"module.exports = 1;\n")
                if case == "symlink":
                    (root / "linked.js").symlink_to(target)
                elif case == "native":
                    self._write(root, "addon.node", b"native")
                else:
                    target.chmod(0o622)
                with self.assertRaisesRegex(
                    NodeRuntimeIntegrityError,
                    f"^{code}$",
                ):
                    build_node_runtime_manifest(root)

    def test_bin_directories_are_excluded_but_other_symlinks_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry = self._write(root, "entry.cjs", b"module.exports = 1;\n")
            shim_directory = root / "node_modules" / ".bin"
            shim_directory.mkdir(parents=True)
            (shim_directory / "tool").symlink_to(entry)

            manifest = build_node_runtime_manifest(root)

            self.assertEqual(
                [item.relative_path for item in manifest.files],
                ["entry.cjs"],
            )
            (root / "node_modules" / "linked.js").symlink_to(entry)
            with self.assertRaisesRegex(
                NodeRuntimeIntegrityError,
                r"^NODE_RUNTIME_SYMLINK_REJECTED\Z",
            ):
                build_node_runtime_manifest(root)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_commonjs_dependency_bytes_are_verified_before_compile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.js",
                b"console.log(require('./dependency.js'));\n",
            )
            dependency = self._write(
                root,
                "dependency.js",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            arguments = [
                "--preserve-symlinks",
                "--require",
                str(payloads[1]),
                "--experimental-loader",
                str(payloads[2]),
                str(entry),
            ]

            completed = self._run_node(
                arguments,
                manifest=payloads[0],
            )
            dependency.write_bytes(b"module.exports = 'changed';\n")
            dependency.chmod(0o600)
            tampered = self._run_node(
                arguments,
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "trusted")
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_SHA256_MISMATCH", tampered.stderr)
        self.assertNotIn("changed", tampered.stdout)

    @unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
    def test_esm_dependency_bytes_are_verified_before_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            self._write(root, "package.json", b'{"type":"module"}\n')
            entry = self._write(
                root,
                "entry.js",
                b"import value from './dependency.js'; console.log(value);\n",
            )
            dependency = self._write(
                root,
                "dependency.js",
                b"export default 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                ["--experimental-loader", str(payloads[2]), str(entry)],
                manifest=payloads[0],
            )
            dependency.write_bytes(b"export default 'changed';\n")
            dependency.chmod(0o600)
            tampered = self._run_node(
                ["--experimental-loader", str(payloads[2]), str(entry)],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "trusted")
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_SHA256_MISMATCH", tampered.stderr)
        self.assertNotIn("changed", tampered.stdout)

    def _payload_files(
        self,
        root: Path,
        workspace: Path,
    ) -> tuple[Path, Path, Path]:
        digest = build_node_runtime_manifest(root).digest
        payloads = build_node_runtime_integrity_payloads(
            root,
            expected_digest=digest,
        )
        manifest = workspace / "manifest.json"
        commonjs = workspace / "preloader.cjs"
        esm = workspace / "loader.mjs"
        manifest.write_bytes(payloads.manifest)
        commonjs.write_bytes(payloads.commonjs_preloader)
        esm.write_bytes(payloads.esm_loader)
        for path in (manifest, commonjs, esm):
            path.chmod(0o400)
        return manifest, commonjs, esm

    def _run_node(
        self,
        arguments: list[str],
        *,
        manifest: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [shutil.which("node") or "node", *arguments],
            check=False,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env={
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                MANIFEST_ENV: str(manifest),
            },
            timeout=20,
        )


if __name__ == "__main__":
    unittest.main()
