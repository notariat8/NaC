from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Protocol

from .azure_activation import LOCATION, RESOURCE_GROUP, SUBSCRIPTION_ID, TENANT_ID
from . import azure_activation_runner as runner


SCHEMA_VERSION = "nac.m365-azure-bff-interruption-reconciliation/v0.1"
MARKER_SCHEMA_VERSION = (
    "nac.m365-azure-bff-interruption-reconciliation-marker/v0.2"
)
INTENT_SCHEMA_VERSION = (
    "nac.m365-azure-bff-interruption-terminalization-intent/v0.1"
)
ACTION = "TERMINALIZE_AND_RELEASE_LOCK_ONLY"
INTERRUPTED_STEP_ID = "ensure_resource_group"
INTERRUPTION_CODE = "EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE"
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
_TERMINALIZATION_APPROVAL_REFERENCE_RE = re.compile(
    r"^https://github\.com/notariat8/NaC/issues/717"
    r"#issuecomment-[1-9][0-9]*$"
)
_MAX_LOCK_ARTIFACT_BYTES = 1024 * 1024
_PROVIDERS = {
    "Microsoft.OperationalInsights": "Registered",
    "Microsoft.Storage": "Registered",
    "Microsoft.Web": "Registered",
}
_RESOURCE_GROUP_TAGS = {
    "dataClassification": "no-production-data",
    "environment": "test",
    "workload": "nac-bff",
}
_STATE_KEYS = {
    "schema_version", "status", "started_at_utc", "finished_at_utc",
    "activation_hash", "approved_commit_sha", "approved_tree_sha",
    "approval_reference_sha256", "approval_body_sha256",
    "provisioner_bootstrap_binding_sha256",
    "toolchain_attestations_sha256", "reason_sha256",
    "correlation_id_sha256", "target_binding_sha256",
    "legacy_target_binding_sha256", "permission_boundary_sha256",
    "ledger_head_sha256", "ledger_sequence", "run_attempt",
    "writes_started", "steps", "duplicate_count",
    "broader_permission_count", "automatic_rollback_count",
    "automatic_deletion_count", "prebuilt_inputs_verified",
    "healthz_before_auth_passed", "authenticated_read_passed",
    "readyz_after_authenticated_read_passed", "synthetic_state_restored",
    "assigned_access_passed", "deputy_access_passed",
    "denied_access_passed", "tampered_access_passed",
    "tampered_workspace_passed", "tampered_matter_passed",
    "tampered_purpose_passed", "tampered_filter_passed",
    "resume_enabled", "ledger_hash_chain_valid",
}
_STEP_KEYS = {
    "order", "id", "status", "attempt", "classification", "http_status",
    "stable_error_code", "request_sha256", "response_sha256",
    "resource_reference_sha256",
}
_EVENT_BASE_KEYS = {
    "schema_version", "sequence", "step_id", "phase", "status", "attempt",
    "timestamp_utc", "previous_event_sha256", "_event_sha256",
}
_EXPECTED_EVENTS = (
    ("runner", "LOCK_ACQUIRED", "LIVE_APPROVED"),
    ("runner", "START", "LIVE_APPROVED"),
    ("runner", "PRE_WRITE_BINDING", "LIVE_APPROVED"),
    ("register_azure_providers", "RUNNING", "RUNNING"),
    ("register_azure_providers", "PASSED", "PASSED"),
    (INTERRUPTED_STEP_ID, "RUNNING", "RUNNING"),
)
_APPROVAL_BINDING_KEYS = {
    "action",
    "activation_hash",
    "state_sha256",
    "ledger_head_sha256",
    "target_lock_sha256",
    "legacy_lock_sha256",
    "legacy_host_lock_sha256",
    "provider_observation_sha256",
    "interrupted_step",
    "reconciler_commit",
    "reconciler_tree",
    "reconciler_toolchain_sha256",
    "required_owner_login",
}
_PHASE_INDEX = {
    "MIDRUN_TERMINALIZATION_AUTHORIZED": 0,
    "MIDRUN_FAILED_EVENT_APPENDED": 1,
    "MIDRUN_TERMINAL_EVENT_APPENDED": 2,
    "MIDRUN_RELEASE_EVENT_APPENDED": 3,
    "MIDRUN_TERMINAL_STATE_WRITTEN": 4,
    "MIDRUN_TERMINAL_STATE_VALIDATED": 5,
    "MIDRUN_EVIDENCE_WRITTEN": 6,
    "MIDRUN_RELEASE_IN_PROGRESS": 6,
    "MIDRUN_TARGET_LOCK_RELEASED": 7,
    "MIDRUN_LEGACY_LOCK_RELEASED": 8,
    "MIDRUN_LEGACY_HOST_LOCK_RELEASED": 9,
    "MIDRUN_RELEASED": 9,
}
_PHASE_FOR_PROGRESS = {
    0: "MIDRUN_TERMINALIZATION_AUTHORIZED",
    1: "MIDRUN_FAILED_EVENT_APPENDED",
    2: "MIDRUN_TERMINAL_EVENT_APPENDED",
    3: "MIDRUN_RELEASE_EVENT_APPENDED",
    4: "MIDRUN_TERMINAL_STATE_WRITTEN",
    5: "MIDRUN_TERMINAL_STATE_VALIDATED",
    6: "MIDRUN_EVIDENCE_WRITTEN",
    7: "MIDRUN_TARGET_LOCK_RELEASED",
    8: "MIDRUN_LEGACY_LOCK_RELEASED",
    9: "MIDRUN_LEGACY_HOST_LOCK_RELEASED",
}


class InterruptionObservationPort(Protocol):
    def observe_ensure_resource_group(
        self, *, tenant_id: str, subscription_id: str, resource_group: str
    ) -> dict[str, Any]: ...


class ImmutableOwnerCommentVerifier(Protocol):
    def verify_owner_comment(
        self,
        *,
        reference: str,
        expected_body: str,
        expected_body_sha256: str,
    ) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class InterruptionReconcilerBinding:
    approved_commit: str
    approved_tree: str
    toolchain_sha256: str
    required_owner_login: str


@dataclass(frozen=True, slots=True)
class InterruptionTerminalizationApproval:
    owner_approved: bool
    action: str
    owner_approval_reference: str
    approval_body_sha256: str
    activation_hash: str
    state_sha256: str
    ledger_head_sha256: str
    target_lock_sha256: str
    legacy_lock_sha256: str
    legacy_host_lock_sha256: str
    provider_observation_sha256: str
    interrupted_step: str
    reconciler_commit: str
    reconciler_tree: str
    reconciler_toolchain_sha256: str
    required_owner_login: str


def inspect_azure_bff_step2_interruption(
    *,
    repo_root: Path,
    request: runner.LiveActivationRequest,
    reconciler_binding: InterruptionReconcilerBinding,
    observation_port: InterruptionObservationPort,
    output_root: Path = runner.DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    run_dir, error = _resolve_run_dir(
        repo_root, output_root, request.expected_activation_hash
    )
    if error:
        return _blocked(error)
    assert run_dir is not None
    error = _validate_reconciler_binding(reconciler_binding)
    if error:
        return _blocked(error)
    error = _validate_bound_live_request(request)
    if error:
        return _blocked(error)

    state_path = run_dir / "resume-state.redacted.json"
    state = runner._read_secure_canonical_json(state_path)
    if state is None:
        return _blocked("INTERRUPTION_STATE_INVALID")
    lock_paths = runner._interruption_reconciliation_lock_paths(state)
    if lock_paths is None:
        return _blocked("INTERRUPTION_LOCK_SET_INVALID")
    tracked = _inspection_snapshot_paths(run_dir, state_path, lock_paths)
    if tracked is None:
        return _blocked("INTERRUPTION_LOCAL_SNAPSHOT_INVALID")
    before = _snapshot_bytes(tracked)
    if before is None:
        return _blocked("INTERRUPTION_LOCAL_SNAPSHOT_INVALID")

    descriptors, error = _open_lock_set_read_only(lock_paths)
    if error:
        return _blocked(error)
    assert descriptors is not None
    try:
        current_state = runner._read_secure_canonical_json(state_path)
        current_paths = (
            runner._interruption_reconciliation_lock_paths(current_state)
            if isinstance(current_state, dict)
            else None
        )
        if current_state != state or current_paths != lock_paths:
            result = _blocked("INTERRUPTION_STATE_CHANGED")
        elif not _descriptors_match_paths(lock_paths, descriptors):
            result = _blocked("INTERRUPTION_LOCK_REPLACED")
        else:
            result = _inspect_locked(
                run_dir=run_dir,
                state=current_state,
                state_path=state_path,
                lock_paths=lock_paths,
                lock_descriptors=descriptors,
                request=request,
                reconciler_binding=reconciler_binding,
                observation_port=observation_port,
            )
    finally:
        _close_lock_set(descriptors)
    after_paths = _inspection_snapshot_paths(run_dir, state_path, lock_paths)
    after = _snapshot_bytes(after_paths) if after_paths is not None else None
    if after_paths is None or after_paths != tracked or after is None or after != before:
        return _blocked("INTERRUPTION_INSPECTION_LOCAL_WRITE_DETECTED")
    return result


def terminalize_azure_bff_step2_interruption(
    *,
    repo_root: Path,
    request: runner.LiveActivationRequest,
    reconciler_binding: InterruptionReconcilerBinding,
    observation_port: InterruptionObservationPort,
    owner_comment_verifier: ImmutableOwnerCommentVerifier,
    approval: InterruptionTerminalizationApproval,
    pre_mutation_revalidate: Callable[[], None],
    output_root: Path = runner.DEFAULT_OUTPUT_ROOT,
    now: Callable[[], datetime] | None = None,
    fault_injector: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    run_dir, error = _resolve_run_dir(
        repo_root, output_root, request.expected_activation_hash
    )
    if error:
        return _blocked(error)
    assert run_dir is not None
    if _validate_reconciler_binding(reconciler_binding):
        return _blocked("INTERRUPTION_RECONCILER_BINDING_INVALID")
    request_error = _validate_bound_live_request(request)
    if request_error:
        return _blocked(request_error)
    if not _approval_shape_is_valid(approval):
        return _blocked("INTERRUPTION_APPROVAL_INVALID")

    state_path = run_dir / "resume-state.redacted.json"
    state = runner._read_secure_canonical_json(state_path)
    if state is None:
        return _blocked("INTERRUPTION_STATE_INVALID")
    return _terminalize_locked(
        run_dir=run_dir,
        state=state,
        state_path=state_path,
        request=request,
        reconciler_binding=reconciler_binding,
        observation_port=observation_port,
        owner_comment_verifier=owner_comment_verifier,
        approval=approval,
        pre_mutation_revalidate=pre_mutation_revalidate,
        now=now,
        fault_injector=fault_injector,
    )


def _terminalize_locked(
    *,
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    request: runner.LiveActivationRequest,
    reconciler_binding: InterruptionReconcilerBinding,
    observation_port: InterruptionObservationPort,
    owner_comment_verifier: ImmutableOwnerCommentVerifier,
    approval: InterruptionTerminalizationApproval,
    pre_mutation_revalidate: Callable[[], None],
    now: Callable[[], datetime] | None,
    fault_injector: Callable[[str], None] | None,
) -> dict[str, Any]:
    marker_path = _marker_path(run_dir)
    local_mutation_exists = marker_path.exists() or state.get("status") == "FAILED_PARTIAL"
    lock_paths = runner._interruption_reconciliation_lock_paths(state)
    if lock_paths is None:
        return _blocked(
            "INTERRUPTION_LOCK_SET_INVALID",
            writes_started=local_mutation_exists,
        )
    descriptors, error = _open_lock_set_for_terminalization(lock_paths)
    if error:
        return _blocked(error, writes_started=local_mutation_exists)
    assert descriptors is not None
    try:
        current_state = runner._read_secure_canonical_json(state_path)
        current_paths = (
            runner._interruption_reconciliation_lock_paths(current_state)
            if isinstance(current_state, dict)
            else None
        )
        if current_state != state or current_paths != lock_paths:
            return _blocked(
                "INTERRUPTION_STATE_CHANGED",
                writes_started=local_mutation_exists,
            )
        if not _descriptors_match_paths(lock_paths, descriptors):
            return _blocked(
                "INTERRUPTION_LOCK_REPLACED",
                writes_started=local_mutation_exists,
            )

        marker = runner._read_secure_canonical_json(marker_path)
        if marker_path.exists() and marker is None:
            return _blocked("INTERRUPTION_MARKER_INVALID", writes_started=True)
        if marker is not None:
            if not _existing_marker_is_valid(marker):
                return _blocked("INTERRUPTION_MARKER_INVALID", writes_started=True)
            if not _marker_runtime_bindings_match(
                marker, request, reconciler_binding
            ):
                return _blocked(
                    "INTERRUPTION_MARKER_BINDING_MISMATCH",
                    writes_started=True,
                )
            if not _marker_approval_matches(approval, marker):
                return _blocked("INTERRUPTION_APPROVAL_MISMATCH", writes_started=True)
            if not _verify_owner_comment(
                owner_comment_verifier,
                reconciler_binding,
                approval.owner_approval_reference,
                marker["owner_comment_body"],
                marker["terminalization_approval_body_sha256"],
            ):
                return _blocked(
                    "OWNER_COMMENT_VERIFICATION_FAILED", writes_started=True
                )
            if not _marker_provider_observation_is_stable(
                observation_port, marker
            ):
                return _blocked(
                    "PROVIDER_OBSERVATION_DRIFT", writes_started=True
                )
            return _continue_terminalization(
                run_dir=run_dir,
                state_path=state_path,
                lock_paths=lock_paths,
                descriptors=descriptors,
                marker=marker,
                pre_mutation_revalidate=pre_mutation_revalidate,
                fault_injector=fault_injector,
                idempotent=True,
            )

        inspection = _inspect_locked(
            run_dir=run_dir,
            state=current_state,
            state_path=state_path,
            lock_paths=lock_paths,
            lock_descriptors=descriptors,
            request=request,
            reconciler_binding=reconciler_binding,
            observation_port=observation_port,
        )
        if inspection.get("status") != "MIDRUN_RECONCILIATION_REQUIRED":
            return inspection
        owner_comment = inspection["owner_comment"]
        if not _verify_owner_comment(
            owner_comment_verifier,
            reconciler_binding,
            approval.owner_approval_reference,
            owner_comment["body"],
            owner_comment["body_sha256"],
        ):
            return _blocked("OWNER_COMMENT_VERIFICATION_FAILED")
        if not _approval_matches(approval, inspection):
            return _blocked("INTERRUPTION_APPROVAL_MISMATCH")

        marker = _authorization_marker(
            inspection, approval, request, current_state, now
        )
        revalidation_error = _pre_mutation_revalidation_error(
            pre_mutation_revalidate,
            state_path,
            current_state,
            lock_paths,
            descriptors,
        )
        if revalidation_error:
            return _blocked(revalidation_error)
        runner._atomic_json_write(marker_path, marker)
        _checkpoint(fault_injector, "marker:MIDRUN_TERMINALIZATION_AUTHORIZED")
        if runner._read_secure_canonical_json(marker_path) != marker:
            return _blocked("INTERRUPTION_MARKER_INVALID", writes_started=True)
        return _continue_terminalization(
            run_dir=run_dir,
            state_path=state_path,
            lock_paths=lock_paths,
            descriptors=descriptors,
            marker=marker,
            pre_mutation_revalidate=pre_mutation_revalidate,
            fault_injector=fault_injector,
            idempotent=False,
            runtime_already_revalidated=True,
        )
    except runner.ActivationStepError as exc:
        return _blocked(exc.code, writes_started=local_mutation_exists or marker_path.exists())
    except Exception:
        return _blocked(
            "INTERRUPTION_TERMINALIZATION_FAILED",
            writes_started=local_mutation_exists or marker_path.exists(),
        )
    finally:
        _close_lock_set(descriptors)


def _inspect_locked(
    *,
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    lock_paths: tuple[Path, Path, Path],
    lock_descriptors: tuple[int, int, int],
    request: runner.LiveActivationRequest,
    reconciler_binding: InterruptionReconcilerBinding,
    observation_port: InterruptionObservationPort,
    allow_authorization_marker: bool = False,
) -> dict[str, Any]:
    error = _validate_interrupted_state(
        run_dir,
        state,
        state_path,
        request,
        allow_authorization_marker=allow_authorization_marker,
    )
    if error:
        return _blocked(error)
    if not _descriptors_match_paths(lock_paths, lock_descriptors):
        return _blocked("INTERRUPTION_LOCK_REPLACED")
    lock_hashes: dict[str, str] = {}
    for name, descriptor in zip(
        ("target", "legacy", "legacy_host"),
        lock_descriptors,
        strict=True,
    ):
        if not runner._held_lock_marker_matches(
            runner._read_lock_marker_descriptor(descriptor),
            request.expected_activation_hash,
        ):
            return _blocked("INTERRUPTION_LOCK_NOT_HELD")
        digest = _descriptor_sha256(descriptor)
        if digest is None:
            return _blocked("INTERRUPTION_LOCK_SET_INVALID")
        lock_hashes[name] = digest

    first = _observe(observation_port)
    if _validate_provider_observation(first):
        return _blocked("PROVIDER_OBSERVATION_INVALID")
    second = _observe(observation_port)
    if (
        _validate_provider_observation(second)
        or runner._canonical_json_bytes(first) != runner._canonical_json_bytes(second)
    ):
        return _blocked("PROVIDER_OBSERVATION_DRIFT")
    observation_sha256 = runner._sha256_json(first)
    state_sha256 = runner._artifact_sha256(state_path)
    if state_sha256 is None:
        return _blocked("INTERRUPTION_STATE_INVALID")
    bindings = {
        "action": ACTION,
        "activation_hash": request.expected_activation_hash,
        "state_sha256": state_sha256,
        "ledger_head_sha256": state["ledger_head_sha256"],
        "target_lock_sha256": lock_hashes["target"],
        "legacy_lock_sha256": lock_hashes["legacy"],
        "legacy_host_lock_sha256": lock_hashes["legacy_host"],
        "provider_observation_sha256": observation_sha256,
        "interrupted_step": INTERRUPTED_STEP_ID,
        "reconciler_commit": reconciler_binding.approved_commit,
        "reconciler_tree": reconciler_binding.approved_tree,
        "reconciler_toolchain_sha256": reconciler_binding.toolchain_sha256,
        "required_owner_login": reconciler_binding.required_owner_login,
    }
    body = (
        "NAC_BFF_INTERRUPTION_RECONCILIATION_APPROVAL\n"
        + runner._canonical_json_bytes(bindings).decode("ascii")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "MIDRUN_RECONCILIATION_REQUIRED",
        "error": {"code": "MIDRUN_RECONCILIATION_REQUIRED"},
        "writes_started": True,
        "running_step": INTERRUPTED_STEP_ID,
        "provider_observation": {
            "status": "STABLE", "read_count": 2,
            "sha256": observation_sha256,
        },
        "approval_bindings": bindings,
        "owner_comment": {
            "body": body,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        },
        "resume_enabled": False,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }


def _validate_interrupted_state(
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    request: runner.LiveActivationRequest,
    *,
    allow_authorization_marker: bool = False,
) -> str | None:
    if set(state) != _STATE_KEYS:
        return "INTERRUPTION_STATE_INVALID"
    expected = {
        "schema_version": runner.STATE_SCHEMA_VERSION,
        "status": "LIVE_APPROVED",
        "finished_at_utc": None,
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": runner._sha256(request.owner_approval_reference),
        "approval_body_sha256": request.approval_body_sha256,
        "provisioner_bootstrap_binding_sha256": request.provisioner_bootstrap_binding_sha256,
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
        "reason_sha256": runner._sha256(request.reason),
        "correlation_id_sha256": runner._sha256(request.correlation_id),
        "ledger_sequence": 6,
        "run_attempt": 1,
        "writes_started": True,
        "resume_enabled": False,
        "ledger_hash_chain_valid": False,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }
    if any(state.get(key) != value for key, value in expected.items()):
        return "INTERRUPTION_STATE_INVALID"
    for key in (
        "target_binding_sha256", "legacy_target_binding_sha256",
        "permission_boundary_sha256", "ledger_head_sha256",
    ):
        if not isinstance(state.get(key), str) or not runner._SHA256_RE.fullmatch(state[key]):
            return "INTERRUPTION_STATE_INVALID"
    steps = state.get("steps")
    if not isinstance(steps, list) or len(steps) != 2:
        return "INTERRUPTION_RECONCILIATION_UNSUPPORTED"
    if any(not isinstance(step, dict) or set(step) != _STEP_KEYS for step in steps):
        return "INTERRUPTION_STATE_INVALID"
    first, second = steps
    if second.get("id") != INTERRUPTED_STEP_ID:
        return "INTERRUPTION_RECONCILIATION_UNSUPPORTED"
    if (
        first.get("order") != 1
        or first.get("id") != "register_azure_providers"
        or first.get("status") != "PASSED"
        or first.get("attempt") != 1
        or second != runner._step_record(
            2, INTERRUPTED_STEP_ID, "RUNNING", 1, "not_applicable"
        )
    ):
        return "INTERRUPTION_STATE_INVALID"
    events, chain_error = runner._validate_event_chain(run_dir / "ledger")
    if chain_error or not runner._state_matches_chain(state, events):
        return "INTERRUPTION_LEDGER_INVALID"
    if len(events) != 6:
        return "INTERRUPTION_LEDGER_INVALID"
    for event, expected_event in zip(events, _EXPECTED_EVENTS, strict=True):
        actual = (event.get("step_id"), event.get("phase"), event.get("status"))
        if actual != expected_event or event.get("attempt") != 1:
            return "INTERRUPTION_LEDGER_INVALID"
    for index, event in enumerate(events):
        expected_keys = set(_EVENT_BASE_KEYS)
        if index == 0:
            expected_keys.add("bindings")
        if index == 4:
            expected_keys.add("outcome")
        if set(event) != expected_keys:
            return "INTERRUPTION_LEDGER_INVALID"
    if events[4].get("outcome") != first or any(
        key in events[5] for key in ("outcome", "bindings")
    ):
        return "INTERRUPTION_LEDGER_INVALID"
    forbidden = [
        run_dir / "activation.redacted.json",
        run_dir / "activation.commit.redacted.json",
        run_dir / "activation.success-receipt.redacted.json",
        run_dir / "activation.finalization-recovery.redacted.json",
        run_dir / "activation.finalization-reconciled.redacted.json",
    ]
    if not allow_authorization_marker:
        forbidden.append(_marker_path(run_dir))
    if any(path.exists() for path in forbidden):
        return "INTERRUPTION_ARTIFACT_STATE_INVALID"
    receipt = runner._success_receipt_path(
        runner._HOST_LOCK_ROOT.expanduser().absolute(),
        state["target_binding_sha256"],
        request,
    )
    if receipt.exists():
        return "INTERRUPTION_ARTIFACT_STATE_INVALID"
    if runner._read_secure_canonical_json(state_path) != state:
        return "INTERRUPTION_STATE_INVALID"
    return None


def _observe(port: InterruptionObservationPort) -> dict[str, Any]:
    try:
        value = port.observe_ensure_resource_group(
            tenant_id=TENANT_ID,
            subscription_id=SUBSCRIPTION_ID,
            resource_group=RESOURCE_GROUP,
        )
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _validate_provider_observation(value: dict[str, Any]) -> bool:
    expected_group = {
        "id": f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}",
        "name": RESOURCE_GROUP,
        "location": LOCATION,
        "provisioning_state": "Succeeded",
        "tags": _RESOURCE_GROUP_TAGS,
    }
    valid = bool(
        set(value) == {
            "tenant_id", "subscription_id", "providers", "resource_groups",
            "resource_inventory",
        }
        and value.get("tenant_id") == TENANT_ID
        and value.get("subscription_id") == SUBSCRIPTION_ID
        and value.get("providers") == _PROVIDERS
        and value.get("resource_groups") == [expected_group]
    )
    if not valid:
        return True
    if value.get("resource_inventory") != []:
        return True
    try:
        runner._reject_secret_sentinel(value)
    except runner.ActivationStepError:
        return True
    return False


def _verify_owner_comment(
    verifier: ImmutableOwnerCommentVerifier,
    binding: InterruptionReconcilerBinding,
    reference: str,
    body: str,
    body_sha256: str,
) -> bool:
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != body_sha256:
        return False
    try:
        result = verifier.verify_owner_comment(
            reference=reference,
            expected_body=body,
            expected_body_sha256=body_sha256,
        )
    except Exception:
        return False
    return bool(
        isinstance(result, dict)
        and set(result) == {
            "status", "owner_login", "immutable", "reference", "body",
            "body_sha256",
        }
        and result.get("status") == "VERIFIED"
        and result.get("owner_login") == binding.required_owner_login
        and result.get("immutable") is True
        and result.get("reference") == reference
        and result.get("body") == body
        and result.get("body_sha256") == body_sha256
        and hashlib.sha256(result["body"].encode("utf-8")).hexdigest()
        == result["body_sha256"]
    )


def _approval_shape_is_valid(approval: InterruptionTerminalizationApproval) -> bool:
    return bool(
        approval.owner_approved is True
        and approval.action == ACTION
        and _TERMINALIZATION_APPROVAL_REFERENCE_RE.fullmatch(
            approval.owner_approval_reference
        )
        and approval.interrupted_step == INTERRUPTED_STEP_ID
        and _OWNER_RE.fullmatch(approval.required_owner_login)
        and all(runner._SHA256_RE.fullmatch(value) for value in (
            approval.approval_body_sha256, approval.activation_hash,
            approval.state_sha256, approval.ledger_head_sha256,
            approval.target_lock_sha256, approval.legacy_lock_sha256,
            approval.legacy_host_lock_sha256,
            approval.provider_observation_sha256,
            approval.reconciler_toolchain_sha256,
        ))
        and runner._COMMIT_RE.fullmatch(approval.reconciler_commit)
        and runner._COMMIT_RE.fullmatch(approval.reconciler_tree)
    )


def _approval_matches(
    approval: InterruptionTerminalizationApproval,
    inspection: dict[str, Any],
) -> bool:
    bindings = inspection.get("approval_bindings")
    comment = inspection.get("owner_comment")
    if (
        not isinstance(bindings, dict)
        or set(bindings) != _APPROVAL_BINDING_KEYS
        or not isinstance(comment, dict)
    ):
        return False
    expected = _approval_bindings_from_approval(approval)
    return bool(
        bindings == expected
        and approval.approval_body_sha256 == comment.get("body_sha256")
    )


def _approval_bindings_from_approval(
    approval: InterruptionTerminalizationApproval,
) -> dict[str, str]:
    return {
        "action": approval.action,
        "activation_hash": approval.activation_hash,
        "state_sha256": approval.state_sha256,
        "ledger_head_sha256": approval.ledger_head_sha256,
        "target_lock_sha256": approval.target_lock_sha256,
        "legacy_lock_sha256": approval.legacy_lock_sha256,
        "legacy_host_lock_sha256": approval.legacy_host_lock_sha256,
        "provider_observation_sha256": approval.provider_observation_sha256,
        "interrupted_step": approval.interrupted_step,
        "reconciler_commit": approval.reconciler_commit,
        "reconciler_tree": approval.reconciler_tree,
        "reconciler_toolchain_sha256": (
            approval.reconciler_toolchain_sha256
        ),
        "required_owner_login": approval.required_owner_login,
    }


def _marker_runtime_bindings_match(
    marker: dict[str, Any],
    request: runner.LiveActivationRequest,
    binding: InterruptionReconcilerBinding,
) -> bool:
    initial = marker["intent"]["initial_state"]
    approval_bindings = marker["approval_bindings"]
    expected_state = {
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": runner._sha256(
            request.owner_approval_reference
        ),
        "approval_body_sha256": request.approval_body_sha256,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": (
            request.toolchain_attestations_sha256
        ),
        "reason_sha256": runner._sha256(request.reason),
        "correlation_id_sha256": runner._sha256(request.correlation_id),
    }
    expected_reconciler = {
        "reconciler_commit": binding.approved_commit,
        "reconciler_tree": binding.approved_tree,
        "reconciler_toolchain_sha256": binding.toolchain_sha256,
        "required_owner_login": binding.required_owner_login,
    }
    return bool(
        all(initial.get(key) == value for key, value in expected_state.items())
        and marker.get("original_approval_reference_sha256")
        == expected_state["approval_reference_sha256"]
        and all(
            approval_bindings.get(key) == value
            for key, value in expected_reconciler.items()
        )
    )


def _marker_approval_matches(
    approval: InterruptionTerminalizationApproval,
    marker: dict[str, Any],
) -> bool:
    return bool(
        marker.get("approval_bindings")
        == _approval_bindings_from_approval(approval)
        and marker.get("terminalization_approval_body_sha256")
        == approval.approval_body_sha256
        and marker.get("terminalization_approval_reference_sha256")
        == runner._sha256(approval.owner_approval_reference)
    )


def _authorization_marker(
    inspection: dict[str, Any],
    approval: InterruptionTerminalizationApproval,
    request: runner.LiveActivationRequest,
    state: dict[str, Any],
    now: Callable[[], datetime] | None,
) -> dict[str, Any]:
    intent = _build_terminalization_intent(state, now)
    return {
        "schema_version": MARKER_SCHEMA_VERSION,
        "status": "MIDRUN_TERMINALIZATION_AUTHORIZED",
        "action": ACTION,
        "activation_hash": request.expected_activation_hash,
        "original_approval_reference_sha256": runner._sha256(
            request.owner_approval_reference
        ),
        "terminalization_approval_reference_sha256": runner._sha256(
            approval.owner_approval_reference
        ),
        "terminalization_approval_body_sha256": (
            approval.approval_body_sha256
        ),
        "owner_comment_body": inspection["owner_comment"]["body"],
        "approval_bindings": inspection["approval_bindings"],
        "intent": intent,
        "released_lock_sha256": {},
        "resume_enabled": False,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }


def _build_terminalization_intent(
    initial_state: dict[str, Any],
    now: Callable[[], datetime] | None,
) -> dict[str, Any]:
    timestamps = tuple(runner._utc_now(now) for _ in range(3))
    finished_at_utc = runner._utc_now(now)
    return _derive_terminalization_intent(
        initial_state,
        finished_at_utc=finished_at_utc,
        event_timestamps=timestamps,
    )


def _derive_terminalization_intent(
    initial_state: dict[str, Any],
    *,
    finished_at_utc: str,
    event_timestamps: tuple[str, str, str],
) -> dict[str, Any]:
    initial = copy.deepcopy(initial_state)
    terminal = copy.deepcopy(initial_state)
    failed = runner._step_record(
        2,
        INTERRUPTED_STEP_ID,
        "FAILED",
        1,
        "not_applicable",
        {"stable_error_code": INTERRUPTION_CODE},
    )
    runner._set_state_step(terminal, failed)
    events: list[dict[str, Any]] = []
    previous = initial_state["ledger_head_sha256"]
    specifications = (
        (
            INTERRUPTED_STEP_ID,
            "FAILED",
            "FAILED",
            {"outcome": failed},
        ),
        (
            "runner",
            "TERMINAL",
            "FAILED_PARTIAL",
            {"outcome": {"stable_error_code": INTERRUPTION_CODE}},
        ),
        (
            "runner",
            "LOCK_RELEASE_AUTHORIZED",
            "FAILED_PARTIAL",
            {},
        ),
    )
    for offset, (step_id, phase, status, extra) in enumerate(
        specifications, start=1
    ):
        event = {
            "schema_version": runner.LEDGER_SCHEMA_VERSION,
            "sequence": int(initial_state["ledger_sequence"]) + offset,
            "step_id": step_id,
            "phase": phase,
            "status": status,
            "attempt": 1,
            "timestamp_utc": event_timestamps[offset - 1],
            "previous_event_sha256": previous,
            **extra,
        }
        previous = hashlib.sha256(
            runner._canonical_json_bytes(event)
        ).hexdigest()
        events.append(event)
    terminal.update(
        {
            "status": "FAILED_PARTIAL",
            "finished_at_utc": finished_at_utc,
            "resume_enabled": False,
            "ledger_sequence": events[-1]["sequence"],
            "ledger_head_sha256": previous,
            "ledger_hash_chain_valid": False,
        }
    )
    validated = copy.deepcopy(terminal)
    validated["ledger_hash_chain_valid"] = True
    evidence = runner._evidence_from_state(validated)
    runner._validate_evidence(evidence)
    return {
        "schema_version": INTENT_SCHEMA_VERSION,
        "initial_state": initial,
        "terminal_events": events,
        "terminal_state_unvalidated": terminal,
        "terminal_state": validated,
        "terminal_evidence": evidence,
    }


def _existing_marker_is_valid(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    expected_keys = {
        "schema_version", "status", "action", "activation_hash",
        "original_approval_reference_sha256",
        "terminalization_approval_reference_sha256",
        "terminalization_approval_body_sha256", "owner_comment_body",
        "approval_bindings", "intent", "released_lock_sha256",
        "resume_enabled", "automatic_rollback_count",
        "automatic_deletion_count",
    }
    bindings = value.get("approval_bindings")
    released = value.get("released_lock_sha256")
    if (
        set(value) != expected_keys
        or value.get("schema_version") != MARKER_SCHEMA_VERSION
        or value.get("status") not in _PHASE_INDEX
        or value.get("action") != ACTION
        or value.get("resume_enabled") is not False
        or value.get("automatic_rollback_count") != 0
        or value.get("automatic_deletion_count") != 0
        or not isinstance(bindings, dict)
        or set(bindings) != _APPROVAL_BINDING_KEYS
        or not all(isinstance(item, str) for item in bindings.values())
        or not isinstance(released, dict)
        or not isinstance(value.get("owner_comment_body"), str)
    ):
        return False
    if not all(
        isinstance(value.get(key), str)
        and runner._SHA256_RE.fullmatch(value[key])
        for key in (
            "activation_hash", "original_approval_reference_sha256",
            "terminalization_approval_reference_sha256",
            "terminalization_approval_body_sha256",
        )
    ):
        return False
    body = value["owner_comment_body"]
    expected_body = (
        "NAC_BFF_INTERRUPTION_RECONCILIATION_APPROVAL\n"
        + runner._canonical_json_bytes(bindings).decode("ascii")
    )
    if (
        body != expected_body
        or hashlib.sha256(body.encode("utf-8")).hexdigest()
        != value["terminalization_approval_body_sha256"]
        or bindings.get("action") != ACTION
        or bindings.get("activation_hash") != value["activation_hash"]
        or bindings.get("interrupted_step") != INTERRUPTED_STEP_ID
    ):
        return False
    return _terminalization_intent_is_valid(value)


def _terminalization_intent_is_valid(marker: dict[str, Any]) -> bool:
    intent = marker.get("intent")
    if not isinstance(intent, dict) or set(intent) != {
        "schema_version", "initial_state", "terminal_events",
        "terminal_state_unvalidated", "terminal_state",
        "terminal_evidence",
    }:
        return False
    initial = intent.get("initial_state")
    events = intent.get("terminal_events")
    terminal = intent.get("terminal_state")
    if (
        intent.get("schema_version") != INTENT_SCHEMA_VERSION
        or not isinstance(initial, dict)
        or set(initial) != _STATE_KEYS
        or not isinstance(events, list)
        or len(events) != 3
        or not isinstance(terminal, dict)
        or not isinstance(terminal.get("finished_at_utc"), str)
        or any(
            not isinstance(event, dict)
            or not isinstance(event.get("timestamp_utc"), str)
            for event in events
        )
    ):
        return False
    try:
        expected = _derive_terminalization_intent(
            initial,
            finished_at_utc=terminal["finished_at_utc"],
            event_timestamps=tuple(
                event["timestamp_utc"] for event in events
            ),
        )
    except (KeyError, TypeError, ValueError, runner.ActivationStepError):
        return False
    bindings = marker["approval_bindings"]
    return bool(
        intent == expected
        and runner._sha256_json(initial) == bindings.get("state_sha256")
        and initial.get("ledger_head_sha256")
        == bindings.get("ledger_head_sha256")
        and initial.get("activation_hash") == marker.get("activation_hash")
    )


def _marker_provider_observation_is_stable(
    observation_port: InterruptionObservationPort,
    marker: dict[str, Any],
) -> bool:
    first, second = _observe(observation_port), _observe(observation_port)
    return bool(
        not _validate_provider_observation(first)
        and not _validate_provider_observation(second)
        and runner._canonical_json_bytes(first)
        == runner._canonical_json_bytes(second)
        and runner._sha256_json(first)
        == marker["approval_bindings"].get(
            "provider_observation_sha256"
        )
    )


def _continue_terminalization(
    *,
    run_dir: Path,
    state_path: Path,
    lock_paths: tuple[Path, Path, Path],
    descriptors: tuple[int, int, int],
    marker: dict[str, Any],
    pre_mutation_revalidate: Callable[[], None],
    fault_injector: Callable[[str], None] | None,
    idempotent: bool,
    runtime_already_revalidated: bool = False,
) -> dict[str, Any]:
    marker_path = _marker_path(run_dir)
    runtime_revalidated = runtime_already_revalidated
    while True:
        progress = _terminalization_progress(
            run_dir, state_path, descriptors, marker
        )
        if progress is None:
            return _blocked(
                "INTERRUPTION_TERMINAL_PROGRESS_INVALID",
                writes_started=True,
            )
        phase = marker["status"]
        phase_index = _PHASE_INDEX[phase]
        actual_index = progress["index"]
        if actual_index not in {phase_index, phase_index + 1}:
            return _blocked(
                "INTERRUPTION_TERMINAL_PROGRESS_INVALID",
                writes_started=True,
            )
        expected_released = _released_hash_prefix(
            progress["released_hashes"], max(phase_index - 6, 0)
        )
        if marker.get("released_lock_sha256") != expected_released:
            return _blocked("INTERRUPTION_MARKER_INVALID", writes_started=True)
        if phase == "MIDRUN_RELEASED":
            if actual_index != 9:
                return _blocked(
                    "INTERRUPTION_TERMINAL_PROGRESS_INVALID",
                    writes_started=True,
                )
            return _terminalization_result(
                run_dir, state_path, marker_path, idempotent
            )

        def ensure_runtime_revalidated() -> str | None:
            nonlocal runtime_revalidated, progress
            if runtime_revalidated:
                return None
            error = _pre_mutation_revalidation_error(
                pre_mutation_revalidate,
                state_path,
                progress["state"],
                lock_paths,
                descriptors,
            )
            if error:
                return error
            refreshed = _terminalization_progress(
                run_dir, state_path, descriptors, marker
            )
            if refreshed != progress:
                return "INTERRUPTION_TERMINAL_PROGRESS_CHANGED"
            progress = refreshed
            runtime_revalidated = True
            return None

        if actual_index == phase_index + 1:
            error = ensure_runtime_revalidated()
            if error:
                return _blocked(error, writes_started=True)
            marker = _advance_marker(
                marker_path,
                marker,
                _PHASE_FOR_PROGRESS[actual_index],
                progress["released_hashes"],
                fault_injector,
            )
            continue
        if actual_index == 6 and phase == "MIDRUN_EVIDENCE_WRITTEN":
            error = ensure_runtime_revalidated()
            if error:
                return _blocked(error, writes_started=True)
            marker = _advance_marker(
                marker_path,
                marker,
                "MIDRUN_RELEASE_IN_PROGRESS",
                progress["released_hashes"],
                fault_injector,
            )
            continue
        if actual_index == 9 and phase == "MIDRUN_LEGACY_HOST_LOCK_RELEASED":
            error = ensure_runtime_revalidated()
            if error:
                return _blocked(error, writes_started=True)
            marker = _advance_marker(
                marker_path,
                marker,
                "MIDRUN_RELEASED",
                progress["released_hashes"],
                fault_injector,
            )
            continue

        error = ensure_runtime_revalidated()
        if error:
            return _blocked(error, writes_started=True)
        intent = marker["intent"]
        if actual_index < 3:
            event = intent["terminal_events"][actual_index]
            _append_intent_event(run_dir / "ledger", event)
            _checkpoint(fault_injector, f"ledger:{event['phase']}")
        elif actual_index == 3:
            runner._atomic_json_write(
                state_path, intent["terminal_state_unvalidated"]
            )
            _checkpoint(fault_injector, "state:TERMINAL_WRITTEN")
        elif actual_index == 4:
            if not runner._terminal_chain_is_valid(
                intent["terminal_state_unvalidated"], run_dir / "ledger"
            ):
                return _blocked(
                    "INTERRUPTION_TERMINAL_LEDGER_INVALID",
                    writes_started=True,
                )
            runner._atomic_json_write(state_path, intent["terminal_state"])
            _checkpoint(fault_injector, "state:CHAIN_VALIDATED")
        elif actual_index == 5:
            evidence = intent["terminal_evidence"]
            runner._validate_evidence(evidence)
            runner._atomic_json_write(
                run_dir / "activation.redacted.json", evidence
            )
            _checkpoint(fault_injector, "evidence:WRITTEN")
        elif 6 <= actual_index < 9:
            lock_index = actual_index - 6
            if (
                actual_index == 6
                and phase != "MIDRUN_RELEASE_IN_PROGRESS"
            ):
                return _blocked(
                    "INTERRUPTION_TERMINAL_PROGRESS_INVALID",
                    writes_started=True,
                )
            if not _descriptors_match_paths(lock_paths, descriptors):
                return _blocked(
                    "INTERRUPTION_LOCK_REPLACED", writes_started=True
                )
            descriptor = descriptors[lock_index]
            activation_hash = marker["activation_hash"]
            if not runner._held_lock_marker_matches(
                runner._read_lock_marker_descriptor(descriptor),
                activation_hash,
            ):
                return _blocked(
                    "INTERRUPTION_LOCK_SET_INVALID", writes_started=True
                )
            runner._write_lock_marker(
                descriptor, activation_hash, "RELEASED"
            )
            _checkpoint(
                fault_injector,
                f"lock:{('target', 'legacy', 'legacy_host')[lock_index]}",
            )
        else:
            return _blocked(
                "INTERRUPTION_TERMINAL_PROGRESS_INVALID",
                writes_started=True,
            )


def _terminalization_progress(
    run_dir: Path,
    state_path: Path,
    descriptors: tuple[int, int, int],
    marker: dict[str, Any],
) -> dict[str, Any] | None:
    intent = marker["intent"]
    events, chain_error = runner._validate_event_chain(run_dir / "ledger")
    if chain_error or len(events) < 6 or len(events) > 9:
        return None
    initial = intent["initial_state"]
    if not runner._state_matches_chain(initial, events[:6]):
        return None
    if not _initial_event_prefix_is_valid(events[:6]):
        return None
    expected_tail = intent["terminal_events"]
    for actual, expected in zip(events[6:], expected_tail, strict=False):
        actual_without_hash = {
            key: value for key, value in actual.items() if key != "_event_sha256"
        }
        if actual_without_hash != expected:
            return None
    tail_count = len(events) - 6

    state = runner._read_secure_canonical_json(state_path)
    if state is None:
        return None
    if state == initial:
        state_index = 0
    elif state == intent["terminal_state_unvalidated"]:
        state_index = 1
    elif state == intent["terminal_state"]:
        state_index = 2
    else:
        return None
    if tail_count < 3 and state_index != 0:
        return None
    if state_index and tail_count != 3:
        return None

    evidence_path = run_dir / "activation.redacted.json"
    evidence = runner._read_secure_canonical_json(evidence_path)
    if evidence_path.exists() and evidence is None:
        return None
    evidence_present = evidence == intent["terminal_evidence"]
    if evidence is not None and not evidence_present:
        return None
    if evidence_present and state_index != 2:
        return None

    activation_hash = marker["activation_hash"]
    statuses: list[str] = []
    released_hashes: dict[str, str] = {}
    names = ("target", "legacy", "legacy_host")
    for name, descriptor in zip(names, descriptors, strict=True):
        lock_marker = runner._read_lock_marker_descriptor(descriptor)
        if runner._held_lock_marker_matches(lock_marker, activation_hash):
            statuses.append("HELD")
        elif runner._released_lock_marker_matches(lock_marker, activation_hash):
            statuses.append("RELEASED")
            digest = _descriptor_sha256(descriptor)
            if digest is None:
                return None
            released_hashes[name] = digest
        else:
            return None
    release_count = statuses.count("RELEASED")
    if statuses != ["RELEASED"] * release_count + ["HELD"] * (3 - release_count):
        return None
    if release_count and not evidence_present:
        return None

    if tail_count < 3:
        index = tail_count
    elif state_index == 0:
        index = 3
    elif state_index == 1:
        index = 4
    elif not evidence_present:
        index = 5
    else:
        index = 6 + release_count
    return {
        "index": index,
        "state": state,
        "released_hashes": released_hashes,
    }


def _initial_event_prefix_is_valid(events: list[dict[str, Any]]) -> bool:
    if len(events) != 6:
        return False
    for event, expected_event in zip(events, _EXPECTED_EVENTS, strict=True):
        actual = (event.get("step_id"), event.get("phase"), event.get("status"))
        if actual != expected_event or event.get("attempt") != 1:
            return False
    for index, event in enumerate(events):
        expected_keys = set(_EVENT_BASE_KEYS)
        if index == 0:
            expected_keys.add("bindings")
        if index == 4:
            expected_keys.add("outcome")
        if set(event) != expected_keys:
            return False
    return True


def _append_intent_event(
    ledger_dir: Path, event: dict[str, Any]
) -> None:
    path = ledger_dir / (
        f"{event['sequence']:06d}-{event['step_id']}-{event['phase']}"
        ".redacted.json"
    )
    runner._atomic_append(path, runner._canonical_json_bytes(event))


def _advance_marker(
    marker_path: Path,
    marker: dict[str, Any],
    status: str,
    released_hashes: dict[str, str],
    fault_injector: Callable[[str], None] | None,
) -> dict[str, Any]:
    phase_index = _PHASE_INDEX[status]
    updated = {
        **marker,
        "status": status,
        "released_lock_sha256": _released_hash_prefix(
            released_hashes, max(phase_index - 6, 0)
        ),
    }
    runner._atomic_json_write(marker_path, updated)
    _checkpoint(fault_injector, f"marker:{status}")
    if runner._read_secure_canonical_json(marker_path) != updated:
        raise runner.ActivationStepError("INTERRUPTION_MARKER_INVALID")
    return updated


def _released_hash_prefix(
    released_hashes: dict[str, str], count: int
) -> dict[str, str]:
    names = ("target", "legacy", "legacy_host")
    return {
        name: released_hashes[name]
        for name in names[:count]
        if name in released_hashes
    }


def _pre_mutation_revalidation_error(
    callback: Callable[[], None],
    state_path: Path,
    expected_state: dict[str, Any],
    lock_paths: tuple[Path, Path, Path],
    descriptors: tuple[int, int, int],
) -> str | None:
    try:
        callback()
    except runner.ActivationStepError as exc:
        return exc.code
    except Exception:
        return "INTERRUPTION_RECONCILER_REVALIDATION_FAILED"
    current_state = runner._read_secure_canonical_json(state_path)
    current_paths = (
        runner._interruption_reconciliation_lock_paths(current_state)
        if isinstance(current_state, dict)
        else None
    )
    if current_state != expected_state or current_paths != lock_paths:
        return "INTERRUPTION_STATE_CHANGED"
    if not _descriptors_match_paths(lock_paths, descriptors):
        return "INTERRUPTION_LOCK_REPLACED"
    return None


def _checkpoint(
    fault_injector: Callable[[str], None] | None, boundary: str
) -> None:
    if fault_injector is not None:
        fault_injector(boundary)


def _terminalization_result(
    run_dir: Path,
    state_path: Path,
    marker_path: Path,
    idempotent: bool,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "FAILED_PARTIAL",
        "error": {"code": INTERRUPTION_CODE},
        "writes_started": True,
        "resume_enabled": False,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
        "reconciliation": {
            "status": "MIDRUN_RELEASED",
            "idempotent": idempotent,
            "state_sha256": runner._artifact_sha256(state_path),
            "evidence_sha256": runner._artifact_sha256(
                run_dir / "activation.redacted.json"
            ),
            "marker_sha256": runner._artifact_sha256(marker_path),
        },
    }

def _resolve_run_dir(
    repo_root: Path, output_root: Path, activation_hash: str
) -> tuple[Path | None, str | None]:
    root = repo_root.expanduser().resolve()
    canonical = (root / runner.DEFAULT_OUTPUT_ROOT).resolve()
    supplied = (
        output_root if output_root.is_absolute() else root / output_root
    ).expanduser().resolve()
    if (
        supplied != canonical
        or root not in canonical.parents
        or not runner._SHA256_RE.fullmatch(activation_hash)
    ):
        return None, "OUTPUT_SCOPE_REJECTED"
    run_dir = (canonical / activation_hash).resolve()
    if run_dir.parent != canonical:
        return None, "OUTPUT_SCOPE_REJECTED"
    return run_dir, None


def _validate_reconciler_binding(value: InterruptionReconcilerBinding) -> str | None:
    if (
        not runner._COMMIT_RE.fullmatch(value.approved_commit)
        or not runner._COMMIT_RE.fullmatch(value.approved_tree)
        or not runner._SHA256_RE.fullmatch(value.toolchain_sha256)
        or not _OWNER_RE.fullmatch(value.required_owner_login)
    ):
        return "INTERRUPTION_RECONCILER_BINDING_INVALID"
    return None


def _validate_bound_live_request(
    request: runner.LiveActivationRequest,
) -> str | None:
    if request.resume is not False:
        return "RESUME_DISABLED_FOR_MVP"
    if not runner._SHA256_RE.fullmatch(request.expected_activation_hash):
        return "ACTIVATION_HASH_INVALID"
    if not runner._COMMIT_RE.fullmatch(request.approved_commit):
        return "APPROVED_COMMIT_INVALID"
    if not runner._COMMIT_RE.fullmatch(request.approved_tree):
        return "APPROVED_TREE_INVALID"
    if not runner._APPROVAL_REFERENCE_RE.fullmatch(
        request.owner_approval_reference.strip()
    ):
        return "APPROVAL_REFERENCE_INVALID"
    if not runner._SHA256_RE.fullmatch(request.approval_body_sha256):
        return "APPROVAL_BODY_HASH_INVALID"
    if not runner._SHA256_RE.fullmatch(
        request.provisioner_bootstrap_binding_sha256
    ):
        return "PROVISIONER_BOOTSTRAP_BINDING_INVALID"
    if any(
        not runner._SHA256_RE.fullmatch(value)
        for value in request.toolchain_attestations.values()
    ):
        return "TOOLCHAIN_ATTESTATION_INVALID"
    if len(request.reason.strip()) < 8:
        return "APPROVAL_REASON_REQUIRED"
    if not runner._CORRELATION_RE.fullmatch(request.correlation_id):
        return "CORRELATION_ID_INVALID"
    return None


def _descriptors_match_paths(
    paths: tuple[Path, Path, Path],
    descriptors: tuple[int, int, int],
) -> bool:
    try:
        for path, descriptor in zip(paths, descriptors, strict=True):
            path_metadata = path.lstat()
            opened = os.fstat(descriptor)
            if (
                not runner._trusted_secure_artifact_metadata(path_metadata)
                or not runner._trusted_secure_artifact_metadata(opened)
                or path_metadata.st_dev != opened.st_dev
                or path_metadata.st_ino != opened.st_ino
            ):
                return False
    except OSError:
        return False
    return True


def _descriptor_sha256(descriptor: int) -> str | None:
    try:
        before = os.fstat(descriptor)
        if (
            not runner._trusted_secure_artifact_metadata(before)
            or before.st_size < 1
            or before.st_size > _MAX_LOCK_ARTIFACT_BYTES
        ):
            return None
        raw = os.pread(descriptor, before.st_size, 0)
        after = os.fstat(descriptor)
        if (
            len(raw) != before.st_size
            or not runner._same_secure_snapshot(before, after)
        ):
            return None
        return hashlib.sha256(raw).hexdigest()
    except OSError:
        return None


def _open_lock_set_read_only(
    paths: tuple[Path, Path, Path]
) -> tuple[tuple[int, int, int] | None, str | None]:
    descriptors: list[int] = []
    try:
        for path in paths:
            metadata = path.lstat()
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) != 0o600
                or metadata.st_nlink != 1
            ):
                return None, "INTERRUPTION_LOCK_SET_INVALID"
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            descriptors.append(descriptor)
            opened = os.fstat(descriptor)
            if opened.st_ino != metadata.st_ino or opened.st_dev != metadata.st_dev:
                return None, "INTERRUPTION_LOCK_SET_INVALID"
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return tuple(descriptors), None  # type: ignore[return-value]
    except BlockingIOError:
        return None, "INTERRUPTION_LOCK_ACTIVE"
    except OSError:
        return None, "INTERRUPTION_LOCK_SET_INVALID"
    finally:
        if len(descriptors) != 3:
            _close_lock_set(tuple(descriptors))


def _open_lock_set_for_terminalization(
    paths: tuple[Path, Path, Path]
) -> tuple[tuple[int, int, int] | None, str | None]:
    descriptors: list[int] = []
    try:
        for path in paths:
            descriptor, error = runner._acquire_existing_lock_for_recovery(path)
            if error or descriptor is None:
                return None, error or "INTERRUPTION_LOCK_SET_INVALID"
            descriptors.append(descriptor)
        return tuple(descriptors), None  # type: ignore[return-value]
    finally:
        if len(descriptors) != 3:
            _close_lock_set(tuple(descriptors))


def _close_lock_set(descriptors: tuple[int, ...]) -> None:
    for descriptor in reversed(descriptors):
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _snapshot_bytes(paths: tuple[Path, ...]) -> dict[Path, bytes] | None:
    snapshots: dict[Path, bytes] = {}
    for path in paths:
        raw = runner._read_secure_artifact_bytes(path)
        if raw is None:
            return None
        snapshots[path] = raw
    return snapshots


def _inspection_snapshot_paths(
    run_dir: Path,
    state_path: Path,
    lock_paths: tuple[Path, Path, Path],
) -> tuple[Path, ...] | None:
    try:
        ledger_paths = tuple(
            sorted((run_dir / "ledger").glob("*.redacted.json"))
        )
    except OSError:
        return None
    return (state_path, *ledger_paths, *lock_paths)


def _marker_path(run_dir: Path) -> Path:
    return run_dir / "activation.interruption-reconciliation.redacted.json"


def _blocked(code: str, *, writes_started: bool = False) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED",
        "error": {"code": runner._safe_error_code(code)},
        "writes_started": writes_started,
        "resume_enabled": False,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }
