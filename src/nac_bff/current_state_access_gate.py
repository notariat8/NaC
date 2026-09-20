from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
import re
from typing import Any


GATE_CLOSED = "CURRENT_STATE_ACCESS_GATE_CLOSED"
BLOCKED_ACCOUNT_BINDING = "BLOCKED_ACCOUNT_BINDING"
BLOCKED_SINGLE_PRINCIPAL = "BLOCKED_SINGLE_PRINCIPAL"
_HEX40 = re.compile(r"[0-9a-f]{40}")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_PRODUCTION_SEAL = object()
_SYNTHETIC_SEAL = object()
BASE_MERGE_COMMIT = "80bf813375d7fc2ab292dfdbcc1db447fdb6684a"
BASE_MERGE_TREE = "007e277ca5643f7cb63355961fd0422d92fd4b87"


class CurrentStateAccessGateError(RuntimeError):
    def __init__(self, code: str, reason: str) -> None:
        super().__init__(f"{code}: {reason}")
        self.code = code
        self.reason = reason


@dataclass(frozen=True)
class GateInput:
    issue: int
    pr: int
    base_pr: int
    base_merge_commit: str
    base_tree: str
    head: str
    tree: str
    head_descends_from_base: bool
    resolver_sha256: str
    operator_account_id: str
    operator_principal_id: str
    authorized_account_id: str
    authorized_principal_id: str
    provider: str
    tenant_binding_sha256: str
    account_permission_sha256: str
    target_binding_sha256: str
    target_payload_sha256: str
    dpa_avv_binding_sha256: str
    contract_sha256: str
    toolchain_sha256: str
    approval_sha256: str
    run_nonce_sha256: str
    approval_mode: str
    four_eyes_satisfied: bool
    external_two_person_required: bool
    external_requirement_citation: str | None
    required_checks_successful: bool
    required_checks_sha256: str
    worktree_clean: bool
    credential_write_guard_active: bool
    evidence_root_binding_sha256: str


@dataclass(frozen=True)
class CurrentStateRunAuthorization:
    head: str
    tree: str
    account_id: str
    principal_id: str
    provider: str
    tenant_binding_sha256: str
    account_permission_sha256: str
    target_binding_sha256: str
    target_payload_sha256: str
    resolver_sha256: str
    dpa_avv_binding_sha256: str
    contract_sha256: str
    toolchain_sha256: str
    approval_sha256: str
    run_nonce_sha256: str
    required_checks_sha256: str
    evidence_root_binding_sha256: str
    authorization_sha256: str
    approval_mode: str = "OWNER_SOLO_APPROVAL"
    four_eyes_satisfied: bool = False
    scope: str = "issue748_current_state_access_read_only"
    _runtime_seal: object = field(default=None, repr=False, compare=False)

    def canonical_payload(self) -> dict[str, object]:
        return {
            "head": self.head,
            "tree": self.tree,
            "account_id": self.account_id,
            "principal_id": self.principal_id,
            "provider": self.provider,
            "tenant_binding_sha256": self.tenant_binding_sha256,
            "account_permission_sha256": self.account_permission_sha256,
            "target_binding_sha256": self.target_binding_sha256,
            "target_payload_sha256": self.target_payload_sha256,
            "resolver_sha256": self.resolver_sha256,
            "dpa_avv_binding_sha256": self.dpa_avv_binding_sha256,
            "contract_sha256": self.contract_sha256,
            "toolchain_sha256": self.toolchain_sha256,
            "approval_sha256": self.approval_sha256,
            "run_nonce_sha256": self.run_nonce_sha256,
            "required_checks_sha256": self.required_checks_sha256,
            "evidence_root_binding_sha256": self.evidence_root_binding_sha256,
            "approval_mode": self.approval_mode,
            "four_eyes_satisfied": self.four_eyes_satisfied,
            "scope": self.scope,
        }

    def verify_for_read(
        self,
        *,
        account_id: str,
        principal_id: str,
        target_binding_sha256: str,
        target_payload_sha256: str,
        evidence_binding_sha256: str,
    ) -> None:
        if (
            self._runtime_seal not in {_PRODUCTION_SEAL, _SYNTHETIC_SEAL}
            or account_id != self.account_id
            or principal_id != self.principal_id
            or target_binding_sha256 != self.target_binding_sha256
            or target_payload_sha256 != self.target_payload_sha256
            or evidence_binding_sha256 != self.authorization_sha256
            or not self.provider
            or self.authorization_sha256
            != _authorization_digest(self.canonical_payload())
            or self.approval_mode != "OWNER_SOLO_APPROVAL"
            or self.four_eyes_satisfied is not False
        ):
            raise CurrentStateAccessGateError(
                GATE_CLOSED, "per-read authorization binding mismatch"
            )


@dataclass(frozen=True)
class RunGateReceipt:
    authorization_sha256: str
    marker_sha256: str
    marker_name: str


def _authorization_digest(value: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _fail(reason: str, code: str = GATE_CLOSED) -> None:
    raise CurrentStateAccessGateError(code, reason)


def authorize_current_state_run(value: GateInput) -> CurrentStateRunAuthorization:
    del value
    _fail("production authorization requires protected composition")


def _authorize_protected_current_state_run(value: GateInput) -> CurrentStateRunAuthorization:
    """Seal only the already cross-checked protected composition input."""
    if (value.issue, value.pr, value.base_pr) != (748, 749, 747):
        _fail("issue or PR binding mismatch")
    if (
        value.base_merge_commit != BASE_MERGE_COMMIT
        or value.base_tree != BASE_MERGE_TREE
    ):
        _fail("approved PR 747 merge base mismatch")
    if not all(
        _HEX40.fullmatch(item)
        for item in (value.base_merge_commit, value.base_tree, value.head, value.tree)
    ) or not value.head_descends_from_base:
        _fail("post-merge Git binding mismatch")
    digest_values = (
        value.resolver_sha256,
        value.tenant_binding_sha256,
        value.account_permission_sha256,
        value.target_binding_sha256,
        value.target_payload_sha256,
        value.dpa_avv_binding_sha256,
        value.contract_sha256,
        value.toolchain_sha256,
        value.approval_sha256,
        value.run_nonce_sha256,
        value.required_checks_sha256,
        value.evidence_root_binding_sha256,
    )
    if not all(_HEX64.fullmatch(item) for item in digest_values):
        _fail("digest binding invalid")
    if (
        not value.required_checks_successful
        or not value.worktree_clean
        or not value.credential_write_guard_active
    ):
        _fail("pre-I/O safety gate not satisfied")
    if (
        value.provider != "microsoft"
        or not value.operator_account_id.startswith("microsoft:")
        or value.operator_account_id != value.authorized_account_id
    ):
        _fail("provider account binding mismatch", BLOCKED_ACCOUNT_BINDING)
    if value.operator_principal_id != value.authorized_principal_id:
        _fail("principal binding mismatch")
    if value.external_two_person_required:
        if not value.external_requirement_citation:
            _fail("external two-person requirement citation missing")
        _fail("only one qualified principal is bound", BLOCKED_SINGLE_PRINCIPAL)
    if (
        value.approval_mode != "OWNER_SOLO_APPROVAL"
        or value.four_eyes_satisfied is not False
    ):
        _fail("solo-owner approval binding invalid")
    payload = {
        "head": value.head,
        "tree": value.tree,
        "account_id": value.operator_account_id,
        "principal_id": value.operator_principal_id,
        "provider": value.provider,
        "tenant_binding_sha256": value.tenant_binding_sha256,
        "account_permission_sha256": value.account_permission_sha256,
        "target_binding_sha256": value.target_binding_sha256,
        "target_payload_sha256": value.target_payload_sha256,
        "resolver_sha256": value.resolver_sha256,
        "dpa_avv_binding_sha256": value.dpa_avv_binding_sha256,
        "contract_sha256": value.contract_sha256,
        "toolchain_sha256": value.toolchain_sha256,
        "approval_sha256": value.approval_sha256,
        "run_nonce_sha256": value.run_nonce_sha256,
        "required_checks_sha256": value.required_checks_sha256,
        "evidence_root_binding_sha256": value.evidence_root_binding_sha256,
        "approval_mode": value.approval_mode,
        "four_eyes_satisfied": value.four_eyes_satisfied,
        "scope": "issue748_current_state_access_read_only",
    }
    return CurrentStateRunAuthorization(
        **{key: payload[key] for key in (
            "head", "tree", "account_id", "principal_id", "provider",
            "tenant_binding_sha256", "account_permission_sha256",
            "target_binding_sha256", "target_payload_sha256", "resolver_sha256",
            "dpa_avv_binding_sha256", "contract_sha256",
            "toolchain_sha256", "approval_sha256", "run_nonce_sha256",
            "required_checks_sha256", "evidence_root_binding_sha256",
        )},
        authorization_sha256=_authorization_digest(payload),
        _runtime_seal=_PRODUCTION_SEAL,
    )


def authorize_synthetic_current_state_run(value: GateInput) -> CurrentStateRunAuthorization:
    """Create test-only capability for the fixed non-production fixture."""

    synthetic_target = _authorization_digest({"opaque": "bound"})
    if (
        value.operator_account_id not in {
            "microsoft:owner-primary", "microsoft:owner-secondary"
        }
        or value.operator_principal_id != "person:owner"
        or value.target_payload_sha256 != synthetic_target
    ):
        _fail("synthetic fixture binding invalid")
    sealed = _authorize_protected_current_state_run(value)
    return replace(sealed, _runtime_seal=_SYNTHETIC_SEAL)


def consume_current_state_run_gate(
    authorization: CurrentStateRunAuthorization,
    *,
    evidence_root: Path,
    backend: Any | None = None,
) -> RunGateReceipt:
    """Persist a non-reusable run marker before any provider port is created."""

    if authorization._runtime_seal is not _PRODUCTION_SEAL:
        _fail("unsealed run authorization")
    if not evidence_root.is_absolute():
        _fail("evidence root must be absolute")
    evidence_root_binding = hashlib.sha256(
        str(evidence_root.resolve()).encode("utf-8")
    ).hexdigest()
    if evidence_root_binding != authorization.evidence_root_binding_sha256:
        _fail("evidence root binding mismatch")
    if backend is None:
        from .activation_security_backend import get_platform_security_backend

        backend = get_platform_security_backend()
    session = None
    run_lock = None
    marker_name = f"issue748-{authorization.authorization_sha256}.consumed.json"
    marker_payload = json.dumps(
        {
            "schema_version": "nac.issue748-current-state-run-gate/v1",
            "authorization_sha256": authorization.authorization_sha256,
            "head": authorization.head,
            "tree": authorization.tree,
            "target_binding_sha256": authorization.target_binding_sha256,
            "run_nonce_sha256": authorization.run_nonce_sha256,
            "scope": authorization.scope,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        session = backend.open_secure_directory(
            evidence_root,
            create=False,
            require_current_owner=True,
            require_restrictive_dacl=True,
        )
        run_lock = backend.acquire_run_lock(authorization.authorization_sha256)
        snapshot = session.create_exclusive(marker_name, marker_payload)
        marker_sha256 = getattr(snapshot, "sha256", "")
        if not _HEX64.fullmatch(marker_sha256):
            _fail("run gate marker binding invalid")
        return RunGateReceipt(
            authorization_sha256=authorization.authorization_sha256,
            marker_sha256=marker_sha256,
            marker_name=marker_name,
        )
    except CurrentStateAccessGateError:
        raise
    except Exception as exc:
        raise CurrentStateAccessGateError(
            GATE_CLOSED, "run gate already consumed or unavailable"
        ) from exc
    finally:
        if run_lock is not None:
            run_lock.close()
        if session is not None:
            session.close()


def verify_consumed_current_state_run_gate(
    authorization: CurrentStateRunAuthorization,
    receipt: RunGateReceipt,
    *,
    evidence_root: Path,
    backend: Any,
) -> None:
    """Re-open the exact one-shot marker and verify its durable hash."""

    if (
        authorization._runtime_seal is not _PRODUCTION_SEAL
        or receipt.authorization_sha256 != authorization.authorization_sha256
        or receipt.marker_name
        != f"issue748-{authorization.authorization_sha256}.consumed.json"
    ):
        _fail("run gate receipt binding invalid")
    path = evidence_root / receipt.marker_name
    try:
        snapshot = backend.inspect_private_path(path, purpose="issue748-consumed-marker")
    except Exception as exc:
        raise CurrentStateAccessGateError(
            GATE_CLOSED, "consumed marker unavailable"
        ) from exc
    if getattr(snapshot, "sha256", "") != receipt.marker_sha256:
        _fail("consumed marker hash drift")


__all__ = [
    "BLOCKED_ACCOUNT_BINDING",
    "BLOCKED_SINGLE_PRINCIPAL",
    "BASE_MERGE_COMMIT",
    "BASE_MERGE_TREE",
    "CurrentStateAccessGateError",
    "CurrentStateRunAuthorization",
    "RunGateReceipt",
    "GATE_CLOSED",
    "GateInput",
    "authorize_current_state_run",
    "consume_current_state_run_gate",
]
