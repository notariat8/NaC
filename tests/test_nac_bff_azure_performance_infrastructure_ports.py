from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import nac_bff.azure_performance_acceptance as acceptance
import nac_bff.azure_performance_infrastructure_ports as ports
from nac_bff.azure_performance_acceptance import (
    OWNER_ACTION,
    PerformanceExecutionAuthorization,
    build_owner_comment,
    build_performance_acceptance_plan,
)
from nac_bff.azure_performance_infrastructure_ports import (
    AzureCliPerformanceInfrastructureCommandExecutor,
    AzurePerformanceInfrastructurePortError,
    DEPLOYMENT_SEQUENCE,
    OwnerBoundInfrastructureDeploymentAuthority,
    PerformanceCoordinationDeploymentPort,
    UnlockedWormBaselineDeploymentPort,
    UnlockedWormBaselineReadbackPort,
)
from nac_bff.azure_live_commands import AzureCliAdapter
from nac_bff.azure_performance_infrastructure_safety import (
    ALLOWED_DATA_ACTIONS,
    CONTAINER_NAME,
    effective_coordination_tags,
    exact_lease_blob_condition,
)


TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
RESOURCE_GROUP = "rg-nac-bff-test"
OWNER_BINDING = "9" * 64
CONTRACT_SHA256 = "1" * 64
ACTIVATION_SHA256 = "2" * 64
ANCHOR = "2026-08-04T12:00:00Z"
CORRELATION_ID = "issue-735-offline-test"
WORM_NAME = "stnacwormoffline001"
COORDINATION_NAME = "stnacperflease001"
BFF_NAME = "stnacbffoffline001"
PRINCIPAL_ID = "11111111-2222-4333-8444-555555555555"
TARGET = build_performance_acceptance_plan(
    ACTIVATION_SHA256, CONTRACT_SHA256
)["target_binding_sha256"]
RESOURCE_GROUP_SCOPE = f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
WORM_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Storage/storageAccounts/{WORM_NAME}"
)
BFF_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Storage/storageAccounts/{BFF_NAME}"
)
COORDINATION_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Storage/storageAccounts/"
    f"{COORDINATION_NAME}"
)
CONTAINER_ID = (
    f"{COORDINATION_ID}/blobServices/default/containers/{CONTAINER_NAME}"
)
ROLE_DEFINITION_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/"
    "roleDefinitions/44444444-4444-4444-8444-444444444444"
)
ROLE_ASSIGNMENT_ID = (
    f"{CONTAINER_ID}/providers/Microsoft.Authorization/roleAssignments/"
    "55555555-5555-4555-8555-555555555555"
)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _infra_parameters() -> dict[str, object]:
    return {
        "location": "germanywestcentral",
        "storageAccountName": COORDINATION_NAME,
        "bffStorageAccountResourceId": BFF_ID,
        "wormStorageAccountResourceId": WORM_ID,
        "provisionerPrincipalId": PRINCIPAL_ID,
        "allowedClientIpAddress": "8.8.8.8",
        "targetBindingSha256": TARGET,
        "tenantId": TENANT_ID,
        "subscriptionId": SUBSCRIPTION_ID,
        "resourceGroupName": RESOURCE_GROUP,
        "deploymentMode": "Incremental",
        "tags": {"owner": "issue-735", "purpose": "performance-test"},
    }


def _worm_parameters() -> dict[str, object]:
    return {
        "location": "germanywestcentral",
        "tenantId": TENANT_ID,
        "subscriptionId": SUBSCRIPTION_ID,
        "resourceGroupName": RESOURCE_GROUP,
        "deploymentMode": "Incremental",
        "storageAccountName": WORM_NAME,
        "containerName": "nac-worm-tenant",
        "encryptionScopeName": "nac-worm-tenant",
        "tags": {"owner": "issue-735", "purpose": "unlocked-worm-baseline"},
    }


def _approval() -> dict[str, str]:
    value = {
        "approved_commit_sha": "a" * 40,
        "approved_tree_sha": "b" * 40,
        "toolchain_attestations_sha256": "3" * 64,
        "infrastructure_binding_sha256": "4" * 64,
        "infrastructure_parameters_sha256": _sha256_json(_infra_parameters()),
        "infrastructure_source_sha256": "5" * 64,
        "lease_bootstrap_policy_sha256": "6" * 64,
        "infrastructure_safety_policy_sha256": "7" * 64,
        "worm_baseline_binding_sha256": "8" * 64,
        "worm_baseline_compiled_arm_sha256": hashlib.sha256(
            (ROOT / ports.WORM_TEMPLATE_RELATIVE_PATH).read_bytes()
        ).hexdigest(),
        "worm_baseline_parameters_sha256": _sha256_json(_worm_parameters()),
        "worm_baseline_source_sha256": "c" * 64,
    }
    value["deployment_sequence_sha256"] = _sha256_json(
        {
            "infrastructure_binding_sha256": value[
                "infrastructure_binding_sha256"
            ],
            "sequence": list(DEPLOYMENT_SEQUENCE),
            "worm_baseline_binding_sha256": value[
                "worm_baseline_binding_sha256"
            ],
        }
    )
    return value


def _authorization(owner_body_sha256: str) -> PerformanceExecutionAuthorization:
    authorization = object.__new__(PerformanceExecutionAuthorization)
    values = {
        "status": "VERIFIED",
        "owner_login": "ofunk",
        "owner_approval_reference_sha256": "d" * 64,
        "owner_approval_body_sha256": owner_body_sha256,
        "action": OWNER_ACTION,
        "correlation_id": CORRELATION_ID,
        "contract_sha256": CONTRACT_SHA256,
        "activation_hash": ACTIVATION_SHA256,
        "activation_receipt_sha256": "e" * 64,
        "activation_evidence_sha256": "f" * 64,
        "target_binding_sha256": TARGET,
        "measurement_preflight_sha256": "0" * 64,
        "phase_plan_sha256": build_performance_acceptance_plan(
            ACTIVATION_SHA256, CONTRACT_SHA256
        )["phase_plan_sha256"],
        "monitor_window_anchor_sha256": hashlib.sha256(
            ANCHOR.encode("ascii")
        ).hexdigest(),
        "interruption_terminalization_status": (
            "VERIFIED_BY_COMMITTED_ACTIVATION_RECEIPT"
        ),
        "_seal": acceptance._EXECUTION_AUTHORIZATION_SEAL,
    }
    for key, value in values.items():
        object.__setattr__(authorization, key, value)
    acceptance._ISSUED_EXECUTION_AUTHORIZATIONS[id(authorization)] = authorization
    return authorization


def _arm_envelopes(values: dict[str, object]) -> dict[str, dict[str, object]]:
    return {key: {"value": value} for key, value in values.items()}


class _FakeAzureExecutor:
    def __init__(self) -> None:
        self.commands: list[ports.BoundAzureCliCommand] = []
        self.bound_artifact_digests: list[tuple[str, str]] = []
        self.locked = False
        self.worm_output_drift = False
        self.fail_operation: str | None = None
        self.worm_deployment: dict[str, object] | None = None

    def execute(
        self, command: ports.BoundAzureCliCommand
    ) -> dict[str, object]:
        command._assert_issued()
        self.commands.append(command)
        for artifact in command.artifacts:
            self.bound_artifact_digests.append(
                (
                    artifact.sha256,
                    hashlib.sha256(artifact.path.read_bytes()).hexdigest(),
                )
            )
        if command.operation == self.fail_operation:
            return {"ok": False, "code": "AZURE_CLI_COMMAND_FAILED"}
        if command.operation == DEPLOYMENT_SEQUENCE[0]:
            parameters = self._bound_parameters(command)
            self.worm_deployment = self._worm_deployment(command, parameters)
            if self.worm_output_drift:
                self.worm_deployment["properties"]["outputs"]["liveStatus"][
                    "value"
                ] = "DRIFTED"
            return self._ok(self.worm_deployment)
        if command.operation == "worm_account_readback":
            return self._ok(
                {
                    "environmentName": "AzureCloud",
                    "tenantId": TENANT_ID,
                    "id": SUBSCRIPTION_ID,
                    "state": "Enabled",
                }
            )
        if command.operation == "worm_deployment_readback":
            assert self.worm_deployment is not None
            return self._ok(self.worm_deployment)
        if command.operation == "worm_storage_readback":
            return self._ok(self._worm_storage())
        if command.operation == "worm_container_readback":
            return self._ok(self._worm_container())
        if command.operation == "worm_policy_readback":
            return self._ok(self._worm_policy())
        if command.operation == DEPLOYMENT_SEQUENCE[2]:
            parameters = self._bound_parameters(command)
            return self._ok(self._coordination_deployment(command, parameters))
        raise AssertionError(f"unexpected operation: {command.operation}")

    @staticmethod
    def _ok(data: object) -> dict[str, object]:
        return {"ok": True, "code": "AZURE_CLI_OK", "data": data}

    @staticmethod
    def _bound_parameters(
        command: ports.BoundAzureCliCommand,
    ) -> dict[str, object]:
        self_artifact = next(
            item for item in command.artifacts if item.path.name == "main.parameters.json"
        )
        content = self_artifact.path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == self_artifact.sha256
        payload = json.loads(content)
        return {
            key: envelope["value"]
            for key, envelope in payload["parameters"].items()
        }

    @staticmethod
    def _deployment_name(command: ports.BoundAzureCliCommand) -> str:
        return command.argv[command.argv.index("--name") + 1]

    def _worm_deployment(
        self,
        command: ports.BoundAzureCliCommand,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        name = self._deployment_name(command)
        container_id = (
            f"{WORM_ID}/blobServices/default/containers/"
            f"{parameters['containerName']}"
        )
        outputs = {
            "offlineStatus": "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE",
            "liveStatus": "BLOCKED_PENDING_S7_APPROVAL",
            "lockActionStatus": "OWNER_GATED_NOT_EXECUTED",
            "lockTargetResourceId": f"{container_id}/immutabilityPolicies/default",
            "configuredContainerName": parameters["containerName"],
            "configuredEncryptionScope": parameters["encryptionScopeName"],
            "providerContextBindingSource": (
                "azure-subscription-resource-tenant-readback"
            ),
            "cmkIdentityResourceId": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.ManagedIdentity/"
                "userAssignedIdentities/id-nac-worm-cmk-testbinding"
            ),
            "writerIdentityResourceId": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.ManagedIdentity/"
                "userAssignedIdentities/id-nac-worm-writer-testbinding"
            ),
            "writerDataRoleDefinitionId": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/"
                "roleDefinitions/22222222-2222-4222-8222-222222222222"
            ),
            "writerManagementReadRoleDefinitionId": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/"
                "roleDefinitions/33333333-3333-4333-8333-333333333333"
            ),
            "deploymentScopeBinding": (
                f"{TENANT_ID}/{SUBSCRIPTION_ID}/{RESOURCE_GROUP}/Incremental"
            ),
            "deploymentModeBinding": "Incremental",
        }
        return {
            "id": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Resources/"
                f"deployments/{name}"
            ),
            "name": name,
            "properties": {
                "provisioningState": "Succeeded",
                "parameters": _arm_envelopes(parameters),
                "outputs": _arm_envelopes(outputs),
            },
        }

    @staticmethod
    def _worm_storage() -> dict[str, object]:
        return {
            "id": WORM_ID,
            "name": WORM_NAME,
            "type": "Microsoft.Storage/storageAccounts",
            "location": "germanywestcentral",
            "kind": "StorageV2",
            "properties": {
                "allowBlobPublicAccess": False,
                "allowCrossTenantReplication": False,
                "allowSharedKeyAccess": False,
                "defaultToOAuthAuthentication": True,
                "minimumTlsVersion": "TLS1_2",
                "publicNetworkAccess": "Disabled",
                "supportsHttpsTrafficOnly": True,
            },
        }

    @staticmethod
    def _worm_container() -> dict[str, object]:
        container_id = f"{WORM_ID}/blobServices/default/containers/nac-worm-tenant"
        return {
            "id": container_id,
            "name": "nac-worm-tenant",
            "properties": {
                "defaultEncryptionScope": "nac-worm-tenant",
                "denyEncryptionScopeOverride": True,
                "publicAccess": "None",
                "immutableStorageWithVersioning": {"enabled": True},
                "metadata": {
                    "nac_schema_version": "nac.azure-blob-worm-container/v0.4",
                    "nac_status": "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE",
                    "provider_context_binding_source": (
                        "azure-subscription-resource-tenant-readback"
                    ),
                    "provider_binding_material": (
                        "runtime-readback-not-template-metadata"
                    ),
                    "legal_hold_capability_source": "container-policy-properties",
                    "minimum_retention_days": "3653",
                    "encryption_scope": "nac-worm-tenant",
                    "encryption_key_source": "Microsoft.Keyvault",
                },
            },
        }

    def _worm_policy(self) -> dict[str, object]:
        return {
            "id": (
                f"{WORM_ID}/blobServices/default/containers/nac-worm-tenant/"
                "immutabilityPolicies/default"
            ),
            "name": "default",
            "properties": {
                "state": "Locked" if self.locked else "Unlocked",
                "immutabilityPeriodSinceCreationInDays": 3653,
                "allowProtectedAppendWrites": False,
                "allowProtectedAppendWritesAll": False,
            },
        }

    def _coordination_deployment(
        self,
        command: ports.BoundAzureCliCommand,
        parameters: dict[str, object],
    ) -> dict[str, object]:
        name = self._deployment_name(command)
        container_id = (
            f"{COORDINATION_ID}/blobServices/default/containers/{CONTAINER_NAME}"
        )
        outputs = {
            "contractSchemaVersion": "nac.azure-bff-performance-coordination/v1",
            "storageAccountName": COORDINATION_NAME,
            "storageAccountResourceId": COORDINATION_ID,
            "effectiveTags": effective_coordination_tags(
                parameters["tags"], TARGET
            ),
            "bffStorageAccountResourceIdBinding": BFF_ID,
            "bffStorageAccountNameBinding": BFF_NAME,
            "wormStorageAccountResourceIdBinding": WORM_ID,
            "wormStorageAccountNameBinding": WORM_NAME,
            "leaseContainerName": CONTAINER_NAME,
            "leaseContainerResourceId": container_id,
            "leaseBlobPath": f"locks/{TARGET}.lock",
            "leaseBlobUri": (
                f"https://{COORDINATION_NAME}.blob.core.windows.net/"
                f"{CONTAINER_NAME}/locks/{TARGET}.lock"
            ),
            "requiredLeaseBlobType": "BlockBlob",
            "requiredLeaseBlobContentLength": 0,
            "targetBindingSha256": TARGET,
            "leaseDataRoleDefinitionId": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/"
                "roleDefinitions/44444444-4444-4444-8444-444444444444"
            ),
            "provisionerLeaseRoleAssignmentId": (
                f"{container_id}/providers/Microsoft.Authorization/roleAssignments/"
                "55555555-5555-4555-8555-555555555555"
            ),
            "exactLeaseBlobCondition": exact_lease_blob_condition(TARGET),
            "allowedDataActions": sorted(ALLOWED_DATA_ACTIONS),
            "deploymentScopeBinding": (
                f"{TENANT_ID}/{SUBSCRIPTION_ID}/{RESOURCE_GROUP}"
            ),
            "blobBootstrapRequired": True,
            "blobBootstrapExecutedByTemplate": False,
            "azureRbacWriteAuthorizedOperations": [
                "blob-create",
                "blob-overwrite",
                "lease-acquire",
                "lease-release",
                "lease-break",
            ],
            "azureRbacOperationRestrictionEnforced": False,
            "operationRestrictionDefenseInDepth": [
                "dedicated-storage-account",
                "exact-container-and-blob-path-abac",
                "sealed-bootstrap-and-runtime-application-apis",
            ],
            "principalSeparationMode": (
                "SINGLE_OWNER_BOUND_PRINCIPAL_FOR_BOOTSTRAP_AND_RUNTIME"
            ),
        }
        return {
            "id": (
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Resources/"
                f"deployments/{name}"
            ),
            "name": name,
            "properties": {
                "provisioningState": "Succeeded",
                "parameters": _arm_envelopes(parameters),
                "outputs": _arm_envelopes(outputs),
            },
        }


class AzurePerformanceInfrastructurePortsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.addCleanup(acceptance._ISSUED_EXECUTION_AUTHORIZATIONS.clear)
        self.addCleanup(ports._ISSUED_AUTHORITIES.clear)
        self.addCleanup(ports._AUTHORITY_STATES.clear)
        self.addCleanup(ports._ISSUED_COMMANDS.clear)
        self.addCleanup(ports._WORM_RECEIPTS.clear)
        self.addCleanup(ports._WORM_READBACKS.clear)
        self.addCleanup(ports._COORDINATION_RECEIPTS.clear)

    def authority(
        self, *, owner_body_override: str | None = None
    ) -> OwnerBoundInfrastructureDeploymentAuthority:
        approval = _approval()
        comment = build_owner_comment(
            CONTRACT_SHA256,
            ACTIVATION_SHA256,
            CORRELATION_ID,
            approval,
            ANCHOR,
        )["body"]
        authorization = _authorization(
            hashlib.sha256(comment.encode("utf-8")).hexdigest()
        )
        measurement = {
            "contract_sha256": CONTRACT_SHA256,
            "parameters": _infra_parameters(),
            "infrastructure_approval": approval,
        }
        with patch(
            "nac_bff.azure_performance_owner_gate."
            "measure_performance_infrastructure_approval",
            return_value=measurement,
        ):
            return OwnerBoundInfrastructureDeploymentAuthority.issue_for_exact_sequence(
                repo_root=ROOT,
                authorization=authorization,
                owner_comment_body=owner_body_override or comment,
                infrastructure_approval=approval,
                toolchain_attestations={"unused": "offline-test"},
                infrastructure_parameters=_infra_parameters(),
                worm_baseline_parameters=_worm_parameters(),
            )

    def run_sequence(self, executor: _FakeAzureExecutor | None = None):
        executor = executor or _FakeAzureExecutor()
        authority = self.authority()
        worm_receipt = UnlockedWormBaselineDeploymentPort(executor).deploy(authority)
        worm_readback = UnlockedWormBaselineReadbackPort(
            executor
        ).verify_exact_unlocked_baseline(authority, worm_receipt)
        coordination_receipt = PerformanceCoordinationDeploymentPort(
            executor
        ).deploy(authority, worm_readback)
        return authority, executor, worm_receipt, worm_readback, coordination_receipt

    def test_exact_owner_bound_sequence_succeeds_offline(self) -> None:
        with (
            patch.object(socket, "socket", side_effect=AssertionError("network")),
            patch.object(
                subprocess, "run", side_effect=AssertionError("subprocess")
            ),
        ):
            authority, executor, worm_receipt, readback, coordination = (
                self.run_sequence()
            )

        self.assertEqual(readback.policy_state, "Unlocked")
        self.assertEqual(
            worm_receipt.owner_binding_sha256,
            coordination.owner_binding_sha256,
        )
        self.assertEqual(
            coordination.coordination_storage_account_resource_id,
            COORDINATION_ID,
        )
        self.assertEqual(
            coordination.lease_container_resource_id,
            CONTAINER_ID,
        )
        self.assertEqual(
            coordination.lease_data_role_definition_id,
            ROLE_DEFINITION_ID,
        )
        self.assertEqual(
            coordination.provisioner_lease_role_assignment_id,
            ROLE_ASSIGNMENT_ID,
        )
        self.assertEqual(
            [command.operation for command in executor.commands],
            [
                DEPLOYMENT_SEQUENCE[0],
                "worm_account_readback",
                "worm_deployment_readback",
                "worm_storage_readback",
                "worm_container_readback",
                "worm_policy_readback",
                DEPLOYMENT_SEQUENCE[2],
            ],
        )
        for command in executor.commands:
            self.assertEqual(command.argv_sha256, _sha256_json(list(command.argv)))
            self.assertNotIn("/lock?", " ".join(command.argv).casefold())
        for command in (executor.commands[0], executor.commands[-1]):
            self.assertFalse(command.read_only)
            self.assertEqual(len(command.artifacts), 2)
        self.assertEqual(len(executor.bound_artifact_digests), 4)
        self.assertTrue(
            all(expected == actual for expected, actual in executor.bound_artifact_digests)
        )
        self.assertIsInstance(authority, OwnerBoundInfrastructureDeploymentAuthority)

    def test_wrong_order_and_replay_permanently_burn_authority(self) -> None:
        executor = _FakeAzureExecutor()
        authority = self.authority()
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "INFRASTRUCTURE_DEPLOYMENT_SEQUENCE_INVALID",
        ):
            PerformanceCoordinationDeploymentPort(executor).deploy(
                authority, object()  # type: ignore[arg-type]
            )
        self.assertEqual(executor.commands, [])
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "INFRASTRUCTURE_DEPLOYMENT_SEQUENCE_INVALID",
        ):
            UnlockedWormBaselineDeploymentPort(executor).deploy(authority)

        authority, executor, _, readback, _ = self.run_sequence()
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "INFRASTRUCTURE_DEPLOYMENT_SEQUENCE_INVALID",
        ):
            PerformanceCoordinationDeploymentPort(executor).deploy(
                authority, readback
            )

    def test_locked_policy_is_rejected_and_coordination_never_runs(self) -> None:
        executor = _FakeAzureExecutor()
        executor.locked = True
        authority = self.authority()
        receipt = UnlockedWormBaselineDeploymentPort(executor).deploy(authority)

        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "WORM_BASELINE_NOT_EXACTLY_UNLOCKED",
        ):
            UnlockedWormBaselineReadbackPort(
                executor
            ).verify_exact_unlocked_baseline(authority, receipt)

        self.assertNotIn(
            DEPLOYMENT_SEQUENCE[2],
            [command.operation for command in executor.commands],
        )
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "INFRASTRUCTURE_DEPLOYMENT_SEQUENCE_INVALID",
        ):
            UnlockedWormBaselineReadbackPort(
                executor
            ).verify_exact_unlocked_baseline(authority, receipt)

    def test_output_drift_and_provider_failure_return_only_fixed_codes(self) -> None:
        drift = _FakeAzureExecutor()
        drift.worm_output_drift = True
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "^WORM_BASELINE_OUTPUTS_INVALID$",
        ):
            UnlockedWormBaselineDeploymentPort(drift).deploy(self.authority())

        failure = _FakeAzureExecutor()
        failure.fail_operation = DEPLOYMENT_SEQUENCE[0]
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "^WORM_BASELINE_DEPLOYMENT_FAILED$",
        ) as caught:
            UnlockedWormBaselineDeploymentPort(failure).deploy(self.authority())
        self.assertNotIn("provider", str(caught.exception).casefold())

    def test_owner_comment_or_measured_binding_drift_is_rejected_offline(self) -> None:
        approval = _approval()
        comment = build_owner_comment(
            CONTRACT_SHA256,
            ACTIVATION_SHA256,
            CORRELATION_ID,
            approval,
            ANCHOR,
        )["body"]
        drifted = comment.replace(
            '"deployment_sequence_sha256":"',
            '"deployment_sequence_sha256":"f',
            1,
        )
        authorization = _authorization(
            hashlib.sha256(drifted.encode("utf-8")).hexdigest()
        )
        measurement = {
            "contract_sha256": CONTRACT_SHA256,
            "parameters": _infra_parameters(),
            "infrastructure_approval": approval,
        }
        with patch(
            "nac_bff.azure_performance_owner_gate."
            "measure_performance_infrastructure_approval",
            return_value=measurement,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "OWNER_BOUND_INFRASTRUCTURE_AUTHORITY_INVALID",
        ):
            OwnerBoundInfrastructureDeploymentAuthority.issue_for_exact_sequence(
                repo_root=ROOT,
                authorization=authorization,
                owner_comment_body=drifted,
                infrastructure_approval=approval,
                toolchain_attestations={},
                infrastructure_parameters=_infra_parameters(),
                worm_baseline_parameters=_worm_parameters(),
            )

    def test_forged_receipt_is_rejected_before_readback(self) -> None:
        executor = _FakeAzureExecutor()
        authority = self.authority()
        UnlockedWormBaselineDeploymentPort(executor).deploy(authority)

        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "WORM_BASELINE_DEPLOYMENT_RECEIPT_INVALID",
        ):
            UnlockedWormBaselineReadbackPort(
                executor
            ).verify_exact_unlocked_baseline(
                authority, object()  # type: ignore[arg-type]
            )
        self.assertEqual(
            [item.operation for item in executor.commands],
            [DEPLOYMENT_SEQUENCE[0]],
        )

    def test_public_capabilities_and_commands_cannot_be_constructed(self) -> None:
        for capability in (
            ports.BoundAzureCliCommand,
            ports.OwnerBoundInfrastructureDeploymentAuthority,
            ports.UnlockedWormBaselineDeploymentReceipt,
            ports.VerifiedUnlockedWormBaseline,
            ports.PerformanceCoordinationDeploymentReceipt,
        ):
            with self.subTest(capability=capability), self.assertRaises(TypeError):
                capability()

    def test_existing_adapter_requires_sealed_exact_rest_integration(self) -> None:
        executor = ports.AzureCliPerformanceInfrastructureCommandExecutor(
            ports.AzureCliAdapter(binary="/must/not/execute")
        )
        command = ports._read_command(
            "worm_policy_readback",
            (
                "rest",
                "--method",
                "get",
                "--url",
                f"https://management.azure.com{WORM_ID}/blobServices/default/"
                "containers/nac-worm-tenant/immutabilityPolicies/default"
                "?api-version=2023-05-01",
            ),
        )

        with self.assertRaisesRegex(
            AzurePerformanceInfrastructurePortError,
            "AZURE_EXACT_REST_BOUNDARY_INTEGRATION_REQUIRED",
        ):
            executor.execute(command)

    def test_sealed_azure_cli_executes_only_issued_exact_rest_command(self) -> None:
        azure = AzureCliAdapter(binary="/must/not/execute")
        executor = AzureCliPerformanceInfrastructureCommandExecutor(
            azure, exact_rest_executor=azure
        )
        command = ports._read_command(
            "worm_policy_readback",
            (
                "rest",
                "--method",
                "get",
                "--url",
                f"https://management.azure.com{WORM_ID}/blobServices/default/"
                "containers/nac-worm-tenant/immutabilityPolicies/default"
                "?api-version=2023-05-01",
            ),
        )
        expected = {"ok": True, "code": "AZURE_CLI_OK", "data": {}}

        with patch(
            "nac_bff.azure_live_commands._run_azure_cli",
            return_value=expected,
        ) as execute:
            self.assertEqual(executor.execute(command), expected)

        self.assertIs(execute.call_args.kwargs["_performance_infrastructure_command"], command)
        self.assertIsNotNone(
            execute.call_args.kwargs[
                "_performance_infrastructure_rest_authority"
            ]
        )
        self.assertEqual(azure.execute_exact_rest(object())["code"], "AZURE_CLI_COMMAND_BLOCKED")


if __name__ == "__main__":
    unittest.main()
