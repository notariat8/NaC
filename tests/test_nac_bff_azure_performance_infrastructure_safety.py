from copy import copy, deepcopy
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

import nac_bff.azure_performance_infrastructure_safety as infrastructure_safety
from nac_bff.azure_activation_attestations import TOOLCHAIN_ATTESTATION_FIELDS
from nac_bff.azure_performance_infrastructure_safety import (
    BOOTSTRAP_ALLOWED_DATA_ACTIONS,
    RUNTIME_ALLOWED_DATA_ACTIONS,
    AzurePerformanceInfrastructureReadbackAdapter,
    AzurePerformanceInfrastructureReadbackCapability,
    AzurePerformanceInfrastructureReadbackResult,
    AzurePerformanceInfrastructureRestartReceiptStore,
    AzurePerformanceInfrastructureSafetyError,
    AzurePerformanceInfrastructureSafetyVerification,
    CONTAINER_NAME,
    begin_azure_performance_infrastructure_readback_session,
    build_infrastructure_restart_receipt_binding,
    canonical_observation_sha256,
    effective_coordination_tags,
    exact_bootstrap_lease_blob_condition,
    exact_runtime_lease_blob_condition,
    infrastructure_safety_policy_sha256,
    validate_infrastructure_safety_evidence,
    verify_azure_performance_infrastructure_safety,
)


SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
PRINCIPAL_ID = "abcdef01-2222-4333-8444-555555555555"
GROUP_ID = "abcdef02-2222-4333-8444-555555555555"
RUNTIME_PRINCIPAL_ID = "abcdef03-2222-4333-8444-555555555555"
RUNTIME_GROUP_ID = "abcdef04-2222-4333-8444-555555555555"
TARGET_BINDING = "a" * 64
OWNER_BINDING = "8" * 64
TOOLCHAIN_BINDING = "7" * 64
LOCATION = "germanywestcentral"
RESOURCE_GROUP = "rg-nac-bff-test"
COORDINATION_NAME = "stnacperflease001"
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
RUNTIME_ROLE_DEFINITION_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Authorization/roleDefinitions/"
    "22222223-2222-4333-8444-555555555555"
)
ROLE_ASSIGNMENT_ID = (
    f"{CONTAINER_SCOPE}/providers/Microsoft.Authorization/roleAssignments/"
    "33333333-2222-4333-8444-555555555555"
)
RUNTIME_ROLE_ASSIGNMENT_ID = (
    f"{CONTAINER_SCOPE}/providers/Microsoft.Authorization/roleAssignments/"
    "33333334-2222-4333-8444-555555555555"
)
DEPLOYMENT_ID = (
    f"{RESOURCE_GROUP_SCOPE}/providers/Microsoft.Resources/deployments/"
    "nac-bff-performance-coordination"
)
ALLOWED_IP = "8.8.8.8"
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
        self._descriptor = -1


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
        "bootstrapPrincipalId": PRINCIPAL_ID,
        "runtimePrincipalId": RUNTIME_PRINCIPAL_ID,
        "allowedClientIpAddress": ALLOWED_IP,
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
        "coordination_storage_account_resource_id": COORDINATION_ID,
        "lease_container_resource_id": CONTAINER_SCOPE,
        "bootstrap_lease_data_role_definition_id": ROLE_DEFINITION_ID,
        "runtime_lease_data_role_definition_id": RUNTIME_ROLE_DEFINITION_ID,
        "bootstrap_lease_role_assignment_id": ROLE_ASSIGNMENT_ID,
        "runtime_lease_role_assignment_id": RUNTIME_ROLE_ASSIGNMENT_ID,
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
                "ipRules": [{"action": "Allow", "value": ALLOWED_IP}],
                "resourceAccessRules": [],
                "virtualNetworkRules": [],
            },
            "publicNetworkAccess": "Enabled",
            "supportsHttpsTrafficOnly": True,
            "unprojectedAzureField": "ignored-by-exact-transform",
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
                "nac_schema_version": (
                    "nac.azure-bff-performance-coordination/v1"
                ),
                "data_classification": "synthetic-only",
                "lease_blob_path": f"locks/{TARGET_BINDING}.lock",
                "lease_blob_type": "BlockBlob",
                "lease_blob_content_length": "0",
                "lease_blob_bootstrap": (
                    "owner-gated-put-if-absent-before-runtime"
                ),
                "bootstrap_authorization": (
                    "blob-read-plus-add-only-no-write-no-delete"
                ),
                "runtime_authorization": (
                    "blob-read-plus-write-only-no-add-no-delete"
                ),
                "azure_blob_write_authorization": (
                    "runtime-write-includes-create-overwrite-lease-and-break"
                ),
                "operation_restriction_boundary": (
                    "sealed-app-api-defense-in-depth-not-azure-enforced"
                ),
                "principal_separation": (
                    "distinct-owner-bound-bootstrap-and-runtime-principals"
                ),
            },
        },
    }


def _role_definition(*, runtime: bool = False) -> dict[str, object]:
    return {
        "id": RUNTIME_ROLE_DEFINITION_ID if runtime else ROLE_DEFINITION_ID,
        "properties": {
            "type": "CustomRole",
            "assignableScopes": [RESOURCE_GROUP_SCOPE],
            "permissions": [{
                "actions": [],
                "notActions": [],
                "dataActions": sorted(
                    RUNTIME_ALLOWED_DATA_ACTIONS
                    if runtime
                    else BOOTSTRAP_ALLOWED_DATA_ACTIONS
                ),
                "notDataActions": [],
            }],
        },
    }


def _role_assignment(*, runtime: bool = False) -> dict[str, object]:
    return {
        "id": RUNTIME_ROLE_ASSIGNMENT_ID if runtime else ROLE_ASSIGNMENT_ID,
        "scope": CONTAINER_SCOPE,
        "properties": {
            "principalId": RUNTIME_PRINCIPAL_ID if runtime else PRINCIPAL_ID,
            "principalType": "ServicePrincipal",
            "roleDefinitionId": (
                RUNTIME_ROLE_DEFINITION_ID if runtime else ROLE_DEFINITION_ID
            ),
            "conditionVersion": "2.0",
            "condition": (
                exact_runtime_lease_blob_condition(TARGET_BINDING)
                if runtime
                else exact_bootstrap_lease_blob_condition(TARGET_BINDING)
            ),
        },
    }


def _deployment() -> dict[str, object]:
    parameters = _infrastructure_parameters()
    return {
        "id": DEPLOYMENT_ID,
        "properties": {
            "provisioningState": "Succeeded",
            "startTime": "2026-08-03T12:00:02Z",
            "timestamp": "2026-08-03T12:00:03Z",
            "parameters": {
                name: {"value": value} for name, value in parameters.items()
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
        f"{COORDINATION_ID}/blobServices/default",
        CONTAINER_SCOPE,
    ]


def _responses() -> dict[str, object]:
    responses: dict[str, object] = {
        f"https://management.azure.com{BFF_ID}?api-version=2023-05-01": _storage("stnacbffoffline001", BFF_ID),
        f"https://management.azure.com{WORM_ID}?api-version=2023-05-01": _storage("stnacwormoffline001", WORM_ID),
        f"https://management.azure.com{COORDINATION_ID}?api-version=2023-05-01": _storage(COORDINATION_NAME, COORDINATION_ID),
        f"https://management.azure.com{BLOB_SERVICE_SCOPE}?api-version=2023-05-01": _blob_service(),
        f"https://management.azure.com{CONTAINER_SCOPE}?api-version=2023-05-01": _lease_container(),
        f"https://management.azure.com{DEPLOYMENT_ID}?api-version=2022-09-01": _deployment(),
        f"https://management.azure.com{ROLE_DEFINITION_ID}?api-version=2022-04-01": _role_definition(),
        (
            f"https://management.azure.com{RUNTIME_ROLE_DEFINITION_ID}"
            "?api-version=2022-04-01"
        ): _role_definition(runtime=True),
        f"https://management.azure.com{ROLE_ASSIGNMENT_ID}?api-version=2022-04-01": _role_assignment(),
        (
            f"https://management.azure.com{RUNTIME_ROLE_ASSIGNMENT_ID}"
            "?api-version=2022-04-01"
        ): _role_assignment(runtime=True),
        (
            f"https://management.azure.com{ROOT_MG}?api-version=2021-04-01"
            "&$expand=children&$recurse=true"
        ): {
            "id": ROOT_MG,
            "properties": {"children": [{
                "id": CHILD_MG,
                "properties": {"children": [{"id": f"/subscriptions/{SUBSCRIPTION_ID}"}]},
            }]},
        },
        (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/{PRINCIPAL_ID}/"
            "transitiveMemberOf/microsoft.graph.group?$select=id"
        ): {"value": [{"id": GROUP_ID}]},
        (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/"
            f"{RUNTIME_PRINCIPAL_ID}/transitiveMemberOf/"
            "microsoft.graph.group?$select=id"
        ): {"value": [{"id": RUNTIME_GROUP_ID}]},
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
            "value": (
                [_role_assignment(), _role_assignment(runtime=True)]
                if scope == CONTAINER_SCOPE
                else []
            )
        }
    return responses


def _write_fake_az(directory: Path) -> tuple[Path, Path]:
    executable = directory / "az"
    environment_log = directory / "environment.json"
    sitecustomize_marker = directory / "sitecustomize-loaded"
    (directory / "sitecustomize.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(sitecustomize_marker)!r}).write_text('loaded', encoding='ascii')\n",
        encoding="utf-8",
    )
    source = f"""#!{sys.executable}
import json
import os
import sys
from pathlib import Path
Path({str(environment_log)!r}).write_text(json.dumps(dict(os.environ), sort_keys=True), encoding='utf-8')
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
    return executable, environment_log


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


def _build_arguments(
    directory: Path,
    *,
    blob_service_resource_id: str = BLOB_SERVICE_SCOPE,
    name_at: datetime = NAME_AT,
) -> tuple[dict[str, object], Path]:
    fake_az, environment_log = _write_fake_az(directory)
    session = _session()
    patches = (
        patch(
            "nac_bff.azure_performance_infrastructure_safety.AZURE_CLI_EXECUTION_PATH",
            fake_az,
        ),
        patch(
            "nac_bff.azure_performance_infrastructure_safety.calculate_azure_cli_toolchain_sha256",
            return_value="a" * 64,
        ),
        patch(
            "nac_bff.azure_performance_infrastructure_safety.calculate_toolchain_attestations_sha256",
            return_value=TOOLCHAIN_BINDING,
        ),
        patch(
            "nac_bff.azure_performance_infrastructure_safety._prepare_bound_runtime",
            side_effect=_prepare_test_runtime,
        ),
    )
    for item in patches:
        item.start()
    try:
        adapter = AzurePerformanceInfrastructureReadbackAdapter(
            session, toolchain_attestations=ADAPTER_TOOLCHAIN
        )
        name = _read(
            adapter,
            name_at,
            adapter.check_storage_account_name_availability,
            subscription_id=SUBSCRIPTION_ID,
            storage_account_name=COORDINATION_NAME,
        )
        deployment = _read(
            adapter,
            DEPLOYMENT_AT,
            adapter.execute_read,
            observation_kind="coordination-deployment-receipt",
            resource_id=DEPLOYMENT_ID,
        )
        post = lambda function, **kwargs: _read(
            adapter, POST_AT, function, **kwargs
        )
        arguments = {
            "readback_session": adapter.verification_capability,
            "coordination_storage_account_name": COORDINATION_NAME,
            "coordination_name_readback_envelope": name,
            "deployment_receipt_envelope": deployment,
            "coordination_storage_readback_envelope": post(
                adapter.execute_read,
                observation_kind="coordination-storage-account-configuration",
                resource_id=COORDINATION_ID,
            ),
            "coordination_blob_service_readback_envelope": post(
                adapter.execute_read,
                observation_kind="coordination-blob-service-configuration",
                resource_id=blob_service_resource_id,
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
            "bootstrap_principal_id": PRINCIPAL_ID,
            "runtime_principal_id": RUNTIME_PRINCIPAL_ID,
            "target_binding_sha256": TARGET_BINDING,
            "bootstrap_role_definition": post(
                adapter.execute_read,
                observation_kind="coordination-role-definition",
                resource_id=ROLE_DEFINITION_ID,
            ),
            "runtime_role_definition": post(
                adapter.execute_read,
                observation_kind="coordination-role-definition",
                resource_id=RUNTIME_ROLE_DEFINITION_ID,
            ),
            "bootstrap_role_assignment": post(
                adapter.execute_read,
                observation_kind="coordination-role-assignment",
                resource_id=ROLE_ASSIGNMENT_ID,
            ),
            "runtime_role_assignment": post(
                adapter.execute_read,
                observation_kind="coordination-role-assignment",
                resource_id=RUNTIME_ROLE_ASSIGNMENT_ID,
            ),
            "subscription_ancestry_readback_envelope": post(
                adapter.read_management_group_ancestry,
                tenant_id=TENANT_ID,
                subscription_id=SUBSCRIPTION_ID,
            ),
            "bootstrap_effective_rbac_readback_envelope": post(
                adapter.read_effective_rbac,
                principal_id=PRINCIPAL_ID,
                target_resource_id=CONTAINER_SCOPE,
                ancestor_scopes=_ancestor_scopes(),
            ),
            "runtime_effective_rbac_readback_envelope": post(
                adapter.read_effective_rbac,
                principal_id=RUNTIME_PRINCIPAL_ID,
                target_resource_id=CONTAINER_SCOPE,
                ancestor_scopes=_ancestor_scopes(),
            ),
            "tenant_id": TENANT_ID,
            "subscription_id": SUBSCRIPTION_ID,
            "resource_group_name": RESOURCE_GROUP,
            "location": LOCATION,
            "tags": TAGS,
            "allowed_client_ip_address": ALLOWED_IP,
        }
        return arguments, environment_log
    finally:
        for item in reversed(patches):
            item.stop()


def _issue_evidence() -> AzurePerformanceInfrastructureSafetyVerification:
    with tempfile.TemporaryDirectory() as value:
        arguments, _ = _build_arguments(Path(value))
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ):
            return verify_azure_performance_infrastructure_safety(**arguments)


class AzurePerformanceInfrastructureSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._ledger_temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self._ledger_temporary.cleanup)
        self.ledger_directory = Path(self._ledger_temporary.name) / "ledger"
        self._ledger_patch = patch(
            "nac_bff.azure_performance_infrastructure_safety."
            "_READBACK_REPLAY_LEDGER_DIRECTORY",
            self.ledger_directory,
        )
        self._ledger_patch.start()
        self.addCleanup(self._ledger_patch.stop)

    def test_accepts_only_the_exact_offline_safety_observation(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, environment_log = _build_arguments(Path(value))
            with patch(
                "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                return_value=VERIFY_AT,
            ):
                evidence = verify_azure_performance_infrastructure_safety(**arguments)
                validated = validate_infrastructure_safety_evidence(evidence)

            self.assertIsInstance(
                evidence, AzurePerformanceInfrastructureSafetyVerification
            )
            self.assertIs(validated, evidence)
            self.assertEqual(validated["status"], "SAFE")
            self.assertEqual(
                validated["bootstrap_effective_assignment_count"], 1
            )
            self.assertEqual(
                validated["runtime_effective_assignment_count"], 1
            )
            self.assertEqual(validated["bootstrap_effective_principal_count"], 2)
            self.assertEqual(validated["runtime_effective_principal_count"], 2)
            self.assertEqual(
                validated["bootstrap_attested_ancestor_scope_count"], 8
            )
            self.assertEqual(
                validated["runtime_attested_ancestor_scope_count"], 8
            )
            self.assertEqual(
                validated["bootstrap_data_actions"],
                sorted(BOOTSTRAP_ALLOWED_DATA_ACTIONS),
            )
            self.assertEqual(
                validated["runtime_data_actions"],
                sorted(RUNTIME_ALLOWED_DATA_ACTIONS),
            )
            self.assertNotEqual(
                validated["bootstrap_principal_id"],
                validated["runtime_principal_id"],
            )
            storage_payload = arguments["coordination_storage_readback_envelope"][
                "payload"
            ]
            network_acls = storage_payload["properties"]["networkAcls"]
            self.assertEqual(network_acls["resourceAccessRules"], [])
            self.assertEqual(
                validated["infrastructure_safety_policy_sha256"],
                infrastructure_safety_policy_sha256(),
            )
            child_environment = json.loads(environment_log.read_text(encoding="utf-8"))
            self.assertEqual(
                set(child_environment),
                {
                    "AZURE_CONFIG_DIR",
                    "AZURE_CORE_COLLECT_TELEMETRY",
                    "HOME",
                    "LANG",
                    "LC_ALL",
                    "PATH",
                    "PYTHONNOUSERSITE",
                    "PYTHONSAFEPATH",
                },
            )
            self.assertNotIn("PYTHONPATH", child_environment)
            self.assertEqual(child_environment["PYTHONNOUSERSITE"], "1")
            self.assertEqual(child_environment["PYTHONSAFEPATH"], "1")
            self.assertFalse(
                environment_log.with_name("sitecustomize-loaded").exists()
            )

    def test_rejects_equal_bootstrap_and_runtime_principals(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        arguments["runtime_principal_id"] = PRINCIPAL_ID
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^BOOTSTRAP_RUNTIME_PRINCIPALS_NOT_DISTINCT$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_bootstrap_or_runtime_role_data_action_drift(self) -> None:
        variants = {
            "bootstrap_has_write": (
                ROLE_DEFINITION_ID,
                sorted(
                    BOOTSTRAP_ALLOWED_DATA_ACTIONS
                    | {
                        "Microsoft.Storage/storageAccounts/blobServices/containers/"
                        "blobs/write"
                    }
                ),
            ),
            "bootstrap_missing_add": (
                ROLE_DEFINITION_ID,
                [
                    "Microsoft.Storage/storageAccounts/blobServices/containers/"
                    "blobs/read"
                ],
            ),
            "runtime_has_add": (
                RUNTIME_ROLE_DEFINITION_ID,
                sorted(
                    RUNTIME_ALLOWED_DATA_ACTIONS
                    | {
                        "Microsoft.Storage/storageAccounts/blobServices/containers/"
                        "blobs/add/action"
                    }
                ),
            ),
            "runtime_missing_write": (
                RUNTIME_ROLE_DEFINITION_ID,
                [
                    "Microsoft.Storage/storageAccounts/blobServices/containers/"
                    "blobs/read"
                ],
            ),
        }
        for name, (role_id, data_actions) in variants.items():
            with self.subTest(name=name):
                responses = _responses()
                role_url = (
                    f"https://management.azure.com{role_id}"
                    "?api-version=2022-04-01"
                )
                responses[role_url]["properties"]["permissions"][0][
                    "dataActions"
                ] = data_actions
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^ROLE_DEFINITION_DATA_ACTIONS_INVALID$",
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_runtime_assignment_condition_or_effective_rbac_gap(self) -> None:
        assignment_url = (
            f"https://management.azure.com{RUNTIME_ROLE_ASSIGNMENT_ID}"
            "?api-version=2022-04-01"
        )
        responses = _responses()
        responses[assignment_url]["properties"]["condition"] = (
            exact_runtime_lease_blob_condition("b" * 64)
        )
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments, _ = _build_arguments(Path(value))
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^ROLE_ASSIGNMENT_CONDITION_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

        responses = _responses()
        container_url = (
            f"https://management.azure.com{CONTAINER_SCOPE}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        responses[container_url] = {"value": [_role_assignment()]}
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments, _ = _build_arguments(Path(value))
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^EXPECTED_EFFECTIVE_ASSIGNMENT_NOT_UNIQUE$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_seals_exact_blob_service_and_lease_container_arm_gets(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ):
            evidence = verify_azure_performance_infrastructure_safety(**arguments)

        expected = {
            "blob_service": (
                "coordination_blob_service_readback_envelope",
                BLOB_SERVICE_SCOPE,
            ),
            "lease_container": (
                "lease_container_readback_envelope",
                CONTAINER_SCOPE,
            ),
        }
        for transcript_name, (argument_name, resource_id) in expected.items():
            with self.subTest(transcript_name=transcript_name):
                envelope = arguments[argument_name]
                operation = envelope["sealed_execution"]["operations"][0]
                url = (
                    f"https://management.azure.com{resource_id}"
                    "?api-version=2023-05-01"
                )
                self.assertEqual(operation["resource_id"], resource_id)
                self.assertEqual(operation["api_version"], "2023-05-01")
                self.assertEqual(
                    operation["argv"][1:],
                    [
                        "rest",
                        "--method",
                        "get",
                        "--url",
                        url,
                        "--only-show-errors",
                        "--output",
                        "json",
                    ],
                )
                self.assertEqual(
                    evidence["readback_transcript"][transcript_name], envelope
                )
                self.assertEqual(
                    evidence["readback_observation_sha256"][transcript_name],
                    envelope["observation_sha256"],
                )
        self.assertEqual(
            evidence["lease_container_resource_id"], CONTAINER_SCOPE
        )

    def test_rejects_blob_service_safety_property_drift(self) -> None:
        blob_url = (
            f"https://management.azure.com{BLOB_SERVICE_SCOPE}"
            "?api-version=2023-05-01"
        )
        variants = {
            "versioning": ("isVersioningEnabled", True),
            "blob_retention": ("deleteRetentionPolicy", {"enabled": True}),
            "container_retention": (
                "containerDeleteRetentionPolicy",
                {"enabled": True},
            ),
            "unknown_retention_state": (
                "deleteRetentionPolicy",
                {"enabled": None},
            ),
        }
        for name, (property_name, property_value) in variants.items():
            with self.subTest(name=name):
                responses = _responses()
                responses[blob_url]["properties"][property_name] = property_value
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^COORDINATION_BLOB_SERVICE_CONFIGURATION_MISMATCH$",
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_missing_blob_service_retention_policy(self) -> None:
        responses = _responses()
        blob_url = (
            f"https://management.azure.com{BLOB_SERVICE_SCOPE}"
            "?api-version=2023-05-01"
        )
        responses[blob_url]["properties"].pop("deleteRetentionPolicy")
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^SEALED_AZURE_READ_RESPONSE_INVALID$",
        ):
            _build_arguments(Path(value))

    def test_rejects_blob_service_read_redirected_to_another_resource(self) -> None:
        redirected = f"{COORDINATION_ID}/blobServices/secondary"
        responses = _responses()
        responses[
            f"https://management.azure.com{redirected}?api-version=2023-05-01"
        ] = _blob_service()
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments, _ = _build_arguments(
                Path(value), blob_service_resource_id=redirected
            )
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^COORDINATION_BLOB_SERVICE_READBACK_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_lease_container_public_access_metadata_or_id_drift(self) -> None:
        container_url = (
            f"https://management.azure.com{CONTAINER_SCOPE}"
            "?api-version=2023-05-01"
        )

        def public_access(resource: dict[str, object]) -> None:
            resource["properties"]["publicAccess"] = "Blob"

        def missing_metadata(resource: dict[str, object]) -> None:
            resource["properties"]["metadata"].pop("lease_blob_path")

        def extra_metadata(resource: dict[str, object]) -> None:
            resource["properties"]["metadata"]["unknown"] = "unsafe"

        def metadata_drift(resource: dict[str, object]) -> None:
            resource["properties"]["metadata"]["lease_blob_content_length"] = "1"

        def redirected_id(resource: dict[str, object]) -> None:
            resource["id"] = f"{BLOB_SERVICE_SCOPE}/containers/other"

        variants = {
            "public_access": public_access,
            "missing_metadata": missing_metadata,
            "extra_metadata": extra_metadata,
            "metadata_drift": metadata_drift,
            "redirected_id": redirected_id,
        }
        for name, mutate in variants.items():
            with self.subTest(name=name):
                responses = _responses()
                mutate(responses[container_url])
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^LEASE_CONTAINER_CONFIGURATION_MISMATCH$",
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_missing_or_extra_child_readback_transcript_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        missing = dict(arguments)
        missing.pop("lease_container_readback_envelope")
        with self.assertRaises(TypeError):
            verify_azure_performance_infrastructure_safety(**missing)

        envelope = deepcopy(
            arguments["coordination_blob_service_readback_envelope"]
        )
        envelope["sealed_execution"]["operations"].append(
            deepcopy(envelope["sealed_execution"]["operations"][0])
        )
        self.assertFalse(
            infrastructure_safety._sealed_observation_matches(
                envelope,
                session=arguments["readback_session"].session,
            )
        )

    def test_rejects_missing_or_malformed_resource_access_rules(self) -> None:
        variants = {
            "missing": None,
            "null": None,
            "mapping": {},
            "string": "none",
        }
        coordination_url = (
            f"https://management.azure.com{COORDINATION_ID}?api-version=2023-05-01"
        )
        for name, rules in variants.items():
            with self.subTest(name=name):
                responses = _responses()
                network_acls = responses[coordination_url]["properties"]["networkAcls"]
                if name == "missing":
                    network_acls.pop("resourceAccessRules")
                else:
                    network_acls["resourceAccessRules"] = rules
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^COORDINATION_STORAGE_CONFIGURATION_MISMATCH$",
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_any_present_or_unknown_resource_access_rule(self) -> None:
        variants = {
            "present": [{"resourceId": BFF_ID, "tenantId": TENANT_ID}],
            "unknown": [{"unexpected": "rule"}],
        }
        coordination_url = (
            f"https://management.azure.com{COORDINATION_ID}?api-version=2023-05-01"
        )
        for name, rules in variants.items():
            with self.subTest(name=name):
                responses = _responses()
                responses[coordination_url]["properties"]["networkAcls"][
                    "resourceAccessRules"
                ] = rules
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^COORDINATION_STORAGE_CONFIGURATION_MISMATCH$",
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_serialized_evidence_does_not_recreate_authorization_capability(self) -> None:
        serialized = json.loads(json.dumps(_issue_evidence(), sort_keys=True))
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED$",
        ):
            validate_infrastructure_safety_evidence(serialized)

    def test_tampered_or_fabricated_transcript_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        envelope = deepcopy(arguments["bff_storage_readback_envelope"])
        envelope["payload"]["resource_id"] = WORM_ID
        envelope["observation_sha256"] = canonical_observation_sha256(envelope)
        arguments["bff_storage_readback_envelope"] = envelope
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^SEALED_READBACK_CAPABILITY_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_imported_seal_and_mint_surfaces_do_not_exist(self) -> None:
        self.assertFalse(hasattr(infrastructure_safety, "_CAPABILITY_SEAL"))
        self.assertFalse(hasattr(infrastructure_safety, "_PROCESS_AUTHORITY"))
        self.assertFalse(hasattr(infrastructure_safety, "_ProcessReadbackAuthority"))
        self.assertNotIn(
            "_issue", AzurePerformanceInfrastructureReadbackCapability.__dict__
        )
        self.assertNotIn(
            "_issue", AzurePerformanceInfrastructureReadbackResult.__dict__
        )
        self.assertNotIn(
            "_issue", AzurePerformanceInfrastructureSafetyVerification.__dict__
        )

    def test_registry_mutation_cannot_authorize_forged_readback_result(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        original = arguments["bff_storage_readback_envelope"]
        capability = arguments["readback_session"]
        forged = object.__new__(AzurePerformanceInfrastructureReadbackResult)
        object.__setattr__(
            forged, "_canonical_evidence", original._canonical_evidence
        )
        object.__setattr__(forged, "_capability", capability)
        object.__setattr__(forged, "_authenticator", b"\x00" * 32)
        forged_registry = {
            id(forged): (forged, capability, forged._canonical_evidence)
        }
        setattr(
            infrastructure_safety,
            "_ISSUED_READBACK_RESULTS",
            forged_registry,
        )
        setattr(
            infrastructure_safety,
            "_ISSUED_READBACK_CAPABILITIES",
            {capability.session.session_sha256: capability},
        )
        self.addCleanup(
            lambda: delattr(infrastructure_safety, "_ISSUED_READBACK_RESULTS")
        )
        self.addCleanup(
            lambda: delattr(infrastructure_safety, "_ISSUED_READBACK_CAPABILITIES")
        )
        arguments["bff_storage_readback_envelope"] = forged
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^SEALED_READBACK_CAPABILITY_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_registry_mutation_cannot_authorize_forged_safe_result(self) -> None:
        original = _issue_evidence()
        forged = dict.__new__(AzurePerformanceInfrastructureSafetyVerification)
        dict.__init__(forged, dict(original))
        forged._canonical_evidence = original._canonical_evidence
        forged._readback_capability = original._readback_capability
        forged._authenticator = b"\x00" * 32
        setattr(
            infrastructure_safety,
            "_ISSUED_SAFETY_VERIFICATIONS",
            {
                id(forged): (
                    forged,
                    forged._readback_capability,
                    forged._canonical_evidence,
                )
            },
        )
        self.addCleanup(
            lambda: delattr(infrastructure_safety, "_ISSUED_SAFETY_VERIFICATIONS")
        )
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID$",
        ):
            validate_infrastructure_safety_evidence(forged)

    def test_copied_capability_result_and_verification_do_not_authorize(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        with self.assertRaisesRegex(TypeError, "cannot be copied"):
            copy(arguments["readback_session"])

        copied_result = copy(arguments["bff_storage_readback_envelope"])
        self.assertIsInstance(copied_result, dict)
        arguments["bff_storage_readback_envelope"] = copied_result
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^SEALED_READBACK_CAPABILITY_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

        evidence = _issue_evidence()
        cloned_verification = dict.__new__(
            AzurePerformanceInfrastructureSafetyVerification
        )
        dict.__init__(cloned_verification, dict(evidence))
        cloned_verification._canonical_evidence = evidence._canonical_evidence
        cloned_verification._readback_capability = evidence._readback_capability
        cloned_verification._authenticator = evidence._authenticator
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID$",
        ):
            validate_infrastructure_safety_evidence(cloned_verification)

        copied_verification = copy(evidence)
        self.assertIsInstance(copied_verification, dict)
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED$",
        ):
            validate_infrastructure_safety_evidence(copied_verification)

    def test_unknown_graph_or_arm_paging_is_fail_closed(self) -> None:
        responses = _responses()
        graph_url = (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/{PRINCIPAL_ID}/"
            "transitiveMemberOf/microsoft.graph.group?$select=id"
        )
        responses[graph_url] = {
            "value": [{"id": GROUP_ID}],
            "@odata.nextLink": graph_url + "&$skiptoken=opaque",
        }
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "^EFFECTIVE_RBAC_READBACK_INCOMPLETE$",
            ):
                _build_arguments(Path(value))

    def test_executable_is_rechecked_immediately_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            fake_az, _ = _write_fake_az(Path(value))
            session = _session()
            calls = 0

            def measured(_path):
                nonlocal calls
                calls += 1
                return "a" * 64 if calls == 1 else "f" * 64

            with patch(
                "nac_bff.azure_performance_infrastructure_safety.AZURE_CLI_EXECUTION_PATH",
                fake_az,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety.calculate_azure_cli_toolchain_sha256",
                side_effect=measured,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety.calculate_toolchain_attestations_sha256",
                return_value=TOOLCHAIN_BINDING,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety._prepare_bound_runtime",
                side_effect=_prepare_test_runtime,
            ):
                adapter = AzurePerformanceInfrastructureReadbackAdapter(
                    session, toolchain_attestations=ADAPTER_TOOLCHAIN
                )
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^AZURE_CLI_TOOLCHAIN_CHANGED_DURING_READBACK$",
                ):
                    adapter.execute_read(
                        observation_kind="bff-storage-account-resource-id",
                        resource_id=BFF_ID,
                    )

    def test_path_replacement_during_launch_executes_measured_fd(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            directory = Path(value)
            fake_az, environment_log = _write_fake_az(directory)
            replacement_ran = directory / "replacement-ran"
            session = _session()

            def seal_then_replace(path: Path, **_kwargs: object):
                runtime = _FdBackedTestRuntime(path)
                replacement = directory / "replacement"
                replacement.write_text(
                    f"#!{sys.executable}\n"
                    "from pathlib import Path\n"
                    f"Path({str(replacement_ran)!r}).write_text('unsafe')\n",
                    encoding="utf-8",
                )
                replacement.chmod(0o755)
                os.replace(replacement, path)
                return runtime

            with patch(
                "nac_bff.azure_performance_infrastructure_safety.AZURE_CLI_EXECUTION_PATH",
                fake_az,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety.calculate_azure_cli_toolchain_sha256",
                return_value="a" * 64,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety.calculate_toolchain_attestations_sha256",
                return_value=TOOLCHAIN_BINDING,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety._prepare_bound_runtime",
                side_effect=seal_then_replace,
            ):
                adapter = AzurePerformanceInfrastructureReadbackAdapter(
                    session, toolchain_attestations=ADAPTER_TOOLCHAIN
                )
                result = adapter.execute_read(
                    observation_kind="bff-storage-account-resource-id",
                    resource_id=BFF_ID,
                )

            self.assertIsInstance(
                result, AzurePerformanceInfrastructureReadbackResult
            )
            self.assertTrue(environment_log.exists())
            self.assertFalse(replacement_ran.exists())

    def test_rejects_all_transcript_executable_digests_rehashed(self) -> None:
        evidence = deepcopy(_issue_evidence())
        forged_executable_sha256 = "f" * 64
        transcript = evidence["readback_transcript"]
        for name, envelope in transcript.items():
            sealed = envelope["sealed_execution"]
            for operation in sealed["operations"]:
                operation["executable_sha256"] = forged_executable_sha256
            attestation = envelope["execution_attestation"]
            envelope["observation_command_sha256"] = _json_sha256(
                {
                    "schema_version": sealed["schema_version"],
                    "observation_kind": envelope["observation_kind"],
                    "readback_session_sha256": envelope[
                        "readback_session_sha256"
                    ],
                    "nonce_sha256": attestation["nonce_sha256"],
                    "execution_attestation_sha256": _json_sha256(attestation),
                    "sealed_execution": sealed,
                }
            )
            envelope["observation_sha256"] = canonical_observation_sha256(
                envelope
            )
            evidence["readback_observation_sha256"][name] = envelope[
                "observation_sha256"
            ]
        evidence["deployment_receipt_sha256"] = transcript[
            "deployment_receipt"
        ]["observation_sha256"]
        unsigned = dict(evidence)
        unsigned.pop("infrastructure_safety_evidence_sha256")
        evidence["infrastructure_safety_evidence_sha256"] = _json_sha256(unsigned)

        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED$",
        ):
            validate_infrastructure_safety_evidence(evidence)

    def test_rejects_tampered_safety_evidence(self) -> None:
        evidence = _issue_evidence()
        fabricated = deepcopy(evidence)
        fabricated["bootstrap_effective_assignment_count"] = 2
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED$",
        ):
            validate_infrastructure_safety_evidence(fabricated)

    def test_verifier_capability_detects_base_dict_mutation(self) -> None:
        evidence = _issue_evidence()
        dict.__setitem__(evidence, "bootstrap_effective_assignment_count", 2)
        with self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_INVALID$",
        ):
            validate_infrastructure_safety_evidence(evidence)

    def test_rejects_forged_safe_summary_with_recomputed_digest(self) -> None:
        evidence = _issue_evidence()
        fabricated = deepcopy(evidence)
        fabricated["runtime_effective_principal_count"] = 99
        unsigned = dict(fabricated)
        unsigned.pop("infrastructure_safety_evidence_sha256")
        fabricated["infrastructure_safety_evidence_sha256"] = _json_sha256(unsigned)
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^INFRASTRUCTURE_SAFETY_CAPABILITY_REQUIRED$",
        ):
            validate_infrastructure_safety_evidence(fabricated)

    def test_readback_session_replay_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ):
            verify_azure_performance_infrastructure_safety(**arguments)
        ledger_entries = list(self.ledger_directory.iterdir())
        self.assertEqual(stat.S_IMODE(self.ledger_directory.stat().st_mode), 0o700)
        self.assertEqual(len(ledger_entries), 1)
        self.assertEqual(stat.S_IMODE(ledger_entries[0].stat().st_mode), 0o600)
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^READBACK_SESSION_REPLAYED$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_mixed_case_arm_principal_ids_are_canonicalized(self) -> None:
        responses = _responses()
        mixed_principal = PRINCIPAL_ID.upper()
        mixed_group = GROUP_ID.upper()
        graph_url = (
            f"https://graph.microsoft.com/v1.0/servicePrincipals/{PRINCIPAL_ID}/"
            "transitiveMemberOf/microsoft.graph.group?$select=id"
        )
        responses[graph_url] = {"value": [{"id": mixed_group}]}
        responses[
            f"https://management.azure.com{ROLE_ASSIGNMENT_ID}"
            "?api-version=2022-04-01"
        ]["properties"]["principalId"] = mixed_principal
        container_url = (
            f"https://management.azure.com{CONTAINER_SCOPE}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        responses[container_url]["value"][0]["properties"][
            "principalId"
        ] = mixed_principal
        responses[
            f"https://management.azure.com{DEPLOYMENT_ID}?api-version=2022-09-01"
        ]["properties"]["parameters"]["bootstrapPrincipalId"][
            "value"
        ] = mixed_principal
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments, _ = _build_arguments(Path(value))
        arguments["bootstrap_principal_id"] = mixed_principal
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ):
            evidence = verify_azure_performance_infrastructure_safety(**arguments)
            validated = validate_infrastructure_safety_evidence(evidence)
        self.assertEqual(validated["bootstrap_principal_id"], PRINCIPAL_ID)

    def test_persists_create_once_receipts_and_reconciles_exact_deployment(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            arguments, _ = _build_arguments(root)
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

            state = store.load()
            reconciled = store.reconcile_successful_deployment(
                arguments["deployment_receipt_envelope"]
            )
            fabricated_arguments = dict(arguments)
            fabricated_arguments["coordination_name_readback_envelope"] = dict(
                original
            )
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "^INFRASTRUCTURE_ORIGINAL_NAME_RECEIPT_CAPABILITY_REQUIRED$",
            ):
                verify_azure_performance_infrastructure_safety(
                    **fabricated_arguments
                )
            arguments["coordination_name_readback_envelope"] = original
            with patch(
                "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                return_value=VERIFY_AT,
            ):
                evidence = verify_azure_performance_infrastructure_safety(
                    **arguments
                )

            self.assertEqual(state["status"], "COMPLETE")
            self.assertEqual(evidence["status"], "SAFE")
            self.assertEqual(
                successful["original_name_receipt_sha256"],
                original["observation_sha256"],
            )
            self.assertEqual(reconciled, successful)
            self.assertEqual(
                stat.S_IMODE(
                    (store.directory / store._NAME_FILE).stat().st_mode
                ),
                0o400,
            )
            self.assertEqual(
                stat.S_IMODE(
                    (store.directory / store._DEPLOYMENT_FILE).stat().st_mode
                ),
                0o400,
            )
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "^INFRASTRUCTURE_ORIGINAL_NAME_RECEIPT_ALREADY_EXISTS$",
            ):
                store.persist_original_name_available(
                    arguments["coordination_name_readback_envelope"]
                )

    def test_restart_receipt_tamper_and_incomplete_pair_block(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            arguments, _ = _build_arguments(root)
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
            name_path = store.directory / store._NAME_FILE
            name_path.chmod(0o600)
            tampered = json.loads(name_path.read_text(encoding="ascii"))
            tampered["observed_at_utc"] = "2026-08-03T11:59:59Z"
            name_path.write_text(json.dumps(tampered) + "\n", encoding="ascii")
            name_path.chmod(0o400)
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "^INFRASTRUCTURE_ORIGINAL_NAME_RECEIPT_INVALID$",
            ):
                store.load()

        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            arguments, _ = _build_arguments(root)
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
            (store.directory / store._NAME_FILE).unlink()
            with self.assertRaisesRegex(
                AzurePerformanceInfrastructureSafetyError,
                "^INFRASTRUCTURE_RESTART_RECEIPTS_INCOMPLETE$",
            ):
                store.load()

    def test_running_failed_replaced_or_mismatched_deployment_blocks(self) -> None:
        variants = {
            "running": ("provisioningState", "Running", "INVALID"),
            "failed": ("provisioningState", "Failed", "INVALID"),
            "replaced": ("timestamp", "2026-08-03T12:00:02Z", "REPLACED"),
            "mismatch": ("targetBindingSha256", "9" * 64, "INVALID"),
        }
        with tempfile.TemporaryDirectory() as value:
            root = Path(value)
            initial = root / "initial"
            initial.mkdir()
            arguments, _ = _build_arguments(initial)
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
            for index, (label, (field, changed, code)) in enumerate(variants.items()):
                with self.subTest(label=label):
                    responses = _responses()
                    deployment = responses[
                        f"https://management.azure.com{DEPLOYMENT_ID}"
                        "?api-version=2022-09-01"
                    ]
                    if field == "targetBindingSha256":
                        deployment["properties"]["parameters"][field]["value"] = changed
                    else:
                        deployment["properties"][field] = changed
                    current = root / f"current-{index}"
                    current.mkdir()
                    with patch(__name__ + "._responses", return_value=responses):
                        changed_arguments, _ = _build_arguments(current)
                    expected_code = (
                        "INFRASTRUCTURE_DEPLOYMENT_REPLACED"
                        if code == "REPLACED"
                        else "INFRASTRUCTURE_RECONCILIATION_DEPLOYMENT_INVALID"
                    )
                    with self.assertRaisesRegex(
                        AzurePerformanceInfrastructureSafetyError,
                        f"^{expected_code}$",
                    ):
                        store.reconcile_successful_deployment(
                            changed_arguments["deployment_receipt_envelope"]
                        )

    def test_existing_name_never_authorizes_reconciliation(self) -> None:
        responses = _responses()
        name_url = (
            f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/"
            "Microsoft.Storage/checkNameAvailability?api-version=2023-05-01"
        )
        responses[name_url] = {"nameAvailable": False}
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ):
            arguments, _ = _build_arguments(Path(value))
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^COORDINATION_NAME_READBACK_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_authoritative_bff_and_worm_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        arguments["bff_storage_account_resource_id"] = WORM_ID
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^AUTHORITATIVE_BFF_STORAGE_MISMATCH$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_requires_complete_root_management_group_and_group_attestation(self) -> None:
        responses = _responses()
        ancestry_url = (
            f"https://management.azure.com{ROOT_MG}?api-version=2021-04-01"
            "&$expand=children&$recurse=true"
        )
        responses[ancestry_url] = {"id": ROOT_MG, "properties": {"children": []}}
        with tempfile.TemporaryDirectory() as value, patch(
            __name__ + "._responses", return_value=responses
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^SUBSCRIPTION_ANCESTRY_READBACK_INVALID$",
        ):
            _build_arguments(Path(value))

    def test_rejects_tampered_effective_rbac_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            arguments, _ = _build_arguments(Path(value))
        envelope = deepcopy(
            arguments["bootstrap_effective_rbac_readback_envelope"]
        )
        envelope["payload"]["transitive_group_principal_ids"] = []
        arguments["bootstrap_effective_rbac_readback_envelope"] = envelope
        with patch(
            "nac_bff.azure_performance_infrastructure_safety._trusted_now",
            return_value=VERIFY_AT,
        ), self.assertRaisesRegex(
            AzurePerformanceInfrastructureSafetyError,
            "^SEALED_READBACK_CAPABILITY_INVALID$",
        ):
            verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_broader_effective_assignment_at_each_ancestor(self) -> None:
        for index, scope in enumerate(_ancestor_scopes()):
            with self.subTest(scope=scope):
                responses = _responses()
                prefix = "" if scope == "/" else scope
                url = (
                    f"https://management.azure.com{prefix}/providers/"
                    "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
                    "&$filter=atScope()"
                )
                broader = {
                    "id": (
                        f"{prefix}/providers/Microsoft.Authorization/roleAssignments/"
                        f"{index + 4}4444444-2222-4333-8444-555555555555"
                    ),
                    "properties": {
                        "principalId": GROUP_ID,
                        "principalType": "Group",
                        "roleDefinitionId": ROLE_DEFINITION_ID,
                    },
                }
                responses[url]["value"].append(broader)
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^BROADER_EFFECTIVE_ASSIGNMENT_PRESENT$",
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_rejects_missing_duplicate_or_unresolved_effective_assignment(self) -> None:
        container_url = (
            f"https://management.azure.com{CONTAINER_SCOPE}/providers/"
            "Microsoft.Authorization/roleAssignments?api-version=2022-04-01"
            "&$filter=atScope()"
        )
        variants = (
            ([], "EXPECTED_EFFECTIVE_ASSIGNMENT_NOT_UNIQUE"),
            ([_role_assignment(), _role_assignment()], "EXPECTED_EFFECTIVE_ASSIGNMENT_NOT_UNIQUE"),
        )
        for assignments, error in variants:
            with self.subTest(error=error, count=len(assignments)):
                responses = _responses()
                responses[container_url] = {"value": assignments}
                with tempfile.TemporaryDirectory() as value, patch(
                    __name__ + "._responses", return_value=responses
                ):
                    arguments, _ = _build_arguments(Path(value))
                with patch(
                    "nac_bff.azure_performance_infrastructure_safety._trusted_now",
                    return_value=VERIFY_AT,
                ), self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError, f"^{error}$"
                ):
                    verify_azure_performance_infrastructure_safety(**arguments)

    def test_unknown_public_read_operation_is_rejected_before_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            fake_az, environment_log = _write_fake_az(Path(value))
            session = _session()
            with patch(
                "nac_bff.azure_performance_infrastructure_safety.AZURE_CLI_EXECUTION_PATH",
                fake_az,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety.calculate_azure_cli_toolchain_sha256",
                return_value="a" * 64,
            ), patch(
                "nac_bff.azure_performance_infrastructure_safety.calculate_toolchain_attestations_sha256",
                return_value=TOOLCHAIN_BINDING,
            ):
                adapter = AzurePerformanceInfrastructureReadbackAdapter(
                    session, toolchain_attestations=ADAPTER_TOOLCHAIN
                )
                with self.assertRaisesRegex(
                    AzurePerformanceInfrastructureSafetyError,
                    "^SEALED_AZURE_READ_COMMAND_NOT_ALLOWED$",
                ):
                    adapter.execute_read(
                        observation_kind="arbitrary-read", resource_id=BFF_ID
                    )
            self.assertFalse(environment_log.exists())


if __name__ == "__main__":
    unittest.main()
