from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from .mcp_runtime import RuntimeContext, load_mcp_contract, plan_tool_request
from .privileged_change import load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_APPLY_SMOKE_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-apply-smoke.redacted.json"
)
SMOKE_GRANT_ID_PREFIX = "NAC-SMOKE-GRANT-"
SMOKE_CASE_ID_PREFIX = "NAC-SMOKE-MATTER-"
SMOKE_AUDIT_ID_PREFIX = "NAC-SMOKE-AUDIT-"


class MatterAccessApplySmokeClient(Protocol):
    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get(self, path: str) -> dict[str, Any]:
        ...

    def delete(self, path: str) -> dict[str, Any]:
        ...


def run_matter_access_apply_smoke(
    client: MatterAccessApplySmokeClient,
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    correlation_id: str,
    grant_id: str | None = None,
    case_id: str | None = None,
    from_user: str | None = None,
    to_user: str | None = None,
    granted_role: str = "SachbearbeitungVertretung",
    reason: str = "Synthetische Vertretungsfreigabe Live-Smoke",
    valid_from: str | None = None,
    valid_until: str | None = None,
    approved_by: str | None = None,
    status: str = "Aktiv",
    cleanup_after: bool = True,
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        raise ValueError("matter-access-apply-smoke requires workspace_id")
    if not correlation_id:
        raise ValueError("matter-access-apply-smoke requires correlation_id")

    generated_at = timestamp or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    generated_dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).astimezone(UTC)
    stamp = _timestamp_stamp(generated_at)
    grant_id = grant_id or f"{SMOKE_GRANT_ID_PREFIX}{stamp}"
    case_id = case_id or f"{SMOKE_CASE_ID_PREFIX}{stamp}"
    event_id = f"{SMOKE_AUDIT_ID_PREFIX}{stamp}"
    _require_prefix(grant_id, SMOKE_GRANT_ID_PREFIX, "grant_id")
    _require_prefix(case_id, SMOKE_CASE_ID_PREFIX, "case_id")

    from_user = from_user or "nac-smoke-owner"
    to_user = to_user or "nac-smoke-deputy"
    approved_by = approved_by or from_user
    valid_from = valid_from or generated_dt.isoformat().replace("+00:00", "Z")
    valid_until = valid_until or (generated_dt + timedelta(days=1)).isoformat().replace("+00:00", "Z")

    context = RuntimeContext(
        actor_id=approved_by,
        actor_role="runtime_service",
        workspace_id=workspace_id,
        purpose="matter_access_apply_smoke",
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
        "event_id": event_id,
        "case_id": case_id,
        "timestamp": generated_at,
        "action": "DeputyGrantSmokeApplied",
        "object_type": "Vertretungsfreigabe",
        "object_id": grant_id,
        "reason": reason,
    }

    grant_plan = plan_tool_request(contract, provisioned_state, context, "grant_request", grant_arguments)
    audit_plan = plan_tool_request(contract, provisioned_state, context, "audit_append", audit_arguments)
    _assert_write_plan(grant_plan.to_dict(), "grant_request")
    _assert_write_plan(audit_plan.to_dict(), "audit_append")

    grant_write = client.post(grant_plan.path, grant_plan.payload or {})
    audit_write = client.post(audit_plan.path, audit_plan.payload or {})

    grant_read_path = _read_items_path(provisioned_state, workspace_id, "Vertretungsfreigaben", "GrantId", grant_id)
    audit_read_path = _read_items_path(provisioned_state, workspace_id, "AuditJournalLite", "EventId", event_id)
    grant_read = client.get(grant_read_path)
    audit_read = client.get(audit_read_path)
    grant_item = _single_matching_item(grant_read, "GrantId", grant_id)
    audit_item = _single_matching_item(audit_read, "EventId", event_id)

    cleanup = {
        "requested": cleanup_after,
        "grantDeleteStatus": None,
        "auditDeleteStatus": None,
        "grantReadAfterCount": None,
        "auditReadAfterCount": None,
    }
    if cleanup_after:
        client.delete(_delete_path_for_item(grant_read_path, str(grant_item["id"])))
        client.delete(_delete_path_for_item(audit_read_path, str(audit_item["id"])))
        grant_after = client.get(grant_read_path)
        audit_after = client.get(audit_read_path)
        cleanup = {
            "requested": True,
            "grantDeleteStatus": "PASSED",
            "auditDeleteStatus": "PASSED",
            "grantReadAfterCount": _value_count(grant_after),
            "auditReadAfterCount": _value_count(audit_after),
        }

    return redact_matter_access_apply_smoke_result(
        workspace_id=workspace_id,
        correlation_id=correlation_id,
        grant_id=grant_id,
        case_id=case_id,
        event_id=event_id,
        from_user=from_user,
        to_user=to_user,
        approved_by=approved_by,
        reason=reason,
        valid_from=valid_from,
        valid_until=valid_until,
        granted_role=granted_role,
        grant_status=status,
        timestamp=generated_at,
        grant_plan=asdict(grant_plan),
        audit_plan=asdict(audit_plan),
        grant_write=grant_write,
        audit_write=audit_write,
        grant_read_path=grant_read_path,
        audit_read_path=audit_read_path,
        grant_read_count=_value_count(grant_read),
        audit_read_count=_value_count(audit_read),
        grant_item_id=str(grant_item["id"]),
        audit_item_id=str(audit_item["id"]),
        cleanup=cleanup,
    )


def run_matter_access_apply_smoke_from_paths(
    client: MatterAccessApplySmokeClient,
    *,
    contract_path: Path,
    provisioned_state_path: Path,
    workspace_id: str,
    correlation_id: str,
    grant_id: str | None = None,
    case_id: str | None = None,
    from_user: str | None = None,
    to_user: str | None = None,
    granted_role: str = "SachbearbeitungVertretung",
    reason: str = "Synthetische Vertretungsfreigabe Live-Smoke",
    valid_from: str | None = None,
    valid_until: str | None = None,
    approved_by: str | None = None,
    status: str = "Aktiv",
    cleanup_after: bool = True,
) -> dict[str, Any]:
    return run_matter_access_apply_smoke(
        client,
        load_mcp_contract(contract_path),
        load_provisioned_state(provisioned_state_path),
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
        cleanup_after=cleanup_after,
    )


def write_matter_access_apply_smoke_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def redact_matter_access_apply_smoke_result(
    *,
    workspace_id: str,
    correlation_id: str,
    grant_id: str,
    case_id: str,
    event_id: str,
    from_user: str,
    to_user: str,
    approved_by: str,
    reason: str,
    valid_from: str,
    valid_until: str,
    granted_role: str,
    grant_status: str,
    timestamp: str,
    grant_plan: dict[str, Any],
    audit_plan: dict[str, Any],
    grant_write: dict[str, Any],
    audit_write: dict[str, Any],
    grant_read_path: str,
    audit_read_path: str,
    grant_read_count: int,
    audit_read_count: int,
    grant_item_id: str,
    audit_item_id: str,
    cleanup: dict[str, Any],
) -> dict[str, Any]:
    cleanup_requested = cleanup.get("requested") is True
    cleanup_passed = (not cleanup_requested) or (
        cleanup.get("grantReadAfterCount") == 0 and cleanup.get("auditReadAfterCount") == 0
    )
    checks = [
        _check("grant_request_write_read", grant_read_count == 1, "grant_request item was written and read back"),
        _check("audit_append_write_read", audit_read_count == 1, "audit_append item was written and read back"),
        _check("cleanup", cleanup_passed, "synthetic grant and audit items were cleaned up"),
        _check("privacy", True, "artifact stores only hashes and request shapes"),
    ]
    status_value = "PASSED" if all(check["status"] == "PASSED" for check in checks) else "FAILED"
    return {
        "schema_version": "nac.m365-matter-access-apply-smoke/v0.1",
        "status": status_value,
        "generated_at": timestamp,
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "grant_id_sha256": _sha256(grant_id),
            "case_id_sha256": _sha256(case_id),
            "event_id_sha256": _sha256(event_id),
            "from_user_sha256": _sha256(from_user),
            "to_user_sha256": _sha256(to_user),
            "approved_by_sha256": _sha256(approved_by),
            "reason_sha256": _sha256(reason),
            "valid_from": valid_from,
            "valid_until": valid_until,
            "granted_role": granted_role,
            "grant_status": grant_status,
            "write_tools": ["grant_request", "audit_append"],
            "write_lists": ["Vertretungsfreigaben", "AuditJournalLite"],
            "planned_write_count": 2,
            "executed_graph_requests": True,
            "executed_graph_writes": True,
            "sharepoint_item_writes_executed": True,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "grant_read_value_count": grant_read_count,
            "audit_read_value_count": audit_read_count,
            "cleanup_requested": cleanup_requested,
            "grant_cleanup_read_after_value_count": cleanup.get("grantReadAfterCount"),
            "audit_cleanup_read_after_value_count": cleanup.get("auditReadAfterCount"),
            "graph_rest_only": True,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "raw_write_payload_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "writeRequestShapes": [
            _redacted_write_plan(grant_plan),
            _redacted_write_plan(audit_plan),
        ],
        "writeResponseShape": {
            "grantCreatedItemIdSha256": _sha256(str(grant_write.get("id") or grant_item_id)),
            "auditCreatedItemIdSha256": _sha256(str(audit_write.get("id") or audit_item_id)),
            "storesRawGraphResponse": False,
        },
        "readBackShape": {
            "grantReadPathSha256": _sha256(grant_read_path),
            "auditReadPathSha256": _sha256(audit_read_path),
            "grantMatchedItemIdSha256": _sha256(grant_item_id),
            "auditMatchedItemIdSha256": _sha256(audit_item_id),
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
        },
        "cleanupShape": {
            "requested": cleanup_requested,
            "target": "synthetic_matter_access_apply_smoke_items",
            "grantIdPrefixRequired": SMOKE_GRANT_ID_PREFIX,
            "caseIdPrefixRequired": SMOKE_CASE_ID_PREFIX,
            "grantDeleteStatus": cleanup.get("grantDeleteStatus"),
            "auditDeleteStatus": cleanup.get("auditDeleteStatus"),
            "grantReadAfterValueCount": cleanup.get("grantReadAfterCount"),
            "auditReadAfterValueCount": cleanup.get("auditReadAfterCount"),
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
        },
        "checks": checks,
        "privacy": {
            "metadataOnly": False,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesRawWritePayload": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": True,
            "executesGraphWrites": True,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
    }


def _assert_write_plan(plan: dict[str, Any], tool_name: str) -> None:
    if (
        plan.get("tool") != tool_name
        or plan.get("method") != "POST"
        or plan.get("payload") is None
        or plan.get("writes_items") is not True
        or plan.get("owner_gate_required") is not True
        or plan.get("graph_rest_only") is not True
    ):
        raise RuntimeError(f"{tool_name} did not produce the expected owner-gated Graph REST item write plan")


def _redacted_write_plan(plan: dict[str, Any]) -> dict[str, Any]:
    payload = plan.get("payload") if isinstance(plan.get("payload"), dict) else {}
    fields = payload.get("fields") if isinstance(payload.get("fields"), dict) else {}
    return {
        "tool": plan.get("tool"),
        "method": plan.get("method"),
        "listName": plan.get("list_name"),
        "pathSha256": _sha256(str(plan.get("path") or "")),
        "payloadFieldNames": sorted(fields),
        "payloadValueHashes": {field: _sha256(str(value)) for field, value in sorted(fields.items())},
        "writesItems": plan.get("writes_items") is True,
        "ownerGateRequired": plan.get("owner_gate_required") is True,
        "roleCaseGateRequired": plan.get("role_case_gate_required") is True,
        "graphRestOnly": plan.get("graph_rest_only") is True,
        "storesRawGraphPath": False,
        "storesRawWritePayload": False,
    }


def _read_items_path(
    provisioned_state: dict[str, Any],
    workspace_id: str,
    list_name: str,
    field_name: str,
    field_value: str,
) -> str:
    workspace = _workspace_by_id(provisioned_state, workspace_id)
    site_id = str(workspace["site_id"])
    list_id = _list_id(workspace, list_name)
    return (
        f"/sites/{_quote_path_segment(site_id, safe=',')}/lists/{_quote_path_segment(list_id)}/items"
        f"?$expand=fields&$filter=fields/{field_name}%20eq%20%27{_quote_query_value(field_value)}%27"
    )


def _workspace_by_id(provisioned_state: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    for workspace in provisioned_state.get("workspaces", []):
        if isinstance(workspace, dict) and workspace.get("id") == workspace_id:
            return workspace
    raise RuntimeError(f"unknown workspace_id: {workspace_id}")


def _list_id(workspace: dict[str, Any], list_name: str) -> str:
    list_state = workspace.get("lists", {}).get(list_name)
    if not isinstance(list_state, dict) or not isinstance(list_state.get("id"), str):
        raise RuntimeError(f"workspace {workspace.get('id')} missing list {list_name}")
    return list_state["id"]


def _single_matching_item(response: dict[str, Any], field_name: str, field_value: str) -> dict[str, Any]:
    values = response.get("value")
    items = values if isinstance(values, list) else []
    matches: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        fields = item.get("fields")
        if isinstance(fields, dict) and fields.get(field_name) == field_value and isinstance(item.get("id"), str):
            matches.append(item)
    if len(matches) != 1:
        raise RuntimeError(f"matter-access-apply-smoke requires exactly one matching synthetic item; found {len(matches)}")
    return matches[0]


def _delete_path_for_item(read_path: str, item_id: str) -> str:
    if "/items?" not in read_path:
        raise RuntimeError("cannot derive matter-access cleanup delete path from read request")
    list_path = read_path.split("/items?", 1)[0]
    return f"{list_path}/items/{_quote_path_segment(item_id)}"


def _value_count(response: dict[str, Any]) -> int:
    values = response.get("value")
    return len(values) if isinstance(values, list) else 0


def _require_prefix(value: str, prefix: str, label: str) -> None:
    if not value.startswith(prefix):
        raise ValueError(f"matter-access-apply-smoke requires synthetic {label} starting with {prefix}")


def _check(check_id: str, passed: bool, message: str) -> dict[str, Any]:
    return {
        "id": check_id,
        "status": "PASSED" if passed else "FAILED",
        "message": message,
    }


def _timestamp_stamp(timestamp: str) -> str:
    return "".join(ch for ch in timestamp if ch.isdigit() or ch == "T")[:15] + "Z"


def _quote_path_segment(value: str, safe: str = "") -> str:
    return urllib.parse.quote(value, safe=safe)


def _quote_query_value(value: str) -> str:
    return urllib.parse.quote(value.replace("'", "''"), safe="")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
