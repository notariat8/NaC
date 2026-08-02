from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Mapping

from nac_bff.synthetic_workspace_graph import (
    GraphGetClient,
    read_bounded_collection,
    synthetic_list_binding,
)
from nac_bff.test_environment import (
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_DEPUTY_REASON,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
)


SYNTHETIC_NOTARY_TEAM = "NaC-Notar-01"
ALLOWED_DEPUTY_ROLES = frozenset({"NotarVertretung", "SachbearbeitungVertretung"})
WORKBENCH_DEPUTY_ROLES = {
    "NotarVertretung": "deputy_notary",
    "SachbearbeitungVertretung": "deputy_clerk",
}
APPROVAL_ACTIONS = frozenset({"GrantApproved", "DeputyGrantApproved"})
ACCESS_DECISION_ID = f"access:{ALLOWED_MATTER_ID}:1"
ACCESS_DECISION_VERSION = "policy-v1"
MAX_ACCESS_LEASE_SECONDS = 300


class LiveAccessDecisionAdapter:
    """Fail-closed AccessDecisionPort backed by fixed synthetic Graph lists."""

    def __init__(
        self,
        client: GraphGetClient,
        *,
        expected_tenant_id: str,
        reference_time: str | datetime | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(expected_tenant_id, str) or not expected_tenant_id.strip():
            raise ValueError("expected_tenant_id is required")
        if reference_time is not None and clock is not None:
            raise ValueError("reference_time and clock are mutually exclusive")
        self._client = client
        self._expected_tenant_id = expected_tenant_id
        self._reference_time = reference_time
        self._clock = clock or (lambda: datetime.now(UTC))

    def decide(
        self,
        *,
        actor_id: str,
        tenant_id: str,
        workspace_id: str,
        matter_id: str,
        purpose: str,
    ) -> AccessDecision:
        try:
            return self._decide(
                actor_id=actor_id,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                matter_id=matter_id,
                purpose=purpose,
            )
        except Exception:
            # Authentication, lookup, parsing and policy failures intentionally
            # collapse to one result so callers cannot infer matter existence.
            return AccessDecision.deny()

    def _decide(
        self,
        *,
        actor_id: object,
        tenant_id: object,
        workspace_id: object,
        matter_id: object,
        purpose: object,
    ) -> AccessDecision:
        if (
            type(actor_id) is not str
            or not actor_id
            or len(actor_id) > 256
            or tenant_id != self._expected_tenant_id
            or workspace_id != ALLOWED_WORKSPACE_ID
            or matter_id != ALLOWED_MATTER_ID
            or purpose != ALLOWED_PURPOSE
        ):
            return AccessDecision.deny()

        cases = read_bounded_collection(
            self._client,
            binding=synthetic_list_binding("Akten"),
            fields=(
                "NacCaseId",
                "NotarTeam",
                "FederfuehrenderNotar",
                "Sachbearbeitung",
            ),
            filter_expression=_equals("NacCaseId", ALLOWED_MATTER_ID),
            top=2,
            max_items=2,
        )
        if len(cases) != 1:
            return AccessDecision.deny()
        case = cases[0]
        if (
            case.get("NacCaseId") != ALLOWED_MATTER_ID
            or case.get("NotarTeam") != SYNTHETIC_NOTARY_TEAM
        ):
            return AccessDecision.deny()

        notaries = _user_ids(case.get("FederfuehrenderNotar"), allow_multiple=False)
        clerks = _user_ids(case.get("Sachbearbeitung"), allow_multiple=True)
        if len(notaries) != 1:
            return AccessDecision.deny()
        lead_notary = next(iter(notaries))
        reference = _reference_time(self)
        if actor_id == lead_notary:
            return _allowed_decision(
                mode="assigned",
                actor_id=actor_id,
                role="notary",
                reference=reference,
            )
        if actor_id in clerks:
            return _allowed_decision(
                mode="assigned",
                actor_id=actor_id,
                role="notary_clerk",
                reference=reference,
            )

        grants = read_bounded_collection(
            self._client,
            binding=synthetic_list_binding("Vertretungsfreigaben"),
            fields=(
                "GrantId",
                "NacCaseId",
                "FromUser",
                "ToUser",
                "GrantedRole",
                "Reason",
                "ValidFrom",
                "ValidUntil",
                "ApprovedBy",
                "Status",
                "AuditCorrelationId",
            ),
            filter_expression=_equals("NacCaseId", ALLOWED_MATTER_ID),
            top=8,
            max_items=8,
        )
        matching = [grant for grant in grants if _single_user_id(grant.get("ToUser")) == actor_id]
        if len(matching) != 1:
            return AccessDecision.deny()
        grant = matching[0]
        if not _valid_grant(grant, lead_notary=lead_notary, reference=reference):
            return AccessDecision.deny()

        correlation_id = _text(grant.get("AuditCorrelationId"))
        audits = read_bounded_collection(
            self._client,
            binding=synthetic_list_binding("AuditJournalLite"),
            fields=("NacCaseId", "Action", "ObjectId", "CorrelationId"),
            filter_expression=(
                f"{_equals('NacCaseId', ALLOWED_MATTER_ID)} and "
                f"{_equals('CorrelationId', correlation_id)}"
            ),
            top=2,
            max_items=2,
        )
        if len(audits) != 1 or not _valid_audit(audits[0], grant):
            return AccessDecision.deny()
        return _allowed_decision(
            mode="deputy",
            actor_id=actor_id,
            role=WORKBENCH_DEPUTY_ROLES[_text(grant.get("GrantedRole"))],
            reference=reference,
            maximum_expiry=_timestamp(grant.get("ValidUntil")),
            reason=_text(grant.get("Reason")),
            active_approved_grant=True,
            matching_audit_event=True,
        )


# Stable descriptive aliases for dependency-injection composition roots.
LiveAccessDecisionPortAdapter = LiveAccessDecisionAdapter
GraphAccessDecisionPortAdapter = LiveAccessDecisionAdapter


def _allowed_decision(
    *,
    mode: str,
    actor_id: str,
    role: str,
    reference: datetime,
    maximum_expiry: datetime | None = None,
    reason: str | None = None,
    active_approved_grant: bool = False,
    matching_audit_event: bool = False,
) -> AccessDecision:
    expires = reference + timedelta(seconds=MAX_ACCESS_LEASE_SECONDS)
    if maximum_expiry is not None:
        expires = min(expires, maximum_expiry)
    metadata = {
        "decision_id": ACCESS_DECISION_ID,
        "decision_version": ACCESS_DECISION_VERSION,
        "subject_id": actor_id,
        "role": role,
        "workspace_id": ALLOWED_WORKSPACE_ID,
        "matter_id": ALLOWED_MATTER_ID,
        "purpose": ALLOWED_PURPOSE,
        "issued_at": _wire_timestamp(reference),
        "expires_at": _wire_timestamp(expires),
        "reason": reason,
        "active_approved_grant": active_approved_grant,
        "matching_audit_event": matching_audit_event,
    }
    if mode == "assigned":
        return AccessDecision.assigned(**metadata)
    return AccessDecision.deputy(**metadata)


def _valid_grant(grant: Mapping[str, Any], *, lead_notary: str, reference: datetime) -> bool:
    try:
        valid_from = _timestamp(grant.get("ValidFrom"))
        valid_until = _timestamp(grant.get("ValidUntil"))
    except (TypeError, ValueError):
        return False
    return (
        grant.get("NacCaseId") == ALLOWED_MATTER_ID
        and _text(grant.get("GrantId")) != ""
        and _single_user_id(grant.get("FromUser")) == lead_notary
        and _text(grant.get("GrantedRole")) in ALLOWED_DEPUTY_ROLES
        and _text(grant.get("Reason")) == ALLOWED_DEPUTY_REASON
        and valid_from < valid_until
        and valid_from <= reference < valid_until
        and _single_user_id(grant.get("ApprovedBy")) == lead_notary
        and grant.get("Status") == "Aktiv"
        and _text(grant.get("AuditCorrelationId")) != ""
    )


def _valid_audit(audit: Mapping[str, Any], grant: Mapping[str, Any]) -> bool:
    return (
        audit.get("NacCaseId") == ALLOWED_MATTER_ID
        and audit.get("Action") in APPROVAL_ACTIONS
        and audit.get("ObjectId") == grant.get("GrantId")
        and audit.get("CorrelationId") == grant.get("AuditCorrelationId")
    )


def _reference_time(adapter: LiveAccessDecisionAdapter) -> datetime:
    value = adapter._reference_time if adapter._reference_time is not None else adapter._clock()
    return _timestamp(value)


def _timestamp(value: object) -> datetime:
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


def _wire_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _user_ids(value: object, *, allow_multiple: bool) -> frozenset[str]:
    if isinstance(value, str):
        text = value.strip()
        return frozenset({text}) if text else frozenset()
    if allow_multiple and type(value) is list:
        if any(not isinstance(item, str) or not item.strip() for item in value):
            return frozenset()
        normalized = [item.strip() for item in value]
        if len(set(normalized)) != len(normalized):
            return frozenset()
        return frozenset(normalized)
    return frozenset()


def _single_user_id(value: object) -> str:
    values = _user_ids(value, allow_multiple=False)
    return next(iter(values)) if len(values) == 1 else ""


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _equals(field: str, value: str) -> str:
    escaped = value.replace("'", "''")
    return f"fields/{field} eq '{escaped}'"
