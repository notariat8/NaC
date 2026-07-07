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

from nac_m365_graph.matter_access_delegation import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    build_matter_access_plan,
    load_matter_access_delegation_contract,
    summarize_matter_access_plan,
    validate_matter_access_delegation_contract,
)
from nac_m365_graph.matter_access_delegation_smoke import (  # noqa: E402
    run_matter_access_delegation_smoke,
    write_matter_access_delegation_smoke_artifact,
)
from nac_m365_graph.matter_access_apply_readiness import (  # noqa: E402
    build_matter_access_apply_readiness,
    write_matter_access_apply_readiness_artifact,
)
from nac_m365_graph.mcp_runtime import (  # noqa: E402
    DEFAULT_MCP_CONTRACT,
    McpRuntimeError,
    RuntimeContext,
    load_mcp_contract,
    plan_tool_request,
)
from nac_m365_graph.schema import load_schema  # noqa: E402


class M365MatterAccessDelegationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_matter_access_delegation_contract(DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT)
        self.schema = load_schema()

    def test_contract_validates_against_existing_sharepoint_schema(self) -> None:
        self.assertEqual(validate_matter_access_delegation_contract(self.contract, self.schema), [])
        self.assertEqual(self.contract["status"], "offline_contract_no_live_apply")
        self.assertTrue(self.contract["graph"]["rest_only"])
        self.assertFalse(self.contract["graph"]["legacy_sharepoint_api_allowed"])
        self.assertFalse(self.contract["scope"]["executes_graph_requests_now"])
        self.assertFalse(self.contract["scope"]["team_membership_mutation_allowed_now"])
        self.assertFalse(self.contract["scope"]["sharepoint_file_content_read_allowed_now"])
        self.assertFalse(self.contract["scope"]["stores_tokens_or_secrets"])

        lists = {item["display_name"]: set(item["required_columns"]) for item in self.contract["sharepoint_lists"]}
        self.assertIn("Reason", lists["Vertretungsfreigaben"])
        self.assertIn("ValidFrom", lists["Vertretungsfreigaben"])
        self.assertIn("ValidUntil", lists["Vertretungsfreigaben"])
        self.assertIn("ApprovedBy", lists["Vertretungsfreigaben"])
        self.assertIn("AuditCorrelationId", lists["Vertretungsfreigaben"])

    def test_matter_access_plan_is_offline_and_workspace_scoped(self) -> None:
        operations = build_matter_access_plan(self.contract, self.schema)
        summary = summarize_matter_access_plan(operations, self.contract)

        self.assertEqual(summary["operation_count"], len(self.schema["workspaces"]) * 6)
        self.assertEqual(summary["mcp_tool_contract_count"], 4)
        self.assertEqual(summary["list_count"], 3)
        self.assertFalse(summary["executes_graph_requests_now"])
        self.assertFalse(summary["tenant_mutation_allowed_now"])
        self.assertFalse(summary["team_membership_mutation_allowed_now"])
        self.assertFalse(summary["reads_sharepoint_file_content"])
        self.assertFalse(summary["stores_tokens_or_secrets"])
        self.assertEqual(
            set(summary["by_action"]),
            {
                "append_access_audit_event",
                "read_active_deputy_grants",
                "read_delegation_audit_events",
                "read_primary_matter_assignment",
                "revoke_deputy_grant",
                "write_deputy_grant_request",
            },
        )
        self.assertTrue(all(operation.graph_path.startswith("/sites/{site-id}/") for operation in operations))
        self.assertTrue(all(not operation.executes_graph_requests_now for operation in operations))
        self.assertTrue(all(not operation.reads_files for operation in operations))

    def test_matter_access_smoke_writes_redacted_offline_evidence(self) -> None:
        with self.subTest("payload"):
            payload = run_matter_access_delegation_smoke(
                self.contract,
                self.schema,
                workspace_id="notary_team_01",
                correlation_id="delegation-corr",
                timestamp="2026-07-07T00:00:00Z",
            )

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["schema_version"], "nac.m365-matter-access-delegation-smoke/v0.1")
        self.assertEqual(payload["summary"]["workspace_id"], "notary_team_01")
        self.assertEqual(payload["summary"]["correlation_id"], "delegation-corr")
        self.assertEqual(payload["summary"]["workspace_operation_count"], 6)
        self.assertEqual(payload["summary"]["owner_gated_workspace_operations"], 3)
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["executes_graph_writes"])
        self.assertFalse(payload["summary"]["tenant_mutation_allowed"])
        self.assertFalse(payload["summary"]["team_membership_mutation_allowed"])
        self.assertFalse(payload["privacy"]["storesTokensOrSecrets"])
        self.assertFalse(payload["privacy"]["storesMatterPayloads"])
        self.assertFalse(payload["privacy"]["readsSharePointFileContent"])
        serialized = json.dumps(payload)
        self.assertNotIn("/sites/{site-id}/", serialized)
        self.assertNotIn("BEGIN PRIVATE KEY", serialized)

        output = REPO_ROOT / "out" / "test" / "matter-access-delegation-smoke.redacted.json"
        try:
            write_matter_access_delegation_smoke_artifact(payload, output)
            artifact = json.loads(output.read_text(encoding="utf-8"))
        finally:
            if output.exists():
                output.unlink()
        self.assertEqual(artifact["status"], "PASSED")

    def test_matter_access_apply_readiness_writes_redacted_offline_evidence(self) -> None:
        payload = build_matter_access_apply_readiness(
            self.contract,
            self.schema,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            workspace_id="notary_team_01",
            correlation_id="apply-readiness-corr",
            timestamp="2026-07-07T00:00:00Z",
        )

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["schema_version"], "nac.m365-matter-access-apply-readiness/v0.1")
        self.assertEqual(payload["summary"]["workspace_id"], "notary_team_01")
        self.assertEqual(payload["summary"]["correlation_id"], "apply-readiness-corr")
        self.assertEqual(payload["summary"]["future_apply_mode"], "owner_gated_graph_rest_item_writes")
        self.assertEqual(payload["summary"]["workspace_operation_count"], 6)
        self.assertEqual(payload["summary"]["planned_apply_operation_count"], 2)
        self.assertTrue(payload["summary"]["grant_request_ready"])
        self.assertTrue(payload["summary"]["audit_append_ready"])
        self.assertTrue(payload["summary"]["required_write_approval"])
        self.assertTrue(payload["summary"]["owner_gate_required"])
        self.assertTrue(payload["summary"]["reason_required"])
        self.assertTrue(payload["summary"]["valid_until_after_valid_from_required"])
        self.assertFalse(payload["summary"]["automation_may_approve_grant"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["executes_graph_writes"])
        self.assertFalse(payload["summary"]["tenant_mutation_allowed"])
        self.assertFalse(payload["summary"]["team_membership_mutation_allowed"])
        self.assertFalse(payload["summary"]["sharepoint_item_permission_mutation_allowed"])
        self.assertEqual(payload["readiness_boundary"]["planned_mcp_tools"], ["grant_request", "audit_append"])
        self.assertFalse(payload["privacy"]["storesTokensOrSecrets"])
        self.assertFalse(payload["privacy"]["storesMatterPayloads"])
        self.assertFalse(payload["privacy"]["readsSharePointFileContent"])
        serialized = json.dumps(payload)
        self.assertNotIn("/sites/{site-id}/", serialized)
        self.assertNotIn("BEGIN PRIVATE KEY", serialized)

        output = REPO_ROOT / "out" / "test" / "matter-access-apply-readiness.redacted.json"
        try:
            write_matter_access_apply_readiness_artifact(payload, output)
            artifact = json.loads(output.read_text(encoding="utf-8"))
        finally:
            if output.exists():
                output.unlink()
        self.assertEqual(artifact["status"], "PASSED")

    def test_central_cli_exposes_matter_access_plan_without_credentials(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "matter-access-plan",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["guardrails"]["executes_graph_requests_now"])
        self.assertFalse(payload["guardrails"]["tenant_mutation_allowed_now"])
        self.assertFalse(payload["guardrails"]["team_membership_mutation_allowed_now"])
        self.assertFalse(payload["guardrails"]["reads_sharepoint_file_content"])
        self.assertTrue(payload["guardrails"]["owner_gate_required_before_future_apply"])
        self.assertEqual(payload["summary"]["operation_count"], len(self.schema["workspaces"]) * 6)

    def test_central_cli_exposes_matter_access_smoke_without_credentials(self) -> None:
        output = REPO_ROOT / "out" / "test" / "matter-access-delegation-smoke-cli.redacted.json"
        if output.exists():
            output.unlink()
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "matter-access-smoke",
                "--mcp-smoke-workspace-id",
                "notary_team_01",
                "--mcp-smoke-correlation-id",
                "delegation-corr",
                "--matter-access-smoke-output",
                str(output),
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        try:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASSED")
            self.assertEqual(payload["summary"]["artifact_path"], str(output))
            self.assertFalse(payload["summary"]["executes_graph_requests"])
            self.assertTrue(output.exists())
        finally:
            if output.exists():
                output.unlink()

    def test_central_cli_exposes_matter_access_apply_readiness_without_credentials(self) -> None:
        output = REPO_ROOT / "out" / "test" / "matter-access-apply-readiness-cli.redacted.json"
        if output.exists():
            output.unlink()
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "matter-access-apply-readiness",
                "--mcp-smoke-workspace-id",
                "notary_team_01",
                "--mcp-smoke-correlation-id",
                "apply-readiness-corr",
                "--matter-access-apply-readiness-output",
                str(output),
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
        try:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASSED")
            self.assertEqual(payload["summary"]["artifact_path"], str(output))
            self.assertTrue(payload["summary"]["grant_request_ready"])
            self.assertTrue(payload["summary"]["audit_append_ready"])
            self.assertFalse(payload["summary"]["executes_graph_requests"])
            self.assertTrue(output.exists())
        finally:
            if output.exists():
                output.unlink()

    def test_grant_request_reuses_existing_mcp_tool_and_validates_semantics(self) -> None:
        plan = plan_tool_request(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _open_context(write_approved=True),
            "grant_request",
            _grant_request_arguments(),
        )

        self.assertEqual(plan.method, "POST")
        self.assertEqual(plan.list_name, "Vertretungsfreigaben")
        self.assertTrue(plan.owner_gate_required)
        self.assertTrue(plan.writes_items)
        self.assertFalse(plan.reads_files)
        fields = plan.payload["fields"] if plan.payload else {}
        self.assertEqual(fields["Reason"], "Urlaubsvertretung")
        self.assertEqual(fields["ValidFrom"], "2026-07-06T09:00:00Z")
        self.assertEqual(fields["ValidUntil"], "2026-07-13T09:00:00Z")
        self.assertEqual(fields["ApprovedBy"], "notary-1")
        self.assertEqual(fields["AuditCorrelationId"], "corr-1")

    def test_grant_request_rejects_invalid_duration_role_status_and_reason(self) -> None:
        invalid_cases = [
            ("reason must be non-empty", {"reason": "   "}),
            ("valid_until must be after valid_from", {"valid_until": "2026-07-06T09:00:00Z"}),
            ("granted_role is not allowed", {"granted_role": "AlleAkten"}),
            ("status is not allowed", {"status": "Dauerhaft"}),
        ]

        for expected_error, override in invalid_cases:
            with self.subTest(expected_error=expected_error):
                args = _grant_request_arguments()
                args.update(override)
                with self.assertRaisesRegex(McpRuntimeError, expected_error):
                    plan_tool_request(
                        load_mcp_contract(DEFAULT_MCP_CONTRACT),
                        _provisioned_state(),
                        _open_context(write_approved=True),
                        "grant_request",
                        args,
                    )

    def test_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_m365_matter_access_delegation.py"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS: PASSED", result.stdout)


def _open_context(*, write_approved: bool = False) -> RuntimeContext:
    return RuntimeContext(
        actor_id="actor-1",
        actor_role="notary",
        workspace_id="notary_team_01",
        purpose="casework_preparation",
        correlation_id="corr-1",
        case_id="case-1",
        role_case_gate="open",
        write_approved=write_approved,
    )


def _grant_request_arguments() -> dict[str, object]:
    return {
        "grant_id": "grant-1",
        "case_id": "case-1",
        "from_user": "notary-1",
        "to_user": "clerk-2",
        "granted_role": "SachbearbeitungVertretung",
        "reason": "Urlaubsvertretung",
        "valid_from": "2026-07-06T09:00:00Z",
        "valid_until": "2026-07-13T09:00:00Z",
        "approved_by": "notary-1",
        "status": "Aktiv",
    }


def _provisioned_state() -> dict[str, object]:
    return {
        "workspaces": [
            {
                "id": "notary_team_01",
                "site_id": "example.sharepoint.com,site-01,web-01",
                "lists": {
                    "Akten": {"id": "list-akten"},
                    "Vertretungsfreigaben": {"id": "list-grants"},
                    "AuditJournalLite": {"id": "list-audit"},
                    "DokumentRegister": {"id": "list-documents"},
                    "AufgabenFristen": {"id": "list-tasks"},
                    "BPMN Models": {"id": "list-bpmn-models"},
                    "Prozessregister": {"id": "list-process-register"},
                },
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
