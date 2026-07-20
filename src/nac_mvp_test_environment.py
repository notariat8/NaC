from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Mapping

WORKSPACE_ID = "notary_team_01"
MATTER_ID = "NAC-SYN-MATTER-001"
PURPOSE = "view_synthetic_matter_workspace"
BUSINESS_CASE_TYPE_ID = "immobilienkaufvertrag"
MATTER_STATUS = "Entwurf"
DEADLINE = "2026-08-31T16:00:00Z"
POLICY_REFERENCE_TIME = "2026-07-13T12:00:00Z"
WORKFLOW_VERSION = "mvp-test-environment-v0.1"
BPMN_PROFILE_VERSION = "nac-bpmn/v0.1"
BPMN_SOURCE_PATH = "bpmn/immobilienkaufvertrag.bpmn"
BPMN_PROCESS_KEY = "Process_immobilienkaufvertrag"
BPMN_SHA256 = "02cc15850e7e828189214a75ad3edfa3a2e704d5a766b3aa2237f2445040dfa0"
KG_SOURCE_PATH = "usecases/immobilienkaufvertrag/knowledge-graph.graph.json"
KG_GRAPH_ID = "usecase.immobilienkaufvertrag"
KG_SCHEMA_VERSION = "nac.knowledge-graph/v0.1"
KG_SHA256 = "3bd379066a3c9656046e930efca8d3c7690cdcbe5a7279f7aec12109e777e019"

TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "NAC-SYN-TASK-001",
        "title": "Vertragsentwurf prüfen",
        "step_code": "Task_EntwurfAbstimmen",
        "status": "Offen",
        "requires_notary_approval": True,
        "due_at": None,
    },
    {
        "task_id": "NAC-SYN-DEADLINE-001",
        "title": "Abschlussfrist überwachen",
        "step_code": "Task_NachweiseNachhalten",
        "status": "Offen",
        "requires_notary_approval": False,
        "due_at": DEADLINE,
    },
)

SYNTHETIC_POLICY_STATE: dict[str, Any] = {
    "matter": {
        "workspace_id": WORKSPACE_ID,
        "matter_id": MATTER_ID,
        "assigned_actor_ids": ["nac-synthetic-assigned"],
        "blanket_visibility": False,
    },
    "deputy_grants": [
        {
            "matter_id": MATTER_ID,
            "actor_id": "nac-synthetic-deputy",
            "role": "SachbearbeitungVertretung",
            "status": "Aktiv",
            "reason": "Synthetische Urlaubsvertretung",
            "valid_from": "2026-07-13T08:00:00Z",
            "valid_until": "2026-07-14T18:00:00Z",
            "approved_by": "nac-synthetic-notary",
            "approval_status": "approved",
            "audit_correlation_id": "NAC-SYN-AUDIT-DEPUTY-001",
        }
    ],
    "audit_events": [
        {
            "correlation_id": "NAC-SYN-AUDIT-DEPUTY-001",
            "matter_id": MATTER_ID,
            "action": "DeputyGrantApproved",
        }
    ],
}


def evaluate_synthetic_access_policy(
    request: Mapping[str, Any],
    *,
    policy_state: Mapping[str, Any] = SYNTHETIC_POLICY_STATE,
    reference_time: str | datetime = POLICY_REFERENCE_TIME,
) -> dict[str, str]:
    """Evaluate the synthetic assignment/deputy policy from data, fail closed."""

    try:
        actor_id = _required_text(request, "actor_id")
        workspace_id = _required_text(request, "workspace_id")
        matter_id = _required_text(request, "case_id")
        purpose = _required_text(request, "purpose")
        reference = _timestamp(reference_time)
        matter = policy_state.get("matter")
        if not isinstance(matter, Mapping):
            return _deny("DENY_POLICY_STATE_INVALID")
        if purpose not in {PURPOSE, "m365_mvp_test_environment_smoke"}:
            return _deny("DENY_PURPOSE_SCOPE")
        if workspace_id != WORKSPACE_ID or matter.get("workspace_id") != WORKSPACE_ID:
            return _deny("DENY_WORKSPACE_SCOPE")
        if matter_id != MATTER_ID or matter.get("matter_id") != MATTER_ID:
            return _deny("DENY_MATTER_SCOPE")
        if matter.get("blanket_visibility") is not False:
            return _deny("DENY_BLANKET_VISIBILITY")

        assignments = matter.get("assigned_actor_ids")
        if isinstance(assignments, list) and actor_id in assignments:
            return {"decision": "ALLOW", "code": "ALLOW_ASSIGNED_USER", "mode": "assigned"}

        grants = policy_state.get("deputy_grants")
        audits = policy_state.get("audit_events")
        if not isinstance(grants, list) or not isinstance(audits, list):
            return _deny("DENY_POLICY_STATE_INVALID")
        matching = [
            grant
            for grant in grants
            if isinstance(grant, Mapping)
            and grant.get("actor_id") == actor_id
            and grant.get("matter_id") == MATTER_ID
        ]
        if not matching:
            return _deny("DENY_NO_ASSIGNMENT_OR_DEPUTY_GRANT")
        if len(matching) != 1:
            return _deny("DENY_AMBIGUOUS_DEPUTY_GRANT")
        grant = matching[0]
        if grant.get("status") != "Aktiv":
            return _deny("DENY_DEPUTY_GRANT_INACTIVE")
        if grant.get("role") not in {"NotarVertretung", "SachbearbeitungVertretung", "NurLesen"}:
            return _deny("DENY_DEPUTY_ROLE")
        if not _text(grant.get("reason")):
            return _deny("DENY_DEPUTY_REASON")
        valid_from = _timestamp(grant.get("valid_from"))
        valid_until = _timestamp(grant.get("valid_until"))
        if valid_until <= valid_from or reference < valid_from or reference >= valid_until:
            return _deny("DENY_DEPUTY_DURATION")
        if not _text(grant.get("approved_by")) or grant.get("approval_status") != "approved":
            return _deny("DENY_DEPUTY_APPROVAL")
        audit_ref = _text(grant.get("audit_correlation_id"))
        if not audit_ref:
            return _deny("DENY_DEPUTY_AUDIT")
        audit_matches = [
            event
            for event in audits
            if isinstance(event, Mapping)
            and event.get("correlation_id") == audit_ref
            and event.get("matter_id") == MATTER_ID
            and event.get("action") == "DeputyGrantApproved"
        ]
        if len(audit_matches) != 1:
            return _deny("DENY_DEPUTY_AUDIT")
        return {"decision": "ALLOW", "code": "ALLOW_ACTIVE_DEPUTY_GRANT", "mode": "deputy"}
    except (TypeError, ValueError):
        return _deny("DENY_POLICY_INPUT_INVALID")


def _deny(code: str) -> dict[str, str]:
    return {"decision": "DENY", "code": code, "mode": "deny"}


def _required_text(mapping: Mapping[str, Any], key: str) -> str:
    value = _text(mapping.get(key))
    if not value:
        raise ValueError(f"{key} is required")
    return value


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError("timestamp requires timezone")
        return value.astimezone(UTC)
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires timezone")
    return parsed.astimezone(UTC)
