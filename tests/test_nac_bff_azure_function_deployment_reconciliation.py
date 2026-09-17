from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nac_bff.activation_security_backend import get_platform_security_backend

from nac_bff.azure_activation_runner import (
    ActivationStepError,
    DEFAULT_OUTPUT_ROOT,
    LiveActivationRequest,
    _atomic_json_write,
    _binding_sha256_json,
    _read_lock_marker_descriptor,
    _sha256_json,
    run_azure_bff_live_activation,
)
from nac_bff.azure_function_deployment_reconciliation import (
    ACTION,
    FunctionDeploymentReconcilerBinding,
    FunctionDeploymentReleaseApproval,
    inspect_azure_bff_function_deployment_failure,
    release_azure_bff_function_deployment_quarantine,
)


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "d" * 40
BODY_HASH = "e" * 64
PERMISSION_HASH = "f" * 64
APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/632#issuecomment-123456789"
)
RELEASE_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/739#issuecomment-987654321"
)
STEPS = (
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
)


def _request() -> LiveActivationRequest:
    return LiveActivationRequest(
        expected_activation_hash=ACTIVATION_HASH,
        approved_commit=COMMIT,
        approved_tree=TREE,
        owner_approval_reference=APPROVAL_REFERENCE,
        approval_body_sha256=BODY_HASH,
        azure_cli_toolchain_sha256="1" * 64,
        m365_cli_sha256="2" * 64,
        m365_node_sha256="3" * 64,
        build_python_sha256="8" * 64,
        build_node_sha256="4" * 64,
        build_npm_cli_sha256="5" * 64,
        gh_cli_sha256="6" * 64,
        provisioner_certificate_sha256="7" * 64,
        provisioner_bootstrap_binding_sha256="9" * 64,
        reason="Activate the synthetic MVP BFF",
        correlation_id="nac-bff-live-20260911",
        owner_approved=True,
        execute_live_activation=True,
        resume=False,
    )


def _plan() -> dict:
    return {
        "status": "READY",
        "activation_hash": ACTIVATION_HASH,
        "source_control": {"commit": COMMIT},
        "bindings": {"workspace_id": "notary_team_01"},
        "steps": [{"id": step} for step in STEPS],
    }


class _FailAtFunctionPort:
    def verify_prewrite(self, context, request):
        del context, request
        return {
            "status": "PASSED",
            "code": "PREWRITE_VERIFIED",
            "prebuilt_inputs_verified": True,
        }

    def execute_step(self, step_id, context):
        del context
        if step_id == "deploy_function_package":
            raise ActivationStepError(
                "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS"
            )
        return {
            "status": "PASSED",
            "classification": "verified",
            "verified_count": 1,
            "reference_sha256": "c" * 64,
            **(
                {"prebuilt_inputs_verified": True}
                if step_id == "ensure_entra_api_application"
                else {}
            ),
        }


class _ObservationPort:
    def __init__(self, *, drift: bool = False, applied: bool = False) -> None:
        self.calls: list[dict[str, str]] = []
        self.drift = drift
        self.applied = applied

    def observe_function_deployment(self, **bindings):
        self.calls.append(dict(bindings))
        started = datetime.fromisoformat(
            bindings["step_started_at_utc"].replace("Z", "+00:00")
        )
        site_time = started + (
            timedelta(seconds=1) if self.applied else -timedelta(seconds=1)
        )
        count = 1 if self.drift and len(self.calls) > 1 else 0
        return {
            "tenant_id": bindings["tenant_id"],
            "subscription_id": bindings["subscription_id"],
            "resource_group": bindings["resource_group"],
            "function_app": bindings["function_app"],
            "classification": "FUNCTION_DEPLOYMENT_NOT_APPLIED",
            "step_started_at_utc": bindings["step_started_at_utc"],
            "site": {
                "state": "Running",
                "last_modified_at_utc": site_time.isoformat().replace(
                    "+00:00", "Z"
                ),
            },
            "arm_deployments": {
                "count": count,
                "latest_started_at_utc": None,
                "started_at_or_after_step_count": 0,
            },
            "deployment_status_count": 0,
            "one_deploy": "ABSENT",
        }


class _OwnerVerifier:
    def __init__(self, *, owner: str = "approved-owner") -> None:
        self.owner = owner

    def verify_owner_comment(
        self, *, reference, expected_body, expected_body_sha256
    ):
        return {
            "status": "VERIFIED",
            "owner_login": self.owner,
            "immutable": True,
            "reference": reference,
            "body": expected_body,
            "body_sha256": expected_body_sha256,
        }


class FunctionDeploymentReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.lock_root = self.root / ".test-locks"
        self.legacy_lock_root = self.root / ".legacy-test-locks"
        self.binding = FunctionDeploymentReconcilerBinding(
            approved_commit="1" * 40,
            approved_tree="2" * 40,
            toolchain_sha256="3" * 64,
            required_owner_login="approved-owner",
        )
        with self._patches():
            result = run_azure_bff_live_activation(
                repo_root=self.root,
                request=_request(),
                execution_port=_FailAtFunctionPort(),
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
                now=lambda: datetime(
                    2026, 9, 8, 13, 9, 48, tzinfo=timezone.utc
                ),
            )
        self.assertEqual(result["status"], "FAILED_PARTIAL")
        self._write_prepared_inputs()

    def _patches(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        for active in (
            patch(
                "nac_bff.azure_activation_runner.build_azure_bff_activation_plan",
                side_effect=[_plan(), _plan()],
            ),
            patch(
                "nac_bff.azure_activation_runner._permission_boundary_hash",
                return_value=PERMISSION_HASH,
            ),
            patch("nac_bff.azure_activation_runner._clean_tree", return_value=True),
            patch("nac_bff.azure_activation_runner._head_commit", return_value=COMMIT),
            patch("nac_bff.azure_activation_runner._head_tree", return_value=TREE),
            patch("nac_bff.azure_activation_runner._HOST_LOCK_ROOT", self.lock_root),
            patch(
                "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                self.legacy_lock_root,
            ),
        ):
            stack.enter_context(active)
        return stack.pop_all()

    def _runtime_patches(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(
            patch("nac_bff.azure_activation_runner._HOST_LOCK_ROOT", self.lock_root)
        )
        stack.enter_context(
            patch(
                "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                self.legacy_lock_root,
            )
        )
        return stack.pop_all()

    @property
    def run_dir(self) -> Path:
        return self.root / DEFAULT_OUTPUT_ROOT / ACTIVATION_HASH

    def _write_prepared_inputs(self) -> None:
        prepared = self.run_dir / "prepared"
        prepared.mkdir(mode=0o700, exist_ok=True)
        package = b"synthetic-function-package"
        package_path = prepared / "nac-bff-function.zip"
        package_path.write_bytes(package)
        package_path.chmod(0o600)
        manifest = {
            "schema_version": "nac.m365-azure-bff-prepared-inputs/v1",
            "activation_hash": ACTIVATION_HASH,
            "approved_commit_sha": COMMIT,
            "approved_tree_sha": TREE,
            "approved_tree_snapshot_sha256": "1" * 64,
            "bicep_parameters_snapshot_sha256": "2" * 64,
            "bicep_snapshot_sha256": "3" * 64,
            "function_package_sha256": hashlib.sha256(package).hexdigest(),
            "prepared_inputs_sha256": "4" * 64,
            "spfx_package_sha256": "5" * 64,
        }
        _atomic_json_write(prepared / "prepared-inputs.redacted.json", manifest)

    def _lock_paths(self) -> tuple[Path, Path, Path]:
        target = _binding_sha256_json({"workspace_id": "notary_team_01"})
        legacy = _sha256_json({"workspace_id": "notary_team_01"})
        return (
            self.lock_root / f"{target}.lock",
            self.lock_root / f"{legacy}.lock",
            self.legacy_lock_root / f"{legacy}.lock",
        )

    @staticmethod
    def _lock_marker(path: Path) -> dict | None:
        session = None
        if os.name == "nt":
            session = get_platform_security_backend().open_secure_directory(
                path.parent,
                create=False,
            )
            descriptor = session.open_regular_descriptor(path.name, create=False)
        else:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            return _read_lock_marker_descriptor(descriptor)
        finally:
            os.close(descriptor)
            if session is not None:
                session.close()

    def _inspect(self, port: _ObservationPort | None = None) -> dict:
        with self._runtime_patches():
            return inspect_azure_bff_function_deployment_failure(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=port or _ObservationPort(),
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

    def _approval(self, inspection: dict, **overrides):
        bindings = inspection["approval_bindings"]
        values = {
            "owner_approved": True,
            "owner_approval_reference": RELEASE_REFERENCE,
            "approval_body_sha256": inspection["owner_comment"]["body_sha256"],
            **bindings,
        }
        values.update(overrides)
        return FunctionDeploymentReleaseApproval(**values)

    def _release(
        self,
        inspection: dict,
        *,
        port: _ObservationPort | None = None,
        approval: FunctionDeploymentReleaseApproval | None = None,
        owner: str = "approved-owner",
        fault_injector=None,
    ) -> dict:
        with self._runtime_patches():
            return release_azure_bff_function_deployment_quarantine(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=port or _ObservationPort(),
                owner_comment_verifier=_OwnerVerifier(owner=owner),
                approval=approval or self._approval(inspection),
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
                fault_injector=fault_injector,
            )

    def test_inspection_is_local_read_only_and_double_reads(self) -> None:
        tracked = (
            self.run_dir / "resume-state.redacted.json",
            self.run_dir / "activation.redacted.json",
            self.run_dir / "prepared" / "prepared-inputs.redacted.json",
            self.run_dir / "prepared" / "nac-bff-function.zip",
            *self._lock_paths(),
        )
        before = {path: path.read_bytes() for path in tracked}
        port = _ObservationPort()

        result = self._inspect(port)

        self.assertEqual(
            result["status"], "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED"
        )
        self.assertEqual(len(port.calls), 2)
        self.assertEqual(before, {path: path.read_bytes() for path in tracked})
        self.assertEqual(
            result["provider_observation"]["classification"],
            "FUNCTION_DEPLOYMENT_NOT_APPLIED",
        )
        self.assertEqual(
            hashlib.sha256(
                result["owner_comment"]["body"].encode("utf-8")
            ).hexdigest(),
            result["owner_comment"]["body_sha256"],
        )

    def test_drift_or_applied_signal_keeps_every_lock_held(self) -> None:
        for port in (_ObservationPort(drift=True), _ObservationPort(applied=True)):
            with self.subTest(port=vars(port)):
                result = self._inspect(port)
                self.assertEqual(result["status"], "BLOCKED")
                for path in self._lock_paths():
                    self.assertEqual(
                        self._lock_marker(path),
                        {"activation_hash": ACTIVATION_HASH, "status": "HELD"},
                    )

    def test_exact_approval_releases_locks_without_changing_failed_run(self) -> None:
        inspection = self._inspect()
        state_path = self.run_dir / "resume-state.redacted.json"
        evidence_path = self.run_dir / "activation.redacted.json"
        state_before = state_path.read_bytes()
        evidence_before = evidence_path.read_bytes()

        result = self._release(inspection)

        self.assertEqual(
            result["status"], "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED"
        )
        self.assertEqual(state_path.read_bytes(), state_before)
        self.assertEqual(evidence_path.read_bytes(), evidence_before)
        for path in self._lock_paths():
            self.assertEqual(
                self._lock_marker(path),
                {"activation_hash": ACTIVATION_HASH, "status": "RELEASED"},
            )

    def test_wrong_owner_or_hash_never_releases_a_lock(self) -> None:
        inspection = self._inspect()
        wrong_hash = self._approval(
            inspection, provider_observation_sha256="0" * 64
        )
        for approval, owner in (
            (wrong_hash, "approved-owner"),
            (self._approval(inspection), "different-owner"),
        ):
            with self.subTest(owner=owner):
                result = self._release(
                    inspection, approval=approval, owner=owner
                )
                self.assertEqual(result["status"], "BLOCKED")
                for path in self._lock_paths():
                    self.assertEqual(
                        self._lock_marker(path),
                        {"activation_hash": ACTIVATION_HASH, "status": "HELD"},
                    )

    def test_crash_after_lock_append_is_recovered_idempotently(self) -> None:
        inspection = self._inspect()

        def fail_after_target(point: str) -> None:
            if point == "lock:target":
                raise RuntimeError("simulated crash")

        first = self._release(inspection, fault_injector=fail_after_target)
        self.assertEqual(first["status"], "BLOCKED")
        self.assertEqual(
            self._lock_marker(self._lock_paths()[0])["status"], "RELEASED"
        )

        second = self._release(inspection)

        self.assertEqual(
            second["status"], "FUNCTION_DEPLOYMENT_QUARANTINE_RELEASED"
        )
        for path in self._lock_paths():
            self.assertEqual(self._lock_marker(path)["status"], "RELEASED")


if __name__ == "__main__":
    unittest.main()
