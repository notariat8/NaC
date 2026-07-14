from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, ContextManager, Mapping, Protocol

from nac_mvp_test_environment import (
    BPMN_PROCESS_KEY,
    BPMN_SHA256,
    BUSINESS_CASE_TYPE_ID,
    DEADLINE,
    MATTER_ID,
    MATTER_STATUS,
    POLICY_REFERENCE_TIME,
    PURPOSE,
    SYNTHETIC_POLICY_STATE,
    TASKS,
    WORKSPACE_ID,
    evaluate_synthetic_access_policy,
)


ALLOWED_WORKSPACE_ID = WORKSPACE_ID
ALLOWED_MATTER_ID = MATTER_ID
ALLOWED_PURPOSE = PURPOSE
_MATTER_DISPLAY_NAME = "Synthetische IKV-Testakte"
_SCHEMA_VERSION = "nac.m365-test-environment-workspace/v0.1"


class AccessMode(str, Enum):
    ASSIGNED = "assigned"
    DEPUTY = "deputy"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class AccessDecision:
    """Result returned by the server-side role/case/deputy decision port."""

    mode: AccessMode

    @classmethod
    def assigned(cls) -> AccessDecision:
        return cls(AccessMode.ASSIGNED)

    @classmethod
    def deputy(cls) -> AccessDecision:
        return cls(AccessMode.DEPUTY)

    @classmethod
    def deny(cls) -> AccessDecision:
        return cls(AccessMode.DENY)


@dataclass(frozen=True, slots=True)
class ValidatedClaims:
    """Minimal identity claims produced only after Entra token validation.

    The FastAPI boundary accepts this type from an injected authentication
    dependency. Request bodies, query strings and browser-supplied role data are
    never converted to this type by the BFF.
    """

    object_id: str
    tenant_id: str
    subject: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("object_id", self.object_id),
            ("tenant_id", self.tenant_id),
            ("subject", self.subject),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f"validated claim {field_name} is invalid")


class AccessDecisionPort(Protocol):
    def decide(
        self,
        *,
        actor_id: str,
        tenant_id: str,
        workspace_id: str,
        matter_id: str,
        purpose: str,
    ) -> AccessDecision:
        ...


class DeterministicSyntheticAccessDecisionPort:
    """BFF policy port backed by the canonical fail-closed synthetic policy."""

    def __init__(
        self,
        *,
        policy_state: Mapping[str, Any] = SYNTHETIC_POLICY_STATE,
        reference_time: str = POLICY_REFERENCE_TIME,
    ) -> None:
        self._policy_state = policy_state
        self._reference_time = reference_time

    def decide(
        self,
        *,
        actor_id: str,
        tenant_id: str,
        workspace_id: str,
        matter_id: str,
        purpose: str,
    ) -> AccessDecision:
        del tenant_id
        result = evaluate_synthetic_access_policy(
            {
                "actor_id": actor_id,
                "workspace_id": workspace_id,
                "case_id": matter_id,
                "purpose": purpose,
            },
            policy_state=self._policy_state,
            reference_time=self._reference_time,
        )
        if result.get("decision") != "ALLOW":
            return AccessDecision.deny()
        if result.get("mode") == "assigned":
            return AccessDecision.assigned()
        if result.get("mode") == "deputy":
            return AccessDecision.deputy()
        return AccessDecision.deny()


class GraphRestPort(Protocol):
    """Read-only, raw Microsoft Graph REST v1.0 data port.

    The concrete adapter owns token acquisition and fixed Graph paths. The
    browser cannot provide Graph URLs, OData clauses, site IDs or list IDs.
    """

    def read_synthetic_workspace(
        self,
        *,
        workspace_id: str,
        matter_id: str,
    ) -> Mapping[str, Any] | None:
        ...


@dataclass(frozen=True, slots=True)
class BffResponse:
    status_code: int
    body: dict[str, Any]


class _ProjectionError(ValueError):
    pass


class TestEnvironmentBff:
    """Narrow read boundary for the single synthetic M365 test matter."""

    __test__ = False

    def __init__(
        self,
        *,
        expected_tenant_id: str,
        access_decision_port: AccessDecisionPort,
        graph_rest_port: GraphRestPort,
        request_budget_factory: Callable[[], ContextManager[None]] | None = None,
    ) -> None:
        if not isinstance(expected_tenant_id, str) or not expected_tenant_id.strip():
            raise ValueError("expected_tenant_id is required")
        self._expected_tenant_id = expected_tenant_id
        self._access_decision_port = access_decision_port
        self._graph_rest_port = graph_rest_port
        self._request_budget_factory = request_budget_factory

    def get_workspace(
        self,
        *,
        claims: object,
        workspace_id: str,
        matter_id: str,
        purpose: str,
        request_filters: Mapping[str, object] | None = None,
        _budget_bound: bool = False,
    ) -> BffResponse:
        if not isinstance(claims, ValidatedClaims):
            return _error(401, "authentication required")

        # Scope checks precede access and data ports so manipulated identifiers
        # cannot be used for probing or arbitrary Graph path construction. All
        # authenticated, unauthorized request shapes deliberately share the
        # same external response so matter existence cannot be inferred.
        if (
            workspace_id != ALLOWED_WORKSPACE_ID
            or matter_id != ALLOWED_MATTER_ID
            or purpose != ALLOWED_PURPOSE
            or not isinstance(request_filters, (Mapping, type(None)))
            or bool(request_filters)
        ):
            return _error(403, "access denied")
        if claims.tenant_id != self._expected_tenant_id:
            return _error(403, "access denied")
        if self._request_budget_factory is not None and not _budget_bound:
            try:
                with self._request_budget_factory():
                    return self.get_workspace(
                        claims=claims,
                        workspace_id=workspace_id,
                        matter_id=matter_id,
                        purpose=purpose,
                        request_filters=request_filters,
                        _budget_bound=True,
                    )
            except Exception:
                return _error(503, "service unavailable")

        try:
            decision = self._access_decision_port.decide(
                actor_id=claims.object_id,
                tenant_id=claims.tenant_id,
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
                purpose=ALLOWED_PURPOSE,
            )
        except Exception:
            return _error(403, "access denied")

        if not isinstance(decision, AccessDecision) or decision.mode is AccessMode.DENY:
            return _error(403, "access denied")
        if decision.mode not in {AccessMode.ASSIGNED, AccessMode.DEPUTY}:
            return _error(403, "access denied")

        try:
            raw_projection = self._graph_rest_port.read_synthetic_workspace(
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
            )
        except Exception:
            return _error(503, "service unavailable")

        if not raw_projection:
            return _error(404, "resource not found")
        try:
            dto = _build_redacted_dto(raw_projection, access_mode=decision.mode.value)
        except _ProjectionError:
            return _error(503, "service unavailable")
        return BffResponse(status_code=200, body=dto)


def _build_redacted_dto(raw: Mapping[str, Any], *, access_mode: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise _ProjectionError("projection must be an object")
    if raw.get("status") != MATTER_STATUS or raw.get("deadline") != DEADLINE:
        raise _ProjectionError("synthetic matter projection diverged")

    tasks_value = raw.get("tasks")
    if not isinstance(tasks_value, list) or len(tasks_value) != len(TASKS):
        raise _ProjectionError("synthetic tasks diverged")
    tasks_by_id = {task.get("taskId"): task for task in tasks_value if isinstance(task, Mapping)}
    if len(tasks_by_id) != len(TASKS):
        raise _ProjectionError("synthetic task IDs diverged")
    tasks: list[dict[str, Any]] = []
    for expected in TASKS:
        task = tasks_by_id.get(expected["task_id"])
        if not isinstance(task, Mapping):
            raise _ProjectionError("synthetic task missing")
        canonical = {
            "taskId": expected["task_id"],
            "title": expected["title"],
            "stepCode": expected["step_code"],
            "status": expected["status"],
            "requiresNotaryApproval": expected["requires_notary_approval"],
            "dueAt": expected["due_at"],
        }
        if any(task.get(key) != value for key, value in canonical.items()):
            raise _ProjectionError("synthetic task projection diverged")
        tasks.append(canonical)

    bpmn_value = raw.get("bpmn")
    if (
        not isinstance(bpmn_value, Mapping)
        or bpmn_value.get("modelKey") != BPMN_PROCESS_KEY
        or bpmn_value.get("sha256") != BPMN_SHA256
    ):
        raise _ProjectionError("synthetic BPMN projection diverged")

    return {
        "schemaVersion": _SCHEMA_VERSION,
        "workspaceId": ALLOWED_WORKSPACE_ID,
        "matter": {
            "matterId": ALLOWED_MATTER_ID,
            "businessCaseTypeId": BUSINESS_CASE_TYPE_ID,
            "displayName": _MATTER_DISPLAY_NAME,
            "status": MATTER_STATUS,
            "deadline": DEADLINE,
            "tasks": tasks,
            "bpmn": {"modelKey": BPMN_PROCESS_KEY, "sha256": BPMN_SHA256},
            "accessMode": access_mode,
        },
    }


def _error(status_code: int, detail: str) -> BffResponse:
    return BffResponse(status_code=status_code, body={"detail": detail})
