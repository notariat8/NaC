from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence


APPROVAL_KEYS = frozenset(
    {
        "owner-approved",
        "expected_activation_sha256",
        "approved_commit_sha",
        "approved_tree_sha",
        "toolchain_attestations_sha256",
        "target_binding_sha256",
        "permission_boundary_sha256",
        "step_sequence_sha256",
        "no_automatic_rollback_or_deletion",
    }
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40}$")


def approval_binding_sha256(value: Any) -> str:
    """Hash the exact compact JSON representation used by owner approvals."""

    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_owner_approval_payload(
    *,
    activation_hash: str,
    approved_commit: str,
    approved_tree: str,
    toolchain_attestations_sha256: str,
    bindings: Mapping[str, Any],
    permission_boundary: Mapping[str, Any],
    step_ids: Sequence[str],
) -> dict[str, Any]:
    _require_digest(activation_hash, "activation_hash")
    _require_git_object(approved_commit, "approved_commit")
    _require_git_object(approved_tree, "approved_tree")
    _require_digest(
        toolchain_attestations_sha256,
        "toolchain_attestations_sha256",
    )
    if not isinstance(bindings, Mapping):
        raise ValueError("bindings must be a mapping")
    if not isinstance(permission_boundary, Mapping):
        raise ValueError("permission_boundary must be a mapping")
    if isinstance(step_ids, (str, bytes)) or not all(
        isinstance(step_id, str) and step_id for step_id in step_ids
    ):
        raise ValueError("step_ids must contain non-empty strings")

    return {
        "owner-approved": True,
        "expected_activation_sha256": activation_hash,
        "approved_commit_sha": approved_commit,
        "approved_tree_sha": approved_tree,
        "toolchain_attestations_sha256": toolchain_attestations_sha256,
        "target_binding_sha256": approval_binding_sha256(bindings),
        "permission_boundary_sha256": approval_binding_sha256(
            permission_boundary
        ),
        "step_sequence_sha256": approval_binding_sha256(list(step_ids)),
        "no_automatic_rollback_or_deletion": True,
    }


def canonical_owner_comment_body(payload: Mapping[str, Any]) -> str:
    if set(payload) != APPROVAL_KEYS:
        raise ValueError("owner approval payload keys do not match the contract")
    return json.dumps(
        dict(payload),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def owner_comment_body_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _require_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")


def _require_git_object(value: str, label: str) -> None:
    if not isinstance(value, str) or _GIT_OBJECT_RE.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase Git object id")
