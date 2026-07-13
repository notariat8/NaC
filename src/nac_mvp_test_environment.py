from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping


WORKSPACE_ID = "notary_team_01"
MATTER_ID = "NAC-SYN-MATTER-001"
PURPOSE = "view_synthetic_matter_workspace"
BUSINESS_CASE_TYPE_ID = "immobilienkaufvertrag"
MATTER_STATUS = "Entwurf"
DEADLINE = "2026-08-31T16:00:00Z"
POLICY_REFERENCE_TIME = "2026-07-13T12:00:00Z"

TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "NAC-SYN-TASK-001",
        "title": "Vertragsentwurf prüfen",
        "step_code": "synthetic_contract_review",
        "status": "Offen",
        "requires_notary_approval": True,
        "due_at": None,
    },
    {
        "task_id": "NAC-SYN-DEADLINE-001",
        "title": "Abschlussfrist überwachen",
        "step_code": "synthetic_completion_deadline",
        "status": "Offen",
        "requires_notary_approval": False,
        "due_at": DEADLINE,
    },
)

BPMN_PROCESS_KEY = "NAC_SYN_MATTER_001"
BPMN_XML = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
  id="Definitions_NacSyntheticMatter"
  targetNamespace="https://notariat8.de/nac/synthetic">
  <bpmn:process id="NAC_SYN_MATTER_001" isExecutable="false">
    <bpmn:startEvent id="StartEvent_Synthetic"/>
    <bpmn:userTask id="synthetic_contract_review" name="Vertragsentwurf prüfen"/>
    <bpmn:userTask id="synthetic_completion_deadline" name="Abschlussfrist überwachen"/>
    <bpmn:endEvent id="EndEvent_Synthetic"/>
    <bpmn:sequenceFlow id="Flow_Start_Review" sourceRef="StartEvent_Synthetic" targetRef="synthetic_contract_review"/>
    <bpmn:sequenceFlow id="Flow_Review_Deadline" sourceRef="synthetic_contract_review" targetRef="synthetic_completion_deadline"/>
    <bpmn:sequenceFlow id="Flow_Deadline_End" sourceRef="synthetic_completion_deadline" targetRef="EndEvent_Synthetic"/>
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_NacSyntheticMatter">
    <bpmndi:BPMNPlane id="BPMNPlane_NacSyntheticMatter" bpmnElement="NAC_SYN_MATTER_001">
      <bpmndi:BPMNShape id="StartEvent_Synthetic_di" bpmnElement="StartEvent_Synthetic">
        <dc:Bounds x="120" y="122" width="36" height="36"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="synthetic_contract_review_di" bpmnElement="synthetic_contract_review">
        <dc:Bounds x="220" y="100" width="140" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="synthetic_completion_deadline_di" bpmnElement="synthetic_completion_deadline">
        <dc:Bounds x="430" y="100" width="150" height="80"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Synthetic_di" bpmnElement="EndEvent_Synthetic">
        <dc:Bounds x="650" y="122" width="36" height="36"/>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_Start_Review_di" bpmnElement="Flow_Start_Review">
        <di:waypoint x="156" y="140"/>
        <di:waypoint x="220" y="140"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Review_Deadline_di" bpmnElement="Flow_Review_Deadline">
        <di:waypoint x="360" y="140"/>
        <di:waypoint x="430" y="140"/>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Deadline_End_di" bpmnElement="Flow_Deadline_End">
        <di:waypoint x="580" y="140"/>
        <di:waypoint x="650" y="140"/>
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>"""
BPMN_SHA256 = sha256(BPMN_XML.encode("utf-8")).hexdigest()

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
