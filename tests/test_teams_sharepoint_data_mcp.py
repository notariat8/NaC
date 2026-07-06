from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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
from nac_m365_graph.mcp_live_read_smoke import (  # noqa: E402
    run_mcp_live_read_smoke,
    write_mcp_live_read_smoke_artifact,
)
from nac_m365_graph.mcp_positive_write_read_smoke import (  # noqa: E402
    run_mcp_positive_write_read_smoke,
    write_mcp_positive_write_read_smoke_artifact,
)
from nac_m365_graph.mcp_smoke_cleanup import (  # noqa: E402
    run_mcp_smoke_cleanup,
    write_mcp_smoke_cleanup_artifact,
)
from nac_m365_graph.mcp_smoke_suite import (  # noqa: E402
    run_mcp_smoke_suite,
    write_mcp_smoke_suite_artifact,
)
from nac_m365_graph.mcp_stdio import (  # noqa: E402
    MCP_PROTOCOL_VERSION,
    TeamsSharePointDataMcpServer,
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
        self.assertEqual(manifest["ownerGatedLiveRead"]["allowed_tools"], ["case_get", "document_list"])
        self.assertFalse(manifest["ownerGatedLiveRead"]["writes_allowed"])
        self.assertEqual(len(manifest["tools"]), 7)
        for tool in manifest["tools"]:
            self.assertTrue(tool["requiresRoleCasePurposeGate"])
            self.assertFalse(tool["readsFiles"])

    def test_stdio_initialize_declares_tools_capability(self) -> None:
        server = _mcp_server()

        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )

        self.assertIsNotNone(response)
        result = response["result"]
        self.assertEqual(result["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.assertEqual(result["serverInfo"]["name"], "teams-sharepoint-data-mcp")
        self.assertIn("tools", result["capabilities"])

    def test_stdio_initialized_notification_has_no_response(self) -> None:
        server = _mcp_server()

        response = server.handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"})

        self.assertIsNone(response)

    def test_stdio_tools_list_returns_mcp_tool_schemas(self) -> None:
        server = _mcp_server()

        response = server.handle_message(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )

        self.assertIsNotNone(response)
        tools = response["result"]["tools"]
        by_name = {tool["name"]: tool for tool in tools}
        self.assertEqual(set(by_name), {tool["id"] for tool in load_mcp_contract(DEFAULT_MCP_CONTRACT)["tools"]})
        case_get = by_name["case_get"]
        self.assertEqual(case_get["inputSchema"]["required"], ["context", "arguments"])
        self.assertEqual(case_get["inputSchema"]["properties"]["arguments"]["required"], ["case_id"])

    def test_stdio_tools_call_returns_request_plan_structured_content(self) -> None:
        server = _mcp_server()

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "case_get",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {"case_id": "case-1"},
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        self.assertNotIn("isError", result)
        structured = result["structuredContent"]
        self.assertFalse(structured["executesGraphRequests"])
        self.assertEqual(structured["requestPlan"]["method"], "GET")
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", structured["requestPlan"]["path"])

    def test_stdio_live_read_executes_case_get_with_injected_graph_client(self) -> None:
        graph_client = _FakeGraphReadClient({"value": [{"id": "item-1", "fields": {"NacCaseId": "case-1"}}]})
        server = _mcp_server(live_read_enabled=True, graph_client=graph_client)

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 33,
                "method": "tools/call",
                "params": {
                    "name": "case_get",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {"case_id": "case-1"},
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        structured = result["structuredContent"]
        self.assertEqual(structured["runtimeMode"], "owner_gated_live_read")
        self.assertTrue(structured["executesGraphRequests"])
        self.assertEqual(structured["graphResponse"]["value"][0]["id"], "item-1")
        self.assertEqual(len(graph_client.paths), 1)
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", graph_client.paths[0])

    def test_stdio_live_read_executes_document_list_with_injected_graph_client(self) -> None:
        graph_client = _FakeGraphReadClient({"value": [{"id": "doc-1", "fields": {"NacCaseId": "case-1"}}]})
        server = _mcp_server(live_read_enabled=True, graph_client=graph_client)

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 34,
                "method": "tools/call",
                "params": {
                    "name": "document_list",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {"case_id": "case-1"},
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        structured = result["structuredContent"]
        self.assertTrue(structured["executesGraphRequests"])
        self.assertEqual(structured["requestPlan"]["list_name"], "DokumentRegister")
        self.assertEqual(structured["graphResponse"]["value"][0]["id"], "doc-1")
        self.assertIn("/lists/list-docs/items", graph_client.paths[0])

    def test_stdio_live_read_without_graph_client_returns_tool_error(self) -> None:
        server = _mcp_server(live_read_enabled=True)

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 35,
                "method": "tools/call",
                "params": {
                    "name": "case_get",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {"case_id": "case-1"},
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["errorType"], "McpLiveReadMissingClient")
        self.assertFalse(result["structuredContent"]["executesGraphRequests"])

    def test_stdio_live_read_blocks_write_tools_even_when_write_approved(self) -> None:
        graph_client = _FakeGraphReadClient({"unexpected": True})
        server = _mcp_server(live_read_enabled=True, graph_client=graph_client)

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 36,
                "method": "tools/call",
                "params": {
                    "name": "case_create",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1", write_approved=True),
                        "arguments": _case_create_arguments(),
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["errorType"], "McpLiveReadBlocked")
        self.assertFalse(result["structuredContent"]["executesGraphRequests"])
        self.assertEqual(graph_client.paths, [])

    def test_mcp_live_read_smoke_artifact_redacts_graph_values_case_id_and_path(self) -> None:
        graph_client = _FakeGraphReadClient(
            {
                "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#items",
                "@odata.nextLink": "https://graph.microsoft.com/v1.0/sites/site/items?$skiptoken=case-1",
                "value": [
                    {
                        "id": "raw-item-id",
                        "webUrl": "https://example.sharepoint.com/sites/notary/raw-item",
                        "fields": {
                            "NacCaseId": "case-1",
                            "Aktenzeichen": "AZ-1",
                            "BeteiligterName": "Alice Example",
                        },
                    }
                ],
            }
        )

        result = run_mcp_live_read_smoke(
            graph_client,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            tool_name="case_get",
            workspace_id="notary_team_01",
            case_id="case-1",
            correlation_id="corr-smoke",
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertTrue(result["summary"]["graph_read_executed"])
        self.assertEqual(result["graphResponseShape"]["valueCount"], 1)
        self.assertEqual(
            result["graphResponseShape"]["fieldNames"],
            ["Aktenzeichen", "BeteiligterName", "NacCaseId"],
        )
        self.assertNotIn("path", result["requestPlan"])
        self.assertIn("pathSha256", result["requestPlan"])
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in (
            "case-1",
            "AZ-1",
            "Alice Example",
            "raw-item-id",
            "example.sharepoint.com",
            "$skiptoken",
        ):
            self.assertNotIn(raw_value, serialized)

    def test_mcp_live_read_smoke_rejects_write_tools_before_graph_read(self) -> None:
        graph_client = _FakeGraphReadClient({"unexpected": True})

        with self.assertRaisesRegex(ValueError, "case_get or document_list"):
            run_mcp_live_read_smoke(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                tool_name="case_create",
                workspace_id="notary_team_01",
                case_id="case-1",
            )

        self.assertEqual(graph_client.paths, [])

    def test_mcp_live_read_smoke_writes_redacted_artifact(self) -> None:
        graph_client = _FakeGraphReadClient({"value": [{"id": "item-1", "fields": {"NacCaseId": "case-1"}}]})
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "smoke.json"
            result = run_mcp_live_read_smoke(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                tool_name="case_get",
                workspace_id="notary_team_01",
                case_id="case-1",
                timestamp="2026-07-06T00:00:00Z",
            )
            write_mcp_live_read_smoke_artifact(result, output)

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertNotIn("case-1", json.dumps(payload))

    def test_mcp_positive_write_read_smoke_creates_case_then_reads_and_redacts(self) -> None:
        graph_client = _FakeGraphWriteReadClient(
            post_response={"id": "raw-created-item-id"},
            get_response={
                "value": [
                    {
                        "id": "raw-created-item-id",
                        "fields": {
                            "NacCaseId": "case-1",
                            "Aktenzeichen": "AZ-1",
                            "Status": "Entwurf",
                        },
                    }
                ]
            },
        )

        result = run_mcp_positive_write_read_smoke(
            graph_client,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            workspace_id="notary_team_01",
            case_id="case-1",
            correlation_id="corr-smoke",
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["write_status"], "PASSED")
        self.assertEqual(result["summary"]["read_status"], "PASSED")
        self.assertEqual(result["summary"]["read_value_count"], 1)
        self.assertEqual(len(graph_client.posts), 1)
        self.assertEqual(len(graph_client.gets), 1)
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", graph_client.posts[0][0])
        self.assertEqual(result["writeRequest"]["payloadFieldNames"], [
            "Aktenzeichen",
            "KgVersion",
            "NacCaseId",
            "NacWorkflowVersion",
            "NotarTeam",
            "Status",
            "Vertraulichkeitsstufe",
            "Vorgangstyp",
        ])
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in ("case-1", "AZ-1", "raw-created-item-id", "example.sharepoint.com"):
            self.assertNotIn(raw_value, serialized)

    def test_mcp_positive_write_read_smoke_writes_redacted_artifact(self) -> None:
        graph_client = _FakeGraphWriteReadClient(
            post_response={"id": "raw-created-item-id"},
            get_response={"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": "case-1"}}]},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "positive-smoke.json"
            result = run_mcp_positive_write_read_smoke(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                case_id="case-1",
                timestamp="2026-07-06T00:00:00Z",
            )
            write_mcp_positive_write_read_smoke_artifact(result, output)

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["privacy"]["storesRawWritePayload"])
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertNotIn("case-1", json.dumps(payload))

    def test_mcp_smoke_cleanup_rejects_non_smoke_case_id_before_graph_calls(self) -> None:
        graph_client = _FakeGraphCleanupClient(get_responses=[], delete_response={})

        with self.assertRaisesRegex(ValueError, "NAC-SMOKE-WRITE-READ-"):
            run_mcp_smoke_cleanup(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                case_id="case-1",
            )

        self.assertEqual(graph_client.gets, [])
        self.assertEqual(graph_client.deletes, [])

    def test_mcp_smoke_cleanup_deletes_exact_synthetic_case_and_redacts(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphCleanupClient(
            get_responses=[
                {"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": case_id, "Aktenzeichen": "AZ-1"}}]},
                {"value": []},
            ],
            delete_response={},
        )

        result = run_mcp_smoke_cleanup(
            graph_client,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            workspace_id="notary_team_01",
            case_id=case_id,
            correlation_id="corr-cleanup",
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["read_before_value_count"], 1)
        self.assertEqual(result["summary"]["delete_status"], "PASSED")
        self.assertEqual(result["summary"]["read_after_value_count"], 0)
        self.assertEqual(len(graph_client.gets), 2)
        self.assertEqual(len(graph_client.deletes), 1)
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", graph_client.deletes[0])
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in (case_id, "AZ-1", "raw-created-item-id", "example.sharepoint.com"):
            self.assertNotIn(raw_value, serialized)

    def test_mcp_smoke_cleanup_writes_redacted_artifact(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphCleanupClient(
            get_responses=[
                {"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": case_id}}]},
                {"value": []},
            ],
            delete_response={},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "cleanup.json"
            result = run_mcp_smoke_cleanup(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                case_id=case_id,
                timestamp="2026-07-06T00:00:00Z",
            )
            write_mcp_smoke_cleanup_artifact(result, output)

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertNotIn(case_id, json.dumps(payload))

    def test_mcp_smoke_suite_runs_write_read_without_cleanup_and_redacts(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphSmokeSuiteClient(
            post_response={"id": "raw-created-item-id"},
            get_responses=[
                {"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": case_id, "Aktenzeichen": "AZ-1"}}]},
            ],
            delete_response={},
        )

        result = run_mcp_smoke_suite(
            graph_client,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            workspace_id="notary_team_01",
            case_id=case_id,
            correlation_id="corr-suite",
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["positive_write_read_status"], "PASSED")
        self.assertFalse(result["summary"]["cleanup_requested"])
        self.assertIsNone(result["summary"]["cleanup_status"])
        self.assertEqual(len(graph_client.posts), 1)
        self.assertEqual(len(graph_client.gets), 1)
        self.assertEqual(graph_client.deletes, [])
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in (case_id, "AZ-1", "raw-created-item-id", "example.sharepoint.com"):
            self.assertNotIn(raw_value, serialized)

    def test_mcp_smoke_suite_runs_write_read_cleanup_in_one_redacted_flow(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphSmokeSuiteClient(
            post_response={"id": "raw-created-item-id"},
            get_responses=[
                {"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": case_id, "Aktenzeichen": "AZ-1"}}]},
                {"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": case_id, "Aktenzeichen": "AZ-1"}}]},
                {"value": []},
            ],
            delete_response={},
        )

        result = run_mcp_smoke_suite(
            graph_client,
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            workspace_id="notary_team_01",
            case_id=case_id,
            cleanup_after=True,
            correlation_id="corr-suite",
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertTrue(result["summary"]["cleanup_requested"])
        self.assertEqual(result["summary"]["cleanup_status"], "PASSED")
        self.assertEqual(result["summary"]["cleanup_read_after_value_count"], 0)
        self.assertEqual(len(graph_client.posts), 1)
        self.assertEqual(len(graph_client.gets), 3)
        self.assertEqual(len(graph_client.deletes), 1)
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", graph_client.deletes[0])
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in (case_id, "AZ-1", "raw-created-item-id", "example.sharepoint.com"):
            self.assertNotIn(raw_value, serialized)

    def test_mcp_smoke_suite_rejects_non_smoke_case_id_before_graph_calls(self) -> None:
        graph_client = _FakeGraphSmokeSuiteClient(post_response={}, get_responses=[], delete_response={})

        with self.assertRaisesRegex(ValueError, "NAC-SMOKE-WRITE-READ-"):
            run_mcp_smoke_suite(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                case_id="case-1",
            )

        self.assertEqual(graph_client.posts, [])
        self.assertEqual(graph_client.gets, [])
        self.assertEqual(graph_client.deletes, [])

    def test_mcp_smoke_suite_writes_redacted_artifact(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphSmokeSuiteClient(
            post_response={"id": "raw-created-item-id"},
            get_responses=[
                {"value": [{"id": "raw-created-item-id", "fields": {"NacCaseId": case_id}}]},
            ],
            delete_response={},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "suite.json"
            result = run_mcp_smoke_suite(
                graph_client,
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                workspace_id="notary_team_01",
                case_id=case_id,
                timestamp="2026-07-06T00:00:00Z",
            )
            write_mcp_smoke_suite_artifact(result, output)

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "PASSED")
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertNotIn(case_id, json.dumps(payload))

    def test_stdio_tools_call_closed_gate_returns_tool_error(self) -> None:
        server = _mcp_server()

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "case_get",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1", role_case_gate="closed"),
                        "arguments": {"case_id": "case-1"},
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["structuredContent"]["errorType"], "McpGateError")
        self.assertFalse(result["structuredContent"]["executesGraphRequests"])

    def test_stdio_write_approval_requires_json_boolean_true(self) -> None:
        server = _mcp_server()
        context = _mcp_context(case_id="case-1", write_approved=True)
        context["write_approved"] = "false"

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "case_create",
                    "arguments": {
                        "context": context,
                        "arguments": _case_create_arguments(),
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        self.assertTrue(result["isError"])
        self.assertIn("write tool requires explicit write approval", result["content"][0]["text"])

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

    def test_central_cli_mcp_stdio_process_handles_initialize_and_tools_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            provisioned_state = Path(tmpdir) / "provisioned.json"
            provisioned_state.write_text(json.dumps(_provisioned_state()), encoding="utf-8")
            messages = "\n".join(
                [
                    json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
                    json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
                    "",
                ]
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "mcp-stdio",
                    "--provisioned-state",
                    str(provisioned_state),
                ],
                cwd=REPO_ROOT,
                input=messages,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        lines = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["result"]["protocolVersion"], MCP_PROTOCOL_VERSION)
        self.assertEqual(len(lines[1]["result"]["tools"]), 7)

    def test_central_cli_mcp_live_read_requires_owner_approval_before_stdio(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-stdio",
                "--mcp-live-read",
            ],
            cwd=REPO_ROOT,
            input="",
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("--owner-approved", result.stderr)

    def test_central_cli_mcp_live_read_smoke_requires_owner_approval(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-live-read-smoke",
                "--mcp-smoke-case-id",
                "case-1",
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

    def test_central_cli_mcp_live_read_smoke_requires_case_id_before_credentials(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-live-read-smoke",
                "--owner-approved",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("STATUS: BLOCKED", result.stdout)
        self.assertIn("--mcp-smoke-case-id", result.stdout)

    def test_central_cli_mcp_positive_write_read_smoke_requires_owner_approval(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-positive-write-read-smoke",
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

    def test_central_cli_mcp_smoke_cleanup_requires_owner_approval(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-smoke-cleanup",
                "--mcp-smoke-case-id",
                "NAC-SMOKE-WRITE-READ-20260706T120223Z",
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

    def test_central_cli_mcp_smoke_cleanup_requires_case_id_before_credentials(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-smoke-cleanup",
                "--owner-approved",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("STATUS: BLOCKED", result.stdout)
        self.assertIn("--mcp-smoke-case-id", result.stdout)

    def test_central_cli_mcp_smoke_suite_requires_owner_approval(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-smoke-suite",
                "--mcp-suite-cleanup",
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


class _FakeGraphReadClient:
    def __init__(self, response: dict) -> None:
        self.response = response
        self.paths: list[str] = []

    def get(self, path: str) -> dict:
        self.paths.append(path)
        return self.response


class _FakeGraphWriteReadClient:
    def __init__(self, post_response: dict, get_response: dict) -> None:
        self.post_response = post_response
        self.get_response = get_response
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[str] = []

    def post(self, path: str, payload: dict) -> dict:
        self.posts.append((path, payload))
        return self.post_response

    def get(self, path: str) -> dict:
        self.gets.append(path)
        return self.get_response


class _FakeGraphCleanupClient:
    def __init__(self, get_responses: list[dict], delete_response: dict) -> None:
        self.get_responses = list(get_responses)
        self.delete_response = delete_response
        self.gets: list[str] = []
        self.deletes: list[str] = []

    def get(self, path: str) -> dict:
        self.gets.append(path)
        if not self.get_responses:
            return {"value": []}
        return self.get_responses.pop(0)

    def delete(self, path: str) -> dict:
        self.deletes.append(path)
        return self.delete_response


class _FakeGraphSmokeSuiteClient:
    def __init__(self, post_response: dict, get_responses: list[dict], delete_response: dict) -> None:
        self.post_response = post_response
        self.get_responses = list(get_responses)
        self.delete_response = delete_response
        self.posts: list[tuple[str, dict]] = []
        self.gets: list[str] = []
        self.deletes: list[str] = []

    def post(self, path: str, payload: dict) -> dict:
        self.posts.append((path, payload))
        return self.post_response

    def get(self, path: str) -> dict:
        self.gets.append(path)
        if not self.get_responses:
            return {"value": []}
        return self.get_responses.pop(0)

    def delete(self, path: str) -> dict:
        self.deletes.append(path)
        return self.delete_response


def _mcp_server(
    *,
    live_read_enabled: bool = False,
    graph_client: _FakeGraphReadClient | None = None,
) -> TeamsSharePointDataMcpServer:
    return TeamsSharePointDataMcpServer(
        load_mcp_contract(DEFAULT_MCP_CONTRACT),
        _provisioned_state(),
        live_read_enabled=live_read_enabled,
        graph_client=graph_client,
    )


def _mcp_context(case_id: str, role_case_gate: str = "open", write_approved: bool = False) -> dict:
    return {
        "actor_id": "user-1",
        "actor_role": "notary_clerk",
        "workspace_id": "notary_team_01",
        "purpose": "matter_workflow",
        "correlation_id": "corr-1",
        "case_id": case_id,
        "role_case_gate": role_case_gate,
        "write_approved": write_approved,
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
