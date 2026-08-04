from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import nac_bff.azure_performance_owner_gate as owner_gate
from nac_bff.azure_performance_acceptance import (
    CONTRACT_RELATIVE_PATH,
    build_performance_acceptance_plan,
)
from nac_bff.azure_activation import RESOURCE_GROUP, SUBSCRIPTION_ID, TENANT_ID
from nac_bff.azure_activation_attestations import (
    TOOLCHAIN_ATTESTATION_FIELDS,
    calculate_toolchain_attestations_sha256,
)
from nac_bff.azure_performance_owner_gate import (
    ACTION,
    build_performance_infrastructure_owner_gate,
    measure_performance_infrastructure_approval,
)
from nac_bff.azure_performance_runtime import _validate_owner_execution_bindings
from nac_cli import cli


REPO_ROOT = Path(__file__).resolve().parents[1]
COMMIT = "1" * 40
TREE = "2" * 40
ACTIVATION = "3" * 64
TOOLCHAIN = {
    name: f"{index:x}" * 64
    for index, name in enumerate(TOOLCHAIN_ATTESTATION_FIELDS, start=1)
}
TOOLCHAIN_SHA256 = calculate_toolchain_attestations_sha256(TOOLCHAIN)
MONITOR_WINDOW_ANCHOR = "2026-08-03T10:00:00Z"


def _parameters() -> dict[str, object]:
    contract = REPO_ROOT / CONTRACT_RELATIVE_PATH
    import hashlib

    contract_sha256 = hashlib.sha256(contract.read_bytes()).hexdigest()
    target = build_performance_acceptance_plan(
        ACTIVATION, contract_sha256
    )["target_binding_sha256"]
    return {
        "location": "germanywestcentral",
        "storageAccountName": "stnacperflease001",
        "bffStorageAccountResourceId": (
            f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/"
            "providers/Microsoft.Storage/storageAccounts/stnacbfftest001"
        ),
        "wormStorageAccountResourceId": (
            f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/"
            "providers/Microsoft.Storage/storageAccounts/stnacwormtest001"
        ),
        "provisionerPrincipalId": "11111111-2222-4333-8444-555555555555",
        "allowedClientIpAddress": "8.8.8.8",
        "targetBindingSha256": target,
        "tenantId": TENANT_ID,
        "subscriptionId": SUBSCRIPTION_ID,
        "resourceGroupName": RESOURCE_GROUP,
        "deploymentMode": "Incremental",
        "tags": {
            "owner": "notariat8",
            "purpose": "endpoint-scoped-conservative-measurement",
        },
    }


def _worm_parameters() -> dict[str, object]:
    return {
        "location": "germanywestcentral",
        "tenantId": TENANT_ID,
        "subscriptionId": SUBSCRIPTION_ID,
        "resourceGroupName": RESOURCE_GROUP,
        "deploymentMode": "Incremental",
        "storageAccountName": "stnacwormtest001",
        "containerName": "nac-worm-tenant",
        "encryptionScopeName": "nac-worm-tenant",
        "tags": {
            "owner": "notariat8",
            "purpose": "unlocked-worm-baseline",
        },
    }


def _attestation_measurement(
    attestations: dict[str, str] | None = None,
    *,
    combined: str | None = None,
) -> dict[str, object]:
    measured = dict(attestations or TOOLCHAIN)
    return {
        "status": "READY",
        "toolchain_attestations": measured,
        "toolchain_attestations_sha256": (
            combined
            if combined is not None
            else calculate_toolchain_attestations_sha256(measured)
        ),
        "reads_private_key": False,
        "executes_provider_requests": False,
    }


class PerformanceInfrastructureOwnerGateTests(unittest.TestCase):
    def build(self, parameters=None, worm_parameters=None):
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            side_effect=[
                (COMMIT, TREE, False),
                (COMMIT, TREE, False),
                (COMMIT, TREE, False),
            ],
        ), patch(
            "nac_bff.azure_performance_owner_gate."
            "build_activation_attestation_plan",
            return_value=_attestation_measurement(),
        ):
            return build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations=TOOLCHAIN,
                infrastructure_parameters=parameters or _parameters(),
                worm_baseline_parameters=(
                    worm_parameters or _worm_parameters()
                ),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

    def test_gate_binds_one_combined_infrastructure_and_live_action(self) -> None:
        result = self.build()

        self.assertEqual(result["status"], "READY")
        payload = result["owner_approval_payload"]
        self.assertEqual(payload["action"], ACTION)
        self.assertEqual(payload["approved_commit_sha"], COMMIT)
        self.assertEqual(payload["approved_tree_sha"], TREE)
        self.assertEqual(
            payload["toolchain_attestations_sha256"], TOOLCHAIN_SHA256
        )
        self.assertEqual(payload["workspace_id_exact"], "notary_team_01")
        self.assertEqual(payload["synthetic_reads_exact"], 500)
        self.assertEqual(
            payload["tenant_wide_sharepoint_baseline_claim"], "NOT_CLAIMED"
        )
        self.assertIn(
            "create_one_exact_zero_byte_coordination_blob_if_absent",
            payload["allowed_infrastructure_actions"],
        )
        self.assertIn("automatic_delete", payload["forbidden_actions"])
        self.assertEqual(
            result["owner_execution_bindings"]["owner_approval_body_sha256"],
            result["owner_comment_body_sha256"],
        )
        for key in (
            "contract_sha256",
            "expected_activation_hash",
            "phase_plan_sha256",
            "measurement_policy_sha256",
            "monitor_policy_sha256",
            "lease_policy_sha256",
        ):
            self.assertEqual(
                result["owner_execution_bindings"][key],
                payload[key],
            )
        self.assertEqual(result["boundaries"]["network_accessed"], False)
        self.assertEqual(result["boundaries"]["azure_resources_created"], 0)
        self.assertNotIn("11111111-2222", result["owner_comment_body"])
        self.assertNotIn("8.8.8.8", result["owner_comment_body"])
        self.assertEqual(
            _validate_owner_execution_bindings(
                result["owner_execution_bindings"]
            ),
            result["owner_execution_bindings"],
        )

    def test_parameter_change_changes_infrastructure_and_body_bindings(self) -> None:
        first = self.build()
        changed = _parameters()
        changed["allowedClientIpAddress"] = "1.1.1.1"
        second = self.build(changed)

        self.assertNotEqual(
            first["owner_approval_payload"]["infrastructure_binding_sha256"],
            second["owner_approval_payload"]["infrastructure_binding_sha256"],
        )
        self.assertNotEqual(
            first["owner_comment_body_sha256"],
            second["owner_comment_body_sha256"],
        )

    def test_worm_baseline_is_derived_and_bound_into_the_same_owner_body(self) -> None:
        first = self.build()
        changed = _worm_parameters()
        changed["containerName"] = "nac-worm-performance"
        second = self.build(worm_parameters=changed)

        payload = first["owner_approval_payload"]
        for key in (
            "worm_baseline_binding_sha256",
            "worm_baseline_compiled_arm_sha256",
            "worm_baseline_parameters_sha256",
            "worm_baseline_source_sha256",
            "deployment_sequence_sha256",
        ):
            self.assertRegex(payload[key], r"^[0-9a-f]{64}$")
            self.assertEqual(
                first["owner_execution_bindings"][key], payload[key]
            )
        self.assertNotEqual(
            first["owner_comment_body_sha256"],
            second["owner_comment_body_sha256"],
        )
        self.assertIn(
            "deploy_exact_unlocked_worm_baseline_without_policy_lock",
            payload["allowed_infrastructure_actions"],
        )
        self.assertIn(
            "irreversible_worm_policy_lock", payload["forbidden_actions"]
        )

    def test_worm_resource_id_cannot_drift_from_bound_baseline_parameters(self) -> None:
        changed = _parameters()
        changed["wormStorageAccountResourceId"] = (
            f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}/"
            "providers/Microsoft.Storage/storageAccounts/stnacwormother001"
        )
        result = self.build(changed)

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            result["error_code"], "WORM_BASELINE_RESOURCE_BINDING_MISMATCH"
        )
        self.assertFalse(result["boundaries"]["network_accessed"])

    def test_gate_binds_exact_infrastructure_safety_policy(self) -> None:
        policy_sha256 = "f" * 64
        with patch(
            "nac_bff.azure_performance_owner_gate."
            "infrastructure_safety_policy_sha256",
            return_value=policy_sha256,
        ):
            result = self.build()

        self.assertEqual(result["status"], "READY")
        self.assertEqual(
            result["owner_approval_payload"][
                "infrastructure_safety_policy_sha256"
            ],
            policy_sha256,
        )
        self.assertEqual(
            result["owner_execution_bindings"][
                "infrastructure_safety_policy_sha256"
            ],
            policy_sha256,
        )

    def test_gate_rejects_helper_body_digest_or_binding_drift(self) -> None:
        ready = self.build()
        with patch(
            "nac_bff.azure_performance_owner_gate.build_owner_comment",
            return_value={
                "body": ready["owner_comment_body"],
                "body_sha256": "f" * 64,
            },
        ):
            result = self.build()

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "OWNER_APPROVAL_BINDING_INVALID")
        self.assertFalse(result["boundaries"]["network_accessed"])

    def test_deployment_scope_and_tags_are_bound_fail_closed(self) -> None:
        for field, value in (
            ("tenantId", "11111111-2222-4333-8444-555555555555"),
            ("subscriptionId", "11111111-2222-4333-8444-555555555555"),
            ("resourceGroupName", "rg-other"),
            ("deploymentMode", "Complete"),
        ):
            with self.subTest(field=field):
                changed = _parameters()
                changed[field] = value
                result = self.build(changed)
                self.assertEqual(result["status"], "NOT_READY")
                self.assertEqual(
                    result["error_code"], "INFRASTRUCTURE_DEPLOYMENT_SCOPE_INVALID"
                )
                self.assertFalse(result["boundaries"]["network_accessed"])

        first = self.build()
        changed = _parameters()
        changed["tags"] = {"owner": "notariat8", "purpose": "changed"}
        second = self.build(changed)
        self.assertNotEqual(
            first["owner_approval_payload"]["infrastructure_binding_sha256"],
            second["owner_approval_payload"]["infrastructure_binding_sha256"],
        )

    def test_dirty_tree_fails_before_network(self) -> None:
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, True),
        ):
            result = build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations=TOOLCHAIN,
                infrastructure_parameters=_parameters(),
                worm_baseline_parameters=_worm_parameters(),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "SOURCE_TREE_NOT_CLEAN")
        self.assertEqual(result["boundaries"]["network_accessed"], False)

    def test_closing_snapshot_drift_fails_before_gate_or_lease_handoff(self) -> None:
        changed_tree = "4" * 40
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            side_effect=[
                (COMMIT, TREE, False),
                (COMMIT, changed_tree, False),
            ],
        ), patch(
            "nac_bff.azure_performance_owner_gate."
            "build_activation_attestation_plan",
            return_value=_attestation_measurement(),
        ):
            result = build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations=TOOLCHAIN,
                infrastructure_parameters=_parameters(),
                worm_baseline_parameters=_worm_parameters(),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            result["error_code"], "SOURCE_TREE_CHANGED_DURING_MEASUREMENT"
        )
        self.assertFalse(result["boundaries"]["network_accessed"])

    def test_effective_bicep_tags_are_bound_separately_from_owner_tags(self) -> None:
        result = self.build()
        bindings = result["redacted_parameter_bindings"]
        self.assertRegex(bindings["effective_tags_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(
            bindings["effective_tags_sha256"],
            result["owner_execution_bindings"][
                "infrastructure_parameters_sha256"
            ],
        )

    def test_incomplete_toolchain_manifest_fails_before_network(self) -> None:
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ):
            result = build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations={"azure_cli_toolchain_sha256": "1" * 64},
                infrastructure_parameters=_parameters(),
                worm_baseline_parameters=_worm_parameters(),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "TOOLCHAIN_ATTESTATIONS_INVALID")
        self.assertEqual(result["boundaries"]["network_accessed"], False)

    def test_binary_drift_fails_closed_before_network(self) -> None:
        drifted = dict(TOOLCHAIN)
        drifted["gh_cli_sha256"] = "f" * 64
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ), patch(
            "nac_bff.azure_performance_owner_gate."
            "build_activation_attestation_plan",
            return_value=_attestation_measurement(drifted),
        ) as measure:
            result = build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations=TOOLCHAIN,
                infrastructure_parameters=_parameters(),
                worm_baseline_parameters=_worm_parameters(),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            result["error_code"], "TOOLCHAIN_ATTESTATIONS_MISMATCH"
        )
        self.assertEqual(result["boundaries"]["network_accessed"], False)
        self.assertEqual(measure.call_count, 1)

    def test_toolchain_gate_digest_drift_fails_closed_before_network(self) -> None:
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ), patch(
            "nac_bff.azure_performance_owner_gate."
            "build_activation_attestation_plan",
            return_value=_attestation_measurement(combined="f" * 64),
        ):
            result = build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations=TOOLCHAIN,
                infrastructure_parameters=_parameters(),
                worm_baseline_parameters=_worm_parameters(),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(result["error_code"], "TOOLCHAIN_ATTESTATIONS_INVALID")
        self.assertEqual(result["boundaries"]["network_accessed"], False)

    def test_unmeasurable_current_toolchain_fails_closed_before_network(self) -> None:
        with patch(
            "nac_bff.azure_performance_owner_gate._git_snapshot",
            return_value=(COMMIT, TREE, False),
        ), patch(
            "nac_bff.azure_performance_owner_gate."
            "build_activation_attestation_plan",
            return_value={
                "status": "NOT_READY",
                "error": {"code": "EXECUTION_ATTESTATION_INPUT_UNTRUSTED"},
                "reads_private_key": False,
                "executes_provider_requests": False,
            },
        ):
            result = build_performance_infrastructure_owner_gate(
                REPO_ROOT,
                expected_activation_hash=ACTIVATION,
                toolchain_attestations=TOOLCHAIN,
                infrastructure_parameters=_parameters(),
                worm_baseline_parameters=_worm_parameters(),
                correlation_id="nac-bff-performance-20260803",
                monitor_window_anchor_utc=MONITOR_WINDOW_ANCHOR,
            )

        self.assertEqual(result["status"], "NOT_READY")
        self.assertEqual(
            result["error_code"], "TOOLCHAIN_ATTESTATIONS_NOT_READY"
        )
        self.assertEqual(result["boundaries"]["network_accessed"], False)

    def test_execution_remeasurement_detects_source_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = list(
                dict.fromkeys(
                    [CONTRACT_RELATIVE_PATH, *owner_gate.INFRASTRUCTURE_SOURCE_PATHS]
                )
            )
            for relative in paths:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / relative, target)
            with patch(
                "nac_bff.azure_performance_owner_gate._git_snapshot",
                return_value=(COMMIT, TREE, False),
            ), patch(
                "nac_bff.azure_performance_owner_gate."
                "build_activation_attestation_plan",
                return_value=_attestation_measurement(),
            ):
                first = measure_performance_infrastructure_approval(
                    root,
                    expected_activation_hash=ACTIVATION,
                    toolchain_attestations=TOOLCHAIN,
                    infrastructure_parameters=_parameters(),
                    worm_baseline_parameters=_worm_parameters(),
                )
                source = root / "src/nac_bff/azure_performance_runtime.py"
                source.write_text(
                    source.read_text(encoding="utf-8") + "\n# drift\n",
                    encoding="utf-8",
                )
                second = measure_performance_infrastructure_approval(
                    root,
                    expected_activation_hash=ACTIVATION,
                    toolchain_attestations=TOOLCHAIN,
                    infrastructure_parameters=_parameters(),
                    worm_baseline_parameters=_worm_parameters(),
                )
        self.assertNotEqual(
            first["infrastructure_approval"]["infrastructure_source_sha256"],
            second["infrastructure_approval"]["infrastructure_source_sha256"],
        )

    def test_source_bundle_covers_live_implementation_and_contracts(self) -> None:
        performance_sources = {
            path.relative_to(REPO_ROOT)
            for path in (REPO_ROOT / "src/nac_bff").glob(
                "azure_performance_*.py"
            )
        }
        expected = performance_sources | {
            Path("src/nac_bff/azure_live_commands.py"),
            Path("scripts/validate_m365_azure_bff_performance_acceptance.py"),
            Path("scripts/validate_nac_bff_performance_coordination_arm.py"),
            Path("workflows/contracts/m365-bff-performance-acceptance.contract.json"),
            Path(
                "workflows/verification-contracts/"
                "m365-bff-performance-acceptance.verification.json"
            ),
        }

        self.assertLessEqual(expected, set(owner_gate.INFRASTRUCTURE_SOURCE_PATHS))

    def test_each_capability_source_omission_or_mutation_changes_hash(
        self,
    ) -> None:
        capability_sources = {
            path.relative_to(REPO_ROOT)
            for path in (REPO_ROOT / "src/nac_bff").glob(
                "azure_performance_*.py"
            )
        } | {Path("src/nac_bff/azure_live_commands.py")}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in owner_gate.INFRASTRUCTURE_SOURCE_PATHS:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(REPO_ROOT / relative, target)
            baseline = owner_gate._source_bundle_sha256(root)

            for relative in sorted(capability_sources):
                with self.subTest(source=relative.as_posix(), change="mutation"):
                    target = root / relative
                    original = target.read_bytes()
                    target.write_bytes(original + b"\n# source mutation\n")
                    self.assertNotEqual(
                        owner_gate._source_bundle_sha256(root), baseline
                    )
                    target.write_bytes(original)

                with self.subTest(source=relative.as_posix(), change="omission"):
                    reduced_paths = tuple(
                        path
                        for path in owner_gate.INFRASTRUCTURE_SOURCE_PATHS
                        if path != relative
                    )
                    with patch.object(
                        owner_gate,
                        "INFRASTRUCTURE_SOURCE_PATHS",
                        reduced_paths,
                    ):
                        self.assertNotEqual(
                            owner_gate._source_bundle_sha256(root), baseline
                        )

    def test_git_snapshot_ignores_hostile_repository_environment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            measured = base / "measured"
            foreign = base / "foreign"
            measured_commit, measured_tree = self._create_git_repo(
                measured, "measured\n"
            )
            self._create_git_repo(foreign, "foreign\n")
            foreign_index = foreign / ".git/index"
            hostile = {
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(
                    foreign / ".git/objects"
                ),
                "GIT_ATTR_NOSYSTEM": "0",
                "GIT_CEILING_DIRECTORIES": str(base),
                "GIT_COMMON_DIR": str(foreign / ".git"),
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_GLOBAL": str(base / "hostile.gitconfig"),
                "GIT_CONFIG_KEY_0": "core.fsmonitor",
                "GIT_CONFIG_NOSYSTEM": "0",
                "GIT_CONFIG_PARAMETERS": "'core.hooksPath'='/tmp/hostile-hooks'",
                "GIT_CONFIG_SYSTEM": str(base / "hostile-system.gitconfig"),
                "GIT_CONFIG_VALUE_0": "/tmp/hostile-fsmonitor",
                "GIT_DIR": str(foreign / ".git"),
                "GIT_DISCOVERY_ACROSS_FILESYSTEM": "1",
                "GIT_EXEC_PATH": str(base / "hostile-git-exec"),
                "GIT_INDEX_FILE": str(foreign_index),
                "GIT_NAMESPACE": "hostile",
                "GIT_NO_REPLACE_OBJECTS": "0",
                "GIT_OBJECT_DIRECTORY": str(foreign / ".git/objects"),
                "GIT_OPTIONAL_LOCKS": "1",
                "GIT_PAGER": str(base / "hostile-pager"),
                "GIT_REPLACE_REF_BASE": "refs/hostile-replacements/",
                "GIT_SHALLOW_FILE": str(foreign / ".git/shallow"),
                "GIT_WORK_TREE": str(foreign),
            }
            with patch.dict(os.environ, hostile, clear=False), patch.object(
                owner_gate.subprocess, "run", wraps=subprocess.run
            ) as git_run:
                snapshot = owner_gate._git_snapshot(measured)

        self.assertEqual(snapshot, (measured_commit, measured_tree, False))
        self.assertEqual(git_run.call_count, 3)
        for call in git_run.call_args_list:
            command = call.args[0]
            environment = call.kwargs["env"]
            self.assertEqual(command[0], "/usr/bin/git")
            self.assertIn("--no-replace-objects", command)
            self.assertIn("core.hooksPath=/dev/null", command)
            self.assertIn("core.fsmonitor=false", command)
            command_suffix = tuple(command[command.index("-C") + 2 :])
            self.assertIn(command_suffix, owner_gate._GIT_ALLOWED_ARGV)
            self.assertFalse(call.kwargs["shell"])
            self.assertEqual(set(environment), set(owner_gate._GIT_ENV))
            for name, hostile_value in hostile.items():
                if name in owner_gate._GIT_ENV:
                    self.assertEqual(environment[name], owner_gate._GIT_ENV[name])
                    self.assertNotEqual(environment[name], hostile_value)
                else:
                    self.assertNotIn(name, environment)
            self.assertEqual(environment["GIT_CONFIG_GLOBAL"], os.devnull)
            self.assertEqual(environment["GIT_CONFIG_SYSTEM"], os.devnull)
            self.assertEqual(environment["GIT_CONFIG_NOSYSTEM"], "1")

    def test_git_snapshot_does_not_use_hostile_git_dir_for_non_repo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            measured = base / "not-a-repository"
            measured.mkdir()
            foreign = base / "foreign"
            self._create_git_repo(foreign, "foreign\n")
            hostile = {
                "GIT_DIR": str(foreign / ".git"),
                "GIT_WORK_TREE": str(foreign),
            }
            with patch.dict(os.environ, hostile, clear=False), self.assertRaisesRegex(
                ValueError, "SOURCE_CONTROL_SNAPSHOT_INVALID"
            ):
                owner_gate._git_snapshot(measured)

    @staticmethod
    def _create_git_repo(root: Path, content: str) -> tuple[str, str]:
        root.mkdir()
        subprocess.run(
            ["/usr/bin/git", "init", "--quiet", str(root)],
            check=True,
            capture_output=True,
        )
        (root / "source.txt").write_text(content, encoding="utf-8")
        subprocess.run(
            ["/usr/bin/git", "-C", str(root), "add", "source.txt"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "/usr/bin/git",
                "-C",
                str(root),
                "-c",
                "user.name=NaC Tests",
                "-c",
                "user.email=nac-tests@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "snapshot",
            ],
            check=True,
            capture_output=True,
        )

        def output(*arguments: str) -> str:
            result = subprocess.run(
                ["/usr/bin/git", "-C", str(root), *arguments],
                check=True,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip()

        return output("rev-parse", "HEAD"), output("rev-parse", "HEAD^{tree}")

    def test_cli_exposes_offline_combined_owner_gate(self) -> None:
        ready = self.build()
        with tempfile.TemporaryDirectory() as directory:
            parameter_path = Path(directory) / "parameters.json"
            parameter_path.write_text(json.dumps(_parameters()), encoding="utf-8")
            worm_parameter_path = Path(directory) / "worm-parameters.json"
            worm_parameter_path.write_text(
                json.dumps(_worm_parameters()), encoding="utf-8"
            )
            toolchain_path = Path(directory) / "toolchain.json"
            toolchain_path.write_text(json.dumps(TOOLCHAIN), encoding="utf-8")
            with patch(
                "nac_bff.azure_performance_owner_gate."
                "build_performance_infrastructure_owner_gate",
                return_value=ready,
            ), patch("builtins.print") as output:
                result = cli.main(
                    [
                        "m365",
                        "teams-sharepoint",
                        "bff-performance-infrastructure-owner-gate",
                        "--repo-root",
                        str(REPO_ROOT),
                        "--expected-activation-hash",
                        ACTIVATION,
                        "--correlation-id",
                        "nac-bff-performance-20260803",
                        "--monitor-window-anchor-utc",
                        MONITOR_WINDOW_ANCHOR,
                        "--toolchain-attestations-json",
                        str(toolchain_path),
                        "--infrastructure-parameters-json",
                        str(parameter_path),
                        "--worm-baseline-parameters-json",
                        str(worm_parameter_path),
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(result, 0)
        rendered = output.call_args.args[0]
        self.assertEqual(json.loads(rendered)["status"], "READY")


if __name__ == "__main__":
    unittest.main()
