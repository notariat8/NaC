from __future__ import annotations

import copy
import io
import json
import socket
import sys
import tempfile
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_cli import cli as nac_cli  # noqa: E402
from nac_m365_graph import business_case_type_write_dry_run as dry_run  # noqa: E402


class BusinessCaseTypeGraphWriteEdgeCliTests(unittest.TestCase):
    def _run(self, *extra: str, output_format: str = "json") -> tuple[int, str]:
        argv = [
            "--repo-root",
            str(ROOT),
            "m365",
            "teams-sharepoint",
            "business-case-type-write-dry-run",
            *extra,
            "--format",
            output_format,
        ]
        output = io.StringIO()
        with (
            patch.object(
                urllib.request,
                "urlopen",
                side_effect=AssertionError("HTTP must stay offline"),
            ),
            patch.object(
                socket,
                "getaddrinfo",
                side_effect=AssertionError("DNS must stay offline"),
            ),
            patch(
                "nac_m365_graph.graph_client.GraphRestClient",
                side_effect=AssertionError("no Graph client"),
            ),
            patch.object(
                nac_cli.subprocess,
                "run",
                side_effect=AssertionError("no child process"),
            ),
            redirect_stdout(output),
        ):
            exit_code = nac_cli.main(argv)
        return exit_code, output.getvalue()

    def test_all_five_operations_build_redacted_offline_plans(self) -> None:
        for operation in dry_run.WRITE_DRY_RUN_OPERATIONS:
            with self.subTest(operation=operation):
                exit_code, output = self._run("--operation", operation)
                payload = json.loads(output)

                self.assertEqual(exit_code, 0)
                self.assertEqual(payload["status"], "PASSED")
                self.assertEqual(payload["operation"], operation)
                self.assertEqual(payload["graph_version"], "v1.0")
                self.assertTrue(payload["write_request_prepared"])
                self.assertFalse(payload["write_request_executed"])
                self.assertEqual(payload["gate_results"]["graph_calls"], 0)
                self.assertEqual(payload["gate_results"]["tenant_writes"], 0)
                self.assertRegex(payload["plan_sha256"], r"[0-9a-f]{64}\Z")
                self.assertRegex(
                    payload["target_binding_sha256"], r"[0-9a-f]{64}\Z"
                )
                lowered = output.lower()
                for forbidden in (
                    "site_id",
                    "list_id",
                    "identity_id",
                    "https://",
                    "synthetic.example",
                    "syn-dry-run",
                    "token",
                    "certificate",
                    "private_key",
                ):
                    self.assertNotIn(forbidden, lowered)

    def test_text_output_is_supported(self) -> None:
        exit_code, output = self._run(output_format="text")
        self.assertEqual(exit_code, 0)
        self.assertIn("STATUS: PASSED", output)
        self.assertIn("Operation: case_create", output)
        self.assertIn("Write executed: false", output)

    def test_contract_drift_blocks_before_plan(self) -> None:
        contract = json.loads(
            (ROOT / dry_run.CONTRACT_PATH).read_text(encoding="utf-8")
        )
        drifted = copy.deepcopy(contract)
        drifted["offline_cli"]["tenant_writes_allowed"] = 1
        with tempfile.TemporaryDirectory() as directory:
            temp_root = Path(directory)
            target = temp_root / dry_run.CONTRACT_PATH
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(drifted), encoding="utf-8")
            result = dry_run.build_business_case_type_write_dry_run(temp_root)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertFalse(result["gate_results"]["contract_valid"])
        self.assertFalse(result["write_request_prepared"])

    def test_help_exposes_only_operation_and_format(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            nac_cli.main(
                [
                    "m365",
                    "teams-sharepoint",
                    "business-case-type-write-dry-run",
                    "--help",
                ]
            )
        self.assertEqual(raised.exception.code, 0)
        help_text = output.getvalue().lower()
        self.assertIn("--operation", help_text)
        self.assertIn("--format", help_text)
        for forbidden in (
            "--site-id",
            "--list-id",
            "--token",
            "--client-secret",
            "--url",
            "--runtime-certificate-path",
            "--runtime-private-key-path",
            "--owner-approved",
        ):
            self.assertNotIn(forbidden, help_text)

    def test_foreign_command_does_not_accept_write_options(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            nac_cli.main(
                [
                    "m365",
                    "teams-sharepoint",
                    "plan",
                    "--operation",
                    "case_create",
                ]
            )
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
