from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from nac_bff.azure_activation_runner import (
    DEFAULT_OUTPUT_ROOT,
    LiveActivationRequest,
    _binding_sha256_json,
    _read_lock_marker_descriptor,
    _sha256_json,
    run_azure_bff_live_activation,
)
from nac_bff.azure_interruption_reconciliation import (
    InterruptionReconcilerBinding,
    InterruptionTerminalizationApproval,
    inspect_azure_bff_step2_interruption,
    terminalize_azure_bff_step2_interruption,
)


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "d" * 40
BODY_HASH = "e" * 64
PERMISSION_HASH = "f" * 64
SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/632#issuecomment-123456789"
)
RECONCILIATION_APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/717#issuecomment-987654321"
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
        correlation_id="nac-bff-live-20260730",
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


def _observation() -> dict:
    return {
        "tenant_id": TENANT_ID,
        "subscription_id": SUBSCRIPTION_ID,
        "providers": {
            "Microsoft.OperationalInsights": "Registered",
            "Microsoft.Storage": "Registered",
            "Microsoft.Web": "Registered",
        },
        "resource_groups": [
            {
                "id": (
                    f"/subscriptions/{SUBSCRIPTION_ID}"
                    "/resourceGroups/rg-nac-bff-test"
                ),
                "name": "rg-nac-bff-test",
                "location": "germanywestcentral",
                "provisioning_state": "Succeeded",
                "tags": {
                    "dataClassification": "no-production-data",
                    "environment": "test",
                    "workload": "nac-bff",
                },
            }
        ],
        "resource_inventory": [],
    }


class _Interrupted(BaseException):
    pass


class _CrashPort:
    def verify_prewrite(self, context, request):
        del context, request
        return {
            "status": "PASSED",
            "code": "PREWRITE_VERIFIED",
            "prebuilt_inputs_verified": True,
        }

    def execute_step(self, step_id, context):
        del context
        if step_id == "ensure_resource_group":
            raise _Interrupted()
        return {
            "status": "PASSED",
            "classification": "verified",
            "verified_count": 1,
            "reference_sha256": "c" * 64,
        }


class _ObservationPort:
    def __init__(self, observations: list[dict] | None = None) -> None:
        self.observations = list(observations or [_observation(), _observation()])
        self.calls: list[dict[str, str]] = []

    def observe_ensure_resource_group(self, **bindings):
        self.calls.append(dict(bindings))
        return self.observations.pop(0)


class _OwnerCommentVerifier:
    def __init__(
        self,
        *,
        status: str = "VERIFIED",
        owner: str = "approved-owner",
        immutable: bool = True,
        body_suffix: str = "",
    ) -> None:
        self.status = status
        self.owner = owner
        self.immutable = immutable
        self.body_suffix = body_suffix
        self.calls: list[dict[str, str]] = []

    def verify_owner_comment(self, *, reference, expected_body, expected_body_sha256):
        self.calls.append({
            "reference": reference,
            "expected_body": expected_body,
            "expected_body_sha256": expected_body_sha256,
        })
        body = expected_body + self.body_suffix
        return {
            "status": self.status,
            "owner_login": self.owner,
            "immutable": self.immutable,
            "reference": reference,
            "body": body,
            "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }


class AzureBffInterruptionReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.lock_root = self.root / ".test-locks"
        self.legacy_host_lock_root = self.root / ".legacy-test-locks"
        self.binding = InterruptionReconcilerBinding(
            approved_commit="1" * 40,
            approved_tree="2" * 40,
            toolchain_sha256="3" * 64,
            required_owner_login="approved-owner",
        )
        with self._runner_patches():
            with self.assertRaises(_Interrupted):
                run_azure_bff_live_activation(
                    repo_root=self.root,
                    request=_request(),
                    execution_port=_CrashPort(),
                    output_root=self.root / DEFAULT_OUTPUT_ROOT,
                    now=lambda: datetime(
                        2026, 7, 30, 12, 0, tzinfo=timezone.utc
                    ),
                )

    def _runner_patches(self):
        return _Patches(
            patch(
                "nac_bff.azure_activation_runner.build_azure_bff_activation_plan",
                side_effect=[_plan(), _plan()],
            ),
            patch(
                "nac_bff.azure_activation_runner._permission_boundary_hash",
                return_value=PERMISSION_HASH,
            ),
            patch(
                "nac_bff.azure_activation_runner._clean_tree",
                return_value=True,
            ),
            patch(
                "nac_bff.azure_activation_runner._head_commit",
                return_value=COMMIT,
            ),
            patch(
                "nac_bff.azure_activation_runner._head_tree",
                return_value=TREE,
            ),
            patch(
                "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                self.lock_root,
            ),
            patch(
                "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                self.legacy_host_lock_root,
            ),
        )

    def _reconciliation_patches(self):
        return _Patches(
            patch(
                "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                self.lock_root,
            ),
            patch(
                "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
                self.legacy_host_lock_root,
            ),
        )

    def _lock_paths(self) -> tuple[Path, Path, Path]:
        target = _binding_sha256_json({"workspace_id": "notary_team_01"})
        legacy = _sha256_json({"workspace_id": "notary_team_01"})
        return (
            self.lock_root / f"{target}.lock",
            self.lock_root / f"{legacy}.lock",
            self.legacy_host_lock_root / f"{legacy}.lock",
        )

    @staticmethod
    def _marker(path: Path) -> dict:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            marker = _read_lock_marker_descriptor(descriptor)
        finally:
            os.close(descriptor)
        assert marker is not None
        return marker

    def _inspect(self, port: _ObservationPort | None = None) -> dict:
        with self._reconciliation_patches():
            return inspect_azure_bff_step2_interruption(
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
            "action": "TERMINALIZE_AND_RELEASE_LOCK_ONLY",
            "owner_approval_reference": RECONCILIATION_APPROVAL_REFERENCE,
            "approval_body_sha256": inspection["owner_comment"]["body_sha256"],
            "activation_hash": bindings["activation_hash"],
            "state_sha256": bindings["state_sha256"],
            "ledger_head_sha256": bindings["ledger_head_sha256"],
            "target_lock_sha256": bindings["target_lock_sha256"],
            "legacy_lock_sha256": bindings["legacy_lock_sha256"],
            "legacy_host_lock_sha256": bindings[
                "legacy_host_lock_sha256"
            ],
            "provider_observation_sha256": bindings[
                "provider_observation_sha256"
            ],
            "interrupted_step": bindings["interrupted_step"],
            "reconciler_commit": bindings["reconciler_commit"],
            "reconciler_tree": bindings["reconciler_tree"],
            "reconciler_toolchain_sha256": bindings[
                "reconciler_toolchain_sha256"
            ],
            "required_owner_login": bindings["required_owner_login"],
        }
        values.update(overrides)
        return InterruptionTerminalizationApproval(**values)

    def test_inspection_is_byte_for_byte_local_read_only_and_double_reads(self):
        tracked = [
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "resume-state.redacted.json",
            *self._lock_paths(),
        ]
        before = {path: path.read_bytes() for path in tracked}
        port = _ObservationPort()

        inspection = self._inspect(port)

        self.assertEqual(inspection["status"], "MIDRUN_RECONCILIATION_REQUIRED")
        self.assertEqual(inspection["running_step"], "ensure_resource_group")
        self.assertEqual(len(port.calls), 2)
        self.assertEqual(before, {path: path.read_bytes() for path in tracked})
        self.assertEqual(
            hashlib.sha256(
                inspection["owner_comment"]["body"].encode("utf-8")
            ).hexdigest(),
            inspection["owner_comment"]["body_sha256"],
        )
        self.assertNotIn("ofunk", json.dumps(inspection))

    def test_provider_drift_or_unsupported_step_keeps_all_locks_held(self):
        drifted = _observation()
        drifted["resource_groups"][0]["location"] = "westeurope"
        result = self._inspect(_ObservationPort([_observation(), drifted]))
        self.assertEqual(result["error"]["code"], "PROVIDER_OBSERVATION_DRIFT")
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

    def test_any_step2_resource_keeps_all_locks_held(self):
        observation = _observation()
        observation["resource_inventory"] = [{
            "id": (
                f"/subscriptions/{SUBSCRIPTION_ID}"
                "/resourceGroups/rg-nac-bff-test/providers/"
                "Microsoft.Storage/storageAccounts/foreign"
            ),
            "name": "foreign",
            "resource_group": "rg-nac-bff-test",
            "type": "Microsoft.Storage/storageAccounts",
        }]

        result = self._inspect(
            _ObservationPort([observation, observation])
        )

        self.assertEqual(
            result["error"]["code"], "PROVIDER_OBSERVATION_INVALID"
        )
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

    def test_inspection_detects_provider_side_ledger_mutation(self):
        ledger_path = next(
            iter(
                sorted(
                    (
                        self.root
                        / DEFAULT_OUTPUT_ROOT
                        / ACTIVATION_HASH
                        / "ledger"
                    ).glob("*.redacted.json")
                )
            )
        )

        class MutatingPort(_ObservationPort):
            def observe_ensure_resource_group(inner_self, **bindings):
                result = super().observe_ensure_resource_group(**bindings)
                if len(inner_self.calls) == 1:
                    ledger_path.write_bytes(ledger_path.read_bytes() + b"\n")
                return result

        result = self._inspect(MutatingPort())

        self.assertEqual(
            result["error"]["code"],
            "INTERRUPTION_INSPECTION_LOCAL_WRITE_DETECTED",
        )
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

    def test_ledger_tamper_is_rejected_and_keeps_all_locks_held(self):
        ledger_dir = self.root / DEFAULT_OUTPUT_ROOT / ACTIVATION_HASH / "ledger"
        tamper = ledger_dir / "000007-runner-TERMINAL.redacted.json"
        tamper.write_text(
            json.dumps(
                {
                    "attempt": 1,
                    "phase": "TERMINAL",
                    "previous_event_sha256": "0" * 64,
                    "schema_version": "nac.m365-azure-bff-live-activation-event/v0.1",
                    "sequence": 7,
                    "status": "FAILED_PARTIAL",
                    "step_id": "runner",
                    "timestamp_utc": "2026-07-30T12:01:00Z",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        os.chmod(tamper, 0o600)

        result = self._inspect()

        self.assertEqual(result["error"]["code"], "INTERRUPTION_LEDGER_INVALID")
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

        state_path = (
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "resume-state.redacted.json"
        )
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["steps"][1]["id"] = "deploy_bicep_baseline"
        state_path.write_text(
            json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(state_path, 0o600)
        unsupported = self._inspect()
        self.assertEqual(
            unsupported["error"]["code"],
            "INTERRUPTION_RECONCILIATION_UNSUPPORTED",
        )
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

    def test_unconfirmed_or_tampered_approval_is_read_only_and_locked(self):
        inspection = self._inspect()
        state_path = (
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "resume-state.redacted.json"
        )
        before = state_path.read_bytes()
        approval = self._approval(
            inspection,
            provider_observation_sha256="0" * 64,
        )
        verifier = _OwnerCommentVerifier()
        with self._reconciliation_patches():
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )
        self.assertEqual(
            result["error"]["code"], "INTERRUPTION_APPROVAL_MISMATCH"
        )
        self.assertEqual(state_path.read_bytes(), before)
        self.assertEqual(len(verifier.calls), 1)
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

    def test_owner_comment_verifier_failures_are_read_only_and_locked(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        state_path = (
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "resume-state.redacted.json"
        )
        tracked = [state_path, *self._lock_paths()]
        before = {path: path.read_bytes() for path in tracked}
        cases = (
            _OwnerCommentVerifier(status="UNAVAILABLE"),
            _OwnerCommentVerifier(owner="wrong-owner"),
            _OwnerCommentVerifier(immutable=False),
            _OwnerCommentVerifier(body_suffix="\n"),
        )
        for verifier in cases:
            with self.subTest(verifier=verifier.__dict__), self._reconciliation_patches():
                result = terminalize_azure_bff_step2_interruption(
                    repo_root=self.root,
                    request=_request(),
                    reconciler_binding=self.binding,
                    observation_port=_ObservationPort(),
                    owner_comment_verifier=verifier,
                    approval=approval,
                    pre_mutation_revalidate=lambda: None,
                    output_root=self.root / DEFAULT_OUTPUT_ROOT,
                )
                self.assertEqual(
                    result["error"]["code"],
                    "OWNER_COMMENT_VERIFICATION_FAILED",
                )
                self.assertEqual(len(verifier.calls), 1)
                self.assertEqual(
                    before, {path: path.read_bytes() for path in tracked}
                )
                for path in self._lock_paths():
                    self.assertEqual(self._marker(path)["status"], "HELD")

    def test_exact_approval_terminalizes_without_resume_rollback_or_delete(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        verifier = _OwnerCommentVerifier()
        revalidation_calls = 0
        marker_path = (
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "activation.interruption-reconciliation.redacted.json"
        )

        def revalidate_before_first_mutation():
            nonlocal revalidation_calls
            revalidation_calls += 1
            self.assertFalse(marker_path.exists())
            self.assertEqual(
                [self._marker(path)["status"] for path in self._lock_paths()],
                ["HELD", "HELD", "HELD"],
            )

        with self._reconciliation_patches():
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=revalidate_before_first_mutation,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
                now=lambda: datetime(
                    2026, 7, 30, 13, 0, tzinfo=timezone.utc
                ),
            )

        self.assertEqual(result["status"], "FAILED_PARTIAL", result)
        self.assertEqual(revalidation_calls, 1)
        self.assertEqual(len(verifier.calls), 1)
        self.assertEqual(
            result["error"]["code"],
            "EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE",
        )
        run_dir = self.root / DEFAULT_OUTPUT_ROOT / ACTIVATION_HASH
        state = json.loads(
            (run_dir / "resume-state.redacted.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["status"], "FAILED_PARTIAL")
        self.assertFalse(state["resume_enabled"])
        self.assertEqual(state["automatic_rollback_count"], 0)
        self.assertEqual(state["automatic_deletion_count"], 0)
        self.assertEqual(len(state["steps"]), 2)
        self.assertEqual(state["steps"][1]["status"], "FAILED")
        self.assertEqual(
            state["steps"][1]["stable_error_code"],
            "EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE",
        )
        self.assertFalse((run_dir / "activation.commit.redacted.json").exists())
        self.assertFalse(
            (run_dir / "activation.success-receipt.redacted.json").exists()
        )
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "RELEASED")
        evidence = json.loads(
            (run_dir / "activation.redacted.json").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["status"], "FAILED_PARTIAL")
        marker = json.loads(
            (
                run_dir
                / "activation.interruption-reconciliation.redacted.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(marker["status"], "MIDRUN_RELEASED")

    def test_terminalization_is_idempotent_after_all_journals_released(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        verifier = _OwnerCommentVerifier()
        with self._reconciliation_patches():
            first = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )
            ledger_dir = (
                self.root
                / DEFAULT_OUTPUT_ROOT
                / ACTIVATION_HASH
                / "ledger"
            )
            before = {
                path.name: path.read_bytes()
                for path in ledger_dir.glob("*.redacted.json")
            }
            second = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )
        after = {
            path.name: path.read_bytes()
            for path in ledger_dir.glob("*.redacted.json")
        }
        self.assertEqual(first["status"], "FAILED_PARTIAL", first)
        self.assertEqual(second["status"], "FAILED_PARTIAL")
        self.assertEqual(second["reconciliation"]["idempotent"], True)
        self.assertEqual(len(verifier.calls), 2)
        self.assertEqual(before, after)

    def test_torn_journal_release_is_idempotently_completed(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        verifier = _OwnerCommentVerifier()
        from nac_bff import azure_activation_runner as activation_runner

        original = activation_runner._write_lock_marker
        released_calls = 0

        def fail_second_release(descriptor, activation_hash, status):
            nonlocal released_calls
            if status == "RELEASED":
                released_calls += 1
                if released_calls == 2:
                    raise OSError("simulated torn release")
            return original(descriptor, activation_hash, status)

        with self._reconciliation_patches(), patch(
            "nac_bff.azure_activation_runner._write_lock_marker",
            side_effect=fail_second_release,
        ):
            interrupted = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )
        self.assertEqual(
            interrupted["error"]["code"],
            "INTERRUPTION_TERMINALIZATION_FAILED",
        )
        self.assertEqual(
            [self._marker(path)["status"] for path in self._lock_paths()],
            ["RELEASED", "HELD", "HELD"],
        )

        with self._reconciliation_patches():
            recovered = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )
        self.assertEqual(recovered["status"], "FAILED_PARTIAL", recovered)
        self.assertTrue(recovered["reconciliation"]["idempotent"])
        self.assertEqual(
            [self._marker(path)["status"] for path in self._lock_paths()],
            ["RELEASED", "RELEASED", "RELEASED"],
        )

    def test_old_issue_632_reference_cannot_authorize_terminalization(self):
        inspection = self._inspect()
        approval = self._approval(
            inspection, owner_approval_reference=APPROVAL_REFERENCE
        )
        verifier = _OwnerCommentVerifier()

        with self._reconciliation_patches():
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

        self.assertEqual(
            result["error"]["code"], "INTERRUPTION_APPROVAL_INVALID"
        )
        self.assertEqual(verifier.calls, [])
        for path in self._lock_paths():
            self.assertEqual(self._marker(path)["status"], "HELD")

    def test_lock_path_replacement_after_open_blocks_before_first_mutation(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        target = self._lock_paths()[0]

        def replace_target_lock():
            replacement = target.with_name(target.name + ".replacement")
            replacement.write_bytes(target.read_bytes())
            os.chmod(replacement, 0o600)
            os.replace(replacement, target)

        with self._reconciliation_patches():
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=_OwnerCommentVerifier(),
                approval=approval,
                pre_mutation_revalidate=replace_target_lock,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

        self.assertEqual(
            result["error"]["code"], "INTERRUPTION_LOCK_REPLACED"
        )
        marker_path = (
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "activation.interruption-reconciliation.redacted.json"
        )
        self.assertFalse(marker_path.exists())

    def test_recovery_rejects_changed_original_issue632_binding(self):
        inspection = self._inspect()
        approval = self._approval(inspection)

        def crash_after_intent(boundary):
            if boundary == "marker:MIDRUN_TERMINALIZATION_AUTHORIZED":
                raise _Interrupted()

        with self._reconciliation_patches(), self.assertRaises(_Interrupted):
            terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=_OwnerCommentVerifier(),
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
                fault_injector=crash_after_intent,
            )

        changed_request = replace(
            _request(),
            owner_approval_reference=(
                "https://github.com/notariat8/NaC/issues/632"
                "#issuecomment-111111111"
            ),
        )
        with self._reconciliation_patches():
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=changed_request,
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=_OwnerCommentVerifier(),
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

        self.assertEqual(
            result["error"]["code"],
            "INTERRUPTION_MARKER_BINDING_MISMATCH",
        )
        for lock_path in self._lock_paths():
            self.assertEqual(self._marker(lock_path)["status"], "HELD")

    def test_unexpected_terminal_ledger_prefix_blocks_recovery(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        verifier = _OwnerCommentVerifier()

        def crash_after_intent(boundary):
            if boundary == "marker:MIDRUN_TERMINALIZATION_AUTHORIZED":
                raise _Interrupted()

        with self._reconciliation_patches(), self.assertRaises(_Interrupted):
            terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
                fault_injector=crash_after_intent,
            )

        run_dir = self.root / DEFAULT_OUTPUT_ROOT / ACTIVATION_HASH
        marker = json.loads(
            (
                run_dir
                / "activation.interruption-reconciliation.redacted.json"
            ).read_text(encoding="utf-8")
        )
        event = marker["intent"]["terminal_events"][0]
        event["outcome"]["stable_error_code"] = "UNEXPECTED_PREFIX"
        event_path = (
            run_dir
            / "ledger"
            / "000007-ensure_resource_group-FAILED.redacted.json"
        )
        event_path.write_text(
            json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.chmod(event_path, 0o600)

        with self._reconciliation_patches():
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

        self.assertEqual(
            result["error"]["code"],
            "INTERRUPTION_TERMINAL_PROGRESS_INVALID",
        )
        for lock_path in self._lock_paths():
            self.assertEqual(self._marker(lock_path)["status"], "HELD")

    def test_lock_paths_changed_after_state_reread_are_rejected(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        state_path = (
            self.root
            / DEFAULT_OUTPUT_ROOT
            / ACTIVATION_HASH
            / "resume-state.redacted.json"
        )
        from nac_bff import azure_interruption_reconciliation as reconciliation

        original_open = reconciliation._open_lock_set_for_terminalization

        def open_then_change_state(paths):
            opened = original_open(paths)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["legacy_target_binding_sha256"] = "0" * 64
            state_path.write_text(
                json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            os.chmod(state_path, 0o600)
            return opened

        with self._reconciliation_patches(), patch(
            "nac_bff.azure_interruption_reconciliation."
            "_open_lock_set_for_terminalization",
            side_effect=open_then_change_state,
        ):
            result = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=_OwnerCommentVerifier(),
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )

        self.assertEqual(
            result["error"]["code"], "INTERRUPTION_STATE_CHANGED"
        )
        for lock_path in self._lock_paths():
            self.assertEqual(self._marker(lock_path)["status"], "HELD")

    def test_crash_after_every_persistent_boundary_is_recoverable(self):
        inspection = self._inspect()
        approval = self._approval(inspection)
        verifier = _OwnerCommentVerifier()
        boundaries = (
            "marker:MIDRUN_TERMINALIZATION_AUTHORIZED",
            "ledger:FAILED",
            "marker:MIDRUN_FAILED_EVENT_APPENDED",
            "ledger:TERMINAL",
            "marker:MIDRUN_TERMINAL_EVENT_APPENDED",
            "ledger:LOCK_RELEASE_AUTHORIZED",
            "marker:MIDRUN_RELEASE_EVENT_APPENDED",
            "state:TERMINAL_WRITTEN",
            "marker:MIDRUN_TERMINAL_STATE_WRITTEN",
            "state:CHAIN_VALIDATED",
            "marker:MIDRUN_TERMINAL_STATE_VALIDATED",
            "evidence:WRITTEN",
            "marker:MIDRUN_EVIDENCE_WRITTEN",
            "marker:MIDRUN_RELEASE_IN_PROGRESS",
            "lock:target",
            "marker:MIDRUN_TARGET_LOCK_RELEASED",
            "lock:legacy",
            "marker:MIDRUN_LEGACY_LOCK_RELEASED",
            "lock:legacy_host",
            "marker:MIDRUN_LEGACY_HOST_LOCK_RELEASED",
            "marker:MIDRUN_RELEASED",
        )

        for target in boundaries:
            def crash_at_boundary(boundary, *, expected=target):
                if boundary == expected:
                    raise _Interrupted()

            with self.subTest(boundary=target), self._reconciliation_patches():
                with self.assertRaises(_Interrupted):
                    terminalize_azure_bff_step2_interruption(
                        repo_root=self.root,
                        request=_request(),
                        reconciler_binding=self.binding,
                        observation_port=_ObservationPort(),
                        owner_comment_verifier=verifier,
                        approval=approval,
                        pre_mutation_revalidate=lambda: None,
                        output_root=self.root / DEFAULT_OUTPUT_ROOT,
                        fault_injector=crash_at_boundary,
                    )

        with self._reconciliation_patches():
            recovered = terminalize_azure_bff_step2_interruption(
                repo_root=self.root,
                request=_request(),
                reconciler_binding=self.binding,
                observation_port=_ObservationPort(),
                owner_comment_verifier=verifier,
                approval=approval,
                pre_mutation_revalidate=lambda: None,
                output_root=self.root / DEFAULT_OUTPUT_ROOT,
            )
        self.assertEqual(recovered["status"], "FAILED_PARTIAL", recovered)
        self.assertTrue(recovered["reconciliation"]["idempotent"])
        self.assertEqual(
            [self._marker(path)["status"] for path in self._lock_paths()],
            ["RELEASED", "RELEASED", "RELEASED"],
        )


class _Patches:
    def __init__(self, *patchers) -> None:
        self.patchers = patchers

    def __enter__(self):
        for patcher in self.patchers:
            patcher.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for patcher in reversed(self.patchers):
            patcher.stop()
        return False
