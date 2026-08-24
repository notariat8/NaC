from __future__ import annotations

import errno
import hashlib
import json
import os
import pwd
import fcntl
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Callable, Protocol

from .azure_activation import build_azure_bff_activation_plan


SCHEMA_VERSION = "nac.m365-azure-bff-live-activation-evidence/v0.1"
LEDGER_SCHEMA_VERSION = "nac.m365-azure-bff-live-activation-event/v0.1"
STATE_SCHEMA_VERSION = "nac.m365-azure-bff-live-activation-resume/v0.1"
FINAL_COMMIT_SCHEMA_VERSION = (
    "nac.m365-azure-bff-live-activation-final-commit/v0.1"
)
SUCCESS_RECEIPT_SCHEMA_VERSION = (
    "nac.m365-azure-bff-live-activation-success-receipt/v0.1"
)
FINALIZATION_RECOVERY_SCHEMA_VERSION = (
    "nac.m365-azure-bff-live-activation-finalization-recovery/v0.1"
)
DEFAULT_OUTPUT_ROOT = Path("out/m365/teams-sharepoint/bff-live-activation")
LIVE_CONTRACT_PATH = Path(
    "workflows/contracts/m365-azure-bff-live-activation.contract.json"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{7,95}$")
_APPROVAL_REFERENCE_RE = re.compile(
    r"^https://github\.com/notariat8/NaC/issues/(?:632|739)#issuecomment-[1-9][0-9]*$"
)
_DIRECTORY_FSYNC_UNSUPPORTED_ERRNOS = frozenset(
    value
    for value in (
        errno.EINVAL,
        errno.EPERM,
        getattr(errno, "ENOTSUP", None),
        getattr(errno, "EOPNOTSUPP", None),
    )
    if value is not None
)
_SAFE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_EVENT_NAME_RE = re.compile(
    r"^(?P<sequence>[0-9]{6})-(?P<step>[a-z0-9_-]+)-(?P<phase>[A-Z_]+)\.redacted\.json$"
)
_ALLOWED_CLASSIFICATIONS = {
    "created", "reused", "updated", "verified", "not_applicable"
}
_ALLOWED_OUTCOME_KEYS = {
    "status", "classification", "code", "stable_error_code",
    "created_count", "reused_count", "updated_count", "verified_count",
    "http_status", "http_status_class", "request_sha256", "response_sha256",
    "reference_sha256", "resource_reference_sha256", "cleanup_verified",
    "prebuilt_inputs_verified", "healthz_before_auth_passed",
    "authenticated_read_passed", "readyz_after_authenticated_read_passed",
    "synthetic_state_restored",
}
_EVIDENCE_KEYS = {
    "schema_version", "status", "started_at_utc", "finished_at_utc",
    "activation_hash", "approved_commit_sha", "approved_tree_sha",
    "approval_reference_sha256", "provisioner_bootstrap_binding_sha256",
    "toolchain_attestations_sha256",
    "target_binding_sha256",
    "permission_boundary_sha256", "ledger_head_sha256", "step_results", "summary",
}
_STEP_EVIDENCE_KEYS = {
    "order", "id", "status", "attempt", "classification", "http_status",
    "stable_error_code", "request_sha256", "response_sha256",
    "resource_reference_sha256",
}
_SUMMARY_EVIDENCE_KEYS = {
    "required_step_count", "passed_step_count", "failed_step_count",
    "duplicate_count", "broader_permission_count", "automatic_rollback_count",
    "automatic_deletion_count", "writes_started", "ledger_hash_chain_valid",
    "prebuilt_inputs_verified", "healthz_before_auth_passed",
    "authenticated_read_passed", "readyz_after_authenticated_read_passed",
    "synthetic_state_restored", "assigned_access_passed",
    "deputy_access_passed", "denied_access_passed",
    "tampered_access_passed", "tampered_workspace_passed",
    "tampered_matter_passed", "tampered_purpose_passed",
    "tampered_filter_passed", "resume_enabled",
}
_SUMMARY_COUNT_KEYS = {
    "required_step_count", "passed_step_count", "failed_step_count",
    "duplicate_count", "broader_permission_count", "automatic_rollback_count",
    "automatic_deletion_count",
}
_SUMMARY_BOOL_KEYS = _SUMMARY_EVIDENCE_KEYS - _SUMMARY_COUNT_KEYS
_HOST_STATE_RELATIVE_PATH = ".local/state/nac/m365-bff-live-activation"
_HOST_LOCK_ROOT = (
    Path(pwd.getpwuid(os.geteuid()).pw_dir) / _HOST_STATE_RELATIVE_PATH
)
_LEGACY_HOST_STATE_RELATIVE_PATH = "nac-m365-bff-live-activation-locks"
_LEGACY_HOST_LOCK_ROOT = (
    Path(tempfile.gettempdir()) / _LEGACY_HOST_STATE_RELATIVE_PATH
)
_MAX_SECURE_ARTIFACT_BYTES = 8 * 1024 * 1024
_GIT_EXECUTABLE = Path("/usr/bin/git")
_STEP_11_SUMMARY_SIGNAL_KEYS = (
    "healthz_before_auth_passed",
    "authenticated_read_passed",
    "readyz_after_authenticated_read_passed",
    "synthetic_state_restored",
)
_STEP_11_ACCESS_SIGNAL_KEYS = (
    "assigned_access_passed",
    "deputy_access_passed",
    "denied_access_passed",
    "tampered_access_passed",
    "tampered_workspace_passed",
    "tampered_matter_passed",
    "tampered_purpose_passed",
    "tampered_filter_passed",
)
_STEP_11_SIGNAL_KEYS = _STEP_11_ACCESS_SIGNAL_KEYS + _STEP_11_SUMMARY_SIGNAL_KEYS

_QUARANTINED_AMBIGUOUS_CODES = frozenset(
    {
        "AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
        "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS",
    }
)


class ActivationExecutionPort(Protocol):
    def verify_prewrite(
        self, context: "ActivationContext", request: "LiveActivationRequest"
    ) -> dict[str, Any]: ...

    def execute_step(
        self, step_id: str, context: "ActivationContext"
    ) -> dict[str, Any]: ...


class ActivationStepError(RuntimeError):
    def __init__(self, code: str) -> None:
        safe_code = _safe_error_code(code)
        super().__init__(safe_code)
        self.code = safe_code


@dataclass(frozen=True, slots=True)
class LiveActivationRequest:
    expected_activation_hash: str
    approved_commit: str
    approved_tree: str
    owner_approval_reference: str
    approval_body_sha256: str
    azure_cli_toolchain_sha256: str
    m365_cli_sha256: str
    m365_node_sha256: str
    build_python_sha256: str
    build_node_sha256: str
    build_npm_cli_sha256: str
    gh_cli_sha256: str
    provisioner_certificate_sha256: str
    provisioner_bootstrap_binding_sha256: str
    reason: str
    correlation_id: str
    owner_approved: bool
    execute_live_activation: bool
    resume: bool = False

    @property
    def toolchain_attestations(self) -> dict[str, str]:
        return {
            "azure_cli_toolchain_sha256": self.azure_cli_toolchain_sha256,
            "m365_cli_sha256": self.m365_cli_sha256,
            "m365_node_sha256": self.m365_node_sha256,
            "build_python_sha256": self.build_python_sha256,
            "build_node_sha256": self.build_node_sha256,
            "build_npm_cli_sha256": self.build_npm_cli_sha256,
            "gh_cli_sha256": self.gh_cli_sha256,
            "provisioner_certificate_sha256": self.provisioner_certificate_sha256,
        }

    @property
    def toolchain_attestations_sha256(self) -> str:
        return _sha256_json(self.toolchain_attestations)


@dataclass(frozen=True, slots=True)
class ActivationContext:
    repo_root: Path
    run_dir: Path
    correlation_reference_sha256: str
    reason_sha256: str
    activation_hash: str
    approved_commit: str
    approved_tree: str


def run_azure_bff_live_activation(
    *,
    repo_root: Path,
    request: LiveActivationRequest,
    execution_port: ActivationExecutionPort,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: Callable[[], datetime] | None = None,
) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    error = _validate_request(request)
    if error:
        return _blocked_result(request, error)

    error = _validate_git_bindings(root, request)
    if error:
        return _blocked_result(request, error)

    plan = build_azure_bff_activation_plan(root)
    error = _validate_initial_bindings(root, request, plan)
    if error:
        return _blocked_result(request, error)
    permission_hash = _permission_boundary_hash(root)
    if permission_hash is None:
        return _blocked_result(request, "PERMISSION_BOUNDARY_INVALID")

    canonical_output_root = (root / DEFAULT_OUTPUT_ROOT).resolve()
    if root not in canonical_output_root.parents:
        return _blocked_result(request, "OUTPUT_SCOPE_REJECTED")
    run_root = output_root if output_root.is_absolute() else root / output_root
    run_root = run_root.expanduser().resolve()
    if run_root != canonical_output_root:
        return _blocked_result(request, "OUTPUT_SCOPE_REJECTED")
    run_dir = (run_root / request.expected_activation_hash).resolve()
    if run_root not in run_dir.parents:
        return _blocked_result(request, "OUTPUT_SCOPE_REJECTED")

    recovery_marker_path = (
        run_dir / "activation.finalization-recovery.redacted.json"
    )

    target_bindings = plan.get("bindings", {})
    target_binding_sha256 = _binding_sha256_json(target_bindings)
    legacy_target_binding_sha256 = _sha256_json(target_bindings)
    global_lock_root = _HOST_LOCK_ROOT.expanduser().absolute()
    legacy_host_lock_root = _LEGACY_HOST_LOCK_ROOT.expanduser().absolute()
    if not _prepare_host_state_root(global_lock_root):
        return _blocked_result(request, "HOST_STATE_ROOT_INVALID")
    if not _prepare_host_state_root(legacy_host_lock_root):
        return _blocked_result(request, "LEGACY_HOST_STATE_ROOT_INVALID")
    lock_path = global_lock_root / f"{target_binding_sha256}.lock"
    legacy_lock_path = global_lock_root / f"{legacy_target_binding_sha256}.lock"
    legacy_host_lock_path = (
        legacy_host_lock_root / f"{legacy_target_binding_sha256}.lock"
    )
    receipt_path = _success_receipt_path(
        global_lock_root, target_binding_sha256, request
    )
    legacy_host_lock_fd = _acquire_lock(
        legacy_host_lock_path, request.expected_activation_hash
    )
    if legacy_host_lock_fd is None:
        return _blocked_result(request, "LEGACY_HOST_ACTIVATION_LOCK_HELD")
    legacy_lock_fd = _acquire_lock(
        legacy_lock_path, request.expected_activation_hash
    )
    if legacy_lock_fd is None:
        _write_lock_marker(
            legacy_host_lock_fd, request.expected_activation_hash, "RELEASED"
        )
        os.close(legacy_host_lock_fd)
        return _blocked_result(request, "LEGACY_ACTIVATION_LOCK_HELD")
    lock_fd = _acquire_lock(lock_path, request.expected_activation_hash)
    if lock_fd is None:
        _write_lock_marker(
            legacy_lock_fd, request.expected_activation_hash, "RELEASED"
        )
        _write_lock_marker(
            legacy_host_lock_fd, request.expected_activation_hash, "RELEASED"
        )
        os.close(legacy_lock_fd)
        os.close(legacy_host_lock_fd)
        receipt_status = _success_receipt_status(
            receipt_path, target_binding_sha256, request
        )
        if receipt_status == "VALID":
            return _blocked_result(request, "ACTIVATION_ALREADY_COMMITTED")
        if receipt_status == "INVALID":
            return _blocked_result(request, "SUCCESS_RECEIPT_INVALID")
        return _blocked_result(request, "ACTIVATION_LOCK_HELD")

    release_lock_marker = True

    def _execute_phase() -> dict[str, Any]:
        nonlocal release_lock_marker
        receipt_status = _success_receipt_status(
            receipt_path, target_binding_sha256, request
        )
        if receipt_status == "VALID":
            return _blocked_result(request, "ACTIVATION_ALREADY_COMMITTED")
        if receipt_status == "INVALID":
            return _blocked_result(request, "SUCCESS_RECEIPT_INVALID")
        run_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(run_root, 0o700)
        ledger_dir = run_dir / "ledger"
        state_path = run_dir / "resume-state.redacted.json"
        evidence_path = run_dir / "activation.redacted.json"
        commit_marker_path = run_dir / "activation.commit.redacted.json"
        recovery_marker_path = (
            run_dir / "activation.finalization-recovery.redacted.json"
        )
        if (
            state_path.exists()
            or ledger_dir.exists()
            or evidence_path.exists()
            or commit_marker_path.exists()
            or recovery_marker_path.exists()
        ):
            return _blocked_result(request, "EXISTING_RUN_REQUIRES_REVIEW")
        if run_dir.exists():
            _cleanup_never_written_run(run_dir, run_root)
        run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(run_dir, 0o700)

        context = ActivationContext(
            repo_root=root,
            run_dir=run_dir,
            correlation_reference_sha256=_sha256(request.owner_approval_reference),
            reason_sha256=_sha256(request.reason),
            activation_hash=request.expected_activation_hash,
            approved_commit=request.approved_commit,
            approved_tree=request.approved_tree,
        )

        try:
            prewrite = execution_port.verify_prewrite(context, request)
        except ActivationStepError as exc:
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, exc.code)
        except Exception:
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, "PREWRITE_VERIFICATION_FAILED")
        if not isinstance(prewrite, dict) or prewrite.get("status") != "PASSED":
            code = prewrite.get("code") if isinstance(prewrite, dict) else None
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(
                request,
                _safe_error_code(
                    code if isinstance(code, str) else "PREWRITE_VERIFICATION_FAILED"
                ),
            )

        if type(prewrite.get("prebuilt_inputs_verified")) is not bool:
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, "PREWRITE_RESULT_INVALID")

        final_plan = build_azure_bff_activation_plan(root)
        final_error = _validate_final_bindings(root, request, final_plan)
        if final_error:
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, "FINAL_PREWRITE_BINDING_MISMATCH")
        if (
            _binding_sha256_json(final_plan.get("bindings", {}))
            != target_binding_sha256
        ):
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, "TARGET_BINDING_MISMATCH")
        if _permission_boundary_hash(root) != permission_hash:
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, "PERMISSION_BOUNDARY_MISMATCH")
        if (
            _head_commit(root) != request.approved_commit
            or _head_tree(root) != request.approved_tree
            or not _clean_tree(root)
        ):
            _cleanup_never_written_run(run_dir, run_root)
            return _blocked_result(request, "FINAL_PREWRITE_BINDING_MISMATCH")

        state, error = _load_or_initialize_state(
            state_path, ledger_dir, request, final_plan, permission_hash, False, now
        )
        if error:
            return _blocked_result(request, error)
        state["prebuilt_inputs_verified"] = prewrite[
            "prebuilt_inputs_verified"
        ]
        _append_event(
            ledger_dir, state, step_id="runner", phase="PRE_WRITE_BINDING",
            status="LIVE_APPROVED", attempt=int(state["run_attempt"]), now=now
        )
        _atomic_json_write(state_path, state)

        for order, step in enumerate(final_plan["steps"], start=1):
            release_lock_marker = False
            step_id = step["id"]
            prior = _state_step(state, step_id)
            attempt = int(prior.get("attempt", 0)) + 1 if prior else 1
            state["writes_started"] = True
            _set_state_step(
                state,
                _step_record(order, step_id, "RUNNING", attempt, "not_applicable"),
            )
            _append_event(
                ledger_dir, state, step_id=step_id, phase="RUNNING",
                status="RUNNING", attempt=attempt, now=now
            )
            _atomic_json_write(state_path, state)
            try:
                outcome = _sanitize_outcome(
                    execution_port.execute_step(step_id, context),
                    step_id=step_id,
                )
            except ActivationStepError as exc:
                result, release_lock_marker = _fail_partial(
                    state, ledger_dir, state_path, evidence_path, request, step_id,
                    exc.code, now
                )
                return result
            except Exception:
                result, release_lock_marker = _fail_partial(
                    state, ledger_dir, state_path, evidence_path, request, step_id,
                    "STEP_FAILED", now
                )
                return result
            if outcome["status"] != "PASSED":
                result, release_lock_marker = _fail_partial(
                    state, ledger_dir, state_path, evidence_path, request, step_id,
                    outcome["stable_error_code"] or "STEP_FAILED", now
                )
                return result
            if (
                step_id == "ensure_entra_api_application"
                and outcome.get("prebuilt_inputs_verified") is not True
            ):
                result, release_lock_marker = _fail_partial(
                    state,
                    ledger_dir,
                    state_path,
                    evidence_path,
                    request,
                    step_id,
                    "PREBUILT_INPUTS_NOT_VERIFIED",
                    now,
                )
                return result
            signal_error = _required_summary_signal_error(step_id, outcome)
            if signal_error is not None:
                result, release_lock_marker = _fail_partial(
                    state,
                    ledger_dir,
                    state_path,
                    evidence_path,
                    request,
                    step_id,
                    signal_error,
                    now,
                )
                return result

            record = _step_record(
                order, step_id, "PASSED", attempt,
                outcome["classification"], outcome
            )
            _set_state_step(state, record)
            _record_summary_signals(state, step_id, outcome)
            _append_event(
                ledger_dir, state, step_id=step_id, phase="PASSED",
                status="PASSED", attempt=attempt, outcome=record, now=now
            )
            _atomic_json_write(state_path, state)

        state["status"] = "FINALIZING"
        state["finished_at_utc"] = _utc_now(now)
        _append_event(
            ledger_dir, state, step_id="runner", phase="TERMINAL",
            status="FINALIZING", attempt=int(state["run_attempt"]), now=now
        )
        _atomic_json_write(state_path, state)
        try:
            _atomic_json_write(
                recovery_marker_path,
                _finalization_recovery_marker(
                    state,
                    request,
                    status="FINALIZATION_IN_PROGRESS",
                    error_code=None,
                    state_path=state_path,
                    evidence_path=evidence_path,
                    commit_marker_path=commit_marker_path,
                    receipt_path=receipt_path,
                ),
            )
            _record_lock_release_authorization(
                ledger_dir, state, state_path, now
            )
            if not _terminal_chain_is_valid(state, ledger_dir):
                raise ActivationStepError("LEDGER_CHAIN_INVALID")
            committed_state = dict(state)
            committed_state["status"] = "PASSED"
            committed_state["ledger_hash_chain_valid"] = True
            evidence = _evidence_from_state(committed_state)
            _validate_evidence(evidence)
            _atomic_json_write(evidence_path, evidence)
            _atomic_json_write(
                commit_marker_path, _final_commit_marker(evidence)
            )
            state.update(committed_state)
            _atomic_json_write(state_path, state)
            if not _committed_artifacts_are_valid(
                state_path,
                evidence_path,
                commit_marker_path,
                ledger_dir,
                state,
                request,
            ):
                raise ActivationStepError("FINAL_COMMIT_VERIFICATION_FAILED")
            receipt = _success_receipt(
                state,
                evidence_path,
                commit_marker_path,
                state_path,
            )
            _atomic_json_create(receipt_path, receipt)
            if _success_receipt_status(
                receipt_path, target_binding_sha256, request
            ) != "VALID":
                raise ActivationStepError("SUCCESS_RECEIPT_INVALID")
            if _load_existing_evidence(
                evidence_path, request, receipt_path=receipt_path
            ) != evidence:
                raise ActivationStepError("FINAL_COMMIT_VERIFICATION_FAILED")
            release_lock_marker = False
            try:
                _release_lock_markers_verified(
                    (lock_fd, legacy_lock_fd, legacy_host_lock_fd),
                    request.expected_activation_hash,
                )
            except Exception:
                return _failed_execution_result(
                    request, "FINALIZATION_LOCK_RELEASE_FAILED"
                )
            try:
                _unlink_and_fsync(recovery_marker_path)
            except OSError:
                return _failed_execution_result(
                    request,
                    "FINALIZATION_RECOVERY_MARKER_CLEANUP_FAILED",
                )
            return evidence
        except Exception as exc:
            code = (
                exc.code
                if isinstance(exc, ActivationStepError)
                else "FINALIZATION_FAILED"
            )
            return _record_finalization_failure(
                state=state,
                ledger_dir=ledger_dir,
                state_path=state_path,
                evidence_path=evidence_path,
                commit_marker_path=commit_marker_path,
                recovery_marker_path=recovery_marker_path,
                receipt_path=receipt_path,
                request=request,
                code=code,
                now=now,
            )

    primary_result: dict[str, Any] | None = None
    pending_exception: BaseException | None = None
    release_error: Exception | None = None
    recoverable_marker: dict[str, Any] | None = None
    try:
        primary_result = _execute_phase()
    except BaseException as exc:
        # Capture any exception (including BaseException subclasses such as
        # KeyboardInterrupt or test-injected crashes) so the lock cleanup
        # below always runs; we re-raise it after the release decision.
        pending_exception = exc
    finally:
        # Release the host locks and verify the release markers.  This
        # cleanup runs for every outcome (success, failure, exception) and
        # must not be skipped.  A terminal release failure overrides the
        # primary result; a non-terminal release error is re-raised so the
        # caller sees the lock release failure rather than the primary
        # outcome.  This previously used return/raise inside a finally block
        # (now a SyntaxWarning in 3.14); the decision is now made after the
        # cleanup so the control flow is explicit.
        if release_lock_marker:
            try:
                _release_lock_markers_verified(
                    (lock_fd, legacy_lock_fd, legacy_host_lock_fd),
                    request.expected_activation_hash,
                )
                if recovery_marker_path.exists():
                    _unlink_and_fsync(recovery_marker_path)
            except Exception as exc:
                release_error = exc
        for descriptor in (lock_fd, legacy_lock_fd, legacy_host_lock_fd):
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        recoverable_marker = _read_secure_canonical_json(
            recovery_marker_path
        )

    # Release decision (made after cleanup so no return/raise sits in a
    # finally block).  A terminal release failure overrides every primary
    # outcome; a non-terminal release error is re-raised; otherwise the
    # pending exception (if any) is re-raised, else the primary result is
    # returned.
    if release_error is not None:
        if (
            isinstance(recoverable_marker, dict)
            and recoverable_marker.get("status")
            == "TERMINAL_RELEASE_IN_PROGRESS"
        ):
            return _failed_execution_result(
                request,
                "TERMINAL_LOCK_RELEASE_RECOVERY_REQUIRED",
            )
        raise release_error
    if pending_exception is not None:
        raise pending_exception
    assert primary_result is not None
    return primary_result


def reconcile_azure_bff_live_activation_lock(
    *,
    repo_root: Path,
    request: LiveActivationRequest,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    confirm_unlock: bool = False,
) -> dict[str, Any]:
    error = _validate_request(request)
    if error:
        return _blocked_result(request, error)
    root = repo_root.expanduser().resolve()
    canonical_output_root = (root / DEFAULT_OUTPUT_ROOT).resolve()
    run_root = output_root if output_root.is_absolute() else root / output_root
    run_root = run_root.expanduser().resolve()
    if run_root != canonical_output_root or root not in run_root.parents:
        return _blocked_result(request, "OUTPUT_SCOPE_REJECTED")
    run_dir = (run_root / request.expected_activation_hash).resolve()
    if run_dir.parent != run_root:
        return _blocked_result(request, "OUTPUT_SCOPE_REJECTED")

    state_path = run_dir / "resume-state.redacted.json"
    ledger_dir = run_dir / "ledger"
    evidence_path = run_dir / "activation.redacted.json"
    commit_marker_path = run_dir / "activation.commit.redacted.json"
    recovery_marker_path = run_dir / "activation.finalization-recovery.redacted.json"
    reconciled_marker_path = run_dir / "activation.finalization-reconciled.redacted.json"
    state = _read_secure_canonical_json(state_path)
    if state is None or not _recovery_state_matches_request(state, request):
        return _failed_execution_result(request, "FINALIZATION_STATE_INVALID")
    target_binding_sha256 = state.get("target_binding_sha256")
    if not isinstance(target_binding_sha256, str) or not _SHA256_RE.fullmatch(target_binding_sha256):
        return _failed_execution_result(request, "FINALIZATION_STATE_INVALID")
    global_lock_root = _HOST_LOCK_ROOT.expanduser().absolute()
    if not _existing_host_state_root_is_valid(global_lock_root):
        return _failed_execution_result(request, "HOST_STATE_ROOT_INVALID")
    lock_path = global_lock_root / f"{target_binding_sha256}.lock"
    legacy_target_binding_sha256 = state.get("legacy_target_binding_sha256")
    if (
        not isinstance(legacy_target_binding_sha256, str)
        or not _SHA256_RE.fullmatch(legacy_target_binding_sha256)
    ):
        return _failed_execution_result(request, "FINALIZATION_STATE_INVALID")
    legacy_lock_path = global_lock_root / f"{legacy_target_binding_sha256}.lock"
    legacy_host_lock_root = _LEGACY_HOST_LOCK_ROOT.expanduser().absolute()
    if not _existing_host_state_root_is_valid(legacy_host_lock_root):
        return _failed_execution_result(
            request, "LEGACY_HOST_STATE_ROOT_INVALID"
        )
    legacy_host_lock_path = (
        legacy_host_lock_root / f"{legacy_target_binding_sha256}.lock"
    )
    lock_fd, lock_error = _acquire_existing_lock_for_recovery(lock_path)
    if lock_error:
        return _failed_execution_result(request, lock_error)
    assert lock_fd is not None
    legacy_lock_fd: int | None = None
    legacy_host_lock_fd: int | None = None
    try:
        lock = _read_lock_marker_descriptor(lock_fd)
        legacy_lock_fd, legacy_lock_error = (
            _acquire_existing_lock_for_recovery(legacy_lock_path)
        )
        if legacy_lock_error or legacy_lock_fd is None:
            return _failed_execution_result(
                request, "LEGACY_ACTIVATION_LOCK_INVALID"
            )
        legacy_lock = _read_lock_marker_descriptor(legacy_lock_fd)
        legacy_host_lock_fd, legacy_host_lock_error = (
            _acquire_existing_lock_for_recovery(legacy_host_lock_path)
        )
        if legacy_host_lock_error or legacy_host_lock_fd is None:
            return _failed_execution_result(
                request, "LEGACY_HOST_ACTIVATION_LOCK_INVALID"
            )
        legacy_host_lock = _read_lock_marker_descriptor(legacy_host_lock_fd)
        if not _terminal_chain_is_valid(state, ledger_dir):
            return _failed_execution_result(request, "LEDGER_CHAIN_INVALID")
        marker = _read_secure_canonical_json(recovery_marker_path)
        receipt_path = _success_receipt_path(
            global_lock_root, target_binding_sha256, request
        )
        terminal_release_pending = bool(
            state.get("status") == "FAILED_PARTIAL"
            and isinstance(marker, dict)
            and marker.get("status") == "TERMINAL_RELEASE_IN_PROGRESS"
            and _finalization_recovery_marker_is_valid(
                marker,
                state=state,
                request=request,
                state_path=state_path,
                evidence_path=evidence_path,
                commit_marker_path=commit_marker_path,
                receipt_path=receipt_path,
            )
        )
        passed_steps = [
            step for step in state.get("steps", [])
            if isinstance(step, dict) and step.get("status") == "PASSED"
        ]
        failed_steps = [
            step for step in state.get("steps", [])
            if isinstance(step, dict) and step.get("status") == "FAILED"
        ]
        if not terminal_release_pending and (
            len(passed_steps) != 12 or failed_steps
        ):
            return _failed_execution_result(
                request, "FINALIZATION_STATE_INVALID"
            )
        if terminal_release_pending and len(failed_steps) != 1:
            return _failed_execution_result(
                request, "FINALIZATION_STATE_INVALID"
            )
        committed = _committed_recovery_state_is_valid(
            state=state,
            state_path=state_path,
            evidence_path=evidence_path,
            commit_marker_path=commit_marker_path,
            ledger_dir=ledger_dir,
            receipt_path=receipt_path,
            target_binding_sha256=target_binding_sha256,
            request=request,
        )
        reconciled_candidate = _reconcile_marker_payload(
            state=state,
            request=request,
            state_path=state_path,
            lock_path=lock_path,
            target_binding_sha256=target_binding_sha256,
            committed=committed,
        )
        existing_reconciled = _read_secure_canonical_json(
            reconciled_marker_path
        )
        if reconciled_marker_path.exists() and not _reconcile_marker_matches(
            existing_reconciled, reconciled_candidate
        ):
            return _failed_execution_result(
                request, "FINALIZATION_RECONCILE_INVALID"
            )
        reconcile_authorized = _reconcile_marker_matches(
            existing_reconciled, reconciled_candidate
        )
        allow_released_markers = (
            committed or reconcile_authorized or terminal_release_pending
        )
        for lock_marker, error_code in (
            (lock, "ACTIVATION_LOCK_INVALID"),
            (legacy_lock, "LEGACY_ACTIVATION_LOCK_INVALID"),
            (legacy_host_lock, "LEGACY_HOST_ACTIVATION_LOCK_INVALID"),
        ):
            if not _recovery_lock_marker_matches(
                lock_marker,
                request.expected_activation_hash,
                committed=allow_released_markers,
            ):
                return _failed_execution_result(request, error_code)
        all_markers_released = all(
            _released_lock_marker_matches(
                item, request.expected_activation_hash
            )
            for item in (lock, legacy_lock, legacy_host_lock)
        )
        if (not committed or not all_markers_released) and not (
            _finalization_recovery_marker_is_valid(
                marker,
                state=state,
                request=request,
                state_path=state_path,
                evidence_path=evidence_path,
                commit_marker_path=commit_marker_path,
                receipt_path=receipt_path,
            )
        ):
            return _failed_execution_result(
                request, "FINALIZATION_RECOVERY_MARKER_INVALID"
            )
        inspection = {
            "status": "FAILED_PARTIAL",
            "writes_started": True,
            "error": {
                "code": (
                    "FINALIZATION_STALE_SUCCESS_LOCK"
                    if committed
                    else (
                        "TERMINAL_LOCK_RELEASE_RECOVERY_REQUIRED"
                        if terminal_release_pending
                        else "FINALIZATION_RECOVERY_REQUIRED"
                    )
                )
            },
            "recovery": {
                "lock_held": True,
                "committed_artifacts_valid": committed,
                "resume_enabled": False,
                "state_sha256": _artifact_sha256(state_path),
                "ledger_head_sha256": state["ledger_head_sha256"],
            },
        }
        if not confirm_unlock:
            return inspection
        if not reconcile_authorized:
            _atomic_json_create(
                reconciled_marker_path, reconciled_candidate
            )
            existing_reconciled = _read_secure_canonical_json(
                reconciled_marker_path
            )
            if existing_reconciled != reconciled_candidate:
                raise ActivationStepError(
                    "FINALIZATION_RECONCILE_INVALID"
                )
        assert existing_reconciled is not None
        try:
            _release_lock_markers_verified(
                (lock_fd, legacy_lock_fd, legacy_host_lock_fd),
                request.expected_activation_hash,
            )
        except Exception:
            return _failed_execution_result(
                request, "FINALIZATION_LOCK_RELEASE_FAILED"
            )
        return {
            **inspection,
            "error": {"code": "FINALIZATION_LOCK_RECONCILED"},
            "recovery": {
                **inspection["recovery"],
                "lock_held": False,
                "reconcile_marker_sha256": _artifact_sha256(reconciled_marker_path),
            },
        }
    except ActivationStepError as exc:
        return _failed_execution_result(request, exc.code)
    except Exception:
        return _failed_execution_result(request, "FINALIZATION_RECONCILE_FAILED")
    finally:
        for descriptor in (legacy_lock_fd, legacy_host_lock_fd):
            if descriptor is None:
                continue
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally:
            os.close(lock_fd)


def _record_finalization_failure(
    *,
    state: dict[str, Any],
    ledger_dir: Path,
    state_path: Path,
    evidence_path: Path,
    commit_marker_path: Path,
    recovery_marker_path: Path,
    receipt_path: Path,
    request: LiveActivationRequest,
    code: str,
    now: Callable[[], datetime] | None,
) -> dict[str, Any]:
    safe_code = _safe_error_code(code)
    state["status"] = "FINALIZATION_FAILED"
    state["ledger_hash_chain_valid"] = False
    try:
        _append_event(
            ledger_dir,
            state,
            step_id="runner",
            phase="FINALIZATION_FAILED",
            status="FINALIZATION_FAILED",
            attempt=int(state["run_attempt"]),
            outcome={"stable_error_code": safe_code},
            now=now,
        )
        _atomic_json_write(state_path, state)
    except Exception:
        pass
    try:
        marker = _finalization_recovery_marker(
            state,
            request,
            status="FINALIZATION_FAILED",
            error_code=safe_code,
            state_path=state_path,
            evidence_path=evidence_path,
            commit_marker_path=commit_marker_path,
            receipt_path=receipt_path,
        )
        _atomic_json_write(recovery_marker_path, marker)
    except Exception:
        return _failed_execution_result(request, "FINALIZATION_RECOVERY_MARKER_FAILED")
    return _failed_execution_result(request, safe_code)


def _finalization_recovery_marker(
    state: dict[str, Any],
    request: LiveActivationRequest,
    *,
    status: str,
    error_code: str | None,
    state_path: Path,
    evidence_path: Path,
    commit_marker_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": FINALIZATION_RECOVERY_SCHEMA_VERSION,
        "status": status,
        "error_code": error_code,
        "activation_hash": request.expected_activation_hash,
        "approval_body_sha256": request.approval_body_sha256,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
        "target_binding_sha256": state["target_binding_sha256"],
        "permission_boundary_sha256": state["permission_boundary_sha256"],
        "ledger_head_sha256": state["ledger_head_sha256"],
        "state_sha256": _artifact_sha256(state_path),
        "evidence_sha256": _artifact_sha256(evidence_path),
        "final_commit_marker_sha256": _artifact_sha256(commit_marker_path),
        "success_receipt_sha256": _artifact_sha256(receipt_path),
        "resume_enabled": False,
    }


def _finalization_recovery_marker_is_valid(
    marker: dict[str, Any] | None,
    *,
    state: dict[str, Any],
    request: LiveActivationRequest,
    state_path: Path,
    evidence_path: Path,
    commit_marker_path: Path,
    receipt_path: Path,
) -> bool:
    if marker is None:
        return False
    expected_keys = {
        "schema_version", "status", "error_code", "activation_hash",
        "approval_body_sha256", "approval_reference_sha256",
        "approved_commit_sha", "approved_tree_sha",
        "provisioner_bootstrap_binding_sha256",
        "toolchain_attestations_sha256", "target_binding_sha256",
        "permission_boundary_sha256", "ledger_head_sha256", "state_sha256",
        "evidence_sha256", "final_commit_marker_sha256",
        "success_receipt_sha256", "resume_enabled",
    }
    if set(marker) != expected_keys or marker.get("schema_version") != FINALIZATION_RECOVERY_SCHEMA_VERSION:
        return False
    if marker.get("status") not in {
        "FINALIZATION_IN_PROGRESS",
        "FINALIZATION_FAILED",
        "TERMINAL_RELEASE_IN_PROGRESS",
    }:
        return False
    if marker.get("resume_enabled") is not False:
        return False
    expected = {
        "activation_hash": request.expected_activation_hash,
        "approval_body_sha256": request.approval_body_sha256,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
        "target_binding_sha256": state["target_binding_sha256"],
        "permission_boundary_sha256": state["permission_boundary_sha256"],
    }
    if any(marker.get(key) != value for key, value in expected.items()):
        return False
    error_code = marker.get("error_code")
    if marker["status"] in {
        "FINALIZATION_FAILED",
        "TERMINAL_RELEASE_IN_PROGRESS",
    } and not (
        isinstance(error_code, str) and _SAFE_CODE_RE.fullmatch(error_code)
    ):
        return False
    if marker["status"] == "FINALIZATION_IN_PROGRESS" and error_code is not None:
        return False
    if (
        marker["status"] == "TERMINAL_RELEASE_IN_PROGRESS"
        and state.get("status") != "FAILED_PARTIAL"
    ):
        return False
    for key in (
        "ledger_head_sha256", "state_sha256", "evidence_sha256",
        "final_commit_marker_sha256", "success_receipt_sha256",
    ):
        value = marker.get(key)
        if value is not None and not (
            isinstance(value, str) and _SHA256_RE.fullmatch(value)
        ):
            return False
    if marker["status"] in {
        "FINALIZATION_FAILED",
        "TERMINAL_RELEASE_IN_PROGRESS",
    }:
        current = {
            "ledger_head_sha256": state["ledger_head_sha256"],
            "state_sha256": _artifact_sha256(state_path),
            "evidence_sha256": _artifact_sha256(evidence_path),
            "final_commit_marker_sha256": _artifact_sha256(commit_marker_path),
            "success_receipt_sha256": _artifact_sha256(receipt_path),
        }
        if any(marker.get(key) != value for key, value in current.items()):
            return False
    return True


def _recovery_state_matches_request(
    state: dict[str, Any], request: LiveActivationRequest
) -> bool:
    expected = {
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "approval_body_sha256": request.approval_body_sha256,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
    }
    return all(state.get(key) == value for key, value in expected.items()) and (
        state.get("status") in {
            "FINALIZING",
            "FINALIZATION_FAILED",
            "FAILED_PARTIAL",
            "PASSED",
        }
    )


def _committed_recovery_state_is_valid(
    *,
    state: dict[str, Any],
    state_path: Path,
    evidence_path: Path,
    commit_marker_path: Path,
    ledger_dir: Path,
    receipt_path: Path,
    target_binding_sha256: str,
    request: LiveActivationRequest,
) -> bool:
    return bool(
        state.get("status") == "PASSED"
        and _committed_artifacts_are_valid(
            state_path,
            evidence_path,
            commit_marker_path,
            ledger_dir,
            state,
            request,
        )
        and _success_receipt_status(
            receipt_path, target_binding_sha256, request
        ) == "VALID"
        and _load_existing_evidence(
            evidence_path, request, receipt_path=receipt_path
        ).get("status") == "PASSED"
    )


def _reconcile_marker_payload(
    *,
    state: dict[str, Any],
    request: LiveActivationRequest,
    state_path: Path,
    lock_path: Path,
    target_binding_sha256: str,
    committed: bool,
) -> dict[str, Any]:
    return {
        "schema_version": FINALIZATION_RECOVERY_SCHEMA_VERSION,
        "status": "LOCK_RELEASE_AUTHORIZED_BY_RECONCILE",
        "activation_hash": request.expected_activation_hash,
        "approval_body_sha256": request.approval_body_sha256,
        "approval_reference_sha256": _sha256(
            request.owner_approval_reference
        ),
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": (
            request.toolchain_attestations_sha256
        ),
        "target_binding_sha256": target_binding_sha256,
        "state_sha256": _artifact_sha256(state_path),
        "ledger_head_sha256": state["ledger_head_sha256"],
        "lock_sha256": _artifact_sha256(lock_path),
        "committed_artifacts_valid": committed,
        "resume_enabled": False,
    }


def _reconcile_marker_matches(
    marker: dict[str, Any] | None, candidate: dict[str, Any]
) -> bool:
    if not isinstance(marker, dict) or set(marker) != set(candidate):
        return False
    lock_sha256 = marker.get("lock_sha256")
    if not isinstance(lock_sha256, str) or not _SHA256_RE.fullmatch(
        lock_sha256
    ):
        return False
    return all(
        marker.get(key) == value
        for key, value in candidate.items()
        if key != "lock_sha256"
    )


def _artifact_sha256(path: Path) -> str | None:
    raw = _read_secure_artifact_bytes(path)
    return hashlib.sha256(raw).hexdigest() if raw is not None else None


def _acquire_existing_lock_for_recovery(
    path: Path,
) -> tuple[int | None, str | None]:
    descriptor: int | None = None
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return None, "FINALIZATION_LOCK_NOT_HELD"
    except OSError:
        return None, "ACTIVATION_LOCK_INVALID"
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
    ):
        return None, "ACTIVATION_LOCK_INVALID"
    try:
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        opened = os.fstat(descriptor)
        if opened.st_ino != metadata.st_ino or opened.st_dev != metadata.st_dev:
            os.close(descriptor)
            return None, "ACTIVATION_LOCK_INVALID"
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return descriptor, None
    except BlockingIOError:
        if descriptor is not None:
            os.close(descriptor)
        return None, "ACTIVATION_LOCK_ACTIVE"
    except OSError:
        if descriptor is not None:
            os.close(descriptor)
        return None, "ACTIVATION_LOCK_INVALID"


def _validate_request(request: LiveActivationRequest) -> str | None:
    if request.resume is not False:
        return "RESUME_DISABLED_FOR_MVP"
    if request.owner_approved is not True or request.execute_live_activation is not True:
        return "OWNER_GATE_CLOSED"
    if not _SHA256_RE.fullmatch(request.expected_activation_hash):
        return "ACTIVATION_HASH_INVALID"
    if not _COMMIT_RE.fullmatch(request.approved_commit):
        return "APPROVED_COMMIT_INVALID"
    if not _COMMIT_RE.fullmatch(request.approved_tree):
        return "APPROVED_TREE_INVALID"
    if not _APPROVAL_REFERENCE_RE.fullmatch(request.owner_approval_reference.strip()):
        return "APPROVAL_REFERENCE_INVALID"
    if not _SHA256_RE.fullmatch(request.approval_body_sha256):
        return "APPROVAL_BODY_HASH_INVALID"
    if not _SHA256_RE.fullmatch(
        request.provisioner_bootstrap_binding_sha256
    ):
        return "PROVISIONER_BOOTSTRAP_BINDING_INVALID"
    if any(
        not _SHA256_RE.fullmatch(value)
        for value in request.toolchain_attestations.values()
    ):
        return "TOOLCHAIN_ATTESTATION_INVALID"
    if len(request.reason.strip()) < 8:
        return "APPROVAL_REASON_REQUIRED"
    if not _CORRELATION_RE.fullmatch(request.correlation_id):
        return "CORRELATION_ID_INVALID"
    return None


def _validate_git_bindings(
    root: Path, request: LiveActivationRequest
) -> str | None:
    if _head_commit(root) != request.approved_commit:
        return "APPROVED_COMMIT_MISMATCH"
    if _head_tree(root) != request.approved_tree:
        return "APPROVED_TREE_MISMATCH"
    if not _clean_tree(root):
        return "GIT_WORKTREE_NOT_CLEAN"
    return None


def _validate_initial_bindings(
    root: Path, request: LiveActivationRequest, plan: dict[str, Any]
) -> str | None:
    if plan.get("status") != "READY":
        return "OFFLINE_PLAN_NOT_READY"
    if plan.get("activation_hash") != request.expected_activation_hash:
        return "ACTIVATION_HASH_MISMATCH"
    if plan.get("source_control", {}).get("commit") != request.approved_commit:
        return "APPROVED_COMMIT_MISMATCH"
    if _head_commit(root) != request.approved_commit:
        return "APPROVED_COMMIT_MISMATCH"
    if _head_tree(root) != request.approved_tree:
        return "APPROVED_TREE_MISMATCH"
    if not _clean_tree(root):
        return "GIT_WORKTREE_NOT_CLEAN"
    return None


def _validate_final_bindings(
    root: Path, request: LiveActivationRequest, plan: dict[str, Any]
) -> bool:
    return bool(
        plan.get("status") != "READY"
        or plan.get("activation_hash") != request.expected_activation_hash
        or plan.get("source_control", {}).get("commit") != request.approved_commit
        or _head_commit(root) != request.approved_commit
        or _head_tree(root) != request.approved_tree
        or not _clean_tree(root)
    )


def _clean_tree(root: Path) -> bool:
    git = _trusted_git_executable()
    if git is None:
        return False
    try:
        completed = subprocess.run(
            [
                git, "--no-optional-locks", "-C", str(root), "status",
                "--porcelain=v1", "--untracked-files=all",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0 and completed.stdout == ""


def _head_commit(root: Path) -> str | None:
    return _git_object(root, ["rev-parse", "HEAD"])


def _head_tree(root: Path) -> str | None:
    return _git_object(root, ["rev-parse", "HEAD^{tree}"])


def _git_object(root: Path, argv: list[str]) -> str | None:
    git = _trusted_git_executable()
    if git is None:
        return None
    try:
        completed = subprocess.run(
            [git, "--no-optional-locks", "-C", str(root), *argv],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip().lower()
    return value if completed.returncode == 0 and _COMMIT_RE.fullmatch(value) else None


def _trusted_git_executable() -> str | None:
    try:
        metadata = _GIT_EXECUTABLE.stat()
    except OSError:
        return None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
    ):
        return None
    return str(_GIT_EXECUTABLE)


def _permission_boundary_hash(root: Path) -> str | None:
    try:
        contract = json.loads((root / LIVE_CONTRACT_PATH).read_text(encoding="utf-8"))
        boundary = contract["permission_boundary"]
    except (OSError, KeyError, json.JSONDecodeError, TypeError):
        return None
    return _binding_sha256_json(boundary)


def _prepare_host_state_root(root: Path) -> bool:
    try:
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        receipts = root / "success-receipts"
        receipts.mkdir(exist_ok=True, mode=0o700)
    except OSError:
        return False
    return _secure_host_directory(root) and _secure_host_directory(receipts)


def _existing_host_state_root_is_valid(root: Path) -> bool:
    return _secure_host_directory(root) and _secure_host_directory(
        root / "success-receipts"
    )


def _secure_host_directory(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return bool(
        stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o700
    )


def _receipt_bindings(
    target_binding_sha256: str, request: LiveActivationRequest
) -> dict[str, str]:
    return {
        "activation_hash": request.expected_activation_hash,
        "approval_body_sha256": request.approval_body_sha256,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
        "target_binding_sha256": target_binding_sha256,
    }


def _success_receipt_path(
    root: Path,
    target_binding_sha256: str,
    request: LiveActivationRequest,
) -> Path:
    binding_sha256 = _sha256_json(
        _receipt_bindings(target_binding_sha256, request)
    )
    return root / "success-receipts" / f"{binding_sha256}.success.redacted.json"


def _success_receipt(
    state: dict[str, Any],
    evidence_path: Path,
    commit_marker_path: Path,
    state_path: Path,
) -> dict[str, Any]:
    artifact_hashes = {
        "evidence_sha256": _artifact_sha256(evidence_path),
        "final_commit_marker_sha256": _artifact_sha256(commit_marker_path),
        "final_state_sha256": _artifact_sha256(state_path),
    }
    if any(value is None for value in artifact_hashes.values()):
        raise ActivationStepError(
            "SUCCESS_RECEIPT_SOURCE_ARTIFACT_INVALID"
        )
    payload = {
        "schema_version": SUCCESS_RECEIPT_SCHEMA_VERSION,
        "status": "COMMITTED",
        "activation_hash": state["activation_hash"],
        "approval_body_sha256": state["approval_body_sha256"],
        "approval_reference_sha256": state["approval_reference_sha256"],
        "approved_commit_sha": state["approved_commit_sha"],
        "approved_tree_sha": state["approved_tree_sha"],
        "provisioner_bootstrap_binding_sha256": state[
            "provisioner_bootstrap_binding_sha256"
        ],
        "toolchain_attestations_sha256": state["toolchain_attestations_sha256"],
        "target_binding_sha256": state["target_binding_sha256"],
        **artifact_hashes,
    }
    payload["receipt_sha256"] = _sha256_json(payload)
    return payload


def _success_receipt_status(
    path: Path,
    target_binding_sha256: str,
    request: LiveActivationRequest,
) -> str:
    try:
        path.lstat()
    except FileNotFoundError:
        return "MISSING"
    except OSError:
        return "INVALID"
    receipt = _read_secure_canonical_json(path)
    if receipt is None:
        return "INVALID"
    expected_keys = {
        "schema_version", "status", "activation_hash",
        "approval_body_sha256", "approval_reference_sha256",
        "approved_commit_sha", "approved_tree_sha",
        "provisioner_bootstrap_binding_sha256",
        "toolchain_attestations_sha256", "target_binding_sha256",
        "evidence_sha256", "final_commit_marker_sha256",
        "final_state_sha256", "receipt_sha256",
    }
    if set(receipt) != expected_keys:
        return "INVALID"
    expected_bindings = _receipt_bindings(target_binding_sha256, request)
    if (
        receipt.get("schema_version") != SUCCESS_RECEIPT_SCHEMA_VERSION
        or receipt.get("status") != "COMMITTED"
        or any(receipt.get(key) != value for key, value in expected_bindings.items())
    ):
        return "INVALID"
    for key in (
        "evidence_sha256", "final_commit_marker_sha256",
        "final_state_sha256", "receipt_sha256",
    ):
        if not isinstance(receipt.get(key), str) or not _SHA256_RE.fullmatch(
            receipt[key]
        ):
            return "INVALID"
    claimed_hash = receipt["receipt_sha256"]
    unhashed = dict(receipt)
    del unhashed["receipt_sha256"]
    return "VALID" if _sha256_json(unhashed) == claimed_hash else "INVALID"


def _read_secure_canonical_json(path: Path) -> dict[str, Any] | None:
    return _decode_canonical_json(_read_secure_artifact_bytes(path))


def _read_secure_canonical_json_descriptor(
    descriptor: int,
) -> dict[str, Any] | None:
    try:
        opened = os.fstat(descriptor)
        if (
            not _trusted_secure_artifact_metadata(opened)
            or opened.st_size < 1
            or opened.st_size > _MAX_SECURE_ARTIFACT_BYTES
        ):
            return None
        os.lseek(descriptor, 0, os.SEEK_SET)
        raw = _read_bounded_descriptor(descriptor)
        after = os.fstat(descriptor)
        if raw is None or not _same_secure_snapshot(opened, after):
            return None
        return _decode_canonical_json(raw)
    except OSError:
        return None


def _read_secure_artifact_bytes(path: Path) -> bytes | None:
    descriptor: int | None = None
    try:
        before = path.lstat()
        if (
            not _trusted_secure_artifact_metadata(before)
            or before.st_size < 1
            or before.st_size > _MAX_SECURE_ARTIFACT_BYTES
        ):
            return None
        descriptor = os.open(
            path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        opened = os.fstat(descriptor)
        if not _same_secure_snapshot(before, opened):
            return None
        raw = _read_bounded_descriptor(descriptor)
        after = os.fstat(descriptor)
        if raw is None or not _same_secure_snapshot(opened, after):
            return None
        return raw
    except OSError:
        return None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _read_bounded_descriptor(descriptor: int) -> bytes | None:
    chunks: list[bytes] = []
    total = 0
    while total <= _MAX_SECURE_ARTIFACT_BYTES:
        chunk = os.read(
            descriptor,
            min(65536, _MAX_SECURE_ARTIFACT_BYTES + 1 - total),
        )
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
    return None


def _trusted_secure_artifact_metadata(metadata: os.stat_result) -> bool:
    return bool(
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
        and metadata.st_nlink == 1
    )


def _same_secure_snapshot(
    left: os.stat_result, right: os.stat_result
) -> bool:
    return (
        left.st_dev, left.st_ino, left.st_mode, left.st_uid, left.st_gid,
        left.st_nlink, left.st_size, left.st_mtime_ns, left.st_ctime_ns,
    ) == (
        right.st_dev, right.st_ino, right.st_mode, right.st_uid, right.st_gid,
        right.st_nlink, right.st_size, right.st_mtime_ns, right.st_ctime_ns,
    )


def _decode_canonical_json(raw: bytes | None) -> dict[str, Any] | None:
    if raw is None:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or raw != _canonical_json_bytes(value):
        return None
    return value


def _committed_artifacts_are_valid(
    state_path: Path,
    evidence_path: Path,
    commit_marker_path: Path,
    ledger_dir: Path,
    expected_state: dict[str, Any],
    request: LiveActivationRequest,
) -> bool:
    state = _read_secure_canonical_json(state_path)
    evidence = _read_secure_canonical_json(evidence_path)
    marker = _read_secure_canonical_json(commit_marker_path)
    if state != expected_state or evidence is None or marker is None:
        return False
    if state.get("status") != "PASSED" or not _terminal_chain_is_valid(
        state, ledger_dir
    ):
        return False
    try:
        _validate_evidence(evidence)
    except ActivationStepError:
        return False
    expected_bindings = {
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
    }
    return bool(
        evidence.get("status") == "PASSED"
        and marker == _final_commit_marker(evidence)
        and all(
            evidence.get(key) == value
            for key, value in expected_bindings.items()
        )
    )


def _lock_marker(activation_hash: str, status: str) -> dict[str, str]:
    return {"activation_hash": activation_hash, "status": status}


def _lock_marker_shape_is_valid(marker: dict[str, Any] | None) -> bool:
    return bool(
        isinstance(marker, dict)
        and set(marker) == {"activation_hash", "status"}
        and isinstance(marker.get("activation_hash"), str)
        and _SHA256_RE.fullmatch(marker["activation_hash"])
        and marker.get("status") in {"HELD", "RELEASED"}
    )


def _released_lock_marker_is_valid(
    marker: dict[str, Any] | None
) -> bool:
    return _lock_marker_shape_is_valid(marker) and (
        marker.get("status") == "RELEASED"
    )


def _held_lock_marker_matches(
    marker: dict[str, Any] | None, activation_hash: str
) -> bool:
    return marker in (
        {"activation_hash": activation_hash},
        _lock_marker(activation_hash, "HELD"),
    )


def _released_lock_marker_matches(
    marker: dict[str, Any] | None, activation_hash: str
) -> bool:
    return marker == _lock_marker(activation_hash, "RELEASED")


def _recovery_lock_marker_matches(
    marker: dict[str, Any] | None,
    activation_hash: str,
    *,
    committed: bool,
) -> bool:
    return _held_lock_marker_matches(marker, activation_hash) or (
        committed and _released_lock_marker_matches(marker, activation_hash)
    )


def _interruption_reconciliation_lock_paths(
    state: dict[str, Any],
) -> tuple[Path, Path, Path] | None:
    target = state.get("target_binding_sha256")
    legacy = state.get("legacy_target_binding_sha256")
    if (
        not isinstance(target, str)
        or not _SHA256_RE.fullmatch(target)
        or not isinstance(legacy, str)
        or not _SHA256_RE.fullmatch(legacy)
        or target == legacy
    ):
        return None
    host_root = _HOST_LOCK_ROOT.expanduser().absolute()
    legacy_host_root = _LEGACY_HOST_LOCK_ROOT.expanduser().absolute()
    if (
        not _existing_host_state_root_is_valid(host_root)
        or not _existing_host_state_root_is_valid(legacy_host_root)
    ):
        return None
    return (
        host_root / f"{target}.lock",
        host_root / f"{legacy}.lock",
        legacy_host_root / f"{legacy}.lock",
    )


def _read_lock_marker_journal_descriptor(
    descriptor: int,
) -> tuple[dict[str, Any], int, bool] | None:
    try:
        opened = os.fstat(descriptor)
        if (
            not _trusted_secure_artifact_metadata(opened)
            or opened.st_size < 1
            or opened.st_size > _MAX_SECURE_ARTIFACT_BYTES
        ):
            return None
        os.lseek(descriptor, 0, os.SEEK_SET)
        raw = _read_bounded_descriptor(descriptor)
        after = os.fstat(descriptor)
        if raw is None or not _same_secure_snapshot(opened, after):
            return None
        if b"\n" not in raw:
            try:
                legacy_value = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            legacy = legacy_value if isinstance(legacy_value, dict) else None
            if legacy is None or _canonical_json_bytes(legacy) != raw + b"\n":
                return None
            legacy_activation_hash = legacy.get("activation_hash")
            if not isinstance(legacy_activation_hash, str) or not (
                _SHA256_RE.fullmatch(legacy_activation_hash)
                and _held_lock_marker_matches(
                    legacy, legacy_activation_hash
                )
            ):
                return None
            return legacy, len(raw), False
        last_newline = raw.rfind(b"\n")
        complete = raw[: last_newline + 1]
        lines = complete.splitlines(keepends=True)
        if not lines:
            return None
        marker: dict[str, Any] | None = None
        for index, line in enumerate(lines):
            marker = _decode_canonical_json(line)
            if _lock_marker_shape_is_valid(marker):
                continue
            legacy_activation_hash = (
                marker.get("activation_hash")
                if isinstance(marker, dict)
                else None
            )
            if not (
                index == 0
                and isinstance(legacy_activation_hash, str)
                and _SHA256_RE.fullmatch(legacy_activation_hash)
                and _held_lock_marker_matches(marker, legacy_activation_hash)
            ):
                return None
        assert marker is not None
        return marker, last_newline + 1, True
    except OSError:
        return None


def _read_lock_marker_descriptor(
    descriptor: int,
) -> dict[str, Any] | None:
    journal = _read_lock_marker_journal_descriptor(descriptor)
    return journal[0] if journal is not None else None


def _append_lock_marker_bytes(descriptor: int, raw: bytes) -> None:
    if os.write(descriptor, raw) != len(raw):
        raise ActivationStepError("ACTIVATION_LOCK_INVALID")


def _write_lock_marker(
    descriptor: int, activation_hash: str, status: str
) -> None:
    metadata = os.fstat(descriptor)
    if not _trusted_secure_artifact_metadata(metadata):
        raise ActivationStepError("ACTIVATION_LOCK_INVALID")
    if status not in {"HELD", "RELEASED"}:
        raise ActivationStepError("ACTIVATION_LOCK_INVALID")
    prefix = b""
    if metadata.st_size:
        journal = _read_lock_marker_journal_descriptor(descriptor)
        if journal is None:
            raise ActivationStepError("ACTIVATION_LOCK_INVALID")
        _, valid_end, ends_with_newline = journal
        if valid_end != metadata.st_size:
            os.ftruncate(descriptor, valid_end)
            os.fsync(descriptor)
        if not ends_with_newline:
            prefix = b"\n"
    os.lseek(descriptor, 0, os.SEEK_END)
    raw = prefix + _canonical_json_bytes(
        _lock_marker(activation_hash, status)
    )
    _append_lock_marker_bytes(descriptor, raw)
    os.fsync(descriptor)
    if not (
        _read_lock_marker_descriptor(descriptor)
        == _lock_marker(activation_hash, status)
    ):
        raise ActivationStepError("ACTIVATION_LOCK_INVALID")


def _release_lock_markers_verified(
    descriptors: tuple[int, ...], activation_hash: str
) -> None:
    for descriptor in descriptors:
        _write_lock_marker(descriptor, activation_hash, "RELEASED")
    for descriptor in descriptors:
        marker = _read_lock_marker_descriptor(descriptor)
        if not _released_lock_marker_matches(marker, activation_hash):
            raise ActivationStepError("FINALIZATION_LOCK_RELEASE_FAILED")


def _acquire_lock(path: Path, activation_hash: str) -> int | None:
    descriptor: int | None = None
    created = False
    try:
        descriptor = os.open(
            path,
            os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
        created = True
    except FileExistsError:
        try:
            descriptor = os.open(
                path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
            )
        except OSError:
            return None
    except OSError:
        return None
    try:
        metadata = os.fstat(descriptor)
        if not _trusted_secure_artifact_metadata(metadata):
            os.close(descriptor)
            return None
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if created:
            if metadata.st_size != 0:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
                return None
        else:
            marker = _read_lock_marker_descriptor(descriptor)
            if not _released_lock_marker_is_valid(marker):
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
                return None
        _write_lock_marker(descriptor, activation_hash, "HELD")
        _fsync_directory(path.parent)
        return descriptor
    except BlockingIOError:
        os.close(descriptor)
        return None
    except Exception:
        os.close(descriptor)
        raise


def _load_or_initialize_state(
    state_path: Path,
    ledger_dir: Path,
    request: LiveActivationRequest,
    plan: dict[str, Any],
    permission_boundary_sha256: str,
    resume: bool,
    now: Callable[[], datetime] | None,
) -> tuple[dict[str, Any], str | None]:
    if state_path.exists() or ledger_dir.exists():
        if not resume:
            return {}, "EXISTING_RUN_REQUIRES_RESUME"
        state = _read_secure_canonical_json(state_path)
        if state is None:
            return {}, "LEDGER_INVALID"
        events, chain_error = _validate_event_chain(ledger_dir)
        if chain_error or not _state_matches_chain(state, events):
            return {}, "LEDGER_CHAIN_INVALID"
        if not _resume_bindings_match(
            state, request, plan, permission_boundary_sha256
        ):
            return {}, "RESUME_BINDING_MISMATCH"
        if state.get("status") == "PASSED":
            return state, "PASSED_TERMINAL"
        state["run_attempt"] = int(state.get("run_attempt", 1)) + 1
        _append_event(
            ledger_dir, state, step_id="runner", phase="RESUME",
            status=str(state.get("status", "FAILED_PARTIAL")),
            attempt=int(state["run_attempt"]), now=now
        )
        _atomic_json_write(state_path, state)
        return state, None

    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "status": "LIVE_APPROVED",
        "started_at_utc": _utc_now(now),
        "finished_at_utc": None,
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "approval_body_sha256": request.approval_body_sha256,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
        "reason_sha256": _sha256(request.reason),
        "correlation_id_sha256": _sha256(request.correlation_id),
        "target_binding_sha256": _binding_sha256_json(plan.get("bindings", {})),
        "legacy_target_binding_sha256": _sha256_json(plan.get("bindings", {})),
        "permission_boundary_sha256": permission_boundary_sha256,
        "ledger_head_sha256": "0" * 64,
        "ledger_sequence": 0,
        "run_attempt": 1,
        "writes_started": False,
        "steps": [],
        "duplicate_count": 0,
        "broader_permission_count": 0,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
        "prebuilt_inputs_verified": False,
        "healthz_before_auth_passed": False,
        "authenticated_read_passed": False,
        "readyz_after_authenticated_read_passed": False,
        "synthetic_state_restored": False,
        "assigned_access_passed": False,
        "deputy_access_passed": False,
        "denied_access_passed": False,
        "tampered_access_passed": False,
        "tampered_workspace_passed": False,
        "tampered_matter_passed": False,
        "tampered_purpose_passed": False,
        "tampered_filter_passed": False,
        "resume_enabled": False,
        "ledger_hash_chain_valid": False,
    }
    bindings = {
        key: state[key]
        for key in (
            "activation_hash", "approved_commit_sha", "approved_tree_sha",
            "approval_reference_sha256", "approval_body_sha256",
            "provisioner_bootstrap_binding_sha256",
            "toolchain_attestations_sha256", "correlation_id_sha256",
            "target_binding_sha256", "legacy_target_binding_sha256",
            "permission_boundary_sha256",
        )
    }
    _append_event(
        ledger_dir, state, step_id="runner", phase="LOCK_ACQUIRED",
        status="LIVE_APPROVED", attempt=1, bindings=bindings, now=now
    )
    _append_event(
        ledger_dir, state, step_id="runner", phase="START",
        status="LIVE_APPROVED", attempt=1, now=now
    )
    _atomic_json_write(state_path, state)
    return state, None


def _resume_bindings_match(
    state: dict[str, Any],
    request: LiveActivationRequest,
    plan: dict[str, Any],
    permission_boundary_sha256: str,
) -> bool:
    expected = {
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "approval_body_sha256": request.approval_body_sha256,
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
        "reason_sha256": _sha256(request.reason),
        "correlation_id_sha256": _sha256(request.correlation_id),
        "target_binding_sha256": _binding_sha256_json(plan.get("bindings", {})),
        "legacy_target_binding_sha256": _sha256_json(plan.get("bindings", {})),
        "permission_boundary_sha256": permission_boundary_sha256,
    }
    return all(state.get(key) == value for key, value in expected.items())


def _validate_event_chain(
    ledger_dir: Path,
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        paths = sorted(ledger_dir.glob("*.redacted.json"))
    except OSError:
        return [], "LEDGER_CHAIN_INVALID"
    if not paths:
        return [], "LEDGER_CHAIN_INVALID"
    events: list[dict[str, Any]] = []
    previous = "0" * 64
    for sequence, path in enumerate(paths, start=1):
        match = _EVENT_NAME_RE.fullmatch(path.name)
        if not match or int(match.group("sequence")) != sequence:
            return [], "LEDGER_CHAIN_INVALID"
        raw = _read_secure_artifact_bytes(path)
        if raw is None:
            return [], "LEDGER_CHAIN_INVALID"
        try:
            event = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return [], "LEDGER_CHAIN_INVALID"
        if raw != _canonical_json_bytes(event):
            return [], "LEDGER_CHAIN_INVALID"
        if (
            event.get("sequence") != sequence
            or event.get("previous_event_sha256") != previous
            or event.get("step_id") != match.group("step")
            or event.get("phase") != match.group("phase")
        ):
            return [], "LEDGER_CHAIN_INVALID"
        previous = hashlib.sha256(raw).hexdigest()
        event["_event_sha256"] = previous
        events.append(event)
    return events, None


def _state_matches_chain(
    state: dict[str, Any], events: list[dict[str, Any]]
) -> bool:
    if not events:
        return False
    if state.get("ledger_sequence") != len(events):
        return False
    if state.get("ledger_head_sha256") != events[-1].get("_event_sha256"):
        return False
    bindings = events[0].get("bindings")
    if not isinstance(bindings, dict):
        return False
    for key in (
        "activation_hash", "approved_commit_sha", "approved_tree_sha",
        "approval_reference_sha256", "approval_body_sha256",
        "provisioner_bootstrap_binding_sha256",
        "toolchain_attestations_sha256", "correlation_id_sha256",
        "target_binding_sha256", "legacy_target_binding_sha256",
        "permission_boundary_sha256",
    ):
        if state.get(key) != bindings.get(key):
            return False
    state_steps = state.get("steps")
    if not isinstance(state_steps, list):
        return False
    state_by_id: dict[str, dict[str, Any]] = {}
    for step in state_steps:
        if (
            not isinstance(step, dict)
            or not isinstance(step.get("id"), str)
            or step["id"] in state_by_id
        ):
            return False
        state_by_id[step["id"]] = step

    terminal_steps: dict[str, dict[str, Any]] = {}
    for event in events:
        if (
            event.get("phase") not in {"PASSED", "FAILED"}
            or event.get("step_id") == "runner"
        ):
            continue
        step_id = event.get("step_id")
        outcome = event.get("outcome")
        if not isinstance(step_id, str) or not isinstance(outcome, dict):
            return False
        terminal_steps[step_id] = outcome

    terminal_state_steps = {
        step_id: step
        for step_id, step in state_by_id.items()
        if step.get("status") in {"PASSED", "FAILED"}
    }
    return terminal_steps == terminal_state_steps


def _append_event(
    ledger_dir: Path,
    state: dict[str, Any],
    *,
    step_id: str,
    phase: str,
    status: str,
    attempt: int,
    now: Callable[[], datetime] | None,
    outcome: dict[str, Any] | None = None,
    bindings: dict[str, str] | None = None,
) -> str:
    sequence = int(state.get("ledger_sequence", 0)) + 1
    safe_step = re.sub(r"[^a-z0-9_-]", "_", step_id.lower())
    event: dict[str, Any] = {
        "schema_version": LEDGER_SCHEMA_VERSION,
        "sequence": sequence,
        "step_id": safe_step,
        "phase": phase,
        "status": status,
        "attempt": attempt,
        "timestamp_utc": _utc_now(now),
        "previous_event_sha256": state.get("ledger_head_sha256", "0" * 64),
    }
    if bindings is not None:
        event["bindings"] = bindings
    if outcome is not None:
        event["outcome"] = outcome
    _reject_secret_sentinel(event)
    payload = _canonical_json_bytes(event)
    path = ledger_dir / f"{sequence:06d}-{safe_step}-{phase}.redacted.json"
    _atomic_append(path, payload)
    event_hash = hashlib.sha256(payload).hexdigest()
    state["ledger_sequence"] = sequence
    state["ledger_head_sha256"] = event_hash
    return event_hash


def _sanitize_outcome(
    value: object, *, step_id: str | None = None
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ActivationStepError("STEP_RESULT_INVALID")
    _reject_secret_sentinel(value)
    step_specific_keys = (
        set(_STEP_11_ACCESS_SIGNAL_KEYS)
        if step_id == "run_access_and_readback_smokes"
        else set()
    )
    if set(value) - _ALLOWED_OUTCOME_KEYS - step_specific_keys:
        raise ActivationStepError("STEP_RESULT_NOT_REDACTED")
    status = value.get("status")
    classification = value.get("classification")
    if status not in {"PASSED", "FAILED"}:
        raise ActivationStepError("STEP_STATUS_INVALID")
    if classification not in _ALLOWED_CLASSIFICATIONS:
        raise ActivationStepError("STEP_CLASSIFICATION_INVALID")
    for key in ("created_count", "reused_count", "updated_count", "verified_count"):
        item = value.get(key, 0)
        if not isinstance(item, int) or isinstance(item, bool) or item < 0:
            raise ActivationStepError("STEP_COUNT_INVALID")

    hashes: dict[str, str | None] = {}
    aliases = {
        "request_sha256": ("request_sha256",),
        "response_sha256": ("response_sha256",),
        "resource_reference_sha256": (
            "resource_reference_sha256", "reference_sha256"
        ),
    }
    for target, names in aliases.items():
        item = next((value[name] for name in names if name in value), None)
        if item is not None and not (
            isinstance(item, str) and _SHA256_RE.fullmatch(item)
        ):
            raise ActivationStepError("STEP_REFERENCE_INVALID")
        hashes[target] = item
    http_status = value.get("http_status", value.get("http_status_class"))
    if http_status is not None and http_status not in {"2xx", "4xx"}:
        raise ActivationStepError("STEP_HTTP_STATUS_INVALID")
    code = value.get("stable_error_code", value.get("code"))
    if code is not None:
        code = _safe_error_code(
            code if isinstance(code, str) else "STEP_CODE_INVALID"
        )
    cleanup = value.get("cleanup_verified")
    if cleanup is not None and type(cleanup) is not bool:
        raise ActivationStepError("STEP_CLEANUP_STATUS_INVALID")
    prebuilt_inputs_verified = value.get("prebuilt_inputs_verified")
    if (
        prebuilt_inputs_verified is not None
        and type(prebuilt_inputs_verified) is not bool
    ):
        raise ActivationStepError("STEP_PREBUILT_INPUTS_STATUS_INVALID")
    summary_signals: dict[str, bool | None] = {}
    signal_keys = (
        _STEP_11_SIGNAL_KEYS
        if step_id == "run_access_and_readback_smokes"
        else _STEP_11_SUMMARY_SIGNAL_KEYS
    )
    for key in signal_keys:
        signal = value.get(key)
        if signal is not None and type(signal) is not bool:
            raise ActivationStepError("STEP_SUMMARY_SIGNAL_INVALID")
        summary_signals[key] = signal
    if step_id == "run_access_and_readback_smokes":
        hashes["response_sha256"] = _sha256_json(
            {
                "provider_response_sha256": hashes["response_sha256"],
                "verified_access_probe_signals": {
                    key: summary_signals[key] for key in _STEP_11_SIGNAL_KEYS
                },
            }
        )
    return {
        "status": status,
        "classification": classification,
        "stable_error_code": code,
        "http_status": http_status,
        **hashes,
        "created_count": int(value.get("created_count", 0)),
        "reused_count": int(value.get("reused_count", 0)),
        "updated_count": int(value.get("updated_count", 0)),
        "verified_count": int(value.get("verified_count", 0)),
        "cleanup_verified": cleanup,
        "prebuilt_inputs_verified": prebuilt_inputs_verified,
        **summary_signals,
    }


def _step_record(
    order: int,
    step_id: str,
    status: str,
    attempt: int,
    classification: str,
    outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = outcome or {}
    return {
        "order": order,
        "id": step_id,
        "status": status,
        "attempt": attempt,
        "classification": classification,
        "http_status": value.get("http_status"),
        "stable_error_code": value.get("stable_error_code"),
        "request_sha256": value.get("request_sha256"),
        "response_sha256": value.get("response_sha256"),
        "resource_reference_sha256": value.get(
            "resource_reference_sha256"
        ),
    }


def _set_state_step(state: dict[str, Any], record: dict[str, Any]) -> None:
    for index, current in enumerate(state["steps"]):
        if current.get("id") == record["id"]:
            state["steps"][index] = record
            return
    state["steps"].append(record)


def _state_step(
    state: dict[str, Any], step_id: str
) -> dict[str, Any] | None:
    return next(
        (item for item in state.get("steps", []) if item.get("id") == step_id),
        None,
    )


def _required_summary_signal_error(
    step_id: str, outcome: dict[str, Any]
) -> str | None:
    if step_id != "run_access_and_readback_smokes":
        return None
    if any(outcome.get(key) is not True for key in _STEP_11_SIGNAL_KEYS):
        return "STEP_11_SUMMARY_SIGNALS_INVALID"
    return None


def _record_summary_signals(
    state: dict[str, Any], step_id: str, outcome: dict[str, Any]
) -> None:
    if (
        step_id == "ensure_entra_api_application"
        and outcome.get("prebuilt_inputs_verified") is True
    ):
        state["prebuilt_inputs_verified"] = True
    elif step_id == "run_access_and_readback_smokes":
        for key in _STEP_11_SIGNAL_KEYS:
            state[key] = outcome[key]


def _record_lock_release(
    ledger_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    now: Callable[[], datetime] | None,
) -> None:
    _append_event(
        ledger_dir,
        state,
        step_id="runner",
        phase="LOCK_RELEASED",
        status=str(state["status"]),
        attempt=int(state["run_attempt"]),
        now=now,
    )
    _atomic_json_write(state_path, state)


def _record_lock_release_authorization(
    ledger_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    now: Callable[[], datetime] | None,
) -> None:
    _append_event(
        ledger_dir,
        state,
        step_id="runner",
        phase="LOCK_RELEASE_AUTHORIZED",
        status=str(state["status"]),
        attempt=int(state["run_attempt"]),
        now=now,
    )
    _atomic_json_write(state_path, state)


def _terminal_chain_is_valid(
    state: dict[str, Any], ledger_dir: Path
) -> bool:
    events, error = _validate_event_chain(ledger_dir)
    return error is None and _state_matches_chain(state, events)


def _cleanup_never_written_run(run_dir: Path, run_root: Path) -> None:
    resolved_run = run_dir.resolve()
    resolved_root = run_root.resolve()
    if (
        resolved_run.parent != resolved_root
        or not _SHA256_RE.fullmatch(resolved_run.name)
    ):
        raise ActivationStepError("OUTPUT_SCOPE_REJECTED")
    if resolved_run.exists():
        shutil.rmtree(resolved_run)
        _fsync_directory(resolved_root)


def _failed_execution_result(
    request: LiveActivationRequest, code: str
) -> dict[str, Any]:
    result = _blocked_result(request, code)
    result["status"] = "FAILED_PARTIAL"
    result["writes_started"] = True
    return result


def _fail_before_write(
    state: dict[str, Any],
    ledger_dir: Path,
    state_path: Path,
    request: LiveActivationRequest,
    code: str,
    now: Callable[[], datetime] | None,
) -> tuple[dict[str, Any], bool]:
    safe_code = _safe_error_code(code)
    state["status"] = "OFFLINE_READY"
    state["finished_at_utc"] = _utc_now(now)
    _append_event(
        ledger_dir, state, step_id="runner", phase="TERMINAL",
        status="OFFLINE_READY", attempt=int(state["run_attempt"]),
        outcome={"stable_error_code": safe_code}, now=now
    )
    _atomic_json_write(state_path, state)
    return _blocked_result(request, safe_code), True


def _fail_partial(
    state: dict[str, Any],
    ledger_dir: Path,
    state_path: Path,
    evidence_path: Path,
    request: LiveActivationRequest,
    step_id: str,
    code: str,
    now: Callable[[], datetime] | None,
) -> tuple[dict[str, Any], bool]:
    safe_code = _safe_error_code(code)
    prior = _state_step(state, step_id)
    order = int(prior.get("order", 0)) if prior else 0
    attempt = int(prior.get("attempt", 1)) if prior else 1
    record = _step_record(
        order, step_id, "FAILED", attempt, "not_applicable",
        {"stable_error_code": safe_code}
    )
    _set_state_step(state, record)
    _append_event(
        ledger_dir, state, step_id=step_id, phase="FAILED",
        status="FAILED", attempt=attempt, outcome=record, now=now
    )
    state["status"] = "FAILED_PARTIAL"
    state["finished_at_utc"] = _utc_now(now)
    _append_event(
        ledger_dir, state, step_id="runner", phase="TERMINAL",
        status="FAILED_PARTIAL", attempt=int(state["run_attempt"]),
        outcome={"stable_error_code": safe_code}, now=now
    )
    _atomic_json_write(state_path, state)
    preserve_quarantine = safe_code in _QUARANTINED_AMBIGUOUS_CODES
    if not preserve_quarantine:
        _record_lock_release(ledger_dir, state, state_path, now)
    if not _terminal_chain_is_valid(state, ledger_dir):
        return _failed_execution_result(request, "LEDGER_CHAIN_INVALID"), False
    state["ledger_hash_chain_valid"] = True
    _atomic_json_write(state_path, state)
    evidence = _evidence_from_state(state)
    _validate_evidence(evidence)
    _atomic_json_write(evidence_path, evidence)
    if _read_secure_canonical_json(evidence_path) != evidence:
        raise ActivationStepError("EVIDENCE_FINAL_COMMIT_INVALID")
    if not preserve_quarantine:
        recovery_marker_path = state_path.with_name(
            "activation.finalization-recovery.redacted.json"
        )
        recovery_marker = _finalization_recovery_marker(
            state,
            request,
            status="TERMINAL_RELEASE_IN_PROGRESS",
            error_code=safe_code,
            state_path=state_path,
            evidence_path=evidence_path,
            commit_marker_path=state_path.with_name(
                "activation.commit.redacted.json"
            ),
            receipt_path=state_path.with_name(
                "activation.success-receipt.redacted.json"
            ),
        )
        _atomic_json_write(recovery_marker_path, recovery_marker)
        if _read_secure_canonical_json(recovery_marker_path) != recovery_marker:
            raise ActivationStepError(
                "FINALIZATION_RECOVERY_MARKER_FAILED"
            )
    return evidence, not preserve_quarantine


def _evidence_from_state(state: dict[str, Any]) -> dict[str, Any]:
    steps = sorted(
        state.get("steps", []), key=lambda item: int(item.get("order", 0))
    )
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "status": state["status"],
        "started_at_utc": state["started_at_utc"],
        "finished_at_utc": state["finished_at_utc"],
        "activation_hash": state["activation_hash"],
        "approved_commit_sha": state["approved_commit_sha"],
        "approved_tree_sha": state["approved_tree_sha"],
        "approval_reference_sha256": state["approval_reference_sha256"],
        "provisioner_bootstrap_binding_sha256": state[
            "provisioner_bootstrap_binding_sha256"
        ],
        "toolchain_attestations_sha256": state["toolchain_attestations_sha256"],
        "target_binding_sha256": state["target_binding_sha256"],
        "permission_boundary_sha256": state["permission_boundary_sha256"],
        "ledger_head_sha256": state["ledger_head_sha256"],
        "step_results": steps,
        "summary": {
            "required_step_count": 12,
            "passed_step_count": sum(
                item.get("status") == "PASSED" for item in steps
            ),
            "failed_step_count": sum(
                item.get("status") == "FAILED" for item in steps
            ),
            "duplicate_count": int(state.get("duplicate_count", 0)),
            "broader_permission_count": int(
                state.get("broader_permission_count", 0)
            ),
            "automatic_rollback_count": int(
                state.get("automatic_rollback_count", 0)
            ),
            "automatic_deletion_count": int(
                state.get("automatic_deletion_count", 0)
            ),
            "writes_started": bool(state.get("writes_started")),
            "ledger_hash_chain_valid": bool(
                state.get("ledger_hash_chain_valid", False)
            ),
            "prebuilt_inputs_verified": bool(
                state.get("prebuilt_inputs_verified", False)
            ),
            "healthz_before_auth_passed": bool(
                state.get("healthz_before_auth_passed", False)
            ),
            "authenticated_read_passed": bool(
                state.get("authenticated_read_passed", False)
            ),
            "readyz_after_authenticated_read_passed": bool(
                state.get("readyz_after_authenticated_read_passed", False)
            ),
            "synthetic_state_restored": bool(
                state.get("synthetic_state_restored", False)
            ),
            "assigned_access_passed": bool(
                state.get("assigned_access_passed", False)
            ),
            "deputy_access_passed": bool(
                state.get("deputy_access_passed", False)
            ),
            "denied_access_passed": bool(
                state.get("denied_access_passed", False)
            ),
            "tampered_access_passed": bool(
                state.get("tampered_access_passed", False)
            ),
            "tampered_workspace_passed": bool(
                state.get("tampered_workspace_passed", False)
            ),
            "tampered_matter_passed": bool(
                state.get("tampered_matter_passed", False)
            ),
            "tampered_purpose_passed": bool(
                state.get("tampered_purpose_passed", False)
            ),
            "tampered_filter_passed": bool(
                state.get("tampered_filter_passed", False)
            ),
            "resume_enabled": bool(state.get("resume_enabled", False)),
        },
    }
    _reject_secret_sentinel(evidence)
    return evidence


def _validate_evidence(evidence: dict[str, Any]) -> None:
    if not isinstance(evidence, dict):
        raise ActivationStepError("EVIDENCE_ALLOWLIST_VIOLATION")
    if evidence.get("schema_version") != SCHEMA_VERSION:
        raise ActivationStepError("EVIDENCE_SCHEMA_INVALID")
    if evidence.get("status") not in {"PASSED", "FAILED_PARTIAL"}:
        raise ActivationStepError("EVIDENCE_STATUS_INVALID")
    if set(evidence) != _EVIDENCE_KEYS:
        raise ActivationStepError("EVIDENCE_ALLOWLIST_VIOLATION")
    if not isinstance(evidence.get("step_results"), list):
        raise ActivationStepError("EVIDENCE_ALLOWLIST_VIOLATION")
    if any(
        not isinstance(step, dict) or set(step) != _STEP_EVIDENCE_KEYS
        for step in evidence["step_results"]
    ):
        raise ActivationStepError("EVIDENCE_ALLOWLIST_VIOLATION")
    summary = evidence.get("summary")
    if not isinstance(summary, dict) or set(summary) != _SUMMARY_EVIDENCE_KEYS:
        raise ActivationStepError("EVIDENCE_SUMMARY_INVALID")
    if any(
        not isinstance(summary.get(key), int)
        or isinstance(summary[key], bool)
        or summary[key] < 0
        for key in _SUMMARY_COUNT_KEYS
    ):
        raise ActivationStepError("EVIDENCE_SUMMARY_INVALID")
    if any(
        not isinstance(summary.get(key), bool)
        for key in _SUMMARY_BOOL_KEYS
    ):
        raise ActivationStepError("EVIDENCE_SUMMARY_INVALID")
    passed_count = sum(
        step.get("status") == "PASSED" for step in evidence["step_results"]
    )
    failed_count = sum(
        step.get("status") == "FAILED" for step in evidence["step_results"]
    )
    if (
        summary["required_step_count"] != 12
        or summary["passed_step_count"] != passed_count
        or summary["failed_step_count"] != failed_count
        or (evidence["status"] == "PASSED" and passed_count != 12)
        or (evidence["status"] == "PASSED" and failed_count != 0)
    ):
        raise ActivationStepError("EVIDENCE_SUMMARY_INVALID")
    if evidence["status"] == "PASSED" and (
        summary["duplicate_count"] != 0
        or summary["broader_permission_count"] != 0
        or summary["automatic_rollback_count"] != 0
        or summary["automatic_deletion_count"] != 0
        or summary["writes_started"] is not True
        or summary["ledger_hash_chain_valid"] is not True
        or summary["prebuilt_inputs_verified"] is not True
        or summary["healthz_before_auth_passed"] is not True
        or summary["authenticated_read_passed"] is not True
        or summary["readyz_after_authenticated_read_passed"] is not True
        or summary["synthetic_state_restored"] is not True
        or summary["assigned_access_passed"] is not True
        or summary["deputy_access_passed"] is not True
        or summary["denied_access_passed"] is not True
        or summary["tampered_access_passed"] is not True
        or summary["tampered_workspace_passed"] is not True
        or summary["tampered_matter_passed"] is not True
        or summary["tampered_purpose_passed"] is not True
        or summary["tampered_filter_passed"] is not True
        or summary["resume_enabled"] is not False
    ):
        raise ActivationStepError("EVIDENCE_SUMMARY_INVALID")
    for key in (
        "activation_hash", "approval_reference_sha256",
        "provisioner_bootstrap_binding_sha256",
        "toolchain_attestations_sha256", "target_binding_sha256",
        "permission_boundary_sha256",
        "ledger_head_sha256",
    ):
        if not isinstance(evidence.get(key), str) or not _SHA256_RE.fullmatch(
            evidence[key]
        ):
            raise ActivationStepError("EVIDENCE_HASH_INVALID")
    for key in ("approved_commit_sha", "approved_tree_sha"):
        if not isinstance(evidence.get(key), str) or not _COMMIT_RE.fullmatch(
            evidence[key]
        ):
            raise ActivationStepError("EVIDENCE_GIT_BINDING_INVALID")
    _reject_secret_sentinel(evidence)


def _final_commit_marker(evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": FINAL_COMMIT_SCHEMA_VERSION,
        "status": "COMMITTED",
        "evidence_sha256": hashlib.sha256(
            _canonical_json_bytes(evidence)
        ).hexdigest(),
        "ledger_head_sha256": evidence["ledger_head_sha256"],
        "activation_hash": evidence["activation_hash"],
    }


def _final_commit_marker_matches(
    path: Path, evidence: dict[str, Any]
) -> bool:
    marker = _read_secure_canonical_json(path)
    return marker == _final_commit_marker(evidence)


def _load_existing_evidence(
    path: Path,
    request: LiveActivationRequest,
    *,
    receipt_path: Path | None = None,
) -> dict[str, Any]:
    evidence = _read_secure_canonical_json(path)
    if evidence is None:
        return _blocked_result(request, "EVIDENCE_INVALID")
    try:
        _validate_evidence(evidence)
    except ActivationStepError:
        return _blocked_result(request, "EVIDENCE_INVALID")
    expected_bindings = {
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "approval_reference_sha256": _sha256(request.owner_approval_reference),
        "provisioner_bootstrap_binding_sha256": (
            request.provisioner_bootstrap_binding_sha256
        ),
        "toolchain_attestations_sha256": request.toolchain_attestations_sha256,
    }
    if evidence.get("status") != "PASSED" or any(
        evidence.get(key) != value for key, value in expected_bindings.items()
    ):
        return _blocked_result(request, "EVIDENCE_BINDING_MISMATCH")
    marker_path = path.with_name("activation.commit.redacted.json")
    if not _final_commit_marker_matches(marker_path, evidence):
        return _blocked_result(request, "EVIDENCE_FINAL_COMMIT_INVALID")
    if receipt_path is None:
        return _blocked_result(request, "EVIDENCE_SUCCESS_RECEIPT_INVALID")
    target_binding = evidence.get("target_binding_sha256")
    if not isinstance(target_binding, str) or _success_receipt_status(
        receipt_path, target_binding, request
    ) != "VALID":
        return _blocked_result(request, "EVIDENCE_SUCCESS_RECEIPT_INVALID")
    receipt = _read_secure_canonical_json(receipt_path)
    state_path = path.with_name("resume-state.redacted.json")
    artifact_hashes = {
        "evidence_sha256": _artifact_sha256(path),
        "final_commit_marker_sha256": _artifact_sha256(marker_path),
        "final_state_sha256": _artifact_sha256(state_path),
    }
    if (
        receipt is None
        or any(value is None for value in artifact_hashes.values())
        or any(
            receipt.get(key) != value
            for key, value in artifact_hashes.items()
        )
    ):
        return _blocked_result(request, "EVIDENCE_SUCCESS_RECEIPT_INVALID")
    state = _read_secure_canonical_json(state_path)
    if (
        state is None
        or state.get("status") != "PASSED"
        or state.get("ledger_head_sha256") != evidence.get("ledger_head_sha256")
        or not _terminal_chain_is_valid(state, path.parent / "ledger")
    ):
        return _blocked_result(request, "EVIDENCE_SUCCESS_RECEIPT_INVALID")
    return evidence


def _blocked_result(
    request: LiveActivationRequest, code: str
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "OFFLINE_READY",
        "correlation_reference_sha256": _sha256(
            request.owner_approval_reference
        ),
        "error": {"code": _safe_error_code(code)},
        "writes_started": False,
    }


def _atomic_json_create(path: Path, payload: dict[str, Any]) -> None:
    try:
        _atomic_append(path, _canonical_json_bytes(payload))
    except ActivationStepError as exc:
        raise ActivationStepError("SUCCESS_RECEIPT_INVALID") from exc


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_append(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise ActivationStepError("LEDGER_APPEND_CONFLICT") from exc
        os.chmod(path, 0o600)
        _fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _unlink_and_fsync(path: Path) -> None:
    path.unlink(missing_ok=True)
    _fsync_directory(path.parent)



def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        try:
            os.fsync(descriptor)
        except OSError as exc:
            # Some mounted filesystems reject directory fsync; file contents are
            # fsynced separately before directory durability is attempted.
            if exc.errno not in _DIRECTORY_FSYNC_UNSUPPORTED_ERRNOS:
                raise
    finally:
        os.close(descriptor)


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        + "\n"
    ).encode("utf-8")


def _safe_error_code(value: str) -> str:
    if "SECRET_SENTINEL" in value.upper():
        return "SENSITIVE_VALUE_REJECTED"
    return value if _SAFE_CODE_RE.fullmatch(value) else "STEP_FAILED"


def _reject_secret_sentinel(value: object) -> None:
    serialized = json.dumps(
        value, sort_keys=True, ensure_ascii=True
    ).upper()
    if "SECRET_SENTINEL" in serialized:
        raise ActivationStepError("SENSITIVE_VALUE_REJECTED")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _binding_sha256_json(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _utc_now(now: Callable[[], datetime] | None) -> str:
    value = now() if now else datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
