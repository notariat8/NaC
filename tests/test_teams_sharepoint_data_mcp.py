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

from nac_m365_graph.mcp_runtime import (  # noqa: E402
    DEFAULT_MCP_CONTRACT,
    McpGateError,
    RuntimeContext,
    build_tool_manifest,
    load_mcp_contract,
    plan_tool_request,
    validate_mcp_contract,
)


class TeamsSharePointDataMcpTests(unittest.TestCase):
    def test_contract_defines_graph_rest_only_mcp_boundary(self) -> None:
        contract = load_mcp_contract(DEFAULT_MCP_CONTRACT)

        self.assertEqual(validate_mcp_contract(contract), [])
        self.assertEqual(contract["server_id"], "teams-sharepoint-data-mcp")
        self.assertTrue(contract["graph"]["rest_only"])
        self.assertFalse(contract["runtime_boundary"]["executes_graph_requests"])
        self.assertFalse(contract["runtime_boundary"]["stores_tokens_or_secrets"])
        self.assertFalse(contract["runtime_boundary"]["reads_sharepoint_file_content"])

        tool_names = {tool["id"] for tool in contract["tools"]}
        self.assertEqual(
            tool_names,
            {
                "case_get",
                "case_create",
                "case_update_status",
                "task_create",
                "grant_request",
                "audit_append",
                "document_list",
            },
        )

    def test_manifest_is_safe_for_cli_and_aiq_binding(self) -> None:
        manifest = build_tool_manifest(load_mcp_contract(DEFAULT_MCP_CONTRACT))

        self.assertEqual(manifest["serverId"], "teams-sharepoint-data-mcp")
        self.assertFalse(manifest["executesGraphRequests"])
        self.assertEqual(len(manifest["tools"]), 7)
        for tool in manifest["tools"]:
            self.assertTrue(tool["requiresRoleCasePurposeGate"])
            self.assertFalse(tool["readsFiles"])

    def test_case_get_plans_graph_rest_request_without_payload(self) -> None:
        plan = plan_tool_request(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _open_context(case_id="case-1"),
            "case_get",
            {"case_id": "case-1"},
        )

        self.assertEqual(plan.method, "GET")
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", plan.path)
        self.assertIn("fields/NacCaseId%20eq%20%27case-1%27", plan.path)
        self.assertIsNone(plan.payload)
        self.assertTrue(plan.reads_items)
        self.assertFalse(plan.reads_files)
        self.assertFalse(plan.writes_items)

    def test_write_tool_requires_open_gate_and_write_approval(self) -> None:
        with self.assertRaisesRegex(McpGateError, "role/case/purpose gate is closed"):
            plan_tool_request(
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                _closed_context(case_id="case-1"),
                "case_create",
                _case_create_arguments(),
            )

        with self.assertRaisesRegex(McpGateError, "write tool requires explicit write approval"):
            plan_tool_request(
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                _open_context(case_id="case-1", write_approved=False),
                "case_create",
                _case_create_arguments(),
            )

    def test_case_create_payload_uses_declared_sharepoint_fields_only(self) -> None:
        plan = plan_tool_request(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _open_context(case_id="case-1", write_approved=True),
            "case_create",
            _case_create_arguments(),
        )

        self.assertEqual(plan.method, "POST")
        self.assertEqual(plan.list_name, "Akten")
        self.assertTrue(plan.owner_gate_required)
        self.assertEqual(
            plan.payload,
            {
                "fields": {
                    "NacCaseId": "case-1",
                    "Aktenzeichen": "AZ-1",
                    "Vorgangstyp": "immobilienkaufvertrag",
                    "Status": "Entwurf",
                    "NotarTeam": "NaC-Notar-01",
                    "Vertraulichkeitsstufe": "Normal",
                    "NacWorkflowVersion": "workflow-v1",
                    "KgVersion": "kg-v1",
                }
            },
        )

    def test_grant_request_payload_keeps_reason_duration_and_audit_correlation(self) -> None:
        plan = plan_tool_request(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _open_context(case_id="case-1", write_approved=True),
            "grant_request",
            {
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
            },
        )

        fields = plan.payload["fields"] if plan.payload else {}
        self.assertEqual(fields["Reason"], "Urlaubsvertretung")
        self.assertEqual(fields["ValidUntil"], "2026-07-13T09:00:00Z")
        self.assertEqual(fields["AuditCorrelationId"], "corr-1")

    def test_cli_exposes_mcp_manifest_without_credentials(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-manifest",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["tool_count"], 7)
        self.assertFalse(payload["result"]["executesGraphRequests"])


def _open_context(case_id: str, write_approved: bool = False) -> RuntimeContext:
    return RuntimeContext(
        actor_id="user-1",
        actor_role="notary_clerk",
        workspace_id="notary_team_01",
        purpose="matter_workflow",
        correlation_id="corr-1",
        case_id=case_id,
        role_case_gate="open",
        write_approved=write_approved,
    )


def _closed_context(case_id: str) -> RuntimeContext:
    return RuntimeContext(
        actor_id="user-1",
        actor_role="notary_clerk",
        workspace_id="notary_team_01",
        purpose="matter_workflow",
        correlation_id="corr-1",
        case_id=case_id,
        role_case_gate="closed",
    )


def _case_create_arguments() -> dict:
    return {
        "case_id": "case-1",
        "aktenzeichen": "AZ-1",
        "vorgangstyp": "immobilienkaufvertrag",
        "status": "Entwurf",
        "notar_team": "NaC-Notar-01",
        "vertraulichkeitsstufe": "Normal",
        "nac_workflow_version": "workflow-v1",
        "kg_version": "kg-v1",
    }


def _provisioned_state() -> dict:
    return {
        "workspaces": [
            {
                "id": "notary_team_01",
                "team_display_name": "NaC-Notar-01",
                "site_id": "example.sharepoint.com,site-01,web-01",
                "lists": {
                    "Akten": {"id": "list-akten"},
                    "AufgabenFristen": {"id": "list-tasks"},
                    "Vertretungsfreigaben": {"id": "list-grants"},
                    "AuditJournalLite": {"id": "list-audit"},
                    "DokumentRegister": {"id": "list-docs"},
                },
            }
        ]
    }


if __name__ == "__main__":
    unittest.main()
