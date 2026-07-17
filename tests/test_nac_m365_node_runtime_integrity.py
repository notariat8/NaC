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


_PINNED_NODE = Path("/tmp/node-v22.23.1-linux-x64/bin/node")
_DISCOVERED_NODE = shutil.which("node")
_NODE_BINARY = (
    _PINNED_NODE
    if _PINNED_NODE.is_file()
    else Path(_DISCOVERED_NODE) if _DISCOVERED_NODE else None
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

    def test_scan_rejects_symlinks_and_untrusted_modes(self) -> None:
        cases = (
            ("symlink", "NODE_RUNTIME_SYMLINK_REJECTED"),
            ("mode", "NODE_RUNTIME_FILE_UNTRUSTED"),
        )
        for case, code in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                target = self._write(root, "target.js", b"module.exports = 1;\n")
                if case == "symlink":
                    (root / "linked.js").symlink_to(target)
                else:
                    target.chmod(0o622)
                with self.assertRaisesRegex(
                    NodeRuntimeIntegrityError,
                    f"^{code}$",
                ):
                    build_node_runtime_manifest(root)

    def test_native_addon_bytes_are_attested_but_execution_stays_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write(root, "entry.cjs", b"require('./addon.node');\n")
            self._write(root, "addon.node", b"native")
            manifest = build_node_runtime_manifest(root)
            payloads = build_node_runtime_integrity_payloads(
                root, expected_digest=manifest.digest
            )

        self.assertIn(
            "addon.node", {item.relative_path for item in manifest.files}
        )
        self.assertIn(
            b"NODE_RUNTIME_NATIVE_ADDON_REJECTED", payloads.commonjs_preloader
        )
        self.assertIn(
            b"NODE_RUNTIME_NATIVE_ADDON_REJECTED", payloads.esm_loader
        )

    def test_explicit_generated_directories_are_excluded_and_loader_bound(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write(root, "entry.cjs", b"module.exports = 1;\n")
            self._write(root, "temp/generated.d.ts", b"export {};\n")
            manifest = build_node_runtime_manifest(
                root,
                excluded_top_level_directories=frozenset({"temp"}),
            )
            payloads = build_node_runtime_integrity_payloads(
                root,
                expected_digest=manifest.digest,
                excluded_top_level_directories=frozenset({"temp"}),
            )

        self.assertEqual(
            [item.relative_path for item in manifest.files],
            ["entry.cjs"],
        )
        self.assertIn(
            b'GENERATED_TOP_LEVEL_DIRECTORIES = new Set(\n  ["temp"]',
            payloads.commonjs_preloader,
        )
        self.assertIn(b"generatedOutputRead", payloads.commonjs_preloader)
        self.assertIn(b"integrityReadFileSync", payloads.commonjs_preloader)
        self.assertIn(b"function IntegrityWorker", payloads.commonjs_preloader)

    def test_generated_directory_exclusions_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write(root, "entry.cjs", b"module.exports = 1;\n")
            for invalid in (
                {"temp"},
                frozenset({".bin"}),
                frozenset({"../temp"}),
            ):
                with self.subTest(invalid=invalid), self.assertRaisesRegex(
                    NodeRuntimeIntegrityError,
                    r"^NODE_RUNTIME_EXCLUSION_INVALID\Z",
                ):
                    build_node_runtime_manifest(
                        root,
                        excluded_top_level_directories=invalid,  # type: ignore[arg-type]
                    )

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

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_async_and_stream_asset_reads_reverify_manifest_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "fs.writeFileSync(asset, 'tampered-wasm');"
                    "(async () => {"
                    "let verified = 0;"
                    "try { await fs.promises.readFile(asset); } "
                    "catch (error) { if (error.code === "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') verified++; }"
                    "await new Promise((resolve) => fs.readFile(asset, (error) => {"
                    "if (error && error.code === "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') verified++;"
                    "resolve();"
                    "}));"
                    "try { fs.createReadStream(asset); } "
                    "catch (error) { if (error.code === "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') verified++; }"
                    "if (verified !== 3) process.exit(44);"
                    "})().catch(() => process.exit(45));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_esm_open_as_blob_reverifies_manifest_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.mjs",
                (
                    "import fs, { openAsBlob } from 'node:fs';"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "fs.writeFileSync(asset, 'tampered-wasm');"
                    "try { await openAsBlob(asset); process.exit(80); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') process.exit(81); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_next_tick_cannot_replace_verified_callback_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const originalNextTick = process.nextTick;"
                    "process.nextTick = function(callback, ...args) {"
                    "if (args.length > 1 && Buffer.isBuffer(args[1])) "
                    "args[1] = Buffer.from('NEXT_TICK_BYPASS');"
                    "return originalNextTick(callback, ...args); };"
                    "fs.readFile("
                    + json.dumps(str(asset))
                    + ", (error, value) => { if (error || value.toString() !== 'trusted') "
                    "process.exit(91); });\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_descriptor_based_runtime_reads_reverify_manifest_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "(async () => {"
                    "let rejected = 0;"
                    "try { fs.openSync(asset, 'r'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_MODULE_SHA256_MISMATCH') rejected++; }"
                    "await new Promise((resolve) => fs.open(asset, 'r', (error) => {"
                    "if (error && error.code === 'NODE_RUNTIME_MODULE_SHA256_MISMATCH') rejected++;"
                    "resolve(); }));"
                    "try { await fs.promises.open(asset, 'r'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_MODULE_SHA256_MISMATCH') rejected++; }"
                    "if (rejected !== 3) process.exit(54);"
                    "})().catch(() => process.exit(55));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            asset.write_bytes(b"tampered-wasm")

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_clean_descriptor_reads_fail_closed_after_byte_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "(async () => {"
                    "let rejected = 0;"
                    "try { fs.openSync(asset, 'r'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED') rejected++; }"
                    "await new Promise(resolve => fs.open(asset, 'r', error => {"
                    "if (error && error.code === 'NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED') rejected++;"
                    "resolve(); }));"
                    "try { await fs.promises.open(asset, 'r'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED') rejected++; }"
                    "if (rejected !== 3) process.exit(59);\n"
                    "})().catch(() => process.exit(60));"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_fork_option_getter_cannot_reenter_spawn_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            child = self._write(root, "child.cjs", b"process.exit(0);\n")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const child = require('node:child_process');"
                    "let blocked = false;"
                    "const options = {};"
                    "Object.defineProperty(options, 'silent', { enumerable: true, get() {"
                    "try { new child.ChildProcess().spawn({ file: '/bin/true' }); }"
                    "catch (error) { blocked = error.code === 'NODE_RUNTIME_NODE_SUBPROCESS_REJECTED'; }"
                    "return true; }});"
                    "try { child.fork(" + json.dumps(str(child)) + ", [], options); }"
                    "catch (error) {"
                    "if (blocked || error.code !== 'NODE_RUNTIME_FORK_OPTIONS_REJECTED') process.exit(61);"
                    "process.exit(0); }"
                    "process.exit(62);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_application_worker_cannot_use_internal_loader_descriptor_exception(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            worker = self._write(
                root,
                "worker.cjs",
                (
                    "const fs = require('node:fs');"
                    "const { parentPort } = require('node:worker_threads');"
                    "try { fs.openSync(" + json.dumps(str(asset)) + ", 'r');"
                    "parentPort.postMessage('OPENED'); } catch (error) {"
                    "parentPort.postMessage(error.code); }\n"
                ).encode("utf-8"),
            )
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const { Worker } = require('node:worker_threads');"
                    "const worker = new Worker(" + json.dumps(str(worker)) + ");"
                    "worker.once('message', code => process.exit("
                    "code === 'NODE_RUNTIME_DESCRIPTOR_OPEN_REJECTED' ? 0 : 63));"
                    "worker.once('error', () => process.exit(64));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_worker_constructor_does_not_expose_original_via_prototype(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            worker = self._write(
                root,
                "worker.cjs",
                b"require('node:worker_threads').parentPort.postMessage('OK');\n",
            )
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const threads = require('node:worker_threads');"
                    "const Guard = threads.Worker;"
                    "if (Object.getPrototypeOf(Guard) !== Function.prototype) "
                    "process.exit(65);"
                    "if (Guard.prototype.constructor !== Guard) process.exit(66);"
                    "try { new (Object.getPrototypeOf(Guard))("
                    + json.dumps(str(worker))
                    + "); process.exit(67); } catch (error) {"
                    "if (!(error instanceof TypeError)) process.exit(68); }"
                    "const worker = new Guard("
                    + json.dumps(str(worker))
                    + ");"
                    "worker.once('message', value => process.exit("
                    "value === 'OK' ? 0 : 69));"
                    "worker.once('error', () => process.exit(70));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutable_object_helpers_cannot_reenter_fork_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            child = self._write(root, "child.cjs", b"process.exit(0);\n")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const childProcess = require('node:child_process');"
                    "const originalEntries = Object.entries;"
                    "const originalFromEntries = Object.fromEntries;"
                    "let reentered = false;"
                    "function attempt() { try {"
                    "new childProcess.ChildProcess().spawn({ file: '/bin/true' });"
                    "reentered = true; } catch {} }"
                    "Object.entries = function(value) { attempt(); return originalEntries(value); };"
                    "Object.fromEntries = function(value) { attempt(); return originalFromEntries(value); };"
                    "const forked = childProcess.fork("
                    + json.dumps(str(child))
                    + ", [], { env: { SAFE: 'yes' }, silent: true });"
                    "Object.entries = originalEntries;"
                    "Object.fromEntries = originalFromEntries;"
                    "forked.once('error', () => process.exit(82));"
                    "forked.once('exit', code => process.exit("
                    "code === 0 && !reentered ? 0 : 83));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_array_some_cannot_reenter_authorized_fork_spawn(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            child = self._write(root, "child.cjs", b"process.exit(0);\n")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const childProcess = require('node:child_process');"
                    "let entered = false; let spawnReturned = false;"
                    "Array.prototype.some = function() { return false; };"
                    "const value = { toString() { entered = true; try {"
                    "new childProcess.ChildProcess().spawn({ file: '/bin/true' });"
                    "spawnReturned = true; } catch {} return 'unsafe'; }};"
                    "try { childProcess.fork("
                    + json.dumps(str(child))
                    + ", [], { env: { TRAP: value } }); process.exit(87); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_FORK_OPTIONS_REJECTED' || entered || spawnReturned) "
                    "process.exit(88); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_fork_environment_value_cannot_reenter_spawn_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            child = self._write(root, "child.cjs", b"process.exit(0);\n")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const childProcess = require('node:child_process');"
                    "let converted = false;"
                    "const envValue = { toString() { converted = true;"
                    "try { new childProcess.ChildProcess().spawn({ file: '/bin/true' }); }"
                    "catch {} return 'unsafe'; }};"
                    "try { childProcess.fork("
                    + json.dumps(str(child))
                    + ", [], { env: { TRAP: envValue } }); process.exit(71); }"
                    "catch (error) {"
                    "if (converted || error.code !== "
                    "'NODE_RUNTIME_FORK_OPTIONS_REJECTED') process.exit(72); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_verification_exports_do_not_disable_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const crypto = require('node:crypto');"
                    "fs.fstatSync = () => ({ size: 0 });"
                    "fs.lstatSync = () => ({ size: 0 });"
                    "fs.readlinkSync = () => '';"
                    "fs.existsSync = () => true;"
                    "crypto.createHash = () => ({ update() { return this; },"
                    "digest() { return " + json.dumps("0" * 64) + "; } });"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "fs.writeFileSync(asset, 'tampered-wasm');"
                    "try { fs.readFileSync(asset); process.exit(73); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') process.exit(74); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_hash_prototype_does_not_disable_integrity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const crypto = require('node:crypto');"
                    "const prototype = Object.getPrototypeOf("
                    "crypto.createHash('sha256'));"
                    "prototype.update = function() { return this; };"
                    "prototype.digest = function() { return "
                    + json.dumps(hashlib.sha256(b"tampered-wasm").hexdigest())
                    + "; };"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "fs.writeFileSync(asset, 'tampered-wasm');"
                    "try { fs.readFileSync(asset); process.exit(77); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') process.exit(78); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_external_symlink_and_hardlink_reads_reverify_runtime_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            symlink = workspace / "binding-symlink.wasm"
            hardlink = workspace / "binding-hardlink.wasm"
            symlink.symlink_to(asset)
            os.link(asset, hardlink)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "const aliases = ["
                    + json.dumps(str(symlink))
                    + ","
                    + json.dumps(str(hardlink))
                    + "];"
                    "fs.writeFileSync(asset, 'tampered-wasm');"
                    "let rejected = 0;"
                    "for (const alias of aliases) {"
                    "try { fs.readFileSync(alias); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_MODULE_SHA256_MISMATCH') "
                    "rejected++; }}"
                    "if (rejected !== 2) process.exit(79);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_buffer_is_buffer_cannot_bypass_runtime_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const asset = " + json.dumps(str(asset)) + ";"
                    "const bufferPath = Buffer.from(asset);"
                    "Buffer.isBuffer = () => false;"
                    "fs.writeFileSync(asset, 'buffer-type-bypassed');"
                    "try { fs.readFileSync(bufferPath); process.exit(89); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') process.exit(90); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_manifest_bound_assets_cannot_be_copied_out(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            destination = workspace / "copied.wasm"
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const source = " + json.dumps(str(asset)) + ";"
                    "const destination = " + json.dumps(str(destination)) + ";"
                    "(async () => { let rejected = 0;"
                    "for (const invoke of ["
                    "() => fs.copyFileSync(source, destination),"
                    "() => fs.cpSync(source, destination)]) {"
                    "try { invoke(); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_COPY_SOURCE_REJECTED') rejected++; }"
                    "}"
                    "try { await fs.promises.copyFile(source, destination); }"
                    "catch (error) { if (error.code === "
                    "'NODE_RUNTIME_COPY_SOURCE_REJECTED') rejected++; }"
                    "try { await fs.promises.cp(source, destination); }"
                    "catch (error) { if (error.code === "
                    "'NODE_RUNTIME_COPY_SOURCE_REJECTED') rejected++; }"
                    "if (rejected !== 4 || fs.existsSync(destination)) process.exit(75);"
                    "})().catch(() => process.exit(76));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_generated_copy_rejects_external_symlink_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            destination = root / "lib" / "copy.wasm"
            outside = workspace / "outside.wasm"
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const source = " + json.dumps(str(asset)) + ";"
                    "const destination = " + json.dumps(str(destination)) + ";"
                    "const outside = " + json.dumps(str(outside)) + ";"
                    "try { fs.copyFileSync(source, destination); process.exit(84); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_COPY_DESTINATION_REJECTED') process.exit(85); }"
                    "if (fs.existsSync(outside) || !fs.lstatSync(destination).isSymbolicLink()) "
                    "process.exit(86);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(
                root,
                workspace,
                excluded_top_level_directories=frozenset({"lib"}),
            )
            destination.parent.mkdir(mode=0o700)
            destination.symlink_to(outside)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_all_unsealed_child_process_launchers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const child = require('node:child_process');"
                    "let rejected = 0;"
                    "for (const invoke of ["
                    "() => child.spawnSync('/proc/self/exe', ['-e', '']),"
                    "() => child.spawnSync('/usr/bin/env', [process.env.NODE, '-e', '']),"
                    "() => child.execSync('true'),"
                    "() => new child.ChildProcess().spawn({ file: '/bin/true' })]) {"
                    "try { invoke(); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_NODE_SUBPROCESS_REJECTED') rejected++; }"
                    "}"
                    "if (rejected !== 4) process.exit(56);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_esm_named_builtin_exports_receive_integrity_guards(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted-wasm")
            entry = self._write(
                root,
                "entry.mjs",
                (
                    "import { spawnSync } from 'node:child_process';"
                    "import { openSync } from 'node:fs';"
                    "let rejected = 0;"
                    "try { spawnSync('/bin/true'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_NODE_SUBPROCESS_REJECTED') rejected++; }"
                    "try { openSync(" + json.dumps(str(asset)) + ", 'r'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_MODULE_SHA256_MISMATCH') rejected++; }"
                    "if (rejected !== 2) process.exit(57);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            asset.write_bytes(b"tampered-wasm")

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_readable_delivery_cannot_replace_verified_stream_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const { Readable } = require('node:stream');"
                    "Readable.from = () => Readable.from(['READABLE_FROM_BYPASS']);"
                    "Readable.prototype.setEncoding = function() { return this; };"
                    "const stream = fs.createReadStream("
                    + json.dumps(str(asset))
                    + "); let output = '';"
                    "stream.on('data', chunk => { output += chunk.toString(); });"
                    "stream.once('error', () => process.exit(94));"
                    "stream.once('end', () => { if (output !== 'trusted') process.exit(95); });\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_readable_push_cannot_replace_verified_stream_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const { Readable } = require('node:stream');"
                    "const originalPush = Readable.prototype.push;"
                    "Readable.prototype.push = function(value, ...args) {"
                    "return originalPush.call(this, value === null ? null : "
                    "Buffer.from('READABLE_PUSH_BYPASS'), ...args); };"
                    "const stream = fs.createReadStream("
                    + json.dumps(str(asset))
                    + "); let output = '';"
                    "stream.on('data', chunk => { output += chunk.toString(); });"
                    "stream.once('error', () => process.exit(96));"
                    "stream.once('end', () => { if (output !== 'trusted') process.exit(97); });\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_readable_emit_cannot_replace_verified_stream_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            asset = self._write(root, "binding.wasm", b"trusted")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const { Readable } = require('node:stream');"
                    "const originalEmit = Readable.prototype.emit;"
                    "Readable.prototype.emit = function(name, value, ...args) {"
                    "return originalEmit.call(this, name, name === 'data' ? "
                    "Buffer.from('READABLE_EMIT_BYPASS') : value, ...args); };"
                    "const stream = fs.createReadStream("
                    + json.dumps(str(asset))
                    + "); let output = '';"
                    "stream.on('data', chunk => { output += chunk.toString(); });"
                    "stream.once('error', () => process.exit(100));"
                    "stream.once('end', () => { if (output !== 'trusted') process.exit(101); });\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_low_level_process_spawn_bindings_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "let rejected = 0;"
                    "for (const name of ['spawn_sync', 'process_wrap', 'fs']) {"
                    "try { process.binding(name); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_LOW_LEVEL_SUBPROCESS_REJECTED') rejected++; }"
                    "}"
                    "try { process._linkedBinding('spawn_sync'); } catch (error) {"
                    "if (error.code === 'NODE_RUNTIME_LOW_LEVEL_SUBPROCESS_REJECTED') rejected++; }"
                    "if (rejected !== 4) process.exit(58);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_direct_node_spawn_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const { spawnSync } = require('node:child_process');"
                    "try { spawnSync(process.execPath, ['-e', "
                    "'console.log(123)']); process.exit(46); } "
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_NODE_SUBPROCESS_REJECTED') process.exit(47); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_missing_optional_asset_is_enoent_but_later_file_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            missing = root / "optional.json"
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const target = " + json.dumps(str(missing)) + ";"
                    "(async () => {"
                    "try { await fs.promises.readFile(target); process.exit(48); } "
                    "catch (error) { if (error.code !== 'ENOENT') process.exit(49); }"
                    "fs.writeFileSync(target, '{}');"
                    "try { await fs.promises.readFile(target); process.exit(50); } "
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_NOT_ALLOWED') process.exit(51); }"
                    "})().catch(() => process.exit(52));\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_fork_uses_immutable_bootstrap_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            child = self._write(
                root,
                "child.cjs",
                b"console.log('SEALED_CHILD_OK');\n",
            )
            marker = workspace / "external-preload-ran"
            preload = self._write(
                workspace,
                "external-preload.cjs",
                (
                    "require('node:fs').writeFileSync("
                    + json.dumps(str(marker))
                    + ", 'bypass');\n"
                ).encode("utf-8"),
            )
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const { fork } = require('node:child_process');"
                    "process.env.NODE = '/bin/echo';"
                    "process.env.NODE_OPTIONS = '--require="
                    + str(preload)
                    + "';"
                    "const child = fork("
                    + json.dumps(str(child))
                    + ", [], { silent: true });"
                    "let output = '';"
                    "child.stdout.on('data', chunk => { output += chunk; });"
                    "child.once('error', () => process.exit(92));"
                    "child.once('exit', code => { if (code !== 0 || "
                    "output.trim() !== 'SEALED_CHILD_OK' || fs.existsSync("
                    + json.dumps(str(marker))
                    + ")) process.exit(93); });\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(marker.exists())

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_fork_discards_custom_exec_path_and_exec_argv(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            child = self._write(
                root,
                "child.cjs",
                b"console.log('SANITIZED_FORK_OK');\n",
            )
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const { fork } = require('node:child_process');"
                    "const child = fork(" + json.dumps(str(child)) + ", [], {"
                    "silent: true, execPath: '/bin/false', "
                    "execArgv: ['-e', 'process.exit(99)']});"
                    "let output = '';"
                    "child.stdout.on('data', chunk => { output += chunk; });"
                    "child.on('exit', status => {"
                    "if (status !== 0 || output.trim() !== 'SANITIZED_FORK_OK') "
                    "process.exit(53);"
                    "});\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_direct_process_dlopen_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            addon = self._write(root, "addon.node", b"not-an-elf")
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "try { process.dlopen({ exports: {} }, "
                    + json.dumps(str(addon))
                    + "); process.exit(41); } "
                    "catch (error) { "
                    "if (error.code !== 'NODE_RUNTIME_NATIVE_ADDON_REJECTED') "
                    "process.exit(42); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_fork_repairs_custom_environment_and_keeps_loader(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            outside = self._write(
                workspace,
                "outside.cjs",
                b"module.exports = 'FORK_ENV_BYPASS';\n",
            )
            child = self._write(
                root,
                "child.cjs",
                (
                    "console.log(require("
                    + json.dumps(str(outside))
                    + "));\n"
                ).encode("utf-8"),
            )
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const { fork } = require('node:child_process');"
                    "const child = fork("
                    + json.dumps(str(child))
                    + ", [], { silent: true, env: { CUSTOM: 'yes' } });"
                    "let stdout = '';"
                    "child.stdout.on('data', chunk => { stdout += chunk; });"
                    "child.on('exit', status => {"
                    "if (status === 0 || stdout.includes('FORK_ENV_BYPASS')) "
                    "process.exit(43);"
                    "});\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)

            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("FORK_ENV_BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
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

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_commonjs_extension_handler_cannot_bypass_verified_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "Module._extensions['.cjs'] = module => {"
                    "module.exports = 'MODULE_EXTENSIONS_BYPASS'; };"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.cjs",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_commonjs_central_loader_references_cannot_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "const extensions = Module._extensions;"
                    "for (const mutate of ["
                    "() => { Module._load = () => 'MODULE_LOAD_BYPASS'; },"
                    "() => { Module._extensions = {'.cjs': m => { "
                    "m.exports = 'EXTENSIONS_CONTAINER_BYPASS'; }}; },"
                    "() => { Module.prototype.load = function () { "
                    "this.exports = 'MODULE_PROTOTYPE_LOAD_BYPASS'; }; },"
                    "() => { Module.prototype._compile = function () { "
                    "this.exports = 'MODULE_COMPILE_BYPASS'; }; },"
                    "() => { Module.prototype = { load() { "
                    "this.exports = 'MODULE_PROTOTYPE_CONTAINER_BYPASS'; }}; }]) {"
                    "try { mutate(); } catch (error) { if (!(error instanceof "
                    "TypeError)) process.exit(97); }}"
                    "if (Module._extensions !== extensions) process.exit(96);"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.cjs",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_unapproved_javascript_extension_handler_cannot_replace_source(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "try { Module._extensions['.js'] = module => {"
                    "module.exports = 'JS_HANDLER_BYPASS'; }; }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_EXTENSION_LOADER_REJECTED') process.exit(97); }"
                    "if (require('./dependency.js') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.js",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_readable_listener_methods_cannot_replace_stream_bytes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "const { Readable } = require('node:stream');"
                    "for (const name of ['on', 'addListener', 'once']) {"
                    "Readable.prototype[name] = function (event, listener) {"
                    "if (event === 'data') listener(Buffer.from("
                    "'READABLE_LISTENER_BYPASS')); return this; }; }"
                    "let output = ''; const stream = fs.createReadStream("
                    "require('node:path').resolve(__dirname, 'asset.txt'));"
                    "stream.on('data', chunk => { output += chunk.toString(); });"
                    "stream.once('end', () => { if (output !== 'trusted') "
                    "process.exit(98); });\n"
                ).encode("utf-8"),
            )
            self._write(root, "asset.txt", b"trusted")
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_injected_commonjs_cache_entry_cannot_replace_verified_module(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "const path = require('node:path');"
                    "const resolved = path.resolve(__dirname, 'dependency.cjs');"
                    "Module._cache[resolved] = { exports: "
                    "'MODULE_CACHE_BYPASS', loaded: true };"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.cjs",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_module_require_cannot_replace_verified_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "try { Module.prototype.require = () => "
                    "'MODULE_REQUIRE_BYPASS'; } catch (error) {"
                    "if (!(error instanceof TypeError)) process.exit(97); }"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.cjs",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_module_require_instrumentation_assignment_is_safely_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "'use strict';"
                    "const Module = require('node:module');"
                    "const original = Module.prototype.require;"
                    "Module.prototype.require = function patched(request) {"
                    "return original.call(this, request); };"
                    "if (Module.prototype.require !== original) process.exit(96);"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.cjs",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_nonconfigurable_injected_cache_entry_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "const resolved = require('node:path').resolve("
                    "__dirname, 'dependency.cjs');"
                    "Object.defineProperty(Module._cache, resolved, {"
                    "value: {exports: 'NONCONFIG_CACHE_BYPASS', loaded: true},"
                    "configurable: false}); require('./dependency.cjs');\n"
                ).encode("utf-8"),
            )
            self._write(root, "dependency.cjs", b"module.exports = 'trusted';\n")
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_CACHE_REJECTED", completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_inherited_commonjs_cache_getter_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "const path = require('node:path');"
                    "const resolved = path.resolve(__dirname, 'dependency.cjs');"
                    "const cache = Module._cache; const prototype = {};"
                    "Object.defineProperty(prototype, resolved, {"
                    "configurable: true, get() {"
                    "const fake = new Module(resolved, module);"
                    "fake.filename = resolved;"
                    "fake.paths = Module._nodeModulePaths(path.dirname(resolved));"
                    "Object.defineProperty(cache, resolved, {value: fake,"
                    "writable: true, configurable: true});"
                    "Module.prototype.load.call(fake, resolved);"
                    "fake.exports = 'INHERITED_CACHE_GETTER_BYPASS';"
                    "return fake; }});"
                    "Object.setPrototypeOf(cache, prototype);"
                    "console.log(require('./dependency.cjs'));\n"
                ).encode("utf-8"),
            )
            self._write(root, "dependency.cjs", b"module.exports = 'trusted';\n")
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_CACHE_REJECTED", completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_late_inherited_commonjs_cache_getter_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "const path = require('node:path');"
                    "const parentFilename = __filename;"
                    "const resolved = path.resolve(__dirname, 'dependency.cjs');"
                    "const cache = Module._cache; const prototype = {};"
                    "Object.defineProperty(prototype, resolved, {"
                    "configurable: true, get() {"
                    "const fake = new Module(resolved, module);"
                    "fake.filename = resolved;"
                    "fake.paths = Module._nodeModulePaths(path.dirname(resolved));"
                    "Object.defineProperty(cache, resolved, {value: fake,"
                    "writable: true, configurable: true});"
                    "Module.prototype.load.call(fake, resolved);"
                    "fake.exports = 'LATE_INHERITED_CACHE_GETTER_BYPASS';"
                    "return fake; }});"
                    "Object.defineProperty(module, 'filename', {"
                    "configurable: true, get() {"
                    "Object.setPrototypeOf(cache, prototype);"
                    "return parentFilename; }});"
                    "console.log(require('./dependency.cjs'));\n"
                ).encode("utf-8"),
            )
            self._write(root, "dependency.cjs", b"module.exports = 'trusted';\n")
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_CACHE_REJECTED", completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_active_module_cache_identity_cannot_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                b"require('./active.cjs');\n",
            )
            self._write(
                root,
                "active.cjs",
                (
                    "const Module = require('node:module');"
                    "Module._cache[__filename] = {exports: "
                    "'ACTIVE_CACHE_BYPASS', loaded: true};"
                    "require('./active.cjs');\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_CACHE_REJECTED", completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_direct_module_load_cannot_publish_completion_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "const resolved = require('node:path').resolve("
                    "__dirname, 'dependency.cjs');"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(96); const real = Module._cache[resolved];"
                    "const fake = new Module(resolved); Module._cache[resolved] = fake;"
                    "try { Module.prototype.load.call(fake, resolved); "
                    "process.exit(97); } catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_CACHE_REJECTED') process.exit(95); }"
                    "Module._cache[resolved] = real;"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(root, "dependency.cjs", b"module.exports = 'trusted';\n")
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_bare_builtin_name_ignores_injected_commonjs_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const Module = require('node:module');"
                    "Module._cache.fs = {exports: "
                    "'BUILTIN_CACHE_BYPASS', loaded: true};"
                    "const fs = require('fs');"
                    "if (!fs || typeof fs.readFileSync !== 'function') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_post_load_cache_replacement_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                b"require('./dependency.cjs');\n",
            )
            self._write(
                root,
                "dependency.cjs",
                (
                    "require('node:module')._cache[__filename] = {"
                    "exports: 'POSTLOAD_CACHE_BYPASS', loaded: true};"
                    "module.exports = 'trusted';\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_CACHE_REJECTED", completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_post_return_cache_prototype_mutation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                b"console.log(require('./dependency.cjs'));\n",
            )
            self._write(
                root,
                "dependency.cjs",
                (
                    "Object.setPrototypeOf("
                    "require('node:module')._cache, {});"
                    "module.exports = 'POST_RETURN_CACHE_PROTOTYPE_MUTATION';\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_CACHE_REJECTED", completed.stderr)
        self.assertNotIn("MUTATION", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_module_own_require_and_prototype_rebase_cannot_bypass_loader(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "try { Object.defineProperty(module, 'require', {"
                    "value: () => 'OWN_REQUIRE_BYPASS'}); process.exit(97); }"
                    "catch (error) { if (!(error instanceof TypeError)) "
                    "process.exit(96); }"
                    "Object.setPrototypeOf(module, {require: () => "
                    "'PROTOTYPE_REBASE_BYPASS'});"
                    "if (require('./dependency.cjs') !== 'trusted') "
                    "process.exit(98);\n"
                ).encode("utf-8"),
            )
            self._write(root, "dependency.cjs", b"module.exports = 'trusted';\n")
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_buffer_to_string_cannot_replace_verified_module(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "Buffer.prototype.toString = function() {"
                    "return \"module.exports = 'BUFFER_BYPASS';\"; };"
                    "console.log(require('./dependency.cjs'));\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.cjs",
                b"module.exports = 'trusted';\n",
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "trusted")
        self.assertNotIn("BUFFER_BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_string_methods_cannot_replace_verified_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "String.prototype.charCodeAt = () => 0xFEFF;"
                    "String.prototype.slice = () => "
                    "'{\\\"value\\\":\\\"STRING_BYPASS\\\"}';"
                    "console.log(require('./dependency.json').value);\n"
                ).encode("utf-8"),
            )
            self._write(
                root,
                "dependency.json",
                b'{"value":"trusted"}\n',
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "trusted")
        self.assertNotIn("STRING_BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
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

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_commonjs_package_metadata_is_verified_before_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            package = root / "node_modules/pkg"
            package.mkdir(parents=True)
            entry = self._write(root, "entry.cjs", b"console.log(require('pkg'));\n")
            metadata = self._write(
                root,
                "node_modules/pkg/package.json",
                b'{"main":"trusted.cjs"}\n',
            )
            self._write(
                root,
                "node_modules/pkg/trusted.cjs",
                b"module.exports = 'trusted';\n",
            )
            self._write(
                root,
                "node_modules/pkg/changed.cjs",
                b"module.exports = 'changed';\n",
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

            completed = self._run_node(arguments, manifest=payloads[0])
            metadata.write_bytes(b'{"main":"changed.cjs"}\n')
            metadata.chmod(0o600)
            tampered = self._run_node(arguments, manifest=payloads[0])

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "trusted")
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_SHA256_MISMATCH", tampered.stderr)
        self.assertNotIn("changed", tampered.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_mutated_set_add_cannot_skip_package_metadata_verification(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            package = root / "node_modules/pkg"
            package.mkdir(parents=True)
            metadata = self._write(
                root,
                "node_modules/pkg/package.json",
                b'{"main":"trusted.cjs"}\n',
            )
            self._write(
                root,
                "node_modules/pkg/trusted.cjs",
                b"module.exports = 'trusted';\n",
            )
            self._write(
                root,
                "node_modules/pkg/changed.cjs",
                b"module.exports = 'SET_ADD_BYPASS';\n",
            )
            entry = self._write(
                root,
                "entry.cjs",
                (
                    "const fs = require('node:fs');"
                    "Set.prototype.add = function() { return this; };"
                    "fs.writeFileSync("
                    + json.dumps(str(metadata))
                    + ", '{\\\"main\\\":\\\"changed.cjs\\\"}');"
                    "try { require('pkg'); process.exit(102); }"
                    "catch (error) { if (error.code !== "
                    "'NODE_RUNTIME_MODULE_SHA256_MISMATCH') process.exit(103); }\n"
                ).encode("utf-8"),
            )
            payloads = self._payload_files(root, workspace)
            completed = self._run_node(
                [
                    "--preserve-symlinks",
                    "--require",
                    str(payloads[1]),
                    "--experimental-loader",
                    str(payloads[2]),
                    str(entry),
                ],
                manifest=payloads[0],
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("SET_ADD_BYPASS", completed.stdout)

    @unittest.skipUnless(_NODE_BINARY, "Node.js is not installed")
    def test_esm_package_type_is_verified_before_format_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            root = workspace / "runtime"
            root.mkdir(mode=0o700)
            metadata = self._write(root, "package.json", b'{"type":"module"}\n')
            entry = self._write(
                root,
                "entry.js",
                b"console.log('trusted-format');\n",
            )
            payloads = self._payload_files(root, workspace)
            arguments = ["--experimental-loader", str(payloads[2]), str(entry)]

            completed = self._run_node(arguments, manifest=payloads[0])
            metadata.write_bytes(b'{"type":"commonjs"}\n')
            metadata.chmod(0o600)
            tampered = self._run_node(arguments, manifest=payloads[0])

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "trusted-format")
        self.assertNotEqual(tampered.returncode, 0)
        self.assertIn("NODE_RUNTIME_MODULE_SHA256_MISMATCH", tampered.stderr)
        self.assertNotIn("trusted-format", tampered.stdout)

    def _payload_files(
        self,
        root: Path,
        workspace: Path,
        *,
        excluded_top_level_directories: frozenset[str] = frozenset(),
    ) -> tuple[Path, Path, Path]:
        digest = build_node_runtime_manifest(
            root,
            excluded_top_level_directories=excluded_top_level_directories,
        ).digest
        payloads = build_node_runtime_integrity_payloads(
            root,
            expected_digest=digest,
            excluded_top_level_directories=excluded_top_level_directories,
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
        environment = {
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "NODE": str(_NODE_BINARY),
            MANIFEST_ENV: str(manifest),
        }
        if "--require" in arguments:
            environment["NAC_NODE_RUNTIME_PRELOADER"] = arguments[
                arguments.index("--require") + 1
            ]
        if "--experimental-loader" in arguments:
            environment["NAC_NODE_RUNTIME_ESM_LOADER"] = arguments[
                arguments.index("--experimental-loader") + 1
            ]
        return subprocess.run(
            [str(_NODE_BINARY), *arguments],
            check=False,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=environment,
            timeout=20,
        )


if __name__ == "__main__":
    unittest.main()
