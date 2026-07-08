from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT = (
    REPO_ROOT / "tests" / "fixtures" / "m365" / "matter-access-decision-replay.snapshot.json"
)
DEFAULT_MATTER_ACCESS_DECISION_REPLAY_OUTPUT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-decision-replay.redacted.json"
)

ALLOWED_DEPUTY_ROLES = {"NotarVertretung", "SachbearbeitungVertretung", "NurLesen"}
ACTIVE_GRANT_STATUS = "Aktiv"


def load_matter_access_decision_snapshot(
    path: Path = DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def replay_matter_access_decisions_from_path(
    *,
    snapshot_path: Path = DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
    reference_time: str | datetime | None = None,
    correlation_id: str = "matter-access-decision-replay",
) -> dict[str, Any]:
    return replay_matter_access_decisions(
        load_matter_access_decision_snapshot(snapshot_path),
        reference_time=reference_time,
        correlation_id=correlation_id,
    )


def replay_matter_access_decisions(
    snapshot: dict[str, Any],
    *,
    reference_time: str | datetime | None = None,
    correlation_id: str = "matter-access-decision-replay",
) -> dict[str, Any]:
    if not correlation_id:
        raise ValueError("matter-access-decision-replay requires correlation_id")

    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    reference = _reference_timestamp(reference_time or snapshot.get("reference_time") or generated_at)
    cases = _list_fields(snapshot, "Akten")
    grants = _list_fields(snapshot, "Vertretungsfreigaben")
    audit_events = _list_fields(snapshot, "AuditJournalLite")
    requests = snapshot.get("decision_requests")
    if not isinstance(requests, list) or not requests:
        raise ValueError("matter-access-decision-replay snapshot requires decision_requests")

    workspace_bindings = _workspace_bindings(snapshot)
    decisions = [
        _evaluate_request(request, cases, grants, audit_events, workspace_bindings, reference)
        for request in requests
        if isinstance(request, dict)
    ]
    if len(decisions) != len(requests):
        raise ValueError("matter-access-decision-replay decision_requests entries must be objects")

    decision_code_counts = _count_by(decisions, "decision_code")
    errors = [
        f"expected decision mismatch for request hash {decision['request_ref_sha256']}"
        for decision in decisions
        if decision.get("expected_match") is False
    ]
    status = "PASSED" if not errors else "FAILED"
    allowed_count = sum(1 for decision in decisions if decision["decision"] == "ALLOW")
    blocked_count = sum(1 for decision in decisions if decision["decision"] == "BLOCK")

    return {
        "schema_version": "nac.m365-matter-access-decision-replay/v0.1",
        "status": status,
        "generated_at": generated_at,
        "summary": {
            "snapshot_schema_version": snapshot.get("schema_version"),
            "snapshot_sha256": _stable_hash(snapshot),
            "correlation_id_sha256": _hash_value(correlation_id),
            "reference_time": reference.isoformat().replace("+00:00", "Z"),
            "request_count": len(decisions),
            "case_count": len(cases),
            "grant_count": len(grants),
            "audit_event_count": len(audit_events),
            "allowed_count": allowed_count,
            "blocked_count": blocked_count,
            "expected_decision_mismatch_count": len(errors),
            "decision_code_counts": decision_code_counts,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "reads_sharepoint_file_content": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
        },
        "decisions": decisions,
        "checks": _checks(decisions, errors),
        "privacy": _privacy_flags(),
        "errors": errors,
    }


def write_matter_access_decision_replay_artifact(result: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _evaluate_request(
    request: dict[str, Any],
    cases: list[dict[str, Any]],
    grants: list[dict[str, Any]],
    audit_events: list[dict[str, Any]],
    workspace_bindings: dict[str, str],
    reference: datetime,
) -> dict[str, Any]:
    actor_id = _required_text(request, "actor_id")
    workspace_id = _required_text(request, "workspace_id")
    case_id = _required_text(request, "case_id")
    request_ref = _required_text(request, "id")
    request_correlation_id = _required_text(request, "correlation_id")

    case = _case_by_id(cases, case_id)
    actor_grants = [grant for grant in grants if _text(grant.get("ToUser")) == actor_id]
    case_grants = [grant for grant in actor_grants if _text(grant.get("NacCaseId")) == case_id]
    matching_audit_count = sum(
        1
        for grant in case_grants
        for event in audit_events
        if _text(event.get("CorrelationId")) and _text(event.get("CorrelationId")) == _text(grant.get("AuditCorrelationId"))
    )

    if case is None:
        return _decision(
            request,
            decision="BLOCK",
            decision_code="BLOCK_CASE_NOT_FOUND",
            matched_rule="case_lookup",
            candidate_grant_count=len(actor_grants),
            matching_case_grant_count=0,
            matching_audit_event_count=0,
        )
    if not _workspace_matches(case, workspace_id, workspace_bindings):
        return _decision(
            request,
            decision="BLOCK",
            decision_code="BLOCK_WORKSPACE_SCOPE",
            matched_rule="workspace_scope",
            candidate_grant_count=len(actor_grants),
            matching_case_grant_count=len(case_grants),
            matching_audit_event_count=matching_audit_count,
        )
    if _has_blanket_visibility(case):
        return _decision(
            request,
            decision="BLOCK",
            decision_code="BLOCK_BLANKET_VISIBILITY",
            matched_rule="blanket_visibility_guard",
            candidate_grant_count=len(actor_grants),
            matching_case_grant_count=len(case_grants),
            matching_audit_event_count=matching_audit_count,
        )
    if actor_id == _text(case.get("FederfuehrenderNotar")):
        return _decision(
            request,
            decision="ALLOW",
            decision_code="ALLOW_LEAD_NOTARY",
            matched_rule="primary_assignment_lead_notary",
            candidate_grant_count=len(actor_grants),
            matching_case_grant_count=len(case_grants),
            matching_audit_event_count=matching_audit_count,
        )
    if actor_id in _user_set(case.get("Sachbearbeitung")):
        return _decision(
            request,
            decision="ALLOW",
            decision_code="ALLOW_ASSIGNED_CLERK",
            matched_rule="primary_assignment_assigned_clerk",
            candidate_grant_count=len(actor_grants),
            matching_case_grant_count=len(case_grants),
            matching_audit_event_count=matching_audit_count,
        )
    if not case_grants and actor_grants:
        return _decision(
            request,
            decision="BLOCK",
            decision_code="BLOCK_CASE_SCOPE",
            matched_rule="deputy_grant_case_scope",
            candidate_grant_count=len(actor_grants),
            matching_case_grant_count=0,
            matching_audit_event_count=0,
        )
    if not case_grants:
        return _decision(
            request,
            decision="BLOCK",
            decision_code="BLOCK_NO_MATCHING_ACCESS_RULE",
            matched_rule="no_assignment_or_deputy_grant",
            candidate_grant_count=0,
            matching_case_grant_count=0,
            matching_audit_event_count=0,
        )

    grant_decisions = [_evaluate_grant(grant, reference) for grant in case_grants]
    for grant_decision in grant_decisions:
        if grant_decision["decision"] == "ALLOW":
            return _decision(
                request,
                decision="ALLOW",
                decision_code="ALLOW_ACTIVE_DEPUTY_GRANT",
                matched_rule="active_deputy_grant",
                candidate_grant_count=len(actor_grants),
                matching_case_grant_count=len(case_grants),
                matching_audit_event_count=matching_audit_count,
                grant_status=ACTIVE_GRANT_STATUS,
            )
    first_block = grant_decisions[0]
    return _decision(
        request,
        decision="BLOCK",
        decision_code=first_block["decision_code"],
        matched_rule=first_block["matched_rule"],
        candidate_grant_count=len(actor_grants),
        matching_case_grant_count=len(case_grants),
        matching_audit_event_count=matching_audit_count,
        grant_status=first_block.get("grant_status"),
    )


def _evaluate_grant(grant: dict[str, Any], reference: datetime) -> dict[str, str]:
    status = _text(grant.get("Status"))
    if status != ACTIVE_GRANT_STATUS:
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_INACTIVE",
            "matched_rule": "deputy_grant_status",
            "grant_status": status,
        }
    if _text(grant.get("GrantedRole")) not in ALLOWED_DEPUTY_ROLES:
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_ROLE_NOT_ALLOWED",
            "matched_rule": "deputy_grant_role",
            "grant_status": status,
        }
    if not _text(grant.get("Reason")).strip():
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_MISSING_REASON",
            "matched_rule": "deputy_grant_reason",
            "grant_status": status,
        }
    valid_from = _optional_timestamp(grant.get("ValidFrom"))
    valid_until = _optional_timestamp(grant.get("ValidUntil"))
    if valid_from is None or valid_until is None or valid_until <= valid_from:
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_INVALID_WINDOW",
            "matched_rule": "deputy_grant_validity_window",
            "grant_status": status,
        }
    if reference < valid_from:
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_NOT_YET_ACTIVE",
            "matched_rule": "deputy_grant_validity_window",
            "grant_status": status,
        }
    if valid_until <= reference:
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_EXPIRED",
            "matched_rule": "deputy_grant_validity_window",
            "grant_status": status,
        }
    if not _text(grant.get("ApprovedBy")).strip():
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_MISSING_APPROVER",
            "matched_rule": "deputy_grant_approver",
            "grant_status": status,
        }
    if not _text(grant.get("AuditCorrelationId")).strip():
        return {
            "decision": "BLOCK",
            "decision_code": "BLOCK_DEPUTY_GRANT_MISSING_AUDIT_CORRELATION",
            "matched_rule": "deputy_grant_audit_correlation",
            "grant_status": status,
        }
    return {
        "decision": "ALLOW",
        "decision_code": "ALLOW_ACTIVE_DEPUTY_GRANT",
        "matched_rule": "active_deputy_grant",
        "grant_status": status,
    }


def _decision(
    request: dict[str, Any],
    *,
    decision: str,
    decision_code: str,
    matched_rule: str,
    candidate_grant_count: int,
    matching_case_grant_count: int,
    matching_audit_event_count: int,
    grant_status: str | None = None,
) -> dict[str, Any]:
    expected_decision = request.get("expected_decision")
    expected_decision_code = request.get("expected_decision_code")
    expected_match = True
    if expected_decision is not None:
        expected_match = expected_match and expected_decision == decision
    if expected_decision_code is not None:
        expected_match = expected_match and expected_decision_code == decision_code
    payload = {
        "request_ref_sha256": _hash_value(_required_text(request, "id")),
        "case_id_sha256": _hash_value(_required_text(request, "case_id")),
        "actor_id_sha256": _hash_value(_required_text(request, "actor_id")),
        "workspace_id_sha256": _hash_value(_required_text(request, "workspace_id")),
        "request_correlation_id_sha256": _hash_value(_required_text(request, "correlation_id")),
        "decision": decision,
        "decision_code": decision_code,
        "matched_rule": matched_rule,
        "candidate_grant_count": candidate_grant_count,
        "matching_case_grant_count": matching_case_grant_count,
        "matching_audit_event_count": matching_audit_event_count,
        "expected_decision": expected_decision,
        "expected_decision_code": expected_decision_code,
        "expected_match": expected_match,
        "executes_graph_requests": False,
        "executes_graph_writes": False,
    }
    if grant_status:
        payload["grant_status"] = grant_status
    return payload


def _list_fields(snapshot: dict[str, Any], list_name: str) -> list[dict[str, Any]]:
    sharepoint_lists = snapshot.get("sharepoint_lists")
    if not isinstance(sharepoint_lists, dict):
        raise ValueError("matter-access-decision-replay snapshot requires sharepoint_lists")
    items = sharepoint_lists.get(list_name)
    if not isinstance(items, list):
        raise ValueError(f"matter-access-decision-replay snapshot missing list {list_name}")
    fields: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError(f"matter-access-decision-replay list {list_name} entries must be objects")
        item_fields = item.get("fields", item)
        if not isinstance(item_fields, dict):
            raise ValueError(f"matter-access-decision-replay list {list_name} entry fields must be objects")
        fields.append(item_fields)
    return fields


def _case_by_id(cases: list[dict[str, Any]], case_id: str) -> dict[str, Any] | None:
    for case in cases:
        if _text(case.get("NacCaseId")) == case_id:
            return case
    return None


def _workspace_bindings(snapshot: dict[str, Any]) -> dict[str, str]:
    bindings = snapshot.get("workspace_bindings", [])
    if not isinstance(bindings, list):
        raise ValueError("matter-access-decision-replay workspace_bindings must be a list")
    result: dict[str, str] = {}
    for binding in bindings:
        if isinstance(binding, dict) and binding.get("workspace_id") and binding.get("notary_team"):
            result[str(binding["workspace_id"])] = str(binding["notary_team"])
    return result


def _workspace_matches(case: dict[str, Any], workspace_id: str, workspace_bindings: dict[str, str]) -> bool:
    case_workspace = _text(case.get("WorkspaceId"))
    case_notary_team = _text(case.get("NotarTeam"))
    if workspace_id in {case_workspace, case_notary_team}:
        return True
    return bool(case_notary_team and workspace_bindings.get(workspace_id) == case_notary_team)


def _has_blanket_visibility(case: dict[str, Any]) -> bool:
    if case.get("BlanketVisibility") is True:
        return True
    visibility_markers = {
        _text(case.get("VisibilityScope")).lower(),
        _text(case.get("Sichtbarkeit")).lower(),
        _text(case.get("MatterVisibility")).lower(),
    }
    return bool(visibility_markers & {"allstaff", "all_staff", "alle", "blanket", "tenantwide", "teamwide"})


def _user_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {_text(item) for item in value if _text(item)}
    return {_text(value)} if _text(value) else set()


def _required_text(mapping: dict[str, Any], key: str) -> str:
    value = _text(mapping.get(key))
    if not value:
        raise ValueError(f"matter-access-decision-replay request {key} must be non-empty")
    return value


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in ("id", "value", "displayName", "name"):
            if value.get(key):
                return str(value[key])
        return ""
    return str(value)


def _reference_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("matter-access-decision-replay reference_time must include timezone")
        return value.astimezone(UTC)
    return _parse_timestamp(value, "reference_time")


def _optional_timestamp(value: Any) -> datetime | None:
    text = _text(value)
    if not text:
        return None
    try:
        return _parse_timestamp(text, "grant timestamp")
    except ValueError:
        return None


def _parse_timestamp(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"matter-access-decision-replay {field_name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"matter-access-decision-replay {field_name} must include timezone")
    return parsed.astimezone(UTC)


def _checks(decisions: list[dict[str, Any]], errors: list[str]) -> list[dict[str, Any]]:
    decision_codes = {decision["decision_code"] for decision in decisions}
    required_codes = {
        "ALLOW_LEAD_NOTARY",
        "ALLOW_ASSIGNED_CLERK",
        "ALLOW_ACTIVE_DEPUTY_GRANT",
        "BLOCK_WORKSPACE_SCOPE",
        "BLOCK_CASE_SCOPE",
        "BLOCK_DEPUTY_GRANT_EXPIRED",
        "BLOCK_DEPUTY_GRANT_MISSING_REASON",
        "BLOCK_DEPUTY_GRANT_MISSING_APPROVER",
        "BLOCK_DEPUTY_GRANT_MISSING_AUDIT_CORRELATION",
        "BLOCK_BLANKET_VISIBILITY",
    }
    coverage_missing = sorted(required_codes - decision_codes)
    return [
        {
            "id": "decision_expectations",
            "status": "PASSED" if not errors else "FAILED",
            "message": "all synthetic decision expectations matched" if not errors else "; ".join(errors),
            "executesGraphRequests": False,
        },
        {
            "id": "acceptance_code_coverage",
            "status": "PASSED" if not coverage_missing else "FAILED",
            "message": (
                "acceptance decision codes covered"
                if not coverage_missing
                else "missing decision codes: " + ", ".join(coverage_missing)
            ),
            "coveredDecisionCodeCount": len(required_codes - set(coverage_missing)),
            "executesGraphRequests": False,
        },
        {
            "id": "privacy_boundary",
            "status": "PASSED",
            "message": "replay stores hashes, counts, decision codes and privacy flags only",
            "executesGraphRequests": False,
        },
    ]


def _privacy_flags() -> dict[str, bool]:
    return {
        "metadataOnly": True,
        "storesSourceFullText": False,
        "storesRawSharePointItems": False,
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
    }


def _count_by(values: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        bucket = str(value.get(key, ""))
        counts[bucket] = counts.get(bucket, 0) + 1
    return dict(sorted(counts.items()))


def _stable_hash(value: dict[str, Any]) -> str:
    return _hash_value(json.dumps(value, sort_keys=True, ensure_ascii=False))


def _hash_value(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()
