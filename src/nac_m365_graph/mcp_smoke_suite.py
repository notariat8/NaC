from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .mcp_positive_write_read_smoke import run_mcp_positive_write_read_smoke
from .mcp_runtime import load_mcp_contract
from .mcp_smoke_cleanup import SMOKE_CASE_ID_PREFIX, run_mcp_smoke_cleanup
from .privileged_change import load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MCP_SMOKE_SUITE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "mcp-smoke-suite.redacted.json"
)


class GraphSmokeSuiteClient(Protocol):
    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get(self, path: str) -> dict[str, Any]:
        ...

    def delete(self, path: str) -> dict[str, Any]:
        ...


def run_mcp_smoke_suite(
    client: GraphSmokeSuiteClient,
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    case_id: str | None = None,
    correlation_id: str = "mcp-smoke-suite",
    cleanup_after: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    smoke_case_id = case_id or f"{SMOKE_CASE_ID_PREFIX}{_timestamp_stamp(generated_at)}"
    if not smoke_case_id.startswith(SMOKE_CASE_ID_PREFIX):
        raise ValueError(f"mcp-smoke-suite requires a synthetic case id starting with {SMOKE_CASE_ID_PREFIX}")

    positive_result = run_mcp_positive_write_read_smoke(
        client,
        contract,
        provisioned_state,
        workspace_id=workspace_id,
        case_id=smoke_case_id,
        correlation_id=correlation_id,
        timestamp=generated_at,
    )
    cleanup_result = None
    if cleanup_after:
        cleanup_result = run_mcp_smoke_cleanup(
            client,
            contract,
            provisioned_state,
            workspace_id=workspace_id,
            case_id=smoke_case_id,
            correlation_id=correlation_id,
            timestamp=generated_at,
        )
    return redact_mcp_smoke_suite_result(
        workspace_id=workspace_id,
        case_id=smoke_case_id,
        correlation_id=correlation_id,
        timestamp=generated_at,
        cleanup_after=cleanup_after,
        positive_result=positive_result,
        cleanup_result=cleanup_result,
    )


def run_mcp_smoke_suite_from_paths(
    client: GraphSmokeSuiteClient,
    *,
    contract_path: Path,
    provisioned_state_path: Path,
    workspace_id: str,
    case_id: str | None = None,
    correlation_id: str = "mcp-smoke-suite",
    cleanup_after: bool = False,
) -> dict[str, Any]:
    return run_mcp_smoke_suite(
        client,
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        workspace_id=workspace_id,
        case_id=case_id,
        correlation_id=correlation_id,
        cleanup_after=cleanup_after,
    )


def write_mcp_smoke_suite_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def redact_mcp_smoke_suite_result(
    *,
    workspace_id: str,
    case_id: str,
    correlation_id: str,
    timestamp: str,
    cleanup_after: bool,
    positive_result: dict[str, Any],
    cleanup_result: dict[str, Any] | None,
) -> dict[str, Any]:
    positive_summary = _dict(positive_result.get("summary"))
    cleanup_summary = _dict(cleanup_result.get("summary") if cleanup_result else None)
    positive_passed = positive_result.get("status") == "PASSED"
    cleanup_passed = (not cleanup_after) or (cleanup_result is not None and cleanup_result.get("status") == "PASSED")
    return {
        "status": "PASSED" if positive_passed and cleanup_passed else "FAILED",
        "generated_at": timestamp,
        "summary": {
            "workspace_id": workspace_id,
            "case_id_sha256": _sha256(case_id),
            "correlation_id": correlation_id,
            "positive_write_read_status": positive_result.get("status"),
            "write_status": positive_summary.get("write_status"),
            "read_status": positive_summary.get("read_status"),
            "read_value_count": positive_summary.get("read_value_count"),
            "cleanup_requested": cleanup_after,
            "cleanup_status": cleanup_result.get("status") if cleanup_result else None,
            "cleanup_read_after_value_count": cleanup_summary.get("read_after_value_count"),
            "graph_rest_only": True,
            "raw_case_id_stored": False,
            "raw_write_payload_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "positiveWriteReadShape": {
            "status": positive_result.get("status"),
            "writeRequest": _dict(positive_result.get("writeRequest")),
            "readArtifactShape": _dict(positive_result.get("readArtifactShape")),
            "privacy": _dict(positive_result.get("privacy")),
        },
        "cleanupShape": {
            "status": cleanup_result.get("status") if cleanup_result else None,
            "readRequest": _dict(cleanup_result.get("readRequest") if cleanup_result else None),
            "privacy": _dict(cleanup_result.get("privacy") if cleanup_result else None),
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


def _timestamp_stamp(timestamp: str) -> str:
    return "".join(ch for ch in timestamp if ch.isdigit() or ch == "T")[:15] + "Z"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
