from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any, ContextManager

from nac_mvp_test_environment import BUSINESS_CASE_TYPE_ID

from .test_environment import (
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_DEPUTY_REASON,
    ALLOWED_TENANT_ID,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    AccessDecisionPort,
    AccessMode,
    BpmnAssetPort,
    GraphRestPort,
    ValidatedClaims,
)
from .workbench_projection import (
    ID_PATTERN,
    SENSITIVE_TEXT_PATTERN,
    WorkbenchProjectionError,
    build_workbench_projection,
    serialize_workbench_projection,
    workbench_projection_content_sha256,
)


PRODUCER_VERSION = "1.0.0"
MATTER_TITLE = "Synthetischer Immobilienkaufvertrag"
REDACTION_POLICY_ID = "nac-redaction"
REDACTION_POLICY_VERSION = "v1"
REDACTION_CLASSIFIER_ID = "synthetic-redaction-verifier"
REDACTION_CLASSIFIER_VERSION = "v1"
ALLOWED_ASSIGNED_ROLES = frozenset({"notary", "notary_clerk"})
ALLOWED_DEPUTY_ROLES = frozenset({"deputy_notary", "deputy_clerk"})


@dataclass(frozen=True, slots=True)
class WorkbenchResponse:
    status_code: int
    body: dict[str, Any]
    body_bytes: bytes


class RecursiveRedactionVerifier:
    """Deterministically scan the complete projected value before attesting it."""

    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def __call__(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        _scan_projected_value(payload)
        return {
            "status": "verified",
            "policyId": REDACTION_POLICY_ID,
            "policyVersion": REDACTION_POLICY_VERSION,
            "classifierId": REDACTION_CLASSIFIER_ID,
            "classifierVersion": REDACTION_CLASSIFIER_VERSION,
            "verifiedAt": _wire_timestamp(self._clock()),
            "contentSha256": workbench_projection_content_sha256(payload),
        }


class WorkbenchEndpoint:
    """Read-only live binding for the single allowlisted synthetic matter."""

    def __init__(
        self,
        *,
        expected_tenant_id: str,
        access_decision_port: AccessDecisionPort,
        graph_rest_port: GraphRestPort,
        bpmn_asset_port: BpmnAssetPort,
        clock: Callable[[], datetime] | None = None,
        redaction_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
        request_budget_factory: Callable[[], ContextManager[None]] | None = None,
    ) -> None:
        if not isinstance(expected_tenant_id, str) or not expected_tenant_id.strip():
            raise ValueError("expected_tenant_id is required")
        self._expected_tenant_id = expected_tenant_id
        self._access_decision_port = access_decision_port
        self._graph_rest_port = graph_rest_port
        self._bpmn_asset_port = bpmn_asset_port
        self._clock = clock or (lambda: datetime.now(UTC))
        self._redaction_verifier = redaction_verifier
        self._request_budget_factory = request_budget_factory

    def get_snapshot(
        self,
        *,
        claims: object,
        workspace_id: str,
        matter_id: str,
        purpose: str,
        request_filters: Mapping[str, object] | None = None,
        _budget_bound: bool = False,
    ) -> WorkbenchResponse:
        if not isinstance(claims, ValidatedClaims):
            return _error(401, "AUTHENTICATION_REQUIRED")

        if (
            claims.tenant_id != ALLOWED_TENANT_ID
            or claims.tenant_id != self._expected_tenant_id
            or workspace_id != ALLOWED_WORKSPACE_ID
            or matter_id != ALLOWED_MATTER_ID
            or purpose != ALLOWED_PURPOSE
            or not isinstance(request_filters, (Mapping, type(None)))
            or bool(request_filters)
        ):
            return _error(403, "ACCESS_DENIED")

        if self._request_budget_factory is not None and not _budget_bound:
            try:
                with self._request_budget_factory():
                    return self.get_snapshot(
                        claims=claims,
                        workspace_id=workspace_id,
                        matter_id=matter_id,
                        purpose=purpose,
                        request_filters=request_filters,
                        _budget_bound=True,
                    )
            except Exception:
                return _error(503, "SERVICE_UNAVAILABLE")

        try:
            decision = self._access_decision_port.decide(
                actor_id=claims.object_id,
                tenant_id=claims.tenant_id,
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
                purpose=ALLOWED_PURPOSE,
            )
        except Exception:
            return _error(403, "ACCESS_DENIED")

        try:
            decision_observed_at = _clock_value(self._clock)
        except Exception:
            return _error(503, "SERVICE_UNAVAILABLE")
        access = _validated_access_projection(
            decision,
            claims=claims,
            observed_at=decision_observed_at,
        )
        if access is None:
            return _error(403, "ACCESS_DENIED")

        try:
            raw = self._graph_rest_port.read_synthetic_workspace(
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
            )
            if not isinstance(raw, Mapping):
                raise WorkbenchProjectionError("matter projection is unavailable")
            bpmn = self._bpmn_asset_port.read_canonical_bpmn()
            generated = _clock_value(self._clock)
            generated_at = _wire_timestamp(generated)
            verifier = self._redaction_verifier or RecursiveRedactionVerifier(
                clock=lambda: generated
            )
            payload = build_workbench_projection(
                generated_at=generated_at,
                expires_at=access["expiresAt"],
                producer_version=PRODUCER_VERSION,
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
                purpose=ALLOWED_PURPOSE,
                actor_id=claims.object_id,
                actor_role=access["role"],
                access=access,
                matter=_matter_projection(raw, bpmn),
                tasks=_task_projection(raw),
                attention=[],
                decisions=[],
                evidence=[
                    {
                        "id": "evidence:model:001",
                        "title": "BPMN-Prozessmodell",
                        "kind": "model_reference",
                        "authority": "non_authoritative",
                        "sourceSystem": "nac-git",
                        "sourceRef": bpmn.model_key,
                        "sha256": bpmn.sha256,
                    }
                ],
                capabilities=[],
                agents=[],
                redaction_verifier=verifier,
                observed_at=generated_at,
            )
            return _success(payload)
        except Exception:
            return _error(503, "SERVICE_UNAVAILABLE")


def _validated_access_projection(
    decision: object,
    *,
    claims: ValidatedClaims,
    observed_at: datetime,
) -> dict[str, Any] | None:
    if not isinstance(decision, AccessDecision) or decision.mode not in {
        AccessMode.ASSIGNED,
        AccessMode.DEPUTY,
    }:
        return None
    required = (
        decision.decision_id,
        decision.decision_version,
        decision.subject_id,
        decision.role,
        decision.workspace_id,
        decision.matter_id,
        decision.purpose,
        decision.issued_at,
        decision.expires_at,
    )
    if any(not _identifier(value) for value in required):
        return None
    if (
        decision.subject_id != claims.object_id
        or decision.workspace_id != ALLOWED_WORKSPACE_ID
        or decision.matter_id != ALLOWED_MATTER_ID
        or decision.purpose != ALLOWED_PURPOSE
    ):
        return None
    try:
        issued = _timestamp(decision.issued_at)
        expires = _timestamp(decision.expires_at)
    except ValueError:
        return None
    if (
        issued > observed_at
        or expires <= observed_at
        or expires <= issued
        or (expires - issued).total_seconds() > 300
    ):
        return None
    if decision.mode is AccessMode.ASSIGNED:
        if decision.role not in ALLOWED_ASSIGNED_ROLES or decision.reason is not None:
            return None
    elif (
        decision.role not in ALLOWED_DEPUTY_ROLES
        or decision.reason != ALLOWED_DEPUTY_REASON
        or decision.active_approved_grant is not True
        or decision.matching_audit_event is not True
    ):
        return None
    return {
        "mode": decision.mode.value,
        "decisionId": decision.decision_id,
        "decisionVersion": decision.decision_version,
        "subjectId": decision.subject_id,
        "role": decision.role,
        "workspaceId": decision.workspace_id,
        "matterId": decision.matter_id,
        "purpose": decision.purpose,
        "issuedAt": decision.issued_at,
        "expiresAt": decision.expires_at,
        "reason": decision.reason,
    }


def _matter_projection(raw: Mapping[str, Any], bpmn: Any) -> dict[str, Any]:
    return {
        "id": ALLOWED_MATTER_ID,
        "businessCaseTypeId": BUSINESS_CASE_TYPE_ID,
        "title": MATTER_TITLE,
        "status": raw.get("status"),
        "deadline": raw.get("deadline"),
        "currentStepId": None,
        "modelReference": {
            "kind": "bpmn",
            "modelKey": bpmn.model_key,
            "sha256": bpmn.sha256,
        },
    }


def _task_projection(raw: Mapping[str, Any]) -> list[dict[str, Any]]:
    tasks = raw.get("tasks")
    if not isinstance(tasks, list):
        raise WorkbenchProjectionError("task projection is invalid")
    projected = []
    for task in tasks:
        if not isinstance(task, Mapping):
            raise WorkbenchProjectionError("task projection is invalid")
        projected.append(
            {
                "id": task.get("taskId"),
                "title": task.get("title"),
                "status": task.get("status"),
                "dueAt": task.get("dueAt"),
                "stepId": task.get("stepCode"),
                "requiresApproval": task.get("requiresNotaryApproval"),
            }
        )
    return projected


def _scan_projected_value(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("projection contains invalid Unicode") from exc
        if SENSITIVE_TEXT_PATTERN.search(value):
            raise ValueError("projection contains sensitive text")
        return
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("projection contains a non-string key")
        for key in sorted(value):
            _scan_projected_value(key)
            _scan_projected_value(value[key])
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _scan_projected_value(item)
        return
    raise ValueError("projection contains an unsupported value")


def _identifier(value: object) -> bool:
    return (
        isinstance(value, str)
        and ID_PATTERN.fullmatch(value) is not None
        and SENSITIVE_TEXT_PATTERN.search(value) is None
    )


def _display_text(value: object) -> bool:
    if (
        not isinstance(value, str)
        or not value.strip()
        or SENSITIVE_TEXT_PATTERN.search(value)
    ):
        return False
    try:
        return len(value.encode("utf-16-le")) // 2 <= 256
    except UnicodeEncodeError:
        return False


def _clock_value(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("workbench clock is invalid")
    return value.astimezone(UTC).replace(microsecond=0)


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("timestamp is invalid") from None
    if (
        parsed.tzinfo is None
        or parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value
    ):
        raise ValueError("timestamp is invalid")
    return parsed.astimezone(UTC)


def _wire_timestamp(value: datetime) -> str:
    normalized = _clock_value(lambda: value)
    return normalized.isoformat().replace("+00:00", "Z")


def _success(payload: dict[str, Any]) -> WorkbenchResponse:
    body_bytes = serialize_workbench_projection(payload).encode("utf-8")
    return WorkbenchResponse(status_code=200, body=payload, body_bytes=body_bytes)


def _error(status: int, code: str) -> WorkbenchResponse:
    body = {"status": status, "error": {"code": code}}
    body_bytes = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return WorkbenchResponse(status_code=status, body=body, body_bytes=body_bytes)
