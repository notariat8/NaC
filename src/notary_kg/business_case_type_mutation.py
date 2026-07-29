from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Mapping

from .business_case_inventory import CANONICAL_SLUGS
from .business_case_type_migration import FROZEN_LEGACY_CHOICES


Operation = str

CASE_CREATE_FIELDS = (
    "NacCaseId",
    "Aktenzeichen",
    "Vorgangstyp",
    "VorgangstypId",
    "Status",
    "NotarTeam",
    "Vertraulichkeitsstufe",
    "NacWorkflowVersion",
    "KgVersion",
)
CASE_STATUS_UPDATE_FIELDS = ("Status",)
TASK_CREATE_REQUIRED_FIELDS = (
    "NacTaskId",
    "NacCaseId",
    "BpmnStepCode",
    "Status",
    "RequiresNotaryApproval",
)
TASK_CREATE_OPTIONAL_FIELDS = ("DueDate",)
TASK_UPDATE_FIELDS = (
    "Status",
    "DueDate",
    "RequiresNotaryApproval",
    "BlockedReason",
)
BACKFILL_FIELDS = ("VorgangstypId",)
OPERATIONS = (
    "case_create",
    "case_status_update",
    "task_create",
    "task_update",
    "business_case_type_backfill",
)

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ITEM_ID = re.compile(r"[1-9][0-9]{0,18}\Z")
_SAFE_VALUE = re.compile(r"[^\x00-\x1f\x7f]{1,256}\Z")
_ISO_8601_DATETIME = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}"
    r"(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})\Z"
)

_TEXT_MAX_LENGTH_BY_LIST = {
    "Akten": {
        "NacCaseId": 255,
        "Aktenzeichen": 255,
        "VorgangstypId": 128,
        "NacWorkflowVersion": 255,
        "KgVersion": 255,
    },
    "AufgabenFristen": {
        "NacTaskId": 255,
        "NacCaseId": 255,
        "BpmnStepCode": 255,
        "BlockedReason": 255,
    },
}
_TEXT_FIELDS = frozenset(
    field
    for fields in _TEXT_MAX_LENGTH_BY_LIST.values()
    for field in fields
)
_CHOICE_FIELDS_BY_LIST = {
    "Akten": {
        "Vorgangstyp": frozenset(FROZEN_LEGACY_CHOICES),
        "Status": frozenset(
            {
                "Entwurf",
                "InPrüfung",
                "Beurkundung",
                "Vollzug",
                "Abgeschlossen",
                "Pausiert",
            }
        ),
        "NotarTeam": frozenset({"NaC-Notar-01", "NaC-Notar-02"}),
        "Vertraulichkeitsstufe": frozenset({"Normal", "Sensibel", "Hoch"}),
    },
    "AufgabenFristen": {
        "Status": frozenset({"Offen", "InArbeit", "Blockiert", "Erledigt"}),
    },
}
_DATETIME_FIELDS = frozenset({"DueDate"})
_BOOLEAN_FIELDS = frozenset({"RequiresNotaryApproval"})


class MutationValidationError(ValueError):
    """Raised when a mutation is not inside the bounded S4b contract."""


@dataclass(frozen=True, slots=True)
class S5BackfillBinding:
    manifest_hash: str
    record_ref_hash: str
    operation_hash: str
    idempotency_key: str


@dataclass(frozen=True, slots=True, init=False)
class BusinessCaseTypeMutation:
    operation: Operation
    fields: Mapping[str, Any]
    item_id: str | None
    expected_etag: str | None
    dedupe_field: str | None
    s5_manifest_hash: str | None
    s5_record_ref_hash: str | None
    s5_operation_hash: str | None
    s5_idempotency_key: str | None
    mutation_id: str

    @classmethod
    def case_create(cls, fields: Mapping[str, Any]) -> BusinessCaseTypeMutation:
        normalized = _exact_fields(fields, CASE_CREATE_FIELDS, "case_create")
        legacy = _nonempty_string(normalized["Vorgangstyp"], "Vorgangstyp")
        canonical = _nonempty_string(
            normalized["VorgangstypId"], "VorgangstypId"
        )
        if legacy not in FROZEN_LEGACY_CHOICES or canonical != legacy:
            raise MutationValidationError(
                "case_create requires an exact legacy-mappable BusinessCaseType"
            )
        _validate_sharepoint_fields(normalized, list_name="Akten")
        return cls._new(
            operation="case_create",
            fields=normalized,
            dedupe_field="NacCaseId",
        )

    @classmethod
    def case_status_update(
        cls,
        *,
        item_id: str,
        expected_etag: str,
        fields: Mapping[str, Any],
    ) -> BusinessCaseTypeMutation:
        normalized = _exact_fields(
            fields, CASE_STATUS_UPDATE_FIELDS, "case_status_update"
        )
        _validate_sharepoint_fields(normalized, list_name="Akten")
        return cls._new(
            operation="case_status_update",
            fields=normalized,
            item_id=_item_id(item_id),
            expected_etag=_etag(expected_etag),
        )

    @classmethod
    def task_create(cls, fields: Mapping[str, Any]) -> BusinessCaseTypeMutation:
        supplied = set(fields)
        required = set(TASK_CREATE_REQUIRED_FIELDS)
        allowed = required | set(TASK_CREATE_OPTIONAL_FIELDS)
        if not required.issubset(supplied) or not supplied.issubset(allowed):
            raise MutationValidationError(
                "task_create field set is outside the exact allowlist"
            )
        order = TASK_CREATE_REQUIRED_FIELDS + tuple(
            field for field in TASK_CREATE_OPTIONAL_FIELDS if field in supplied
        )
        normalized = {field: fields[field] for field in order}
        _validate_sharepoint_fields(
            normalized, list_name="AufgabenFristen"
        )
        return cls._new(
            operation="task_create",
            fields=normalized,
            dedupe_field="NacTaskId",
        )

    @classmethod
    def task_update(
        cls,
        *,
        item_id: str,
        expected_etag: str,
        fields: Mapping[str, Any],
    ) -> BusinessCaseTypeMutation:
        supplied = set(fields)
        if not supplied or not supplied.issubset(TASK_UPDATE_FIELDS):
            raise MutationValidationError(
                "task_update field set is outside the exact allowlist"
            )
        normalized = {
            field: fields[field] for field in TASK_UPDATE_FIELDS if field in supplied
        }
        _validate_sharepoint_fields(
            normalized,
            list_name="AufgabenFristen",
            empty_string_fields=frozenset({"BlockedReason"}),
        )
        return cls._new(
            operation="task_update",
            fields=normalized,
            item_id=_item_id(item_id),
            expected_etag=_etag(expected_etag),
        )

    @classmethod
    def business_case_type_backfill(
        cls,
        *,
        item_id: str,
        expected_etag: str,
        business_case_type_id: str,
        s5_binding: S5BackfillBinding,
    ) -> BusinessCaseTypeMutation:
        target = _nonempty_string(
            business_case_type_id, "business_case_type_id"
        )
        if target not in CANONICAL_SLUGS:
            raise MutationValidationError(
                "backfill target must be a canonical BusinessCaseTypeId"
            )
        _validate_sharepoint_fields(
            {"VorgangstypId": target}, list_name="Akten"
        )
        etag = _etag(expected_etag)
        for name, value in {
            "S5 manifest hash": s5_binding.manifest_hash,
            "S5 record-ref hash": s5_binding.record_ref_hash,
            "S5 operation hash": s5_binding.operation_hash,
            "S5 idempotency key": s5_binding.idempotency_key,
        }.items():
            _sha256(value, name)
        expected_idempotency = canonical_hash(
            [
                s5_binding.manifest_hash,
                s5_binding.record_ref_hash,
                target,
                etag,
            ]
        )
        if s5_binding.idempotency_key != expected_idempotency:
            raise MutationValidationError("S5 idempotency key mismatch")
        s5_operation = {
            "record_ref_hash": s5_binding.record_ref_hash,
            "field": "VorgangstypId",
            "value": target,
            "if_match": etag,
            "idempotency_key": s5_binding.idempotency_key,
        }
        if s5_binding.operation_hash != canonical_hash(s5_operation):
            raise MutationValidationError("S5 operation hash mismatch")
        return cls._new(
            operation="business_case_type_backfill",
            fields={"VorgangstypId": target},
            item_id=_item_id(item_id),
            expected_etag=etag,
            s5_manifest_hash=s5_binding.manifest_hash,
            s5_record_ref_hash=s5_binding.record_ref_hash,
            s5_operation_hash=s5_binding.operation_hash,
            s5_idempotency_key=s5_binding.idempotency_key,
        )

    @classmethod
    def _new(
        cls,
        *,
        operation: Operation,
        fields: Mapping[str, Any],
        item_id: str | None = None,
        expected_etag: str | None = None,
        dedupe_field: str | None = None,
        s5_manifest_hash: str | None = None,
        s5_record_ref_hash: str | None = None,
        s5_operation_hash: str | None = None,
        s5_idempotency_key: str | None = None,
    ) -> BusinessCaseTypeMutation:
        if operation not in OPERATIONS:
            raise MutationValidationError("unknown mutation operation")
        normalized = dict(fields)
        identity = {
            "operation": operation,
            "fields": normalized,
            "item_id": item_id,
            "expected_etag": expected_etag,
            "dedupe_field": dedupe_field,
            "s5_manifest_hash": s5_manifest_hash,
            "s5_record_ref_hash": s5_record_ref_hash,
            "s5_operation_hash": s5_operation_hash,
            "s5_idempotency_key": s5_idempotency_key,
        }
        instance = object.__new__(cls)
        object.__setattr__(instance, "operation", operation)
        object.__setattr__(
            instance, "fields", MappingProxyType(normalized)
        )
        object.__setattr__(instance, "item_id", item_id)
        object.__setattr__(instance, "expected_etag", expected_etag)
        object.__setattr__(instance, "dedupe_field", dedupe_field)
        object.__setattr__(instance, "s5_manifest_hash", s5_manifest_hash)
        object.__setattr__(instance, "s5_record_ref_hash", s5_record_ref_hash)
        object.__setattr__(instance, "s5_operation_hash", s5_operation_hash)
        object.__setattr__(instance, "s5_idempotency_key", s5_idempotency_key)
        object.__setattr__(instance, "mutation_id", canonical_hash(identity))
        return instance


def mutation_snapshot(mutation: BusinessCaseTypeMutation) -> dict[str, Any]:
    return {
        "operation": mutation.operation,
        "fields": dict(mutation.fields),
        "item_id": mutation.item_id,
        "expected_etag": mutation.expected_etag,
        "dedupe_field": mutation.dedupe_field,
        "s5_manifest_hash": mutation.s5_manifest_hash,
        "s5_record_ref_hash": mutation.s5_record_ref_hash,
        "s5_operation_hash": mutation.s5_operation_hash,
        "s5_idempotency_key": mutation.s5_idempotency_key,
        "mutation_id": mutation.mutation_id,
    }


def revalidate_business_case_type_mutation(
    mutation: BusinessCaseTypeMutation,
) -> BusinessCaseTypeMutation:
    try:
        if mutation.operation == "case_create":
            canonical = BusinessCaseTypeMutation.case_create(mutation.fields)
        elif mutation.operation == "case_status_update":
            canonical = BusinessCaseTypeMutation.case_status_update(
                item_id=mutation.item_id or "",
                expected_etag=mutation.expected_etag or "",
                fields=mutation.fields,
            )
        elif mutation.operation == "task_create":
            canonical = BusinessCaseTypeMutation.task_create(mutation.fields)
        elif mutation.operation == "task_update":
            canonical = BusinessCaseTypeMutation.task_update(
                item_id=mutation.item_id or "",
                expected_etag=mutation.expected_etag or "",
                fields=mutation.fields,
            )
        elif mutation.operation == "business_case_type_backfill":
            canonical = BusinessCaseTypeMutation.business_case_type_backfill(
                item_id=mutation.item_id or "",
                expected_etag=mutation.expected_etag or "",
                business_case_type_id=str(
                    mutation.fields.get("VorgangstypId", "")
                ),
                s5_binding=S5BackfillBinding(
                    manifest_hash=mutation.s5_manifest_hash or "",
                    record_ref_hash=mutation.s5_record_ref_hash or "",
                    operation_hash=mutation.s5_operation_hash or "",
                    idempotency_key=mutation.s5_idempotency_key or "",
                ),
            )
        else:
            raise MutationValidationError("unknown mutation operation")
    except (AttributeError, TypeError, KeyError) as exc:
        raise MutationValidationError("mutation canonical revalidation failed") from exc
    if mutation_snapshot(mutation) != mutation_snapshot(canonical):
        raise MutationValidationError("mutation canonical snapshot drift")
    return canonical

def canonical_hash(value: Any) -> str:
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MutationValidationError("value is not canonical JSON") from exc
    return hashlib.sha256(payload).hexdigest()


def _exact_fields(
    fields: Mapping[str, Any],
    expected: tuple[str, ...],
    operation: str,
) -> dict[str, Any]:
    if not isinstance(fields, Mapping) or set(fields) != set(expected):
        raise MutationValidationError(
            f"{operation} field set is outside the exact allowlist"
        )
    return {field: fields[field] for field in expected}


def _validate_sharepoint_fields(
    fields: Mapping[str, Any],
    *,
    list_name: str,
    empty_string_fields: frozenset[str] = frozenset(),
) -> None:
    for field, value in fields.items():
        text_max_length = _TEXT_MAX_LENGTH_BY_LIST.get(list_name, {}).get(field)
        if text_max_length is not None:
            if value == "" and field in empty_string_fields:
                continue
            _bounded_text(value, field, max_length=text_max_length)
            continue
        if field in _CHOICE_FIELDS_BY_LIST.get(list_name, {}):
            _choice(value, field, list_name=list_name)
            continue
        if field in _DATETIME_FIELDS:
            _iso_8601_datetime(value, field)
            continue
        if field in _BOOLEAN_FIELDS:
            _require_bool(value, field)
            continue
        raise MutationValidationError(
            f"{field} is not provisioned for {list_name}"
        )


def _nonempty_string(value: Any, name: str) -> str:
    if type(value) is not str or _SAFE_VALUE.fullmatch(value) is None:
        raise MutationValidationError(f"{name} must be a bounded nonempty string")
    return value


def _bounded_text(value: Any, name: str, *, max_length: int) -> str:
    normalized = _nonempty_string(value, name)
    if len(normalized) > max_length:
        raise MutationValidationError(
            f"{name} exceeds the provisioned text maxLength {max_length}"
        )
    return normalized


def _require_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise MutationValidationError(f"{name} must be boolean")
    return value


def _choice(value: Any, name: str, *, list_name: str) -> str:
    normalized = _nonempty_string(value, name)
    choices = _CHOICE_FIELDS_BY_LIST.get(list_name, {}).get(name)
    if choices is None or normalized not in choices:
        raise MutationValidationError(
            f"{name} must be a provisioned {list_name} choice"
        )
    return normalized


def _iso_8601_datetime(value: Any, name: str) -> str:
    if type(value) is not str or _ISO_8601_DATETIME.fullmatch(value) is None:
        raise MutationValidationError(
            f"{name} must be an ISO-8601 date-time with timezone"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MutationValidationError(
            f"{name} must be an ISO-8601 date-time with timezone"
        ) from exc
    if parsed.tzinfo is None:
        raise MutationValidationError(
            f"{name} must be an ISO-8601 date-time with timezone"
        )
    return value


def _item_id(value: Any) -> str:
    if type(value) is not str or _ITEM_ID.fullmatch(value) is None:
        raise MutationValidationError("item_id must be a positive decimal identifier")
    return value


def _etag(value: Any) -> str:
    return _nonempty_string(value, "expected_etag")


def _sha256(value: Any, name: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise MutationValidationError(f"{name} must be lowercase sha256")
    return value
