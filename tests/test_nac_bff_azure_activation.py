from __future__ import annotations

import json
import os
import socket
import unittest
import urllib.request
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from nac_bff.azure_activation import (
    API_APP_URI,
    DELEGATED_SCOPE,
    FUNCTION_APP,
    MATTER_ID,
    SITE_ID,
    SUBSCRIPTION_ID,
    TENANT_ID,
    WORKSPACE_ID,
    build_azure_bff_activation_plan,
)
from nac_cli.cli import main as nac_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class AzureBffActivationPlanTests(unittest.TestCase):
    def test_current_repository_produces_hash_bound_ready_plan(self) -> None:
        first = build_azure_bff_activation_plan(REPO_ROOT)
        second = build_azure_bff_activation_plan(REPO_ROOT)

        self.assertEqual(first["status"], "READY")
        self.assertEqual(first["activation_hash"], second["activation_hash"])
        self.assertRegex(first["activation_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["bindings"]["subscription_id"], SUBSCRIPTION_ID)
        self.assertEqual(first["bindings"]["tenant_id"], TENANT_ID)
        self.assertEqual(first["bindings"]["workspace_id"], WORKSPACE_ID)
        self.assertEqual(first["bindings"]["matter_id"], MATTER_ID)
        self.assertEqual(first["bindings"]["site_id"], SITE_ID)
        self.assertEqual(first["bindings"]["function_app"], FUNCTION_APP)
        self.assertEqual(first["bindings"]["api_app_uri"], API_APP_URI)
        self.assertEqual(first["bindings"]["delegated_scope"], DELEGATED_SCOPE)
        self.assertEqual(len(first["steps"]), 12)
        self.assertTrue(first["gate_results"]["activation_contract_valid"])
        self.assertIn(
            "generated:nac-bff-function.zip",
            {binding["path"] for binding in first["artifact_bindings"]},
        )
        self.assertTrue(all(step["stop_on_error"] for step in first["steps"]))
        self.assertEqual(first["boundaries"]["live_actions_executed"], 0)
        self.assertFalse(first["boundaries"]["production_data_allowed"])
        self.assertFalse(first["boundaries"]["other_workspaces_allowed"])
        self.assertFalse(first["boundaries"]["credential_changes_allowed"])

    def test_plan_builder_does_not_access_environment_network_or_subprocess(self) -> None:
        secret = "must-not-appear"
        with (
            patch.dict(os.environ, {"AZURE_CLIENT_SECRET": secret}),
            patch.object(socket, "getaddrinfo", side_effect=AssertionError("DNS access")),
            patch.object(urllib.request, "urlopen", side_effect=AssertionError("HTTP access")),
            patch("subprocess.run", side_effect=AssertionError("subprocess access")),
        ):
            plan = build_azure_bff_activation_plan(REPO_ROOT)

        self.assertEqual(plan["status"], "READY")
        self.assertNotIn(secret, json.dumps(plan))

    def test_cli_emits_ready_json_plan(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            return_code = nac_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "bff-azure-activation-plan",
                    "--format",
                    "json",
                ]
            )

        payload = json.loads(output.getvalue())
        self.assertEqual(return_code, 0)
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["bindings"]["workspace_id"], WORKSPACE_ID)


if __name__ == "__main__":
    unittest.main()
