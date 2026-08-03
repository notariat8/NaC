from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from nac_bff import azure_performance_acceptance as acceptance
from nac_bff import azure_performance_authorization as authorization
from nac_bff.azure_performance_infrastructure_safety import (
    AzurePerformanceInfrastructureSafetyVerification,
)
from nac_bff.azure_performance_monitor import (
    AzurePerformanceMonitorAdapter,
    AzurePerformanceMonitorError,
    monitor_policy_sha256,
)


OWNER = "1" * 64
TARGET = "2" * 64
RUN = "3" * 64
POLICY = "4" * 64
SAFETY_EVIDENCE = "5" * 64
CONTRACT = "6" * 64
ACTIVATION = "7" * 64
PHASE_PLAN = "8" * 64
MONITOR_ANCHOR = "9" * 64
MONITOR_POLICY = monitor_policy_sha256()
BOOTSTRAP_BINDING = "a" * 64


def _owner_authorization():
    value = object.__new__(acceptance.PerformanceExecutionAuthorization)
    fields = {
        "status": "VERIFIED",
        "owner_login": acceptance.REQUIRED_OWNER_LOGIN,
        "owner_approval_reference_sha256": "a" * 64,
        "owner_approval_body_sha256": OWNER,
        "action": acceptance.OWNER_ACTION,
        "correlation_id": "authorization-ledger-test",
        "contract_sha256": CONTRACT,
        "activation_hash": ACTIVATION,
        "activation_receipt_sha256": "b" * 64,
        "activation_evidence_sha256": "c" * 64,
        "target_binding_sha256": TARGET,
        "measurement_preflight_sha256": "d" * 64,
        "phase_plan_sha256": PHASE_PLAN,
        "monitor_window_anchor_sha256": MONITOR_ANCHOR,
        "interruption_terminalization_status": (
            "VERIFIED_BY_COMMITTED_ACTIVATION_RECEIPT"
        ),
    }
    for name, field_value in fields.items():
        object.__setattr__(value, name, field_value)
    object.__setattr__(value, "_seal", acceptance._EXECUTION_AUTHORIZATION_SEAL)
    acceptance._ISSUED_EXECUTION_AUTHORIZATIONS[id(value)] = value
    return value


def _safety_verification(**overrides):
    evidence = {
        "owner_binding_sha256": OWNER,
        "target_binding_sha256": TARGET,
        "infrastructure_safety_policy_sha256": POLICY,
        "infrastructure_safety_evidence_sha256": SAFETY_EVIDENCE,
        **overrides,
    }
    value = dict.__new__(AzurePerformanceInfrastructureSafetyVerification)
    dict.__init__(value, evidence)
    return value


def _execution_bindings(**overrides):
    return {
        "contract_sha256": CONTRACT,
        "expected_activation_hash": ACTIVATION,
        "phase_plan_sha256": PHASE_PLAN,
        "monitor_window_anchor_sha256": MONITOR_ANCHOR,
        "monitor_policy_sha256": MONITOR_POLICY,
        "owner_approval_body_sha256": OWNER,
        "target_binding_sha256": TARGET,
        "infrastructure_safety_policy_sha256": POLICY,
        "infrastructure_safety_evidence_sha256": SAFETY_EVIDENCE,
        **overrides,
    }


def _artifact_paths(root: Path):
    run_dir = root / "checkpoint"
    return (
        run_dir / "state.commit.redacted.json",
        {
            "a": run_dir / "state.slot-a.redacted.json",
            "b": run_dir / "state.slot-b.redacted.json",
        },
        run_dir / "evidence.redacted.json",
    )


def _write_bound_checkpoint(root: Path) -> None:
    commit_path, slots, _evidence_path = _artifact_paths(root)
    commit_path.parent.mkdir(mode=0o700, parents=True)
    os.chmod(commit_path.parent, 0o700)
    state = {
        "owner_approval_body_sha256": OWNER,
        "target_binding_sha256": TARGET,
        "plan_sha256": RUN,
    }
    digest = authorization._sha256_json(state)
    slots["a"].write_text(
        json.dumps(state, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    os.chmod(slots["a"], 0o600)
    commit_path.write_text(
        json.dumps(
            {
                "schema_version": "nac.performance-checkpoint-commit/v1",
                "slot": "a",
                "state_sha256": digest,
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    os.chmod(commit_path, 0o600)


def _issue(
    root: Path,
    safety,
    *,
    maximum_target_gets: int = 2,
    maximum_monitor_reads: int | None = None,
):
    commit_path, slots, evidence_path = _artifact_paths(root)
    action_bindings = {
        authorization.TARGET_GET: (TARGET, maximum_target_gets),
    }
    if maximum_monitor_reads is not None:
        action_bindings[authorization.MONITOR_READ] = (
            MONITOR_POLICY,
            maximum_monitor_reads,
        )
    with patch.object(
        authorization,
        "validate_infrastructure_safety_evidence",
        return_value=safety,
    ):
        return authorization._issue_verified_performance_authority(
            owner_authorization=_owner_authorization(),
            infrastructure_safety_verification=safety,
            execution_bindings=_execution_bindings(),
            action_bindings=action_bindings,
            repo_root=root,
            run_binding_sha256=RUN,
            checkpoint_commit_path=commit_path,
            checkpoint_slot_paths=slots,
            final_evidence_path=evidence_path,
        )


def _issue_bootstrap(root: Path, safety):
    with patch.object(
        authorization,
        "validate_infrastructure_safety_evidence",
        return_value=safety,
    ):
        return authorization._issue_verified_bootstrap_authority(
            owner_authorization=_owner_authorization(),
            infrastructure_safety_verification=safety,
            execution_bindings=_execution_bindings(),
            bootstrap_binding_sha256=BOOTSTRAP_BINDING,
        )


class AzurePerformanceAuthorizationTests(unittest.TestCase):
    def test_bootstrap_authority_contains_only_bounded_blob_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = _issue_bootstrap(root, _safety_verification())
            with authorization._CAPABILITY_LOCK:
                state = authorization._CAPABILITY_STATES[
                    authority.capability._nonce
                ]
                self.assertEqual(
                    dict(state.action_bindings),
                    {authorization.BLOB_BOOTSTRAP: BOOTSTRAP_BINDING},
                )
                self.assertEqual(
                    state.remaining_uses,
                    {authorization.BLOB_BOOTSTRAP: 2},
                )
                self.assertIsNone(state.usage_ledger)

            for action, binding in (
                (authorization.TARGET_GET, TARGET),
                (authorization.MONITOR_READ, MONITOR_POLICY),
                (authorization.BLOB_LEASE_ACQUIRE, BOOTSTRAP_BINDING),
                (authorization.BLOB_LEASE_ASSERT_HELD, BOOTSTRAP_BINDING),
                (authorization.BLOB_LEASE_RELEASE, BOOTSTRAP_BINDING),
            ):
                with self.subTest(action=action), self.assertRaisesRegex(
                    ValueError,
                    "^PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH$",
                ):
                    authorization._authorize_live_action(
                        authority.capability,
                        action=action,
                        target_binding_sha256=TARGET,
                        binding_sha256=binding,
                        consume=True,
                    )

            for _ in range(2):
                authorization._authorize_live_action(
                    authority.capability,
                    action=authorization.BLOB_BOOTSTRAP,
                    target_binding_sha256=TARGET,
                    binding_sha256=BOOTSTRAP_BINDING,
                    consume=True,
                )
            with self.assertRaisesRegex(
                ValueError,
                "^PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED$",
            ):
                authorization._authorize_live_action(
                    authority.capability,
                    action=authorization.BLOB_BOOTSTRAP,
                    target_binding_sha256=TARGET,
                    binding_sha256=BOOTSTRAP_BINDING,
                    consume=True,
                )
            self.assertFalse((root / authorization.AUTHORIZATION_USAGE_ROOT).exists())

    def test_monitor_capability_cannot_exceed_issuer_read_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            ValueError,
            "^PERFORMANCE_LIVE_AUTHORIZATION_INVALID$",
        ):
            _issue(
                Path(directory),
                _safety_verification(),
                maximum_monitor_reads=authorization.MAXIMUM_MONITOR_READS + 1,
            )

    def test_monitor_capability_is_owner_bound_bounded_and_separate_from_500_gets(
        self,
    ) -> None:
        class CountingPort:
            def __init__(self) -> None:
                self.commands: list[tuple[str, ...]] = []

            def run_monitor_metrics(
                self,
                argv: object,
                *,
                live_action_capability: object,
                target_binding_sha256: str,
            ):
                authorization._authorize_live_action(
                    live_action_capability,
                    action=authorization.MONITOR_READ,
                    target_binding_sha256=target_binding_sha256,
                    binding_sha256=monitor_policy_sha256(),
                    consume=True,
                )
                self.commands.append(tuple(argv))
                raise RuntimeError("simulated command failure")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = _issue(
                root,
                _safety_verification(),
                maximum_target_gets=500,
                maximum_monitor_reads=1,
            )
            port = CountingPort()
            adapter = AzurePerformanceMonitorAdapter(
                port,
                clock=lambda: datetime(2026, 8, 3, 12, 10, tzinfo=UTC),
            )
            window_start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
            window_end = datetime(2026, 8, 3, 12, 1, tzinfo=UTC)

            with self.assertRaisesRegex(
                AzurePerformanceMonitorError,
                "^PERFORMANCE_MONITOR_READ_FAILED$",
            ):
                adapter.observe(
                    window_start,
                    window_end,
                    live_action_capability=authority.capability,
                    target_binding_sha256=TARGET,
                )
            self.assertEqual(len(port.commands), 1)

            with self.assertRaisesRegex(
                ValueError,
                "^PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED$",
            ):
                adapter.observe(
                    window_start,
                    window_end,
                    live_action_capability=authority.capability,
                    target_binding_sha256=TARGET,
                )
            self.assertEqual(len(port.commands), 1)

            fresh = _issue(
                root,
                _safety_verification(),
                maximum_target_gets=500,
                maximum_monitor_reads=1,
            )
            with self.assertRaisesRegex(
                ValueError,
                "^PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH$",
            ):
                adapter.observe(
                    window_start,
                    window_end,
                    live_action_capability=fresh.capability,
                    target_binding_sha256="f" * 64,
                )
            forged = object.__new__(authorization.VerifiedLiveActionCapability)
            forged._nonce = fresh.capability._nonce
            with self.assertRaisesRegex(
                ValueError,
                "^PERFORMANCE_LIVE_CAPABILITY_INVALID$",
            ):
                adapter.observe(
                    window_start,
                    window_end,
                    live_action_capability=forged,
                    target_binding_sha256=TARGET,
                )
            self.assertEqual(len(port.commands), 1)

            ledger_path = authorization._authorization_usage_path(
                repo_root=root,
                owner_binding_sha256=OWNER,
                target_binding_sha256=TARGET,
                run_binding_sha256=RUN,
            )
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(ledger["limits"][authorization.TARGET_GET], 500)
            self.assertEqual(ledger["used"][authorization.TARGET_GET], 0)
            with authorization._CAPABILITY_LOCK:
                state = authorization._CAPABILITY_STATES[
                    authority.capability._nonce
                ]
                self.assertEqual(
                    set(state.action_bindings),
                    {authorization.TARGET_GET, authorization.MONITOR_READ},
                )
                self.assertIsNotNone(state.usage_ledger)

    def test_untrusted_callers_and_digest_mappings_cannot_mint(self) -> None:
        with self.assertRaisesRegex(TypeError, "issued by owner verification"):
            acceptance.PerformanceExecutionAuthorization()
        with self.assertRaisesRegex(TypeError, "cannot be constructed"):
            authorization.VerifiedLiveActionCapability()
        with self.assertRaisesRegex(TypeError, "cannot be constructed"):
            authorization.VerifiedPerformanceAuthority()
        self.assertFalse(hasattr(authorization, "_issue_test_live_action_capability"))
        self.assertFalse(hasattr(authorization, "_issue_test_performance_authority"))
        self.assertFalse(hasattr(authorization, "_create_live_action_capability"))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commit_path, slots, evidence_path = _artifact_paths(root)
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_OWNER_AUTHORIZATION_CAPABILITY_REQUIRED"
            ):
                authorization._issue_verified_performance_authority(
                    owner_authorization=_execution_bindings(),
                    infrastructure_safety_verification=_safety_verification(),
                    execution_bindings=_execution_bindings(),
                    action_bindings={authorization.TARGET_GET: (TARGET, 1)},
                    repo_root=root,
                    run_binding_sha256=RUN,
                    checkpoint_commit_path=commit_path,
                    checkpoint_slot_paths=slots,
                    final_evidence_path=evidence_path,
                )
            with self.assertRaisesRegex(
                ValueError,
                "PERFORMANCE_INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED",
            ):
                authorization._issue_verified_performance_authority(
                    owner_authorization=_owner_authorization(),
                    infrastructure_safety_verification={  # type: ignore[arg-type]
                        "owner_binding_sha256": OWNER,
                        "target_binding_sha256": TARGET,
                    },
                    execution_bindings=_execution_bindings(),
                    action_bindings={authorization.TARGET_GET: (TARGET, 1)},
                    repo_root=root,
                    run_binding_sha256=RUN,
                    checkpoint_commit_path=commit_path,
                    checkpoint_slot_paths=slots,
                    final_evidence_path=evidence_path,
                )

    def test_authority_requires_matching_owner_and_safety_bindings(self) -> None:
        mismatches = (
            (_execution_bindings(owner_approval_body_sha256="e" * 64), _safety_verification()),
            (_execution_bindings(), _safety_verification(target_binding_sha256="e" * 64)),
            (
                _execution_bindings(infrastructure_safety_policy_sha256="e" * 64),
                _safety_verification(),
            ),
            (
                _execution_bindings(
                    infrastructure_safety_evidence_sha256="e" * 64
                ),
                _safety_verification(),
            ),
        )
        for bindings, safety in mismatches:
            with self.subTest(bindings=bindings, safety=dict(safety)):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    commit_path, slots, evidence_path = _artifact_paths(root)
                    with (
                        patch.object(
                            authorization,
                            "validate_infrastructure_safety_evidence",
                            return_value=safety,
                        ),
                        self.assertRaisesRegex(
                            ValueError, "PERFORMANCE_EXECUTION_BINDING_MISMATCH"
                        ),
                    ):
                        authorization._issue_verified_performance_authority(
                            owner_authorization=_owner_authorization(),
                            infrastructure_safety_verification=safety,
                            execution_bindings=bindings,
                            action_bindings={
                                authorization.TARGET_GET: (TARGET, 2)
                            },
                            repo_root=root,
                            run_binding_sha256=RUN,
                            checkpoint_commit_path=commit_path,
                            checkpoint_slot_paths=slots,
                            final_evidence_path=evidence_path,
                        )

    def test_replay_wrong_binding_and_cross_capability_overuse_are_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_bound_checkpoint(root)
            safety = _safety_verification()
            first = _issue(root, safety)
            capability = first.capability

            authorization._authorize_live_action(
                capability,
                action=authorization.TARGET_GET,
                target_binding_sha256=TARGET,
                binding_sha256=TARGET,
                consume=True,
            )
            ledger_path = authorization._authorization_usage_path(
                repo_root=root,
                owner_binding_sha256=OWNER,
                target_binding_sha256=TARGET,
                run_binding_sha256=RUN,
            )
            persisted = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["used"][authorization.TARGET_GET], 1)
            self.assertEqual(stat.S_IMODE(ledger_path.parent.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(ledger_path.stat().st_mode), 0o600)

            forged = object.__new__(authorization.VerifiedLiveActionCapability)
            forged._nonce = capability._nonce
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_LIVE_CAPABILITY_INVALID"
            ):
                authorization._authorize_live_action(
                    forged,
                    action=authorization.TARGET_GET,
                    target_binding_sha256=TARGET,
                    binding_sha256=TARGET,
                    consume=True,
                )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH"
            ):
                authorization._authorize_live_action(
                    capability,
                    action=authorization.TARGET_GET,
                    target_binding_sha256="f" * 64,
                    binding_sha256=TARGET,
                    consume=True,
                )

            second = _issue(root, safety)
            authorization._authorize_live_action(
                second.capability,
                action=authorization.TARGET_GET,
                target_binding_sha256=TARGET,
                binding_sha256=TARGET,
                consume=True,
            )
            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
            ):
                authorization._authorize_live_action(
                    capability,
                    action=authorization.TARGET_GET,
                    target_binding_sha256=TARGET,
                    binding_sha256=TARGET,
                    consume=True,
                )

    def test_exhausted_target_budget_rehydrates_for_finalization_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _write_bound_checkpoint(root)
            safety = _safety_verification()
            first = _issue(root, safety, maximum_target_gets=1)
            authorization._authorize_live_action(
                first.capability,
                action=authorization.TARGET_GET,
                target_binding_sha256=TARGET,
                binding_sha256=TARGET,
                consume=True,
            )

            recovered = _issue(root, safety, maximum_target_gets=1)

            with self.assertRaisesRegex(
                ValueError, "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED"
            ):
                authorization._authorize_live_action(
                    recovered.capability,
                    action=authorization.TARGET_GET,
                    target_binding_sha256=TARGET,
                    binding_sha256=TARGET,
                    consume=True,
                )
    def test_two_process_restart_blocks_after_checkpoint_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            counter = root / "network-count.txt"
            _write_bound_checkpoint(root)
            common = {
                "root": str(root),
                "counter": str(counter),
                "owner": OWNER,
                "target": TARGET,
                "run": RUN,
            }
            script = r'''
import json
import os
from pathlib import Path
import sys
from nac_bff import azure_performance_authorization as a

values = json.loads(sys.argv[1])
root = Path(values["root"])
commit = root / "checkpoint/state.commit.redacted.json"
slots = {
    "a": root / "checkpoint/state.slot-a.redacted.json",
    "b": root / "checkpoint/state.slot-b.redacted.json",
}
ledger = a._DurableAuthorizationUsageLedger(
    path=a._authorization_usage_path(
        repo_root=root,
        owner_binding_sha256=values["owner"],
        target_binding_sha256=values["target"],
        run_binding_sha256=values["run"],
    ),
    owner_binding_sha256=values["owner"],
    target_binding_sha256=values["target"],
    run_binding_sha256=values["run"],
    maximum_target_gets=2,
    checkpoint_commit_path=commit,
    checkpoint_slot_paths=slots,
    final_evidence_path=root / "checkpoint/evidence.redacted.json",
)
if sys.argv[2] == "first":
    ledger.rehydrate()
    ledger.authorize(consume=True)
    with Path(values["counter"]).open("a", encoding="utf-8") as stream:
        stream.write("GET\n")
else:
    try:
        ledger.rehydrate()
        ledger.authorize(consume=True)
    except a.PerformanceLiveAuthorizationError as error:
        if str(error) != "PERFORMANCE_AUTHORIZATION_USAGE_RECOVERY_EVIDENCE_MISSING":
            raise
        print("blocked")
    else:
        with Path(values["counter"]).open("a", encoding="utf-8") as stream:
            stream.write("GET\n")
'''
            environment = {
                **os.environ,
                "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
            }
            first = subprocess.run(
                [sys.executable, "-c", script, json.dumps(common), "first"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(counter.read_text(encoding="utf-8"), "GET\n")

            shutil.rmtree(root / "checkpoint")
            second = subprocess.run(
                [sys.executable, "-c", script, json.dumps(common), "second"],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(second.stdout.strip(), "blocked")
            self.assertEqual(counter.read_text(encoding="utf-8"), "GET\n")


if __name__ == "__main__":
    unittest.main()
