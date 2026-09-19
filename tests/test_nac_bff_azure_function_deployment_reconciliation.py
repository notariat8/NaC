from __future__ import annotations

from contextlib import ExitStack
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import io
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
    PROVENANCE_LOSS_ACTION,
    PROVENANCE_LOSS_ARTIFACT_CATEGORIES,
    PROVENANCE_LOSS_COUNTER_KEYS,
    PROVENANCE_LOSS_RUN_ID,
    FunctionDeploymentProvenanceLossConfirmation,
    FunctionDeploymentReconcilerBinding,
    FunctionDeploymentReleaseApproval,
    classify_function_deployment_provenance_loss,
    inspect_azure_bff_function_deployment_failure,
    load_function_deployment_provenance_loss_confirmation,
    release_azure_bff_function_deployment_quarantine,
)


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "d" * 40
BODY_HASH = "e" * 64
PERMISSION_HASH = "f" * 64
OWNER_PRINCIPAL_SHA256 = "9" * 64
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
    def __init__(
        self,
        *,
        owner: str = "approved-owner",
        principal_sha256: str = OWNER_PRINCIPAL_SHA256,
    ) -> None:
        self.owner = owner
        self.principal_sha256 = principal_sha256

    def verify_owner_comment(
        self, *, reference, expected_body, expected_body_sha256
    ):
        return {
            "status": "VERIFIED",
            "owner_login": self.owner,
            "owner_principal_id_sha256": self.principal_sha256,
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
            required_owner_principal_id_sha256=OWNER_PRINCIPAL_SHA256,
        )
        if "provenance_loss" in self._testMethodName:
            return
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

    def _loss_confirmation(self, **overrides):
        values = {
            "owner_confirmed": True,
            "issue": 739,
            "action": PROVENANCE_LOSS_ACTION,
            "run_id": PROVENANCE_LOSS_RUN_ID,
            "activation_hash": ACTIVATION_HASH,
            "correlation_id": PROVENANCE_LOSS_RUN_ID,
            "canonical_run_relative_path": (
                f"out/m365/teams-sharepoint/bff-live-activation/{ACTIVATION_HASH}"
            ),
            "expected_artifact_categories": PROVENANCE_LOSS_ARTIFACT_CATEGORIES,
            "operator_account_id_sha256": "4" * 64,
            "operator_principal_id_sha256": "5" * 64,
            "identity_resolver_sha256": "6" * 64,
            "target_lock_binding_sha256": _binding_sha256_json(
                {"workspace_id": "notary_team_01"}
            ),
            "legacy_lock_binding_sha256": _sha256_json(
                {"workspace_id": "notary_team_01"}
            ),
            "reconciler_commit": self.binding.approved_commit,
            "reconciler_tree": self.binding.approved_tree,
            "reconciler_toolchain_sha256": self.binding.toolchain_sha256,
        }
        values.update(overrides)
        return FunctionDeploymentProvenanceLossConfirmation(**values)

    def _classify_loss(self, confirmation=None, request=None) -> dict:
        with self._runtime_patches():
            return classify_function_deployment_provenance_loss(
                repo_root=self.root,
                request=request
                or replace(_request(), correlation_id=PROVENANCE_LOSS_RUN_ID),
                confirmation=confirmation or self._loss_confirmation(),
                resolved_operator_account_id_sha256="4" * 64,
                resolved_operator_principal_id_sha256="5" * 64,
                resolved_identity_resolver_sha256="6" * 64,
                reconciler_commit=self.binding.approved_commit,
                reconciler_tree=self.binding.approved_tree,
                reconciler_toolchain_sha256=self.binding.toolchain_sha256,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

    def test_total_provenance_loss_is_terminal_and_has_closed_zero_counters(
        self,
    ) -> None:
        for path in self._lock_paths():
            if path.exists():
                path.unlink()

        with patch(
            "nac_bff.azure_activation_runner.build_azure_bff_activation_plan",
            side_effect=AssertionError("activation plan must not be built"),
        ), patch(
            "nac_bff.azure_activation._build_function_package_bytes",
            side_effect=AssertionError("function package must not be built"),
        ), patch(
            "subprocess.run",
            side_effect=AssertionError("subprocess must not be started"),
        ), patch.object(
            Path,
            "write_bytes",
            side_effect=AssertionError("file must not be written"),
        ), patch.object(
            Path,
            "write_text",
            side_effect=AssertionError("text file must not be written"),
        ), patch.object(
            Path,
            "open",
            side_effect=AssertionError("path handle must not be opened"),
        ), patch(
            "builtins.open",
            side_effect=AssertionError("file handle must not be opened"),
        ), patch(
            "os.open",
            side_effect=AssertionError("descriptor must not be opened"),
        ):
            result = self._classify_loss()

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(
            result["reason_code"], "FUNCTION_DEPLOYMENT_PROVENANCE_LOST"
        )
        self.assertEqual(
            result["error"]["code"], "FUNCTION_DEPLOYMENT_PROVENANCE_LOST"
        )
        self.assertIs(result["terminal"], True)
        self.assertIs(result["retry_allowed"], False)
        self.assertIsNone(result["next_phase"])
        self.assertEqual(
            set(result["operation_counts"]), set(PROVENANCE_LOSS_COUNTER_KEYS)
        )
        self.assertTrue(
            all(value == 0 for value in result["operation_counts"].values())
        )
        self.assertIs(result["writes_started"], False)

    def test_provenance_loss_rejects_wrong_binding_or_partial_inventory(
        self,
    ) -> None:
        cases = (
            self._loss_confirmation(owner_confirmed=False),
            self._loss_confirmation(issue=740),
            self._loss_confirmation(action="WRONG_ACTION"),
            self._loss_confirmation(activation_hash="0" * 64),
            self._loss_confirmation(correlation_id="other-run"),
            self._loss_confirmation(run_id="other-run"),
            self._loss_confirmation(canonical_run_relative_path="wrong/path"),
            self._loss_confirmation(
                expected_artifact_categories=PROVENANCE_LOSS_ARTIFACT_CATEGORIES[:-1]
            ),
            self._loss_confirmation(operator_account_id_sha256="0" * 64),
            self._loss_confirmation(operator_principal_id_sha256="0" * 64),
            self._loss_confirmation(identity_resolver_sha256="0" * 64),
            self._loss_confirmation(target_lock_binding_sha256="0" * 63),
            self._loss_confirmation(reconciler_commit="0" * 40),
            self._loss_confirmation(reconciler_tree="0" * 40),
            self._loss_confirmation(reconciler_toolchain_sha256="0" * 64),
            self._loss_confirmation(terminal_status="READY"),
            self._loss_confirmation(terminal_reason_code="WRONG"),
            self._loss_confirmation(terminal=False),
            self._loss_confirmation(retry_allowed=True),
            self._loss_confirmation(next_phase="issue739"),
        )
        for confirmation in cases:
            with self.subTest(confirmation=confirmation):
                result = self._classify_loss(confirmation=confirmation)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertNotEqual(
                    result["error"]["code"],
                    "FUNCTION_DEPLOYMENT_PROVENANCE_LOST",
                )

        self.run_dir.mkdir(parents=True)
        result = self._classify_loss()
        self.assertEqual(
            result["error"]["code"],
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_INVALID",
        )
        self.run_dir.rmdir()
        for lock_path in self._lock_paths():
            with self.subTest(lock_path=lock_path):
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                lock_path.write_bytes(b"original issue-739 lock evidence")
                result = self._classify_loss()
                self.assertEqual(
                    result["error"]["code"],
                    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_INVALID",
                )
                lock_path.unlink()

        with patch(
            "nac_bff.azure_function_deployment_reconciliation._path_entry_exists",
            side_effect=OSError("synthetic inaccessible path"),
        ):
            result = self._classify_loss()
        self.assertEqual(
            result["error"]["code"],
            "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_UNINSPECTABLE",
        )

    def test_provenance_loss_confirmation_loader_binds_hash_and_shape(
        self,
    ) -> None:
        confirmation = self._loss_confirmation()
        payload = {
            "schema_version": (
                "nac.issue739-function-deployment-provenance-loss-confirmation/v1"
            ),
            **{
                field: getattr(confirmation, field)
                for field in confirmation.__dataclass_fields__
            },
        }
        payload["expected_artifact_categories"] = list(
            payload["expected_artifact_categories"]
        )
        raw = json.dumps(
            payload, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")

        class Backend:
            def __init__(
                self,
                data: bytes,
                *,
                reported_size: int | None = None,
                inspect_error: Exception | None = None,
                open_error: Exception | None = None,
            ) -> None:
                self.data = data
                self.reported_size = (
                    len(data) if reported_size is None else reported_size
                )
                self.inspect_error = inspect_error
                self.open_error = open_error

            def inspect_private_path(self, path, purpose):
                del path, purpose
                if self.inspect_error is not None:
                    raise self.inspect_error
                return type("Binding", (), {"size": self.reported_size})()

            def open_bound_read(self, path, binding):
                del path, binding
                if self.open_error is not None:
                    raise self.open_error
                return io.BytesIO(self.data)

        confirmation_path = self.root.parent / "protected-loss-confirmation.json"

        def load(data: bytes, *, backend=None, expected_sha256=None):
            selected_backend = backend or Backend(data)
            selected_hash = expected_sha256 or hashlib.sha256(data).hexdigest()
            with patch(
                "nac_bff.activation_security_backend.get_platform_security_backend",
                return_value=selected_backend,
            ):
                return load_function_deployment_provenance_loss_confirmation(
                    repo_root=self.root,
                    path=confirmation_path,
                    expected_sha256=selected_hash,
                )

        loaded = load(raw)
        self.assertEqual(loaded, confirmation)

        with self.assertRaises(ValueError):
            load(raw, expected_sha256="0" * 64)

        invalid_payloads = {
            "duplicate_json_key": (
                b'{"schema_version":"first","schema_version":"second"}'
            ),
            "invalid_utf8": b"\xff",
            "invalid_json": b"{",
        }
        missing_field = dict(payload)
        missing_field.pop("issue")
        invalid_payloads["missing_field"] = json.dumps(missing_field).encode("utf-8")
        extra_field = dict(payload)
        extra_field["unexpected"] = True
        invalid_payloads["extra_field"] = json.dumps(extra_field).encode("utf-8")
        wrong_schema = dict(payload)
        wrong_schema["schema_version"] = "wrong-schema/v1"
        invalid_payloads["wrong_schema"] = json.dumps(wrong_schema).encode("utf-8")
        categories_not_list = dict(payload)
        categories_not_list["expected_artifact_categories"] = "resume_state"
        invalid_payloads["categories_not_list"] = json.dumps(
            categories_not_list
        ).encode("utf-8")
        categories_non_string = dict(payload)
        categories_non_string["expected_artifact_categories"] = ["resume_state", 1]
        invalid_payloads["categories_non_string"] = json.dumps(
            categories_non_string
        ).encode("utf-8")
        for case_id, invalid_raw in invalid_payloads.items():
            with self.subTest(case_id=case_id), self.assertRaises(ValueError):
                load(invalid_raw)

        backend_failures = {
            "oversized_binding": Backend(raw, reported_size=131073),
            "oversized_read": Backend(b"x" * 131073, reported_size=131072),
            "inspect_error": Backend(raw, inspect_error=OSError("inspect failed")),
            "open_error": Backend(raw, open_error=OSError("open failed")),
        }
        for case_id, backend in backend_failures.items():
            with self.subTest(case_id=case_id), self.assertRaises(ValueError):
                load(backend.data, backend=backend)

        for invalid_path in (
            Path("relative-confirmation.json"),
            self.root / "inside-repository.json",
        ):
            with self.subTest(invalid_path=invalid_path), self.assertRaises(ValueError):
                load_function_deployment_provenance_loss_confirmation(
                    repo_root=self.root,
                    path=invalid_path,
                    expected_sha256=hashlib.sha256(raw).hexdigest(),
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
        principal_sha256: str = OWNER_PRINCIPAL_SHA256,
        fault_injector=None,
    ) -> dict:
        with self._runtime_patches():
            return release_azure_bff_function_deployment_quarantine(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=port or _ObservationPort(),
                owner_comment_verifier=_OwnerVerifier(
                    owner=owner, principal_sha256=principal_sha256
                ),
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
        for approval, owner, principal_sha256 in (
            (wrong_hash, "approved-owner", OWNER_PRINCIPAL_SHA256),
            (self._approval(inspection), "different-owner", "0" * 64),
        ):
            with self.subTest(owner=owner):
                result = self._release(
                    inspection,
                    approval=approval,
                    owner=owner,
                    principal_sha256=principal_sha256,
                )
                self.assertEqual(result["status"], "BLOCKED")
                for path in self._lock_paths():
                    self.assertEqual(
                        self._lock_marker(path),
                        {"activation_hash": ACTIVATION_HASH, "status": "HELD"},
                    )

    def test_different_owner_login_with_same_principal_never_releases_a_lock(self) -> None:
        inspection = self._inspect()
        result = self._release(
            inspection,
            approval=self._approval(inspection),
            owner="different-owner",
            principal_sha256=OWNER_PRINCIPAL_SHA256,
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
