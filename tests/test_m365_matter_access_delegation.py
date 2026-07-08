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
from nac_m365_graph.matter_access_apply_request import (  # noqa: E402
    build_matter_access_apply_request_plan,
    write_matter_access_apply_request_plan_artifact,
)
from nac_m365_graph.matter_access_apply_policy_smoke import (  # noqa: E402
    run_matter_access_apply_policy_smoke,
    write_matter_access_apply_policy_smoke_artifact,
)
from nac_m365_graph.matter_access_apply_policy import MatterAccessApplyPolicyError  # noqa: E402
from nac_m365_graph.matter_access_apply_smoke import (  # noqa: E402
    run_matter_access_apply_smoke,
    write_matter_access_apply_smoke_artifact,
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
        self.assertTrue(self.contract["apply_policy"]["fail_closed_before_graph_write"])
        self.assertTrue(self.contract["apply_policy"]["cleanup_required_before_write"])
        self.assertTrue(self.contract["apply_policy"]["audit_reason_must_match_grant_reason"])
        self.assertEqual(
            self.contract["apply_policy"]["negative_case_ids"],
            [
                "missing_reason",
                "expired_delegation",
                "workspace_scope_violation",
                "missing_cleanup",
                "audit_readback_missing",
            ],
        )

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

    def test_matter_access_apply_request_plan_writes_redacted_offline_evidence(self) -> None:
        readiness = build_matter_access_apply_readiness(
            self.contract,
            self.schema,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            workspace_id="notary_team_01",
            correlation_id="apply-request-corr",
            timestamp="2026-07-07T00:00:00Z",
        )
        payload = build_matter_access_apply_request_plan(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            readiness,
            workspace_id="notary_team_01",
            correlation_id="apply-request-corr",
            grant_id="grant-1",
            case_id="case-1",
            from_user="notary-1",
            to_user="clerk-2",
            reason="Urlaubsvertretung",
            approved_by="notary-1",
            timestamp="2026-07-07T00:00:00Z",
        )

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["schema_version"], "nac.m365-matter-access-apply-request-plan/v0.1")
        self.assertEqual(payload["summary"]["workspace_id"], "notary_team_01")
        self.assertEqual(payload["summary"]["correlation_id"], "apply-request-corr")
        self.assertEqual(payload["summary"]["future_apply_mode"], "owner_gated_graph_rest_item_writes")
        self.assertEqual(payload["summary"]["planned_write_count"], 2)
        self.assertEqual(payload["summary"]["planned_tools"], ["grant_request", "audit_append"])
        self.assertEqual(payload["summary"]["planned_lists"], ["Vertretungsfreigaben", "AuditJournalLite"])
        self.assertTrue(payload["summary"]["apply_policy_enforced"])
        self.assertEqual(
            payload["summary"]["policy_negative_case_ids"],
            [
                "missing_reason",
                "expired_delegation",
                "workspace_scope_violation",
                "missing_cleanup",
                "audit_readback_missing",
            ],
        )
        self.assertTrue(payload["summary"]["audit_reason_matches_grant_reason"])
        self.assertTrue(payload["summary"]["required_write_approval"])
        self.assertTrue(payload["summary"]["owner_gate_required"])
        self.assertTrue(payload["summary"]["role_case_purpose_gate_required"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["executes_graph_writes"])
        self.assertFalse(payload["summary"]["tenant_mutation_allowed"])
        self.assertFalse(payload["summary"]["team_membership_mutation_allowed"])
        self.assertFalse(payload["summary"]["sharepoint_item_permission_mutation_allowed"])
        self.assertFalse(payload["summary"]["raw_graph_path_stored"])
        self.assertFalse(payload["summary"]["raw_graph_response_stored"])
        self.assertFalse(payload["summary"]["stores_tokens_or_secrets"])
        self.assertFalse(payload["summary"]["stores_matter_payloads"])
        self.assertTrue(payload["privacy"]["metadataOnly"])
        self.assertFalse(payload["privacy"]["storesSourceFullText"])
        self.assertFalse(payload["privacy"]["storesRawXsd"])
        self.assertFalse(payload["privacy"]["storesTokensOrSecrets"])
        self.assertFalse(payload["privacy"]["storesMatterPayloads"])
        self.assertFalse(payload["privacy"]["storesRawGraphPath"])
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertFalse(payload["privacy"]["readsSharePointFileContent"])
        self.assertFalse(payload["privacy"]["executesGraphRequests"])
        self.assertFalse(payload["privacy"]["executesGraphWrites"])
        self.assertTrue(all(plan["writes_items"] for plan in payload["request_plans"]))
        self.assertTrue(all(plan["owner_gate_required"] for plan in payload["request_plans"]))
        self.assertTrue(all(plan["role_case_gate_required"] for plan in payload["request_plans"]))
        self.assertTrue(all(plan["stores_raw_graph_path"] is False for plan in payload["request_plans"]))
        self.assertTrue(all(plan["stores_raw_graph_response"] is False for plan in payload["request_plans"]))
        serialized = json.dumps(payload)
        for raw_value in (
            "grant-1",
            "case-1",
            "notary-1",
            "clerk-2",
            "Urlaubsvertretung",
            "example.sharepoint.com",
            "list-grants",
            "list-audit",
            "BEGIN PRIVATE KEY",
        ):
            self.assertNotIn(raw_value, serialized)

        output = REPO_ROOT / "out" / "test" / "matter-access-apply-request-plan.redacted.json"
        try:
            write_matter_access_apply_request_plan_artifact(payload, output)
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

    def test_central_cli_exposes_matter_access_apply_request_plan_without_credentials(self) -> None:
        output = REPO_ROOT / "out" / "test" / "matter-access-apply-request-plan-cli.redacted.json"
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
                "matter-access-apply-request-plan",
                "--mcp-smoke-workspace-id",
                "notary_team_01",
                "--mcp-smoke-correlation-id",
                "apply-request-corr",
                "--mcp-smoke-case-id",
                "case-1",
                "--matter-access-grant-id",
                "grant-1",
                "--matter-access-from-user",
                "notary-1",
                "--matter-access-to-user",
                "clerk-2",
                "--matter-access-reason",
                "Urlaubsvertretung",
                "--matter-access-approved-by",
                "notary-1",
                "--matter-access-apply-request-output",
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
            self.assertEqual(payload["summary"]["planned_tools"], ["grant_request", "audit_append"])
            self.assertFalse(payload["summary"]["executes_graph_requests"])
            self.assertTrue(output.exists())
            artifact_text = output.read_text(encoding="utf-8")
            self.assertNotIn("case-1", artifact_text)
            self.assertNotIn("grant-1", artifact_text)
            self.assertNotIn("notary-1", artifact_text)
            self.assertNotIn("clerk-2", artifact_text)
        finally:
            if output.exists():
                output.unlink()

    def test_matter_access_apply_smoke_writes_reads_cleans_and_redacts(self) -> None:
        grant_id = "NAC-SMOKE-GRANT-20260708T000000Z"
        case_id = "NAC-SMOKE-MATTER-20260708T000000Z"
        event_id = "NAC-SMOKE-AUDIT-20260708T000000Z"
        graph_client = _FakeMatterAccessApplySmokeClient(
            post_responses=[{"id": "raw-grant-item"}, {"id": "raw-audit-item"}],
            get_responses=[
                {"value": [{"id": "raw-grant-item", "fields": {"GrantId": grant_id}}]},
                {"value": [{"id": "raw-audit-item", "fields": {"EventId": event_id}}]},
                {"value": []},
                {"value": []},
            ],
            delete_response={},
        )

        payload = run_matter_access_apply_smoke(
            graph_client,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            workspace_id="notary_team_01",
            correlation_id="apply-smoke-corr",
            grant_id=grant_id,
            case_id=case_id,
            from_user="notary-1",
            to_user="clerk-2",
            reason="Urlaubsvertretung",
            approved_by="notary-1",
            timestamp="2026-07-08T00:00:00Z",
        )

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["schema_version"], "nac.m365-matter-access-apply-smoke/v0.1")
        self.assertEqual(payload["summary"]["write_tools"], ["grant_request", "audit_append"])
        self.assertEqual(payload["summary"]["write_lists"], ["Vertretungsfreigaben", "AuditJournalLite"])
        self.assertTrue(payload["summary"]["apply_policy_enforced"])
        self.assertTrue(payload["summary"]["fail_closed_before_graph_write"])
        self.assertTrue(payload["summary"]["cleanup_required"])
        self.assertTrue(payload["summary"]["audit_append_required"])
        self.assertTrue(payload["summary"]["audit_readback_required"])
        self.assertTrue(payload["summary"]["cleanup_readback_required"])
        self.assertTrue(payload["summary"]["executed_graph_requests"])
        self.assertTrue(payload["summary"]["executed_graph_writes"])
        self.assertTrue(payload["summary"]["sharepoint_item_writes_executed"])
        self.assertFalse(payload["summary"]["tenant_mutation_allowed"])
        self.assertFalse(payload["summary"]["team_membership_mutation_allowed"])
        self.assertFalse(payload["summary"]["sharepoint_item_permission_mutation_allowed"])
        self.assertEqual(payload["summary"]["grant_read_value_count"], 1)
        self.assertEqual(payload["summary"]["audit_read_value_count"], 1)
        self.assertEqual(payload["summary"]["grant_cleanup_read_after_value_count"], 0)
        self.assertEqual(payload["summary"]["audit_cleanup_read_after_value_count"], 0)
        self.assertFalse(payload["privacy"]["storesTokensOrSecrets"])
        self.assertFalse(payload["privacy"]["storesRawWritePayload"])
        self.assertFalse(payload["privacy"]["storesRawGraphPath"])
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertEqual(len(graph_client.posts), 2)
        self.assertEqual(len(graph_client.gets), 4)
        self.assertEqual(len(graph_client.deletes), 2)

        serialized = json.dumps(payload, ensure_ascii=False)
        for raw_value in (
            grant_id,
            case_id,
            event_id,
            "notary-1",
            "clerk-2",
            "Urlaubsvertretung",
            "raw-grant-item",
            "raw-audit-item",
            "example.sharepoint.com",
            "list-grants",
            "list-audit",
        ):
            self.assertNotIn(raw_value, serialized)

        output = REPO_ROOT / "out" / "test" / "matter-access-apply-smoke.redacted.json"
        try:
            write_matter_access_apply_smoke_artifact(payload, output)
            artifact = json.loads(output.read_text(encoding="utf-8"))
        finally:
            if output.exists():
                output.unlink()
        self.assertEqual(artifact["status"], "PASSED")

    def test_matter_access_apply_smoke_rejects_non_synthetic_ids_before_graph_calls(self) -> None:
        graph_client = _FakeMatterAccessApplySmokeClient(post_responses=[], get_responses=[], delete_response={})

        with self.assertRaisesRegex(ValueError, "NAC-SMOKE-GRANT-"):
            run_matter_access_apply_smoke(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                correlation_id="apply-smoke-corr",
                grant_id="grant-1",
                case_id="NAC-SMOKE-MATTER-20260708T000000Z",
                timestamp="2026-07-08T00:00:00Z",
            )

        self.assertEqual(graph_client.posts, [])
        self.assertEqual(graph_client.gets, [])
        self.assertEqual(graph_client.deletes, [])

    def test_matter_access_apply_smoke_rejects_expired_delegation_before_graph_calls(self) -> None:
        graph_client = _FakeMatterAccessApplySmokeClient(post_responses=[], get_responses=[], delete_response={})

        with self.assertRaisesRegex(ValueError, "valid_until must be after apply timestamp"):
            run_matter_access_apply_smoke(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                correlation_id="apply-smoke-corr",
                grant_id="NAC-SMOKE-GRANT-20260708T000000Z",
                case_id="NAC-SMOKE-MATTER-20260708T000000Z",
                valid_from="2026-07-01T00:00:00Z",
                valid_until="2026-07-02T00:00:00Z",
                timestamp="2026-07-08T00:00:00Z",
            )

        self.assertEqual(graph_client.posts, [])
        self.assertEqual(graph_client.gets, [])
        self.assertEqual(graph_client.deletes, [])

    def test_matter_access_apply_smoke_blocks_missing_cleanup_before_graph_calls(self) -> None:
        grant_id = "NAC-SMOKE-GRANT-20260708T000000Z"
        graph_client = _FakeMatterAccessApplySmokeClient(post_responses=[], get_responses=[], delete_response={})

        with self.assertRaisesRegex(MatterAccessApplyPolicyError, "cleanup_after must be true"):
            run_matter_access_apply_smoke(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                correlation_id="apply-smoke-corr",
                grant_id=grant_id,
                case_id="NAC-SMOKE-MATTER-20260708T000000Z",
                cleanup_after=False,
                timestamp="2026-07-08T00:00:00Z",
            )

        self.assertEqual(graph_client.posts, [])
        self.assertEqual(graph_client.gets, [])
        self.assertEqual(graph_client.deletes, [])

    def test_matter_access_apply_policy_smoke_detects_negative_cases_and_redacts(self) -> None:
        payload = run_matter_access_apply_policy_smoke(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            workspace_id="notary_team_01",
            correlation_id="policy-hardening-corr",
            timestamp="2026-07-08T00:00:00Z",
        )

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(
            payload["summary"]["expected_case_ids"],
            [
                "missing_reason",
                "expired_delegation",
                "workspace_scope_violation",
                "missing_cleanup",
                "audit_readback_missing",
            ],
        )
        self.assertEqual(payload["summary"]["negative_case_count"], 5)
        self.assertEqual(payload["summary"]["detected_policy_violation_count"], 5)
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["tenant_writes_executed"])
        self.assertTrue(payload["summary"]["uses_fake_graph_client"])
        self.assertTrue(all(case["status"] == "PASSED" for case in payload["cases"]))
        self.assertEqual(payload["cases"][0]["fake_graph_post_count"], 0)
        self.assertEqual(payload["cases"][1]["fake_graph_post_count"], 0)
        self.assertEqual(payload["cases"][2]["fake_graph_post_count"], 0)
        self.assertEqual(payload["cases"][3]["fake_graph_post_count"], 0)
        self.assertEqual(payload["cases"][3]["observed_error_type"], "MatterAccessApplyPolicyError")
        self.assertEqual(payload["cases"][4]["observed_error_type"], "MatterAccessApplyPolicyError")

        serialized = json.dumps(payload, ensure_ascii=False)
        for raw_value in (
            "NAC-SMOKE-GRANT-20260708T010000Z",
            "NAC-SMOKE-MATTER-20260708T050000Z",
            "raw-grant-item",
            "raw-audit-item",
            "wrong_workspace",
            "example.sharepoint.com",
        ):
            self.assertNotIn(raw_value, serialized)

        output = REPO_ROOT / "out" / "test" / "matter-access-apply-policy-smoke.redacted.json"
        try:
            write_matter_access_apply_policy_smoke_artifact(payload, output)
            artifact = json.loads(output.read_text(encoding="utf-8"))
        finally:
            if output.exists():
                output.unlink()
        self.assertEqual(artifact["status"], "PASSED")

    def test_central_cli_matter_access_apply_policy_smoke_writes_redacted_artifact(self) -> None:
        output = REPO_ROOT / "out" / "test" / "matter-access-apply-policy-smoke-cli.redacted.json"
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "matter-access-apply-policy-smoke",
                    "--mcp-smoke-workspace-id",
                    "notary_team_01",
                    "--mcp-smoke-correlation-id",
                    "policy-hardening-corr",
                    "--matter-access-apply-policy-smoke-output",
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

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASSED")
            self.assertEqual(payload["summary"]["artifact_path"], str(output))
            self.assertFalse(payload["summary"]["executes_graph_requests"])
            self.assertTrue(output.exists())
            artifact_text = output.read_text(encoding="utf-8")
            self.assertNotIn("raw-grant-item", artifact_text)
            self.assertNotIn("example.sharepoint.com", artifact_text)
        finally:
            if output.exists():
                output.unlink()

    def test_central_cli_matter_access_apply_smoke_requires_owner_approval(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "matter-access-apply-smoke",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("STATUS: BLOCKED", result.stdout)
        self.assertIn("--owner-approved", result.stdout)

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


class _FakeMatterAccessApplySmokeClient:
    def __init__(
        self,
        *,
        post_responses: list[dict[str, object]],
        get_responses: list[dict[str, object]],
        delete_response: dict[str, object],
    ) -> None:
        self.post_responses = list(post_responses)
        self.get_responses = list(get_responses)
        self.delete_response = delete_response
        self.posts: list[tuple[str, dict[str, object]]] = []
        self.gets: list[str] = []
        self.deletes: list[str] = []

    def post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        self.posts.append((path, payload))
        return self.post_responses.pop(0)

    def get(self, path: str) -> dict[str, object]:
        self.gets.append(path)
        return self.get_responses.pop(0)

    def delete(self, path: str) -> dict[str, object]:
        self.deletes.append(path)
        return self.delete_response


if __name__ == "__main__":
    unittest.main()
