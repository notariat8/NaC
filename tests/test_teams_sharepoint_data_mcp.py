from __future__ import annotations

import importlib.util
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
SCRIPTS_ROOT = REPO_ROOT / "scripts"
PROVISION_CLI_SPEC = importlib.util.spec_from_file_location(
    "provision_teams_sharepoint_graph",
    SCRIPTS_ROOT / "provision_teams_sharepoint_graph.py",
)
if PROVISION_CLI_SPEC is None or PROVISION_CLI_SPEC.loader is None:
    raise ImportError("Could not load provision_teams_sharepoint_graph.py")
provision_cli = importlib.util.module_from_spec(PROVISION_CLI_SPEC)
PROVISION_CLI_SPEC.loader.exec_module(provision_cli)
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_teams_sharepoint_graph_data_plane",
    SCRIPTS_ROOT / "validate_teams_sharepoint_graph_data_plane.py",
)
if VALIDATOR_SPEC is None or VALIDATOR_SPEC.loader is None:
    raise ImportError("Could not load validate_teams_sharepoint_graph_data_plane.py")
data_plane_validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(data_plane_validator)

from nac_m365_graph.mcp_runtime import (  # noqa: E402
    DEFAULT_MCP_CONTRACT,
    McpGateError,
    RuntimeContext,
    build_tool_manifest,
    load_mcp_contract,
    load_notarial_interface_inventory_contract,
    plan_tool_request,
    validate_mcp_contract,
)
from nac_m365_graph.mcp_live_read_smoke import (  # noqa: E402
    run_mcp_live_read_smoke,
    write_mcp_live_read_smoke_artifact,
)
from nac_m365_graph.mcp_inventory_smoke import (  # noqa: E402
    run_mcp_inventory_smoke,
    write_mcp_inventory_smoke_artifact,
)
from nac_m365_graph.mcp_positive_write_read_smoke import (  # noqa: E402
    run_mcp_positive_write_read_smoke,
    write_mcp_positive_write_read_smoke_artifact,
)
from nac_m365_graph.mcp_smoke_cleanup import (  # noqa: E402
    run_mcp_smoke_cleanup,
    write_mcp_smoke_cleanup_artifact,
)
from nac_m365_graph.mcp_smoke_leftover_cleanup import (  # noqa: E402
    run_mcp_smoke_leftover_cleanup,
    write_mcp_smoke_leftover_cleanup_artifact,
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
    def test_mcp_smoke_correlation_defaults_are_command_specific(self) -> None:
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-live-read-smoke", None),
            "mcp-live-read-smoke",
        )
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-inventory-smoke", None),
            "mcp-inventory-smoke",
        )
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-positive-write-read-smoke", None),
            "mcp-positive-write-read-smoke",
        )
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-smoke-cleanup", None),
            "mcp-smoke-cleanup",
        )
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-smoke-leftover-cleanup", None),
            "mcp-smoke-leftover-cleanup",
        )
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-smoke-suite", None),
            "mcp-smoke-suite",
        )
        self.assertEqual(
            provision_cli.resolve_mcp_smoke_correlation_id("mcp-smoke-leftover-cleanup", "explicit-corr"),
            "explicit-corr",
        )

    def test_contract_defines_graph_rest_only_mcp_boundary(self) -> None:
        contract = load_mcp_contract(DEFAULT_MCP_CONTRACT)

        self.assertEqual(validate_mcp_contract(contract), [])
        self.assertEqual(contract["server_id"], "teams-sharepoint-data-mcp")
        self.assertTrue(contract["graph"]["rest_only"])
        self.assertFalse(contract["runtime_boundary"]["executes_graph_requests"])
        self.assertFalse(contract["runtime_boundary"]["stores_tokens_or_secrets"])
        self.assertFalse(contract["runtime_boundary"]["reads_sharepoint_file_content"])
        readiness = contract["runtime_boundary"]["bpmn_viewer_runtime_readiness"]
        self.assertEqual(
            readiness["command"],
            "nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json",
        )
        self.assertFalse(readiness["executes_graph_requests"])
        self.assertFalse(readiness["reads_sharepoint_file_content"])
        self.assertTrue(readiness["owner_gate_required_before_live_bpmn_content_read"])
        self.assertEqual(set(readiness["live_read_tools_enabled_now"]), {"case_get", "document_list"})

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
                "bpmn_model_get",
                "process_register_list",
                "bpmn_viewer_overlay_get",
                "notarial_interface_inventory_list",
                "notarial_interface_boundary_check",
            },
        )

    def test_manifest_is_safe_for_cli_and_aiq_binding(self) -> None:
        manifest = build_tool_manifest(load_mcp_contract(DEFAULT_MCP_CONTRACT))

        self.assertEqual(manifest["serverId"], "teams-sharepoint-data-mcp")
        self.assertFalse(manifest["executesGraphRequests"])
        self.assertEqual(manifest["ownerGatedLiveRead"]["allowed_tools"], ["case_get", "document_list"])
        self.assertFalse(manifest["ownerGatedLiveRead"]["writes_allowed"])
        self.assertEqual(len(manifest["tools"]), 12)
        by_name = {tool["name"]: tool for tool in manifest["tools"]}
        self.assertTrue(by_name["notarial_interface_inventory_list"]["metadataOnly"])
        self.assertEqual(
            by_name["notarial_interface_boundary_check"]["sourceContract"],
            "workflow.notarial_application_interface_inventory",
        )
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
        boundary_check = by_name["notarial_interface_boundary_check"]
        self.assertEqual(
            boundary_check["inputSchema"]["properties"]["arguments"]["required"],
            ["interface_id", "requested_operation"],
        )

    def test_stdio_inventory_list_returns_metadata_only_contract_rows(self) -> None:
        server = _mcp_server()

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/call",
                "params": {
                    "name": "notarial_interface_inventory_list",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {},
                    },
                },
            }
        )

        self.assertIsNotNone(response)
        result = response["result"]
        structured = result["structuredContent"]
        self.assertEqual(structured["runtime_mode"], "metadata_inventory_only")
        self.assertFalse(structured["executes_graph_requests"])
        self.assertEqual(structured["source_contract"], "workflow.notarial_application_interface_inventory")
        self.assertEqual(len(structured["interfaces"]), 11)
        ids = {item["interfaceId"] for item in structured["interfaces"]}
        self.assertIn("ben", ids)
        self.assertIn("xjustiz_331", ids)
        self.assertIn("xnotar_xjustiz_package_boundary", ids)
        self.assertFalse(structured["privacy"]["callsExternalBnotkSystems"])
        serialized = json.dumps(structured, ensure_ascii=False)
        for forbidden in ("<html", "<xsd:schema", "IdentityToken=", "BEGIN CERTIFICATE"):
            self.assertNotIn(forbidden, serialized)

    def test_stdio_inventory_boundary_check_marks_safe_and_owner_gated_operations(self) -> None:
        server = _mcp_server(live_read_enabled=True, graph_client=_FakeGraphReadClient({"unexpected": True}))

        safe_response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 31,
                "method": "tools/call",
                "params": {
                    "name": "notarial_interface_boundary_check",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {
                            "interface_id": "zvr",
                            "requested_operation": "metadata_inventory",
                        },
                    },
                },
            }
        )
        gated_response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 32,
                "method": "tools/call",
                "params": {
                    "name": "notarial_interface_boundary_check",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {
                            "interface_id": "ben",
                            "requested_operation": "productive_ben_send_or_fetch",
                        },
                    },
                },
            }
        )

        self.assertIsNotNone(safe_response)
        safe_check = safe_response["result"]["structuredContent"]["boundary_check"]
        self.assertEqual(safe_check["boundaryStatus"], "allowed_metadata_only")
        self.assertTrue(safe_check["allowedNow"])
        self.assertFalse(safe_check["ownerGateRequired"])
        self.assertFalse(safe_response["result"]["structuredContent"]["executes_graph_requests"])

        self.assertIsNotNone(gated_response)
        gated_check = gated_response["result"]["structuredContent"]["boundary_check"]
        self.assertEqual(gated_check["boundaryStatus"], "owner_gate_required")
        self.assertFalse(gated_check["allowedNow"])
        self.assertTrue(gated_check["ownerGateRequired"])
        self.assertTrue(gated_check["privateOperatingFrameRequired"])
        self.assertEqual(gated_check["area"], "besonderes elektronisches Notarpostfach")

    def test_mcp_inventory_smoke_runs_metadata_tools_and_gate_checks_offline(self) -> None:
        result = run_mcp_inventory_smoke(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _interface_inventory_contract(),
            workspace_id="notary_team_01",
            correlation_id="inventory-corr",
            timestamp="2026-07-07T10:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["interface_count"], 11)
        self.assertEqual(result["summary"]["metadata_boundary_status"], "allowed_metadata_only")
        self.assertEqual(result["summary"]["owner_gated_boundary_status"], "owner_gate_required")
        self.assertTrue(result["summary"]["closed_gate_blocks"])
        self.assertFalse(result["summary"]["graph_requests_executed"])
        self.assertFalse(result["privacy"]["storesSourceFullText"])
        self.assertFalse(result["privacy"]["storesRawXsd"])
        self.assertFalse(result["privacy"]["storesCredentials"])
        self.assertFalse(result["privacy"]["storesMatterData"])
        self.assertFalse(result["privacy"]["callsExternalBnotkSystems"])
        serialized = json.dumps(result, ensure_ascii=False)
        for forbidden in ("<html", "<xsd:schema", "IdentityToken=", "BEGIN CERTIFICATE"):
            self.assertNotIn(forbidden, serialized)

    def test_mcp_inventory_smoke_writes_redacted_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "mcp-inventory-smoke.redacted.json"
            result = run_mcp_inventory_smoke(
                load_mcp_contract(DEFAULT_MCP_CONTRACT),
                _provisioned_state(),
                _interface_inventory_contract(),
                workspace_id="notary_team_01",
                correlation_id="inventory-corr",
                timestamp="2026-07-07T10:00:00Z",
            )
            write_mcp_inventory_smoke_artifact(result, output)
            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["tool_call_count"], 4)
        self.assertFalse(payload["privacy"]["executesGraphRequests"])

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

    def test_stdio_live_read_blocks_optional_bpmn_viewer_tools(self) -> None:
        graph_client = _FakeGraphReadClient({"unexpected": True})
        server = _mcp_server(live_read_enabled=True, graph_client=graph_client)

        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 37,
                "method": "tools/call",
                "params": {
                    "name": "bpmn_model_get",
                    "arguments": {
                        "context": _mcp_context(case_id="case-1"),
                        "arguments": {"bpmn_model_id": "model-1"},
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
        self.assertEqual(graph_client.posts[0][1]["fields"]["Vorgangstyp"], "immobilienkaufvertrag")
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

    def test_mcp_schema_binding_rejects_invalid_choice_values(self) -> None:
        schema = json.loads((REPO_ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json").read_text())
        akten_schema = {
            item["display_name"]: item
            for item in schema["sharepoint"]["lists"]
        }["Akten"]

        errors = data_plane_validator._validate_mcp_payload_fields(
            "case_create",
            akten_schema,
            {
                "fields": {
                    "NacCaseId": "case-1",
                    "Aktenzeichen": "SMOKE-1",
                    "Vorgangstyp": "synthetischer_mcp_smoke",
                    "Status": "Entwurf",
                    "NotarTeam": "NaC-Notar-01",
                    "Vertraulichkeitsstufe": "Normal",
                    "NacWorkflowVersion": "m365-mcp-smoke-v0.1",
                    "KgVersion": "kg-smoke-v0.1",
                }
            },
        )

        self.assertIn("invalid choice value 'synthetischer_mcp_smoke'", "\n".join(errors))

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

    def test_mcp_smoke_leftover_cleanup_deletes_only_prefix_matches_and_redacts(self) -> None:
        case_id_1 = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        case_id_2 = "NAC-SMOKE-WRITE-READ-20260706T120224Z"
        graph_client = _FakeGraphCleanupClient(
            get_responses=[
                {
                    "value": [
                        {"id": "raw-item-1", "fields": {"NacCaseId": case_id_1}},
                        {"id": "raw-item-2", "fields": {"NacCaseId": case_id_2}},
                    ]
                },
                {"value": []},
            ],
            delete_response={},
        )

        result = run_mcp_smoke_leftover_cleanup(
            graph_client,
            _provisioned_state(),
            workspace_id="notary_team_01",
            correlation_id="corr-leftover",
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["summary"]["read_before_value_count"], 2)
        self.assertEqual(result["summary"]["deleted_value_count"], 2)
        self.assertEqual(result["summary"]["read_after_value_count"], 0)
        self.assertEqual(len(graph_client.gets), 2)
        self.assertEqual(len(graph_client.deletes), 2)
        self.assertIn("startswith(fields/NacCaseId", graph_client.gets[0])
        self.assertIn("/sites/example.sharepoint.com,site-01,web-01/lists/list-akten/items", graph_client.deletes[0])
        serialized = json.dumps(result, ensure_ascii=False)
        for raw_value in (case_id_1, case_id_2, "raw-item-1", "raw-item-2", "example.sharepoint.com"):
            self.assertNotIn(raw_value, serialized)

    def test_mcp_smoke_leftover_cleanup_dry_run_does_not_delete(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphCleanupClient(
            get_responses=[{"value": [{"id": "raw-item-1", "fields": {"NacCaseId": case_id}}]}],
            delete_response={},
        )

        result = run_mcp_smoke_leftover_cleanup(
            graph_client,
            _provisioned_state(),
            workspace_id="notary_team_01",
            delete_after=False,
            timestamp="2026-07-06T00:00:00Z",
        )

        self.assertEqual(result["status"], "PASSED")
        self.assertFalse(result["summary"]["delete_requested"])
        self.assertEqual(result["summary"]["read_before_value_count"], 1)
        self.assertEqual(result["summary"]["deleted_value_count"], 0)
        self.assertEqual(result["summary"]["read_after_value_count"], 1)
        self.assertEqual(len(graph_client.gets), 1)
        self.assertEqual(graph_client.deletes, [])

    def test_mcp_smoke_leftover_cleanup_refuses_non_prefix_result_before_delete(self) -> None:
        graph_client = _FakeGraphCleanupClient(
            get_responses=[{"value": [{"id": "raw-item-1", "fields": {"NacCaseId": "case-1"}}]}],
            delete_response={},
        )

        with self.assertRaisesRegex(RuntimeError, "non-smoke case id"):
            run_mcp_smoke_leftover_cleanup(
                graph_client,
                _provisioned_state(),
                workspace_id="notary_team_01",
            )

        self.assertEqual(graph_client.deletes, [])

    def test_mcp_smoke_leftover_cleanup_refuses_pagination_before_delete(self) -> None:
        graph_client = _FakeGraphCleanupClient(
            get_responses=[
                {
                    "@odata.nextLink": "https://graph.microsoft.com/v1.0/next",
                    "value": [
                        {
                            "id": "raw-item-1",
                            "fields": {"NacCaseId": "NAC-SMOKE-WRITE-READ-20260706T120223Z"},
                        }
                    ],
                }
            ],
            delete_response={},
        )

        with self.assertRaisesRegex(RuntimeError, "pagination"):
            run_mcp_smoke_leftover_cleanup(
                graph_client,
                _provisioned_state(),
                workspace_id="notary_team_01",
            )

        self.assertEqual(graph_client.deletes, [])

    def test_mcp_smoke_leftover_cleanup_writes_redacted_artifact(self) -> None:
        case_id = "NAC-SMOKE-WRITE-READ-20260706T120223Z"
        graph_client = _FakeGraphCleanupClient(
            get_responses=[
                {"value": [{"id": "raw-item-1", "fields": {"NacCaseId": case_id}}]},
                {"value": []},
            ],
            delete_response={},
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "leftover.json"
            result = run_mcp_smoke_leftover_cleanup(
                graph_client,
                _provisioned_state(),
                workspace_id="notary_team_01",
                timestamp="2026-07-06T00:00:00Z",
            )
            write_mcp_smoke_leftover_cleanup_artifact(result, output)

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

    def test_optional_bpmn_viewer_tools_plan_graph_rest_requests_without_payloads(self) -> None:
        contract = load_mcp_contract(DEFAULT_MCP_CONTRACT)
        state = _provisioned_state()
        context = _open_context(case_id="case-1")

        bpmn_model = plan_tool_request(contract, state, context, "bpmn_model_get", {"bpmn_model_id": "model-1"})
        process_register = plan_tool_request(contract, state, context, "process_register_list", {})
        overlay = plan_tool_request(contract, state, context, "bpmn_viewer_overlay_get", {"case_id": "case-1"})

        self.assertEqual(bpmn_model.method, "GET")
        self.assertEqual(bpmn_model.list_name, "BPMN Models")
        self.assertIn("/lists/list-bpmn-models/items", bpmn_model.path)
        self.assertIn("fields/NacBpmnModelId%20eq%20%27model-1%27", bpmn_model.path)
        self.assertIn("fields/ContainsMatterData%20eq%20false", bpmn_model.path)
        self.assertIsNone(bpmn_model.payload)
        self.assertFalse(bpmn_model.reads_files)

        self.assertEqual(process_register.method, "GET")
        self.assertEqual(process_register.list_name, "Prozessregister")
        self.assertIn("/lists/list-process-register/items", process_register.path)
        self.assertIn("$top=50", process_register.path)
        self.assertIn("fields/ViewerEnabled%20eq%20true", process_register.path)
        self.assertIsNone(process_register.payload)

        self.assertEqual(overlay.method, "GET")
        self.assertEqual(overlay.list_name, "AufgabenFristen")
        self.assertIn("/lists/list-tasks/items", overlay.path)
        self.assertIn("fields/NacCaseId%20eq%20%27case-1%27", overlay.path)
        self.assertIsNone(overlay.payload)

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

    def test_task_create_payload_includes_optional_due_date(self) -> None:
        plan = plan_tool_request(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _open_context(case_id="case-1", write_approved=True),
            "task_create",
            {
                "task_id": "task-1",
                "case_id": "case-1",
                "bpmn_step_code": "draft-contract",
                "status": "Offen",
                "requires_notary_approval": True,
                "due_date": "2026-08-31T16:00:00Z",
            },
        )

        self.assertEqual(
            plan.payload,
            {
                "fields": {
                    "NacTaskId": "task-1",
                    "NacCaseId": "case-1",
                    "BpmnStepCode": "draft-contract",
                    "Status": "Offen",
                    "RequiresNotaryApproval": True,
                    "DueDate": "2026-08-31T16:00:00Z",
                }
            },
        )

    def test_task_create_payload_is_unchanged_without_due_date(self) -> None:
        plan = plan_tool_request(
            load_mcp_contract(DEFAULT_MCP_CONTRACT),
            _provisioned_state(),
            _open_context(case_id="case-1", write_approved=True),
            "task_create",
            {
                "task_id": "task-1",
                "case_id": "case-1",
                "bpmn_step_code": "draft-contract",
                "status": "Offen",
                "requires_notary_approval": True,
            },
        )

        self.assertEqual(
            plan.payload,
            {
                "fields": {
                    "NacTaskId": "task-1",
                    "NacCaseId": "case-1",
                    "BpmnStepCode": "draft-contract",
                    "Status": "Offen",
                    "RequiresNotaryApproval": True,
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
        self.assertEqual(payload["summary"]["tool_count"], 12)
        self.assertFalse(payload["result"]["executesGraphRequests"])

    def test_central_cli_mcp_inventory_smoke_runs_without_owner_or_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "mcp-inventory-smoke.redacted.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "mcp-inventory-smoke",
                    "--mcp-inventory-smoke-output",
                    str(output),
                    "--mcp-smoke-correlation-id",
                    "inventory-corr",
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )
            artifact = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["artifact_path"], str(output))
        self.assertEqual(payload["summary"]["correlation_id"], "inventory-corr")
        self.assertFalse(payload["summary"]["graph_requests_executed"])
        self.assertEqual(artifact["status"], "PASSED")
        self.assertFalse(artifact["privacy"]["storesMatterData"])

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
        self.assertEqual(len(lines[1]["result"]["tools"]), 12)

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

    def test_central_cli_test_environment_deploy_requires_owner_before_credentials(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "test-environment-deploy",
                "--format",
                "json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )

        self.assertEqual(result.returncode, 2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn("--owner-approved", payload["errors"][0])

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

    def test_central_cli_mcp_smoke_leftover_cleanup_requires_owner_approval(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "--repo-root",
                str(REPO_ROOT),
                "m365",
                "teams-sharepoint",
                "mcp-smoke-leftover-cleanup",
                "--mcp-leftover-dry-run",
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
                    "BPMN Models": {"id": "list-bpmn-models"},
                    "Prozessregister": {"id": "list-process-register"},
                },
            }
        ]
    }


def _interface_inventory_contract() -> dict:
    return load_notarial_interface_inventory_contract()


if __name__ == "__main__":
    unittest.main()
