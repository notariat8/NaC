from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType
from uuid import UUID

from .synthetic_workspace_graph import SYNTHETIC_SITE_ID


PERSON_BINDINGS_SCHEMA = "nac.sharepoint-person-bindings/v1"
MAX_PERSON_BINDINGS = 128
MAX_BINDINGS_JSON_BYTES = 32_768
_INVALID = "SharePoint person bindings are invalid"


def _subject_id(value: object) -> str:
    if type(value) is not str or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ):
        raise ValueError(_INVALID)
    if UUID(value).int == 0:
        raise ValueError(_INVALID)
    return value.lower()


def canonical_lookup_id(value: object) -> str:
    if (
        type(value) is not str
        or not re.fullmatch(r"[1-9][0-9]{0,9}", value)
        or int(value) > 2_147_483_647
    ):
        raise ValueError(_INVALID)
    return value


@dataclass(frozen=True, slots=True, repr=False)
class SharePointPersonBindings:
    """Private operator-verified identity data, never a role/assignment grant.

    The composition root supplies this trusted runtime configuration. It is
    not accepted from request headers, DTOs, usernames or optional JWT claims.
    """

    tenant_id: str
    site_id: str
    subjects: Mapping[str, str] = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.tenant_id) is not str
            or not self.tenant_id
            or self.tenant_id != self.tenant_id.strip()
            or len(self.tenant_id) > 256
            or self.site_id != SYNTHETIC_SITE_ID
            or not isinstance(self.subjects, Mapping)
            or not 1 <= len(self.subjects) <= MAX_PERSON_BINDINGS
        ):
            raise ValueError(_INVALID)
        normalized: dict[str, str] = {}
        for subject, lookup in self.subjects.items():
            canonical = _subject_id(subject)
            person = canonical_lookup_id(lookup)
            if canonical in normalized or person in normalized.values():
                raise ValueError(_INVALID)
            normalized[canonical] = person
        object.__setattr__(self, "subjects", MappingProxyType(normalized))

    def resolve(self, *, tenant_id: str, site_id: str, subject_id: str) -> str | None:
        if tenant_id != self.tenant_id or site_id != self.site_id:
            return None
        try:
            return self.subjects.get(_subject_id(subject_id))
        except ValueError:
            return None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(_INVALID)
        result[key] = value
    return result


def parse_person_bindings(value: object, *, expected_tenant_id: str) -> SharePointPersonBindings:
    """Parse a bounded, closed-schema private runtime value without IO."""
    try:
        if type(value) is not str or len(value.encode("utf-8")) > MAX_BINDINGS_JSON_BYTES:
            raise ValueError(_INVALID)
        payload = json.loads(value, object_pairs_hook=_unique_object)
        if (
            type(payload) is not dict
            or set(payload) != {"schema_version", "tenant_id", "site_id", "subjects"}
            or payload["schema_version"] != PERSON_BINDINGS_SCHEMA
            or payload["tenant_id"] != expected_tenant_id
            or type(payload["subjects"]) is not list
            or not 1 <= len(payload["subjects"]) <= MAX_PERSON_BINDINGS
        ):
            raise ValueError(_INVALID)
        subjects: dict[str, str] = {}
        for entry in payload["subjects"]:
            if type(entry) is not dict or set(entry) != {"subject_id", "lookup_id"}:
                raise ValueError(_INVALID)
            subject = _subject_id(entry["subject_id"])
            if subject in subjects:
                raise ValueError(_INVALID)
            subjects[subject] = canonical_lookup_id(entry["lookup_id"])
        return SharePointPersonBindings(
            tenant_id=payload["tenant_id"], site_id=payload["site_id"], subjects=subjects
        )
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise ValueError(_INVALID) from None
