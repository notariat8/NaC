from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.privileged_change import (  # noqa: E402
    DEFAULT_PRIVILEGED_CHANGE_CONFIG,
    DEFAULT_PROVISIONED_STATE,
    build_privileged_change_plan,
    load_privileged_change_config,
    load_provisioned_state,
    summarize_privileged_change_plan,
    validate_privileged_change_config,
)
from nac_m365_graph.provisioner import build_plan, summarize_plan  # noqa: E402
from nac_m365_graph.schema import (  # noqa: E402
    DEFAULT_SCHEMA,
    column_create_payload,
    load_schema,
    validate_schema,
)


CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-graph-data-plane.contract.json"
APPLIED_STATE = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-mvp.privileged-change-path.applied.f8.json"


class TeamsSharePointGraphDataPlaneTests(unittest.TestCase):
    def test_contract_sets_graph_rest_only_decision(self) -> None:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(payload["contract_id"], "m365.teams_sharepoint_graph_data_plane")
        self.assertTrue(payload["target_decision"]["graph_rest_only"])
        self.assertTrue(payload["target_decision"]["mcp_allowed_only_when_backed_by_graph_rest"])
        self.assertFalse(payload["graph_policy"]["sdk_usage_allowed"])
        self.assertFalse(payload["graph_policy"]["legacy_sharepoint_api_allowed"])
        self.assertEqual(payload["target_decision"]["workspace_model"], "team_per_notary_team")
        self.assertIn("Sites.Selected", payload["permission_model"]["runtime_target_permissions"])

    def test_contract_captures_application_owned_privileged_change_path(self) -> None:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        permission_model = payload["permission_model"]

        self.assertTrue(permission_model["standard_users_must_not_hold_m365_admin_permissions"])
        self.assertTrue(permission_model["privileged_m365_changes_must_run_through_app_or_api"])
        self.assertTrue(permission_model["application_governance_group_required"])
        self.assertEqual(permission_model["application_governance_group_target"], "nac_platform_admins")
        self.assertFalse(permission_model["direct_application_owner_group_supported_by_graph"])
        self.assertTrue(permission_model["direct_application_owner_must_be_user_or_service_principal"])
        self.assertTrue(permission_model["technical_application_owner_user_allowed"])
        self.assertEqual(permission_model["technical_application_owner_user_target"], "funktion8@funktion8.de")
        self.assertTrue(permission_model["human_team_owner_still_required"])
        self.assertTrue(permission_model["technical_bootstrap_owner_user_allowed"])
        self.assertEqual(permission_model["technical_bootstrap_owner_user_target"], "funktion8@funktion8.de")
        self.assertTrue(permission_model["technical_bootstrap_owner_user_must_not_be_sole_owner"])
        self.assertTrue(permission_model["licensed_human_team_owner_required"])
        self.assertTrue(permission_model["technical_owner_must_not_hold_m365_admin_roles"])
        self.assertTrue(permission_model["technical_owner_use_requires_license_terms_review"])

        roadmap_ids = {item["id"] for item in payload["next_iteration_roadmap"]}
        self.assertIn("m365-application-owned-privileged-change-path", roadmap_ids)

    def test_schema_validates_and_contains_required_lists(self) -> None:
        schema = load_schema(DEFAULT_SCHEMA)

        self.assertEqual(validate_schema(schema), [])
        list_names = {item["display_name"] for item in schema["sharepoint"]["lists"]}
        self.assertGreaterEqual(
            list_names,
            {
                "Akten",
                "Beteiligte",
                "AufgabenFristen",
                "Vertretungsfreigaben",
                "AuditJournalLite",
                "DokumentRegister",
            },
        )

    def test_schema_rejects_reserved_sharepoint_column_names(self) -> None:
        schema = load_schema(DEFAULT_SCHEMA)
        schema["sharepoint"]["lists"][0]["columns"].append(
            {
                "name": "WorkflowVersion",
                "type": "text",
            }
        )

        self.assertIn(
            "list Akten column WorkflowVersion conflicts with a SharePoint system field",
            validate_schema(schema),
        )

    def test_plan_runs_without_credentials(self) -> None:
        schema = load_schema(DEFAULT_SCHEMA)
        plan = build_plan(schema)
        summary = summarize_plan(plan)

        self.assertEqual(summary["by_action"]["ensure_team"], 2)
        self.assertEqual(summary["by_action"]["resolve_group_site"], 2)
        self.assertEqual(summary["by_action"]["ensure_document_library"], 4)
        self.assertGreater(summary["by_action"]["ensure_column"], 80)

    def test_privileged_change_plan_runs_without_credentials(self) -> None:
        config = load_privileged_change_config(DEFAULT_PRIVILEGED_CHANGE_CONFIG)
        state = load_provisioned_state(DEFAULT_PROVISIONED_STATE)

        self.assertEqual(validate_privileged_change_config(config), [])
        plan = build_privileged_change_plan(config, state)
        summary = summarize_privileged_change_plan(plan)

        self.assertEqual(summary["by_action"]["resolve_technical_owner_user"], 1)
        self.assertEqual(summary["by_action"]["ensure_governance_group"], 1)
        self.assertEqual(summary["by_action"]["ensure_application"], 2)
        self.assertEqual(summary["by_action"]["assign_direct_application_owner"], 2)
        self.assertEqual(summary["by_action"]["verify_human_team_owner"], 2)
        self.assertEqual(summary["by_action"]["grant_runtime_sites_selected_site_permission"], 2)

    def test_applied_privileged_state_captures_runtime_site_grants(self) -> None:
        state = json.loads(APPLIED_STATE.read_text(encoding="utf-8"))
        runtime_app = state["applications"]["m365_runtime_app"]

        self.assertEqual(state["state_version"], "nac.m365-privileged-change-path.applied/v0.1")
        self.assertEqual(runtime_app["application_permissions"], ["Sites.Selected"])
        self.assertTrue(runtime_app["runtime_allowed"])
        self.assertEqual(len(state["runtime_site_permissions"]), 2)
        for permission in state["runtime_site_permissions"]:
            self.assertEqual(permission["application_client_id"], runtime_app["client_id"])
            self.assertEqual(permission["role"], "write")
        for owner_check in state["team_owner_checks"]:
            self.assertGreaterEqual(owner_check["licensed_human_owner_count"], 1)

    def test_column_mapping_uses_graph_column_payloads(self) -> None:
        payload = column_create_payload(
            {
                "name": "Status",
                "type": "choice",
                "required": True,
                "choices": ["Offen", "Erledigt"],
            }
        )

        self.assertEqual(payload["displayName"], "Status")
        self.assertTrue(payload["required"])
        self.assertEqual(payload["choice"]["choices"], ["Offen", "Erledigt"])

    def test_unique_columns_are_indexed_for_graph(self) -> None:
        payload = column_create_payload(
            {
                "name": "NacCaseId",
                "type": "text",
                "enforce_unique_values": True,
            }
        )

        self.assertTrue(payload["enforceUniqueValues"])
        self.assertTrue(payload["indexed"])

    def test_validator_accepts_repository_state(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_teams_sharepoint_graph_data_plane.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)

    def test_cli_plan_runs_without_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "plan", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertGreater(payload["summary"]["operation_count"], 100)

    def test_cli_privileged_plan_runs_without_credentials(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/provision_teams_sharepoint_graph.py", "privileged-plan", "--json"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["by_action"]["ensure_application"], 2)
        self.assertEqual(
            payload["summary"]["by_action"]["grant_runtime_sites_selected_site_permission"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
