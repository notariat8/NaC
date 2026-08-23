from __future__ import annotations

import hashlib
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nac_bff.azure_activation import (
    PROVISIONER_CLIENT_ID,
    PROVISIONER_GRAPH_APPLICATION_ROLES,
    SUCCESSFUL_UPDATE_BASELINE_TEMPLATE_HASHES,
    TENANT_ID,
    activation_step_ids,
)
from nac_bff.azure_activation_approval import (
    approval_binding_sha256,
    build_owner_approval_payload,
    canonical_owner_comment_body,
    owner_comment_body_sha256,
)
from nac_bff.azure_activation_owner_gate import build_activation_owner_gate
from nac_bff.azure_activation_attestations import (
    LIVE_CLI_ARGUMENT_BY_ATTESTATION,
    TOOLCHAIN_ATTESTATION_FIELDS,
    calculate_toolchain_attestations_sha256,
)
from nac_bff.azure_activation_runner import _sha256_json as toolchain_sha256_json
from nac_cli.cli import main as nac_main


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "c" * 40
ATTESTATION_VALUES = {
    name: f"{index:x}" * 64
    for index, name in enumerate(TOOLCHAIN_ATTESTATION_FIELDS, start=1)
}
TOOLCHAIN_HASH = calculate_toolchain_attestations_sha256(ATTESTATION_VALUES)
PROVISIONER_BOOTSTRAP_BINDING_HASH = "9" * 64


class AzureBffActivationOwnerGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        contract = (
            self.root
            / "workflows/contracts/m365-azure-bff-live-activation.contract.json"
        )
        contract.parent.mkdir(parents=True)
        contract.write_text(
            json.dumps({"permission_boundary": {"graph": ["Sites.Selected"]}}),
            encoding="utf-8",
        )
        self.certificate = self.root / "public-cert.pem"
        self.certificate.write_text("public", encoding="utf-8")
        self.private_key = self.root / "private-key.pem"
        self.private_key.write_text("private-key-must-not-escape", encoding="utf-8")
        self.private_key.chmod(0o600)
        self.state = self.root / "privileged-apply-result.json"
        self.state.write_text(
            json.dumps(
                {
                    "status": "PASSED",
                    "tenantId": TENANT_ID,
                    "applications": {
                        "m365_provisioning_app": {
                            "displayName": "NaC M365 Provisioning",
                            "clientId": PROVISIONER_CLIENT_ID,
                            "appRoleAssignments": [
                                {
                                    "permission": permission,
                                    "status": "existing",
                                }
                                for permission in PROVISIONER_GRAPH_APPLICATION_ROLES
                            ],
                        }
                    },
                }
            ),
            encoding="utf-8",
        )

    def _gate_kwargs(self) -> dict:
        return {
            "provisioner_state": self.state,
            "provisioner_private_key": self.private_key,
            "provisioner_env": {},
        }

    @staticmethod
    def _plan() -> dict:
        return {
            "status": "READY",
            "activation_hash": ACTIVATION_HASH,
            "source_control": {"commit": COMMIT},
            "bindings": {"workspace_id": "notary_team_01"},
            "steps": [{"id": step_id} for step_id in activation_step_ids()],
        }

    @staticmethod
    def _attestations() -> dict:
        return {
            "status": "READY",
            "toolchain_attestations": dict(ATTESTATION_VALUES),
            "toolchain_attestations_sha256": TOOLCHAIN_HASH,
            "live_cli_arguments": {
                LIVE_CLI_ARGUMENT_BY_ATTESTATION[name]: ATTESTATION_VALUES[name]
                for name in TOOLCHAIN_ATTESTATION_FIELDS
            },
        }

    def test_binding_hash_has_no_toolchain_trailing_newline(self) -> None:
        value = {"workspace_id": "notary_team_01"}
        compact = json.dumps(value, sort_keys=True, separators=(",", ":"))

        self.assertEqual(
            approval_binding_sha256(value),
            hashlib.sha256(compact.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(
            approval_binding_sha256(value),
            toolchain_sha256_json(value),
        )

    def test_payload_and_comment_are_exact_compact_json(self) -> None:
        payload = build_owner_approval_payload(
            activation_hash=ACTIVATION_HASH,
            approved_commit=COMMIT,
            approved_tree=TREE,
            provisioner_bootstrap_binding_sha256=(
                PROVISIONER_BOOTSTRAP_BINDING_HASH
            ),
            toolchain_attestations_sha256=TOOLCHAIN_HASH,
            bindings={"workspace_id": "notary_team_01"},
            permission_boundary={"graph": ["Sites.Selected"]},
            step_ids=["read", "apply"],
        )
        body = canonical_owner_comment_body(payload)

        self.assertNotIn("\n", body)
        self.assertNotIn(": ", body)
        self.assertEqual(json.loads(body), payload)
        self.assertEqual(
            owner_comment_body_sha256(body),
            hashlib.sha256(body.encode("utf-8")).hexdigest(),
        )

    def test_binding_or_permission_mutation_changes_approval_body_hash(self) -> None:
        def payload(
            bindings: dict,
            permission_boundary: dict,
            bootstrap_binding: str = PROVISIONER_BOOTSTRAP_BINDING_HASH,
            approved_update_baseline_template_hashes: tuple[str, ...] = (),
        ) -> dict:
            return build_owner_approval_payload(
                activation_hash=ACTIVATION_HASH,
                approved_commit=COMMIT,
                approved_tree=TREE,
                provisioner_bootstrap_binding_sha256=bootstrap_binding,
                toolchain_attestations_sha256=TOOLCHAIN_HASH,
                bindings=bindings,
                permission_boundary=permission_boundary,
                step_ids=list(activation_step_ids()),
                approved_update_baseline_template_hashes=(
                    approved_update_baseline_template_hashes
                ),
            )

        baseline = payload(
            {"workspace_id": "notary_team_01"},
            {"graph": ["Sites.Selected"]},
        )
        changed_binding = payload(
            {"workspace_id": "notary_team_02"},
            {"graph": ["Sites.Selected"]},
        )
        changed_permission = payload(
            {"workspace_id": "notary_team_01"},
            {"graph": ["Sites.Read.All"]},
        )
        changed_bootstrap_binding = payload(
            {"workspace_id": "notary_team_01"},
            {"graph": ["Sites.Selected"]},
            "8" * 64,
        )
        changed_update_baseline = payload(
            {"workspace_id": "notary_team_01"},
            {"graph": ["Sites.Selected"]},
            approved_update_baseline_template_hashes=("15781720678765630241",),
        )

        self.assertNotEqual(
            baseline["target_binding_sha256"],
            changed_binding["target_binding_sha256"],
        )
        self.assertNotEqual(
            baseline["permission_boundary_sha256"],
            changed_permission["permission_boundary_sha256"],
        )
        self.assertNotEqual(
            baseline["provisioner_bootstrap_binding_sha256"],
            changed_bootstrap_binding["provisioner_bootstrap_binding_sha256"],
        )
        baseline_body_hash = owner_comment_body_sha256(
            canonical_owner_comment_body(baseline)
        )
        for mutated in (
            changed_binding,
            changed_permission,
            changed_bootstrap_binding,
            changed_update_baseline,
        ):
            self.assertNotEqual(
                baseline_body_hash,
                owner_comment_body_sha256(
                    canonical_owner_comment_body(mutated)
                ),
            )

    def test_builder_emits_atomic_ready_gate(self) -> None:
        snapshots = [(COMMIT, TREE, False), (COMMIT, TREE, False)]
        with patch(
            "nac_bff.azure_activation_owner_gate._git_snapshot",
            side_effect=snapshots,
        ):
            result = build_activation_owner_gate(
                self.root,
                self.certificate,
                **self._gate_kwargs(),
                activation_plan_builder=lambda _root: self._plan(),
                attestation_builder=lambda **_kwargs: self._attestations(),
            )

        self.assertEqual(result["status"], "READY")
        self.assertEqual(result["approved_commit"], COMMIT)
        self.assertEqual(result["approved_tree"], TREE)
        self.assertEqual(
            result["owner_comment_body_sha256"],
            owner_comment_body_sha256(result["owner_comment_body"]),
        )
        self.assertEqual(result["boundaries"]["provider_requests_made"], 0)
        self.assertIs(result["boundaries"]["private_key_read"], False)
        self.assertEqual(result["provisioner_bootstrap"]["status"], "PASSED")
        binding_sha256 = result["provisioner_bootstrap_binding_sha256"]
        self.assertEqual(
            result["live_cli_arguments"][
                "--provisioner-bootstrap-binding-sha256"
            ],
            binding_sha256,
        )
        self.assertEqual(
            result["owner_approval_payload"][
                "provisioner_bootstrap_binding_sha256"
            ],
            binding_sha256,
        )
        self.assertEqual(
            result["owner_approval_payload"][
                "approved_update_baseline_template_hashes"
            ],
            list(SUCCESSFUL_UPDATE_BASELINE_TEMPLATE_HASHES),
        )
        serialized = json.dumps(result)
        self.assertNotIn(TENANT_ID, serialized)
        self.assertNotIn(PROVISIONER_CLIENT_ID, serialized)
        self.assertNotIn(str(self.root), serialized)
        self.assertNotIn("private-key-must-not-escape", serialized)

    def test_builder_stops_before_plan_on_provisioner_binding_mismatch(self) -> None:
        plan_builder = Mock(
            side_effect=AssertionError("plan must remain unreachable")
        )
        attestation_builder = Mock(
            side_effect=AssertionError("attestations must remain unreachable")
        )
        kwargs = self._gate_kwargs()
        kwargs["provisioner_env"] = {"M365_TENANT_ID": "wrong-tenant"}
        with patch(
            "nac_bff.azure_activation_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ):
            result = build_activation_owner_gate(
                self.root,
                self.certificate,
                **kwargs,
                activation_plan_builder=plan_builder,
                attestation_builder=attestation_builder,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            result["error_code"], "PROVISIONER_ENV_BINDING_MISMATCH"
        )
        self.assertFalse(result["boundaries"]["private_key_read"])
        self.assertEqual(result["boundaries"]["provider_requests_made"], 0)
        self.assertNotIn("wrong-tenant", json.dumps(result))
        plan_builder.assert_not_called()
        attestation_builder.assert_not_called()

    def test_binding_hash_rejects_nonstandard_json_numbers(self) -> None:
        with self.assertRaises(ValueError):
            approval_binding_sha256({"invalid": float("nan")})

    def test_payload_rejects_string_step_sequence(self) -> None:
        with self.assertRaises(ValueError):
            build_owner_approval_payload(
                activation_hash=ACTIVATION_HASH,
                approved_commit=COMMIT,
                approved_tree=TREE,
                provisioner_bootstrap_binding_sha256=(
                    PROVISIONER_BOOTSTRAP_BINDING_HASH
                ),
                toolchain_attestations_sha256=TOOLCHAIN_HASH,
                bindings={"workspace_id": "notary_team_01"},
                permission_boundary={"graph": ["Sites.Selected"]},
                step_ids="not-a-sequence",
            )

    def test_payload_rejects_invalid_update_baseline_template_hashes(self) -> None:
        with self.assertRaises(ValueError):
            build_owner_approval_payload(
                activation_hash=ACTIVATION_HASH,
                approved_commit=COMMIT,
                approved_tree=TREE,
                provisioner_bootstrap_binding_sha256=(
                    PROVISIONER_BOOTSTRAP_BINDING_HASH
                ),
                toolchain_attestations_sha256=TOOLCHAIN_HASH,
                bindings={"workspace_id": "notary_team_01"},
                permission_boundary={"graph": ["Sites.Selected"]},
                step_ids=["read", "apply"],
                approved_update_baseline_template_hashes=(
                    "not-an-arm-template-hash",
                ),
            )

    def test_builder_rejects_noncanonical_step_sequence(self) -> None:
        plan = self._plan()
        plan["steps"] = []
        with patch(
            "nac_bff.azure_activation_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ):
            result = build_activation_owner_gate(
                self.root,
                self.certificate,
                **self._gate_kwargs(),
                activation_plan_builder=lambda _root: plan,
                attestation_builder=lambda **_kwargs: self._attestations(),
            )
        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "ACTIVATION_STEP_SEQUENCE_INVALID")

    def test_builder_rejects_inconsistent_attestations_and_live_arguments(self) -> None:
        cases = (
            ({**self._attestations(), "toolchain_attestations_sha256": "f" * 64}, "TOOLCHAIN_ATTESTATIONS_INVALID"),
            ({**self._attestations(), "live_cli_arguments": "not-a-map"}, "TOOLCHAIN_LIVE_ARGUMENTS_INVALID"),
        )
        for attestations, code in cases:
            with self.subTest(code=code), patch(
                "nac_bff.azure_activation_owner_gate._git_snapshot",
                return_value=(COMMIT, TREE, False),
            ):
                result = build_activation_owner_gate(
                    self.root,
                    self.certificate,
                    **self._gate_kwargs(),
                    activation_plan_builder=lambda _root: self._plan(),
                    attestation_builder=lambda **_kwargs: attestations,
                )
            self.assertEqual(result["status"], "NOT_READY")
            self.assertEqual(result["error_code"], code)
            self.assertNotIn("owner_comment_body", result)

    def test_builder_redacts_repo_path_resolution_failure(self) -> None:
        loop = self.root / "loop"
        loop.symlink_to(loop)
        result = build_activation_owner_gate(
            loop,
            self.certificate,
            **self._gate_kwargs(),
        )
        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "GIT_SNAPSHOT_UNAVAILABLE")
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_builder_rejects_dirty_or_changed_tree_without_partial_gate(self) -> None:
        cases = (
            ([(COMMIT, TREE, True)], "SOURCE_TREE_NOT_CLEAN"),
            (
                [(COMMIT, TREE, False), (COMMIT, "f" * 40, False)],
                "SOURCE_TREE_CHANGED_DURING_GATE_BUILD",
            ),
        )
        for snapshots, code in cases:
            with self.subTest(code=code), patch(
                "nac_bff.azure_activation_owner_gate._git_snapshot",
                side_effect=snapshots,
            ):
                result = build_activation_owner_gate(
                    self.root,
                    self.certificate,
                    **self._gate_kwargs(),
                    activation_plan_builder=lambda _root: self._plan(),
                    attestation_builder=lambda **_kwargs: self._attestations(),
                )
            self.assertEqual(result["status"], "NOT_READY")
            self.assertEqual(result["error_code"], code)
            self.assertNotIn("owner_comment_body", result)
            self.assertNotIn("owner_approval_payload", result)

    def test_builder_redacts_unexpected_exception_details(self) -> None:
        with patch(
            "nac_bff.azure_activation_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ):
            result = build_activation_owner_gate(
                self.root,
                self.certificate,
                **self._gate_kwargs(),
                activation_plan_builder=lambda _root: (_ for _ in ()).throw(
                    OSError("/secret/local/path")
                ),
                attestation_builder=lambda **_kwargs: self._attestations(),
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "OWNER_GATE_GENERATION_FAILED")
        self.assertNotIn("secret", json.dumps(result))
        self.assertNotIn("owner_comment_body", result)

    def test_builder_propagates_attestation_not_ready_without_private_key(self) -> None:
        with patch(
            "nac_bff.azure_activation_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ):
            result = build_activation_owner_gate(
                self.root,
                self.certificate,
                **self._gate_kwargs(),
                activation_plan_builder=lambda _root: self._plan(),
                attestation_builder=lambda **_kwargs: {"status": "NOT_READY"},
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "TOOLCHAIN_ATTESTATIONS_NOT_READY")
        self.assertIs(result["boundaries"]["private_key_read"], False)
        self.assertNotIn("owner_comment_body", result)


class AzureBffActivationOwnerGateCliTests(unittest.TestCase):
    def test_cli_requires_all_provisioner_bootstrap_inputs(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            result = nac_main(
                [
                    "--repo-root",
                    str(Path(__file__).resolve().parents[1]),
                    "m365",
                    "teams-sharepoint",
                    "bff-azure-activation-owner-gate",
                    "--format",
                    "json",
                ]
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(result, 2)
        self.assertEqual(payload["status"], "NOT_READY")
        self.assertEqual(
            payload["error_code"], "PROVISIONER_BOOTSTRAP_INPUTS_REQUIRED"
        )
        self.assertFalse(payload["boundaries"]["private_key_read"])
        self.assertEqual(payload["boundaries"]["provider_requests_made"], 0)

    def test_cli_dispatches_ready_owner_gate(self) -> None:
        output = StringIO()
        ready = {
            "schema_version": "nac.m365-azure-bff-activation-owner-gate/v1",
            "status": "READY",
            "owner_comment_body": "{}",
        }
        with patch(
            "nac_cli.cli.build_activation_owner_gate", return_value=ready
        ) as builder, redirect_stdout(output):
            result = nac_main(
                [
                    "--repo-root",
                    str(Path(__file__).resolve().parents[1]),
                    "m365",
                    "teams-sharepoint",
                    "bff-azure-activation-owner-gate",
                    "--bff-attestation-provisioner-certificate",
                    "/tmp/public-cert.pem",
                    "--bff-provisioner-state",
                    "/tmp/privileged-apply-result.json",
                    "--bff-provisioner-private-key",
                    "/tmp/private-key.pem",
                    "--format",
                    "json",
                ]
            )
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "READY")
        builder.assert_called_once()
        self.assertEqual(
            builder.call_args.kwargs["provisioner_state"],
            Path("/tmp/privileged-apply-result.json"),
        )
        self.assertEqual(
            builder.call_args.kwargs["provisioner_private_key"],
            Path("/tmp/private-key.pem"),
        )


if __name__ == "__main__":
    unittest.main()
