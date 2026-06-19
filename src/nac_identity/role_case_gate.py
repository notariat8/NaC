from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


ROLE_CASE_GATE_SCHEMA_VERSION = "nac.role-case-gate/v0.1"
ROLE_CASE_GATE_AUDIT_SCHEMA_VERSION = "nac.role-case-gate.audit/v0.1"
PROTECTED_STATUS_METADATA_SURFACE = "protected_status_metadata"
ROLE_CASE_GATE_REASON_CLASSES = (
    "session_missing",
    "session_revoked",
    "session_expired",
    "role_missing",
    "tenant_mismatch",
    "case_missing",
    "purpose_missing",
    "four_eyes_required",
)


def normalize_workspace_role_gate_context(*, role: str, role_gate_open: bool) -> dict[str, Any]:
    return {
        "status": "open" if role_gate_open is True else "closed",
        "role": role,
        "session_allowed": role_gate_open is True,
    }


def normalize_workspace_tenant_binding_context(*, tenant_bound: bool) -> dict[str, Any]:
    return {
        "status": "bound" if tenant_bound is True else "unbound",
        "tenant_authorized": tenant_bound is True,
    }


def normalize_workspace_case_binding_context(*, case_bound: bool) -> dict[str, Any]:
    return {
        "status": "bound" if case_bound is True else "unbound",
        "case_authorized": case_bound is True,
    }


def normalize_workspace_purpose_binding_context(*, purpose_bound: bool) -> dict[str, Any]:
    return {
        "status": "bound" if purpose_bound is True else "unbound",
        "purpose_allowed": purpose_bound is True,
    }


def evaluate_role_case_gate(
    *,
    session_validation: Mapping[str, Any] | None,
    role_gate: Mapping[str, Any] | None,
    tenant_context: Mapping[str, Any] | None,
    case_context: Mapping[str, Any] | None,
    purpose_context: Mapping[str, Any] | None,
    subject_matter_roles: Sequence[str],
    requires_four_eyes: bool = False,
    four_eyes_approval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the fail-closed gate before routes beyond protected start.

    The result intentionally contains only reason classes and booleans. It must
    not echo tenant hints, case identifiers, session IDs, claims, or callback
    values into browser-facing payloads.
    """

    session_status = str((session_validation or {}).get("status") or "")
    if session_status != "valid":
        return _closed(_session_reason(session_status))
    if not _session_allows_protected_start(session_validation or {}):
        return _closed("session_missing")

    role = str((role_gate or {}).get("role") or "")
    if (role_gate or {}).get("status") != "open" or role not in set(subject_matter_roles):
        return _closed("role_missing")

    if not _binding_allows(tenant_context, status_key="status", allowed_key="tenant_authorized"):
        return _closed("tenant_mismatch")
    if not _binding_allows(case_context, status_key="status", allowed_key="case_authorized"):
        return _closed("case_missing")
    if not _binding_allows(purpose_context, status_key="status", allowed_key="purpose_allowed"):
        return _closed("purpose_missing")
    if requires_four_eyes and not _four_eyes_approved(four_eyes_approval):
        return _closed("four_eyes_required")

    return {
        "schema_version": ROLE_CASE_GATE_SCHEMA_VERSION,
        "status": "open",
        "reason": "authorized",
        "allowed_surface": PROTECTED_STATUS_METADATA_SURFACE,
        "tenant_bound": True,
        "case_bound": True,
        "purpose_bound": True,
        "four_eyes_satisfied": not requires_four_eyes or _four_eyes_approved(four_eyes_approval),
        "full_workspace_opened": False,
        "mandate_data_loaded": False,
        "guardrails": _guardrails(),
        "audit_evidence": _audit_evidence(
            reason="authorized",
            session_valid=True,
            protected_start_allowed=True,
            subject_matter_role_matched=True,
            tenant_bound=True,
            case_bound=True,
            purpose_bound=True,
            four_eyes_satisfied=not requires_four_eyes or _four_eyes_approved(four_eyes_approval),
        ),
    }


def _closed(reason: str) -> dict[str, Any]:
    return {
        "schema_version": ROLE_CASE_GATE_SCHEMA_VERSION,
        "status": "closed",
        "reason": reason,
        "allowed_surface": "none",
        "tenant_bound": False,
        "case_bound": False,
        "purpose_bound": False,
        "four_eyes_satisfied": False,
        "full_workspace_opened": False,
        "mandate_data_loaded": False,
        "guardrails": _guardrails(),
        "audit_evidence": _audit_evidence(reason=reason),
    }


def _guardrails() -> dict[str, bool]:
    return {
        "contains_credentials": False,
        "tokens_returned": False,
        "claims_exposed": False,
        "callback_values_exposed": False,
        "session_identifier_exposed": False,
        "case_identifier_exposed": False,
        "tenant_identifier_exposed": False,
        "mandate_content_exposed": False,
    }


def _audit_evidence(
    *,
    reason: str,
    session_valid: bool = False,
    protected_start_allowed: bool = False,
    subject_matter_role_matched: bool = False,
    tenant_bound: bool = False,
    case_bound: bool = False,
    purpose_bound: bool = False,
    four_eyes_satisfied: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": ROLE_CASE_GATE_AUDIT_SCHEMA_VERSION,
        "status": "recorded",
        "reason_class": reason,
        "checks": {
            "session_valid": session_valid,
            "protected_start_allowed": protected_start_allowed,
            "subject_matter_role_matched": subject_matter_role_matched,
            "tenant_bound": tenant_bound,
            "case_bound": case_bound,
            "purpose_bound": purpose_bound,
            "four_eyes_satisfied": four_eyes_satisfied,
        },
        "redaction": {
            "contains_session_identifier": False,
            "contains_tenant_identifier": False,
            "contains_case_identifier": False,
            "contains_claim_values": False,
            "contains_email": False,
            "contains_provider_details": False,
            "contains_callback_values": False,
            "contains_mandate_content": False,
        },
    }


def _session_reason(status: str) -> str:
    if status == "revoked":
        return "session_revoked"
    if status == "expired":
        return "session_expired"
    return "session_missing"


def _session_allows_protected_start(session_validation: Mapping[str, Any]) -> bool:
    session = session_validation.get("session")
    if not isinstance(session, Mapping):
        return False
    if session.get("workspace_opened") is True:
        return False
    return session.get("protected_start_page_allowed") is True


def _binding_allows(context: Mapping[str, Any] | None, *, status_key: str, allowed_key: str) -> bool:
    if not isinstance(context, Mapping):
        return False
    return context.get(status_key) == "bound" and context.get(allowed_key) is True


def _four_eyes_approved(approval: Mapping[str, Any] | None) -> bool:
    return isinstance(approval, Mapping) and approval.get("status") == "approved"
