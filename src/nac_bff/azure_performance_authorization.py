"""Trusted issuance and durable live-action authorization.

Untrusted mappings and callers cannot mint owner, infrastructure, or live-action
authority. This boundary assumes callers cannot execute arbitrary Python inside
the trusted NaC process. Such code execution is out of scope because it can
monkeypatch any Python control, including type checks and module-private state.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import threading
from types import MappingProxyType
from typing import Any, Mapping

from .azure_performance_infrastructure_safety import (
    AzurePerformanceInfrastructureReadbackCapability,
    AzurePerformanceInfrastructureSafetyVerification,
    validate_infrastructure_safety_evidence,
    verify_azure_performance_infrastructure_safety,
)


TARGET_GET = "target_get"
MONITOR_READ = "monitor_read"
BLOB_BOOTSTRAP = "blob_bootstrap"
BLOB_LEASE_ACQUIRE = "blob_lease_acquire"
BLOB_LEASE_ASSERT_HELD = "blob_lease_assert_held"
BLOB_LEASE_RELEASE = "blob_lease_release"
MAXIMUM_MONITOR_READS = 2048

_ACTIONS = frozenset(
    {
        TARGET_GET,
        MONITOR_READ,
        BLOB_BOOTSTRAP,
        BLOB_LEASE_ACQUIRE,
        BLOB_LEASE_ASSERT_HELD,
        BLOB_LEASE_RELEASE,
    }
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
AUTHORIZATION_USAGE_ROOT = Path(
    "out/m365/teams-sharepoint/bff-performance-authorization-usage"
)
_USAGE_SCHEMA_VERSION = "nac.performance-authorization-usage/v1"


class PerformanceLiveAuthorizationError(ValueError):
    """Stable failure raised before a protected live action can start."""


class SecurePerformancePathError(ValueError):
    """A persistence path escaped the root-anchored no-symlink traversal."""


class VerifiedLiveActionCapability:
    """Opaque identity capability issued after owner and safety verification."""

    __slots__ = ("_nonce",)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("verified live-action capabilities cannot be constructed")


@dataclass
class _CapabilityState:
    capability: VerifiedLiveActionCapability
    target_binding_sha256: str
    action_bindings: Mapping[str, str]
    remaining_uses: dict[str, int]
    usage_ledger: _DurableAuthorizationUsageLedger | None


_CAPABILITY_LOCK = threading.Lock()
_CAPABILITY_STATES: dict[str, _CapabilityState] = {}


class VerifiedInfrastructureSafetySource:
    """Single-use source backed by the sealed infrastructure readback session."""

    __slots__ = ("_arguments", "_consumed", "_session")

    def __init__(
        self,
        *,
        readback_capability: AzurePerformanceInfrastructureReadbackCapability,
        verification_arguments: Mapping[str, Any],
    ) -> None:
        if type(readback_capability) is not AzurePerformanceInfrastructureReadbackCapability:
            raise TypeError("readback_capability")
        if not isinstance(verification_arguments, Mapping):
            raise TypeError("verification_arguments")
        arguments = dict(verification_arguments)
        if arguments.get("readback_session") is not readback_capability:
            raise ValueError("PERFORMANCE_INFRASTRUCTURE_READBACK_SOURCE_INVALID")
        self._session = readback_capability.session
        self._arguments = arguments
        self._consumed = False

    def _verify(
        self,
        *,
        owner_binding_sha256: str,
        target_binding_sha256: str,
        infrastructure_safety_policy_sha256: str,
    ) -> AzurePerformanceInfrastructureSafetyVerification:
        if self._consumed:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_INFRASTRUCTURE_READBACK_REPLAYED"
            )
        self._consumed = True
        if (
            self._session.owner_binding_sha256 != owner_binding_sha256
            or self._arguments.get("target_binding_sha256")
            != target_binding_sha256
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID"
            )
        try:
            evidence = validate_infrastructure_safety_evidence(
                verify_azure_performance_infrastructure_safety(**self._arguments)
            )
        except (TypeError, ValueError):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID"
            ) from None
        if (
            evidence.get("owner_binding_sha256") != owner_binding_sha256
            or evidence.get("target_binding_sha256") != target_binding_sha256
            or evidence.get("infrastructure_safety_policy_sha256")
            != infrastructure_safety_policy_sha256
            or evidence.get("readback_session_sha256")
            != self._session.session_sha256
            or evidence.get("readback_nonce_sha256")
            != self._session.nonce_sha256
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_INFRASTRUCTURE_PREFLIGHT_INVALID"
            )
        return evidence


class VerifiedPerformanceAuthority:
    """Owner-bound execution bindings paired with one bounded capability."""

    __slots__ = ("_bindings", "_capability")

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("verified performance authorities cannot be constructed")

    @property
    def execution_bindings(self) -> Mapping[str, str]:
        return self._bindings

    @property
    def capability(self) -> VerifiedLiveActionCapability:
        return self._capability


def _validated_authority_bindings(
    *,
    owner_authorization: object,
    infrastructure_safety_verification: AzurePerformanceInfrastructureSafetyVerification,
    execution_bindings: Mapping[str, str],
) -> tuple[dict[str, str], str, str]:
    from .azure_performance_acceptance import PerformanceExecutionAuthorization

    if type(owner_authorization) is not PerformanceExecutionAuthorization:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_OWNER_AUTHORIZATION_CAPABILITY_REQUIRED"
        )
    owner_authorization._assert_issued()
    if (
        type(infrastructure_safety_verification)
        is not AzurePerformanceInfrastructureSafetyVerification
    ):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED"
        )
    try:
        safety = validate_infrastructure_safety_evidence(
            infrastructure_safety_verification
        )
    except (TypeError, ValueError):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID"
        ) from None
    bindings = _validated_digest_mapping(execution_bindings)
    target = bindings.get("target_binding_sha256")
    owner_binding = bindings.get("owner_approval_body_sha256")
    safety_policy = bindings.get("infrastructure_safety_policy_sha256")
    safety_evidence = bindings.get("infrastructure_safety_evidence_sha256")
    if (
        target is None
        or owner_binding is None
        or safety_policy is None
        or safety_evidence is None
        or owner_authorization.target_binding_sha256 != target
        or owner_authorization.owner_approval_body_sha256 != owner_binding
        or owner_authorization.contract_sha256 != bindings.get("contract_sha256")
        or owner_authorization.activation_hash
        != bindings.get("expected_activation_hash")
        or owner_authorization.phase_plan_sha256
        != bindings.get("phase_plan_sha256")
        or owner_authorization.monitor_window_anchor_sha256
        != bindings.get("monitor_window_anchor_sha256")
        or safety.get("owner_binding_sha256") != owner_binding
        or safety.get("target_binding_sha256") != target
        or safety.get("infrastructure_safety_policy_sha256") != safety_policy
        or safety.get("infrastructure_safety_evidence_sha256") != safety_evidence
    ):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_EXECUTION_BINDING_MISMATCH"
        )
    return bindings, target, owner_binding


def _mint_verified_performance_authority(
    *,
    bindings: Mapping[str, str],
    target_binding_sha256: str,
    action_bindings: Mapping[str, tuple[str, int]],
    usage_ledger: _DurableAuthorizationUsageLedger | None,
    used_target_gets: int = 0,
) -> VerifiedPerformanceAuthority:
    live_bindings = {
        action: value[0] for action, value in action_bindings.items()
    }
    remaining_uses = {
        action: value[1] for action, value in action_bindings.items()
    }
    if usage_ledger is not None:
        remaining_uses[TARGET_GET] -= used_target_gets
        if remaining_uses[TARGET_GET] < 0:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
            )
    capability = object.__new__(VerifiedLiveActionCapability)
    nonce = secrets.token_hex(32)
    capability._nonce = nonce
    with _CAPABILITY_LOCK:
        _CAPABILITY_STATES[nonce] = _CapabilityState(
            capability=capability,
            target_binding_sha256=target_binding_sha256,
            action_bindings=MappingProxyType(live_bindings),
            remaining_uses=remaining_uses,
            usage_ledger=usage_ledger,
        )
    authority = object.__new__(VerifiedPerformanceAuthority)
    authority._bindings = MappingProxyType(dict(bindings))
    authority._capability = capability
    return authority


def _issue_verified_performance_authority(
    *,
    owner_authorization: object,
    infrastructure_safety_verification: AzurePerformanceInfrastructureSafetyVerification,
    execution_bindings: Mapping[str, str],
    action_bindings: Mapping[str, tuple[str, int]],
    repo_root: Path,
    run_binding_sha256: str,
    checkpoint_commit_path: Path,
    checkpoint_slot_paths: Mapping[str, Path],
    final_evidence_path: Path,
) -> VerifiedPerformanceAuthority:
    bindings, target, owner_binding = _validated_authority_bindings(
        owner_authorization=owner_authorization,
        infrastructure_safety_verification=infrastructure_safety_verification,
        execution_bindings=execution_bindings,
    )
    _require_sha256(run_binding_sha256)
    normalized_actions = _validated_action_bindings(action_bindings)
    target_specification = normalized_actions.get(TARGET_GET)
    if target_specification is None or target_specification[0] != target:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )
    monitor_policy = bindings.get("monitor_policy_sha256")
    monitor_specification = normalized_actions.get(MONITOR_READ)
    if monitor_policy is None:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_EXECUTION_BINDING_MISMATCH"
        )
    if monitor_specification is None:
        normalized_actions[MONITOR_READ] = (
            monitor_policy,
            MAXIMUM_MONITOR_READS,
        )
    elif (
        monitor_specification[0] != monitor_policy
        or monitor_specification[1] > MAXIMUM_MONITOR_READS
    ):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )
    ledger = _DurableAuthorizationUsageLedger(
        path=_authorization_usage_path(
            repo_root=repo_root,
            owner_binding_sha256=owner_binding,
            target_binding_sha256=target,
            run_binding_sha256=run_binding_sha256,
        ),
        owner_binding_sha256=owner_binding,
        target_binding_sha256=target,
        run_binding_sha256=run_binding_sha256,
        maximum_target_gets=target_specification[1],
        checkpoint_commit_path=checkpoint_commit_path,
        checkpoint_slot_paths=checkpoint_slot_paths,
        final_evidence_path=final_evidence_path,
    )
    used_target_gets = ledger.rehydrate()
    return _mint_verified_performance_authority(
        bindings=bindings,
        target_binding_sha256=target,
        action_bindings=normalized_actions,
        usage_ledger=ledger,
        used_target_gets=used_target_gets,
    )


def _issue_verified_bootstrap_authority(
    *,
    owner_authorization: object,
    infrastructure_safety_verification: AzurePerformanceInfrastructureSafetyVerification,
    execution_bindings: Mapping[str, str],
    bootstrap_binding_sha256: str,
) -> VerifiedPerformanceAuthority:
    bindings, target, _owner_binding = _validated_authority_bindings(
        owner_authorization=owner_authorization,
        infrastructure_safety_verification=infrastructure_safety_verification,
        execution_bindings=execution_bindings,
    )
    _require_sha256(bootstrap_binding_sha256)
    return _mint_verified_performance_authority(
        bindings=bindings,
        target_binding_sha256=target,
        action_bindings={BLOB_BOOTSTRAP: (bootstrap_binding_sha256, 2)},
        usage_ledger=None,
    )


def _transition_verified_bootstrap_authority(
    *,
    bootstrap_authority: object,
    bootstrap_binding_sha256: str,
    owner_authorization: object,
    infrastructure_safety_verification: AzurePerformanceInfrastructureSafetyVerification,
    execution_bindings: Mapping[str, str],
    action_bindings: Mapping[str, tuple[str, int]],
    repo_root: Path,
    run_binding_sha256: str,
    checkpoint_commit_path: Path,
    checkpoint_slot_paths: Mapping[str, Path],
    final_evidence_path: Path,
) -> VerifiedPerformanceAuthority:
    """Replace one exhausted bootstrap capability with one runtime capability."""

    if type(bootstrap_authority) is not VerifiedPerformanceAuthority:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_BOOTSTRAP_TRANSITION_INVALID"
        )
    _require_sha256(bootstrap_binding_sha256)
    if BLOB_BOOTSTRAP in action_bindings:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_BOOTSTRAP_TRANSITION_INVALID"
        )
    new_bindings, target, _owner_binding = _validated_authority_bindings(
        owner_authorization=owner_authorization,
        infrastructure_safety_verification=infrastructure_safety_verification,
        execution_bindings=execution_bindings,
    )
    old_bindings = _validated_digest_mapping(
        bootstrap_authority.execution_bindings
    )
    mutable_transition_bindings = {
        "lease_binding_sha256",
        "lease_acquisition_safety_evidence_sha256",
    }
    if any(
        old_bindings.get(key) != value
        for key, value in new_bindings.items()
        if key not in mutable_transition_bindings
    ) or any(
        new_bindings.get(key) != value
        for key, value in old_bindings.items()
        if key not in mutable_transition_bindings
    ):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_BOOTSTRAP_TRANSITION_BINDING_MISMATCH"
        )
    if (
        old_bindings.get("lease_binding_sha256") != bootstrap_binding_sha256
        or old_bindings.get("lease_acquisition_safety_evidence_sha256")
        != bootstrap_binding_sha256
    ):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_BOOTSTRAP_TRANSITION_BINDING_MISMATCH"
        )

    capability = bootstrap_authority.capability
    with _CAPABILITY_LOCK:
        state = _CAPABILITY_STATES.get(capability._nonce)
        if state is None or state.capability is not capability:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_BOOTSTRAP_TRANSITION_REPLAYED"
            )
        if (
            state.target_binding_sha256 != target
            or dict(state.action_bindings)
            != {BLOB_BOOTSTRAP: bootstrap_binding_sha256}
            or state.remaining_uses != {BLOB_BOOTSTRAP: 0}
            or state.usage_ledger is not None
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_BOOTSTRAP_TRANSITION_NOT_READY"
            )
        del _CAPABILITY_STATES[capability._nonce]
    try:
        return _issue_verified_performance_authority(
            owner_authorization=owner_authorization,
            infrastructure_safety_verification=(
                infrastructure_safety_verification
            ),
            execution_bindings=new_bindings,
            action_bindings=action_bindings,
            repo_root=repo_root,
            run_binding_sha256=run_binding_sha256,
            checkpoint_commit_path=checkpoint_commit_path,
            checkpoint_slot_paths=checkpoint_slot_paths,
            final_evidence_path=final_evidence_path,
        )
    except Exception:
        with _CAPABILITY_LOCK:
            if capability._nonce not in _CAPABILITY_STATES:
                _CAPABILITY_STATES[capability._nonce] = state
        raise


def _authorize_live_action(
    capability: object,
    *,
    action: str,
    target_binding_sha256: str,
    binding_sha256: str,
    consume: bool,
    uses: int = 1,
) -> None:
    if type(uses) is not int or uses <= 0:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )
    if type(capability) is not VerifiedLiveActionCapability:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_CAPABILITY_REQUIRED"
        )
    with _CAPABILITY_LOCK:
        state = _CAPABILITY_STATES.get(capability._nonce)
        if state is None or state.capability is not capability:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_CAPABILITY_INVALID"
            )
        if (
            action not in state.action_bindings
            or state.target_binding_sha256 != target_binding_sha256
            or state.action_bindings[action] != binding_sha256
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH"
            )
        remaining = state.remaining_uses[action]
        if remaining < uses:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
            )
        if action == TARGET_GET and state.usage_ledger is not None:
            if uses != 1:
                raise PerformanceLiveAuthorizationError(
                    "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
                )
            used = state.usage_ledger.authorize(consume=consume)
            state.remaining_uses[action] = max(
                0, state.usage_ledger.maximum_target_gets - used
            )
        if consume:
            if action != TARGET_GET or state.usage_ledger is None:
                state.remaining_uses[action] = remaining - uses


class _DurableAuthorizationUsageLedger:
    """Private, process-safe target budget independent of checkpoints."""

    def __init__(
        self,
        *,
        path: Path,
        owner_binding_sha256: str,
        target_binding_sha256: str,
        run_binding_sha256: str,
        maximum_target_gets: int,
        checkpoint_commit_path: Path,
        checkpoint_slot_paths: Mapping[str, Path],
        final_evidence_path: Path,
    ) -> None:
        for digest in (
            owner_binding_sha256,
            target_binding_sha256,
            run_binding_sha256,
        ):
            _require_sha256(digest)
        if type(maximum_target_gets) is not int or maximum_target_gets <= 0:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
            )
        if set(checkpoint_slot_paths) != {"a", "b"} or any(
            not isinstance(value, Path) for value in checkpoint_slot_paths.values()
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
            )
        self.path = _absolute_path(path)
        self.maximum_target_gets = maximum_target_gets
        self._binding = {
            "owner_binding_sha256": owner_binding_sha256,
            "target_binding_sha256": target_binding_sha256,
            "run_binding_sha256": run_binding_sha256,
            "checkpoint_commit_path_sha256": _sha256_text(
                str(_absolute_path(checkpoint_commit_path))
            ),
            "final_evidence_path_sha256": _sha256_text(
                str(_absolute_path(final_evidence_path))
            ),
        }
        self._checkpoint_commit_path = _absolute_path(checkpoint_commit_path)
        self._checkpoint_slot_paths = {
            key: _absolute_path(value) for key, value in checkpoint_slot_paths.items()
        }
        self._final_evidence_path = _absolute_path(final_evidence_path)

    def rehydrate(self) -> int:
        return self._locked_update(consume=False, initialize=True)

    def authorize(self, *, consume: bool) -> int:
        return self._locked_update(consume=consume, initialize=False)

    def _locked_update(self, *, consume: bool, initialize: bool) -> int:
        parent_fd = _open_root_anchored_private_parent(self.path, create=True)
        if parent_fd is None:  # pragma: no cover - create=True
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
            )
        lock_fd: int | None = None
        try:
            lock_fd = _open_private_regular_at(
                parent_fd, self.path.name + ".lock", create=True
            )
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            record = _read_json_at(parent_fd, self.path.name)
            if record is None:
                if not initialize:
                    raise PerformanceLiveAuthorizationError(
                        "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
                    )
                record = self._new_record()
                _atomic_json_write_at(parent_fd, self.path.name, record)
            self._validate_record(record)
            used = record["used"][TARGET_GET]
            if used > 0 and not self._has_bound_recovery_evidence():
                raise PerformanceLiveAuthorizationError(
                    "PERFORMANCE_AUTHORIZATION_USAGE_RECOVERY_EVIDENCE_MISSING"
                )
            if used > self.maximum_target_gets or (
                consume and used == self.maximum_target_gets
            ):
                raise PerformanceLiveAuthorizationError(
                    "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
                )
            if consume:
                used += 1
                record["used"][TARGET_GET] = used
                _atomic_json_write_at(parent_fd, self.path.name, record)
            return used
        finally:
            if lock_fd is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                finally:
                    os.close(lock_fd)
            os.close(parent_fd)

    def _new_record(self) -> dict[str, Any]:
        return {
            "schema_version": _USAGE_SCHEMA_VERSION,
            "binding": dict(self._binding),
            "limits": {TARGET_GET: self.maximum_target_gets},
            "used": {TARGET_GET: 0},
        }

    def _validate_record(self, record: object) -> None:
        if (
            not isinstance(record, dict)
            or set(record) != {"schema_version", "binding", "limits", "used"}
            or record.get("schema_version") != _USAGE_SCHEMA_VERSION
            or record.get("binding") != self._binding
            or record.get("limits") != {TARGET_GET: self.maximum_target_gets}
            or not isinstance(record.get("used"), dict)
            or set(record["used"]) != {TARGET_GET}
            or type(record["used"][TARGET_GET]) is not int
            or not 0 <= record["used"][TARGET_GET] <= self.maximum_target_gets
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
            )

    def _has_bound_recovery_evidence(self) -> bool:
        expected = {
            "owner_approval_body_sha256": self._binding["owner_binding_sha256"],
            "target_binding_sha256": self._binding["target_binding_sha256"],
            "plan_sha256": self._binding["run_binding_sha256"],
        }
        final = _read_root_anchored_json(self._final_evidence_path)
        if isinstance(final, dict) and all(
            final.get(key) == value for key, value in expected.items()
        ):
            return True
        commit = _read_root_anchored_json(self._checkpoint_commit_path)
        if (
            not isinstance(commit, dict)
            or set(commit) != {"schema_version", "slot", "state_sha256"}
            or commit.get("schema_version")
            != "nac.performance-checkpoint-commit/v1"
            or commit.get("slot") not in self._checkpoint_slot_paths
            or not isinstance(commit.get("state_sha256"), str)
            or _SHA256_RE.fullmatch(commit["state_sha256"]) is None
        ):
            return False
        state = _read_root_anchored_json(
            self._checkpoint_slot_paths[commit["slot"]]
        )
        return (
            isinstance(state, dict)
            and _sha256_json(state) == commit["state_sha256"]
            and all(state.get(key) == value for key, value in expected.items())
        )


def _open_root_anchored_private_parent(
    path: Path,
    *,
    create: bool,
) -> int | None:
    """Open a private parent without following a symlink in any component."""

    if not isinstance(path, Path) or path.name in {"", ".", ".."}:
        raise SecurePerformancePathError("PERFORMANCE_SECURE_PATH_INVALID")
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise SecurePerformancePathError("PERFORMANCE_SECURE_PATH_INVALID")
    absolute = Path(os.path.abspath(path.expanduser()))
    components = absolute.parent.parts
    if not components or components[0] != os.sep:
        raise SecurePerformancePathError("PERFORMANCE_SECURE_PATH_INVALID")
    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | nofollow
        | getattr(os, "O_CLOEXEC", 0)
    )
    descriptor = os.open(os.sep, flags)
    try:
        for component in components[1:]:
            if component in {"", ".", ".."}:
                raise SecurePerformancePathError(
                    "PERFORMANCE_SECURE_PATH_INVALID"
                )
            try:
                child = os.open(component, flags, dir_fd=descriptor)
            except FileNotFoundError:
                if not create:
                    os.close(descriptor)
                    return None
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                    child = os.open(component, flags, dir_fd=descriptor)
                except OSError:
                    raise SecurePerformancePathError(
                        "PERFORMANCE_SECURE_PATH_INVALID"
                    ) from None
            except OSError:
                raise SecurePerformancePathError(
                    "PERFORMANCE_SECURE_PATH_INVALID"
                ) from None
            os.close(descriptor)
            descriptor = child
        metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or metadata.st_uid != os.geteuid()
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise SecurePerformancePathError("PERFORMANCE_SECURE_PATH_INVALID")
        return descriptor
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _validated_action_bindings(
    value: Mapping[str, tuple[str, int]],
) -> dict[str, tuple[str, int]]:
    if not isinstance(value, Mapping) or not value:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )
    result: dict[str, tuple[str, int]] = {}
    for action, specification in value.items():
        if (
            action not in _ACTIONS
            or not isinstance(specification, tuple)
            or len(specification) != 2
        ):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
            )
        binding_sha256, maximum_uses = specification
        _require_sha256(binding_sha256)
        if type(maximum_uses) is not int or maximum_uses <= 0:
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
            )
        result[action] = (binding_sha256, maximum_uses)
    return result


def _authorization_usage_path(
    *,
    repo_root: Path,
    owner_binding_sha256: str,
    target_binding_sha256: str,
    run_binding_sha256: str,
) -> Path:
    root = _absolute_path(repo_root)
    key = _sha256_json(
        {
            "owner_binding_sha256": owner_binding_sha256,
            "target_binding_sha256": target_binding_sha256,
            "run_binding_sha256": run_binding_sha256,
        }
    )
    return root / AUTHORIZATION_USAGE_ROOT / key[:2] / key / "usage.json"


def _absolute_path(path: Path) -> Path:
    if not isinstance(path, Path):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )
    return Path(os.path.abspath(path.expanduser()))


def _open_private_regular_at(parent_fd: int, name: str, *, create: bool) -> int:
    if not isinstance(name, str) or name in {"", ".", ".."} or "/" in name:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
        )
    flags = os.O_RDWR | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    if create:
        flags |= os.O_CREAT
    try:
        descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
    except OSError:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
        ) from None
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        os.close(descriptor)
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
        )
    return descriptor


def _read_json_at(parent_fd: int, name: str) -> dict[str, Any] | None:
    try:
        descriptor = _open_private_regular_at(parent_fd, name, create=False)
    except PerformanceLiveAuthorizationError:
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return None
        raise
    try:
        with os.fdopen(os.dup(descriptor), "r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
        ) from None
    finally:
        os.close(descriptor)
    if not isinstance(value, dict):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
        )
    return value


def _atomic_json_write_at(parent_fd: int, name: str, value: Mapping[str, Any]) -> None:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    temporary = f".{name}.{secrets.token_hex(16)}.tmp"
    descriptor: int | None = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=parent_fd,
        )
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(
            temporary,
            name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
    except (OSError, TypeError, ValueError):
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_AUTHORIZATION_USAGE_LEDGER_INVALID"
        ) from None
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            os.unlink(temporary, dir_fd=parent_fd)
        except FileNotFoundError:
            pass


def _read_root_anchored_json(path: Path) -> dict[str, Any] | None:
    try:
        parent_fd = _open_root_anchored_private_parent(path, create=False)
    except SecurePerformancePathError:
        return None
    if parent_fd is None:
        return None
    try:
        return _read_json_at(parent_fd, path.name)
    except PerformanceLiveAuthorizationError:
        return None
    finally:
        os.close(parent_fd)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: Any) -> str:
    payload = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validated_digest_mapping(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )
    result = dict(value)
    for name, digest in result.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            raise PerformanceLiveAuthorizationError(
                "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
            )
        if name in {"approved_commit_sha", "approved_tree_sha"}:
            if re.fullmatch(r"[0-9a-f]{40}", digest) is None:
                raise PerformanceLiveAuthorizationError(
                    "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
                )
        else:
            _require_sha256(digest)
    return result


def _require_sha256(value: object) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise PerformanceLiveAuthorizationError(
            "PERFORMANCE_LIVE_AUTHORIZATION_INVALID"
        )


__all__ = [
    "PerformanceLiveAuthorizationError",
    "VerifiedInfrastructureSafetySource",
    "VerifiedLiveActionCapability",
    "VerifiedPerformanceAuthority",
]
