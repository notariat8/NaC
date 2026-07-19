from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import fcntl
import os
import pwd
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nac_bff.azure_activation_runner import (
    ActivationStepError,
    DEFAULT_OUTPUT_ROOT,
    LiveActivationRequest,
    _binding_sha256_json,
    _acquire_lock,
    _HOST_LOCK_ROOT,
    _LEGACY_HOST_LOCK_ROOT,
    _LEGACY_HOST_STATE_RELATIVE_PATH,
    _HOST_STATE_RELATIVE_PATH,
    _load_existing_evidence,
    _read_secure_canonical_json,
    _read_lock_marker_descriptor,
    _sha256_json,
    _atomic_json_write,
    _state_matches_chain,
    _write_lock_marker,
    _validate_event_chain,
    reconcile_azure_bff_live_activation_lock,
    run_azure_bff_live_activation,
)


HASH = "a" * 64
COMMIT = "b" * 40
TREE = "d" * 40
BODY_HASH = "e" * 64
PERMISSION_HASH = "f" * 64
AZURE_TOOLCHAIN_HASH = "1" * 64
M365_CLI_HASH = "2" * 64
M365_NODE_HASH = "3" * 64
BUILD_NODE_HASH = "4" * 64
BUILD_NPM_HASH = "5" * 64
GH_CLI_HASH = "6" * 64
PROVISIONER_CERTIFICATE_HASH = "7" * 64
PROVISIONER_BOOTSTRAP_BINDING_HASH = "9" * 64
APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/632#issuecomment-123456789"
)
STEPS = [
    "register_azure_providers",
    "ensure_resource_group",
    "ensure_entra_api_application",
    "deploy_bicep_baseline",
    "assign_sites_selected",
    "grant_target_site_read",
    "deploy_function_package",
    "build_and_deploy_spfx",
    "approve_spfx_bff_scope",
    "seed_synthetic_workspace",
    "run_access_and_readback_smokes",
    "run_idempotency_and_evidence",
]


class _Port:
    def __init__(
        self,
        *,
        fail_at: str | None = None,
        fail_code: str = "INJECTED_FAILURE",
        outcome: dict | None = None,
        ordering: list[str] | None = None,
        prewrite_failures: int = 0,
        prewrite_prebuilt_inputs_verified: object = True,
        ensure_prebuilt_inputs_verified: object = True,
        step_11_signals: dict[str, object] | None = None,
    ) -> None:
        self.fail_at = fail_at
        self.fail_code = fail_code
        self.outcome = outcome
        self.ordering = ordering
        self.prewrite_failures = prewrite_failures
        self.prewrite_prebuilt_inputs_verified = (
            prewrite_prebuilt_inputs_verified
        )
        self.ensure_prebuilt_inputs_verified = ensure_prebuilt_inputs_verified
        self.step_11_signals = (
            {
                "assigned_access_passed": True,
                "deputy_access_passed": True,
                "denied_access_passed": True,
                "tampered_access_passed": True,
                "healthz_before_auth_passed": True,
                "authenticated_read_passed": True,
                "readyz_after_authenticated_read_passed": True,
                "synthetic_state_restored": True,
            }
            if step_11_signals is None
            else step_11_signals
        )
        self.calls: list[str] = []
        self.prewrite_calls = 0

    def verify_prewrite(self, context, request):
        del context, request
        self.prewrite_calls += 1
        if self.ordering is not None:
            self.ordering.append("prewrite")
        if self.prewrite_failures:
            self.prewrite_failures -= 1
            return {"status": "FAILED", "code": "PREWRITE_TRANSIENT_FAILURE"}
        return {
            "status": "PASSED",
            "code": "PREWRITE_VERIFIED",
            "prebuilt_inputs_verified": self.prewrite_prebuilt_inputs_verified,
        }

    def execute_step(self, step_id, context):
        del context
        self.calls.append(step_id)
        if step_id == self.fail_at:
            raise ActivationStepError(self.fail_code)
        result = dict(self.outcome or {
            "status": "PASSED",
            "classification": "verified",
            "verified_count": 1,
            "reference_sha256": "c" * 64,
        })
        if step_id == "ensure_entra_api_application":
            result.setdefault(
                "prebuilt_inputs_verified",
                self.ensure_prebuilt_inputs_verified,
            )
        if step_id == "run_access_and_readback_smokes":
            result.update(self.step_11_signals)
        return result


def _request(**overrides) -> LiveActivationRequest:
    values = {
        "expected_activation_hash": HASH,
        "approved_commit": COMMIT,
        "approved_tree": TREE,
        "owner_approval_reference": APPROVAL_REFERENCE,
        "approval_body_sha256": BODY_HASH,
        "azure_cli_toolchain_sha256": AZURE_TOOLCHAIN_HASH,
        "m365_cli_sha256": M365_CLI_HASH,
        "m365_node_sha256": M365_NODE_HASH,
        "build_python_sha256": "8" * 64,
        "build_node_sha256": BUILD_NODE_HASH,
        "build_npm_cli_sha256": BUILD_NPM_HASH,
        "gh_cli_sha256": GH_CLI_HASH,
        "provisioner_certificate_sha256": PROVISIONER_CERTIFICATE_HASH,
        "provisioner_bootstrap_binding_sha256": (
            PROVISIONER_BOOTSTRAP_BINDING_HASH
        ),
        "reason": "Activate the synthetic MVP BFF",
        "correlation_id": "nac-bff-live-20260714",
        "owner_approved": True,
        "execute_live_activation": True,
        "resume": False,
    }
    values.update(overrides)
    return LiveActivationRequest(**values)


def _plan(*, activation_hash: str = HASH, commit: str = COMMIT) -> dict:
    return {
        "status": "READY",
        "activation_hash": activation_hash,
        "source_control": {"commit": commit},
        "bindings": {"workspace_id": "notary_team_01"},
        "steps": [{"id": step} for step in STEPS],
    }


def _run_dir(root: Path) -> Path:
    return root / DEFAULT_OUTPUT_ROOT / HASH


def _lock_path(root: Path) -> Path:
    target_hash = _binding_sha256_json({"workspace_id": "notary_team_01"})
    return root / ".test-locks" / f"{target_hash}.lock"


def _legacy_lock_path(root: Path) -> Path:
    target_hash = _sha256_json({"workspace_id": "notary_team_01"})
    return root / ".test-locks" / f"{target_hash}.lock"


def _legacy_host_lock_path(root: Path) -> Path:
    target_hash = _sha256_json({"workspace_id": "notary_team_01"})
    return root / ".legacy-test-locks" / f"{target_hash}.lock"


def _read_test_lock_marker(path: Path) -> dict | None:
    descriptor = os.open(
        path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    )
    try:
        return _read_lock_marker_descriptor(descriptor)
    finally:
        os.close(descriptor)


def _receipt_path(root: Path) -> Path:
    receipts = list(
        (root / ".test-locks" / "success-receipts").glob(
            "*.success.redacted.json"
        )
    )
    if len(receipts) != 1:
        raise AssertionError(f"expected one success receipt, got {len(receipts)}")
    return receipts[0]


class AzureBffActivationRunnerTests(unittest.TestCase):
    def test_binding_hash_uses_approval_compact_json_canonicalization(self) -> None:
        binding = {"workspace_id": "notary_team_01", "tenant_id": "f8"}
        compact = json.dumps(
            binding, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

        self.assertEqual(
            _binding_sha256_json(binding), hashlib.sha256(compact).hexdigest()
        )
        self.assertNotEqual(_binding_sha256_json(binding), _sha256_json(binding))

    def _managed_temp(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def _run(
        self,
        port,
        request=None,
        *,
        clean=True,
        plans=None,
        output_root=None,
        repo_root=None,
        lock_root=None,
        head_commit=COMMIT,
        head_tree=TREE,
        ordering=None,
    ):
        plan_values = iter(plans or [_plan(), _plan()])

        def next_plan(_root):
            if ordering is not None:
                ordering.append("plan")
            return next(plan_values)

        activation_repo_root = repo_root or self._managed_temp()
        canonical_output_root = activation_repo_root / DEFAULT_OUTPUT_ROOT
        activation_lock_root = lock_root or activation_repo_root / ".test-locks"
        with (
            patch(
                "nac_bff.azure_activation_runner.build_azure_bff_activation_plan",
                side_effect=next_plan,
            ),
            patch(
                "nac_bff.azure_activation_runner._permission_boundary_hash",
                return_value=PERMISSION_HASH,
            ),
            patch(
                "nac_bff.azure_activation_runner._clean_tree",
                return_value=clean,
            ),
            patch(
                "nac_bff.azure_activation_runner._head_commit",
                return_value=head_commit,
            ),
            patch(
                "nac_bff.azure_activation_runner._head_tree",
                return_value=head_tree,
            ),
            patch(
                "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                activation_lock_root,
            ),
            patch(
                "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                activation_repo_root / ".legacy-test-locks",
            ),
        ):
            return run_azure_bff_live_activation(
                repo_root=activation_repo_root,
                request=request or _request(),
                execution_port=port,
                output_root=output_root or canonical_output_root,
                now=lambda: datetime(
                    2026, 7, 14, 12, 0, tzinfo=timezone.utc
                ),
            )

    def test_owner_hash_commit_and_tree_gates_have_zero_execution(self) -> None:
        cases = (
            (_request(owner_approved=False), "OWNER_GATE_CLOSED", COMMIT, TREE),
            (
                _request(execute_live_activation=False),
                "OWNER_GATE_CLOSED",
                COMMIT,
                TREE,
            ),
            (
                _request(expected_activation_hash="0" * 64),
                "ACTIVATION_HASH_MISMATCH",
                COMMIT,
                TREE,
            ),
            (
                _request(approved_commit="0" * 40),
                "APPROVED_COMMIT_MISMATCH",
                COMMIT,
                TREE,
            ),
            (
                _request(approved_tree="0" * 40),
                "APPROVED_TREE_MISMATCH",
                COMMIT,
                TREE,
            ),
            (
                _request(m365_cli_sha256="not-a-digest"),
                "TOOLCHAIN_ATTESTATION_INVALID",
                COMMIT,
                TREE,
            ),
        )
        for request, code, head_commit, head_tree in cases:
            with self.subTest(code=code):
                port = _Port()
                result = self._run(
                    port,
                    request=request,
                    head_commit=head_commit,
                    head_tree=head_tree,
                )
                self.assertEqual(result["status"], "OFFLINE_READY")
                self.assertEqual(result["error"]["code"], code)
                self.assertFalse(result["writes_started"])
                self.assertEqual(port.calls, [])

    def test_default_host_state_root_is_persistent_user_state(self) -> None:
        expected = (
            Path(pwd.getpwuid(os.geteuid()).pw_dir)
            / ".local/state/nac/m365-bff-live-activation"
        )
        self.assertEqual(
            _HOST_STATE_RELATIVE_PATH,
            ".local/state/nac/m365-bff-live-activation",
        )
        self.assertEqual(_HOST_LOCK_ROOT, expected)
        self.assertNotEqual(_HOST_LOCK_ROOT.parent, Path(tempfile.gettempdir()))
        self.assertEqual(
            _LEGACY_HOST_STATE_RELATIVE_PATH,
            "nac-m365-bff-live-activation-locks",
        )
        self.assertEqual(
            _LEGACY_HOST_LOCK_ROOT,
            Path(tempfile.gettempdir())
            / "nac-m365-bff-live-activation-locks",
        )

    def test_legacy_binding_lock_blocks_new_hash_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_lock = _legacy_lock_path(root)
            legacy_lock.parent.mkdir(parents=True, mode=0o700)
            legacy_lock.write_text(
                json.dumps({"activation_hash": "9" * 64}, sort_keys=True) + "\n"
            )
            port = _Port()

            result = self._run(port, repo_root=root)

            self.assertEqual(
                result["error"]["code"], "LEGACY_ACTIVATION_LOCK_HELD"
            )
            self.assertEqual(port.prewrite_calls, 0)
            self.assertEqual(port.calls, [])
            self.assertTrue(legacy_lock.exists())

    def test_old_host_lock_namespace_blocks_new_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_lock = _legacy_host_lock_path(root)
            old_lock.parent.mkdir(parents=True, mode=0o700)
            old_lock.write_text(
                json.dumps({"activation_hash": "9" * 64}, sort_keys=True) + "\n"
            )
            port = _Port()

            result = self._run(port, repo_root=root)

            self.assertEqual(
                result["error"]["code"],
                "LEGACY_HOST_ACTIVATION_LOCK_HELD",
            )
            self.assertEqual(port.prewrite_calls, 0)
            self.assertEqual(port.calls, [])
            self.assertTrue(old_lock.exists())

    def test_ambiguous_arm_state_retains_cross_version_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._run(
                _Port(
                    fail_at="deploy_bicep_baseline",
                    fail_code="AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
                ),
                repo_root=root,
            )

            self.assertEqual(first["status"], "FAILED_PARTIAL")
            self.assertEqual(
                first["step_results"][-1]["stable_error_code"],
                "AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
            )
            self.assertTrue(_lock_path(root).exists())
            self.assertTrue(_legacy_lock_path(root).exists())
            self.assertTrue(_legacy_host_lock_path(root).exists())
            state = json.loads(
                (_run_dir(root) / "resume-state.redacted.json").read_text()
            )
            events, chain_error = _validate_event_chain(
                _run_dir(root) / "ledger"
            )
            self.assertIsNone(chain_error)
            self.assertEqual(
                events[0]["bindings"]["legacy_target_binding_sha256"],
                state["legacy_target_binding_sha256"],
            )
            self.assertTrue(_state_matches_chain(state, events))
            tampered_state = dict(state)
            tampered_state["legacy_target_binding_sha256"] = "0" * 64
            self.assertFalse(_state_matches_chain(tampered_state, events))

            other_hash = "9" * 64
            retry_port = _Port()
            second = self._run(
                retry_port,
                request=_request(expected_activation_hash=other_hash),
                plans=[_plan(activation_hash=other_hash)],
                repo_root=root,
            )

            self.assertEqual(
                second["error"]["code"],
                "LEGACY_HOST_ACTIVATION_LOCK_HELD",
            )
            self.assertEqual(retry_port.prewrite_calls, 0)
            self.assertEqual(retry_port.calls, [])
            self.assertTrue(_lock_path(root).exists())
            self.assertTrue(_legacy_lock_path(root).exists())
            self.assertTrue(_legacy_host_lock_path(root).exists())

            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                reconcile = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )

            self.assertEqual(
                reconcile["error"]["code"], "FINALIZATION_STATE_INVALID"
            )
            self.assertTrue(_lock_path(root).exists())
            self.assertTrue(_legacy_lock_path(root).exists())

    def test_dirty_tree_blocks_before_plan_or_execution(self) -> None:
        port = _Port()
        ordering: list[str] = []
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self._run(
                port,
                clean=False,
                repo_root=root,
                ordering=ordering,
            )
            self.assertFalse(_run_dir(root).exists())
        self.assertEqual(result["error"]["code"], "GIT_WORKTREE_NOT_CLEAN")
        self.assertEqual(ordering, [])
        self.assertEqual(port.calls, [])

    def test_prewrite_precedes_final_hash_and_git_recomputation(self) -> None:
        ordering: list[str] = []
        port = _Port(ordering=ordering)
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                port, repo_root=Path(tmp), ordering=ordering
            )
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(ordering[:3], ["plan", "prewrite", "plan"])

    def test_existing_app_prewrite_true_remains_true(self) -> None:
        port = _Port(
            prewrite_prebuilt_inputs_verified=True,
            ensure_prebuilt_inputs_verified=True,
        )
        result = self._run(port)

        self.assertEqual(result["status"], "PASSED")
        self.assertTrue(result["summary"]["prebuilt_inputs_verified"])

    def test_first_deploy_step_promotes_prewrite_false_to_true(self) -> None:
        port = _Port(
            prewrite_prebuilt_inputs_verified=False,
            ensure_prebuilt_inputs_verified=True,
        )
        result = self._run(port)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(port.calls[2], "ensure_entra_api_application")
        self.assertTrue(result["summary"]["prebuilt_inputs_verified"])

    def test_failure_before_app_step_preserves_false_summary_signal(self) -> None:
        port = _Port(
            fail_at=STEPS[1],
            prewrite_prebuilt_inputs_verified=False,
        )
        result = self._run(port)

        self.assertEqual(result["status"], "FAILED_PARTIAL")
        self.assertEqual(port.calls, STEPS[:2])
        self.assertFalse(result["summary"]["prebuilt_inputs_verified"])

    def test_prewrite_prebuilt_signal_requires_exact_bool(self) -> None:
        port = _Port(prewrite_prebuilt_inputs_verified="true")
        result = self._run(port)

        self.assertEqual(result["status"], "OFFLINE_READY")
        self.assertEqual(result["error"]["code"], "PREWRITE_RESULT_INVALID")
        self.assertEqual(port.calls, [])

    def test_app_step_prebuilt_signal_requires_exact_true_bool(self) -> None:
        cases = (
            ("true", "STEP_PREBUILT_INPUTS_STATUS_INVALID"),
            (False, "PREBUILT_INPUTS_NOT_VERIFIED"),
        )
        for value, code in cases:
            with self.subTest(value=value):
                port = _Port(
                    prewrite_prebuilt_inputs_verified=False,
                    ensure_prebuilt_inputs_verified=value,
                )
                result = self._run(port)

                self.assertEqual(result["status"], "FAILED_PARTIAL")
                self.assertEqual(result["step_results"][-1]["id"], STEPS[2])
                self.assertEqual(
                    result["step_results"][-1]["stable_error_code"], code
                )
                self.assertFalse(
                    result["summary"]["prebuilt_inputs_verified"]
                )

    def test_step_11_requires_all_exact_summary_signals(self) -> None:
        cases = (
            ({}, "STEP_11_SUMMARY_SIGNALS_INVALID"),
            (
                {
                    "healthz_before_auth_passed": True,
                    "authenticated_read_passed": True,
                    "readyz_after_authenticated_read_passed": True,
                    "synthetic_state_restored": False,
                },
                "STEP_11_SUMMARY_SIGNALS_INVALID",
            ),
            (
                {
                    "healthz_before_auth_passed": "true",
                    "authenticated_read_passed": True,
                    "readyz_after_authenticated_read_passed": True,
                    "synthetic_state_restored": True,
                },
                "STEP_SUMMARY_SIGNAL_INVALID",
            ),
            (
                {
                    "assigned_access_passed": False,
                    "deputy_access_passed": True,
                    "denied_access_passed": True,
                    "tampered_access_passed": True,
                    "healthz_before_auth_passed": True,
                    "authenticated_read_passed": True,
                    "readyz_after_authenticated_read_passed": True,
                    "synthetic_state_restored": True,
                },
                "STEP_11_SUMMARY_SIGNALS_INVALID",
            ),
        )
        for signals, expected_code in cases:
            with self.subTest(signals=signals):
                result = self._run(_Port(step_11_signals=signals))
                self.assertEqual(result["status"], "FAILED_PARTIAL")
                self.assertEqual(
                    result["step_results"][-1]["id"],
                    "run_access_and_readback_smokes",
                )
                self.assertEqual(
                    result["step_results"][-1]["stable_error_code"],
                    expected_code,
                )

    def test_final_recomputation_blocks_toctou_with_zero_writes(self) -> None:
        port = _Port()
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(
                port,
                plans=[_plan(), _plan(activation_hash="d" * 64)],
                repo_root=Path(tmp),
            )
            run_dir = _run_dir(Path(tmp))
            self.assertFalse(run_dir.exists())
            self.assertTrue(_lock_path(Path(tmp)).exists())
        self.assertEqual(result["status"], "OFFLINE_READY")
        self.assertEqual(
            result["error"]["code"], "FINAL_PREWRITE_BINDING_MISMATCH"
        )
        self.assertFalse(result["writes_started"])
        self.assertEqual(port.calls, [])

    def test_complete_run_has_exact_contract_evidence_and_hash_chain(self) -> None:
        port = _Port()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self._run(port, repo_root=root)
            run_dir = _run_dir(root)
            evidence_path = run_dir / "activation.redacted.json"
            state_path = run_dir / "resume-state.redacted.json"
            evidence = json.loads(evidence_path.read_text())
            contract = json.loads(
                (
                    Path(__file__).parents[1]
                    / "workflows/contracts/m365-azure-bff-live-activation.contract.json"
                ).read_text()
            )
            event_paths = sorted(
                (run_dir / "ledger").glob("*.redacted.json")
            )

            self.assertEqual(
                set(evidence),
                set(contract["evidence_policy"]["strict_top_level_allowlist"]),
            )
            expected_step_keys = set(
                contract["evidence_policy"]["step_result_allowlist"]
            )
            self.assertTrue(evidence["step_results"])
            self.assertTrue(
                all(set(step) == expected_step_keys for step in evidence["step_results"])
            )
            self.assertEqual(len(event_paths), 29)
            self.assertEqual(
                evidence["ledger_head_sha256"],
                __import__("hashlib").sha256(event_paths[-1].read_bytes()).hexdigest(),
            )
            phases = [
                json.loads(path.read_text())["phase"] for path in event_paths
            ]
            self.assertEqual(phases[0], "LOCK_ACQUIRED")
            self.assertEqual(
                phases[-2:], ["TERMINAL", "LOCK_RELEASE_AUTHORIZED"]
            )
            self.assertTrue(_lock_path(root).exists())
            self.assertTrue(_legacy_lock_path(root).exists())
            self.assertTrue(_legacy_host_lock_path(root).exists())
            commit_marker = run_dir / "activation.commit.redacted.json"
            self.assertTrue(commit_marker.exists())
            receipt = json.loads(_receipt_path(root).read_text())
            self.assertEqual(
                evidence["toolchain_attestations_sha256"],
                _request().toolchain_attestations_sha256,
            )
            self.assertEqual(
                receipt["toolchain_attestations_sha256"],
                _request().toolchain_attestations_sha256,
            )
            for path in [
                evidence_path,
                commit_marker,
                state_path,
                _receipt_path(root),
                *event_paths,
            ]:
                self.assertEqual(oct(path.stat().st_mode & 0o777), "0o600")

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["started_at_utc"], "2026-07-14T12:00:00Z")
        self.assertEqual(result["finished_at_utc"], "2026-07-14T12:00:00Z")
        self.assertEqual(result["approved_commit_sha"], COMMIT)
        self.assertEqual(result["approved_tree_sha"], TREE)
        self.assertEqual(result["permission_boundary_sha256"], PERMISSION_HASH)
        self.assertEqual(port.calls, STEPS)
        self.assertEqual(len(result["step_results"]), 12)
        self.assertEqual(
            set(result["summary"]),
            set(contract["evidence_policy"]["summary_field_allowlist_exact"])
            | {
                "assigned_access_passed",
                "deputy_access_passed",
                "denied_access_passed",
                "tampered_access_passed",
            },
        )
        self.assertEqual(result["summary"]["broader_permission_count"], 0)
        self.assertTrue(result["summary"]["prebuilt_inputs_verified"])
        self.assertTrue(result["summary"]["healthz_before_auth_passed"])
        self.assertTrue(result["summary"]["authenticated_read_passed"])
        self.assertTrue(
            result["summary"]["readyz_after_authenticated_read_passed"]
        )
        self.assertTrue(result["summary"]["synthetic_state_restored"])
        self.assertTrue(result["summary"]["assigned_access_passed"])
        self.assertTrue(result["summary"]["deputy_access_passed"])
        self.assertTrue(result["summary"]["denied_access_passed"])
        self.assertTrue(result["summary"]["tampered_access_passed"])
        self.assertFalse(result["summary"]["resume_enabled"])
        serialized = json.dumps(result)
        self.assertNotIn(APPROVAL_REFERENCE, serialized)
        self.assertNotIn("Activate the synthetic MVP BFF", serialized)

    def test_failure_after_write_is_failed_partial_and_stops(self) -> None:
        port = _Port(fail_at=STEPS[3])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self._run(port, repo_root=root)
            run_dir = _run_dir(root)
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            terminal = json.loads(
                sorted((run_dir / "ledger").glob("*-TERMINAL.redacted.json"))[-1]
                .read_text()
            )
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path),
                    {"activation_hash": HASH, "status": "RELEASED"},
                )
            self.assertEqual(
                list((root / ".test-locks" / "success-receipts").glob("*")),
                [],
            )

        self.assertEqual(result["status"], "FAILED_PARTIAL")
        self.assertEqual(result["step_results"][-1]["id"], STEPS[3])
        self.assertEqual(
            result["step_results"][-1]["stable_error_code"],
            "INJECTED_FAILURE",
        )
        self.assertEqual(port.calls, STEPS[:4])
        self.assertEqual(state["status"], "FAILED_PARTIAL")
        self.assertEqual(terminal["status"], "FAILED_PARTIAL")
        self.assertEqual(result["summary"]["automatic_rollback_count"], 0)
        self.assertEqual(result["summary"]["automatic_deletion_count"], 0)

    def test_resume_is_unsupported_before_any_filesystem_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence_root = root / "custom-evidence"
            port = _Port()
            result = self._run(
                port,
                request=_request(resume=True),
                output_root=evidence_root,
                repo_root=root,
            )
            self.assertFalse(evidence_root.exists())
            self.assertFalse((root / DEFAULT_OUTPUT_ROOT).exists())

        self.assertEqual(result["status"], "OFFLINE_READY")
        self.assertEqual(
            result["error"]["code"], "RESUME_DISABLED_FOR_MVP"
        )
        self.assertEqual(port.prewrite_calls, 0)
        self.assertEqual(port.calls, [])

    def test_custom_output_root_is_rejected_before_filesystem_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            custom_output_root = root / "custom-evidence"
            port = _Port()
            result = self._run(
                port, output_root=custom_output_root, repo_root=root
            )
            self.assertFalse(custom_output_root.exists())
            self.assertFalse(_lock_path(root).exists())

        self.assertEqual(result["error"]["code"], "OUTPUT_SCOPE_REJECTED")
        self.assertEqual(port.prewrite_calls, 0)
        self.assertEqual(port.calls, [])

    def test_host_global_target_lock_blocks_another_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_repo = root / "checkout-a"
            second_repo = root / "checkout-b"
            first_repo.mkdir()
            second_repo.mkdir()
            shared_lock_root = root / "host-locks"
            shared_lock_root.mkdir(mode=0o700)
            target_hash = _binding_sha256_json(
                {"workspace_id": "notary_team_01"}
            )
            lock = shared_lock_root / f"{target_hash}.lock"
            descriptor = os.open(
                lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600
            )
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                port = _Port()
                result = self._run(
                    port,
                    repo_root=second_repo,
                    lock_root=shared_lock_root,
                )
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)
                lock.unlink()

        self.assertEqual(result["error"]["code"], "ACTIVATION_LOCK_HELD")
        self.assertEqual(port.prewrite_calls, 0)
        self.assertEqual(port.calls, [])

    def test_prewrite_failure_releases_markers_and_new_approval_hash_can_retry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            port = _Port(prewrite_failures=1)
            first = self._run(port, repo_root=root)
            self.assertEqual(first["error"]["code"], "PREWRITE_TRANSIENT_FAILURE")
            self.assertFalse(_run_dir(root).exists())
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path)["status"], "RELEASED"
                )

            next_hash = "9" * 64
            second = self._run(
                port,
                repo_root=root,
                request=_request(expected_activation_hash=next_hash),
                plans=[
                    _plan(activation_hash=next_hash),
                    _plan(activation_hash=next_hash),
                ],
            )

        self.assertEqual(second["status"], "PASSED")
        self.assertEqual(port.prewrite_calls, 2)
        self.assertEqual(port.calls, STEPS)

    def test_failed_partial_cannot_be_blindly_retried(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._run(
                _Port(fail_at=STEPS[2]), repo_root=root
            )
            retry_port = _Port()
            second = self._run(retry_port, repo_root=root)

        self.assertEqual(first["status"], "FAILED_PARTIAL")
        self.assertEqual(
            second["error"]["code"], "EXISTING_RUN_REQUIRES_REVIEW"
        )
        self.assertEqual(retry_port.prewrite_calls, 0)
        self.assertEqual(retry_port.calls, [])

    def test_evidence_write_crash_never_persists_passed_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_evidence(path, payload):
                if path.name == "activation.redacted.json":
                    raise OSError("simulated evidence write failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_evidence,
            ):
                result = self._run(_Port(), repo_root=root)

            run_dir = _run_dir(root)
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            marker = json.loads(
                (
                    run_dir
                    / "activation.finalization-recovery.redacted.json"
                ).read_text()
            )
            self.assertEqual(result["status"], "FAILED_PARTIAL")
            self.assertEqual(result["error"]["code"], "FINALIZATION_FAILED")
            self.assertEqual(state["status"], "FINALIZATION_FAILED")
            self.assertEqual(marker["status"], "FINALIZATION_FAILED")
            self.assertFalse(
                (run_dir / "activation.commit.redacted.json").exists()
            )
            self.assertTrue(_lock_path(root).exists())

    def test_commit_marker_crash_leaves_evidence_non_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_marker(path, payload):
                if path.name == "activation.commit.redacted.json":
                    raise OSError("simulated final commit failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_marker,
            ):
                result = self._run(_Port(), repo_root=root)

            run_dir = _run_dir(root)
            evidence_path = run_dir / "activation.redacted.json"
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            loaded = _load_existing_evidence(evidence_path, _request())
            self.assertEqual(result["status"], "FAILED_PARTIAL")
            self.assertEqual(state["status"], "FINALIZATION_FAILED")
            self.assertEqual(
                loaded["error"]["code"], "EVIDENCE_FINAL_COMMIT_INVALID"
            )
            self.assertTrue(_lock_path(root).exists())

    def test_invalid_final_ledger_chain_never_claims_valid_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "nac_bff.azure_activation_runner._terminal_chain_is_valid",
                return_value=False,
            ):
                result = self._run(_Port(), repo_root=root)
            run_dir = _run_dir(root)
            self.assertFalse((run_dir / "activation.redacted.json").exists())
            self.assertTrue(_lock_path(root).exists())

        self.assertEqual(result["status"], "FAILED_PARTIAL")
        self.assertEqual(result["error"]["code"], "LEDGER_CHAIN_INVALID")
        self.assertTrue(result["writes_started"])

    def test_recovery_requires_legacy_markers_and_never_creates_roots(
        self,
    ) -> None:
        def fail_evidence(path, payload):
            if path.name == "activation.redacted.json":
                raise OSError("simulated evidence write failure")
            return _atomic_json_write(path, payload)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_evidence,
            ):
                self._run(_Port(), repo_root=root)
            _legacy_lock_path(root).unlink()
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                missing_legacy = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                )
            self.assertEqual(
                missing_legacy["error"]["code"],
                "LEGACY_ACTIVATION_LOCK_INVALID",
            )
            self.assertFalse(_legacy_lock_path(root).exists())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_evidence,
            ):
                self._run(_Port(), repo_root=root)
            receipts = root / ".test-locks" / "success-receipts"
            receipts.rmdir()
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                missing_root_member = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                )
            self.assertEqual(
                missing_root_member["error"]["code"],
                "HOST_STATE_ROOT_INVALID",
            )
            self.assertFalse(receipts.exists())

    def test_existing_empty_or_invalid_lock_journal_blocks_acquisition(
        self,
    ) -> None:
        invalid_payloads = (
            b"",
            b"{}\n",
            b'{"activation_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","status":"BROKEN"}\n',
        )
        for raw in invalid_payloads:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "activation.lock"
                path.write_bytes(raw)
                path.chmod(0o600)
                before = path.read_bytes()
                self.assertIsNone(_acquire_lock(path, HASH))
                self.assertEqual(path.read_bytes(), before)

    def test_canonical_newline_legacy_lock_is_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_evidence(path, payload):
                if path.name == "activation.redacted.json":
                    raise OSError("simulated evidence write failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_evidence,
            ):
                self._run(_Port(), repo_root=root)

            legacy = (
                json.dumps(
                    {"activation_hash": HASH},
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                path.write_bytes(legacy)
                path.chmod(0o600)
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                before = path.read_bytes()
                self.assertIsNone(_acquire_lock(path, HASH))
                self.assertEqual(path.read_bytes(), before)

            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                recovered = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
            self.assertEqual(
                recovered["error"]["code"],
                "FINALIZATION_LOCK_RECONCILED",
            )
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertTrue(path.read_bytes().startswith(legacy))
                self.assertEqual(
                    _read_test_lock_marker(path),
                    {"activation_hash": HASH, "status": "RELEASED"},
                )

    def test_explicit_reconcile_is_read_only_until_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_evidence(path, payload):
                if path.name == "activation.redacted.json":
                    raise OSError("simulated evidence write failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_evidence,
            ):
                self._run(_Port(), repo_root=root)

            lock_path = _lock_path(root)
            run_dir = _run_dir(root)
            state_path = run_dir / "resume-state.redacted.json"
            before_lock = lock_path.read_bytes()
            before_state = state_path.read_bytes()
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                mismatched = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(
                        provisioner_bootstrap_binding_sha256="0" * 64
                    ),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
                self.assertEqual(
                    mismatched["error"]["code"],
                    "FINALIZATION_STATE_INVALID",
                )
                self.assertTrue(lock_path.exists())
                inspected = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                )
                self.assertTrue(lock_path.exists())
                self.assertEqual(lock_path.read_bytes(), before_lock)
                self.assertEqual(state_path.read_bytes(), before_state)
                released = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )

            self.assertEqual(
                inspected["error"]["code"],
                "FINALIZATION_RECOVERY_REQUIRED",
            )
            self.assertTrue(inspected["recovery"]["lock_held"])
            self.assertEqual(
                released["error"]["code"], "FINALIZATION_LOCK_RECONCILED"
            )
            self.assertFalse(released["recovery"]["lock_held"])
            self.assertTrue(lock_path.exists())
            self.assertTrue(_legacy_lock_path(root).exists())
            self.assertTrue(_legacy_host_lock_path(root).exists())
            for path in (
                lock_path,
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path)["status"], "RELEASED"
                )
            self.assertTrue(
                (
                    run_dir
                    / "activation.finalization-reconciled.redacted.json"
                ).exists()
            )

    def test_hard_crash_during_write_retains_all_markers_and_blocks_retry(
        self,
    ) -> None:
        class SimulatedCrash(BaseException):
            pass

        class CrashPort(_Port):
            def execute_step(self, step_id, context):
                del step_id, context
                raise SimulatedCrash()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(SimulatedCrash):
                self._run(CrashPort(), repo_root=root)

            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path),
                    {"activation_hash": HASH, "status": "HELD"},
                )

            next_hash = "9" * 64
            blocked = self._run(
                _Port(),
                repo_root=root,
                request=_request(expected_activation_hash=next_hash),
                plans=[
                    _plan(activation_hash=next_hash),
                    _plan(activation_hash=next_hash),
                ],
            )
            self.assertEqual(
                blocked["error"]["code"],
                "LEGACY_HOST_ACTIVATION_LOCK_HELD",
            )
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                recovery = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
            self.assertEqual(
                recovery["error"]["code"], "FINALIZATION_STATE_INVALID"
            )

    def test_partial_release_marker_writes_are_committed_and_recoverable(
        self,
    ) -> None:
        original = __import__(
            "nac_bff.azure_activation_runner",
            fromlist=["_write_lock_marker"],
        )._write_lock_marker
        for fail_at in (1, 2, 3):
            with self.subTest(fail_at=fail_at), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                released_calls = 0

                def fail_selected_release(descriptor, activation_hash, status):
                    nonlocal released_calls
                    if status == "RELEASED":
                        released_calls += 1
                        if released_calls == fail_at:
                            raise OSError("simulated marker release failure")
                    return original(descriptor, activation_hash, status)

                with patch(
                    "nac_bff.azure_activation_runner._write_lock_marker",
                    side_effect=fail_selected_release,
                ):
                    result = self._run(_Port(), repo_root=root)

                self.assertEqual(result["status"], "FAILED_PARTIAL")
                self.assertEqual(
                    result["error"]["code"],
                    "FINALIZATION_LOCK_RELEASE_FAILED",
                )
                run_dir = _run_dir(root)
                self.assertEqual(
                    json.loads(
                        (run_dir / "resume-state.redacted.json").read_text()
                    )["status"],
                    "PASSED",
                )
                self.assertTrue(_receipt_path(root).exists())
                self.assertTrue(
                    (
                        run_dir
                        / "activation.finalization-recovery.redacted.json"
                    ).exists()
                )

                with (
                    patch(
                        "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                        root / ".test-locks",
                    ),
                    patch(
                        "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                        root / ".legacy-test-locks",
                    ),
                ):
                    recovered = reconcile_azure_bff_live_activation_lock(
                        repo_root=root,
                        request=_request(),
                        output_root=root / DEFAULT_OUTPUT_ROOT,
                        confirm_unlock=True,
                    )
                self.assertEqual(
                    recovered["error"]["code"],
                    "FINALIZATION_LOCK_RECONCILED",
                )
                self.assertTrue(
                    recovered["recovery"]["committed_artifacts_valid"]
                )
                for path in (
                    _lock_path(root),
                    _legacy_lock_path(root),
                    _legacy_host_lock_path(root),
                ):
                    self.assertEqual(
                        _read_test_lock_marker(path),
                        {"activation_hash": HASH, "status": "RELEASED"},
                    )

    def test_torn_release_journal_appends_are_recoverable(self) -> None:
        runner = __import__(
            "nac_bff.azure_activation_runner",
            fromlist=["_append_lock_marker_bytes"],
        )
        original_append = runner._append_lock_marker_bytes
        for fail_at in (1, 2, 3):
            with self.subTest(fail_at=fail_at), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                release_calls = 0

                def tear_selected_release(descriptor, raw):
                    nonlocal release_calls
                    if b'"status":"RELEASED"' in raw:
                        release_calls += 1
                        if release_calls == fail_at:
                            written = os.write(descriptor, raw[: len(raw) // 2])
                            self.assertGreater(written, 0)
                            os.fsync(descriptor)
                            raise OSError("simulated torn marker append")
                    return original_append(descriptor, raw)

                with patch(
                    "nac_bff.azure_activation_runner._append_lock_marker_bytes",
                    side_effect=tear_selected_release,
                ):
                    result = self._run(_Port(), repo_root=root)

                self.assertEqual(
                    result["error"]["code"],
                    "FINALIZATION_LOCK_RELEASE_FAILED",
                )
                run_dir = _run_dir(root)
                self.assertEqual(
                    json.loads(
                        (run_dir / "resume-state.redacted.json").read_text()
                    )["status"],
                    "PASSED",
                )
                self.assertTrue(_receipt_path(root).exists())
                self.assertTrue(
                    (
                        run_dir
                        / "activation.finalization-recovery.redacted.json"
                    ).exists()
                )
                torn_path = (
                    _lock_path(root),
                    _legacy_lock_path(root),
                    _legacy_host_lock_path(root),
                )[fail_at - 1]
                self.assertFalse(torn_path.read_bytes().endswith(b"\n"))
                self.assertEqual(
                    _read_test_lock_marker(torn_path),
                    {"activation_hash": HASH, "status": "HELD"},
                )
                with (
                    patch(
                        "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                        root / ".test-locks",
                    ),
                    patch(
                        "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                        root / ".legacy-test-locks",
                    ),
                ):
                    recovered = reconcile_azure_bff_live_activation_lock(
                        repo_root=root,
                        request=_request(),
                        output_root=root / DEFAULT_OUTPUT_ROOT,
                        confirm_unlock=True,
                    )
                self.assertEqual(
                    recovered["error"]["code"],
                    "FINALIZATION_LOCK_RECONCILED",
                )
                for path in (
                    _lock_path(root),
                    _legacy_lock_path(root),
                    _legacy_host_lock_path(root),
                ):
                    self.assertEqual(
                        _read_test_lock_marker(path),
                        {"activation_hash": HASH, "status": "RELEASED"},
                    )

    def test_terminal_failed_partial_torn_release_is_recoverable(
        self,
    ) -> None:
        runner = __import__(
            "nac_bff.azure_activation_runner",
            fromlist=["_append_lock_marker_bytes"],
        )
        original_append = runner._append_lock_marker_bytes
        release_calls = 0

        def tear_second_release(descriptor, raw):
            nonlocal release_calls
            if b'"status":"RELEASED"' in raw:
                release_calls += 1
                if release_calls == 2:
                    written = os.write(descriptor, raw[: len(raw) // 2])
                    self.assertGreater(written, 0)
                    os.fsync(descriptor)
                    raise OSError("simulated terminal release tear")
            return original_append(descriptor, raw)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "nac_bff.azure_activation_runner._append_lock_marker_bytes",
                side_effect=tear_second_release,
            ):
                result = self._run(
                    _Port(fail_at=STEPS[3]), repo_root=root
                )
            self.assertEqual(result["status"], "FAILED_PARTIAL")
            self.assertEqual(
                result["error"]["code"],
                "TERMINAL_LOCK_RELEASE_RECOVERY_REQUIRED",
            )
            recovery_marker_path = (
                _run_dir(root)
                / "activation.finalization-recovery.redacted.json"
            )
            self.assertEqual(
                json.loads(recovery_marker_path.read_text())["status"],
                "TERMINAL_RELEASE_IN_PROGRESS",
            )
            self.assertFalse(
                _legacy_lock_path(root).read_bytes().endswith(b"\n")
            )
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                recovered = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
            self.assertEqual(
                recovered["error"]["code"],
                "FINALIZATION_LOCK_RECONCILED",
            )
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path),
                    {"activation_hash": HASH, "status": "RELEASED"},
                )

    def test_recovery_release_is_retryable_after_torn_append(self) -> None:
        runner = __import__(
            "nac_bff.azure_activation_runner",
            fromlist=["_write_lock_marker", "_append_lock_marker_bytes"],
        )
        original_write = runner._write_lock_marker
        initial_release_calls = 0

        def fail_first_release(descriptor, activation_hash, status):
            nonlocal initial_release_calls
            if status == "RELEASED":
                initial_release_calls += 1
                if initial_release_calls == 1:
                    raise OSError("simulated initial release failure")
            return original_write(descriptor, activation_hash, status)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "nac_bff.azure_activation_runner._write_lock_marker",
                side_effect=fail_first_release,
            ):
                result = self._run(_Port(), repo_root=root)
            self.assertEqual(
                result["error"]["code"],
                "FINALIZATION_LOCK_RELEASE_FAILED",
            )

            original_append = runner._append_lock_marker_bytes
            recovery_release_calls = 0

            def tear_second_recovery_release(descriptor, raw):
                nonlocal recovery_release_calls
                if b'"status":"RELEASED"' in raw:
                    recovery_release_calls += 1
                    if recovery_release_calls == 2:
                        written = os.write(descriptor, raw[: len(raw) // 2])
                        self.assertGreater(written, 0)
                        os.fsync(descriptor)
                        raise OSError("simulated recovery release tear")
                return original_append(descriptor, raw)

            patches = (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            )
            with (
                patches[0],
                patches[1],
                patch(
                    "nac_bff.azure_activation_runner._append_lock_marker_bytes",
                    side_effect=tear_second_recovery_release,
                ),
            ):
                first_recovery = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
            self.assertEqual(
                first_recovery["error"]["code"],
                "FINALIZATION_LOCK_RELEASE_FAILED",
            )
            reconciled_path = (
                _run_dir(root)
                / "activation.finalization-reconciled.redacted.json"
            )
            self.assertTrue(reconciled_path.exists())
            self.assertFalse(
                _legacy_lock_path(root).read_bytes().endswith(b"\n")
            )
            self.assertEqual(
                _read_test_lock_marker(_legacy_lock_path(root)),
                {"activation_hash": HASH, "status": "HELD"},
            )

            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                retried = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
            self.assertEqual(
                retried["error"]["code"],
                "FINALIZATION_LOCK_RECONCILED",
            )
            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path),
                    {"activation_hash": HASH, "status": "RELEASED"},
                )

    def test_hard_finalization_crash_leaves_inspectable_recovery_marker(self) -> None:
        class SimulatedCrash(BaseException):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def crash_during_evidence(path, payload):
                if path.name == "activation.redacted.json":
                    raise SimulatedCrash()
                return _atomic_json_write(path, payload)

            with (
                patch(
                    "nac_bff.azure_activation_runner._atomic_json_write",
                    side_effect=crash_during_evidence,
                ),
                self.assertRaises(SimulatedCrash),
            ):
                self._run(_Port(), repo_root=root)

            marker = json.loads(
                (
                    _run_dir(root)
                    / "activation.finalization-recovery.redacted.json"
                ).read_text()
            )
            self.assertEqual(marker["status"], "FINALIZATION_IN_PROGRESS")
            self.assertTrue(_lock_path(root).exists())
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                inspected = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                )
            self.assertEqual(
                inspected["error"]["code"],
                "FINALIZATION_RECOVERY_REQUIRED",
            )
            self.assertTrue(inspected["recovery"]["lock_held"])

    def test_tampered_recovery_marker_never_releases_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_evidence(path, payload):
                if path.name == "activation.redacted.json":
                    raise OSError("simulated evidence write failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_evidence,
            ):
                self._run(_Port(), repo_root=root)

            marker_path = (
                _run_dir(root)
                / "activation.finalization-recovery.redacted.json"
            )
            marker = json.loads(marker_path.read_text())
            marker["target_binding_sha256"] = "0" * 64
            _atomic_json_write(marker_path, marker)
            with (
                patch(
                    "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                    root / ".test-locks",
                ),
                patch(
                    "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                    root / ".legacy-test-locks",
                ),
            ):
                result = reconcile_azure_bff_live_activation_lock(
                    repo_root=root,
                    request=_request(),
                    output_root=root / DEFAULT_OUTPUT_ROOT,
                    confirm_unlock=True,
                )
            self.assertEqual(
                result["error"]["code"],
                "FINALIZATION_RECOVERY_MARKER_INVALID",
            )
            self.assertTrue(_lock_path(root).exists())


    def test_tampered_event_chain_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(fail_at=STEPS[2]), repo_root=root)
            ledger_dir = _run_dir(root) / "ledger"
            event = sorted(
                ledger_dir.glob("*.redacted.json")
            )[1]
            payload = json.loads(event.read_text())
            payload["status"] = "TAMPERED"
            event.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
            )
            events, error = _validate_event_chain(ledger_dir)

        self.assertEqual(events, [])
        self.assertEqual(error, "LEDGER_CHAIN_INVALID")

    def test_success_receipt_blocks_same_approval_from_second_clone(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            first_repo = host / "clone-a"
            second_repo = host / "clone-b"
            first_repo.mkdir()
            second_repo.mkdir()
            lock_root = host / "host-state"

            first_port = _Port()
            first = self._run(
                first_port, repo_root=first_repo, lock_root=lock_root
            )
            second_port = _Port()
            second = self._run(
                second_port, repo_root=second_repo, lock_root=lock_root
            )

            receipts = list(
                (lock_root / "success-receipts").glob(
                    "*.success.redacted.json"
                )
            )
            self.assertEqual(len(receipts), 1)
            self.assertEqual(oct(receipts[0].stat().st_mode & 0o777), "0o600")

        self.assertEqual(first["status"], "PASSED")
        self.assertEqual(
            second["error"]["code"], "ACTIVATION_ALREADY_COMMITTED"
        )
        self.assertEqual(second_port.prewrite_calls, 0)
        self.assertEqual(second_port.calls, [])

    def test_tampered_host_success_receipt_fails_closed_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            first_repo = host / "clone-a"
            second_repo = host / "clone-b"
            first_repo.mkdir()
            second_repo.mkdir()
            lock_root = host / "host-state"
            self._run(_Port(), repo_root=first_repo, lock_root=lock_root)
            receipt_path = next(
                (lock_root / "success-receipts").glob(
                    "*.success.redacted.json"
                )
            )
            receipt = json.loads(receipt_path.read_text())
            receipt["status"] = "TAMPERED"
            _atomic_json_write(receipt_path, receipt)

            port = _Port()
            result = self._run(
                port, repo_root=second_repo, lock_root=lock_root
            )

        self.assertEqual(result["error"]["code"], "SUCCESS_RECEIPT_INVALID")
        self.assertEqual(port.prewrite_calls, 0)
        self.assertEqual(port.calls, [])

    def test_symlinked_host_success_receipt_fails_closed_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            host = Path(tmp)
            first_repo = host / "clone-a"
            second_repo = host / "clone-b"
            first_repo.mkdir()
            second_repo.mkdir()
            lock_root = host / "host-state"
            self._run(_Port(), repo_root=first_repo, lock_root=lock_root)
            receipt_path = next(
                (lock_root / "success-receipts").glob(
                    "*.success.redacted.json"
                )
            )
            target = host / "attacker-controlled.json"
            target.write_text("{}\n")
            receipt_path.unlink()
            receipt_path.symlink_to(target)

            port = _Port()
            result = self._run(
                port, repo_root=second_repo, lock_root=lock_root
            )

        self.assertEqual(result["error"]["code"], "SUCCESS_RECEIPT_INVALID")
        self.assertEqual(port.prewrite_calls, 0)
        self.assertEqual(port.calls, [])

    def test_final_state_crash_keeps_lock_and_sets_no_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_passed_state(path, payload):
                if (
                    path.name == "resume-state.redacted.json"
                    and payload.get("status") == "PASSED"
                ):
                    raise OSError("simulated final state failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_write",
                side_effect=fail_passed_state,
            ):
                result = self._run(_Port(), repo_root=root)

            run_dir = _run_dir(root)
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            self.assertEqual(result["status"], "FAILED_PARTIAL")
            self.assertEqual(state["status"], "FINALIZATION_FAILED")
            self.assertTrue((run_dir / "activation.redacted.json").exists())
            self.assertTrue(
                (run_dir / "activation.commit.redacted.json").exists()
            )
            self.assertTrue(_lock_path(root).exists())
            self.assertEqual(
                list((root / ".test-locks" / "success-receipts").glob("*")),
                [],
            )

    def test_success_receipt_crash_keeps_lock_and_audit_pass_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail_receipt(path, payload):
                if path.parent.name == "success-receipts":
                    raise OSError("simulated receipt failure")
                return _atomic_json_write(path, payload)

            with patch(
                "nac_bff.azure_activation_runner._atomic_json_create",
                side_effect=fail_receipt,
            ):
                result = self._run(_Port(), repo_root=root)

            run_dir = _run_dir(root)
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            evidence_path = run_dir / "activation.redacted.json"
            loaded = _load_existing_evidence(
                evidence_path,
                _request(),
                receipt_path=(
                    root / ".test-locks" / "success-receipts" / "missing"
                ),
            )
            self.assertEqual(result["status"], "FAILED_PARTIAL")
            self.assertEqual(state["status"], "FINALIZATION_FAILED")
            self.assertEqual(
                loaded["error"]["code"],
                "EVIDENCE_SUCCESS_RECEIPT_INVALID",
            )
            self.assertTrue(_lock_path(root).exists())

    def test_persistent_lock_markers_are_released_after_verified_receipt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self._run(_Port(), repo_root=root)
            run_dir = _run_dir(root)

            self.assertEqual(result["status"], "PASSED")
            self.assertEqual(
                json.loads((run_dir / "resume-state.redacted.json").read_text())[
                    "status"
                ],
                "PASSED",
            )
            self.assertTrue(
                (run_dir / "activation.commit.redacted.json").exists()
            )
            self.assertTrue(_receipt_path(root).exists())
            last_event = json.loads(
                sorted((run_dir / "ledger").glob("*.redacted.json"))[-1]
                .read_text()
            )
            self.assertEqual(last_event["phase"], "LOCK_RELEASE_AUTHORIZED")

            for path in (
                _lock_path(root),
                _legacy_lock_path(root),
                _legacy_host_lock_path(root),
            ):
                self.assertEqual(
                    _read_test_lock_marker(path),
                    {"activation_hash": HASH, "status": "RELEASED"},
                )
                descriptor = os.open(
                    path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
                )
                try:
                    fcntl.flock(
                        descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                finally:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                    os.close(descriptor)

    def test_released_marker_accepts_new_activation_and_held_blocks(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "activation.lock"
            first = _acquire_lock(path, HASH)
            self.assertIsNotNone(first)
            assert first is not None
            _write_lock_marker(first, HASH, "RELEASED")
            fcntl.flock(first, fcntl.LOCK_UN)
            os.close(first)

            next_hash = "9" * 64
            second = _acquire_lock(path, next_hash)
            self.assertIsNotNone(second)
            assert second is not None
            fcntl.flock(second, fcntl.LOCK_UN)
            os.close(second)

            self.assertIsNone(_acquire_lock(path, "8" * 64))
            self.assertEqual(
                _read_test_lock_marker(path),
                {"activation_hash": next_hash, "status": "HELD"},
            )

    def test_passed_evidence_without_receipt_is_never_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(), repo_root=root)
            evidence_path = _run_dir(root) / "activation.redacted.json"
            receipt_path = _receipt_path(root)
            receipt_path.unlink()
            loaded = _load_existing_evidence(
                evidence_path, _request(), receipt_path=receipt_path
            )

        self.assertEqual(
            loaded["error"]["code"], "EVIDENCE_SUCCESS_RECEIPT_INVALID"
        )

    def test_access_probe_fields_are_rejected_outside_step_eleven(self) -> None:
        result = self._run(
            _Port(
                outcome={
                    "status": "PASSED",
                    "classification": "verified",
                    "assigned_access_passed": True,
                }
            )
        )
        self.assertEqual(result["status"], "FAILED_PARTIAL")
        self.assertEqual(
            result["step_results"][0]["stable_error_code"],
            "STEP_RESULT_NOT_REDACTED",
        )

    def test_real_composition_step_eleven_output_is_accepted_and_hashed(self) -> None:
        try:
            from nac_bff.azure_activation_composition import (
                AzureBffLiveExecutionPort,
            )
        except (ImportError, SyntaxError) as exc:
            self.skipTest(f"composition fixture is not importable: {type(exc).__name__}")

        class Synthetic:
            def set_access_mode(self, mode, actor, correlation):
                del mode, actor, correlation

            def restore_assigned(self, actor, correlation):
                del actor, correlation
                return {"verified_count": 1}

        class Readiness:
            def wait_for_status(self, url, expected_status):
                del url, expected_status

        composition = AzureBffLiveExecutionPort.__new__(
            AzureBffLiveExecutionPort
        )
        composition._actor_id = "11111111-1111-4111-8111-111111111111"
        composition._synthetic = Synthetic()
        composition._http_readiness = Readiness()
        composition._request_bff = lambda expected_mode: None

        class CompositionOutputPort(_Port):
            def execute_step(self, step_id, context):
                if step_id == "run_access_and_readback_smokes":
                    self.calls.append(step_id)
                    return composition._run_access_smokes(context)
                return super().execute_step(step_id, context)

        result = self._run(CompositionOutputPort())
        step = next(
            item
            for item in result["step_results"]
            if item["id"] == "run_access_and_readback_smokes"
        )
        signals = {
            "assigned_access_passed": True,
            "deputy_access_passed": True,
            "denied_access_passed": True,
            "tampered_access_passed": True,
            "healthz_before_auth_passed": True,
            "authenticated_read_passed": True,
            "readyz_after_authenticated_read_passed": True,
            "synthetic_state_restored": True,
        }
        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(
            step["response_sha256"],
            _sha256_json(
                {
                    "provider_response_sha256": None,
                    "verified_access_probe_signals": signals,
                }
            ),
        )

    def test_activation_step_error_exposes_only_redacted_code(self) -> None:
        error = ActivationStepError("NAC_SECRET_SENTINEL_620")
        self.assertEqual(error.code, "SENSITIVE_VALUE_REJECTED")
        self.assertEqual(str(error), "SENSITIVE_VALUE_REJECTED")

    def test_unknown_result_and_secret_sentinel_fail_closed(self) -> None:
        sentinel = "NAC_SECRET_SENTINEL_620"
        cases = (
            (
                {
                    "status": "PASSED",
                    "classification": "verified",
                    "raw_stdout": "unallowlisted-provider-output",
                },
                "STEP_RESULT_NOT_REDACTED",
            ),
            (
                {
                    "status": "FAILED",
                    "classification": "not_applicable",
                    "code": sentinel,
                },
                "SENSITIVE_VALUE_REJECTED",
            ),
        )
        for outcome, expected_code in cases:
            with self.subTest(expected_code=expected_code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = self._run(
                    _Port(outcome=outcome), repo_root=root
                )
                all_content = "".join(
                    path.read_text(errors="replace")
                    for path in _run_dir(root).rglob("*")
                    if path.is_file()
                )
                self.assertEqual(result["status"], "FAILED_PARTIAL")
                self.assertEqual(
                    result["step_results"][0]["stable_error_code"],
                    expected_code,
                )
                self.assertNotIn(sentinel, all_content)

    def test_loaded_evidence_requires_exact_summary_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(), repo_root=root)
            evidence_path = _run_dir(root) / "activation.redacted.json"
            evidence = json.loads(evidence_path.read_text())
            summary = evidence["summary"]
            variants = (
                {**summary, "unexpected": 0},
                {
                    key: value
                    for key, value in summary.items()
                    if key != "duplicate_count"
                },
                {**summary, "passed_step_count": True},
            )
            for tampered_summary in variants:
                with self.subTest(summary=tampered_summary):
                    tampered = dict(evidence)
                    tampered["summary"] = tampered_summary
                    _atomic_json_write(evidence_path, tampered)
                    loaded = _load_existing_evidence(
                        evidence_path,
                        _request(),
                        receipt_path=_receipt_path(root),
                    )
                    self.assertEqual(loaded["status"], "OFFLINE_READY")
                    self.assertEqual(
                        loaded["error"]["code"], "EVIDENCE_INVALID"
                    )

    def test_loaded_passed_evidence_must_match_request_bindings(self) -> None:
        changes = (
            ("activation_hash", "0" * 64),
            ("approved_commit_sha", "0" * 40),
            ("approved_tree_sha", "1" * 40),
            ("approval_reference_sha256", "2" * 64),
            ("provisioner_bootstrap_binding_sha256", "3" * 64),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(), repo_root=root)
            evidence_path = _run_dir(root) / "activation.redacted.json"
            evidence = json.loads(evidence_path.read_text())
            for field, value in changes:
                with self.subTest(field=field):
                    tampered = dict(evidence)
                    tampered[field] = value
                    _atomic_json_write(evidence_path, tampered)
                    loaded = _load_existing_evidence(
                        evidence_path,
                        _request(),
                        receipt_path=_receipt_path(root),
                    )
                    self.assertEqual(loaded["status"], "OFFLINE_READY")
                    self.assertEqual(
                        loaded["error"]["code"],
                        "EVIDENCE_BINDING_MISMATCH",
                    )

    def test_secure_canonical_json_rejects_path_swap_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "state.redacted.json"
            replacement = root / "replacement.redacted.json"
            backup = root / "original.redacted.json"
            _atomic_json_write(path, {"status": "ORIGINAL"})
            _atomic_json_write(replacement, {"status": "REPLACEMENT"})
            original_open = os.open
            swapped = False

            def swap_before_open(target, flags, *args, **kwargs):
                nonlocal swapped
                if Path(target) == path and not swapped:
                    swapped = True
                    path.rename(backup)
                    replacement.rename(path)
                return original_open(target, flags, *args, **kwargs)

            with patch(
                "nac_bff.azure_activation_runner.os.open",
                side_effect=swap_before_open,
            ):
                loaded = _read_secure_canonical_json(path)

            self.assertTrue(swapped)
            self.assertIsNone(loaded)

    def test_symlinked_ledger_event_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(fail_at=STEPS[1]), repo_root=root)
            ledger_dir = _run_dir(root) / "ledger"
            event_path = sorted(ledger_dir.glob("*.redacted.json"))[0]
            target = event_path.with_suffix(".target")
            event_path.rename(target)
            event_path.symlink_to(target)

            events, error = _validate_event_chain(ledger_dir)

            self.assertEqual(events, [])
            self.assertEqual(error, "LEDGER_CHAIN_INVALID")

    def test_state_head_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(fail_at=STEPS[1]), repo_root=root)
            run_dir = _run_dir(root)
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            events, error = _validate_event_chain(run_dir / "ledger")
            self.assertIsNone(error)
            self.assertTrue(_state_matches_chain(state, events))
            state["ledger_head_sha256"] = "0" * 64
            self.assertFalse(_state_matches_chain(state, events))

    def test_removing_any_terminal_state_step_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._run(_Port(fail_at=STEPS[2]), repo_root=root)
            run_dir = _run_dir(root)
            state = json.loads(
                (run_dir / "resume-state.redacted.json").read_text()
            )
            events, error = _validate_event_chain(run_dir / "ledger")
            self.assertIsNone(error)
            terminal_indices = [
                index
                for index, step in enumerate(state["steps"])
                if step["status"] in {"PASSED", "FAILED"}
            ]
            self.assertTrue(_state_matches_chain(state, events))
            for index in terminal_indices:
                without_step = dict(state)
                without_step["steps"] = (
                    state["steps"][:index]
                    + state["steps"][index + 1:]
                )
                self.assertFalse(
                    _state_matches_chain(without_step, events)
                )


if __name__ == "__main__":
    unittest.main()
