from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .mcp_live_read_smoke import run_mcp_live_read_smoke
from .mcp_runtime import RuntimeContext, load_mcp_contract, plan_tool_request
from .privileged_change import load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_POSITIVE_WRITE_READ_SMOKE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "mcp-positive-write-read-smoke.redacted.json"
)


class GraphWriteReadClient(Protocol):
    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get(self, path: str) -> dict[str, Any]:
        ...


def run_mcp_positive_write_read_smoke(
    client: GraphWriteReadClient,
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    case_id: str | None = None,
    correlation_id: str = "mcp-positive-write-read-smoke",
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    smoke_case_id = case_id or f"NAC-SMOKE-WRITE-READ-{_timestamp_stamp(generated_at)}"
    context = RuntimeContext(
        actor_id="nac-positive-write-read-smoke",
        actor_role="runtime_service",
        workspace_id=workspace_id,
        purpose="m365_mcp_positive_write_read_smoke",
        correlation_id=correlation_id,
        case_id=smoke_case_id,
        role_case_gate="open",
        write_approved=True,
    )
    write_arguments = _case_create_arguments(smoke_case_id, workspace_id, generated_at)
    write_plan = plan_tool_request(contract, provisioned_state, context, "case_create", write_arguments)
    if write_plan.method != "POST" or write_plan.payload is None or not write_plan.writes_items:
        raise RuntimeError("case_create did not produce the expected Graph REST POST item write plan")

    write_response = client.post(write_plan.path, write_plan.payload)
    read_result = run_mcp_live_read_smoke(
        client,
        contract,
        provisioned_state,
        tool_name="case_get",
        workspace_id=workspace_id,
        case_id=smoke_case_id,
        correlation_id=correlation_id,
        timestamp=generated_at,
    )
    return redact_mcp_positive_write_read_smoke_result(
        write_plan=asdict(write_plan),
        write_response=write_response,
        read_result=read_result,
        workspace_id=workspace_id,
        case_id=smoke_case_id,
        correlation_id=correlation_id,
        timestamp=generated_at,
    )


def run_mcp_positive_write_read_smoke_from_paths(
    client: GraphWriteReadClient,
    *,
    contract_path: Path,
    provisioned_state_path: Path,
    workspace_id: str,
    case_id: str | None = None,
    correlation_id: str = "mcp-positive-write-read-smoke",
) -> dict[str, Any]:
    return run_mcp_positive_write_read_smoke(
        client,
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        workspace_id=workspace_id,
        case_id=case_id,
        correlation_id=correlation_id,
    )


def write_mcp_positive_write_read_smoke_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def redact_mcp_positive_write_read_smoke_result(
    *,
    write_plan: dict[str, Any],
    write_response: dict[str, Any],
    read_result: dict[str, Any],
    workspace_id: str,
    case_id: str,
    correlation_id: str,
    timestamp: str,
) -> dict[str, Any]:
    item_id = write_response.get("id")
    read_summary = read_result.get("summary") if isinstance(read_result.get("summary"), dict) else {}
    read_shape = read_result.get("graphResponseShape") if isinstance(read_result.get("graphResponseShape"), dict) else {}
    status = "PASSED" if read_result.get("status") == "PASSED" and read_summary.get("value_count") == 1 else "FAILED"
    return {
        "status": status,
        "generated_at": timestamp,
        "summary": {
            "workspace_id": workspace_id,
            "case_id_sha256": _sha256(case_id),
            "correlation_id": correlation_id,
            "write_tool": "case_create",
            "write_status": "PASSED",
            "created_item_id_sha256": _sha256(item_id) if isinstance(item_id, str) and item_id else None,
            "read_tool": "case_get",
            "read_status": read_result.get("status"),
            "read_value_count": read_summary.get("value_count"),
            "graph_rest_only": True,
            "raw_case_id_stored": False,
            "raw_write_payload_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "writeRequest": _redacted_write_plan(write_plan),
        "readArtifactShape": {
            "status": read_result.get("status"),
            "valueCount": read_shape.get("valueCount"),
            "fieldNames": read_shape.get("fieldNames"),
            "privacy": read_result.get("privacy"),
        },
        "privacy": {
            "storesRawGraphResponse": False,
            "storesRawWritePayload": False,
            "storesRawCaseId": False,
            "storesRawGraphPath": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def _case_create_arguments(case_id: str, workspace_id: str, timestamp: str) -> dict[str, str]:
    return {
        "case_id": case_id,
        "aktenzeichen": f"SMOKE-{_timestamp_stamp(timestamp)}",
        "vorgangstyp": "synthetischer_mcp_smoke",
        "status": "Entwurf",
        "notar_team": "NaC-Notar-01" if workspace_id == "notary_team_01" else "NaC-Notar-02",
        "vertraulichkeitsstufe": "Normal",
        "nac_workflow_version": "m365-mcp-smoke-v0.1",
        "kg_version": "kg-smoke-v0.1",
    }


def _redacted_write_plan(write_plan: dict[str, Any]) -> dict[str, Any]:
    payload = write_plan.get("payload")
    fields = payload.get("fields") if isinstance(payload, dict) else {}
    return {
        "tool": write_plan.get("tool"),
        "method": write_plan.get("method"),
        "listName": write_plan.get("list_name"),
        "pathSha256": _sha256(write_plan["path"]) if isinstance(write_plan.get("path"), str) else None,
        "payloadPresent": payload is not None,
        "payloadFieldNames": sorted(fields) if isinstance(fields, dict) else [],
        "writesItems": write_plan.get("writes_items") is True,
        "graphRestOnly": write_plan.get("graph_rest_only") is True,
    }


def _timestamp_stamp(timestamp: str) -> str:
    return "".join(ch for ch in timestamp if ch.isdigit() or ch == "T")[:15] + "Z"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
