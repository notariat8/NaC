from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from .matter_access_apply_policy import MATTER_ACCESS_APPLY_POLICY_NEGATIVE_CASE_IDS
from .matter_access_apply_smoke import run_matter_access_apply_smoke
from .mcp_runtime import DEFAULT_MCP_CONTRACT, McpRuntimeError, load_mcp_contract
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_APPLY_POLICY_SMOKE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-apply-policy-smoke.redacted.json"
)


def run_matter_access_apply_policy_smoke_from_paths(
    *,
    contract_path: Path = DEFAULT_MCP_CONTRACT,
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    workspace_id: str,
    correlation_id: str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    return run_matter_access_apply_policy_smoke(
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        timestamp=timestamp,
    )


def run_matter_access_apply_policy_smoke(
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        raise ValueError("matter-access-apply-policy-smoke requires workspace_id")
    if not correlation_id:
        raise ValueError("matter-access-apply-policy-smoke requires correlation_id")
    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    cases = [
        _expected_exception_case(
            case_id="missing_reason",
            expected_failure_mode="pre_write_policy_validation",
            expected_error_type="MatterAccessApplyPolicyError",
            client=_FakeMatterAccessApplySmokeClient(),
            action=lambda client: run_matter_access_apply_smoke(
                client,
                contract,
                provisioned_state,
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                grant_id="NAC-SMOKE-GRANT-20260708T010000Z",
                case_id="NAC-SMOKE-MATTER-20260708T010000Z",
                reason="   ",
                timestamp=generated_at,
            ),
        ),
        _expected_exception_case(
            case_id="expired_delegation",
            expected_failure_mode="pre_write_time_window_validation",
            expected_error_type="MatterAccessApplyPolicyError",
            client=_FakeMatterAccessApplySmokeClient(),
            action=lambda client: run_matter_access_apply_smoke(
                client,
                contract,
                provisioned_state,
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                grant_id="NAC-SMOKE-GRANT-20260708T020000Z",
                case_id="NAC-SMOKE-MATTER-20260708T020000Z",
                valid_from="2026-07-01T09:00:00Z",
                valid_until="2026-07-02T09:00:00Z",
                timestamp=generated_at,
            ),
        ),
        _expected_exception_case(
            case_id="workspace_scope_violation",
            expected_failure_mode="workspace_scope_validation",
            expected_error_type="MatterAccessApplyPolicyError",
            client=_FakeMatterAccessApplySmokeClient(),
            action=lambda client: run_matter_access_apply_smoke(
                client,
                contract,
                provisioned_state,
                workspace_id="wrong_workspace",
                correlation_id=correlation_id,
                grant_id="NAC-SMOKE-GRANT-20260708T030000Z",
                case_id="NAC-SMOKE-MATTER-20260708T030000Z",
                timestamp=generated_at,
            ),
        ),
        _expected_exception_case(
            case_id="missing_cleanup",
            expected_failure_mode="cleanup_required",
            expected_error_type="MatterAccessApplyPolicyError",
            client=_FakeMatterAccessApplySmokeClient(),
            action=lambda client: run_matter_access_apply_smoke(
                client,
                contract,
                provisioned_state,
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                grant_id="NAC-SMOKE-GRANT-20260708T040000Z",
                case_id="NAC-SMOKE-MATTER-20260708T040000Z",
                cleanup_after=False,
                timestamp=generated_at,
            ),
        ),
        _expected_exception_case(
            case_id="audit_readback_missing",
            expected_failure_mode="audit_append_readback_required",
            expected_error_type="MatterAccessApplyPolicyError",
            client=_FakeMatterAccessApplySmokeClient(
                post_responses=[{"id": "raw-grant-item"}, {"id": "raw-audit-item"}],
                get_responses=[
                    {
                        "value": [
                            {
                                "id": "raw-grant-item",
                                "fields": {"GrantId": "NAC-SMOKE-GRANT-20260708T050000Z"},
                            }
                        ]
                    },
                    {"value": []},
                ],
            ),
            action=lambda client: run_matter_access_apply_smoke(
                client,
                contract,
                provisioned_state,
                workspace_id=workspace_id,
                correlation_id=correlation_id,
                grant_id="NAC-SMOKE-GRANT-20260708T050000Z",
                case_id="NAC-SMOKE-MATTER-20260708T050000Z",
                timestamp=generated_at,
            ),
        ),
    ]
    detected_count = sum(1 for case in cases if case["status"] == "PASSED")
    status = "PASSED" if detected_count == len(cases) else "FAILED"
    return {
        "schema_version": "nac.m365-matter-access-apply-policy-smoke/v0.1",
        "status": status,
        "generated_at": generated_at,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "negative_case_count": len(cases),
            "detected_policy_violation_count": detected_count,
            "expected_case_ids": list(MATTER_ACCESS_APPLY_POLICY_NEGATIVE_CASE_IDS),
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_writes_executed": False,
            "sharepoint_item_writes_executed": False,
            "uses_fake_graph_client": True,
            "graph_rest_only": True,
            "stores_tokens_or_secrets": False,
            "stores_raw_graph_path": False,
            "stores_raw_graph_response": False,
            "stores_raw_write_payload": False,
            "stores_matter_payloads": False,
            "reads_sharepoint_file_content": False,
        },
        "cases": cases,
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesMessagePayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "storesRawWritePayload": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
    }


def write_matter_access_apply_policy_smoke_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _expected_exception_case(
    *,
    case_id: str,
    expected_failure_mode: str,
    expected_error_type: str,
    client: _FakeMatterAccessApplySmokeClient,
    action: Callable[[_FakeMatterAccessApplySmokeClient], dict[str, Any]],
) -> dict[str, Any]:
    observed_error_type = None
    detected = False
    try:
        action(client)
    except (McpRuntimeError, RuntimeError, ValueError) as exc:
        observed_error_type = type(exc).__name__
        detected = observed_error_type == expected_error_type
    return _case_result(
        case_id=case_id,
        detected=detected,
        expected_failure_mode=expected_failure_mode,
        observed_error_type=observed_error_type,
        client=client,
    )


def _case_result(
    *,
    case_id: str,
    detected: bool,
    expected_failure_mode: str,
    observed_error_type: str | None,
    client: _FakeMatterAccessApplySmokeClient,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "status": "PASSED" if detected else "FAILED",
        "expected_failure_mode": expected_failure_mode,
        "observed_error_type": observed_error_type,
        "policy_violation_detected": detected,
        "fake_graph_client_used": True,
        "real_graph_requests_executed": False,
        "fake_graph_post_count": len(client.posts),
        "fake_graph_get_count": len(client.gets),
        "fake_graph_delete_count": len(client.deletes),
        "stores_raw_graph_path": False,
        "stores_raw_graph_response": False,
        "stores_raw_write_payload": False,
    }


class _FakeMatterAccessApplySmokeClient:
    def __init__(
        self,
        *,
        post_responses: list[dict[str, object]] | None = None,
        get_responses: list[dict[str, object]] | None = None,
        delete_response: dict[str, object] | None = None,
    ) -> None:
        self.post_responses = list(post_responses or [])
        self.get_responses = list(get_responses or [])
        self.delete_response = delete_response or {}
        self.posts: list[tuple[str, dict[str, object]]] = []
        self.gets: list[str] = []
        self.deletes: list[str] = []

    def post(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        self.posts.append((path, payload))
        if not self.post_responses:
            return {"id": f"raw-fake-item-{len(self.posts)}"}
        return self.post_responses.pop(0)

    def get(self, path: str) -> dict[str, object]:
        self.gets.append(path)
        if not self.get_responses:
            return {"value": []}
        return self.get_responses.pop(0)

    def delete(self, path: str) -> dict[str, object]:
        self.deletes.append(path)
        return self.delete_response
