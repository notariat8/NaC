from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


MATTER_ACCESS_APPLY_POLICY_NEGATIVE_CASE_IDS = (
    "missing_reason",
    "expired_delegation",
    "workspace_scope_violation",
    "missing_cleanup",
    "audit_readback_missing",
)

GRANT_REQUEST_ALLOWED_ROLES = {"NotarVertretung", "SachbearbeitungVertretung", "NurLesen"}
GRANT_REQUEST_ALLOWED_STATUSES = {"Aktiv", "Abgelaufen", "Widerrufen"}


class MatterAccessApplyPolicyError(ValueError):
    """Raised when a deputy-grant apply request violates the fail-closed policy."""


def validate_grant_request_policy(
    arguments: dict[str, Any],
    *,
    generated_at: str | datetime | None = None,
    reject_expired: bool = False,
) -> list[str]:
    errors: list[str] = []
    reason = str(arguments.get("reason", "")).strip()
    if not reason:
        errors.append("grant_request reason must be non-empty")

    granted_role = str(arguments.get("granted_role", ""))
    if granted_role not in GRANT_REQUEST_ALLOWED_ROLES:
        errors.append("grant_request granted_role is not allowed")

    status = str(arguments.get("status", ""))
    if status not in GRANT_REQUEST_ALLOWED_STATUSES:
        errors.append("grant_request status is not allowed")

    valid_from = _parse_utc_timestamp(str(arguments.get("valid_from", "")), "valid_from", errors)
    valid_until = _parse_utc_timestamp(str(arguments.get("valid_until", "")), "valid_until", errors)
    if valid_from is not None and valid_until is not None:
        if valid_until <= valid_from:
            errors.append("grant_request valid_until must be after valid_from")
        if reject_expired:
            reference = _reference_timestamp(generated_at, errors)
            if reference is not None and valid_until <= reference:
                errors.append("grant_request valid_until must be after apply timestamp")

    for field_name in ("grant_id", "case_id", "from_user", "to_user", "approved_by"):
        if not str(arguments.get(field_name, "")).strip():
            errors.append(f"grant_request {field_name} must be non-empty")
    return errors


def enforce_grant_request_policy(
    arguments: dict[str, Any],
    *,
    generated_at: str | datetime | None = None,
    reject_expired: bool = False,
) -> None:
    errors = validate_grant_request_policy(
        arguments,
        generated_at=generated_at,
        reject_expired=reject_expired,
    )
    if errors:
        raise MatterAccessApplyPolicyError("; ".join(errors))


def enforce_apply_pre_write_policy(
    provisioned_state: dict[str, Any],
    *,
    workspace_id: str,
    grant_arguments: dict[str, Any],
    audit_arguments: dict[str, Any],
    generated_at: str | datetime,
    cleanup_after: bool,
) -> dict[str, Any]:
    errors: list[str] = []
    workspace_known = _workspace_exists(provisioned_state, workspace_id)
    if not workspace_known:
        errors.append("matter-access apply workspace_id must resolve to one provisioned workspace")
    errors.extend(
        validate_grant_request_policy(
            grant_arguments,
            generated_at=generated_at,
            reject_expired=True,
        )
    )
    if not cleanup_after:
        errors.append("matter-access apply cleanup_after must be true")
    if str(audit_arguments.get("reason", "")).strip() != str(grant_arguments.get("reason", "")).strip():
        errors.append("matter-access apply audit_append reason must match grant_request reason")
    for field_name in ("event_id", "case_id", "timestamp", "action", "object_type", "object_id"):
        if not str(audit_arguments.get(field_name, "")).strip():
            errors.append(f"matter-access apply audit_append {field_name} must be non-empty")
    if str(audit_arguments.get("case_id", "")).strip() != str(grant_arguments.get("case_id", "")).strip():
        errors.append("matter-access apply audit_append case_id must match grant_request case_id")
    if str(audit_arguments.get("object_id", "")).strip() != str(grant_arguments.get("grant_id", "")).strip():
        errors.append("matter-access apply audit_append object_id must match grant_request grant_id")
    if errors:
        raise MatterAccessApplyPolicyError("; ".join(errors))
    return {
        "policy_enforced": True,
        "workspace_scope_validated": True,
        "grant_request_semantics_validated": True,
        "cleanup_required": True,
        "audit_append_required": True,
        "audit_reason_matches_grant_reason": True,
        "fail_closed_before_graph_write": True,
    }


def enforce_apply_readback_policy(*, grant_read_count: int, audit_read_count: int) -> dict[str, Any]:
    errors: list[str] = []
    if grant_read_count != 1:
        errors.append("matter-access apply grant_request readback must return exactly one synthetic item")
    if audit_read_count != 1:
        errors.append("matter-access apply audit_append readback must return exactly one synthetic item")
    if errors:
        raise MatterAccessApplyPolicyError("; ".join(errors))
    return {
        "grant_request_readback_required": True,
        "audit_append_readback_required": True,
        "readback_count_policy": "exactly_one_each",
    }


def enforce_apply_cleanup_policy(*, grant_after_count: int, audit_after_count: int) -> dict[str, Any]:
    errors: list[str] = []
    if grant_after_count != 0:
        errors.append("matter-access apply cleanup must remove the synthetic grant item")
    if audit_after_count != 0:
        errors.append("matter-access apply cleanup must remove the synthetic audit item")
    if errors:
        raise MatterAccessApplyPolicyError("; ".join(errors))
    return {
        "cleanup_readback_required": True,
        "cleanup_count_policy": "zero_after_delete",
    }


def _workspace_exists(provisioned_state: dict[str, Any], workspace_id: str) -> bool:
    for workspace in provisioned_state.get("workspaces", []):
        if isinstance(workspace, dict) and workspace.get("id") == workspace_id:
            return True
    return False


def _parse_utc_timestamp(value: str, field_name: str, errors: list[str]) -> datetime | None:
    if not value:
        errors.append(f"grant_request {field_name} must be set")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"grant_request {field_name} must be ISO-8601")
        return None
    if parsed.tzinfo is None:
        errors.append(f"grant_request {field_name} must include timezone")
        return None
    return parsed.astimezone(UTC)


def _reference_timestamp(value: str | datetime | None, errors: list[str]) -> datetime | None:
    if value is None:
        return datetime.now(UTC)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            errors.append("matter-access apply timestamp must include timezone")
            return None
        return value.astimezone(UTC)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append("matter-access apply timestamp must be ISO-8601")
        return None
    if parsed.tzinfo is None:
        errors.append("matter-access apply timestamp must include timezone")
        return None
    return parsed.astimezone(UTC)
