from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Protocol


JsonObject = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class RuntimeRecord:
    record_type: str
    record_id: str
    tenant_id: str
    payload: dict[str, Any]
    sequence: int = 0
    matter_id: str = ""
    process_instance_id: str = ""
    subject_ref: str = ""
    action: str = ""
    event_type: str = ""


class RuntimeStoreAdapter(Protocol):
    def put_tenant(self, *, tenant_id: str, payload: JsonObject) -> RuntimeRecord:
        """Create or replace a tenant runtime anchor."""

    def put_user_binding(self, *, user_binding_id: str, tenant_id: str, payload: JsonObject) -> RuntimeRecord:
        """Create or replace a redacted tenant user binding."""

    def put_matter(self, *, matter_id: str, tenant_id: str, payload: JsonObject) -> RuntimeRecord:
        """Create or replace a matter metadata anchor without raw mandate data."""

    def put_process_instance(
        self,
        *,
        process_instance_id: str,
        tenant_id: str,
        matter_id: str,
        payload: JsonObject,
    ) -> RuntimeRecord:
        """Create or replace a process instance anchor."""

    def append_process_event(
        self,
        *,
        event_id: str,
        tenant_id: str,
        process_instance_id: str,
        event_type: str,
        payload: JsonObject,
    ) -> RuntimeRecord:
        """Append a process event used later for graph projection."""

    def append_audit_event(
        self,
        *,
        audit_event_id: str,
        tenant_id: str,
        subject_ref: str,
        action: str,
        payload: JsonObject,
    ) -> RuntimeRecord:
        """Append an audit event with redacted metadata only."""


class InMemoryRuntimeStore:
    def __init__(self) -> None:
        self._tenants: dict[str, RuntimeRecord] = {}
        self._user_bindings: dict[str, RuntimeRecord] = {}
        self._matters: dict[str, RuntimeRecord] = {}
        self._process_instances: dict[str, RuntimeRecord] = {}
        self._process_events: dict[str, list[RuntimeRecord]] = {}
        self._audit_events: dict[str, list[RuntimeRecord]] = {}

    def put_tenant(self, *, tenant_id: str, payload: JsonObject) -> RuntimeRecord:
        record = _record("tenant", tenant_id, tenant_id, payload)
        self._tenants[tenant_id] = record
        return record

    def put_user_binding(self, *, user_binding_id: str, tenant_id: str, payload: JsonObject) -> RuntimeRecord:
        record = _record("user_binding", user_binding_id, tenant_id, payload)
        self._user_bindings[user_binding_id] = record
        return record

    def put_matter(self, *, matter_id: str, tenant_id: str, payload: JsonObject) -> RuntimeRecord:
        record = _record("matter", matter_id, tenant_id, payload, matter_id=matter_id)
        self._matters[matter_id] = record
        return record

    def put_process_instance(
        self,
        *,
        process_instance_id: str,
        tenant_id: str,
        matter_id: str,
        payload: JsonObject,
    ) -> RuntimeRecord:
        _require(self._matters.get(matter_id), "matter_missing")
        record = _record(
            "process_instance",
            process_instance_id,
            tenant_id,
            payload,
            matter_id=matter_id,
            process_instance_id=process_instance_id,
        )
        self._process_instances[process_instance_id] = record
        return record

    def append_process_event(
        self,
        *,
        event_id: str,
        tenant_id: str,
        process_instance_id: str,
        event_type: str,
        payload: JsonObject,
    ) -> RuntimeRecord:
        _require(self._process_instances.get(process_instance_id), "process_instance_missing")
        events = self._process_events.setdefault(process_instance_id, [])
        record = _record(
            "process_event",
            event_id,
            tenant_id,
            payload,
            sequence=len(events) + 1,
            process_instance_id=process_instance_id,
            event_type=event_type,
        )
        events.append(record)
        return record

    def append_audit_event(
        self,
        *,
        audit_event_id: str,
        tenant_id: str,
        subject_ref: str,
        action: str,
        payload: JsonObject,
    ) -> RuntimeRecord:
        events = self._audit_events.setdefault(tenant_id, [])
        record = _record(
            "audit_event",
            audit_event_id,
            tenant_id,
            payload,
            sequence=len(events) + 1,
            subject_ref=subject_ref,
            action=action,
        )
        events.append(record)
        return record

    def get_tenant(self, tenant_id: str) -> RuntimeRecord | None:
        return self._tenants.get(tenant_id)

    def list_process_events(self, process_instance_id: str) -> list[RuntimeRecord]:
        return list(self._process_events.get(process_instance_id, []))

    def list_audit_events(self, tenant_id: str) -> list[RuntimeRecord]:
        return list(self._audit_events.get(tenant_id, []))

    def export_json(self) -> dict[str, Any]:
        return {
            "schema_version": "nac.atp-runtime-store-adapter-export/v0.1",
            "requires_owner_approval": False,
            "live_oci_enabled": False,
            "schema_apply_enabled": False,
            "graph_projection": {
                "mode": "deferred_projection_from_events",
                "source": "process_events",
            },
            "records": {
                "tenants": _records(self._tenants.values()),
                "user_bindings": _records(self._user_bindings.values()),
                "matters": _records(self._matters.values()),
                "process_instances": _records(self._process_instances.values()),
                "process_events": _records(
                    event for events in self._process_events.values() for event in events
                ),
                "audit_events": _records(event for events in self._audit_events.values() for event in events),
            },
        }


def _record(
    record_type: str,
    record_id: str,
    tenant_id: str,
    payload: JsonObject,
    *,
    sequence: int = 0,
    matter_id: str = "",
    process_instance_id: str = "",
    subject_ref: str = "",
    action: str = "",
    event_type: str = "",
) -> RuntimeRecord:
    _require_text(record_id, "record_id_missing")
    _require_text(tenant_id, "tenant_id_missing")
    safe_payload = _json_payload(payload)
    _reject_forbidden_payload(safe_payload)
    return RuntimeRecord(
        record_type=record_type,
        record_id=record_id,
        tenant_id=tenant_id,
        payload=safe_payload,
        sequence=sequence,
        matter_id=matter_id,
        process_instance_id=process_instance_id,
        subject_ref=subject_ref,
        action=action,
        event_type=event_type,
    )


def _json_payload(payload: JsonObject) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise TypeError("payload_must_be_json_object")
    try:
        return json.loads(json.dumps(dict(payload), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise TypeError("payload_must_be_json_serializable") from exc


def _reject_forbidden_payload(payload: Mapping[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True).lower()
    forbidden_terms = ("client_secret", "private_key", "raw_mandate", "mandatsdaten", "owner_id")
    for term in forbidden_terms:
        if term in serialized:
            raise ValueError("runtime_payload_forbidden_term: " + term)


def _records(records: Any) -> list[dict[str, Any]]:
    return [asdict(copy.deepcopy(record)) for record in records]


def _require(value: object, message: str) -> None:
    if not value:
        raise ValueError(message)


def _require_text(value: str, message: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(message)
