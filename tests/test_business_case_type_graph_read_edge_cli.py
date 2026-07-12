from __future__ import annotations

import io
import copy
import json
import tempfile
import socket
import sys
import unittest
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402
from nac_m365_graph import business_case_type_read_plan as read_plan  # noqa: E402


class BusinessCaseTypeGraphReadEdgeCliTests(unittest.TestCase):
    def _run(self, *extra: str, output_format: str = "json") -> tuple[int, str]:
        argv = [
            "--repo-root", str(REPO_ROOT), "m365", "teams-sharepoint",
            "business-case-type-read-plan", *extra, "--format", output_format,
        ]
        output = io.StringIO()
        with (
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("HTTP must stay offline")),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS must stay offline")),
            patch("nac_m365_graph.graph_client.GraphRestClient", side_effect=AssertionError("no Graph client")),
            patch.object(nac_cli.subprocess, "run", side_effect=AssertionError("no child process")),
            redirect_stdout(output),
        ):
            exit_code = nac_cli.main(argv)
        return exit_code, output.getvalue()

    def test_default_json_plan_passes_and_is_redacted(self) -> None:
        exit_code, output = self._run()
        payload = json.loads(output)

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["method"], "GET")
        self.assertEqual(payload["graph_version"], "v1.0")
        self.assertEqual(payload["logical_resource_binding"], "Vorgangsartenregister")
        self.assertEqual(
            payload["selected_field_names"],
            ["id", "eTag", "BusinessCaseTypeId", "LifecycleStatus", "Selectable", "CatalogVersion"],
        )
        self.assertEqual(payload["page_limit"], 100)
        self.assertEqual(payload["item_limit"], 1000)
        self.assertEqual(payload["response_byte_limit"], 1048576)
        self.assertTrue(all(payload["gate_results"].values()))
        lowered = output.lower()
        for forbidden in ("site_id", "list_id", "https://", "token", "credential"):
            self.assertNotIn(forbidden, lowered)

    def test_text_plan_is_supported(self) -> None:
        exit_code, output = self._run(output_format="text")

        self.assertEqual(exit_code, 0)
        self.assertIn("STATUS: PASSED", output)
        self.assertIn("Selected fields: id, eTag, BusinessCaseTypeId", output)

    def test_invalid_operation_role_permission_and_grant_are_blocked(self) -> None:
        cases = (
            ("--operation", "unknown_operation", "operation_allowed"),
            ("--role", "BackfillOperator", "role_allowed_for_operation"),
            ("--runtime-permission", "Sites.Read.All", "runtime_permission_allowed"),
            ("--site-grant-role", "write", "site_grant_role_allowed"),
        )
        for option, value, gate in cases:
            with self.subTest(option=option):
                exit_code, output = self._run(option, value)
                payload = json.loads(output)
                self.assertEqual(exit_code, 2)
                self.assertEqual(payload["status"], "BLOCKED")
                self.assertFalse(payload["gate_results"][gate])

    def test_contract_role_matrix_accepts_matching_operation_role(self) -> None:
        exit_code, output = self._run(
            "--operation",
            "backfill_validation",
            "--role",
            "BackfillOperator",
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output)["status"], "PASSED")

    def test_help_has_planner_inputs_but_no_resource_or_transport_inputs(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            nac_cli.main(["m365", "teams-sharepoint", "business-case-type-read-plan", "--help"])
        help_text = output.getvalue().lower()

        self.assertEqual(raised.exception.code, 0)
        for expected in (
            "business-case-type-read-plan",
            "--operation",
            "--role",
            "--runtime-permission",
            "--site-grant-role",
        ):
            self.assertIn(expected, help_text)
        for forbidden in (
            "--site-id",
            "--list-id",
            "--token",
            "--client-secret",
            "--url",
            "--runtime-certificate-path",
            "--runtime-private-key-path",
            "--schema",
        ):
            self.assertNotIn(forbidden, help_text)


    def test_command_sequence_is_ordered_and_foreign_commands_reject_options(self) -> None:
        for argv in (
            ["m365", "business-case-type-read-plan", "teams-sharepoint"],
            ["m365", "teams-sharepoint", "plan", "--operation", "case_create_validation"],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                nac_cli.main(argv)
            self.assertEqual(raised.exception.code, 2)

    def test_contract_drift_is_blocked(self) -> None:
        contract = json.loads((REPO_ROOT / read_plan.CONTRACT_PATH).read_text(encoding="utf-8"))
        mutations = []
        extra_operation = copy.deepcopy(contract)
        extra_operation["authorization"]["operation_role_bindings"]["extra"] = ["runtime_service"]
        mutations.append(extra_operation)
        extra_role = copy.deepcopy(contract)
        extra_role["authorization"]["operation_role_bindings"]["case_create_validation"].append("extra")
        mutations.append(extra_role)
        for path, value in (
            (("offline_cli", "command"), "nac wrong"),
            (("graph_request", "base_url"), "https://graph.microsoft.com/beta"),
            (("graph_request", "filter_fields_exact"), ["BusinessCaseTypeId"]),
            (("binding", "broader_site_grant_roles_allowed"), True),
            (("paging", "next_link_same_catalog_version_filter_required"), False),
            (("offline_cli", "http_allowed"), True),
        ):
            mutation = copy.deepcopy(contract)
            mutation[path[0]][path[1]] = value
            mutations.append(mutation)
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                temp_root = Path(directory)
                contract_path = temp_root / read_plan.CONTRACT_PATH
                contract_path.parent.mkdir(parents=True)
                contract_path.write_text(json.dumps(mutation), encoding="utf-8")
                plan = read_plan.build_business_case_type_read_plan(temp_root)
            self.assertEqual(plan["status"], "BLOCKED")
            self.assertFalse(plan["gate_results"]["contract_valid"])


if __name__ == "__main__":
    unittest.main()
