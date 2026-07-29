from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping, Protocol

from notary_kg.business_case_type_mutation import canonical_hash


S4D_READY_OFFLINE = "S4D_READY_OFFLINE"
S4D_LIVE_BLOCKED = "BLOCKED_PENDING_OWNER_GATED_PRODUCTION_ADAPTERS"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")
_OWNER_APPROVAL = re.compile(r"owner-approval-v1-([0-9a-f]{64})\Z")
MAX_IDENTITY_READBACK_AGE_SECONDS = 300
MAX_IDENTITY_READBACK_FUTURE_SKEW_SECONDS = 30


class LiveWriteGateBlocked(PermissionError):
    """Raised before credentials when an S4d binding is not exact."""


@dataclass(frozen=True, slots=True)
class LiveWriteApprovalAttestation:
    workspace_id: str
    commit_sha: str
    tree_sha: str
    domain_contract_sha256: str
    verification_contract_sha256: str
    plan_binding_sha256: str
    toolchain_sha256: str
    step_sequence_sha256: str
    evidence_policy_sha256: str
    target_binding_sha256: str
    write_principal_binding_sha256: str
    bff_principal_binding_sha256: str
    owner_verifier_binding_sha256: str
    owner_allowlist_sha256: str
    inspection_principal_binding_sha256: str
    owner_comment_sha256: str
    approval_ref: str


@dataclass(frozen=True, slots=True)
class OwnerApprovalVerification:
    source: str
    issue_ref: str
    owner_comment_sha256: str
    owner_principal_binding_sha256: str
    verifier_principal_binding_sha256: str
    owner_allowlist_sha256: str
    observed_at: str
    verified: bool


@dataclass(frozen=True, slots=True)
class WriteIdentityContext:
    workspace_id: str
    site_binding_sha256: str
    write_principal_binding_sha256: str
    write_graph_permissions: tuple[str, ...]
    write_site_roles: tuple[str, ...]
    bff_principal_binding_sha256: str
    bff_graph_permissions: tuple[str, ...]
    bff_site_roles: tuple[str, ...]
    broader_write_graph_roles: tuple[str, ...] = ()
    broader_bff_graph_roles: tuple[str, ...] = ()
    inspection_source: str = ""
    inspection_observed_at: str = ""
    inspection_principal_binding_sha256: str = ""
    inspection_approval_sha256: str = ""


class OwnerApprovalVerifierPort(Protocol):
    def verify(
        self,
        attestation: LiveWriteApprovalAttestation,
        *,
        expected: Mapping[str, str],
    ) -> OwnerApprovalVerification: ...


class WriteIdentityInspectionPort(Protocol):
    def readback(self) -> WriteIdentityContext: ...


class WriteIdentityFactoryPort(Protocol):
    def build(self, context: WriteIdentityContext): ...


def build_unverified_live_write_approval_attestation(
    *,
    workspace_id: str,
    commit_sha: str,
    tree_sha: str,
    domain_contract_sha256: str,
    verification_contract_sha256: str,
    plan_binding_sha256: str,
    toolchain_sha256: str,
    step_sequence_sha256: str,
    evidence_policy_sha256: str,
    target_binding_sha256: str,
    write_principal_binding_sha256: str,
    bff_principal_binding_sha256: str,
    owner_verifier_binding_sha256: str,
    owner_allowlist_sha256: str,
    inspection_principal_binding_sha256: str,
) -> LiveWriteApprovalAttestation:
    """Build an offline candidate; a verifier must still attest it."""
    values = {
        "workspace_id": workspace_id,
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "domain_contract_sha256": domain_contract_sha256,
        "verification_contract_sha256": verification_contract_sha256,
        "plan_binding_sha256": plan_binding_sha256,
        "toolchain_sha256": toolchain_sha256,
        "step_sequence_sha256": step_sequence_sha256,
        "evidence_policy_sha256": evidence_policy_sha256,
        "target_binding_sha256": target_binding_sha256,
        "write_principal_binding_sha256": write_principal_binding_sha256,
        "bff_principal_binding_sha256": bff_principal_binding_sha256,
        "owner_verifier_binding_sha256": owner_verifier_binding_sha256,
        "owner_allowlist_sha256": owner_allowlist_sha256,
        "inspection_principal_binding_sha256": (
            inspection_principal_binding_sha256
        ),
    }
    _validate_attestation_fields(values)
    owner_comment_sha256 = canonical_hash(
        {"schema_version": "nac.s4d-owner-comment/v0.1", **values}
    )
    approval_ref = f"owner-approval-v1-{owner_comment_sha256}"
    return LiveWriteApprovalAttestation(
        **values,
        owner_comment_sha256=owner_comment_sha256,
        approval_ref=approval_ref,
    )


def verify_live_write_owner_approval(
    attestation: LiveWriteApprovalAttestation,
    *,
    expected: Mapping[str, str],
    verifier: OwnerApprovalVerifierPort,
) -> LiveWriteApprovalAttestation:
    if not isinstance(attestation, LiveWriteApprovalAttestation):
        raise LiveWriteGateBlocked("owner attestation type is invalid")
    values = asdict(attestation)
    _validate_attestation_fields(values)
    allowed_expected = frozenset(values) - {
        "owner_comment_sha256",
        "approval_ref",
    }
    if frozenset(expected) != allowed_expected:
        raise LiveWriteGateBlocked("expected owner binding fields are invalid")
    for field in sorted(allowed_expected):
        if values[field] != expected[field]:
            raise LiveWriteGateBlocked(f"owner binding drift: {field}")
    expected_comment = canonical_hash(
        {
            "schema_version": "nac.s4d-owner-comment/v0.1",
            **{field: values[field] for field in sorted(allowed_expected)},
        }
    )
    if (
        values["owner_comment_sha256"] != expected_comment
        or values["approval_ref"]
        != f"owner-approval-v1-{expected_comment}"
    ):
        raise LiveWriteGateBlocked("owner comment binding drift")
    verification = verifier.verify(attestation, expected=expected)
    if not isinstance(verification, OwnerApprovalVerification):
        raise LiveWriteGateBlocked("owner verification type is invalid")
    if (
        verification.source != "github_issue_owner_comment"
        or verification.issue_ref
        != "https://github.com/notariat8/NaC/issues/700"
        or verification.owner_comment_sha256
        != attestation.owner_comment_sha256
        or verification.verifier_principal_binding_sha256
        != attestation.owner_verifier_binding_sha256
        or verification.owner_allowlist_sha256
        != attestation.owner_allowlist_sha256
        or verification.verified is not True
        or not _is_sha256(verification.owner_principal_binding_sha256)
    ):
        raise LiveWriteGateBlocked("owner approval verification failed")
    _utc_seconds(verification.observed_at)
    return attestation


def validate_write_identity_context(
    context: WriteIdentityContext,
    *,
    workspace_id: str,
    site_binding_sha256: str,
    write_principal_binding_sha256: str,
    bff_principal_binding_sha256: str,
    inspection_principal_binding_sha256: str,
    inspection_approval_sha256: str,
    now: datetime | None = None,
) -> WriteIdentityContext:
    if not isinstance(context, WriteIdentityContext):
        raise LiveWriteGateBlocked("identity readback type is invalid")
    if context.workspace_id != workspace_id:
        raise LiveWriteGateBlocked("identity workspace binding drift")
    for name, actual, expected in (
        ("site", context.site_binding_sha256, site_binding_sha256),
        (
            "write principal",
            context.write_principal_binding_sha256,
            write_principal_binding_sha256,
        ),
        (
            "BFF principal",
            context.bff_principal_binding_sha256,
            bff_principal_binding_sha256,
        ),
    ):
        if not _is_sha256(actual) or actual != expected:
            raise LiveWriteGateBlocked(f"identity {name} binding drift")
    if (
        context.write_principal_binding_sha256
        == context.bff_principal_binding_sha256
    ):
        raise LiveWriteGateBlocked("write and BFF principals must differ")
    if context.write_graph_permissions != ("Sites.Selected",):
        raise LiveWriteGateBlocked("write Graph permission drift")
    if context.write_site_roles != ("write",):
        raise LiveWriteGateBlocked("write site role drift")
    if context.bff_graph_permissions != ("Sites.Selected",):
        raise LiveWriteGateBlocked("BFF Graph permission drift")
    if context.bff_site_roles != ("read",):
        raise LiveWriteGateBlocked("BFF site role drift")
    if context.broader_write_graph_roles or context.broader_bff_graph_roles:
        raise LiveWriteGateBlocked("broader Graph role detected")
    if (
        context.inspection_source
        != "synthetic-offline-owner-bound-readback"
        or context.inspection_principal_binding_sha256
        != inspection_principal_binding_sha256
        or context.inspection_approval_sha256
        != inspection_approval_sha256
    ):
        raise LiveWriteGateBlocked("identity inspection provenance drift")
    observed_at = _utc_seconds(context.inspection_observed_at)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise LiveWriteGateBlocked("identity validation clock is invalid")
    current = current.astimezone(timezone.utc)
    if observed_at > current + timedelta(
        seconds=MAX_IDENTITY_READBACK_FUTURE_SKEW_SECONDS
    ):
        raise LiveWriteGateBlocked(
            "identity inspection timestamp is in the future"
        )
    if current - observed_at > timedelta(
        seconds=MAX_IDENTITY_READBACK_AGE_SECONDS
    ):
        raise LiveWriteGateBlocked("identity inspection readback is stale")
    return context


def _validate_attestation_fields(values: Mapping[str, str]) -> None:
    if values.get("workspace_id") != "notary_team_01":
        raise LiveWriteGateBlocked("workspace is outside the S4d allowlist")
    for field in ("commit_sha", "tree_sha"):
        value = values.get(field)
        if type(value) is not str or _GIT_SHA.fullmatch(value) is None:
            raise LiveWriteGateBlocked(f"{field} is invalid")
    for field in (
        "domain_contract_sha256",
        "verification_contract_sha256",
        "plan_binding_sha256",
        "toolchain_sha256",
        "step_sequence_sha256",
        "evidence_policy_sha256",
        "target_binding_sha256",
        "write_principal_binding_sha256",
        "bff_principal_binding_sha256",
        "owner_verifier_binding_sha256",
        "owner_allowlist_sha256",
        "inspection_principal_binding_sha256",
        "owner_comment_sha256",
    ):
        if field in values and not _is_sha256(values[field]):
            raise LiveWriteGateBlocked(f"{field} is invalid")
    if "approval_ref" in values:
        approval_ref = values["approval_ref"]
        if (
            type(approval_ref) is not str
            or _OWNER_APPROVAL.fullmatch(approval_ref) is None
        ):
            raise LiveWriteGateBlocked("approval_ref is invalid")


def _is_sha256(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None



def _utc_seconds(value: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise LiveWriteGateBlocked("inspection timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LiveWriteGateBlocked("inspection timestamp is invalid") from exc
    if parsed.microsecond != 0:
        raise LiveWriteGateBlocked("inspection timestamp is invalid")
    return parsed.astimezone(timezone.utc)
