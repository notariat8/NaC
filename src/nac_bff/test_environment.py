from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from typing import Any, Mapping, Protocol


ALLOWED_WORKSPACE_ID = "notary_team_01"
ALLOWED_MATTER_ID = "NAC-SYN-MATTER-001"
ALLOWED_PURPOSE = "view_synthetic_matter_workspace"

_BUSINESS_CASE_TYPE_ID = "immobilienkaufvertrag"
_MATTER_DISPLAY_NAME = "Synthetische IKV-Testakte"
_MODEL_KEY = "immobilienkaufvertrag"
_SCHEMA_VERSION = "nac.m365-test-environment-workspace/v0.1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_MATTER_STATUSES = frozenset(
    {"draft", "open", "in_review", "ready_for_signature", "completed"}
)
_ALLOWED_TASK_STATUSES = frozenset({"planned", "open", "in_progress", "completed"})


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
    ) -> None:
        if not isinstance(expected_tenant_id, str) or not expected_tenant_id.strip():
            raise ValueError("expected_tenant_id is required")
        self._expected_tenant_id = expected_tenant_id
        self._access_decision_port = access_decision_port
        self._graph_rest_port = graph_rest_port

    def get_workspace(
        self,
        *,
        claims: object,
        workspace_id: str,
        matter_id: str,
        purpose: str,
    ) -> BffResponse:
        if not isinstance(claims, ValidatedClaims):
            return _error(401, "authentication required")

        # Scope checks precede access and data ports so manipulated identifiers
        # cannot be used for probing or arbitrary Graph path construction.
        if (
            workspace_id != ALLOWED_WORKSPACE_ID
            or matter_id != ALLOWED_MATTER_ID
            or purpose != ALLOWED_PURPOSE
        ):
            return _error(404, "resource not found")
        if claims.tenant_id != self._expected_tenant_id:
            return _error(403, "access denied")

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

    status = _bounded_string(raw.get("status"), field="status", maximum=40)
    if status not in _ALLOWED_MATTER_STATUSES:
        raise _ProjectionError("unsupported matter status")

    deadline = _bounded_string(raw.get("deadline"), field="deadline", maximum=10)
    try:
        date.fromisoformat(deadline)
    except ValueError as exc:
        raise _ProjectionError("deadline must be an ISO date") from exc

    tasks_value = raw.get("tasks")
    if not isinstance(tasks_value, list) or len(tasks_value) > 20:
        raise _ProjectionError("tasks must be a bounded list")
    tasks: list[dict[str, str]] = []
    for task in tasks_value:
        if not isinstance(task, Mapping):
            raise _ProjectionError("task must be an object")
        title = _bounded_string(task.get("title"), field="task.title", maximum=160)
        task_status = _bounded_string(task.get("status"), field="task.status", maximum=40)
        if task_status not in _ALLOWED_TASK_STATUSES:
            raise _ProjectionError("unsupported task status")
        tasks.append({"title": title, "status": task_status})

    bpmn_value = raw.get("bpmn")
    if not isinstance(bpmn_value, Mapping):
        raise _ProjectionError("bpmn must be an object")
    model_key = _bounded_string(bpmn_value.get("modelKey"), field="bpmn.modelKey", maximum=80)
    if model_key != _MODEL_KEY:
        raise _ProjectionError("unexpected BPMN model key")
    sha256 = _bounded_string(bpmn_value.get("sha256"), field="bpmn.sha256", maximum=64)
    if not _SHA256_RE.fullmatch(sha256):
        raise _ProjectionError("invalid BPMN SHA-256")

    # This explicit shape is the redaction boundary. No raw Graph IDs, fields,
    # download URLs, user identifiers or token-adjacent values are copied.
    return {
        "schemaVersion": _SCHEMA_VERSION,
        "workspaceId": ALLOWED_WORKSPACE_ID,
        "matter": {
            "matterId": ALLOWED_MATTER_ID,
            "businessCaseTypeId": _BUSINESS_CASE_TYPE_ID,
            "displayName": _MATTER_DISPLAY_NAME,
            "status": status,
            "deadline": deadline,
            "tasks": tasks,
            "bpmn": {"modelKey": model_key, "sha256": sha256},
            "accessMode": access_mode,
        },
    }


def _bounded_string(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise _ProjectionError(f"{field} must be a bounded string")
    if any(ord(character) < 32 for character in value):
        raise _ProjectionError(f"{field} contains control characters")
    return value


def _error(status_code: int, detail: str) -> BffResponse:
    return BffResponse(status_code=status_code, body={"detail": detail})
