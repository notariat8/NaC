from collections import Counter
import json
from pathlib import Path
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_ROOT = (
    REPO_ROOT
    / "deploy"
    / "runtime"
    / "azure"
    / "nac-bff-performance-coordination"
)
QUALITY_GATE = REPO_ROOT / ".github" / "workflows" / "quality-gate.yml"
COMPILED_TEMPLATE = INFRA_ROOT / "compiled" / "main.json"
COMPILED_PARAMETERS = INFRA_ROOT / "compiled" / "main.example.json"

BLOB_READ = (
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
)
BLOB_WRITE = (
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
)
BROKER_ACTIONS = {BLOB_READ, BLOB_WRITE}
EXACT_CONTAINER_SCOPE = (
    "[resourceId('Microsoft.Storage/storageAccounts/blobServices/containers', "
    "variables('validatedStorageAccountName'), 'default', "
    "variables('containerName'))]"
)


def read_infra(name: str) -> str:
    path = INFRA_ROOT / name
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} is missing")
    return path.read_text(encoding="utf-8")


def resources_of_type(template: dict, resource_type: str) -> list[dict]:
    return [
        resource
        for resource in template["resources"]
        if resource["type"] == resource_type
    ]


class NaCBffPerformanceCoordinationIacTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = read_infra("main.bicep")
        cls.example_source = read_infra("main.example.bicepparam")
        cls.template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        cls.parameter_artifact = json.loads(
            COMPILED_PARAMETERS.read_text(encoding="utf-8")
        )
        cls.parameters = json.loads(cls.parameter_artifact["parametersJson"])
        cls.embedded_template = json.loads(cls.parameter_artifact["templateJson"])

    def test_storage_is_dedicated_from_bff_and_worm(self) -> None:
        for marker in (
            "param storageAccountName string",
            "param bffStorageAccountResourceId string",
            "param wormStorageAccountResourceId string",
            "toLower(coordinationStorageAccountResourceId) != toLower(validatedBffStorageAccountResourceId)",
            "toLower(coordinationStorageAccountResourceId) != toLower(validatedWormStorageAccountResourceId)",
            "toLower(validatedBffStorageAccountResourceId) != toLower(validatedWormStorageAccountResourceId)",
            "toLower(storageAccountName) != toLower(bffStorageAccountName)",
            "toLower(storageAccountName) != toLower(wormStorageAccountName)",
            "toLower(bffStorageAccountName) != toLower(wormStorageAccountName)",
            "fail('Performance coordination, BFF, and WORM storage accounts must be pairwise distinct.')",
        ):
            self.assertIn(marker, self.source)
        self.assertNotIn("immutableStorageWithVersioning", self.source)
        self.assertNotIn("immutabilityPolicies", self.source)

    def test_deployment_scope_and_resource_ids_fail_closed(self) -> None:
        for marker in (
            "tenant().tenantId == tenantId",
            "subscription().subscriptionId == subscriptionId",
            "resourceGroup().name == resourceGroupName",
            "fail('Performance coordination deployment scope does not match",
            "length(bffStorageAccountResourceIdSegments) == 9",
            "length(wormStorageAccountResourceIdSegments) == 9",
            "fail('BFF storage account resource ID is not an authoritative",
            "fail('WORM storage account resource ID is not an authoritative",
        ):
            self.assertIn(marker, self.source)

    def test_storage_disables_shared_keys_public_blobs_and_open_network(self) -> None:
        for marker in (
            "allowBlobPublicAccess: false",
            "allowCrossTenantReplication: false",
            "allowSharedKeyAccess: false",
            "defaultToOAuthAuthentication: true",
            "publicAccess: 'None'",
            "defaultAction: 'Deny'",
            "ipRules: brokerIpRules",
            "resourceAccessRules: []",
        ):
            self.assertIn(marker, self.source)
        lowered = self.source.lower()
        for forbidden in (
            "listkeys(",
            "sharedaccesssignature",
            "connectionstring",
            "microsoft.resources/deploymentscripts",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_owner_gated_broker_contract_matches_runtime_path(self) -> None:
        for marker in (
            "var containerName = 'nac-bff-performance-leases'",
            "var leaseBlobPath = 'locks/${targetBindingSha256}.lock'",
            "lease_blob_type: 'BlockBlob'",
            "lease_blob_content_length: '0'",
            "lease_blob_bootstrap: 'broker-internal-put-if-absent-before-acquire'",
            "local_runner_storage_authorization: 'none'",
            "output blobBootstrapRequired bool = true",
            "output blobBootstrapExecutedByTemplate bool = false",
        ):
            self.assertIn(marker, self.source)
        self.assertRegex(
            self.source,
            r"@minLength\(64\)\s*@maxLength\(64\)\s*param targetBindingSha256 string",
        )

    def test_source_binds_non_exportable_broker_identity_and_package(self) -> None:
        for marker in (
            "param brokerPrincipalId string",
            "param brokerCallerServicePrincipalId string",
            "param brokerFunctionAppResourceId string",
            "param brokerFunctionPackageSha256 string",
            "param brokerTicketVerificationCertificateSha256 string",
            "param brokerOutboundIpAddresses array",
            "output credentialBoundaryMode string = 'BFF_BROKER_UAMI_ONLY'",
            "output localRunnerStorageDataActions array = []",
        ):
            self.assertIn(marker, self.source)
        for forbidden in (
            "bootstrapPrincipalId",
            "runtimePrincipalId",
            "runtimeCertificateSha256",
            "allowedClientIpAddress",
        ):
            self.assertNotIn(forbidden, self.source)
        self.assertIn(
            "toLower(brokerPrincipalId) != toLower(brokerCallerServicePrincipalId)",
            self.source,
        )

    def test_source_role_is_exclusive_to_the_broker_uami(self) -> None:
        broker_match = re.search(
            r"resource brokerLeaseDataRole .*?\n\}\n\nresource brokerLeaseBinding",
            self.source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(broker_match)

        action_pattern = r"'(Microsoft\.Storage/storageAccounts/blobServices/containers/blobs/[^']+)'"
        broker_actions = set(re.findall(action_pattern, broker_match.group(0)))
        self.assertEqual(broker_actions, BROKER_ACTIONS)
        self.assertNotIn("/blobs/delete", broker_match.group(0))

    def test_source_assignment_binds_only_broker_uami_to_exact_path(self) -> None:
        for marker in (
            "resource brokerLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01'",
            "principalId: validatedBrokerPrincipalId",
            "roleDefinitionId: brokerLeaseDataRole.id",
            "condition: exactBrokerLeaseBlobCondition",
        ):
            self.assertIn(marker, self.source)
        self.assertEqual(
            self.source.count(
                "resource brokerLeaseBinding 'Microsoft.Authorization/roleAssignments"
            ),
            1,
        )

    def test_source_abac_condition_is_exact_path(self) -> None:
        broker_condition = re.search(
            r"var exactBrokerLeaseBlobCondition = (.*)", self.source
        ).group(1)
        self.assertIn("containers:name] StringEquals", broker_condition)
        self.assertIn("containers/blobs:path] StringEquals", broker_condition)
        self.assertIn("${containerName}", broker_condition)
        self.assertIn("${leaseBlobPath}", broker_condition)
        self.assertIn("${blobWriteDataAction}", broker_condition)
        self.assertNotIn("StringLike", broker_condition)
        self.assertNotIn("StringStartsWith", broker_condition)

    def test_source_metadata_and_outputs_document_identity_boundaries(self) -> None:
        for marker in (
            "broker_authorization: 'non-exportable-managed-identity-read-write-no-delete'",
            "operation_restriction_boundary: 'owner-ticketed-fixed-function-route'",
            "output brokerLeaseDataRoleDefinitionId string = brokerLeaseDataRole.id",
            "output brokerLeaseRoleAssignmentId string = brokerLeaseBinding.id",
            "output brokerAllowedDataActions array",
            "output localRunnerStorageDataActions array = []",
        ):
            self.assertIn(marker, self.source)
        self.assertNotIn("output allowedDataActions array", self.source)
        self.assertNotIn("newGuid(", self.source)
        self.assertNotIn("utcNow(", self.source)

    def test_example_parameters_are_complete_synthetic_and_distinct(self) -> None:
        for marker in (
            "using './main.bicep'",
            "param brokerPrincipalId = '11111111-2222-4333-8444-555555555555'",
            "param brokerFunctionAppResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/sites/fn-nac-bff-test'",
            "param brokerOutboundIpAddresses = [",
            "param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'",
            "Only the BFF Function managed identity receives exact-path Blob read/write.",
            "local runner receives a broker API role",
        ):
            self.assertIn(marker, self.example_source)
        self.assertNotIn("provisionerPrincipalId", self.example_source)

    def test_ci_uses_pinned_bicep_for_deterministic_compilation(self) -> None:
        workflow = QUALITY_GATE.read_text(encoding="utf-8")
        for marker in (
            "az bicep install --version v0.45.15",
            '"$HOME/.azure/bin/bicep" build deploy/runtime/azure/nac-bff-performance-coordination/main.bicep --stdout',
            '"$HOME/.azure/bin/bicep" build-params deploy/runtime/azure/nac-bff-performance-coordination/main.example.bicepparam --stdout',
            "cmp /tmp/nac-bff-performance-coordination-main.json deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.json",
            "cmp /tmp/nac-bff-performance-coordination-main-params.json deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.example.json",
        ):
            self.assertIn(marker, workflow)

    def test_compiled_artifacts_are_pinned_and_embedded_template_matches(self) -> None:
        self.assertEqual(
            self.template["metadata"]["_generator"]["version"],
            "0.45.15.27210",
        )
        self.assertEqual(self.parameter_artifact["templateSpecId"], None)
        self.assertEqual(self.embedded_template, self.template)

    def test_compiled_parameter_contract_binds_broker_boundary(self) -> None:
        expected_parameters = {
            "location",
            "tenantId",
            "subscriptionId",
            "resourceGroupName",
            "deploymentMode",
            "storageAccountName",
            "bffStorageAccountResourceId",
            "wormStorageAccountResourceId",
            "brokerPrincipalId",
            "brokerCallerServicePrincipalId",
            "brokerFunctionAppResourceId",
            "brokerFunctionPackageSha256",
            "brokerTicketVerificationCertificateSha256",
            "brokerOutboundIpAddresses",
            "targetBindingSha256",
            "tags",
        }
        self.assertEqual(set(self.template["parameters"]), expected_parameters)
        self.assertEqual(set(self.parameters["parameters"]), expected_parameters)
        self.assertNotIn("runtimePrincipalId", self.template["parameters"])

    def test_compiled_template_has_exact_resource_counts(self) -> None:
        self.assertEqual(
            Counter(resource["type"] for resource in self.template["resources"]),
            Counter(
                {
                    "Microsoft.Storage/storageAccounts": 1,
                    "Microsoft.Storage/storageAccounts/blobServices": 1,
                    "Microsoft.Storage/storageAccounts/blobServices/containers": 1,
                    "Microsoft.Authorization/roleDefinitions": 1,
                    "Microsoft.Authorization/roleAssignments": 1,
                }
            ),
        )

    def test_compiled_broker_resource_guard_is_fail_closed(self) -> None:
        expression = self.template["variables"]["validatedBrokerFunctionAppResourceId"]
        self.assertIn("microsoft.web", expression.lower())
        self.assertIn("fail('Broker Function App resource ID is not authoritative", expression)

    def test_compiled_custom_role_is_exact_and_broker_only(self) -> None:
        roles = resources_of_type(
            self.template, "Microsoft.Authorization/roleDefinitions"
        )
        roles_by_name = {role["name"]: role for role in roles}
        expected = {"[variables('brokerLeaseDataRoleDefinitionGuid')]": BROKER_ACTIONS}
        self.assertEqual(set(roles_by_name), set(expected))
        for name, expected_actions in expected.items():
            permission = roles_by_name[name]["properties"]["permissions"]
            self.assertEqual(len(permission), 1)
            self.assertEqual(set(permission[0]["dataActions"]), expected_actions)
            self.assertEqual(permission[0]["actions"], [])
            self.assertEqual(permission[0]["notActions"], [])
            self.assertEqual(permission[0]["notDataActions"], [])
            self.assertEqual(
                roles_by_name[name]["properties"]["assignableScopes"],
                ["[resourceGroup().id]"],
            )
            self.assertFalse(any(action.endswith("/delete") for action in expected_actions))

    def test_compiled_assignment_binds_only_broker_principal(self) -> None:
        assignments = resources_of_type(
            self.template, "Microsoft.Authorization/roleAssignments"
        )
        by_principal = {
            assignment["properties"]["principalId"]: assignment
            for assignment in assignments
        }
        expected = {"[variables('validatedBrokerPrincipalId')]": (
            "brokerLeaseDataRoleDefinitionGuid", "exactBrokerLeaseBlobCondition"
        )}
        self.assertEqual(set(by_principal), set(expected))
        for principal, (role_guid, condition) in expected.items():
            assignment = by_principal[principal]
            self.assertEqual(assignment["scope"], EXACT_CONTAINER_SCOPE)
            self.assertEqual(assignment["properties"]["conditionVersion"], "2.0")
            self.assertEqual(
                assignment["properties"]["condition"],
                f"[variables('{condition}')]",
            )
            self.assertEqual(
                assignment["properties"]["roleDefinitionId"],
                "[resourceId('Microsoft.Authorization/roleDefinitions', "
                f"variables('{role_guid}'))]",
            )
            self.assertIn(principal[1:-1], assignment["name"])
            self.assertIn("variables('leaseBlobPath')", assignment["name"])

    def test_compiled_condition_binds_only_the_exact_blob_path(self) -> None:
        variables = self.template["variables"]
        broker = variables["exactBrokerLeaseBlobCondition"]
        self.assertIn("containers:name] StringEquals", broker)
        self.assertIn("containers/blobs:path] StringEquals", broker)
        self.assertIn("variables('containerName')", broker)
        self.assertIn("variables('leaseBlobPath')", broker)
        self.assertIn("variables('blobWriteDataAction')", broker)
        self.assertNotIn("StringLike", broker)
        self.assertNotIn("StringStartsWith", broker)

    def test_compiled_outputs_are_unambiguous_for_broker_boundary(self) -> None:
        outputs = self.template["outputs"]
        expected = {
            "brokerLeaseDataRoleDefinitionId",
            "brokerLeaseRoleAssignmentId",
            "brokerAllowedDataActions",
            "brokerFunctionPackageSha256Binding",
            "brokerTicketVerificationCertificateSha256Binding",
            "localRunnerStorageDataActions",
            "credentialBoundaryMode",
        }
        self.assertTrue(expected <= set(outputs))
        self.assertEqual(
            outputs["brokerAllowedDataActions"]["value"],
            ["[variables('blobReadDataAction')]", "[variables('blobWriteDataAction')]"],
        )
        self.assertEqual(
            outputs["credentialBoundaryMode"]["value"],
            "BFF_BROKER_UAMI_ONLY",
        )
        self.assertNotIn("leaseDataRoleDefinitionId", outputs)
        self.assertNotIn("provisionerLeaseRoleAssignmentId", outputs)
        self.assertNotIn("allowedDataActions", outputs)

    def test_compiled_container_metadata_matches_identity_contract(self) -> None:
        container = resources_of_type(
            self.template,
            "Microsoft.Storage/storageAccounts/blobServices/containers",
        )[0]
        metadata = container["properties"]["metadata"]
        self.assertEqual(
            metadata["broker_authorization"],
            "non-exportable-managed-identity-read-write-no-delete",
        )
        self.assertEqual(
            metadata["operation_restriction_boundary"],
            "owner-ticketed-fixed-function-route",
        )
        self.assertEqual(
            metadata["local_runner_storage_authorization"],
            "none",
        )


if __name__ == "__main__":
    unittest.main()
