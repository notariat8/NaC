from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = "nac.workbench.snapshot/v1"
PRODUCER_ID = "nac-bff"
MAX_LEASE_SECONDS = 300
MAX_ITEMS = 64
MAX_TEXT = 256
MAX_SNAPSHOT_BYTES = 128 * 1024
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
SENSITIVE_TEXT_PATTERN = re.compile(
    r"(?:https?://|Bearer\s+|(?:access_token|refresh_token|id_token|client_secret|authorization_code|sig|sv|se|sp|spr)="
    r"|(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}"
    r"|eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}"
    r"|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})",
    re.IGNORECASE,
)


class WorkbenchProjectionError(ValueError):
    pass


def build_workbench_projection(
    *,
    generated_at: str,
    expires_at: str,
    producer_version: str,
    workspace_id: str,
    matter_id: str,
    purpose: str,
    actor_id: str,
    actor_role: str,
    access: Mapping[str, Any],
    matter: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    attention: Sequence[Mapping[str, Any]],
    decisions: Sequence[Mapping[str, Any]],
    evidence: Sequence[Mapping[str, Any]],
    capabilities: Sequence[Mapping[str, Any]],
    agents: Sequence[Mapping[str, Any]],
    redaction_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Build an allowlisted, short-lived DTO from authoritative server ports."""

    observed = _timestamp(observed_at) if observed_at is not None else datetime.now(timezone.utc)
    generated = _timestamp(generated_at)
    expires = _timestamp(expires_at)
    if generated > observed or expires <= observed:
        raise WorkbenchProjectionError("projection is not currently valid")
    if expires <= generated or (expires - generated).total_seconds() > MAX_LEASE_SECONDS:
        raise WorkbenchProjectionError("projection lease is invalid")

    payload: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": generated_at,
        "expiresAt": expires_at,
        "producer": {"id": PRODUCER_ID, "version": _id(producer_version, "producer.version")},
        "scope": {
            "workspaceId": _id(workspace_id, "scope.workspaceId"),
            "matterId": _id(matter_id, "scope.matterId"),
            "purpose": _id(purpose, "scope.purpose"),
        },
        "access": _project_access(
            access,
            generated,
            expires,
            observed,
            workspace_id=workspace_id,
            matter_id=matter_id,
            purpose=purpose,
            actor_id=actor_id,
            actor_role=actor_role,
        ),
        "matter": _project_matter(matter),
        "tasks": _project_collection(tasks, "tasks", _project_task),
        "attention": _project_collection(attention, "attention", _project_attention),
        "decisions": _project_collection(decisions, "decisions", _project_decision),
        "evidence": _project_collection(evidence, "evidence", _project_evidence),
        "capabilities": _project_collection(capabilities, "capabilities", _project_capability),
        "agents": _project_collection(agents, "agents", _project_agent),
    }
    _validate_references(payload)
    content_sha256 = workbench_projection_content_sha256(payload)
    try:
        raw_attestation = redaction_verifier(payload)
    except Exception as exc:
        raise WorkbenchProjectionError("redaction verification failed") from exc
    if workbench_projection_content_sha256(payload) != content_sha256:
        raise WorkbenchProjectionError("redaction verifier mutated projection")
    payload["redaction"] = _project_redaction(
        raw_attestation,
        generated=generated,
        observed=observed,
        content_sha256=content_sha256,
    )
    if len(serialize_workbench_projection(payload).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise WorkbenchProjectionError("projection exceeds wire size limit")
    return payload


def workbench_projection_content_sha256(payload: Mapping[str, Any]) -> str:
    """Return the canonical digest bound by the redaction verifier."""

    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def serialize_workbench_projection(payload: Mapping[str, Any]) -> str:
    """Serialize the exact compact UTF-8 JSON wire representation consumed by the browser."""

    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def validate_workbench_projection(
    payload: Mapping[str, Any],
    *,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    """Validate an existing wire snapshot against the exact projection contract."""

    item = _exact(
        payload,
        "snapshot",
        {
            "schemaVersion",
            "generatedAt",
            "expiresAt",
            "producer",
            "scope",
            "access",
            "matter",
            "tasks",
            "attention",
            "decisions",
            "evidence",
            "capabilities",
            "agents",
            "redaction",
        },
    )
    if item["schemaVersion"] != SCHEMA_VERSION:
        raise WorkbenchProjectionError("snapshot schema version is invalid")
    observed = observed_at or datetime.now(timezone.utc)
    generated = _timestamp(item["generatedAt"])
    expires = _timestamp(item["expiresAt"])
    if generated > observed or expires <= observed:
        raise WorkbenchProjectionError("projection is not currently valid")
    if expires <= generated or (expires - generated).total_seconds() > MAX_LEASE_SECONDS:
        raise WorkbenchProjectionError("projection lease is invalid")

    producer = _exact(item["producer"], "producer", {"id", "version"})
    if producer["id"] != PRODUCER_ID:
        raise WorkbenchProjectionError("producer is invalid")
    scope = _exact(
        item["scope"],
        "scope",
        {"workspaceId", "matterId", "purpose"},
    )
    projected: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": item["generatedAt"],
        "expiresAt": item["expiresAt"],
        "producer": {
            "id": PRODUCER_ID,
            "version": _id(producer["version"], "producer.version"),
        },
        "scope": {
            "workspaceId": _id(scope["workspaceId"], "scope.workspaceId"),
            "matterId": _id(scope["matterId"], "scope.matterId"),
            "purpose": _id(scope["purpose"], "scope.purpose"),
        },
    }
    access_input = _mapping(item["access"], "access")
    projected["access"] = _project_access(
        access_input,
        generated,
        expires,
        observed,
        workspace_id=projected["scope"]["workspaceId"],
        matter_id=projected["scope"]["matterId"],
        purpose=projected["scope"]["purpose"],
        actor_id=access_input.get("subjectId"),
        actor_role=access_input.get("role"),
    )
    projected["matter"] = _project_matter(_mapping(item["matter"], "matter"))
    projected["tasks"] = _project_collection(item["tasks"], "tasks", _project_task)
    projected["attention"] = _project_collection(
        item["attention"], "attention", _project_attention
    )
    projected["decisions"] = _project_collection(
        item["decisions"], "decisions", _project_decision
    )
    projected["evidence"] = _project_collection(
        item["evidence"], "evidence", _project_evidence
    )
    projected["capabilities"] = _project_collection(
        item["capabilities"], "capabilities", _project_capability
    )
    projected["agents"] = _project_collection(item["agents"], "agents", _project_agent)
    _validate_references(projected)
    projected["redaction"] = _project_redaction(
        _mapping(item["redaction"], "redaction"),
        generated=generated,
        observed=observed,
        content_sha256=workbench_projection_content_sha256(projected),
    )
    if projected != dict(item):
        raise WorkbenchProjectionError("snapshot canonical projection mismatch")
    if len(serialize_workbench_projection(projected).encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise WorkbenchProjectionError("projection exceeds wire size limit")
    return projected


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _project_redaction(
    value: Mapping[str, Any],
    *,
    generated: datetime,
    observed: datetime,
    content_sha256: str,
) -> dict[str, Any]:
    item = _exact(
        value,
        "redaction",
        {
            "status",
            "policyId",
            "policyVersion",
            "classifierId",
            "classifierVersion",
            "verifiedAt",
            "contentSha256",
        },
    )
    verified_at = _timestamp(item["verifiedAt"])
    if item["status"] != "verified" or verified_at < generated or verified_at > observed:
        raise WorkbenchProjectionError("redaction attestation is invalid")
    if item["contentSha256"] != content_sha256:
        raise WorkbenchProjectionError("redaction content binding mismatch")
    return {
        "status": "verified",
        "policyId": _id(item["policyId"], "redaction.policyId"),
        "policyVersion": _id(item["policyVersion"], "redaction.policyVersion"),
        "classifierId": _id(item["classifierId"], "redaction.classifierId"),
        "classifierVersion": _id(item["classifierVersion"], "redaction.classifierVersion"),
        "verifiedAt": item["verifiedAt"],
        "contentSha256": content_sha256,
    }


def _project_access(
    value: Mapping[str, Any],
    generated: datetime,
    projection_expires: datetime,
    observed: datetime,
    *,
    workspace_id: str,
    matter_id: str,
    purpose: str,
    actor_id: str,
    actor_role: str,
) -> dict[str, Any]:
    item = _exact(
        value,
        "access",
        {
            "mode",
            "decisionId",
            "decisionVersion",
            "subjectId",
            "role",
            "workspaceId",
            "matterId",
            "purpose",
            "issuedAt",
            "expiresAt",
            "reason",
        },
    )
    if item["mode"] == "deny":
        raise WorkbenchProjectionError("deny must not produce a snapshot")
    mode = _enum(item["mode"], "access.mode", {"assigned", "deputy"})
    issued = _timestamp(item["issuedAt"])
    expires = _timestamp(item["expiresAt"])
    if issued > observed or issued > generated:
        raise WorkbenchProjectionError("access issue time is in the future")
    if expires <= observed or expires <= issued or expires > projection_expires:
        raise WorkbenchProjectionError("access lease is invalid")
    if (expires - issued).total_seconds() > MAX_LEASE_SECONDS:
        raise WorkbenchProjectionError("access lease is invalid")
    reason = item["reason"]
    if mode == "deputy":
        reason = _display_text(reason, "access.reason")
    elif reason is not None:
        raise WorkbenchProjectionError("assigned access reason must be null")
    expected_scope = {
        "subjectId": _id(actor_id, "actor_id"),
        "role": _id(actor_role, "actor_role"),
        "workspaceId": _id(workspace_id, "workspace_id"),
        "matterId": _id(matter_id, "matter_id"),
        "purpose": _id(purpose, "purpose"),
    }
    if any(item[key] != expected for key, expected in expected_scope.items()):
        raise WorkbenchProjectionError("access scope binding mismatch")
    return {
        "mode": mode,
        "decisionId": _id(item["decisionId"], "access.decisionId"),
        "decisionVersion": _id(item["decisionVersion"], "access.decisionVersion"),
        "subjectId": expected_scope["subjectId"],
        "role": expected_scope["role"],
        "workspaceId": expected_scope["workspaceId"],
        "matterId": expected_scope["matterId"],
        "purpose": expected_scope["purpose"],
        "issuedAt": item["issuedAt"],
        "expiresAt": item["expiresAt"],
        "reason": reason,
    }


def _project_matter(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "matter", {"id", "businessCaseTypeId", "title", "status", "deadline", "currentStepId", "modelReference"})
    model = _exact(item["modelReference"], "matter.modelReference", {"kind", "modelKey", "sha256"})
    if model["kind"] != "bpmn" or not isinstance(model["sha256"], str) or not SHA256_PATTERN.fullmatch(model["sha256"]):
        raise WorkbenchProjectionError("matter model reference is invalid")
    current_step = item["currentStepId"]
    return {
        "id": _id(item["id"], "matter.id"),
        "businessCaseTypeId": _id(item["businessCaseTypeId"], "matter.businessCaseTypeId"),
        "title": _display_text(item["title"], "matter.title"),
        "status": _display_text(item["status"], "matter.status"),
        "deadline": _nullable_timestamp(item["deadline"], "matter.deadline"),
        "currentStepId": None if current_step is None else _id(current_step, "matter.currentStepId"),
        "modelReference": {
            "kind": "bpmn",
            "modelKey": _id(model["modelKey"], "matter.modelReference.modelKey"),
            "sha256": model["sha256"],
        },
    }


def _project_task(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "task", {"id", "title", "status", "dueAt", "stepId", "requiresApproval"})
    if not isinstance(item["requiresApproval"], bool):
        raise WorkbenchProjectionError("task.requiresApproval must be boolean")
    return {
        "id": _id(item["id"], "task.id"),
        "title": _display_text(item["title"], "task.title"),
        "status": _display_text(item["status"], "task.status"),
        "dueAt": _nullable_timestamp(item["dueAt"], "task.dueAt"),
        "stepId": _id(item["stepId"], "task.stepId"),
        "requiresApproval": item["requiresApproval"],
    }


def _project_attention(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "attention", {"id", "title", "reason", "severity", "dueAt", "taskId"})
    task_id = item["taskId"]
    return {
        "id": _id(item["id"], "attention.id"),
        "title": _display_text(item["title"], "attention.title"),
        "reason": _display_text(item["reason"], "attention.reason"),
        "severity": _enum(item["severity"], "attention.severity", {"info", "warning", "critical"}),
        "dueAt": _nullable_timestamp(item["dueAt"], "attention.dueAt"),
        "taskId": None if task_id is None else _id(task_id, "attention.taskId"),
    }


def _project_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "decision", {"id", "title", "status", "riskClass", "dueAt", "evidenceIds", "capabilityId"})
    refs = item["evidenceIds"]
    if not isinstance(refs, list) or len(refs) > MAX_ITEMS:
        raise WorkbenchProjectionError("decision.evidenceIds must be a bounded list")
    return {
        "id": _id(item["id"], "decision.id"),
        "title": _display_text(item["title"], "decision.title"),
        "status": _enum(item["status"], "decision.status", {"pending", "approved", "rejected", "expired"}),
        "riskClass": _enum(item["riskClass"], "decision.riskClass", {"R0", "R1", "R2", "R3", "R4"}),
        "dueAt": _nullable_timestamp(item["dueAt"], "decision.dueAt"),
        "evidenceIds": [_id(ref, "decision.evidenceIds") for ref in refs],
        "capabilityId": _id(item["capabilityId"], "decision.capabilityId"),
    }


def _project_evidence(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "evidence", {"id", "title", "kind", "authority", "sourceSystem", "sourceRef", "sha256"})
    digest = item["sha256"]
    if digest is not None and (not isinstance(digest, str) or not SHA256_PATTERN.fullmatch(digest)):
        raise WorkbenchProjectionError("evidence.sha256 is invalid")
    return {
        "id": _id(item["id"], "evidence.id"),
        "title": _display_text(item["title"], "evidence.title"),
        "kind": _enum(item["kind"], "evidence.kind", {"model_reference", "supporting", "audit", "immutable"}),
        "authority": _enum(item["authority"], "evidence.authority", {"non_authoritative", "authoritative"}),
        "sourceSystem": _opaque_id(item["sourceSystem"], "evidence.sourceSystem"),
        "sourceRef": _opaque_id(item["sourceRef"], "evidence.sourceRef"),
        "sha256": digest,
    }


def _project_capability(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "capability", {"id", "mode", "decision", "reason"})
    if item["decision"] != "deny":
        raise WorkbenchProjectionError("foundation capabilities must be deny-only")
    return {
        "id": _id(item["id"], "capability.id"),
        "mode": _enum(item["mode"], "capability.mode", {"read", "propose", "approve", "execute"}),
        "decision": "deny",
        "reason": _display_text(item["reason"], "capability.reason"),
    }


def _project_agent(value: Mapping[str, Any]) -> dict[str, Any]:
    item = _exact(value, "agent", {"id", "label", "status", "detail"})
    return {
        "id": _id(item["id"], "agent.id"),
        "label": _display_text(item["label"], "agent.label"),
        "status": _enum(item["status"], "agent.status", {"idle", "working", "waiting", "blocked"}),
        "detail": _display_text(item["detail"], "agent.detail"),
    }


def _validate_references(payload: Mapping[str, Any]) -> None:
    scope = payload["scope"]
    matter = payload["matter"]
    if matter["id"] != scope["matterId"]:
        raise WorkbenchProjectionError("matter scope mismatch")
    tasks = payload["tasks"]
    attention = payload["attention"]
    decisions = payload["decisions"]
    evidence = payload["evidence"]
    capabilities = payload["capabilities"]
    task_ids = _unique_ids(tasks, "tasks")
    step_ids = _unique_values(tasks, "stepId", "task step")
    _unique_ids(attention, "attention")
    _unique_ids(decisions, "decisions")
    evidence_ids = _unique_ids(evidence, "evidence")
    capability_ids = _unique_ids(capabilities, "capabilities")
    _unique_ids(payload["agents"], "agents")
    if matter["currentStepId"] is not None and matter["currentStepId"] not in step_ids:
        raise WorkbenchProjectionError("current step is not a projected task step")
    if any(item["taskId"] is not None and item["taskId"] not in task_ids for item in attention):
        raise WorkbenchProjectionError("attention task reference is invalid")
    for item in decisions:
        if item["capabilityId"] not in capability_ids:
            raise WorkbenchProjectionError("decision capability reference is invalid")
        if any(ref not in evidence_ids for ref in item["evidenceIds"]):
            raise WorkbenchProjectionError("decision evidence reference is invalid")
    if any(item["kind"] == "model_reference" and item["authority"] != "non_authoritative" for item in evidence):
        raise WorkbenchProjectionError("model references are not authoritative evidence")
    model = matter["modelReference"]
    if not any(item["kind"] == "model_reference" and item["sha256"] == model["sha256"] for item in evidence):
        raise WorkbenchProjectionError("model reference evidence is missing")


def _project_collection(
    value: Sequence[Mapping[str, Any]], label: str, projector: Callable[[Mapping[str, Any]], dict[str, Any]]
) -> list[dict[str, Any]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) or len(value) > MAX_ITEMS:
        raise WorkbenchProjectionError(f"{label} must be a bounded object list")
    return [projector(_mapping(item, label)) for item in value]


def _exact(value: Any, label: str, keys: set[str]) -> Mapping[str, Any]:
    item = _mapping(value, label)
    if set(item) != keys:
        raise WorkbenchProjectionError(f"{label} fields are invalid")
    return item


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WorkbenchProjectionError(f"{label} must be an object")
    return value


def _unique_ids(items: Sequence[Mapping[str, Any]], label: str) -> set[str]:
    return _unique_values(items, "id", label)


def _unique_values(items: Sequence[Mapping[str, Any]], key: str, label: str) -> set[str]:
    values = [item[key] for item in items]
    if len(set(values)) != len(values):
        raise WorkbenchProjectionError(f"{label} values are not unique")
    return set(values)


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise WorkbenchProjectionError("timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WorkbenchProjectionError("timestamp is invalid") from exc
    if parsed.isoformat(timespec="seconds").replace("+00:00", "Z") != value:
        raise WorkbenchProjectionError("timestamp is not canonical")
    return parsed


def _nullable_timestamp(value: Any, label: str) -> str | None:
    if value is None:
        return None
    _timestamp(value)
    return value


def _id(value: Any, label: str) -> str:
    if (
        not isinstance(value, str)
        or not ID_PATTERN.fullmatch(value)
        or SENSITIVE_TEXT_PATTERN.search(value)
    ):
        raise WorkbenchProjectionError(f"{label} is invalid")
    return value


def _opaque_id(value: Any, label: str) -> str:
    identifier = _id(value, label)
    if SENSITIVE_TEXT_PATTERN.search(identifier):
        raise WorkbenchProjectionError(f"{label} is invalid")
    return identifier


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkbenchProjectionError(f"{label} is invalid")
    try:
        utf16_units = len(value.encode("utf-16-le")) // 2
    except UnicodeEncodeError as exc:
        raise WorkbenchProjectionError(f"{label} is invalid") from exc
    if utf16_units > MAX_TEXT:
        raise WorkbenchProjectionError(f"{label} is invalid")
    return value


def _display_text(value: Any, label: str) -> str:
    text = _text(value, label)
    if SENSITIVE_TEXT_PATTERN.search(text):
        raise WorkbenchProjectionError(f"{label} contains prohibited sensitive text")
    return text


def _enum(value: Any, label: str, allowed: set[str]) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise WorkbenchProjectionError(f"{label} is invalid")
    return value
