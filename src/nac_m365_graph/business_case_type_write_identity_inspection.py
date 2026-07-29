from __future__ import annotations

from dataclasses import dataclass
import re
from typing import NoReturn, Protocol
from uuid import UUID

from notary_kg.business_case_type_mutation import canonical_hash


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ROLE_NAME = re.compile(r"[A-Za-z][A-Za-z0-9.]{0,127}\Z")
_SITE_ROLE = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,63}\Z")
_SITES_SELECTED = ("Sites.Selected",)
_WRITER_SITE_ROLE = ("write",)
_BFF_SITE_ROLE = ("read",)


class IdentityInspectionError(PermissionError):
    """Stable, redacted S4g identity-inspection failure."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class EntraPrincipalSnapshot:
    app_id: str
    service_principal_object_id: str
    graph_application_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EntraPrincipalReference:
    app_id: str
    service_principal_object_id: str


@dataclass(frozen=True, slots=True)
class SiteRoleAssignmentSnapshot:
    service_principal_object_id: str
    roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BusinessCaseTypeWriteIdentitySnapshot:
    """Current-state values supplied by an injected read-only port."""

    site_binding_sha256: str
    provisioner: EntraPrincipalSnapshot
    writer: EntraPrincipalSnapshot
    bff: EntraPrincipalSnapshot
    writer_site_assignment: SiteRoleAssignmentSnapshot
    bff_site_assignment: SiteRoleAssignmentSnapshot
    business_writer: EntraPrincipalReference
    write_token_source: EntraPrincipalReference


@dataclass(frozen=True, slots=True)
class ValidatedBusinessCaseTypeWriteIdentity:
    """Redacted validation result suitable for an S4g envelope."""

    schema_version: str
    site_binding_sha256: str
    provisioner_principal_binding_sha256: str
    writer_principal_binding_sha256: str
    bff_principal_binding_sha256: str
    identity_inspection_binding_sha256: str
    writer_graph_application_roles: tuple[str, ...]
    writer_site_roles: tuple[str, ...]
    bff_graph_application_roles: tuple[str, ...]
    bff_site_roles: tuple[str, ...]
    principals_pairwise_distinct: bool
    business_writer_is_writer: bool
    write_token_source_is_writer: bool
    provisioner_is_business_writer: bool
    provisioner_is_write_token_source: bool


class IdentityInspectionSnapshotPort(Protocol):
    def readback(self) -> BusinessCaseTypeWriteIdentitySnapshot: ...


class SnapshotIdentityInspectionPort:
    """In-memory read-only port for injected snapshots and offline tests."""

    def __init__(self, snapshot: BusinessCaseTypeWriteIdentitySnapshot) -> None:
        self._snapshot = snapshot

    def readback(self) -> BusinessCaseTypeWriteIdentitySnapshot:
        return self._snapshot


class BusinessCaseTypeWriteIdentityInspectionAdapter:
    """Validate one injected readback without credentials or network access."""

    def __init__(self, port: IdentityInspectionSnapshotPort) -> None:
        self._port = port

    def inspect(self) -> ValidatedBusinessCaseTypeWriteIdentity:
        try:
            snapshot = self._port.readback()
        except Exception:
            raise IdentityInspectionError(
                "identity_snapshot_unavailable"
            ) from None
        return validate_business_case_type_write_identity_snapshot(snapshot)

    def readback(self) -> ValidatedBusinessCaseTypeWriteIdentity:
        """Protocol-friendly alias for composition boundaries."""
        return self.inspect()


def validate_business_case_type_write_identity_snapshot(
    snapshot: BusinessCaseTypeWriteIdentitySnapshot,
) -> ValidatedBusinessCaseTypeWriteIdentity:
    """Fail closed unless all S4g identity and permission invariants hold."""
    if type(snapshot) is not BusinessCaseTypeWriteIdentitySnapshot:
        _fail("identity_snapshot_type_invalid")

    principals = (snapshot.provisioner, snapshot.writer, snapshot.bff)
    if any(type(value) is not EntraPrincipalSnapshot for value in principals):
        _fail("entra_principal_snapshot_type_invalid")
    assignments = (
        snapshot.writer_site_assignment,
        snapshot.bff_site_assignment,
    )
    if any(
        type(value) is not SiteRoleAssignmentSnapshot
        for value in assignments
    ):
        _fail("site_role_assignment_snapshot_type_invalid")
    references = (snapshot.business_writer, snapshot.write_token_source)
    if any(
        type(value) is not EntraPrincipalReference
        for value in references
    ):
        _fail("entra_principal_reference_type_invalid")
    if not _is_sha256(snapshot.site_binding_sha256):
        _fail("site_binding_invalid")

    for principal in principals:
        _validate_principal(principal)
    for assignment in assignments:
        _validate_site_assignment(assignment)
    for reference in references:
        _validate_reference(reference)

    if any(
        principal.app_id == principal.service_principal_object_id
        for principal in principals
    ):
        _fail("entra_identifier_namespace_collision")

    app_ids = tuple(principal.app_id for principal in principals)
    if len(set(app_ids)) != len(app_ids):
        _fail("entra_app_ids_not_pairwise_distinct")
    object_ids = tuple(
        principal.service_principal_object_id for principal in principals
    )
    if len(set(object_ids)) != len(object_ids):
        _fail("service_principal_ids_not_pairwise_distinct")
    if not set(app_ids).isdisjoint(object_ids):
        _fail("entra_identifier_namespace_collision")

    if snapshot.writer.graph_application_roles != _SITES_SELECTED:
        _fail("writer_graph_roles_not_exact")
    if snapshot.writer_site_assignment.roles != _WRITER_SITE_ROLE:
        _fail("writer_site_role_not_exact")
    if snapshot.bff.graph_application_roles != _SITES_SELECTED:
        _fail("bff_graph_roles_not_exact")
    if snapshot.bff_site_assignment.roles != _BFF_SITE_ROLE:
        _fail("bff_site_role_not_exact")
    if (
        snapshot.writer_site_assignment.service_principal_object_id
        != snapshot.writer.service_principal_object_id
    ):
        _fail("writer_site_assignment_principal_mismatch")
    if (
        snapshot.bff_site_assignment.service_principal_object_id
        != snapshot.bff.service_principal_object_id
    ):
        _fail("bff_site_assignment_principal_mismatch")

    if len(set(snapshot.provisioner.graph_application_roles)) != len(
        snapshot.provisioner.graph_application_roles
    ):
        _fail("graph_application_roles_invalid")

    writer_reference = _reference_for(snapshot.writer)
    if snapshot.business_writer != writer_reference:
        _fail("business_writer_not_bound_to_writer")
    if snapshot.write_token_source != writer_reference:
        _fail("write_token_source_not_bound_to_writer")

    provisioner_binding = entra_principal_binding_sha256(
        snapshot.provisioner
    )
    writer_binding = entra_principal_binding_sha256(snapshot.writer)
    bff_binding = entra_principal_binding_sha256(snapshot.bff)
    inspection_binding = canonical_hash(
        {
            "schema_version": "nac.s4g-identity-inspection-binding/v0.1",
            "site_binding_sha256": snapshot.site_binding_sha256,
            "principals": {
                "provisioner": _principal_payload(snapshot.provisioner),
                "writer": _principal_payload(snapshot.writer),
                "bff": _principal_payload(snapshot.bff),
            },
            "site_assignments": {
                "writer": _site_assignment_payload(
                    snapshot.writer_site_assignment
                ),
                "bff": _site_assignment_payload(
                    snapshot.bff_site_assignment
                ),
            },
            "business_writer": _reference_payload(
                snapshot.business_writer
            ),
            "write_token_source": _reference_payload(
                snapshot.write_token_source
            ),
        }
    )
    return ValidatedBusinessCaseTypeWriteIdentity(
        schema_version="nac.s4g-identity-inspection/v0.1",
        site_binding_sha256=snapshot.site_binding_sha256,
        provisioner_principal_binding_sha256=provisioner_binding,
        writer_principal_binding_sha256=writer_binding,
        bff_principal_binding_sha256=bff_binding,
        identity_inspection_binding_sha256=inspection_binding,
        writer_graph_application_roles=_SITES_SELECTED,
        writer_site_roles=_WRITER_SITE_ROLE,
        bff_graph_application_roles=_SITES_SELECTED,
        bff_site_roles=_BFF_SITE_ROLE,
        principals_pairwise_distinct=True,
        business_writer_is_writer=True,
        write_token_source_is_writer=True,
        provisioner_is_business_writer=False,
        provisioner_is_write_token_source=False,
    )


def entra_principal_binding_sha256(
    principal: EntraPrincipalSnapshot | EntraPrincipalReference,
) -> str:
    """Hash-bind an app registration to its service-principal object."""
    if type(principal) is EntraPrincipalSnapshot:
        _validate_principal(principal)
    elif type(principal) is EntraPrincipalReference:
        _validate_reference(principal)
    else:
        _fail("entra_principal_type_invalid")
    return canonical_hash(
        {
            "schema_version": "nac.s4g-entra-principal-binding/v0.1",
            **_reference_payload(principal),
        }
    )


def _validate_principal(principal: EntraPrincipalSnapshot) -> None:
    _validate_identifier(principal.app_id)
    _validate_identifier(principal.service_principal_object_id)
    _validate_string_tuple(
        principal.graph_application_roles,
        pattern=_ROLE_NAME,
        code="graph_application_roles_invalid",
    )


def _validate_reference(reference: EntraPrincipalReference) -> None:
    _validate_identifier(reference.app_id)
    _validate_identifier(reference.service_principal_object_id)


def _validate_site_assignment(
    assignment: SiteRoleAssignmentSnapshot,
) -> None:
    _validate_identifier(assignment.service_principal_object_id)
    _validate_string_tuple(
        assignment.roles,
        pattern=_SITE_ROLE,
        code="site_roles_invalid",
    )


def _validate_identifier(value: object) -> None:
    if type(value) is not str:
        _fail("entra_identifier_invalid")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError):
        _fail("entra_identifier_invalid")
    if parsed.int == 0 or str(parsed) != value:
        _fail("entra_identifier_invalid")


def _validate_string_tuple(
    values: object,
    *,
    pattern: re.Pattern[str],
    code: str,
) -> None:
    if (
        type(values) is not tuple
        or any(
            type(value) is not str or pattern.fullmatch(value) is None
            for value in values
        )
    ):
        _fail(code)


def _principal_payload(principal: EntraPrincipalSnapshot) -> dict[str, object]:
    return {
        **_reference_payload(principal),
        "graph_application_roles": sorted(
            principal.graph_application_roles
        ),
    }


def _reference_payload(
    principal: EntraPrincipalSnapshot | EntraPrincipalReference,
) -> dict[str, str]:
    return {
        "app_id": principal.app_id,
        "service_principal_object_id": (
            principal.service_principal_object_id
        ),
    }


def _site_assignment_payload(
    assignment: SiteRoleAssignmentSnapshot,
) -> dict[str, object]:
    return {
        "service_principal_object_id": (
            assignment.service_principal_object_id
        ),
        "roles": sorted(assignment.roles),
    }


def _reference_for(
    principal: EntraPrincipalSnapshot,
) -> EntraPrincipalReference:
    return EntraPrincipalReference(
        app_id=principal.app_id,
        service_principal_object_id=principal.service_principal_object_id,
    )


def _is_sha256(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _fail(code: str) -> NoReturn:
    raise IdentityInspectionError(code)
