from __future__ import annotations

import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "plugins" / "noc-pkcs7-certbundle" / "scripts" / "inspect_certbundle.py"


def load_certbundle_module():
    spec = importlib.util.spec_from_file_location("inspect_certbundle", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


certbundle = load_certbundle_module()


def pkcs7_pem(body: str) -> bytes:
    return (
        f"{certbundle.PEM_BEGIN}{certbundle.PKCS7_LABEL}{certbundle.PEM_CLOSE}\n"
        f"{body}\n"
        f"{certbundle.PEM_END}{certbundle.PKCS7_LABEL}{certbundle.PEM_CLOSE}\n"
    ).encode("utf-8")


class Pkcs7CertBundleTests(unittest.TestCase):
    def test_no_input_is_manual_review_and_non_signing(self) -> None:
        args = argparse.Namespace(input=None, max_bytes=certbundle.MAX_INPUT_BYTES)
        evidence = certbundle.build_evidence(args)

        self.assertEqual(evidence["plugin"], "noc-pkcs7-certbundle")
        self.assertEqual(evidence["overall_status"], "manual_review")
        self.assertFalse(evidence["policy"]["private_key_loaded"])
        self.assertFalse(evidence["policy"]["pkcs12_pfx_imported"])
        self.assertFalse(evidence["policy"]["signature_created"])
        self.assertFalse(evidence["policy"]["signature_verified"])
        self.assertFalse(evidence["policy"]["certificate_material_stored"])

    def test_pfx_is_blocked_as_out_of_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "token.pfx"
            path.write_bytes(b"not a real token")
            args = argparse.Namespace(input=path, max_bytes=certbundle.MAX_INPUT_BYTES)
            evidence = certbundle.build_evidence(args)

        self.assertEqual(evidence["overall_status"], "blocked")
        self.assertIn("out of scope", str(evidence["checks"]).lower())

    def test_pem_pkcs7_is_classified_without_raw_material(self) -> None:
        payload = pkcs7_pem("fixture-body")
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "bundle.p7b"
            path.write_bytes(payload)
            detected = certbundle.detect_container_format(path, payload)

        self.assertEqual(detected["kind"], "pem_pkcs7")
        self.assertEqual(detected["encoding"], "pem")

    def test_successful_openssl_parse_can_mark_ready(self) -> None:
        original_command_exists = certbundle.command_exists
        original_run_command = certbundle.run_command
        original_platform_system = certbundle.platform.system

        def fake_command_exists(command: str) -> bool:
            return command == "openssl"

        def fake_run_command(command, timeout=5.0):
            if command[:2] == ["openssl", "pkcs7"]:
                return 0, "subject=CN=Example\nissuer=CN=Example CA\n", ""
            return 1, "", "unexpected command"

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "bundle.p7b"
            path.write_bytes(pkcs7_pem("fixture-body"))
            certbundle.command_exists = fake_command_exists
            certbundle.run_command = fake_run_command
            certbundle.platform.system = lambda: "Linux"
            try:
                evidence = certbundle.build_evidence(
                    argparse.Namespace(input=path, max_bytes=certbundle.MAX_INPUT_BYTES)
                )
            finally:
                certbundle.command_exists = original_command_exists
                certbundle.run_command = original_run_command
                certbundle.platform.system = original_platform_system

        serialized = str(evidence)
        self.assertEqual(evidence["overall_status"], "ready")
        self.assertIn("openssl_parse", serialized)
        self.assertNotIn("fixture-body", serialized)


if __name__ == "__main__":
    unittest.main()
