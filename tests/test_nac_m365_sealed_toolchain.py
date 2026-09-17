from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from nac_m365_graph.sealed_toolchain import (
    SealedToolchainError,
    sealed_artifacts,
    sealed_toolchain,
    verified_tool_bytes,
)


class SealedToolchainTests(unittest.TestCase):
    def test_sealed_execution_is_immune_to_source_path_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            tool = Path(temporary) / "tool"
            original = b"#!/bin/sh\nprintf original\n"
            tool.write_bytes(original)
            tool.chmod(0o700)
            digest = hashlib.sha256(original).hexdigest()

            with sealed_toolchain(((tool, True, digest),)) as sealed:
                if os.name == "nt":
                    self.assertEqual(sealed.paths, (str(tool),))
                    self.assertEqual(sealed.pass_fds, ())
                    with self.assertRaises(PermissionError):
                        tool.write_bytes(b"replaced")
                    self.assertEqual(tool.read_bytes(), original)
                    completed = None
                else:
                    tool.write_bytes(b"#!/bin/sh\nprintf replaced\n")
                    tool.chmod(0o700)
                    completed = subprocess.run(
                        [sealed.paths[0]],
                        check=False,
                        capture_output=True,
                        text=True,
                        pass_fds=sealed.pass_fds,
                    )
                    with self.assertRaises(OSError):
                        os.write(sealed.pass_fds[0], b"tamper")

        if completed is not None:
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(completed.stdout, "original")

    def test_sealed_artifact_preserves_name_and_realpath_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "nac-bpmn-viewer.sppkg"
            artifact.write_bytes(b"approved-package")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

            with sealed_artifacts(((artifact, digest),)) as sealed:
                provider_path = sealed.paths[0]
                self.assertEqual(Path(provider_path).name, artifact.name)
                resolved = Path(os.path.realpath(provider_path))
                self.assertEqual(resolved.read_bytes(), b"approved-package")
                if os.name == "nt":
                    self.assertEqual(sealed.pass_fds, ())
                else:
                    self.assertIn(sealed.pass_fds[0], (sealed.pass_fds[0],))

    def test_sealed_artifact_detects_provider_mutation_on_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "nac-bpmn-viewer.sppkg"
            artifact.write_bytes(b"approved-package")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

            if os.name == "nt":
                with sealed_artifacts(((artifact, digest),)) as sealed:
                    provider_path = Path(os.path.realpath(sealed.paths[0]))
                    with self.assertRaises(PermissionError):
                        provider_path.write_bytes(b"provider-mutation")
                self.assertEqual(artifact.read_bytes(), b"approved-package")
            else:
                with self.assertRaisesRegex(
                    SealedToolchainError,
                    "^SEALED_TOOLCHAIN_SHA256_MISMATCH$",
                ):
                    with sealed_artifacts(((artifact, digest),)) as sealed:
                        provider_path = Path(os.path.realpath(sealed.paths[0]))
                        provider_path.chmod(0o600)
                        provider_path.write_bytes(b"provider-mutation")
                        provider_path.chmod(0o400)

    def test_sealed_artifact_detects_provider_mode_change_on_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "nac-bpmn-viewer.sppkg"
            artifact.write_bytes(b"approved-package")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

            if os.name == "nt":
                os.link(artifact, Path(temporary) / "artifact-hardlink")
                with self.assertRaises(SealedToolchainError):
                    with sealed_artifacts(((artifact, digest),)):
                        self.fail("hard-linked artifact must not be exposed")
            else:
                with self.assertRaisesRegex(
                    SealedToolchainError,
                    "^SEALED_ARTIFACT_POST_USE_MODE_MISMATCH$",
                ):
                    with sealed_artifacts(((artifact, digest),)) as sealed:
                        provider_path = Path(os.path.realpath(sealed.paths[0]))
                        provider_path.chmod(0o600)

    def test_verified_bytes_reject_digest_drift_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tool = root / "tool"
            tool.write_bytes(b"trusted")
            tool.chmod(0o700)
            digest = hashlib.sha256(tool.read_bytes()).hexdigest()
            self.assertEqual(
                verified_tool_bytes(
                    tool,
                    executable=True,
                    expected_sha256=digest,
                ),
                b"trusted",
            )
            tool.write_bytes(b"changed")
            with self.assertRaisesRegex(
                SealedToolchainError,
                "^SEALED_TOOLCHAIN_SHA256_MISMATCH$",
            ):
                verified_tool_bytes(
                    tool,
                    executable=True,
                    expected_sha256=digest,
                )
            if os.name == "nt":
                target_directory = root / "target-directory"
                target_directory.mkdir()
                target = target_directory / "tool"
                target.write_bytes(b"trusted")
                link = root / "link-directory"
                subprocess.run(
                    [
                        "cmd.exe",
                        "/d",
                        "/c",
                        "mklink",
                        "/J",
                        str(link),
                        str(target_directory),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                linked_tool = link / "tool"
            else:
                target = root / "target"
                target.write_bytes(b"trusted")
                target.chmod(0o700)
                linked_tool = root / "link"
                linked_tool.symlink_to(target)
            with self.assertRaises(SealedToolchainError):
                verified_tool_bytes(
                    linked_tool,
                    executable=True,
                    expected_sha256=digest,
                )


if __name__ == "__main__":
    unittest.main()
