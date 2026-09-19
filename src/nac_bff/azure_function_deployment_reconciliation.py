from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Protocol

from .azure_activation import FUNCTION_APP, RESOURCE_GROUP, SUBSCRIPTION_ID, TENANT_ID
from . import azure_activation_runner as runner
from . import azure_interruption_reconciliation as interruption


SCHEMA_VERSION = "nac.m365-azure-bff-function-deployment-reconciliation/v0.1"
MARKER_SCHEMA_VERSION = (
    "nac.m365-azure-bff-function-deployment-reconciliation-marker/v0.1"
)
ACTION = "RELEASE_QUARANTINE_FOR_NOT_APPLIED_FUNCTION_DEPLOYMENT"
FAILED_STEP_ID = "deploy_function_package"
FAILURE_CODE = "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS"
NOT_APPLIED = "FUNCTION_DEPLOYMENT_NOT_APPLIED"
PROVENANCE_LOSS = "FUNCTION_DEPLOYMENT_PROVENANCE_LOST"
PROVENANCE_LOSS_ACTION = "CONFIRM_FUNCTION_DEPLOYMENT_PROVENANCE_LOST"
PROVENANCE_LOSS_RUN_ID = "nac-bff-live-20260908-issue739-v4"
PROVENANCE_LOSS_CONFIRMATION_SCHEMA_VERSION = (
    "nac.issue739-function-deployment-provenance-loss-confirmation/v1"
)
PROVENANCE_LOSS_ARTIFACT_CATEGORIES = (
    "resume_state",
    "activation_evidence",
    "ledger",
    "target_lock_journal",
    "legacy_lock_journal",
    "legacy_host_lock_journal",
    "prepared_inputs_manifest",
    "function_package",
)
PROVENANCE_LOSS_COUNTER_KEYS = (
    "github_read_count",
    "credential_access_count",
    "network_access_count",
    "subprocess_count",
    "provider_read_count",
    "provider_write_count",
    "tenant_write_count",
    "local_write_count",
    "journal_append_count",
    "quarantine_release_count",
    "package_build_count",
    "live_run_count",
    "recovery_count",
    "retry_count",
    "rollback_count",
    "deletion_count",
)
_APPROVAL_REFERENCE_RE = re.compile(
    r"^https://github\.com/notariat8/NaC/issues/739"
    r"#issuecomment-[1-9][0-9]*$"
)
_OWNER_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$"
)
_STEP_IDS = (
    "register_azure_providers",
    "ensure_resource_group",
    "ensure_entra_api_application",
    "deploy_bicep_baseline",
    "assign_sites_selected",
    "grant_target_site_read",
    FAILED_STEP_ID,
)
_LOCK_NAMES = ("target", "legacy", "legacy_host")
_MARKER_PHASES = (
    "FUNCTION_DEPLOYMENT_RELEASE_AUTHORIZED",
    "FUNCTION_DEPLOYMENT_TARGET_LOCK_RELEASED",
    "FUNCTION_DEPLOYMENT_LEGACY_LOCK_RELEASED",
    "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED",
)
_OBSERVATION_ERROR_CODES = frozenset({
    "AZURE_FUNCTION_DEPLOYMENT_NOT_APPLIED_NOT_PROVEN",
    "AZURE_FUNCTION_RECONCILIATION_ACCOUNT_MISMATCH",
    "AZURE_FUNCTION_RECONCILIATION_DEPLOYMENTS_INVALID",
    "AZURE_FUNCTION_RECONCILIATION_READ_FAILED",
    "AZURE_FUNCTION_RECONCILIATION_READ_FORBIDDEN",
    "AZURE_FUNCTION_RECONCILIATION_SITE_INVALID",
    "AZURE_FUNCTION_RECONCILIATION_TARGET_MISMATCH",
    "AZURE_FUNCTION_RECONCILIATION_TIME_INVALID",
})
_APPROVAL_BINDING_KEYS = {
    "action",
    "activation_hash",
    "state_sha256",
    "evidence_sha256",
    "ledger_head_sha256",
    "target_lock_sha256",
    "legacy_lock_sha256",
    "legacy_host_lock_sha256",
    "provider_observation_sha256",
    "failed_step",
    "failed_step_started_at_utc",
    "prepared_inputs_manifest_sha256",
    "function_package_sha256",
    "reconciler_commit",
    "reconciler_tree",
    "reconciler_toolchain_sha256",
    "required_owner_login",
    "required_owner_principal_id_sha256",
}


class FunctionDeploymentObservationPort(Protocol):
    def observe_function_deployment(
        self,
        *,
        tenant_id: str,
        subscription_id: str,
        resource_group: str,
        function_app: str,
        step_started_at_utc: str,
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
class FunctionDeploymentReconcilerBinding:
    approved_commit: str
    approved_tree: str
    toolchain_sha256: str
    required_owner_login: str
    required_owner_principal_id_sha256: str


@dataclass(frozen=True, slots=True)
class FunctionDeploymentReleaseApproval:
    owner_approved: bool
    action: str
    owner_approval_reference: str
    approval_body_sha256: str
    activation_hash: str
    state_sha256: str
    evidence_sha256: str
    ledger_head_sha256: str
    target_lock_sha256: str
    legacy_lock_sha256: str
    legacy_host_lock_sha256: str
    provider_observation_sha256: str
    failed_step: str
    failed_step_started_at_utc: str
    prepared_inputs_manifest_sha256: str
    function_package_sha256: str
    reconciler_commit: str
    reconciler_tree: str
    reconciler_toolchain_sha256: str
    required_owner_login: str
    required_owner_principal_id_sha256: str


@dataclass(frozen=True, slots=True)
class FunctionDeploymentProvenanceLossConfirmation:
    owner_confirmed: bool
    issue: int
    action: str
    run_id: str
    activation_hash: str
    correlation_id: str
    canonical_run_relative_path: str
    expected_artifact_categories: tuple[str, ...]
    operator_account_id_sha256: str
    operator_principal_id_sha256: str
    identity_resolver_sha256: str
    target_lock_binding_sha256: str
    legacy_lock_binding_sha256: str
    reconciler_commit: str
    reconciler_tree: str
    reconciler_toolchain_sha256: str
    terminal_status: str = "BLOCKED"
    terminal_reason_code: str = PROVENANCE_LOSS
    terminal: bool = True
    retry_allowed: bool = False
    next_phase: None = None


def load_function_deployment_provenance_loss_confirmation(
    *, repo_root: Path, path: Path, expected_sha256: str
) -> FunctionDeploymentProvenanceLossConfirmation:
    if not path.is_absolute() or not runner._SHA256_RE.fullmatch(expected_sha256):
        raise ValueError("FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID")
    normalized = Path(os.path.abspath(path))
    try:
        normalized.relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID")
    try:
        from .activation_security_backend import get_platform_security_backend

        backend = get_platform_security_backend()
        binding = backend.inspect_private_path(
            normalized, purpose="provenance-loss-confirmation"
        )
        if binding.size > 131072:
            raise ValueError(
                "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID"
            )
        with backend.open_bound_read(normalized, binding) as handle:
            payload_bytes = handle.read(131073)
    except ValueError:
        raise
    except (OSError, RuntimeError) as exc:
        raise ValueError(
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID"
        ) from exc
    if (
        len(payload_bytes) > 131072
        or hashlib.sha256(payload_bytes).hexdigest() != expected_sha256
    ):
        raise ValueError("FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID")
    try:
        payload = json.loads(
            payload_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID"
        ) from exc
    expected_keys = {
        "schema_version",
        "owner_confirmed",
        "issue",
        "action",
        "run_id",
        "activation_hash",
        "correlation_id",
        "canonical_run_relative_path",
        "expected_artifact_categories",
        "operator_account_id_sha256",
        "operator_principal_id_sha256",
        "identity_resolver_sha256",
        "target_lock_binding_sha256",
        "legacy_lock_binding_sha256",
        "reconciler_commit",
        "reconciler_tree",
        "reconciler_toolchain_sha256",
        "terminal_status",
        "terminal_reason_code",
        "terminal",
        "retry_allowed",
        "next_phase",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID")
    if payload.pop("schema_version") != PROVENANCE_LOSS_CONFIRMATION_SCHEMA_VERSION:
        raise ValueError("FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID")
    categories = payload.get("expected_artifact_categories")
    if not isinstance(categories, list) or not all(
        isinstance(item, str) for item in categories
    ):
        raise ValueError("FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID")
    payload["expected_artifact_categories"] = tuple(categories)
    try:
        return FunctionDeploymentProvenanceLossConfirmation(**payload)
    except TypeError as exc:
        raise ValueError(
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID"
        ) from exc


def classify_function_deployment_provenance_loss(
    *,
    repo_root: Path,
    request: runner.LiveActivationRequest,
    confirmation: FunctionDeploymentProvenanceLossConfirmation,
    resolved_operator_account_id_sha256: str,
    resolved_operator_principal_id_sha256: str,
    resolved_identity_resolver_sha256: str,
    reconciler_commit: str,
    reconciler_tree: str,
    reconciler_toolchain_sha256: str,
    output_root: Path = runner.DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    expected_relative = (
        f"{runner.DEFAULT_OUTPUT_ROOT.as_posix()}/{request.expected_activation_hash}"
    )
    binding_valid = (
        confirmation.owner_confirmed is True
        and confirmation.issue == 739
        and confirmation.action == PROVENANCE_LOSS_ACTION
        and confirmation.run_id == PROVENANCE_LOSS_RUN_ID
        and request.correlation_id == PROVENANCE_LOSS_RUN_ID
        and confirmation.correlation_id == request.correlation_id
        and confirmation.activation_hash == request.expected_activation_hash
        and confirmation.canonical_run_relative_path == expected_relative
        and confirmation.expected_artifact_categories
        == PROVENANCE_LOSS_ARTIFACT_CATEGORIES
        and confirmation.operator_account_id_sha256
        == resolved_operator_account_id_sha256
        and confirmation.operator_principal_id_sha256
        == resolved_operator_principal_id_sha256
        and confirmation.identity_resolver_sha256
        == resolved_identity_resolver_sha256
        and confirmation.reconciler_commit == reconciler_commit
        and confirmation.reconciler_tree == reconciler_tree
        and confirmation.reconciler_toolchain_sha256
        == reconciler_toolchain_sha256
        and confirmation.terminal_status == "BLOCKED"
        and confirmation.terminal_reason_code == PROVENANCE_LOSS
        and confirmation.terminal is True
        and confirmation.retry_allowed is False
        and confirmation.next_phase is None
        and runner._SHA256_RE.fullmatch(request.expected_activation_hash)
        and runner._COMMIT_RE.fullmatch(reconciler_commit)
        and runner._COMMIT_RE.fullmatch(reconciler_tree)
        and runner._SHA256_RE.fullmatch(reconciler_toolchain_sha256)
        and runner._SHA256_RE.fullmatch(resolved_operator_account_id_sha256)
        and runner._SHA256_RE.fullmatch(resolved_operator_principal_id_sha256)
        and runner._SHA256_RE.fullmatch(resolved_identity_resolver_sha256)
        and runner._SHA256_RE.fullmatch(
            confirmation.target_lock_binding_sha256
        )
        and runner._SHA256_RE.fullmatch(
            confirmation.legacy_lock_binding_sha256
        )
    )
    if not binding_valid:
        return _provenance_loss_blocked(
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_BINDING_INVALID"
        )
    run_dir, error = interruption._resolve_run_dir(
        repo_root, output_root, request.expected_activation_hash
    )
    if error or run_dir is None:
        return _provenance_loss_blocked(error or "OUTPUT_SCOPE_REJECTED")
    paths = (
        run_dir,
        runner._HOST_LOCK_ROOT.expanduser().absolute()
        / f"{confirmation.target_lock_binding_sha256}.lock",
        runner._HOST_LOCK_ROOT.expanduser().absolute()
        / f"{confirmation.legacy_lock_binding_sha256}.lock",
        runner._LEGACY_HOST_LOCK_ROOT.expanduser().absolute()
        / f"{confirmation.legacy_lock_binding_sha256}.lock",
    )
    try:
        if any(_path_entry_exists(path) for path in paths):
            return _provenance_loss_blocked(
                "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_INVALID"
            )
    except OSError:
        return _provenance_loss_blocked(
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_UNINSPECTABLE"
        )
    return _provenance_loss_blocked(PROVENANCE_LOSS, terminal=True)


def inspect_azure_bff_function_deployment_failure(
    *,
    repo_root: Path,
    request: runner.LiveActivationRequest,
    reconciler_binding: FunctionDeploymentReconcilerBinding,
    observation_port: FunctionDeploymentObservationPort,
    output_root: Path = runner.DEFAULT_OUTPUT_ROOT,
) -> dict[str, Any]:
    run_dir, error = interruption._resolve_run_dir(
        repo_root, output_root, request.expected_activation_hash
    )
    if error:
        return _blocked(error)
    assert run_dir is not None
    error = _validate_bindings(request, reconciler_binding)
    if error:
        return _blocked(error)

    state_path = run_dir / "resume-state.redacted.json"
    state = runner._read_secure_canonical_json(state_path)
    if state is None:
        return _blocked("FUNCTION_DEPLOYMENT_STATE_INVALID")
    lock_paths = runner._interruption_reconciliation_lock_paths(state)
    if lock_paths is None:
        return _blocked("FUNCTION_DEPLOYMENT_LOCK_SET_INVALID")
    tracked = _inspection_paths(run_dir, lock_paths)
    before = _snapshot_bytes(tracked) if tracked is not None else None
    if tracked is None or before is None:
        return _blocked("FUNCTION_DEPLOYMENT_LOCAL_SNAPSHOT_INVALID")

    descriptors, error = interruption._open_lock_set_read_only(lock_paths)
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
            result = _blocked("FUNCTION_DEPLOYMENT_STATE_CHANGED")
        elif not interruption._descriptors_match_paths(lock_paths, descriptors):
            result = _blocked("FUNCTION_DEPLOYMENT_LOCK_REPLACED")
        else:
            result = _inspect_locked(
                run_dir=run_dir,
                state=current_state,
                state_path=state_path,
                lock_descriptors=descriptors,
                request=request,
                reconciler_binding=reconciler_binding,
                observation_port=observation_port,
                allow_marker=False,
            )
    finally:
        interruption._close_lock_set(descriptors)

    after_paths = _inspection_paths(run_dir, lock_paths)
    after = _snapshot_bytes(after_paths) if after_paths is not None else None
    if after_paths != tracked or after is None or after != before:
        return _blocked("FUNCTION_DEPLOYMENT_INSPECTION_LOCAL_WRITE_DETECTED")
    return result


def release_azure_bff_function_deployment_quarantine(
    *,
    repo_root: Path,
    request: runner.LiveActivationRequest,
    reconciler_binding: FunctionDeploymentReconcilerBinding,
    observation_port: FunctionDeploymentObservationPort,
    owner_comment_verifier: ImmutableOwnerCommentVerifier,
    approval: FunctionDeploymentReleaseApproval,
    pre_mutation_revalidate: Callable[[], None],
    output_root: Path = runner.DEFAULT_OUTPUT_ROOT,
    fault_injector: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    run_dir, error = interruption._resolve_run_dir(
        repo_root, output_root, request.expected_activation_hash
    )
    if error:
        return _blocked(error)
    assert run_dir is not None
    error = _validate_bindings(request, reconciler_binding)
    if error:
        return _blocked(error)
    if not _approval_shape_is_valid(approval):
        return _blocked("FUNCTION_DEPLOYMENT_APPROVAL_INVALID")

    state_path = run_dir / "resume-state.redacted.json"
    state = runner._read_secure_canonical_json(state_path)
    if state is None:
        return _blocked("FUNCTION_DEPLOYMENT_STATE_INVALID")
    lock_paths = runner._interruption_reconciliation_lock_paths(state)
    if lock_paths is None:
        return _blocked("FUNCTION_DEPLOYMENT_LOCK_SET_INVALID")
    descriptors, error = interruption._open_lock_set_for_terminalization(
        lock_paths
    )
    if error:
        return _blocked(error)
    assert descriptors is not None
    try:
        if not interruption._descriptors_match_paths(lock_paths, descriptors):
            return _blocked("FUNCTION_DEPLOYMENT_LOCK_REPLACED")
        marker_path = _marker_path(run_dir)
        marker = runner._read_secure_canonical_json(marker_path)
        if marker_path.exists() and marker is None:
            return _blocked(
                "FUNCTION_DEPLOYMENT_MARKER_INVALID", writes_started=True
            )
        if marker is None:
            inspection = _inspect_locked(
                run_dir=run_dir,
                state=state,
                state_path=state_path,
                lock_descriptors=descriptors,
                request=request,
                reconciler_binding=reconciler_binding,
                observation_port=observation_port,
                allow_marker=False,
            )
            if inspection.get("status") != (
                "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED"
            ):
                return inspection
            if not _approval_matches(approval, inspection):
                return _blocked("FUNCTION_DEPLOYMENT_APPROVAL_MISMATCH")
            owner_comment = inspection["owner_comment"]
            if not _verify_function_owner_comment(
                owner_comment_verifier,
                reconciler_binding,
                approval.owner_approval_reference,
                owner_comment["body"],
                owner_comment["body_sha256"],
            ):
                return _blocked("OWNER_COMMENT_VERIFICATION_FAILED")
            error = _pre_mutation_revalidation_error(
                run_dir=run_dir,
                state=state,
                state_path=state_path,
                descriptors=descriptors,
                approval_bindings=inspection["approval_bindings"],
                observation_port=observation_port,
                pre_mutation_revalidate=pre_mutation_revalidate,
            )
            if error:
                return _blocked(error)
            marker = _build_marker(
                request=request,
                approval=approval,
                inspection=inspection,
                descriptors=descriptors,
            )
            runner._atomic_json_write(marker_path, marker)
            _checkpoint(fault_injector, "marker:AUTHORIZED")
            if runner._read_secure_canonical_json(marker_path) != marker:
                return _blocked(
                    "FUNCTION_DEPLOYMENT_MARKER_INVALID", writes_started=True
                )
        else:
            if not _marker_is_valid(marker, request, reconciler_binding):
                return _blocked(
                    "FUNCTION_DEPLOYMENT_MARKER_INVALID", writes_started=True
                )
            if not _marker_approval_matches(marker, approval):
                return _blocked(
                    "FUNCTION_DEPLOYMENT_APPROVAL_MISMATCH", writes_started=True
                )
            if not _verify_function_owner_comment(
                owner_comment_verifier,
                reconciler_binding,
                approval.owner_approval_reference,
                marker["owner_comment_body"],
                marker["terminalization_approval_body_sha256"],
            ):
                return _blocked(
                    "OWNER_COMMENT_VERIFICATION_FAILED", writes_started=True
                )
            error = _pre_mutation_revalidation_error(
                run_dir=run_dir,
                state=state,
                state_path=state_path,
                descriptors=descriptors,
                approval_bindings=marker["approval_bindings"],
                observation_port=observation_port,
                pre_mutation_revalidate=pre_mutation_revalidate,
                marker=marker,
            )
            if error:
                return _blocked(error, writes_started=True)

        return _continue_release(
            run_dir=run_dir,
            state=state,
            state_path=state_path,
            lock_paths=lock_paths,
            descriptors=descriptors,
            marker=marker,
            observation_port=observation_port,
            pre_mutation_revalidate=pre_mutation_revalidate,
            fault_injector=fault_injector,
        )
    except runner.ActivationStepError as exc:
        return _blocked(exc.code, writes_started=_marker_path(run_dir).exists())
    except Exception:
        return _blocked(
            "FUNCTION_DEPLOYMENT_RELEASE_FAILED",
            writes_started=_marker_path(run_dir).exists(),
        )
    finally:
        interruption._close_lock_set(descriptors)


def _inspect_locked(
    *,
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    lock_descriptors: tuple[int, int, int],
    request: runner.LiveActivationRequest,
    reconciler_binding: FunctionDeploymentReconcilerBinding,
    observation_port: FunctionDeploymentObservationPort,
    allow_marker: bool,
) -> dict[str, Any]:
    step_started, error = _validate_failed_state(
        run_dir, state, state_path, request, allow_marker=allow_marker
    )
    if error:
        return _blocked(error)
    assert step_started is not None
    prepared, error = _validate_prepared_inputs(run_dir, request)
    if error:
        return _blocked(error)
    assert prepared is not None

    lock_hashes: dict[str, str] = {}
    for name, descriptor in zip(_LOCK_NAMES, lock_descriptors, strict=True):
        marker = runner._read_lock_marker_descriptor(descriptor)
        if not runner._held_lock_marker_matches(
            marker, request.expected_activation_hash
        ):
            return _blocked("FUNCTION_DEPLOYMENT_LOCK_NOT_HELD")
        digest = interruption._descriptor_sha256(descriptor)
        if digest is None:
            return _blocked("FUNCTION_DEPLOYMENT_LOCK_SET_INVALID")
        lock_hashes[name] = digest

    observation, error = _stable_observation(
        observation_port, step_started
    )
    if error:
        return _blocked(error)
    assert observation is not None
    observation_sha256 = runner._sha256_json(observation)
    state_sha256 = runner._artifact_sha256(state_path)
    evidence_sha256 = runner._artifact_sha256(
        run_dir / "activation.redacted.json"
    )
    if state_sha256 is None or evidence_sha256 is None:
        return _blocked("FUNCTION_DEPLOYMENT_ARTIFACT_INVALID")
    bindings = {
        "action": ACTION,
        "activation_hash": request.expected_activation_hash,
        "state_sha256": state_sha256,
        "evidence_sha256": evidence_sha256,
        "ledger_head_sha256": state["ledger_head_sha256"],
        "target_lock_sha256": lock_hashes["target"],
        "legacy_lock_sha256": lock_hashes["legacy"],
        "legacy_host_lock_sha256": lock_hashes["legacy_host"],
        "provider_observation_sha256": observation_sha256,
        "failed_step": FAILED_STEP_ID,
        "failed_step_started_at_utc": step_started,
        "prepared_inputs_manifest_sha256": prepared[
            "manifest_artifact_sha256"
        ],
        "function_package_sha256": prepared["function_package_sha256"],
        "reconciler_commit": reconciler_binding.approved_commit,
        "reconciler_tree": reconciler_binding.approved_tree,
        "reconciler_toolchain_sha256": reconciler_binding.toolchain_sha256,
        "required_owner_login": reconciler_binding.required_owner_login,
        "required_owner_principal_id_sha256": (
            reconciler_binding.required_owner_principal_id_sha256
        ),
    }
    body = (
        "NAC_BFF_FUNCTION_DEPLOYMENT_RECONCILIATION_APPROVAL\n"
        + runner._canonical_json_bytes(bindings).decode("ascii")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED",
        "error": {"code": "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED"},
        "writes_started": True,
        "failed_step": FAILED_STEP_ID,
        "provider_observation": {
            "classification": NOT_APPLIED,
            "status": "STABLE",
            "read_count": 2,
            "sha256": observation_sha256,
        },
        "approval_bindings": bindings,
        "owner_comment": {
            "body": body,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        },
        "resume_enabled": False,
        "provider_write_count": 0,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }


def _validate_failed_state(
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    request: runner.LiveActivationRequest,
    *,
    allow_marker: bool,
) -> tuple[str | None, str | None]:
    expected = {
        "schema_version": runner.STATE_SCHEMA_VERSION,
        "status": "FAILED_PARTIAL",
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
        "ledger_sequence": 18,
        "run_attempt": 1,
        "writes_started": True,
        "resume_enabled": False,
        "ledger_hash_chain_valid": True,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }
    if set(state) != interruption._STATE_KEYS or any(
        state.get(key) != value for key, value in expected.items()
    ):
        return None, "FUNCTION_DEPLOYMENT_STATE_INVALID"
    if not isinstance(state.get("finished_at_utc"), str):
        return None, "FUNCTION_DEPLOYMENT_STATE_INVALID"
    steps = state.get("steps")
    if not isinstance(steps, list) or len(steps) != 7:
        return None, "FUNCTION_DEPLOYMENT_RECONCILIATION_UNSUPPORTED"
    for order, (step, step_id) in enumerate(
        zip(steps, _STEP_IDS, strict=True), start=1
    ):
        if (
            not isinstance(step, dict)
            or set(step) != interruption._STEP_KEYS
            or step.get("order") != order
            or step.get("id") != step_id
            or step.get("attempt") != 1
        ):
            return None, "FUNCTION_DEPLOYMENT_STATE_INVALID"
        if order < 7 and step.get("status") != "PASSED":
            return None, "FUNCTION_DEPLOYMENT_RECONCILIATION_UNSUPPORTED"
    if steps[-1] != runner._step_record(
        7,
        FAILED_STEP_ID,
        "FAILED",
        1,
        "not_applicable",
        {"stable_error_code": FAILURE_CODE},
    ):
        return None, "FUNCTION_DEPLOYMENT_STATE_INVALID"

    events, chain_error = runner._validate_event_chain(run_dir / "ledger")
    if (
        chain_error
        or len(events) != 18
        or not runner._state_matches_chain(state, events)
    ):
        return None, "FUNCTION_DEPLOYMENT_LEDGER_INVALID"
    expected_events: list[tuple[str, str, str]] = [
        ("runner", "LOCK_ACQUIRED", "LIVE_APPROVED"),
        ("runner", "START", "LIVE_APPROVED"),
        ("runner", "PRE_WRITE_BINDING", "LIVE_APPROVED"),
    ]
    for step_id in _STEP_IDS[:6]:
        expected_events.extend(
            ((step_id, "RUNNING", "RUNNING"), (step_id, "PASSED", "PASSED"))
        )
    expected_events.extend((
        (FAILED_STEP_ID, "RUNNING", "RUNNING"),
        (FAILED_STEP_ID, "FAILED", "FAILED"),
        ("runner", "TERMINAL", "FAILED_PARTIAL"),
    ))
    if any(
        (
            event.get("step_id"),
            event.get("phase"),
            event.get("status"),
        )
        != expected_event
        or event.get("attempt") != 1
        for event, expected_event in zip(events, expected_events, strict=True)
    ):
        return None, "FUNCTION_DEPLOYMENT_LEDGER_INVALID"
    if events[-2].get("outcome") != steps[-1] or events[-1].get(
        "outcome"
    ) != {"stable_error_code": FAILURE_CODE}:
        return None, "FUNCTION_DEPLOYMENT_LEDGER_INVALID"
    step_started = events[-3].get("timestamp_utc")
    if not _valid_timestamp(step_started):
        return None, "FUNCTION_DEPLOYMENT_LEDGER_INVALID"

    evidence_path = run_dir / "activation.redacted.json"
    evidence = runner._read_secure_canonical_json(evidence_path)
    try:
        expected_evidence = runner._evidence_from_state(state)
        runner._validate_evidence(expected_evidence)
    except runner.ActivationStepError:
        return None, "FUNCTION_DEPLOYMENT_EVIDENCE_INVALID"
    if evidence != expected_evidence:
        return None, "FUNCTION_DEPLOYMENT_EVIDENCE_INVALID"
    forbidden = (
        run_dir / "activation.commit.redacted.json",
        run_dir / "activation.success-receipt.redacted.json",
        run_dir / "activation.finalization-recovery.redacted.json",
        run_dir / "activation.finalization-reconciled.redacted.json",
        run_dir / "activation.interruption-reconciliation.redacted.json",
    )
    if any(path.exists() for path in forbidden) or (
        not allow_marker and _marker_path(run_dir).exists()
    ):
        return None, "FUNCTION_DEPLOYMENT_ARTIFACT_STATE_INVALID"
    if runner._read_secure_canonical_json(state_path) != state:
        return None, "FUNCTION_DEPLOYMENT_STATE_CHANGED"
    return step_started, None


def _validate_prepared_inputs(
    run_dir: Path, request: runner.LiveActivationRequest
) -> tuple[dict[str, str] | None, str | None]:
    manifest_path = run_dir / "prepared" / "prepared-inputs.redacted.json"
    package_path = run_dir / "prepared" / "nac-bff-function.zip"
    manifest = runner._read_secure_canonical_json(manifest_path)
    expected_keys = {
        "schema_version",
        "activation_hash",
        "approved_commit_sha",
        "approved_tree_sha",
        "approved_tree_snapshot_sha256",
        "bicep_parameters_snapshot_sha256",
        "bicep_snapshot_sha256",
        "function_package_sha256",
        "prepared_inputs_sha256",
        "spfx_package_sha256",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != expected_keys
        or manifest.get("schema_version")
        != "nac.m365-azure-bff-prepared-inputs/v1"
        or manifest.get("activation_hash") != request.expected_activation_hash
        or manifest.get("approved_commit_sha") != request.approved_commit
        or manifest.get("approved_tree_sha") != request.approved_tree
        or any(
            not isinstance(manifest.get(key), str)
            or not runner._SHA256_RE.fullmatch(manifest[key])
            for key in expected_keys - {
                "schema_version",
                "activation_hash",
                "approved_commit_sha",
                "approved_tree_sha",
            }
        )
    ):
        return None, "FUNCTION_DEPLOYMENT_PREPARED_INPUTS_INVALID"
    package = runner._read_secure_artifact_bytes(package_path)
    manifest_raw = runner._read_secure_artifact_bytes(manifest_path)
    if (
        package is None
        or manifest_raw is None
        or hashlib.sha256(package).hexdigest()
        != manifest["function_package_sha256"]
    ):
        return None, "FUNCTION_DEPLOYMENT_PACKAGE_BINDING_INVALID"
    return {
        "manifest_artifact_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "function_package_sha256": manifest["function_package_sha256"],
    }, None


def _stable_observation(
    port: FunctionDeploymentObservationPort, step_started_at_utc: str
) -> tuple[dict[str, Any] | None, str | None]:
    first, error = _observe(port, step_started_at_utc)
    if error:
        return None, error
    second, error = _observe(port, step_started_at_utc)
    if error:
        return None, error
    if (
        first != second
        or not _observation_is_valid(first, step_started_at_utc)
    ):
        return None, "FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_DRIFT"
    return first, None


def _observe(
    port: FunctionDeploymentObservationPort, step_started_at_utc: str
) -> tuple[dict[str, Any], str | None]:
    try:
        value = port.observe_function_deployment(
            tenant_id=TENANT_ID,
            subscription_id=SUBSCRIPTION_ID,
            resource_group=RESOURCE_GROUP,
            function_app=FUNCTION_APP,
            step_started_at_utc=step_started_at_utc,
        )
    except ValueError as exc:
        code = str(exc)
        return {}, (
            code
            if code in _OBSERVATION_ERROR_CODES
            else "FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_INVALID"
        )
    except Exception:
        return {}, "FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_INVALID"
    return value if isinstance(value, dict) else {}, None


def _observation_is_valid(
    value: dict[str, Any], step_started_at_utc: str
) -> bool:
    site = value.get("site")
    deployments = value.get("arm_deployments")
    expected_keys = {
        "tenant_id",
        "subscription_id",
        "resource_group",
        "function_app",
        "classification",
        "step_started_at_utc",
        "site",
        "arm_deployments",
        "deployment_status_count",
        "one_deploy",
    }
    return bool(
        set(value) == expected_keys
        and value.get("tenant_id") == TENANT_ID
        and value.get("subscription_id") == SUBSCRIPTION_ID
        and value.get("resource_group") == RESOURCE_GROUP
        and value.get("function_app") == FUNCTION_APP
        and value.get("classification") == NOT_APPLIED
        and value.get("step_started_at_utc") == step_started_at_utc
        and isinstance(site, dict)
        and set(site) == {"state", "last_modified_at_utc"}
        and site.get("state") == "Running"
        and _valid_timestamp(site.get("last_modified_at_utc"))
        and isinstance(deployments, dict)
        and set(deployments)
        == {
            "count",
            "latest_started_at_utc",
            "started_at_or_after_step_count",
        }
        and type(deployments.get("count")) is int
        and deployments["count"] >= 0
        and (
            deployments.get("latest_started_at_utc") is None
            or _valid_timestamp(deployments["latest_started_at_utc"])
        )
        and deployments.get("started_at_or_after_step_count") == 0
        and value.get("deployment_status_count") == 0
        and value.get("one_deploy") == "ABSENT"
        and _timestamp_before(
            site["last_modified_at_utc"], step_started_at_utc
        )
        and (
            deployments["latest_started_at_utc"] is None
            or _timestamp_before(
                deployments["latest_started_at_utc"],
                step_started_at_utc,
            )
        )
    )


def _continue_release(
    *,
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    lock_paths: tuple[Path, Path, Path],
    descriptors: tuple[int, int, int],
    marker: dict[str, Any],
    observation_port: FunctionDeploymentObservationPort,
    pre_mutation_revalidate: Callable[[], None],
    fault_injector: Callable[[str], None] | None,
) -> dict[str, Any]:
    marker_path = _marker_path(run_dir)
    while True:
        progress, error = _lock_progress(descriptors, marker)
        if error:
            return _blocked(error, writes_started=True)
        assert progress is not None
        released_count = progress["released_count"]
        expected_phase = _MARKER_PHASES[released_count]
        marker_phase_index = _MARKER_PHASES.index(marker["status"])
        if marker_phase_index > released_count:
            return _blocked(
                "FUNCTION_DEPLOYMENT_RELEASE_PROGRESS_INVALID",
                writes_started=True,
            )
        if marker_phase_index < released_count:
            if marker_phase_index + 1 != released_count:
                return _blocked(
                    "FUNCTION_DEPLOYMENT_RELEASE_PROGRESS_INVALID",
                    writes_started=True,
                )
            marker = _advance_marker(
                marker_path,
                marker,
                expected_phase,
                progress["released_hashes"],
            )
            continue
        if released_count == 3:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED",
                "error": {"code": "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED"},
                "writes_started": True,
                "failed_step": FAILED_STEP_ID,
                "reconciliation": {
                    "status": "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED",
                    "state_preserved": True,
                    "provider_write_count": 0,
                    "marker_sha256": runner._artifact_sha256(marker_path),
                },
                "resume_enabled": False,
                "provider_write_count": 0,
                "automatic_rollback_count": 0,
                "automatic_deletion_count": 0,
            }

        error = _pre_mutation_revalidation_error(
            run_dir=run_dir,
            state=state,
            state_path=state_path,
            descriptors=descriptors,
            approval_bindings=marker["approval_bindings"],
            observation_port=observation_port,
            pre_mutation_revalidate=pre_mutation_revalidate,
            marker=marker,
        )
        if error:
            return _blocked(error, writes_started=True)
        if not interruption._descriptors_match_paths(lock_paths, descriptors):
            return _blocked(
                "FUNCTION_DEPLOYMENT_LOCK_REPLACED", writes_started=True
            )
        descriptor = descriptors[released_count]
        raw = interruption._descriptor_bytes(descriptor)
        initial = marker["initial_locks"][_LOCK_NAMES[released_count]]
        if raw is None:
            return _blocked(
                "FUNCTION_DEPLOYMENT_LOCK_SET_INVALID", writes_started=True
            )
        raw = _repair_partial_release(descriptor, raw, initial, marker)
        if raw is None:
            return _blocked(
                "FUNCTION_DEPLOYMENT_RELEASE_PROGRESS_INVALID",
                writes_started=True,
            )
        if hashlib.sha256(raw).hexdigest() != initial["sha256"]:
            return _blocked(
                "FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED", writes_started=True
            )
        runner._write_lock_marker(
            descriptor, marker["activation_hash"], "RELEASED"
        )
        _checkpoint(fault_injector, f"lock:{_LOCK_NAMES[released_count]}")


def _pre_mutation_revalidation_error(
    *,
    run_dir: Path,
    state: dict[str, Any],
    state_path: Path,
    descriptors: tuple[int, int, int],
    approval_bindings: dict[str, Any],
    observation_port: FunctionDeploymentObservationPort,
    pre_mutation_revalidate: Callable[[], None],
    marker: dict[str, Any] | None = None,
) -> str | None:
    try:
        pre_mutation_revalidate()
    except runner.ActivationStepError as exc:
        return exc.code
    except Exception:
        return "FUNCTION_DEPLOYMENT_RUNTIME_REVALIDATION_FAILED"
    if runner._read_secure_canonical_json(state_path) != state:
        return "FUNCTION_DEPLOYMENT_STATE_CHANGED"
    current_state = runner._artifact_sha256(state_path)
    current_evidence = runner._artifact_sha256(run_dir / "activation.redacted.json")
    manifest = runner._artifact_sha256(
        run_dir / "prepared" / "prepared-inputs.redacted.json"
    )
    package = runner._artifact_sha256(
        run_dir / "prepared" / "nac-bff-function.zip"
    )
    if (
        current_state != approval_bindings.get("state_sha256")
        or current_evidence != approval_bindings.get("evidence_sha256")
        or manifest != approval_bindings.get("prepared_inputs_manifest_sha256")
        or package != approval_bindings.get("function_package_sha256")
    ):
        return "FUNCTION_DEPLOYMENT_LOCAL_ARTIFACT_CHANGED"
    observation, error = _stable_observation(
        observation_port,
        approval_bindings["failed_step_started_at_utc"],
    )
    if error:
        return error
    if runner._sha256_json(observation) != approval_bindings.get(
        "provider_observation_sha256"
    ):
        return "FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_DRIFT"
    if marker is None:
        current_hashes = {
            name: interruption._descriptor_sha256(descriptor)
            for name, descriptor in zip(_LOCK_NAMES, descriptors, strict=True)
        }
        expected = {
            name: approval_bindings[f"{name}_lock_sha256"]
            for name in _LOCK_NAMES
        }
        if current_hashes != expected:
            return "FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED"
    else:
        progress, progress_error = _lock_progress(descriptors, marker)
        if progress_error or progress is None:
            return progress_error or "FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED"
    return None


def _build_marker(
    *,
    request: runner.LiveActivationRequest,
    approval: FunctionDeploymentReleaseApproval,
    inspection: dict[str, Any],
    descriptors: tuple[int, int, int],
) -> dict[str, Any]:
    initial: dict[str, dict[str, Any]] = {}
    released_marker = runner._canonical_json_bytes({
        "activation_hash": request.expected_activation_hash,
        "status": "RELEASED",
    })
    for name, descriptor in zip(_LOCK_NAMES, descriptors, strict=True):
        raw = interruption._descriptor_bytes(descriptor)
        if raw is None:
            raise runner.ActivationStepError(
                "FUNCTION_DEPLOYMENT_LOCK_SET_INVALID"
            )
        separator = b"" if raw.endswith(b"\n") else b"\n"
        released = raw + separator + released_marker
        initial[name] = {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "size": len(raw),
            "released_sha256": hashlib.sha256(released).hexdigest(),
            "released_size": len(released),
        }
    return {
        "schema_version": MARKER_SCHEMA_VERSION,
        "status": "FUNCTION_DEPLOYMENT_RELEASE_AUTHORIZED",
        "action": ACTION,
        "activation_hash": request.expected_activation_hash,
        "original_approval_reference_sha256": runner._sha256(
            request.owner_approval_reference
        ),
        "terminalization_approval_reference_sha256": runner._sha256(
            approval.owner_approval_reference
        ),
        "terminalization_approval_body_sha256": approval.approval_body_sha256,
        "owner_comment_body": inspection["owner_comment"]["body"],
        "approval_bindings": inspection["approval_bindings"],
        "initial_locks": initial,
        "released_lock_sha256": {},
        "resume_enabled": False,
        "provider_write_count": 0,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }


def _lock_progress(
    descriptors: tuple[int, int, int], marker: dict[str, Any]
) -> tuple[dict[str, Any] | None, str | None]:
    statuses: list[str] = []
    released_hashes: dict[str, str] = {}
    for name, descriptor in zip(_LOCK_NAMES, descriptors, strict=True):
        raw = interruption._descriptor_bytes(descriptor)
        if raw is None:
            return None, "FUNCTION_DEPLOYMENT_LOCK_SET_INVALID"
        digest = hashlib.sha256(raw).hexdigest()
        initial = marker["initial_locks"][name]
        if digest == initial["sha256"] and runner._held_lock_marker_matches(
            runner._read_lock_marker_descriptor(descriptor),
            marker["activation_hash"],
        ):
            statuses.append("HELD")
        elif digest == initial["released_sha256"] and (
            runner._released_lock_marker_matches(
                runner._read_lock_marker_descriptor(descriptor),
                marker["activation_hash"],
            )
        ):
            statuses.append("RELEASED")
            released_hashes[name] = digest
        elif _partial_release_is_valid(raw, initial, marker):
            statuses.append("PARTIAL")
        else:
            return None, "FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED"
    released_count = 0
    while released_count < 3 and statuses[released_count] == "RELEASED":
        released_count += 1
    if any(status == "RELEASED" for status in statuses[released_count:]):
        return None, "FUNCTION_DEPLOYMENT_RELEASE_PROGRESS_INVALID"
    if statuses.count("PARTIAL") > 1 or (
        "PARTIAL" in statuses and statuses[released_count] != "PARTIAL"
    ):
        return None, "FUNCTION_DEPLOYMENT_RELEASE_PROGRESS_INVALID"
    expected_recorded = {
        name: released_hashes[name] for name in _LOCK_NAMES[:released_count]
    }
    recorded = marker.get("released_lock_sha256")
    phase_count = _MARKER_PHASES.index(marker["status"])
    if not isinstance(recorded, dict) or recorded != {
        name: released_hashes[name] for name in _LOCK_NAMES[:phase_count]
    }:
        return None, "FUNCTION_DEPLOYMENT_MARKER_INVALID"
    return {
        "released_count": released_count,
        "released_hashes": expected_recorded,
        "statuses": statuses,
    }, None


def _partial_release_is_valid(
    raw: bytes, initial: dict[str, Any], marker: dict[str, Any]
) -> bool:
    size = initial["size"]
    if not size < len(raw) < initial["released_size"]:
        return False
    prefix = raw[:size]
    if hashlib.sha256(prefix).hexdigest() != initial["sha256"]:
        return False
    separator = b"" if prefix.endswith(b"\n") else b"\n"
    complete = prefix + separator + runner._canonical_json_bytes({
        "activation_hash": marker["activation_hash"],
        "status": "RELEASED",
    })
    return complete.startswith(raw) and (
        hashlib.sha256(complete).hexdigest() == initial["released_sha256"]
    )


def _repair_partial_release(
    descriptor: int,
    raw: bytes,
    initial: dict[str, Any],
    marker: dict[str, Any],
) -> bytes | None:
    if hashlib.sha256(raw).hexdigest() == initial["sha256"]:
        return raw
    if not _partial_release_is_valid(raw, initial, marker):
        return None
    try:
        os.ftruncate(descriptor, initial["size"])
        os.fsync(descriptor)
    except OSError:
        return None
    repaired = interruption._descriptor_bytes(descriptor)
    return repaired


def _advance_marker(
    marker_path: Path,
    marker: dict[str, Any],
    status: str,
    released_hashes: dict[str, str],
) -> dict[str, Any]:
    updated = dict(marker)
    updated["status"] = status
    updated["released_lock_sha256"] = dict(released_hashes)
    runner._atomic_json_write(marker_path, updated)
    if runner._read_secure_canonical_json(marker_path) != updated:
        raise runner.ActivationStepError("FUNCTION_DEPLOYMENT_MARKER_INVALID")
    return updated


def _marker_is_valid(
    marker: dict[str, Any],
    request: runner.LiveActivationRequest,
    binding: FunctionDeploymentReconcilerBinding,
) -> bool:
    expected_keys = {
        "schema_version",
        "status",
        "action",
        "activation_hash",
        "original_approval_reference_sha256",
        "terminalization_approval_reference_sha256",
        "terminalization_approval_body_sha256",
        "owner_comment_body",
        "approval_bindings",
        "initial_locks",
        "released_lock_sha256",
        "resume_enabled",
        "provider_write_count",
        "automatic_rollback_count",
        "automatic_deletion_count",
    }
    bindings = marker.get("approval_bindings")
    initial = marker.get("initial_locks")
    if (
        set(marker) != expected_keys
        or marker.get("schema_version") != MARKER_SCHEMA_VERSION
        or marker.get("status") not in _MARKER_PHASES
        or marker.get("action") != ACTION
        or marker.get("activation_hash") != request.expected_activation_hash
        or marker.get("original_approval_reference_sha256")
        != runner._sha256(request.owner_approval_reference)
        or marker.get("resume_enabled") is not False
        or marker.get("provider_write_count") != 0
        or marker.get("automatic_rollback_count") != 0
        or marker.get("automatic_deletion_count") != 0
        or not isinstance(bindings, dict)
        or set(bindings) != _APPROVAL_BINDING_KEYS
        or bindings.get("reconciler_commit") != binding.approved_commit
        or bindings.get("reconciler_tree") != binding.approved_tree
        or bindings.get("reconciler_toolchain_sha256")
        != binding.toolchain_sha256
        or bindings.get("required_owner_login") != binding.required_owner_login
        or bindings.get("required_owner_principal_id_sha256")
        != binding.required_owner_principal_id_sha256
        or not isinstance(initial, dict)
        or set(initial) != set(_LOCK_NAMES)
    ):
        return False
    body = marker.get("owner_comment_body")
    if not isinstance(body, str) or body != (
        "NAC_BFF_FUNCTION_DEPLOYMENT_RECONCILIATION_APPROVAL\n"
        + runner._canonical_json_bytes(bindings).decode("ascii")
    ):
        return False
    if hashlib.sha256(body.encode("utf-8")).hexdigest() != marker.get(
        "terminalization_approval_body_sha256"
    ):
        return False
    for name in _LOCK_NAMES:
        value = initial.get(name)
        if (
            not isinstance(value, dict)
            or set(value)
            != {"sha256", "size", "released_sha256", "released_size"}
            or not runner._SHA256_RE.fullmatch(str(value.get("sha256", "")))
            or not runner._SHA256_RE.fullmatch(
                str(value.get("released_sha256", ""))
            )
            or type(value.get("size")) is not int
            or type(value.get("released_size")) is not int
            or value["size"] < 1
            or value["released_size"] <= value["size"]
        ):
            return False
    return True


def _approval_shape_is_valid(
    approval: FunctionDeploymentReleaseApproval,
) -> bool:
    return bool(
        approval.owner_approved is True
        and approval.action == ACTION
        and _APPROVAL_REFERENCE_RE.fullmatch(approval.owner_approval_reference)
        and approval.failed_step == FAILED_STEP_ID
        and _valid_timestamp(approval.failed_step_started_at_utc)
        and _OWNER_RE.fullmatch(approval.required_owner_login)
        and runner._SHA256_RE.fullmatch(
            approval.required_owner_principal_id_sha256
        )
        and all(
            runner._SHA256_RE.fullmatch(value)
            for value in (
                approval.approval_body_sha256,
                approval.activation_hash,
                approval.state_sha256,
                approval.evidence_sha256,
                approval.ledger_head_sha256,
                approval.target_lock_sha256,
                approval.legacy_lock_sha256,
                approval.legacy_host_lock_sha256,
                approval.provider_observation_sha256,
                approval.prepared_inputs_manifest_sha256,
                approval.function_package_sha256,
                approval.reconciler_toolchain_sha256,
            )
        )
        and runner._COMMIT_RE.fullmatch(approval.reconciler_commit)
        and runner._COMMIT_RE.fullmatch(approval.reconciler_tree)
    )


def _approval_matches(
    approval: FunctionDeploymentReleaseApproval,
    inspection: dict[str, Any],
) -> bool:
    bindings = inspection.get("approval_bindings")
    comment = inspection.get("owner_comment")
    return bool(
        isinstance(bindings, dict)
        and set(bindings) == _APPROVAL_BINDING_KEYS
        and bindings == _approval_bindings(approval)
        and isinstance(comment, dict)
        and approval.approval_body_sha256 == comment.get("body_sha256")
    )


def _marker_approval_matches(
    marker: dict[str, Any], approval: FunctionDeploymentReleaseApproval
) -> bool:
    return bool(
        marker.get("approval_bindings") == _approval_bindings(approval)
        and marker.get("terminalization_approval_reference_sha256")
        == runner._sha256(approval.owner_approval_reference)
        and marker.get("terminalization_approval_body_sha256")
        == approval.approval_body_sha256
    )


def _approval_bindings(
    approval: FunctionDeploymentReleaseApproval,
) -> dict[str, str]:
    return {
        "action": approval.action,
        "activation_hash": approval.activation_hash,
        "state_sha256": approval.state_sha256,
        "evidence_sha256": approval.evidence_sha256,
        "ledger_head_sha256": approval.ledger_head_sha256,
        "target_lock_sha256": approval.target_lock_sha256,
        "legacy_lock_sha256": approval.legacy_lock_sha256,
        "legacy_host_lock_sha256": approval.legacy_host_lock_sha256,
        "provider_observation_sha256": approval.provider_observation_sha256,
        "failed_step": approval.failed_step,
        "failed_step_started_at_utc": approval.failed_step_started_at_utc,
        "prepared_inputs_manifest_sha256": (
            approval.prepared_inputs_manifest_sha256
        ),
        "function_package_sha256": approval.function_package_sha256,
        "reconciler_commit": approval.reconciler_commit,
        "reconciler_tree": approval.reconciler_tree,
        "reconciler_toolchain_sha256": approval.reconciler_toolchain_sha256,
        "required_owner_login": approval.required_owner_login,
        "required_owner_principal_id_sha256": (
            approval.required_owner_principal_id_sha256
        ),
    }


def _validate_bindings(
    request: runner.LiveActivationRequest,
    binding: FunctionDeploymentReconcilerBinding,
) -> str | None:
    request_error = interruption._validate_bound_live_request(request)
    if request_error:
        return request_error
    if (
        not runner._COMMIT_RE.fullmatch(binding.approved_commit)
        or not runner._COMMIT_RE.fullmatch(binding.approved_tree)
        or not runner._SHA256_RE.fullmatch(binding.toolchain_sha256)
        or not _OWNER_RE.fullmatch(binding.required_owner_login)
        or not runner._SHA256_RE.fullmatch(
            binding.required_owner_principal_id_sha256
        )
    ):
        return "FUNCTION_DEPLOYMENT_RECONCILER_BINDING_INVALID"
    return None


def _verify_function_owner_comment(
    verifier: ImmutableOwnerCommentVerifier,
    binding: FunctionDeploymentReconcilerBinding,
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
        and set(result)
        == {
            "status",
            "owner_login",
            "owner_principal_id_sha256",
            "immutable",
            "reference",
            "body",
            "body_sha256",
        }
        and result.get("status") == "VERIFIED"
        and result.get("owner_login") == binding.required_owner_login
        and result.get("owner_principal_id_sha256")
        == binding.required_owner_principal_id_sha256
        and result.get("immutable") is True
        and result.get("reference") == reference
        and result.get("body") == body
        and result.get("body_sha256") == body_sha256
    )


def _inspection_paths(
    run_dir: Path, lock_paths: tuple[Path, Path, Path]
) -> tuple[Path, ...] | None:
    try:
        ledger_paths = tuple(sorted((run_dir / "ledger").glob("*.redacted.json")))
    except OSError:
        return None
    required = (
        run_dir / "resume-state.redacted.json",
        run_dir / "activation.redacted.json",
        *ledger_paths,
        run_dir / "prepared" / "prepared-inputs.redacted.json",
        run_dir / "prepared" / "nac-bff-function.zip",
        *lock_paths,
    )
    return required if all(path.exists() for path in required) else None


def _snapshot_bytes(paths: tuple[Path, ...]) -> dict[Path, bytes] | None:
    snapshots: dict[Path, bytes] = {}
    for path in paths:
        raw = runner._read_secure_artifact_bytes(path)
        if raw is None:
            return None
        snapshots[path] = raw
    return snapshots


def _valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _timestamp_before(left: str, right: str) -> bool:
    return datetime.fromisoformat(left.replace("Z", "+00:00")) < (
        datetime.fromisoformat(right.replace("Z", "+00:00"))
    )


def _marker_path(run_dir: Path) -> Path:
    return run_dir / "activation.function-deployment-reconciliation.redacted.json"


def _checkpoint(
    fault_injector: Callable[[str], None] | None, point: str
) -> None:
    if fault_injector is not None:
        fault_injector(point)


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _path_entry_exists(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False
    return True


def _provenance_loss_blocked(
    code: str, *, terminal: bool = False
) -> dict[str, Any]:
    safe_code = runner._safe_error_code(code)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED",
        "reason_code": safe_code,
        "error": {"code": safe_code},
        "terminal": terminal,
        "retry_allowed": False,
        "next_phase": None,
        "writes_started": False,
        "resume_enabled": False,
        "operation_counts": {
            key: 0 for key in PROVENANCE_LOSS_COUNTER_KEYS
        },
        "provider_write_count": 0,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }


def _blocked(code: str, *, writes_started: bool = False) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED",
        "error": {"code": runner._safe_error_code(code)},
        "writes_started": writes_started,
        "resume_enabled": False,
        "provider_write_count": 0,
        "automatic_rollback_count": 0,
        "automatic_deletion_count": 0,
    }
