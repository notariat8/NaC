from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .matter_access_delegation import DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT
from .matter_access_apply_readiness import build_matter_access_apply_readiness_from_paths
from .mcp_runtime import DEFAULT_MCP_CONTRACT, RuntimeContext, load_mcp_contract, plan_tool_request
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state
from .schema import DEFAULT_SCHEMA


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_APPLY_REQUEST_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-apply-request-plan.redacted.json"
)


def build_matter_access_apply_request_plan_from_paths(
    *,
    contract_path: Path = DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    schema_path: Path = DEFAULT_SCHEMA,
    mcp_contract_path: Path = DEFAULT_MCP_CONTRACT,
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    workspace_id: str,
    correlation_id: str,
    grant_id: str | None = None,
    case_id: str | None = None,
    from_user: str | None = None,
    to_user: str | None = None,
    granted_role: str = "SachbearbeitungVertretung",
    reason: str = "Synthetischer Offline-Vertretungsfreigabeplan",
    valid_from: str = "2026-07-08T09:00:00Z",
    valid_until: str = "2026-07-15T09:00:00Z",
    approved_by: str | None = None,
    status: str = "Aktiv",
    timestamp: str | None = None,
) -> dict[str, Any]:
    mcp_contract = load_mcp_contract(mcp_contract_path)
    provisioned_state = load_provisioned_state(provisioned_state_path)
    readiness = build_matter_access_apply_readiness_from_paths(
        contract_path=contract_path,
        schema_path=schema_path,
        mcp_contract_path=mcp_contract_path,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
    )
    return build_matter_access_apply_request_plan(
        mcp_contract,
        provisioned_state,
        readiness,
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        grant_id=grant_id,
        case_id=case_id,
        from_user=from_user,
        to_user=to_user,
        granted_role=granted_role,
        reason=reason,
        valid_from=valid_from,
        valid_until=valid_until,
        approved_by=approved_by,
        status=status,
        timestamp=timestamp,
    )


def build_matter_access_apply_request_plan(
    mcp_contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    readiness: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str,
    grant_id: str | None = None,
    case_id: str | None = None,
    from_user: str | None = None,
    to_user: str | None = None,
    granted_role: str = "SachbearbeitungVertretung",
    reason: str = "Synthetischer Offline-Vertretungsfreigabeplan",
    valid_from: str = "2026-07-08T09:00:00Z",
    valid_until: str = "2026-07-15T09:00:00Z",
    approved_by: str | None = None,
    status: str = "Aktiv",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        raise ValueError("matter-access-apply-request-plan requires workspace_id")
    if not correlation_id:
        raise ValueError("matter-access-apply-request-plan requires correlation_id")
    if readiness.get("status") != "PASSED":
        raise ValueError("matter-access-apply-readiness must pass before rendering an apply request plan")

    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    grant_id = grant_id or f"grant-{correlation_id}"
    case_id = case_id or f"case-{correlation_id}"
    from_user = from_user or "lead-notary"
    to_user = to_user or "deputy-user"
    approved_by = approved_by or from_user

    context = RuntimeContext(
        actor_id=approved_by,
        actor_role="lead_notary",
        workspace_id=workspace_id,
        purpose="deputy_access_grant",
        correlation_id=correlation_id,
        case_id=case_id,
        role_case_gate="open",
        write_approved=True,
    )
    grant_arguments = {
        "grant_id": grant_id,
        "case_id": case_id,
        "from_user": from_user,
        "to_user": to_user,
        "granted_role": granted_role,
        "reason": reason,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "approved_by": approved_by,
        "status": status,
    }
    audit_arguments = {
        "event_id": f"audit-{correlation_id}",
        "case_id": case_id,
        "timestamp": generated_at,
        "action": "DeputyGrantRequested",
        "object_type": "Vertretungsfreigabe",
        "object_id": grant_id,
    }

    grant_plan = plan_tool_request(mcp_contract, provisioned_state, context, "grant_request", grant_arguments)
    audit_plan = plan_tool_request(mcp_contract, provisioned_state, context, "audit_append", audit_arguments)
    request_plans = [
        _redacted_request_plan(grant_plan.to_dict()),
        _redacted_request_plan(audit_plan.to_dict()),
    ]
    plan_hash = _stable_hash(
        {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "request_plans": request_plans,
        }
    )
    checks = [
        _check("apply_readiness", readiness.get("status") == "PASSED", "matter-access-apply-readiness passed"),
        _check("grant_request_plan", grant_plan.tool == "grant_request", "grant_request write plan rendered"),
        _check("audit_append_plan", audit_plan.tool == "audit_append", "audit_append write plan rendered"),
        _check(
            "owner_gate",
            grant_plan.owner_gate_required and audit_plan.owner_gate_required,
            "grant and audit plans require write approval",
        ),
        _check("privacy", _privacy_ok(request_plans), "request plan stores only redacted metadata and hashes"),
    ]
    errors = [check["message"] for check in checks if check["status"] != "PASSED"]
    status_value = "PASSED" if not errors else "FAILED"
    return {
        "schema_version": "nac.m365-matter-access-apply-request-plan/v0.1",
        "status": status_value,
        "generated_at": generated_at,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "request_plan_hash": plan_hash,
            "future_apply_mode": "owner_gated_graph_rest_item_writes",
            "planned_write_count": len(request_plans),
            "planned_tools": [plan["tool"] for plan in request_plans],
            "planned_lists": [plan["list_name"] for plan in request_plans],
            "required_write_approval": True,
            "owner_gate_required": True,
            "role_case_purpose_gate_required": True,
            "grant_id_sha256": _hash_value(grant_id),
            "case_id_sha256": _hash_value(case_id),
            "from_user_sha256": _hash_value(from_user),
            "to_user_sha256": _hash_value(to_user),
            "approved_by_sha256": _hash_value(approved_by),
            "reason_sha256": _hash_value(reason),
            "valid_from": valid_from,
            "valid_until": valid_until,
            "granted_role": granted_role,
            "grant_status": status,
            "graph_rest_only": True,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
            "reads_sharepoint_file_content": False,
        },
        "request_plans": request_plans,
        "checks": checks,
        "privacy": {
            "metadataOnly": True,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesMessagePayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
        "errors": errors,
    }


def write_matter_access_apply_request_plan_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _redacted_request_plan(plan: dict[str, Any]) -> dict[str, Any]:
    payload = plan.get("payload") if isinstance(plan.get("payload"), dict) else {}
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    return {
        "tool": plan.get("tool"),
        "method": plan.get("method"),
        "list_name": plan.get("list_name"),
        "path_sha256": _hash_value(str(plan.get("path") or "")),
        "path_template": "/sites/{site-id}/lists/{list-id}/items",
        "payload_field_names": sorted(fields),
        "payload_value_hashes": {field: _hash_value(str(value)) for field, value in sorted(fields.items())},
        "reads_items": plan.get("reads_items") is True,
        "reads_files": plan.get("reads_files") is True,
        "writes_items": plan.get("writes_items") is True,
        "owner_gate_required": plan.get("owner_gate_required") is True,
        "role_case_gate_required": plan.get("role_case_gate_required") is True,
        "graph_rest_only": plan.get("graph_rest_only") is True,
        "executes_graph_requests_now": False,
        "stores_raw_graph_path": False,
        "stores_raw_graph_response": False,
    }


def _check(check_id: str, passed: bool, message: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "PASSED" if passed else "FAILED",
        "message": message,
        "executesGraphRequests": False,
    }


def _privacy_ok(request_plans: list[dict[str, Any]]) -> bool:
    return all(
        plan.get("stores_raw_graph_path") is False
        and plan.get("stores_raw_graph_response") is False
        and plan.get("reads_files") is False
        and plan.get("writes_items") is True
        for plan in request_plans
    )


def _stable_hash(value: dict[str, Any]) -> str:
    return _hash_value(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _hash_value(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
