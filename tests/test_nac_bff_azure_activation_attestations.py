from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nac_bff.azure_activation_attestations import build_activation_attestation_plan
from nac_bff.azure_activation_runner import _sha256_json
from nac_m365_graph.node_runtime_integrity import build_node_runtime_manifest


class AzureBffActivationAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def _file(self, name: str, content: bytes, mode: int) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(mode)
        return path

    def test_plan_emits_exact_eight_digests_and_runner_combined_hash(self) -> None:
        paths = {
            "m365_cli_path": self._file("m365-runtime/dist/index.js", b"m365", 0o700),
            "m365_node_path": self._file("m365-node", b"node", 0o700),
            "build_python_path": self._file("build-python", b"python", 0o700),
            "build_node_path": self._file("build-node", b"build", 0o700),
            "build_npm_cli_path": self._file("npm-runtime/bin/npm-cli.js", b"npm", 0o600),
            "gh_cli_path": self._file("gh", b"gh", 0o700),
            "provisioner_certificate_path": self._file("cert.pem", b"cert", 0o600),
        }
        azure = self._file("az", b"azure-toolchain", 0o700)
        execution_paths = {
            "azure_cli": azure,
            "m365_cli": paths["m365_cli_path"],
            "m365_node": paths["m365_node_path"],
            "build_python": paths["build_python_path"],
            "build_node": paths["build_node_path"],
            "build_npm_cli": paths["build_npm_cli_path"],
            "gh_cli": paths["gh_cli_path"],
        }
        with (
            patch.dict(
                "nac_bff.azure_activation_attestations._EXECUTION_PATHS",
                execution_paths,
                clear=True,
            ),
            patch(
                "nac_bff.azure_activation_attestations."
                "calculate_azure_cli_toolchain_sha256",
                return_value="1" * 64,
            ),
        ):
            result = build_activation_attestation_plan(
                azure_cli_path=azure,
                **paths,
            )

        self.assertEqual(result["status"], "READY")
        attestations = result["toolchain_attestations"]
        self.assertEqual(len(attestations), 8)
        self.assertEqual(
            attestations["m365_cli_sha256"],
            build_node_runtime_manifest(
                paths["m365_cli_path"].parent.parent
            ).digest,
        )
        self.assertEqual(
            attestations["build_npm_cli_sha256"],
            hashlib.sha256(b"npm").hexdigest(),
        )
        self.assertEqual(result["toolchain_attestations_sha256"], _sha256_json(attestations))
        self.assertEqual(set(result["live_cli_arguments"].values()), set(attestations.values()))
        self.assertIs(result["reads_private_key"], False)
        self.assertIs(result["executes_provider_requests"], False)

    def test_plan_rejects_symlink_or_group_writable_input(self) -> None:
        trusted = self._file("trusted", b"trusted", 0o700)
        symlink = self.root / "m365"
        symlink.symlink_to(trusted)
        certificate = self._file("cert.pem", b"cert", 0o600)
        execution_paths = {
            "azure_cli": trusted,
            "m365_cli": symlink,
            "m365_node": trusted,
            "build_python": trusted,
            "build_node": trusted,
            "build_npm_cli": trusted,
            "gh_cli": trusted,
        }
        with (
            patch.dict(
                "nac_bff.azure_activation_attestations._EXECUTION_PATHS",
                execution_paths,
                clear=True,
            ),
            patch(
                "nac_bff.azure_activation_attestations."
                "calculate_azure_cli_toolchain_sha256",
                return_value="1" * 64,
            ),
        ):
            result = build_activation_attestation_plan(
                azure_cli_path=trusted,
                m365_cli_path=symlink,
                m365_node_path=trusted,
                build_python_path=trusted,
                build_node_path=trusted,
                build_npm_cli_path=trusted,
                gh_cli_path=trusted,
                provisioner_certificate_path=certificate,
            )
        self.assertEqual(result["status"], "NOT_READY")
        self.assertNotIn("toolchain_attestations", result)

    def test_plan_rejects_path_not_used_by_live_factory(self) -> None:
        foreign = self._file("foreign-node", b"node", 0o700)
        certificate = self._file("cert.pem", b"cert", 0o600)

        result = build_activation_attestation_plan(
            provisioner_certificate_path=certificate,
            build_node_path=foreign,
        )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            result["error"]["code"], "EXECUTION_ATTESTATION_PATH_MISMATCH"
        )
        self.assertNotIn("toolchain_attestations", result)

    def test_plan_never_hashes_or_accepts_private_key_argument(self) -> None:
        signature = __import__("inspect").signature(build_activation_attestation_plan)
        self.assertNotIn("private_key", " ".join(signature.parameters))
