from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.azure_activation import RESOURCE_GROUP  # noqa: E402
from nac_bff.azure_activation_composition import (  # noqa: E402
    AzureBffLiveExecutionPort,
    GitHubApprovalVerifier,
    _sha256_file,
    _sha256_json,
    _sha256_text,
    _validate_azure_resource_inventory,
    _validate_spfx_grants,
)
from nac_bff.azure_activation_runner import (  # noqa: E402
    ActivationContext,
    ActivationStepError,
    DEFAULT_OUTPUT_ROOT,
    LiveActivationRequest,
    _reject_secret_sentinel,
    run_azure_bff_live_activation,
)


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "c" * 40
APPROVAL_BODY_HASH = "d" * 64
PERMISSION_HASH = "e" * 64
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
ACTOR_ID = "11111111-1111-4111-8111-111111111111"
API_SERVICE_PRINCIPAL_ID = "22222222-2222-4222-8222-222222222222"
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

# Verification-contract IDs intentionally map to the narrower stable production
# classifications asserted below. The contract IDs remain the audit vocabulary.
VERIFICATION_MARKERS = {
    "wrong_owner_login": "APPROVAL_OWNER_MISMATCH",
    "wrong_owner_association": "APPROVAL_OWNER_MISMATCH",
    "duplicates": "AZURE_RESOURCE_INVENTORY_DUPLICATE",
    "dirty_tree": "GIT_WORKTREE_NOT_CLEAN",
    "health_auth_ready_order": "ordered_probe_sequence_exact",
    "secret_sentinel": "SENSITIVE_VALUE_REJECTED",
    "broader_permissions": "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE",
    "prepared_input_drift": "PREPARED_INPUTS_MANIFEST_MISMATCH",
    "wrong_target": "TARGET_BINDING_MISMATCH",
    "restoration": "synthetic_restoration_failure",
}


class _NoWritePort:
    def __init__(self) -> None:
        self.prewrite_calls = 0
        self.step_calls: list[str] = []

    def verify_prewrite(self, context, request):
        del context, request
        self.prewrite_calls += 1
        return {
            "status": "PASSED",
            "code": "PREWRITE_VERIFIED",
            "prebuilt_inputs_verified": True,
        }

    def execute_step(self, step_id, context):
        del context
        self.step_calls.append(step_id)
        return {
            "status": "PASSED",
            "classification": "verified",
            "verified_count": 1,
            "reference_sha256": "f" * 64,
        }


class _SyntheticProbe:
    def __init__(self, events: list[str], *, restoration_fails: bool = False) -> None:
        self._events = events
        self._restoration_fails = restoration_fails

    def set_access_mode(self, mode, actor_id, correlation_id):
        del actor_id, correlation_id
        self._events.append(f"mode:{mode}")
        return {"updated_count": 1, "verified_count": 1}

    def restore_assigned(self, actor_id, correlation_id):
        del actor_id, correlation_id
        self._events.append("restore:assigned")
        if self._restoration_fails:
            raise RuntimeError("provider body must remain redacted")
        return {"updated_count": 1, "verified_count": 1}


class _ReadinessProbe:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def wait_for_status(self, url, expected_status):
        del expected_status
        self._events.append("healthz" if url.endswith("/healthz") else "readyz")


def _request(*, approval_body_sha256: str = APPROVAL_BODY_HASH) -> LiveActivationRequest:
    return LiveActivationRequest(
        expected_activation_hash=ACTIVATION_HASH,
        approved_commit=COMMIT,
        approved_tree=TREE,
        owner_approval_reference=APPROVAL_REFERENCE,
        approval_body_sha256=approval_body_sha256,
        azure_cli_toolchain_sha256=AZURE_TOOLCHAIN_HASH,
        m365_cli_sha256=M365_CLI_HASH,
        m365_node_sha256=M365_NODE_HASH,
        build_python_sha256="8" * 64,
        build_node_sha256=BUILD_NODE_HASH,
        build_npm_cli_sha256=BUILD_NPM_HASH,
        gh_cli_sha256=GH_CLI_HASH,
        provisioner_certificate_sha256=PROVISIONER_CERTIFICATE_HASH,
        provisioner_bootstrap_binding_sha256=(
            PROVISIONER_BOOTSTRAP_BINDING_HASH
        ),
        reason="Activate the exact synthetic BFF target.",
        correlation_id="nac-bff-live-20260715",
        owner_approved=True,
        execute_live_activation=True,
    )


def _context(repo_root: Path, *, run_dir: Path | None = None) -> ActivationContext:
    return ActivationContext(
        repo_root=repo_root,
        run_dir=run_dir or repo_root / "out",
        correlation_reference_sha256="1" * 64,
        reason_sha256="2" * 64,
        activation_hash=ACTIVATION_HASH,
        approved_commit=COMMIT,
        approved_tree=TREE,
    )


def _plan(*, workspace_id: str = "notary_team_01") -> dict:
    return {
        "status": "READY",
        "activation_hash": ACTIVATION_HASH,
        "source_control": {"commit": COMMIT},
        "bindings": {"workspace_id": workspace_id},
        "steps": [{"id": step} for step in STEPS],
    }


def _run_with_plans(
    repo_root: Path,
    port: _NoWritePort,
    plans: list[dict],
    *,
    clean: bool = True,
) -> dict:
    plan_values = iter(plans)
    lock_root = repo_root / ".test-locks"
    with (
        patch(
            "nac_bff.azure_activation_runner.build_azure_bff_activation_plan",
            side_effect=lambda _root: next(plan_values),
        ),
        patch(
            "nac_bff.azure_activation_runner._permission_boundary_hash",
            return_value=PERMISSION_HASH,
        ),
        patch("nac_bff.azure_activation_runner._clean_tree", return_value=clean),
        patch("nac_bff.azure_activation_runner._head_commit", return_value=COMMIT),
        patch("nac_bff.azure_activation_runner._head_tree", return_value=TREE),
        patch("nac_bff.azure_activation_runner._HOST_LOCK_ROOT", lock_root),
        patch(
            "nac_bff.azure_activation_runner._LEGACY_HOST_LOCK_ROOT",
            repo_root / ".legacy-test-locks",
        ),
    ):
        return run_azure_bff_live_activation(
            repo_root=repo_root,
            request=_request(),
            execution_port=port,
            output_root=repo_root / DEFAULT_OUTPUT_ROOT,
            now=lambda: datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
        )


class M365AzureBffLiveActivationNegativePathTests(unittest.TestCase):
    def test_wrong_owner_uses_stable_approval_snapshot_classification(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["wrong_owner_login"], "APPROVAL_OWNER_MISMATCH"
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            contract = (
                root
                / "workflows/contracts/m365-azure-bff-live-activation.contract.json"
            )
            contract.parent.mkdir(parents=True)
            permission_boundary = {
                "graph": ["Sites.Selected"],
                "site": ["read"],
            }
            contract.write_text(
                json.dumps({"permission_boundary": permission_boundary}),
                encoding="utf-8",
            )
            plan = _plan()
            payload = {
                "owner-approved": True,
                "expected_activation_sha256": ACTIVATION_HASH,
                "approved_commit_sha": COMMIT,
                "approved_tree_sha": TREE,
                "provisioner_bootstrap_binding_sha256": (
                    PROVISIONER_BOOTSTRAP_BINDING_HASH
                ),
                "target_binding_sha256": _sha256_json(plan["bindings"]),
                "permission_boundary_sha256": _sha256_json(permission_boundary),
                "step_sequence_sha256": _sha256_json(list(STEPS)),
                "no_automatic_rollback_or_deletion": True,
            }
            body = json.dumps(payload, sort_keys=True)
            request = _request(approval_body_sha256=_sha256_text(body))
            comment = {
                "user": {"login": "not-the-owner"},
                "author_association": "OWNER",
                "html_url": APPROVAL_REFERENCE,
                "created_at": "2026-07-15T10:00:00Z",
                "updated_at": "2026-07-15T10:00:00Z",
                "body": body,
            }
            verifier = object.__new__(GitHubApprovalVerifier)
            verifier._binary = Path("/usr/bin/gh")
            with patch.object(verifier, "_gh_json", return_value=comment):
                result = verifier.verify(request, _context(root), plan)
        self.assertEqual(
            result, {"status": "FAILED", "code": "APPROVAL_OWNER_MISMATCH"}
        )

    def test_owner_association_contract_is_exact_and_fail_closed(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["wrong_owner_association"],
            "APPROVAL_OWNER_MISMATCH",
        )
        contract = json.loads(
            (
                REPO_ROOT
                / "workflows/contracts/m365-azure-bff-live-activation.contract.json"
            ).read_text(encoding="utf-8")
        )
        snapshot = contract["consolidated_owner_gate"][
            "immutable_approval_reference"
        ]
        self.assertEqual(
            snapshot["owner_author_associations_exact"], ["OWNER", "MEMBER"]
        )
        self.assertEqual(
            snapshot["missing_or_malformed_author_association_behavior"],
            "reject_with_APPROVAL_OWNER_MISMATCH",
        )

    def test_duplicate_target_resource_is_rejected_by_inventory_validator(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["duplicates"], "AZURE_RESOURCE_INVENTORY_DUPLICATE"
        )
        duplicate = {
            "name": "id-nac-bff-test-abc123",
            "type": "Microsoft.ManagedIdentity/userAssignedIdentities",
            "resourceGroup": RESOURCE_GROUP,
        }
        with self.assertRaises(ActivationStepError) as raised:
            _validate_azure_resource_inventory([duplicate, dict(duplicate)])
        self.assertEqual(raised.exception.code, "AZURE_RESOURCE_INVENTORY_DUPLICATE")

    def test_dirty_worktree_blocks_before_prewrite_or_artifacts(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["dirty_tree"], "GIT_WORKTREE_NOT_CLEAN"
        )
        port = _NoWritePort()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = _run_with_plans(root, port, [_plan()], clean=False)
            self.assertFalse((root / DEFAULT_OUTPUT_ROOT).exists())
        self.assertEqual(result["error"]["code"], "GIT_WORKTREE_NOT_CLEAN")
        self.assertEqual(port.prewrite_calls, 0)
        self.assertEqual(port.step_calls, [])

    def test_live_probe_order_keeps_readyz_after_restore_and_final_read(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["health_auth_ready_order"],
            "ordered_probe_sequence_exact",
        )
        events: list[str] = []
        port = object.__new__(AzureBffLiveExecutionPort)
        port._actor_id = ACTOR_ID
        port._synthetic = _SyntheticProbe(events)
        port._http_readiness = _ReadinessProbe(events)
        port._function_health_readback_passed = True

        def request_bff(mode: str) -> None:
            events.append(f"read:{mode}")

        with patch.object(port, "_request_bff", side_effect=request_bff):
            result = port._run_access_smokes(_context(REPO_ROOT))

        self.assertEqual(result["classification"], "verified")
        self.assertEqual(
            events,
            [
                "healthz",
                "mode:assigned",
                "read:assigned",
                "mode:deputy",
                "read:deputy",
                "mode:denied",
                "read:denied",
                "read:tampered",
                "restore:assigned",
                "read:assigned",
                "readyz",
            ],
        )

    def test_secret_sentinel_is_replaced_by_stable_redacted_code(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["secret_sentinel"], "SENSITIVE_VALUE_REJECTED"
        )
        with self.assertRaises(ActivationStepError) as raised:
            _reject_secret_sentinel({"provider_stderr": "NAC_SECRET_SENTINEL_632"})
        self.assertEqual(raised.exception.code, "SENSITIVE_VALUE_REJECTED")
        self.assertNotIn("NAC_SECRET_SENTINEL_632", str(raised.exception))

    def test_broader_permission_is_rejected_by_spfx_boundary_validator(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["broader_permissions"],
            "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE",
        )
        grants = [
            {
                "resourceId": API_SERVICE_PRINCIPAL_ID,
                "scope": "Matter.Read.All",
            }
        ]
        with self.assertRaises(ActivationStepError) as raised:
            _validate_spfx_grants(
                grants,
                API_SERVICE_PRINCIPAL_ID,
                allow_absent=False,
            )
        self.assertEqual(
            raised.exception.code, "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE"
        )

    def test_prepared_input_binding_drift_is_rejected_before_deployment(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["prepared_input_drift"],
            "PREPARED_INPUTS_MANIFEST_MISMATCH",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = {
                name: root / name
                for name in (
                    "main.bicep",
                    "main.parameters.json",
                    "function.zip",
                    "viewer.sppkg",
                )
            }
            for name, path in paths.items():
                path.write_text(name, encoding="utf-8")
            digests = {name: _sha256_file(path) for name, path in paths.items()}
            manifest_base = {
                "schema_version": "nac.m365-azure-bff-prepared-inputs/v1",
                "approved_commit_sha": COMMIT,
                "approved_tree_sha": "0" * 40,
                "activation_hash": ACTIVATION_HASH,
                "approved_tree_snapshot_sha256": "1" * 64,
                "bicep_snapshot_sha256": digests["main.bicep"],
                "bicep_parameters_snapshot_sha256": digests[
                    "main.parameters.json"
                ],
                "function_package_sha256": digests["function.zip"],
                "spfx_package_sha256": digests["viewer.sppkg"],
            }
            manifest = {
                **manifest_base,
                "prepared_inputs_sha256": _sha256_json(manifest_base),
            }
            manifest_path = root / "prepared-inputs.redacted.json"
            manifest_path.write_text(
                json.dumps(manifest, sort_keys=True), encoding="utf-8"
            )

            port = object.__new__(AzureBffLiveExecutionPort)
            port._approved_tree_snapshot_sha256 = "1" * 64
            port._bicep_path = paths["main.bicep"]
            port._bicep_sha256 = digests["main.bicep"]
            port._bicep_parameters_path = paths["main.parameters.json"]
            port._bicep_parameters_sha256 = digests["main.parameters.json"]
            port._function_package_path = paths["function.zip"]
            port._function_package_sha256 = digests["function.zip"]
            port._spfx_package_path = paths["viewer.sppkg"]
            port._spfx_package_sha256 = digests["viewer.sppkg"]
            port._prepared_inputs_path = manifest_path
            port._prepared_inputs_manifest_sha256 = _sha256_file(manifest_path)
            port._prepared_inputs_sha256 = manifest["prepared_inputs_sha256"]

            with self.assertRaises(ActivationStepError) as raised:
                port._require_prepared_inputs(_context(root))
        self.assertEqual(
            raised.exception.code, "PREPARED_INPUTS_MANIFEST_MISMATCH"
        )

    def test_target_binding_change_after_prewrite_stops_before_steps(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["wrong_target"], "TARGET_BINDING_MISMATCH"
        )
        port = _NoWritePort()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = _run_with_plans(
                root,
                port,
                [_plan(), _plan(workspace_id="foreign_workspace")],
            )
            self.assertFalse((root / DEFAULT_OUTPUT_ROOT / ACTIVATION_HASH).exists())
        self.assertEqual(result["error"]["code"], "TARGET_BINDING_MISMATCH")
        self.assertEqual(port.prewrite_calls, 1)
        self.assertEqual(port.step_calls, [])

    def test_synthetic_restoration_failure_blocks_final_read_and_readyz(self) -> None:
        self.assertEqual(
            VERIFICATION_MARKERS["restoration"], "synthetic_restoration_failure"
        )
        events: list[str] = []
        port = object.__new__(AzureBffLiveExecutionPort)
        port._actor_id = ACTOR_ID
        port._synthetic = _SyntheticProbe(events, restoration_fails=True)
        port._http_readiness = _ReadinessProbe(events)

        def request_bff(mode: str) -> None:
            events.append(f"read:{mode}")

        with (
            patch.object(port, "_request_bff", side_effect=request_bff),
            self.assertRaises(ActivationStepError) as raised,
        ):
            port._run_access_smokes(_context(REPO_ROOT))

        self.assertEqual(
            raised.exception.code, "SYNTHETIC_STATE_RESTORATION_FAILED"
        )
        self.assertEqual(events[-1], "restore:assigned")
        self.assertNotIn("readyz", events)
        self.assertEqual(events.count("read:assigned"), 1)


if __name__ == "__main__":
    unittest.main()
