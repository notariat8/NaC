from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from nac_bff.azure_activation import LIST_IDS, MATTER_ID, SITE_ID, WORKSPACE_ID
from nac_mvp_test_environment import (
    BUSINESS_CASE_TYPE_ID,
    DEADLINE,
    KG_SCHEMA_VERSION,
    MATTER_STATUS,
    TASKS,
    WORKFLOW_VERSION,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
SYNTHETIC_NOTARY_TEAM = "NaC-Notar-01"
SYNTHETIC_LEAD_ACTOR = "00000000-0000-4000-8000-000000000001"
SYNTHETIC_LIVE_ACTOR_ID = "94f4a71c-ff52-4074-b215-8cc138be329b"
SYNTHETIC_LIVE_ACTOR_LOOKUP_ID = "11"
SYNTHETIC_LIVE_LEAD_LOOKUP_ID = "12"
SYNTHETIC_GRANT_ID = "NAC-SYN-BFF-GRANT-001"
SYNTHETIC_AUDIT_EVENT_ID = "NAC-SYN-BFF-AUDIT-001"
SYNTHETIC_AUDIT_CORRELATION_ID = "NAC-SYN-BFF-AUDIT-CORRELATION-001"
SYNTHETIC_VALID_FROM = "2026-07-01T00:00:00Z"
# Stable synthetic fixture horizon. Denied-mode tests still patch this row to an
# expired state and restore the exact baseline afterwards.
SYNTHETIC_VALID_UNTIL = "2099-12-31T23:59:59Z"

_ACTOR_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_ITEM_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_MODES = frozenset({"assigned", "deputy", "denied"})


class GraphRestV1Client(Protocol):
    base_url: str

    def get(self, path: str) -> dict[str, Any]: ...

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]: ...


class LiveSyntheticWorkspaceError(RuntimeError):
    """Stable fail-closed error that never includes Graph data."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class _Target:
    list_name: str
    key_field: str
    key_value: str
    fields: Mapping[str, Any]

    @property
    def collection_path(self) -> str:
        return _collection_path(self.list_name)

    @property
    def read_path(self) -> str:
        projection = ",".join(self.fields)
        expression = f"fields/{self.key_field} eq '{_escape_filter(self.key_value)}'"
        encoded_filter = urllib.parse.quote(expression, safe="/'")
        return (
            f"{self.collection_path}?$select=id"
            f"&$expand=fields($select={projection})"
            f"&$filter={encoded_filter}&$top=2"
        )


class LiveSyntheticWorkspaceManager:
    """Owns only the fixed synthetic BFF workspace rows used by live smoke tests."""

    def __init__(self, client: GraphRestV1Client) -> None:
        if getattr(client, "base_url", None) != GRAPH_BASE_URL:
            raise LiveSyntheticWorkspaceError("GRAPH_V1_BOUNDARY_INVALID")
        self._client = client

    def inspect_seed(
        self,
        actor_id: str,
        correlation_id: str,
        *,
        workspace_id: str = WORKSPACE_ID,
    ) -> dict[str, Any]:
        """Inspect canonical rows without creating or patching any item."""

        actor = _validate_scope(actor_id, correlation_id, workspace_id)
        targets = _targets(actor)
        absent = 0
        verified = 0
        for target in targets:
            existing = self._lookup(target)
            if existing is None:
                absent += 1
                continue
            self._assert_target_fields(
                target,
                existing,
                actor=actor,
                allow_modes=True,
            )
            verified += 1
        return {
            "schema_version": "nac.live-synthetic-workspace-preflight/v1",
            "status": "PASSED",
            "absent_count": absent,
            "verified_count": verified,
            "target_binding_sha256": _digest(
                {
                    "workspace": WORKSPACE_ID,
                    "site": SITE_ID,
                    "lists": LIST_IDS,
                    "matter": MATTER_ID,
                }
            ),
            "actor_binding_sha256": _digest(actor),
            "correlation_sha256": _digest(correlation_id),
        }

    def ensure_seed(
        self,
        actor_id: str,
        correlation_id: str,
        *,
        workspace_id: str = WORKSPACE_ID,
    ) -> dict[str, Any]:
        actor = _validate_scope(actor_id, correlation_id, workspace_id)
        targets = _targets(actor)
        created = 0

        for target in targets:
            existing = self._lookup(target)
            if existing is None:
                response = self._post(
                    target.collection_path, {"fields": dict(target.fields)}
                )
                _response_item_id(response)
                created += 1
                existing = self._lookup(target)
                if existing is None:
                    raise LiveSyntheticWorkspaceError("CREATE_READBACK_MISSING")
            self._assert_target_fields(target, existing, actor=actor, allow_modes=True)

        transition = self._set_mode("assigned", actor, targets=targets)
        self._assert_all_exact(actor, mode="assigned")
        return _result(
            operation="ensure_seed",
            mode="assigned",
            actor=actor,
            correlation_id=correlation_id,
            created=created,
            patched=transition,
            verified=len(targets),
        )

    def set_access_mode(
        self,
        mode: str,
        actor_id: str,
        correlation_id: str,
        *,
        workspace_id: str = WORKSPACE_ID,
    ) -> dict[str, Any]:
        actor = _validate_scope(actor_id, correlation_id, workspace_id)
        if mode not in _MODES:
            raise LiveSyntheticWorkspaceError("ACCESS_MODE_INVALID")
        targets = _targets(actor)
        for target in targets:
            existing = self._lookup(target)
            if existing is None:
                raise LiveSyntheticWorkspaceError("SYNTHETIC_SEED_MISSING")
            self._assert_target_fields(target, existing, actor=actor, allow_modes=True)

        patched = self._set_mode(mode, actor, targets=targets)
        self._assert_all_exact(actor, mode=mode)
        return _result(
            operation="set_access_mode",
            mode=mode,
            actor=actor,
            correlation_id=correlation_id,
            created=0,
            patched=patched,
            verified=len(targets),
        )

    def restore_assigned(
        self,
        actor_id: str,
        correlation_id: str,
        *,
        workspace_id: str = WORKSPACE_ID,
    ) -> dict[str, Any]:
        return self.set_access_mode(
            "assigned", actor_id, correlation_id, workspace_id=workspace_id
        )

    def verify_idempotency(
        self,
        actor_id: str,
        correlation_id: str,
        *,
        workspace_id: str = WORKSPACE_ID,
    ) -> dict[str, Any]:
        actor = _validate_scope(actor_id, correlation_id, workspace_id)
        self._assert_all_exact(actor, mode="assigned")
        return _result(
            operation="verify_idempotency",
            mode="assigned",
            actor=actor,
            correlation_id=correlation_id,
            created=0,
            patched=0,
            verified=len(_targets(actor)),
        )

    def _set_mode(self, mode: str, actor: str, *, targets: tuple[_Target, ...]) -> int:
        matter = targets[0]
        grant = targets[-2]
        matter_item = self._required_lookup(matter)
        grant_item = self._required_lookup(grant)
        desired_matter = _matter_access_fields(mode, actor)
        desired_grant = {"Status": "Aktiv" if mode == "deputy" else "Inaktiv"}
        patched = 0

        # Revoke first for assigned/denied; unassign first for deputy. This
        # prevents a transient deputy grant from widening assigned access.
        if mode != "deputy":
            patched += self._patch_if_needed(grant, grant_item, desired_grant)
            patched += self._patch_if_needed(matter, matter_item, desired_matter)
        else:
            patched += self._patch_if_needed(matter, matter_item, desired_matter)
            patched += self._patch_if_needed(grant, grant_item, desired_grant)
        return patched

    def _patch_if_needed(
        self,
        target: _Target,
        item: tuple[str, dict[str, Any]],
        desired: Mapping[str, Any],
    ) -> int:
        item_id, current = item
        if all(current.get(key) == value for key, value in desired.items()):
            return 0
        path = f"{target.collection_path}/{urllib.parse.quote(item_id, safe='')}/fields"
        response = self._patch(path, dict(desired))
        if type(response) is not dict:
            raise LiveSyntheticWorkspaceError("PATCH_RESPONSE_INVALID")
        readback = self._required_lookup(target)
        if any(readback[1].get(key) != value for key, value in desired.items()):
            raise LiveSyntheticWorkspaceError("PATCH_READBACK_DIVERGED")
        return 1

    def _assert_all_exact(self, actor: str, *, mode: str) -> None:
        targets = _targets(actor)
        for target in targets:
            item = self._required_lookup(target)
            expected = dict(target.fields)
            if target.list_name == "Akten":
                expected.update(_matter_access_fields(mode, actor))
            elif target.list_name == "Vertretungsfreigaben":
                expected["Status"] = "Aktiv" if mode == "deputy" else "Inaktiv"
            if item[1] != expected:
                raise LiveSyntheticWorkspaceError("EXACT_READBACK_DIVERGED")

    def _assert_target_fields(
        self,
        target: _Target,
        item: tuple[str, dict[str, Any]],
        *,
        actor: str,
        allow_modes: bool,
    ) -> None:
        fields = item[1]
        if fields == dict(target.fields):
            return
        if allow_modes and target.list_name in {"Akten", "Vertretungsfreigaben"}:
            variants: list[dict[str, Any]] = []
            for mode in _MODES:
                expected = dict(target.fields)
                if target.list_name == "Akten":
                    expected.update(_matter_access_fields(mode, actor))
                else:
                    expected["Status"] = "Aktiv" if mode == "deputy" else "Inaktiv"
                variants.append(expected)
            if fields in variants:
                return
        raise LiveSyntheticWorkspaceError("SYNTHETIC_ROW_DIVERGED")

    def _required_lookup(self, target: _Target) -> tuple[str, dict[str, Any]]:
        item = self._lookup(target)
        if item is None:
            raise LiveSyntheticWorkspaceError("SYNTHETIC_SEED_MISSING")
        return item

    def _lookup(self, target: _Target) -> tuple[str, dict[str, Any]] | None:
        payload = self._get(target.read_path)
        if type(payload) is not dict or type(payload.get("value")) is not list:
            raise LiveSyntheticWorkspaceError("GRAPH_RESPONSE_INVALID")
        if payload.get("@odata.nextLink") is not None:
            raise LiveSyntheticWorkspaceError("GRAPH_PAGING_BLOCKED")
        if set(payload) - {"value", "@odata.context"}:
            raise LiveSyntheticWorkspaceError("GRAPH_RESPONSE_TOO_BROAD")
        rows = payload["value"]
        if len(rows) > 1:
            raise LiveSyntheticWorkspaceError("SYNTHETIC_DUPLICATE_BLOCKED")
        if not rows:
            return None
        row = rows[0]
        if type(row) is not dict or set(row) - {
            "id",
            "fields",
            "@odata.etag",
            "fields@odata.context",
        }:
            raise LiveSyntheticWorkspaceError("GRAPH_ITEM_INVALID")
        item_id = row.get("id")
        fields = row.get("fields")
        if (
            type(item_id) is not str
            or _ITEM_ID_RE.fullmatch(item_id) is None
            or type(fields) is not dict
        ):
            raise LiveSyntheticWorkspaceError("GRAPH_ITEM_INVALID")
        normalized_fields = {
            key: value for key, value in fields.items() if key != "@odata.etag"
        }
        if set(normalized_fields) - set(target.fields):
            raise LiveSyntheticWorkspaceError("GRAPH_ITEM_INVALID")
        missing_fields = set(target.fields) - set(normalized_fields)
        if any(target.fields[key] not in {"", None} for key in missing_fields):
            raise LiveSyntheticWorkspaceError("GRAPH_ITEM_INVALID")
        normalized_fields.update({key: target.fields[key] for key in missing_fields})
        if normalized_fields.get(target.key_field) != target.key_value:
            raise LiveSyntheticWorkspaceError("GRAPH_FILTER_READBACK_INVALID")
        return item_id, normalized_fields

    def _get(self, path: str) -> dict[str, Any]:
        try:
            return self._client.get(path)
        except LiveSyntheticWorkspaceError:
            raise
        except Exception:
            raise LiveSyntheticWorkspaceError("GRAPH_REQUEST_FAILED") from None

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._client.post(path, payload)
        except LiveSyntheticWorkspaceError:
            raise
        except Exception:
            raise LiveSyntheticWorkspaceError("GRAPH_REQUEST_FAILED") from None

    def _patch(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._client.patch(path, payload)
        except LiveSyntheticWorkspaceError:
            raise
        except Exception:
            raise LiveSyntheticWorkspaceError("GRAPH_REQUEST_FAILED") from None


def _targets(actor: str) -> tuple[_Target, ...]:
    live_lookup_mode = actor == SYNTHETIC_LIVE_ACTOR_ID
    actor_value = SYNTHETIC_LIVE_ACTOR_LOOKUP_ID if live_lookup_mode else actor
    lead_value = SYNTHETIC_LIVE_LEAD_LOOKUP_ID if live_lookup_mode else SYNTHETIC_LEAD_ACTOR

    def person_field(name: str) -> str:
        return f"{name}LookupId" if live_lookup_mode else name

    matter_fields = {
        "NacCaseId": MATTER_ID,
        "Aktenzeichen": "SYN-MAT-001",
        "Vorgangstyp": BUSINESS_CASE_TYPE_ID,
        "Status": MATTER_STATUS,
        "NotarTeam": SYNTHETIC_NOTARY_TEAM,
        "Vertraulichkeitsstufe": "Normal",
        "NacWorkflowVersion": WORKFLOW_VERSION,
        "KgVersion": KG_SCHEMA_VERSION,
        "FristNaechsteAktion": DEADLINE,
        **_matter_access_fields("assigned", actor),
    }
    targets: list[_Target] = [
        _Target("Akten", "NacCaseId", MATTER_ID, matter_fields)
    ]
    for task in TASKS:
        task_fields = {
            "NacTaskId": task["task_id"],
            "NacCaseId": MATTER_ID,
            "BpmnStepCode": task["step_code"],
            "Status": task["status"],
            "RequiresNotaryApproval": task["requires_notary_approval"],
            "DueDate": task["due_at"],
        }
        targets.append(
            _Target("AufgabenFristen", "NacTaskId", task["task_id"], task_fields)
        )
    targets.extend(
        (
            _Target(
                "Vertretungsfreigaben",
                "GrantId",
                SYNTHETIC_GRANT_ID,
                {
                    "GrantId": SYNTHETIC_GRANT_ID,
                    "NacCaseId": MATTER_ID,
                    person_field("FromUser"): lead_value,
                    person_field("ToUser"): actor_value,
                    "GrantedRole": "SachbearbeitungVertretung",
                    "Reason": "Synthetische zeitbegrenzte BFF-Vertretung",
                    "ValidFrom": SYNTHETIC_VALID_FROM,
                    "ValidUntil": SYNTHETIC_VALID_UNTIL,
                    person_field("ApprovedBy"): lead_value,
                    "Status": "Inaktiv",
                    "AuditCorrelationId": SYNTHETIC_AUDIT_CORRELATION_ID,
                },
            ),
            _Target(
                "AuditJournalLite",
                "EventId",
                SYNTHETIC_AUDIT_EVENT_ID,
                {
                    "EventId": SYNTHETIC_AUDIT_EVENT_ID,
                    "Timestamp": SYNTHETIC_VALID_FROM,
                    person_field("Actor"): lead_value,
                    "NacCaseId": MATTER_ID,
                    "Action": "DeputyGrantApproved",
                    "ObjectType": "Vertretungsfreigabe",
                    "ObjectId": SYNTHETIC_GRANT_ID,
                    "Reason": "Synthetischer BFF-Zugriffstest",
                    "CorrelationId": SYNTHETIC_AUDIT_CORRELATION_ID,
                },
            ),
        )
    )
    return tuple(targets)


def _matter_access_fields(mode: str, actor: str) -> dict[str, Any]:
    if actor == SYNTHETIC_LIVE_ACTOR_ID:
        field = "FederfuehrenderNotarLookupId"
        clerk_field = "SachbearbeitungLookupId"
        actor_value = SYNTHETIC_LIVE_ACTOR_LOOKUP_ID
        lead_value = SYNTHETIC_LIVE_LEAD_LOOKUP_ID
    else:
        field = "FederfuehrenderNotar"
        clerk_field = "Sachbearbeitung"
        actor_value = actor
        lead_value = SYNTHETIC_LEAD_ACTOR
    if mode == "assigned":
        return {field: actor_value, clerk_field: ""}
    return {field: lead_value, clerk_field: ""}


def _collection_path(list_name: str) -> str:
    if list_name not in LIST_IDS or set(LIST_IDS) != {
        "Akten",
        "AufgabenFristen",
        "Vertretungsfreigaben",
        "AuditJournalLite",
    }:
        raise LiveSyntheticWorkspaceError("LIST_BINDING_INVALID")
    site = urllib.parse.quote(SITE_ID, safe="")
    list_id = urllib.parse.quote(LIST_IDS[list_name], safe="")
    return f"/sites/{site}/lists/{list_id}/items"


def _response_item_id(response: object) -> str:
    if type(response) is not dict:
        raise LiveSyntheticWorkspaceError("CREATE_RESPONSE_INVALID")
    item_id = response.get("id")
    if type(item_id) is not str or _ITEM_ID_RE.fullmatch(item_id) is None:
        raise LiveSyntheticWorkspaceError("CREATE_RESPONSE_INVALID")
    return item_id


def _validate_scope(actor_id: object, correlation_id: object, workspace_id: object) -> str:
    if workspace_id != WORKSPACE_ID:
        raise LiveSyntheticWorkspaceError("WORKSPACE_SCOPE_INVALID")
    if type(actor_id) is not str or _ACTOR_RE.fullmatch(actor_id) is None:
        raise LiveSyntheticWorkspaceError("ACTOR_ID_INVALID")
    if type(correlation_id) is not str or _CORRELATION_RE.fullmatch(correlation_id) is None:
        raise LiveSyntheticWorkspaceError("CORRELATION_ID_INVALID")
    return actor_id.lower()


def _escape_filter(value: str) -> str:
    return value.replace("'", "''")


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _result(
    *,
    operation: str,
    mode: str,
    actor: str,
    correlation_id: str,
    created: int,
    patched: int,
    verified: int,
) -> dict[str, Any]:
    return {
        "schema_version": "nac.live-synthetic-workspace-result/v1",
        "status": "PASSED",
        "operation": operation,
        "mode": mode,
        "created_count": created,
        "patched_count": patched,
        "verified_count": verified,
        "target_binding_sha256": _digest(
            {"workspace": WORKSPACE_ID, "site": SITE_ID, "lists": LIST_IDS, "matter": MATTER_ID}
        ),
        "actor_binding_sha256": _digest(actor),
        "correlation_sha256": _digest(correlation_id),
        "state_sha256": _digest(
            {
                "mode": mode,
                "targets": [
                    {
                        "list": target.list_name,
                        "key_field": target.key_field,
                        "fields": dict(target.fields),
                    }
                    for target in _targets(actor)
                ],
            }
        ),
    }


__all__ = [
    "GRAPH_BASE_URL",
    "LiveSyntheticWorkspaceError",
    "LiveSyntheticWorkspaceManager",
]
