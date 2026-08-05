from __future__ import annotations

import io
import json
import socket
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402


ACTIVATION_HASH = "a" * 64
APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/735#issuecomment-123456"
)
CORRELATION_ID = "nac-bff-performance-20260804"
MONITOR_ANCHOR = "2026-08-04T10:00:00Z"
FINAL_EVIDENCE_HASH = "b" * 64
COMPLETION_MANIFEST_HASH = "c" * 64


class BffPerformanceAcceptanceCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._temporary_directory.cleanup)
        root = Path(self._temporary_directory.name)
        self.toolchain_path = root / "toolchain.json"
        self.infrastructure_path = root / "infrastructure.json"
        self.worm_path = root / "worm.json"
        self.provisioner_state = root / "provisioner-state.json"
        self.certificate_path = root / "provisioner.cert.pem"
        self.private_key_path = root / "provisioner.key.pem"
        self.runtime_state = root / "runtime-state.json"
        self.runtime_certificate_path = root / "runtime.cert.pem"
        self.runtime_private_key_path = root / "runtime.key.pem"
        self.toolchain = {"toolchain": "bound"}
        self.infrastructure = {"infrastructure": "bound"}
        self.worm = {"worm": "bound"}
        self.toolchain_path.write_text(json.dumps(self.toolchain), encoding="utf-8")
        self.infrastructure_path.write_text(
            json.dumps(self.infrastructure), encoding="utf-8"
        )
        self.worm_path.write_text(json.dumps(self.worm), encoding="utf-8")
        self.provisioner_state.write_text("{}", encoding="utf-8")
        self.certificate_path.write_text("certificate", encoding="utf-8")
        self.private_key_path.write_text("private-key", encoding="utf-8")
        self.runtime_state.write_text("{}", encoding="utf-8")
        self.runtime_certificate_path.write_text("certificate", encoding="utf-8")
        self.runtime_private_key_path.write_text("private-key", encoding="utf-8")

    def _argv(self, *extra: str) -> list[str]:
        return [
            "m365",
            "teams-sharepoint",
            "bff-performance-acceptance",
            "--repo-root",
            str(REPO_ROOT),
            "--owner-approved",
            "--execute-live-acceptance",
            "--approval-reference",
            APPROVAL_REFERENCE,
            "--expected-activation-hash",
            ACTIVATION_HASH,
            "--correlation-id",
            CORRELATION_ID,
            "--monitor-window-anchor-utc",
            MONITOR_ANCHOR,
            "--toolchain-attestations-json",
            str(self.toolchain_path),
            "--infrastructure-parameters-json",
            str(self.infrastructure_path),
            "--worm-baseline-parameters-json",
            str(self.worm_path),
            "--provisioner-state",
            str(self.provisioner_state),
            "--provisioner-certificate-path",
            str(self.certificate_path),
            "--provisioner-private-key-path",
            str(self.private_key_path),
            "--runtime-state",
            str(self.runtime_state),
            "--runtime-certificate-path",
            str(self.runtime_certificate_path),
            "--runtime-private-key-path",
            str(self.runtime_private_key_path),
            *extra,
        ]

    @staticmethod
    def _module(result: object) -> tuple[types.ModuleType, Mock]:
        run = Mock(return_value=result)
        module = types.ModuleType("nac_bff.azure_performance_composition")
        module.run_azure_performance_acceptance_live = run
        return module, run

    def _invoke(self, argv: list[str]) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = nac_cli.main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_closed_gate_precedes_files_imports_and_network(self) -> None:
        module, run = self._module({"status": "PASSED"})
        with (
            patch.dict(
                sys.modules,
                {"nac_bff.azure_performance_composition": module},
            ),
            patch.object(
                nac_cli,
                "_read_bff_performance_acceptance_json",
                side_effect=AssertionError("files must remain unread"),
            ),
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("provider process"),
            ),
        ):
            rc, stdout, stderr = self._invoke(
                [
                    "m365",
                    "teams-sharepoint",
                    "bff-performance-acceptance",
                    "--format",
                    "json",
                ]
            )

        self.assertEqual(rc, 2)
        self.assertEqual(stderr, "")
        self.assertEqual(
            json.loads(stdout),
            {
                "schema_version": "nac.m365-bff-performance-acceptance-cli/v1",
                "status": "BLOCKED",
                "error": {
                    "code": "PERFORMANCE_ACCEPTANCE_OWNER_GATE_CLOSED"
                },
                "live_execution_invoked": False,
            },
        )
        run.assert_not_called()

    def test_every_explicit_input_is_required_with_redacted_error(self) -> None:
        required_value_options = (
            "--repo-root",
            "--approval-reference",
            "--expected-activation-hash",
            "--correlation-id",
            "--monitor-window-anchor-utc",
            "--toolchain-attestations-json",
            "--infrastructure-parameters-json",
            "--worm-baseline-parameters-json",
            "--provisioner-state",
            "--provisioner-certificate-path",
            "--provisioner-private-key-path",
            "--runtime-state",
            "--runtime-certificate-path",
            "--runtime-private-key-path",
        )
        module, run = self._module({"status": "PASSED"})
        with patch.dict(
            sys.modules,
            {"nac_bff.azure_performance_composition": module},
        ):
            for option in required_value_options:
                with self.subTest(option=option):
                    argv = self._argv("--format", "json")
                    index = argv.index(option)
                    del argv[index : index + 2]
                    rc, stdout, stderr = self._invoke(argv)
                    self.assertEqual(rc, 2)
                    self.assertEqual(stderr, "")
                    self.assertEqual(
                        json.loads(stdout)["error"]["code"],
                        "PERFORMANCE_ACCEPTANCE_INPUT_INVALID",
                    )
        run.assert_not_called()

    def test_caller_supplied_binding_hashes_are_rejected(self) -> None:
        module, run = self._module({"status": "PASSED"})
        caller_hash_options = (
            "--approval-body-sha256",
            "--approved-commit",
            "--approved-tree",
            "--contract-sha256",
            "--infrastructure-binding-sha256",
            "--target-binding-sha256",
        )
        with patch.dict(
            sys.modules,
            {"nac_bff.azure_performance_composition": module},
        ):
            for option in caller_hash_options:
                with self.subTest(option=option):
                    rc, stdout, stderr = self._invoke(
                        self._argv(option, "d" * 64, "--format", "json")
                    )
                    self.assertEqual(rc, 2)
                    self.assertEqual(stderr, "")
                    self.assertEqual(
                        json.loads(stdout)["error"]["code"],
                        "PERFORMANCE_ACCEPTANCE_INPUT_INVALID",
                    )
        run.assert_not_called()

    def test_duplicate_live_gate_flags_are_rejected_before_import(self) -> None:
        module, run = self._module({"status": "PASSED"})
        for flag in ("--owner-approved", "--execute-live-acceptance"):
            with self.subTest(flag=flag), patch.dict(
                sys.modules,
                {"nac_bff.azure_performance_composition": module},
            ):
                rc, stdout, stderr = self._invoke(
                    self._argv(flag, "--format", "json")
                )
                self.assertEqual(rc, 2)
                self.assertEqual(stderr, "")
                self.assertEqual(
                    json.loads(stdout)["error"]["code"],
                    "PERFORMANCE_ACCEPTANCE_OWNER_GATE_CLOSED",
                )
        run.assert_not_called()

    def test_invalid_json_stops_before_runtime_import(self) -> None:
        self.infrastructure_path.write_text("provider-secret{", encoding="utf-8")
        module, run = self._module({"status": "PASSED"})
        with patch.dict(
            sys.modules,
            {"nac_bff.azure_performance_composition": module},
        ):
            rc, stdout, stderr = self._invoke(self._argv("--format", "json"))

        self.assertEqual(rc, 2)
        self.assertEqual(stderr, "")
        self.assertEqual(
            json.loads(stdout)["error"]["code"],
            "PERFORMANCE_ACCEPTANCE_INPUT_INVALID",
        )
        self.assertNotIn("provider-secret", stdout)
        run.assert_not_called()

    def test_explicit_inputs_are_forwarded_to_lazy_entry_point_offline(self) -> None:
        module, run = self._module(
            {
                "status": "PASSED",
                "final_evidence_sha256": FINAL_EVIDENCE_HASH,
                "completion_manifest_sha256": COMPLETION_MANIFEST_HASH,
                "provider_url": "https://provider.invalid/private",
                "authorization": "Bearer must-not-escape",
            }
        )
        with (
            patch.dict(
                sys.modules,
                {"nac_bff.azure_performance_composition": module},
            ),
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(
                subprocess,
                "run",
                side_effect=AssertionError("provider process"),
            ),
        ):
            rc, stdout, stderr = self._invoke(self._argv("--format", "json"))

        self.assertEqual(rc, 0)
        self.assertEqual(stderr, "")
        run.assert_called_once_with(
            repo_root=REPO_ROOT,
            owner_approved=True,
            execute_live_acceptance=True,
            approval_reference=APPROVAL_REFERENCE,
            expected_activation_hash=ACTIVATION_HASH,
            correlation_id=CORRELATION_ID,
            monitor_window_anchor_utc=MONITOR_ANCHOR,
            toolchain_attestations=self.toolchain,
            infrastructure_parameters=self.infrastructure,
            worm_baseline_parameters=self.worm,
            provisioner_state_path=self.provisioner_state,
            provisioner_certificate_path=self.certificate_path,
            provisioner_private_key_path=self.private_key_path,
            runtime_state_path=self.runtime_state,
            runtime_certificate_path=self.runtime_certificate_path,
            runtime_private_key_path=self.runtime_private_key_path,
        )
        self.assertEqual(
            json.loads(stdout),
            {
                "schema_version": "nac.m365-bff-performance-acceptance-cli/v1",
                "status": "PASSED",
                "final_evidence_sha256": FINAL_EVIDENCE_HASH,
                "completion_manifest_sha256": COMPLETION_MANIFEST_HASH,
            },
        )
        self.assertNotIn("provider.invalid", stdout)
        self.assertNotIn("Bearer", stdout)

    def test_runtime_and_execution_failures_are_fixed_and_redacted(self) -> None:
        secret = "provider-token-must-not-escape"
        cases = (
            (None, "PERFORMANCE_ACCEPTANCE_RUNTIME_UNAVAILABLE", False),
            (RuntimeError(secret), "PERFORMANCE_ACCEPTANCE_EXECUTION_FAILED", True),
        )
        for failure, expected_code, invoked in cases:
            with self.subTest(expected_code=expected_code):
                module = types.ModuleType("nac_bff.azure_performance_composition")
                if failure is not None:
                    module.run_azure_performance_acceptance_live = Mock(
                        side_effect=failure
                    )
                with patch.dict(
                    sys.modules,
                    {"nac_bff.azure_performance_composition": module},
                ):
                    rc, stdout, stderr = self._invoke(
                        self._argv("--format", "json")
                    )
                payload = json.loads(stdout)
                self.assertEqual(rc, 2)
                self.assertEqual(stderr, "")
                self.assertEqual(payload["error"]["code"], expected_code)
                self.assertEqual(payload["live_execution_invoked"], invoked)
                self.assertNotIn(secret, stdout)

    def test_failed_result_cannot_expose_provider_details(self) -> None:
        module, run = self._module(
            {
                "status": "FAILED",
                "error": {
                    "code": "PROVIDER_DETAIL",
                    "body": "secret-response-body",
                },
                "request_url": "https://provider.invalid/private",
            }
        )
        with patch.dict(
            sys.modules,
            {"nac_bff.azure_performance_composition": module},
        ):
            rc, stdout, stderr = self._invoke(self._argv("--format", "json"))

        self.assertEqual(rc, 2)
        self.assertEqual(stderr, "")
        self.assertEqual(
            json.loads(stdout)["error"]["code"],
            "PERFORMANCE_ACCEPTANCE_RUN_FAILED",
        )
        self.assertNotIn("PROVIDER_DETAIL", stdout)
        self.assertNotIn("secret-response-body", stdout)
        self.assertNotIn("provider.invalid", stdout)
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
