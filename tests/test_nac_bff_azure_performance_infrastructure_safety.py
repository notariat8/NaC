from copy import deepcopy
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

from nac_bff.azure_activation_attestations import TOOLCHAIN_ATTESTATION_FIELDS
from nac_bff.azure_performance_infrastructure_safety import (
    BROKER_ALLOWED_DATA_ACTIONS,
    AzurePerformanceInfrastructureReadbackAdapter,
    AzurePerformanceInfrastructureRestartReceiptStore,
    AzurePerformanceInfrastructureSafetyError,
    AzurePerformanceInfrastructureSafetyVerification,
    CONTAINER_NAME,
    begin_azure_performance_infrastructure_readback_session,
    build_infrastructure_restart_receipt_binding,
    effective_coordination_tags,
    exact_broker_lease_blob_condition,
    validate_infrastructure_safety_evidence,
    verify_azure_performance_infrastructure_safety,
)


SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
BROKER_PRINCIPAL_ID = "abcdef01-2222-4333-8444-555555555555"
BROKER_GROUP_ID = "abcdef02-2222-4333-8444-555555555555"
CALLER_PRINCIPAL_ID = "abcdef03-2222-4333-8444-555555555555"
TARGET_BINDING = "a" * 64
OWNER_BINDING = "8" * 64
TOOLCHAIN_BINDING = "7" * 64
PACKAGE_SHA256 = "5" * 64
TICKET_CERTIFICATE_SHA256 = "6" * 64
LOCATION = "germanywestcentral"
RESOURCE_GROUP = "rg-nac-bff-test"
COORDINATION_NAME = "stnacperflease001"
OUTBOUND_IP_ADDRESSES = ["8.8.8.8"]
RUNTIME_UAMI_PRINCIPAL_ID = "aaaaaaaa-2222-4333-8444-555555555555"
RESOURCE_GROUP_SCOPE = f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"
COORDINATION_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Storage/storageAccounts/"
    f"{COORDINATION_NAME}"
)
BFF_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Storage/storageAccounts/"
    "stnacbffoffline001"
)
WORM_ID = (
    f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/rg-nac-worm/providers/"
    "Microsoft.Storage/storageAccounts/stnacwormoffline001"
)
FUNCTION_APP_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Web/sites/fn-nac-bff-test"
)
ROOT_MG = f"/providers/Microsoft.Management/managementGroups/{TENANT_ID}"
CHILD_MG = "/providers/Microsoft.Management/managementGroups/nac-test-platform"
CONTAINER_SCOPE = (
    f"{COORDINATION_ID}/blobServices/default/containers/{CONTAINER_NAME}"
)
BLOB_SERVICE_SCOPE = f"{COORDINATION_ID}/blobServices/default"
ROLE_DEFINITION_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/roleDefinitions/"
    "22222222-2222-4333-8444-555555555555"
)
ROLE_ASSIGNMENT_ID = (
    f"{CONTAINER_SCOPE}/providers/Microsoft.Authorization/roleAssignments/"
    "33333333-2222-4333-8444-555555555555"
)
DEPLOYMENT_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Resources/deployments/"
    "nac-bff-performance-coordination"
)
TAGS = {"environment": "test", "system": "nac"}
SESSION_AT = datetime(2026, 8, 3, 12, 0, 0, tzinfo=UTC)
NAME_AT = datetime(2026, 8, 3, 12, 0, 1, tzinfo=UTC)
DEPLOYMENT_AT = datetime(2026, 8, 3, 12, 0, 4, tzinfo=UTC)
POST_AT = datetime(2026, 8, 3, 12, 1, 1, tzinfo=UTC)
VERIFY_AT = datetime(2026, 8, 3, 12, 5, 0, tzinfo=UTC)
ADAPTER_TOOLCHAIN = {
    name: ("a" if name == "azure_cli_toolchain_sha256" else "b") * 64
    for name in TOOLCHAIN_ATTESTATION_FIELDS
}


class _FdBackedTestRuntime:
    def __init__(self, executable: Path) -> None:
        self._descriptor = os.open(executable, os.O_RDONLY)
        self.pass_fds = (self._descriptor,)

    def command(self, azure_argv: list[str]) -> list[str]:
        return [f"/proc/self/fd/{self._descriptor}", *azure_argv]

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        os.close(self._descriptor)


def _prepare_test_runtime(path: Path, **_kwargs: object) -> _FdBackedTestRuntime:
    return _FdBackedTestRuntime(path)


def _json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()


def _infrastructure_parameters() -> dict[str, object]:
    return {
        "tenantId": TENANT_ID,
        "subscriptionId": SUBSCRIPTION_ID,
        "resourceGroupName": RESOURCE_GROUP,
        "storageAccountName": COORDINATION_NAME,
        "brokerCallerServicePrincipalId": CALLER_PRINCIPAL_ID,
        "brokerFunctionAppResourceId": FUNCTION_APP_ID,
        "brokerFunctionPackageSha256": PACKAGE_SHA256,
        "brokerTicketVerificationCertificateSha256": TICKET_CERTIFICATE_SHA256,
        "targetBindingSha256": TARGET_BINDING,
        "location": LOCATION,
        "tags": TAGS,
    }


def _restart_binding() -> dict[str, str]:
    parameters = _infrastructure_parameters()
    return build_infrastructure_restart_receipt_binding(
        owner_binding_sha256=OWNER_BINDING,
        deployment_id=DEPLOYMENT_ID,
        infrastructure_approval={
            "infrastructure_binding_sha256": "b" * 64,
            "infrastructure_parameters_sha256": _json_sha256(parameters),
            "infrastructure_source_sha256": "c" * 64,
            "toolchain_attestations_sha256": "d" * 64,
        },
        infrastructure_parameters=parameters,
    )


def _coordination_resources() -> dict[str, str]:
    return {
        "broker_principal_id": BROKER_PRINCIPAL_ID,
        "coordination_storage_account_resource_id": COORDINATION_ID,
        "lease_container_resource_id": CONTAINER_SCOPE,
        "broker_lease_data_role_definition_id": ROLE_DEFINITION_ID,
        "broker_lease_role_assignment_id": ROLE_ASSIGNMENT_ID,
    }


def _storage(name: str, resource_id: str) -> dict[str, object]:
    if resource_id != COORDINATION_ID:
        return {"id": resource_id, "name": name}
    return {
        "id": resource_id,
        "name": name,
        "type": "Microsoft.Storage/storageAccounts",
        "location": LOCATION,
        "kind": "StorageV2",
        "sku": {"name": "Standard_LRS", "tier": "Standard"},
        "tags": effective_coordination_tags(TAGS, TARGET_BINDING),
        "properties": {
            "accessTier": "Hot",
            "allowBlobPublicAccess": False,
            "allowCrossTenantReplication": False,
            "allowSharedKeyAccess": False,
            "defaultToOAuthAuthentication": True,
            "isHnsEnabled": False,
            "minimumTlsVersion": "TLS1_2",
            "networkAcls": {
                "bypass": "None",
                "defaultAction": "Deny",
                "ipRules": [],
                "resourceAccessRules": [
                    {"resourceId": FUNCTION_APP_ID, "tenantId": TENANT_ID}
                ],
                "virtualNetworkRules": [],
            },
            "publicNetworkAccess": "Enabled",
            "supportsHttpsTrafficOnly": True,
        },
    }


def _function_app() -> dict[str, object]:
    return {
        "id": FUNCTION_APP_ID,
        "name": "fn-nac-bff-test",
        "type": "Microsoft.Web/sites",
        "identity": {
            "type": "SystemAssigned, UserAssigned",
            "principalId": BROKER_PRINCIPAL_ID,
            "userAssignedIdentities": {
                f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.ManagedIdentity/"
                "userAssignedIdentities/id-nac-bff-broker": {
                    "principalId": RUNTIME_UAMI_PRINCIPAL_ID,
                    "clientId": "99999999-2222-4333-8444-555555555555",
                }
            },
        },
        "properties": {
            "state": "Running",
            "httpsOnly": True,
        },
    }


def _blob_service() -> dict[str, object]:
    return {
        "id": BLOB_SERVICE_SCOPE,
        "name": "default",
        "type": "Microsoft.Storage/storageAccounts/blobServices",
        "properties": {
            "isVersioningEnabled": False,
            "deleteRetentionPolicy": {"enabled": False},
            "containerDeleteRetentionPolicy": {"enabled": False},
        },
    }


def _lease_container() -> dict[str, object]:
    return {
        "id": CONTAINER_SCOPE,
        "name": CONTAINER_NAME,
        "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
        "properties": {
            "publicAccess": "None",
            "metadata": {
                "nac_schema_version": "nac.azure-bff-performance-coordination/v2",
                "data_classification": "synthetic-only",
                "lease_blob_path": f"locks/{TARGET_BINDING}.lock",
                "lease_blob_type": "BlockBlob",
                "lease_blob_content_length": "0",
                "lease_blob_bootstrap": (
                    "broker-internal-put-if-absent-before-acquire"
                ),
                "broker_authorization": (
                    "non-exportable-managed-identity-read-write-no-delete"
                ),
                "azure_blob_write_authorization": (
                    "broker-system-identity-write-includes-create-overwrite-lease-and-break"
                ),
                "operation_restriction_boundary": (
                    "owner-ticketed-fixed-function-route"
                ),
                "local_runner_storage_authorization": "none",
                "brokerFunctionPackageSha256": PACKAGE_SHA256,
                "brokerTicketVerificationCertificateSha256": (
                    TICKET_CERTIFICATE_SHA256
                ),
            },
        },
    }


def _role_definition() -> dict[str, object]:
    return {
        "id": ROLE_DEFINITION_ID,
        "properties": {
            "type": "CustomRole",
            "assignableScopes": [RESOURCE_GROUP_SCOPE],
            "permissions": [{
                "actions": [],
                "notActions": [],
                "dataActions": sorted(BROKER_ALLOWED_DATA_ACTIONS),
                "notDataActions": [],
            }],
        },
    }


def _role_assignment() -> dict[str, object]:
    return {
        "id": ROLE_ASSIGNMENT_ID,
        "scope": CONTAINER_SCOPE,
        "properties": {
            "principalId": BROKER_PRINCIPAL_ID,
            "principalType": "ServicePrincipal",
            "roleDefinitionId": ROLE_DEFINITION_ID,
            "conditionVersion": "2.0",
            "condition": exact_broker_lease_blob_condition(TARGET_BINDING),
        },
    }


def _deployment() -> dict[str, object]:
    return {
        "id": DEPLOYMENT_ID,
        "properties": {
            "provisioningState": "Succeeded",
            "startTime": "2026-08-03T12:00:02Z",
            "timestamp": "2026-08-03T12:00:03Z",
            "parameters": {
                name: {"value": value}
                for name, value in _infrastructure_parameters().items()
            },
            "outputs": {
                "brokerPrincipalIdBinding": {
                    "type": "String",
                    "value": BROKER_PRINCIPAL_ID,
                }
            },
        },
    }


def _ancestor_scopes() -> list[str]:
    return [
        "/",
        ROOT_MG,
        CHILD_MG,
        f"/subscriptions/{SUBSCRIPTION_ID}",
        RESOURCE_GROUP_SCOPE,
        COORDINATION_ID,
        BLOB_SERVICE_SCOPE,
        CONTAINER_SCOPE,
    ]


def _responses() -> dict[str, object]:
    responses: dict[str, object] = {
        f"https://management.azure.com{BFF_ID}?api-version=2023-05-01": _storage(
            "stnacbffoffline001", BFF_ID
        ),
        f"https://management.azure.com{WORM_ID}?api-version=2023-05-01": _storage(
            "stnacwormoffline001", WORM_ID
        ),
        f"https://management.azure.com{FUNCTION_APP_ID}?api-version=2023-12-01": (
            _function_app()
        ),
        f"https://management.azure.com{COORDINATION_ID}?api-version=2023-05-01": (
            _storage(COORDINATION_NAME, COORDINATION_ID)
        ),
        f"https://management.azure.com{BLOB_SERVICE_SCOPE}?api-version=2023-05-01": (
            _blob_service()
        ),
        f"https://management.azure.com{CONTAINER_SCOPE}?api-version=2023-05-01": (
            _lease_container()
        ),
        f"https://management.azure.com{DEPLOYMENT_ID}?api-version=2022-09-01": (
            _deployment()
        ),
        f"https://management.azure.com{ROLE_DEFINITION_ID}?api-version=2022-04-01": (
            _role_definition()
        ),
        f"https://management.azure.com{ROLE_ASSIGNMENT_ID}?api-version=2022-04-01": (
            _role_assignment()
        ),
        (
            f"https://management.azure.com{ROOT_MG}?api-version=2021-04-01"
            "&$expand=children&$recurse=true"
        ): {
            "id": ROOT_MG,
            "properties": {"children": [{
                "id": CHILD_MG,
                "properties": {"children": [{
                    "id": f"/subscriptions/{SUBSCRIPTION_ID}"
                }]},
            }]},
        },
        (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/"
            f"{BROKER_PRINCIPAL_ID}/transitiveMemberOf/"
            "microsoft.graph.group?$select=id"
        ): {"value": [{"id": BROKER_GROUP_ID}]},
        (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/"
            f"{CALLER_PRINCIPAL_ID}/transitiveMemberOf/"
            "microsoft.graph.group?$select=id"
        ): {"value": []},
    }
    name_resource = (
        f"/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.Storage/"
        "checkNameAvailability"
    )
    responses[
        f"https://management.azure.com{name_resource}?api-version=2023-05-01"
    ] = {"nameAvailable": True}
    for scope in _ancestor_scopes():
        prefix = "" if scope == "/" else scope
        url = (
            f"https://management.azure.com{prefix}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        responses[url] = {
            "value": [_role_assignment()] if scope == CONTAINER_SCOPE else []
        }
    return responses


def _write_fake_az(directory: Path) -> Path:
    executable = directory / "az"
    source = f"""#!{sys.executable}
import json
import sys
args = sys.argv[1:]
url = args[args.index('--url') + 1]
responses = json.loads({json.dumps(json.dumps(_responses(), separators=(',', ':'), sort_keys=True))})
if url not in responses:
    print('unexpected URL: ' + url, file=sys.stderr)
    raise SystemExit(64)
print(json.dumps(responses[url], separators=(',', ':'), sort_keys=True))
"""
    executable.write_text(source, encoding="utf-8")
    executable.chmod(0o755)
    return executable


def _session():
    with patch(
        "nac_bff.azure_performance_infrastructure_safety._trusted_now",
        return_value=SESSION_AT,
    ):
        return begin_azure_performance_infrastructure_readback_session(
            owner_approval_body_sha256=OWNER_BINDING,
            toolchain_attestations_sha256=TOOLCHAIN_BINDING,
        )


def _read(adapter, at, function, *args, **kwargs):
    with patch(
        "nac_bff.azure_performance_infrastructure_safety._trusted_now",
        return_value=at,
    ):
        return function(*args, **kwargs)


def _build_arguments(directory: Path) -> dict[str, object]:
    fake_az = _write_fake_az(directory)
    session = _session()
    patches = (
        patch(
            "nac_bff.azure_performance_infrastructure_safety."
            "AZURE_CLI_EXECUTION_PATH",
            fake_az,
        ),
        patch(
            "nac_bff.azure_performance_infrastructure_safety."
            "calculate_azure_cli_toolchain_sha256",
            return_value="a" * 64,
        ),
        patch(
            "nac_bff.azure_performance_infrastructure_safety."
            "calculate_toolchain_attestations_sha256",
            return_value=TOOLCHAIN_BINDING,
        ),
        patch(
            "nac_bff.azure_performance_infrastructure_safety."
            "_prepare_bound_runtime",
            side_effect=_prepare_test_runtime,
        ),
    )
    for item in patches:
        item.start()
    try:
        adapter = AzurePerformanceInfrastructureReadbackAdapter(
            session, toolchain_attestations=ADAPTER_TOOLCHAIN
        )
        post = lambda function, **kwargs: _read(
            adapter, POST_AT, function, **kwargs
        )
        return {
            "readback_session": adapter.verification_capability,
            "coordination_storage_account_name": COORDINATION_NAME,
            "coordination_name_readback_envelope": _read(
                adapter,
                NAME_AT,
                adapter.check_storage_account_name_availability,
                subscription_id=SUBSCRIPTION_ID,
                storage_account_name=COORDINATION_NAME,
            ),
            "deployment_receipt_envelope": _read(
                adapter,
                DEPLOYMENT_AT,
                adapter.execute_read,
                observation_kind="coordination-deployment-receipt",
                resource_id=DEPLOYMENT_ID,
            ),
            "coordination_storage_readback_envelope": post(
                adapter.execute_read,
                observation_kind="coordination-storage-account-configuration",
                resource_id=COORDINATION_ID,
            ),
            "coordination_blob_service_readback_envelope": post(
                adapter.execute_read,
                observation_kind="coordination-blob-service-configuration",
                resource_id=BLOB_SERVICE_SCOPE,
            ),
            "lease_container_readback_envelope": post(
                adapter.execute_read,
                observation_kind="coordination-lease-container-configuration",
                resource_id=CONTAINER_SCOPE,
            ),
            "coordination_storage_account_resource_id": COORDINATION_ID,
            "bff_storage_account_resource_id": BFF_ID,
            "worm_storage_account_resource_id": WORM_ID,
            "bff_storage_readback_envelope": post(
                adapter.execute_read,
                observation_kind="bff-storage-account-resource-id",
                resource_id=BFF_ID,
            ),
            "worm_storage_readback_envelope": post(
                adapter.execute_read,
                observation_kind="worm-storage-account-resource-id",
                resource_id=WORM_ID,
            ),
            "broker_principal_id": BROKER_PRINCIPAL_ID,
            "broker_caller_service_principal_id": CALLER_PRINCIPAL_ID,
            "broker_function_app_resource_id": FUNCTION_APP_ID,
            "broker_function_app_readback_envelope": post(
                adapter.execute_read,
                observation_kind="coordination-broker-function-app",
                resource_id=FUNCTION_APP_ID,
            ),
            "broker_function_package_sha256": PACKAGE_SHA256,
            "broker_ticket_verification_certificate_sha256": (
                TICKET_CERTIFICATE_SHA256
            ),
            "target_binding_sha256": TARGET_BINDING,
            "broker_role_definition": post(
                adapter.execute_read,
                observation_kind="coordination-broker-role-definition",
                resource_id=ROLE_DEFINITION_ID,
            ),
            "broker_role_assignment": post(
                adapter.execute_read,
                observation_kind="coordination-broker-role-assignment",
                resource_id=ROLE_ASSIGNMENT_ID,
            ),
            "subscription_ancestry_readback_envelope": post(
                adapter.read_management_group_ancestry,
                tenant_id=TENANT_ID,
                subscription_id=SUBSCRIPTION_ID,
            ),
            "broker_effective_rbac_readback_envelope": post(
                adapter.read_effective_rbac,
                principal_id=BROKER_PRINCIPAL_ID,
                target_resource_id=CONTAINER_SCOPE,
                ancestor_scopes=_ancestor_scopes(),
            ),
            "broker_caller_effective_rbac_readback_envelope": post(
                adapter.read_effective_rbac,
                principal_id=CALLER_PRINCIPAL_ID,
                target_resource_id=CONTAINER_SCOPE,
                ancestor_scopes=_ancestor_scopes(),
            ),
            "tenant_id": TENANT_ID,
            "subscription_id": SUBSCRIPTION_ID,
            "resource_group_name": RESOURCE_GROUP,
            "location": LOCATION,
            "tags": TAGS,
        }
    finally:
        for item in reversed(patches):
            item.stop()


class AzurePerformanceInfrastructureSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._ledger_temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._ledger_temporary.cleanup)
        self._ledger_patch = patch(
            "nac_bff.azure_performance_infrastructure_safety."
            "_READBACK_REPLAY_LEDGER_DIRECTORY",
            Path(self._ledger_temporary.name) / "ledger",
        )
        self._ledger_patch.start()
        self.addCleanup(self._ledger_patch.stop)

    def _verify(self, arguments: dict[str, object]):
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ):
            return verify_azure_performance_infrastructure_safety(**arguments)

    def _persist_complete_restart(self, root: Path):
        arguments = _build_arguments(root)
        store = AzurePerformanceInfrastructureRestartReceiptStore(
            root / "restart-receipts", binding=_restart_binding()
        )
        original = store.persist_original_name_available(
            arguments["coordination_name_readback_envelope"]
        )
        successful = store.persist_successful_deployment(
            arguments["deployment_receipt_envelope"],
            coordination_resources=_coordination_resources(),
            create_deployment_receipt_sha256="e" * 64,
            deployment_outputs_sha256="f" * 64,
        )
        return arguments, store, original, successful

    def test_accepts_single_owner_bound_broker_and_zero_action_caller(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            evidence = self._verify(_build_arguments(Path(value)))
        self.assertIsInstance(
            evidence, AzurePerformanceInfrastructureSafetyVerification
        )
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ):
            self.assertIs(validate_infrastructure_safety_evidence(evidence), evidence)
        self.assertEqual(evidence["broker_principal_id"], BROKER_PRINCIPAL_ID)
        self.assertEqual(
            evidence["broker_caller_service_principal_id"], CALLER_PRINCIPAL_ID
        )
        self.assertEqual(evidence["broker_function_app_resource_id"], FUNCTION_APP_ID)
        self.assertEqual(evidence["broker_function_package_sha256"], PACKAGE_SHA256)
        self.assertEqual(
            evidence["broker_ticket_verification_certificate_sha256"],
            TICKET_CERTIFICATE_SHA256,
        )
        self.assertEqual(
            evidence["broker_resource_access_rule_sha256"],
            _json_sha256(
                {"resourceId": FUNCTION_APP_ID, "tenantId": TENANT_ID}
            ),
        )
        self.assertEqual(evidence["broker_effective_assignment_count"], 1)
        self.assertEqual(
            evidence["broker_data_actions"], sorted(BROKER_ALLOWED_DATA_ACTIONS)
        )
        self.assertNotIn("bootstrap_principal_id", evidence)
        self.assertNotIn("runtime_principal_id", evidence)

    def test_rejects_same_broker_and_caller_identity(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments = _build_arguments(Path(value))
        arguments["broker_caller_service_principal_id"] = BROKER_PRINCIPAL_ID
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "BROKER_CALLER_SERVICE_PRINCIPAL_INVALID",
        ):
            self._verify(arguments)

    def test_rejects_authoritative_bff_worm_and_coordination_target_mismatch(
        self,
    ) -> None:
        variants = (
            (
                "bff_storage_account_resource_id",
                BFF_ID.replace("stnacbffoffline001", "stnacbffoffline002"),
                "AUTHORITATIVE_BFF_STORAGE_MISMATCH",
            ),
            (
                "worm_storage_account_resource_id",
                WORM_ID.replace("stnacwormoffline001", "stnacwormoffline002"),
                "AUTHORITATIVE_WORM_STORAGE_MISMATCH",
            ),
            (
                "coordination_storage_account_resource_id",
                COORDINATION_ID.replace(COORDINATION_NAME, "stnacperflease002"),
                "DEPLOYMENT_RECEIPT_INVALID",
            ),
        )
        for key, mismatched_target, error in variants:
            with self.subTest(target=key), tempfile.TemporaryDirectory() as value:
                arguments = _build_arguments(Path(value))
                arguments[key] = mismatched_target
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError, error
                ):
                    self._verify(arguments)

    def test_rejects_management_group_and_ancestor_provenance_tamper(self) -> None:
        other_management_group = (
            "/providers/Microsoft.Management/managementGroups/"
            "nac-tampered-platform"
        )
        management_group_url = (
            f"https://management.azure.com{ROOT_MG}?api-version=2021-04-01"
            "&$expand=children&$recurse=true"
        )

        responses = _responses()
        responses[management_group_url]["properties"]["children"][0]["id"] = (
            other_management_group
        )
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments = _build_arguments(Path(value))
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "EFFECTIVE_RBAC_ANCESTRY_INVALID",
        ):
            self._verify(arguments)

        tampered_scopes = _ancestor_scopes()
        tampered_scopes[2] = other_management_group
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._ancestor_scopes", return_value=tampered_scopes
        ):
            arguments = _build_arguments(Path(value))
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "EFFECTIVE_RBAC_ANCESTRY_INVALID",
        ):
            self._verify(arguments)

    def test_rejects_broker_role_or_assignment_drift(self) -> None:
        variants = (
            ("broker_role_definition", "payload", "resource", "properties"),
            ("broker_role_assignment", "payload", "resource", "properties"),
        )
        for index, path in enumerate(variants):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as value:
                arguments = _build_arguments(Path(value))
                envelope = deepcopy(arguments[path[0]])
                if index == 0:
                    envelope[path[1]][path[2]][path[3]]["permissions"][0][
                        "dataActions"
                    ] = []
                else:
                    envelope[path[1]][path[2]][path[3]]["principalId"] = (
                        CALLER_PRINCIPAL_ID
                    )
                arguments[path[0]] = envelope
                with self.assertRaises(AzurePerformanceInfrastructureSafetyError):
                    self._verify(arguments)

    def test_rejects_function_app_uami_or_package_binding_drift(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments = _build_arguments(Path(value))
        arguments["broker_function_app_resource_id"] = FUNCTION_APP_ID + "-other"
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "BROKER_FUNCTION_APP_READBACK_INVALID",
        ):
            self._verify(arguments)

        with tempfile.TemporaryDirectory() as value:
            arguments = _build_arguments(Path(value))
        arguments["broker_function_package_sha256"] = "9" * 64
        with self.assertRaises(AzurePerformanceInfrastructureSafetyError):
            self._verify(arguments)

    def test_rejects_mismatched_resource_instance_rule(self) -> None:
        responses = _responses()
        storage_url = (
            f"https://management.azure.com{COORDINATION_ID}"
            "?api-version=2023-05-01"
        )
        responses[storage_url]["properties"]["networkAcls"][
            "resourceAccessRules"
        ][0]["resourceId"] = FUNCTION_APP_ID + "-other"
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments = _build_arguments(Path(value))
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "COORDINATION_STORAGE_CONFIGURATION_MISMATCH",
        ):
            self._verify(arguments)

    def test_caller_effective_storage_data_action_is_rejected(self) -> None:
        responses = _responses()
        caller_role_definition_id = (
            f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/"
            "roleDefinitions/77777777-2222-4333-8444-555555555555"
        )
        caller_assignment = deepcopy(_role_assignment())
        caller_assignment["id"] = ROLE_ASSIGNMENT_ID.rsplit("/", 1)[0] + (
            "/44444444-2222-4333-8444-555555555555"
        )
        caller_assignment["properties"]["principalId"] = CALLER_PRINCIPAL_ID
        caller_assignment["properties"]["roleDefinitionId"] = (
            caller_role_definition_id
        )
        responses[
            f"https://management.azure.com{caller_role_definition_id}"
            "?api-version=2022-04-01"
        ] = {
            "id": caller_role_definition_id,
            "properties": {
                "permissions": [{
                    "actions": [],
                    "notActions": [],
                    "dataActions": [
                        "Microsoft.Storage/storageAccounts/blobServices/"
                        "containers/blobs/read"
                    ],
                    "notDataActions": [],
                }]
            },
        }
        container_url = (
            f"https://management.azure.com{CONTAINER_SCOPE}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        responses[container_url]["value"].append(caller_assignment)
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments = _build_arguments(Path(value))
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "BROKER_CALLER_STORAGE_DATA_ACTIONS_PRESENT",
        ):
            self._verify(arguments)

    def test_stale_broker_role_assignment_is_rejected(self) -> None:
        stale_principals = {
            "runtime-uami": RUNTIME_UAMI_PRINCIPAL_ID,
            "previous-system-identity": "66666666-2222-4333-8444-555555555555",
        }
        for label, stale_principal in stale_principals.items():
            with self.subTest(label=label):
                responses = _responses()
                stale = deepcopy(_role_assignment())
                stale["id"] = ROLE_ASSIGNMENT_ID.rsplit("/", 1)[0] + (
                    "/55555555-2222-4333-8444-555555555555"
                )
                stale["properties"]["principalId"] = stale_principal
                container_url = (
                    f"https://management.azure.com{CONTAINER_SCOPE}/providers/"
                    "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
                    "&$filter=atScope()"
                )
                responses[container_url]["value"].append(stale)
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments = _build_arguments(Path(value))
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "EXPECTED_ROLE_ASSIGNMENT_NOT_EXCLUSIVE",
                ):
                    self._verify(arguments)

    def test_rejects_broader_effective_assignment_at_each_ancestor(self) -> None:
        for index, scope in enumerate(_ancestor_scopes()[:-1]):
            with self.subTest(scope=scope):
                responses = _responses()
                broader = deepcopy(_role_assignment())
                assignment_scope = "" if scope == "/" else scope
                broader["id"] = (
                    f"{assignment_scope}/providers/Microsoft.Authorization/"
                    "roleAssignments/"
                    f"{index + 4:08d}-2222-4333-8444-555555555555"
                )
                broader["properties"]["principalId"] = BROKER_GROUP_ID
                broader["properties"]["principalType"] = "Group"
                url = (
                    f"https://management.azure.com{assignment_scope}/providers/"
                    "Microsoft.Authorization/roleAssignments"
                    "?api-version=2022-04-01&$filter=atScope()"
                )
                responses[url]["value"].append(broader)
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments = _build_arguments(Path(value))
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "BROADER_EFFECTIVE_ASSIGNMENT_PRESENT",
                ):
                    self._verify(arguments)

    def test_rejects_missing_duplicate_or_unresolved_effective_assignment(
        self,
    ) -> None:
        container_url = (
            f"https://management.azure.com{CONTAINER_SCOPE}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        root_url = (
            f"https://management.azure.com{ROOT_MG}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        unresolved_role_id = (
            f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/"
            "roleDefinitions/55555555-2222-4333-8444-555555555555"
        )
        for variant, error in (
            ("missing", "EXPECTED_EFFECTIVE_ASSIGNMENT_NOT_UNIQUE"),
            ("duplicate", "EFFECTIVE_ASSIGNMENTS_INVALID"),
            ("unresolved", "EFFECTIVE_ASSIGNMENT_DATA_ACTIONS_UNRESOLVED"),
        ):
            with self.subTest(variant=variant):
                responses = _responses()
                if variant == "missing":
                    responses[container_url]["value"] = []
                elif variant == "duplicate":
                    responses[container_url]["value"].append(
                        deepcopy(_role_assignment())
                    )
                else:
                    unresolved = deepcopy(_role_assignment())
                    unresolved["id"] = (
                        f"{ROOT_MG}/providers/Microsoft.Authorization/"
                        "roleAssignments/66666666-2222-4333-8444-555555555555"
                    )
                    unresolved["properties"]["principalId"] = BROKER_GROUP_ID
                    unresolved["properties"]["principalType"] = "Group"
                    unresolved["properties"]["roleDefinitionId"] = (
                        unresolved_role_id
                    )
                    responses[root_url]["value"].append(unresolved)
                    responses[
                        f"https://management.azure.com{unresolved_role_id}"
                        "?api-version=2022-04-01"
                    ] = {
                        "id": unresolved_role_id,
                        "properties": {"permissions": [{"actions": []}]},
                    }
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments = _build_arguments(Path(value))
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError, error
                ):
                    self._verify(arguments)

    def test_rejects_tampered_safety_evidence_or_capability(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            evidence = self._verify(_build_arguments(Path(value)))
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED",
        ):
            validate_infrastructure_safety_evidence(deepcopy(evidence))

        with tempfile.TemporaryDirectory() as value:
            evidence = self._verify(_build_arguments(Path(value)))
        dict.__setitem__(evidence, "status", "TAMPERED")
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID",
        ):
            validate_infrastructure_safety_evidence(evidence)

        with tempfile.TemporaryDirectory() as value:
            evidence = self._verify(_build_arguments(Path(value)))
        object.__setattr__(evidence, "_authenticator", b"tampered")
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID",
        ):
            validate_infrastructure_safety_evidence(evidence)

    def test_restart_receipts_are_create_once_and_reconcile_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            arguments, store, original, successful = (
                self._persist_complete_restart(root)
            )
            self.assertEqual(store.load()["status"], "COMPLETE")
            self.assertEqual(
                store.reconcile_successful_deployment(
                    arguments["deployment_receipt_envelope"]
                ),
                successful,
            )
            self.assertEqual(
                successful["original_name_receipt_sha256"],
                original["observation_sha256"],
            )
            self.assertEqual(
                successful["coordination_resources"]["lease_blob_path"],
                f"locks/{TARGET_BINDING}.lock",
            )
            self.assertEqual(
                stat.S_IMODE((store.directory / store._NAME_FILE).stat().st_mode),
                0o400,
            )
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "INFRASTRUCTURE_ORIGINAL_NAME_RECEIPT_ALREADY_EXISTS",
            ):
                store.persist_original_name_available(
                    arguments["coordination_name_readback_envelope"]
                )

    def test_restart_rejects_incomplete_or_tampered_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            arguments = _build_arguments(root)
            store = AzurePerformanceInfrastructureRestartReceiptStore(
                root / "restart-receipts", binding=_restart_binding()
            )
            store.persist_original_name_available(
                arguments["coordination_name_readback_envelope"]
            )
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "INFRASTRUCTURE_RESTART_STATE_INVALID",
            ):
                store.reconcile_successful_deployment(
                    arguments["deployment_receipt_envelope"]
                )

        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            _, store, _, _ = self._persist_complete_restart(root)
            (store.directory / store._NAME_FILE).unlink()
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "INFRASTRUCTURE_RESTART_RECEIPTS_INCOMPLETE",
            ):
                store.load()

        for filename, error in (
            (
                AzurePerformanceInfrastructureRestartReceiptStore._NAME_FILE,
                "INFRASTRUCTURE_ORIGINAL_NAME_RECEIPT_INVALID",
            ),
            (
                AzurePerformanceInfrastructureRestartReceiptStore._DEPLOYMENT_FILE,
                "INFRASTRUCTURE_SUCCESSFUL_DEPLOYMENT_RECEIPT_INVALID",
            ),
        ):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as value:
                root = Path(value)
                _, store, _, _ = self._persist_complete_restart(root)
                receipt_path = store.directory / filename
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                receipt["provider_observation_sha256"] = "0" * 64
                receipt_path.chmod(0o600)
                receipt_path.write_text(
                    json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8"
                )
                receipt_path.chmod(0o400)
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError, error
                ):
                    store.load()

    def test_restart_rejects_running_failed_missing_or_mismatched_deployment(
        self,
    ) -> None:
        deployment_url = (
            f"https://management.azure.com{DEPLOYMENT_ID}?api-version=2022-09-01"
        )
        for variant in ("running", "failed", "mismatched"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as value:
                root = Path(value)
                _, store, _, _ = self._persist_complete_restart(root)
                responses = _responses()
                deployment = responses[deployment_url]
                if variant == "running":
                    deployment["properties"]["provisioningState"] = "Running"
                elif variant == "failed":
                    deployment["properties"]["provisioningState"] = "Failed"
                else:
                    deployment["properties"]["parameters"][
                        "targetBindingSha256"
                    ]["value"] = "9" * 64
                current = root / "current"
                current.mkdir()
                with patch(__name__ + "._responses", return_value=responses):
                    arguments = _build_arguments(current)
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "INFRASTRUCTURE_RECONCILIATION_DEPLOYMENT_INVALID",
                ):
                    store.reconcile_successful_deployment(
                        arguments["deployment_receipt_envelope"]
                    )

        responses = _responses()
        responses.pop(deployment_url)
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ), self.assertRaises(AzurePerformanceInfrastructureSafetyError):
            _build_arguments(Path(value))

    def test_restart_rejects_replaced_deployment_and_invalid_time_order(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            arguments = _build_arguments(root)
            store = AzurePerformanceInfrastructureRestartReceiptStore(
                root / "restart-receipts", binding=_restart_binding()
            )
            store.persist_original_name_available(
                arguments["coordination_name_readback_envelope"]
            )
            store.persist_successful_deployment(
                arguments["deployment_receipt_envelope"],
                coordination_resources=_coordination_resources(),
                create_deployment_receipt_sha256="e" * 64,
                deployment_outputs_sha256="f" * 64,
            )

            changed = _responses()
            changed[
                f"https://management.azure.com{DEPLOYMENT_ID}?api-version=2022-09-01"
            ]["properties"]["timestamp"] = "2026-08-03T12:00:02Z"
            current = root / "current"
            current.mkdir()
            with patch(__name__ + "._responses", return_value=changed):
                changed_arguments = _build_arguments(current)
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "INFRASTRUCTURE_DEPLOYMENT_REPLACED",
            ):
                store.reconcile_successful_deployment(
                    changed_arguments["deployment_receipt_envelope"]
                )

        responses = _responses()
        responses[
            f"https://management.azure.com{DEPLOYMENT_ID}?api-version=2022-09-01"
        ]["properties"]["startTime"] = "2026-08-03T12:00:00Z"
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments = _build_arguments(Path(value))
            store = AzurePerformanceInfrastructureRestartReceiptStore(
                Path(value) / "receipts", binding=_restart_binding()
            )
            store.persist_original_name_available(
                arguments["coordination_name_readback_envelope"]
            )
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "READBACK_TIMESTAMP_CONTINUITY_INVALID",
            ):
                store.persist_successful_deployment(
                    arguments["deployment_receipt_envelope"],
                    coordination_resources=_coordination_resources(),
                    create_deployment_receipt_sha256="e" * 64,
                    deployment_outputs_sha256="f" * 64,
                )


if __name__ == "__main__":
    unittest.main()
