from __future__ import annotations

import re
import urllib.parse
from dataclasses import asdict, dataclass, replace
from types import MappingProxyType
from typing import Any, Mapping

from notary_kg.business_case_type_mutation import (
    BusinessCaseTypeMutation,
    canonical_hash,
    mutation_snapshot,
    revalidate_business_case_type_mutation,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
WRITE_PERMISSION = "Sites.Selected"
WRITE_SITE_GRANT_ROLE = "write"
BFF_PERMISSION = "Sites.Selected"
BFF_SITE_GRANT_ROLE = "read"
MAX_DEDUPE_ROWS = 2

_CASE_OPERATIONS = frozenset({"case_create", "case_status_update"})
_TASK_OPERATIONS = frozenset({"task_create", "task_update"})
_PATCH_OPERATIONS = frozenset(
    {"case_status_update", "task_update", "business_case_type_backfill"}
)
_OPERATION_ROLES = {
    "case_create": frozenset(
        {"notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"}
    ),
    "case_status_update": frozenset(
        {"notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"}
    ),
    "task_create": frozenset(
        {"notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"}
    ),
    "task_update": frozenset(
        {"notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"}
    ),
    "business_case_type_backfill": frozenset(
        {"BackfillOperator", "runtime_service"}
    ),
}
_OPERATION_PURPOSE = {
    "case_create": "matter_workflow",
    "case_status_update": "matter_workflow",
    "task_create": "matter_workflow",
    "task_update": "matter_workflow",
    "business_case_type_backfill": "business_case_type_migration",
}
_BOUND_VALUE = re.compile(r"[^\x00-\x20\x7f]{1,256}\Z")
_ITEM_ID = re.compile(r"[1-9][0-9]{0,18}\Z")


class WritePlanBlocked(PermissionError):
    """Raised when a write plan differs from its issued canonical snapshot."""


@dataclass(frozen=True, slots=True)
class BoundWriteTarget:
    workspace_id: str
    site_id: str
    akten_list_id: str
    aufgaben_list_id: str
    write_identity_id: str
    bff_uami_identity_id: str


@dataclass(frozen=True, slots=True)
class MutationAuthorization:
    workspace_id: str
    site_id: str
    list_id: str
    actor_role: str
    purpose: str
    approval_ref: str
    approved_operation: str
    write_approved: bool
    write_identity_id: str
    write_identity_permission: str
    write_site_grant_role: str
    write_identity_site_id: str
    bff_uami_identity_id: str
    bff_uami_permission: str
    bff_uami_site_grant_role: str
    bff_uami_site_id: str


@dataclass(frozen=True, slots=True)
class GraphWriteRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    payload: Mapping[str, Any] | None
    phase: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "headers", _freeze_json(self.headers))
        if self.payload is not None:
            object.__setattr__(self, "payload", _freeze_json(self.payload))


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeWritePlan:
    mutation: BusinessCaseTypeMutation
    authorization: MutationAuthorization
    logical_list_name: str
    target_binding_hash: str
    collection_url: str
    write_method: str
    write_url: str
    write_payload: Mapping[str, Any]
    dedupe_request: GraphWriteRequest | None
    freshness_request: GraphWriteRequest | None
    plan_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "write_payload", _freeze_json(self.write_payload))

    def write_request(self, *, fresh_etag: str | None = None) -> GraphWriteRequest:
        headers = {"Content-Type": "application/json"}
        if self.write_method == "PATCH":
            if fresh_etag is None or fresh_etag != self.mutation.expected_etag:
                raise WritePlanBlocked("PATCH requires the fresh exact expected ETag")
            headers["If-Match"] = fresh_etag
        return GraphWriteRequest(
            method=self.write_method,
            url=self.write_url,
            headers=headers,
            payload=self.write_payload,
            phase="write",
        )

    def item_readback_request(self, item_id: str) -> GraphWriteRequest:
        if _ITEM_ID.fullmatch(item_id) is None:
            raise WritePlanBlocked("readback item id is invalid")
        selected_fields = ",".join(self.mutation.fields)
        return GraphWriteRequest(
            method="GET",
            url=(
                f"{self.collection_url}/{item_id}"
                f"?$select=id,eTag&$expand=fields($select={selected_fields})"
            ),
            headers={},
            payload=None,
            phase="readback",
        )

    def collection_readback_request(self) -> GraphWriteRequest:
        if self.dedupe_request is None:
            raise WritePlanBlocked("collection readback is create-only")
        return GraphWriteRequest(
            method="GET",
            url=self.dedupe_request.url,
            headers={},
            payload=None,
            phase="readback",
        )


class BusinessCaseTypeWritePlanBuilder:
    def __init__(self, target: BoundWriteTarget) -> None:
        _validate_target(target)
        if target.write_identity_id == target.bff_uami_identity_id:
            raise WritePlanBlocked(
                "write identity must be separate from the BFF read identity"
            )
        self._target = target
        self._issued_snapshots: dict[str, dict[str, Any]] = {}

    def build(
        self,
        mutation: BusinessCaseTypeMutation,
        authorization: MutationAuthorization,
    ) -> BusinessCaseTypeWritePlan:
        canonical_mutation = revalidate_business_case_type_mutation(mutation)
        plan = self._construct(canonical_mutation, authorization)
        plan_sha256 = canonical_hash(_plan_snapshot(plan))
        issued = replace(plan, plan_sha256=plan_sha256)
        self._issued_snapshots[plan_sha256] = _plan_snapshot(
            issued, include_plan_hash=True
        )
        return issued

    def revalidate(
        self, plan: BusinessCaseTypeWritePlan
    ) -> BusinessCaseTypeWritePlan:
        if not isinstance(plan, BusinessCaseTypeWritePlan):
            raise WritePlanBlocked("plan type is invalid")
        issued = self._issued_snapshots.get(plan.plan_sha256)
        if issued is None:
            raise WritePlanBlocked("plan was not issued by this bound builder")
        current = _plan_snapshot(plan, include_plan_hash=True)
        if current != issued:
            raise WritePlanBlocked("issued plan snapshot drift")
        try:
            mutation = revalidate_business_case_type_mutation(plan.mutation)
            expected = self._construct(mutation, plan.authorization)
        except Exception as exc:
            raise WritePlanBlocked("plan canonical revalidation failed") from exc
        expected_hash = canonical_hash(_plan_snapshot(expected))
        if expected_hash != plan.plan_sha256:
            raise WritePlanBlocked("plan canonical hash drift")
        if _plan_snapshot(plan) != _plan_snapshot(expected):
            raise WritePlanBlocked("plan canonical target or request drift")
        return replace(expected, plan_sha256=expected_hash)

    def _construct(
        self,
        mutation: BusinessCaseTypeMutation,
        authorization: MutationAuthorization,
    ) -> BusinessCaseTypeWritePlan:
        logical_list_name, expected_list_id = self._list_binding(
            mutation.operation
        )
        self._validate_authorization(
            mutation, authorization, expected_list_id=expected_list_id
        )
        collection_url = (
            f"{GRAPH_BASE_URL}/sites/{_segment(self._target.site_id, safe=',')}"
            f"/lists/{_segment(expected_list_id)}/items"
        )
        if mutation.operation in _PATCH_OPERATIONS:
            if mutation.item_id is None:
                raise WritePlanBlocked("PATCH mutation lacks item binding")
            write_url = f"{collection_url}/{_segment(mutation.item_id)}/fields"
            freshness_request = GraphWriteRequest(
                method="GET",
                url=(
                    f"{collection_url}/{_segment(mutation.item_id)}"
                    f"?$select=id,eTag&$expand=fields($select={','.join(mutation.fields)})"
                ),
                headers={},
                payload=None,
                phase="freshness",
            )
            dedupe_request = None
            write_payload: Mapping[str, Any] = dict(mutation.fields)
            method = "PATCH"
        else:
            if mutation.dedupe_field is None:
                raise WritePlanBlocked("create mutation lacks dedupe binding")
            dedupe_value = mutation.fields[mutation.dedupe_field]
            if type(dedupe_value) is not str:
                raise WritePlanBlocked("create dedupe value must be a string")
            dedupe_request = GraphWriteRequest(
                method="GET",
                url=_dedupe_url(
                    collection_url,
                    mutation.dedupe_field,
                    dedupe_value,
                    tuple(mutation.fields),
                ),
                headers={},
                payload=None,
                phase="dedupe",
            )
            freshness_request = None
            write_url = collection_url
            write_payload = {"fields": dict(mutation.fields)}
            method = "POST"
        binding_hash = canonical_hash(
            {
                "workspace_id": self._target.workspace_id,
                "site_id": self._target.site_id,
                "akten_list_id": self._target.akten_list_id,
                "aufgaben_list_id": self._target.aufgaben_list_id,
                "list_id": expected_list_id,
                "logical_list_name": logical_list_name,
                "operation": mutation.operation,
                "write_identity_id": self._target.write_identity_id,
                "write_permission": WRITE_PERMISSION,
                "write_site_grant_role": WRITE_SITE_GRANT_ROLE,
                "bff_uami_identity_id": self._target.bff_uami_identity_id,
                "bff_permission": BFF_PERMISSION,
                "bff_site_grant_role": BFF_SITE_GRANT_ROLE,
            }
        )
        return BusinessCaseTypeWritePlan(
            mutation=mutation,
            authorization=authorization,
            logical_list_name=logical_list_name,
            target_binding_hash=binding_hash,
            collection_url=collection_url,
            write_method=method,
            write_url=write_url,
            write_payload=write_payload,
            dedupe_request=dedupe_request,
            freshness_request=freshness_request,
            plan_sha256="",
        )

    def _list_binding(self, operation: str) -> tuple[str, str]:
        if operation in _CASE_OPERATIONS or operation == "business_case_type_backfill":
            return "Akten", self._target.akten_list_id
        if operation in _TASK_OPERATIONS:
            return "AufgabenFristen", self._target.aufgaben_list_id
        raise WritePlanBlocked("operation is outside the S4b allowlist")

    def _validate_authorization(
        self,
        mutation: BusinessCaseTypeMutation,
        authorization: MutationAuthorization,
        *,
        expected_list_id: str,
    ) -> None:
        if not isinstance(authorization, MutationAuthorization):
            raise WritePlanBlocked("authorization type is invalid")
        exact_bindings = {
            "workspace": (authorization.workspace_id, self._target.workspace_id),
            "site": (authorization.site_id, self._target.site_id),
            "list": (authorization.list_id, expected_list_id),
            "purpose": (authorization.purpose, _OPERATION_PURPOSE.get(mutation.operation)),
            "approved operation": (authorization.approved_operation, mutation.operation),
            "write identity": (authorization.write_identity_id, self._target.write_identity_id),
            "write permission": (authorization.write_identity_permission, WRITE_PERMISSION),
            "write site grant": (authorization.write_site_grant_role, WRITE_SITE_GRANT_ROLE),
            "write identity site": (authorization.write_identity_site_id, self._target.site_id),
            "BFF identity": (
                authorization.bff_uami_identity_id,
                self._target.bff_uami_identity_id,
            ),
            "BFF permission": (authorization.bff_uami_permission, BFF_PERMISSION),
            "BFF site grant": (authorization.bff_uami_site_grant_role, BFF_SITE_GRANT_ROLE),
            "BFF identity site": (authorization.bff_uami_site_id, self._target.site_id),
        }
        for name, (actual, expected) in exact_bindings.items():
            if actual != expected:
                raise WritePlanBlocked(f"{name} binding drift")
        if authorization.actor_role not in _OPERATION_ROLES.get(
            mutation.operation, frozenset()
        ):
            raise WritePlanBlocked("role binding drift")
        if authorization.write_approved is not True:
            raise WritePlanBlocked("write approval is absent")
        if (
            type(authorization.approval_ref) is not str
            or not authorization.approval_ref.startswith("synthetic-approval-")
            or _BOUND_VALUE.fullmatch(authorization.approval_ref) is None
        ):
            raise WritePlanBlocked("approval reference binding drift")
        if authorization.write_identity_id == authorization.bff_uami_identity_id:
            raise WritePlanBlocked(
                "write identity must remain separate from BFF UAMI"
            )


def plan_snapshot(plan: BusinessCaseTypeWritePlan) -> dict[str, Any]:
    return _plan_snapshot(plan, include_plan_hash=True)


def _plan_snapshot(
    plan: BusinessCaseTypeWritePlan,
    *,
    include_plan_hash: bool = False,
) -> dict[str, Any]:
    payload = {
        "mutation": mutation_snapshot(plan.mutation),
        "authorization": asdict(plan.authorization),
        "logical_list_name": plan.logical_list_name,
        "target_binding_hash": plan.target_binding_hash,
        "collection_url": plan.collection_url,
        "write_method": plan.write_method,
        "write_url": plan.write_url,
        "write_payload": _plain_json(plan.write_payload),
        "dedupe_request": _request_snapshot(plan.dedupe_request),
        "freshness_request": _request_snapshot(plan.freshness_request),
    }
    if include_plan_hash:
        payload["plan_sha256"] = plan.plan_sha256
    return payload


def _request_snapshot(request: GraphWriteRequest | None) -> dict[str, Any] | None:
    if request is None:
        return None
    return {
        "method": request.method,
        "url": request.url,
        "headers": _plain_json(request.headers),
        "payload": _plain_json(request.payload),
        "phase": request.phase,
    }


def _validate_target(target: BoundWriteTarget) -> None:
    for name, value in asdict(target).items():
        if type(value) is not str or _BOUND_VALUE.fullmatch(value) is None:
            raise WritePlanBlocked(f"invalid bound {name}")
    if target.akten_list_id == target.aufgaben_list_id:
        raise WritePlanBlocked("Akten and AufgabenFristen list bindings differ")


def _segment(value: str, *, safe: str = "") -> str:
    return urllib.parse.quote(value, safe=safe)


def _dedupe_url(
    collection_url: str,
    field: str,
    value: str,
    selected_fields: tuple[str, ...],
) -> str:
    escaped = urllib.parse.quote(value.replace("'", "''"), safe="")
    projection = ",".join(selected_fields)
    return (
        f"{collection_url}?$select=id,eTag"
        f"&$expand=fields($select={projection})"
        f"&$filter=fields/{field}%20eq%20%27{escaped}%27"
        f"&$top={MAX_DEDUPE_ROWS}"
    )


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _plain_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json(item) for item in value]
    return value
