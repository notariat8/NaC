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
BLOB_ADD = (
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action"
)
BLOB_WRITE = (
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
)
BOOTSTRAP_ACTIONS = {BLOB_READ, BLOB_ADD}
RUNTIME_ACTIONS = {BLOB_READ, BLOB_WRITE}
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
            "value: allowedClientIpAddress",
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

    def test_owner_gated_blob_bootstrap_contract_matches_runtime_path(self) -> None:
        for marker in (
            "var containerName = 'nac-bff-performance-leases'",
            "var leaseBlobPath = 'locks/${targetBindingSha256}.lock'",
            "lease_blob_type: 'BlockBlob'",
            "lease_blob_content_length: '0'",
            "lease_blob_bootstrap: 'owner-gated-put-if-absent-before-runtime'",
            "output blobBootstrapRequired bool = true",
            "output blobBootstrapExecutedByTemplate bool = false",
        ):
            self.assertIn(marker, self.source)
        self.assertRegex(
            self.source,
            r"@minLength\(64\)\s*@maxLength\(64\)\s*param targetBindingSha256 string",
        )

    def test_source_forces_distinct_bootstrap_and_runtime_principals(self) -> None:
        for marker in (
            "param bootstrapPrincipalId string",
            "param runtimePrincipalId string",
            "toLower(bootstrapPrincipalId) != toLower(runtimePrincipalId)",
            "fail('Bootstrap and runtime principal and certificate identities must be different.')",
            "principal_separation: 'distinct-owner-bound-bootstrap-and-runtime-principals'",
            "output principalSeparationMode string = 'DISTINCT_BOOTSTRAP_AND_RUNTIME_PRINCIPALS'",
        ):
            self.assertIn(marker, self.source)
        self.assertNotIn("provisionerPrincipalId", self.source)
        self.assertEqual(
            self.source.count(
                "toLower(bootstrapPrincipalId) != toLower(runtimePrincipalId)"
            ),
            2,
        )

    def test_source_roles_have_exact_disjoint_write_capabilities(self) -> None:
        bootstrap_match = re.search(
            r"resource bootstrapLeaseDataRole .*?\n\}\n\nresource runtimeLeaseDataRole",
            self.source,
            flags=re.DOTALL,
        )
        runtime_match = re.search(
            r"resource runtimeLeaseDataRole .*?\n\}\n\nresource bootstrapLeaseBinding",
            self.source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(bootstrap_match)
        self.assertIsNotNone(runtime_match)

        action_pattern = r"'(Microsoft\.Storage/storageAccounts/blobServices/containers/blobs/[^']+)'"
        bootstrap_actions = set(re.findall(action_pattern, bootstrap_match.group(0)))
        runtime_actions = set(re.findall(action_pattern, runtime_match.group(0)))
        self.assertEqual(bootstrap_actions, BOOTSTRAP_ACTIONS)
        self.assertEqual(runtime_actions, RUNTIME_ACTIONS)
        self.assertNotIn(BLOB_WRITE, bootstrap_actions)
        self.assertNotIn(BLOB_ADD, runtime_actions)
        self.assertNotIn("/blobs/delete", bootstrap_match.group(0))
        self.assertNotIn("/blobs/delete", runtime_match.group(0))

    def test_source_assignments_bind_each_identity_to_its_role_and_condition(self) -> None:
        for marker in (
            "resource bootstrapLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01'",
            "principalId: validatedBootstrapPrincipalId",
            "roleDefinitionId: bootstrapLeaseDataRole.id",
            "condition: exactBootstrapLeaseBlobCondition",
            "resource runtimeLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01'",
            "principalId: validatedRuntimePrincipalId",
            "roleDefinitionId: runtimeLeaseDataRole.id",
            "condition: exactRuntimeLeaseBlobCondition",
        ):
            self.assertIn(marker, self.source)
        self.assertEqual(
            self.source.count(
                "resource bootstrapLeaseBinding 'Microsoft.Authorization/roleAssignments"
            ),
            1,
        )
        self.assertEqual(
            self.source.count(
                "resource runtimeLeaseBinding 'Microsoft.Authorization/roleAssignments"
            ),
            1,
        )

    def test_source_abac_conditions_are_identity_specific_and_exact_path(self) -> None:
        bootstrap_condition = re.search(
            r"var exactBootstrapLeaseBlobCondition = (.*)", self.source
        ).group(1)
        runtime_condition = re.search(
            r"var exactRuntimeLeaseBlobCondition = (.*)", self.source
        ).group(1)
        for condition in (bootstrap_condition, runtime_condition):
            self.assertIn("containers:name] StringEquals", condition)
            self.assertIn("containers/blobs:path] StringEquals", condition)
            self.assertIn("${containerName}", condition)
            self.assertIn("${leaseBlobPath}", condition)
            self.assertNotIn("StringLike", condition)
            self.assertNotIn("StringStartsWith", condition)
        self.assertIn("${blobAddDataAction}", bootstrap_condition)
        self.assertNotIn("${blobWriteDataAction}", bootstrap_condition)
        self.assertIn("${blobWriteDataAction}", runtime_condition)
        self.assertNotIn("${blobAddDataAction}", runtime_condition)

    def test_source_metadata_and_outputs_document_identity_boundaries(self) -> None:
        for marker in (
            "bootstrap_authorization: 'blob-read-plus-add-only-no-write-no-delete'",
            "runtime_authorization: 'blob-read-plus-write-only-no-add-no-delete'",
            "output bootstrapLeaseDataRoleDefinitionId string = bootstrapLeaseDataRole.id",
            "output runtimeLeaseDataRoleDefinitionId string = runtimeLeaseDataRole.id",
            "output bootstrapLeaseRoleAssignmentId string = bootstrapLeaseBinding.id",
            "output runtimeLeaseRoleAssignmentId string = runtimeLeaseBinding.id",
            "output bootstrapAllowedDataActions array",
            "output runtimeAllowedDataActions array",
        ):
            self.assertIn(marker, self.source)
        self.assertNotIn("output allowedDataActions array", self.source)
        self.assertNotIn("newGuid(", self.source)
        self.assertNotIn("utcNow(", self.source)

    def test_example_parameters_are_complete_synthetic_and_distinct(self) -> None:
        for marker in (
            "using './main.bicep'",
            "param bootstrapPrincipalId = '11111111-2222-4333-8444-555555555555'",
            "param runtimePrincipalId = '66666666-7777-4888-8999-aaaaaaaaaaaa'",
            "param allowedClientIpAddress = '203.0.113.10'",
            "param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'",
            "Bootstrap can only read/add the exact bound blob.",
            "Runtime can only read/write it",
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

    def test_compiled_parameter_contract_replaces_provisioner(self) -> None:
        expected_parameters = {
            "location",
            "tenantId",
            "subscriptionId",
            "resourceGroupName",
            "deploymentMode",
            "storageAccountName",
            "bffStorageAccountResourceId",
            "wormStorageAccountResourceId",
            "bootstrapPrincipalId",
            "runtimePrincipalId",
            "bootstrapCertificateSha256",
            "runtimeCertificateSha256",
            "allowedClientIpAddress",
            "targetBindingSha256",
            "tags",
        }
        self.assertEqual(set(self.template["parameters"]), expected_parameters)
        self.assertEqual(set(self.parameters["parameters"]), expected_parameters)
        self.assertNotIn("provisionerPrincipalId", self.template["parameters"])
        self.assertNotEqual(
            self.parameters["parameters"]["bootstrapPrincipalId"]["value"],
            self.parameters["parameters"]["runtimePrincipalId"]["value"],
        )

    def test_compiled_template_has_exact_resource_counts(self) -> None:
        self.assertEqual(
            Counter(resource["type"] for resource in self.template["resources"]),
            Counter(
                {
                    "Microsoft.Storage/storageAccounts": 1,
                    "Microsoft.Storage/storageAccounts/blobServices": 1,
                    "Microsoft.Storage/storageAccounts/blobServices/containers": 1,
                    "Microsoft.Authorization/roleDefinitions": 2,
                    "Microsoft.Authorization/roleAssignments": 2,
                }
            ),
        )

    def test_compiled_principal_guard_is_fail_closed(self) -> None:
        expected_guard = (
            "not(equals(toLower(parameters('bootstrapPrincipalId')), "
            "toLower(parameters('runtimePrincipalId'))))"
        )
        for variable_name, expected_parameter in (
            ("validatedBootstrapPrincipalId", "bootstrapPrincipalId"),
            ("validatedRuntimePrincipalId", "runtimePrincipalId"),
        ):
            expression = self.template["variables"][variable_name]
            self.assertIn(expected_guard, expression)
            self.assertIn(f"parameters('{expected_parameter}')", expression)
            self.assertIn(
                "fail('Bootstrap and runtime principal and certificate identities must be different.')",
                expression,
            )
            self.assertIn(
                "not(equals(parameters('bootstrapCertificateSha256'), "
                "parameters('runtimeCertificateSha256')))",
                expression,
            )

    def test_compiled_custom_roles_are_exact_and_never_combine_add_write(self) -> None:
        roles = resources_of_type(
            self.template, "Microsoft.Authorization/roleDefinitions"
        )
        roles_by_name = {role["name"]: role for role in roles}
        expected = {
            "[variables('bootstrapLeaseDataRoleDefinitionGuid')]": BOOTSTRAP_ACTIONS,
            "[variables('runtimeLeaseDataRoleDefinitionGuid')]": RUNTIME_ACTIONS,
        }
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
            self.assertFalse({BLOB_ADD, BLOB_WRITE} <= expected_actions)
            self.assertFalse(any(action.endswith("/delete") for action in expected_actions))

    def test_compiled_assignments_bind_distinct_principals_roles_and_conditions(self) -> None:
        assignments = resources_of_type(
            self.template, "Microsoft.Authorization/roleAssignments"
        )
        by_principal = {
            assignment["properties"]["principalId"]: assignment
            for assignment in assignments
        }
        expected = {
            "[variables('validatedBootstrapPrincipalId')]": (
                "bootstrapLeaseDataRoleDefinitionGuid",
                "exactBootstrapLeaseBlobCondition",
            ),
            "[variables('validatedRuntimePrincipalId')]": (
                "runtimeLeaseDataRoleDefinitionGuid",
                "exactRuntimeLeaseBlobCondition",
            ),
        }
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

    def test_compiled_conditions_bind_only_the_exact_blob_path(self) -> None:
        variables = self.template["variables"]
        bootstrap = variables["exactBootstrapLeaseBlobCondition"]
        runtime = variables["exactRuntimeLeaseBlobCondition"]
        for condition in (bootstrap, runtime):
            self.assertIn("containers:name] StringEquals", condition)
            self.assertIn("containers/blobs:path] StringEquals", condition)
            self.assertIn("variables('containerName')", condition)
            self.assertIn("variables('leaseBlobPath')", condition)
            self.assertNotIn("StringLike", condition)
            self.assertNotIn("StringStartsWith", condition)
        self.assertIn("variables('blobAddDataAction')", bootstrap)
        self.assertNotIn("variables('blobWriteDataAction')", bootstrap)
        self.assertIn("variables('blobWriteDataAction')", runtime)
        self.assertNotIn("variables('blobAddDataAction')", runtime)

    def test_compiled_outputs_are_unambiguous_per_identity(self) -> None:
        outputs = self.template["outputs"]
        expected = {
            "bootstrapLeaseDataRoleDefinitionId",
            "runtimeLeaseDataRoleDefinitionId",
            "bootstrapLeaseRoleAssignmentId",
            "runtimeLeaseRoleAssignmentId",
            "bootstrapAllowedDataActions",
            "runtimeAllowedDataActions",
            "principalSeparationMode",
        }
        self.assertTrue(expected <= set(outputs))
        self.assertEqual(
            outputs["bootstrapAllowedDataActions"]["value"],
            ["[variables('blobReadDataAction')]", "[variables('blobAddDataAction')]"],
        )
        self.assertEqual(
            outputs["runtimeAllowedDataActions"]["value"],
            ["[variables('blobReadDataAction')]", "[variables('blobWriteDataAction')]"],
        )
        self.assertEqual(
            outputs["principalSeparationMode"]["value"],
            "DISTINCT_BOOTSTRAP_AND_RUNTIME_PRINCIPALS",
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
            metadata["bootstrap_authorization"],
            "blob-read-plus-add-only-no-write-no-delete",
        )
        self.assertEqual(
            metadata["runtime_authorization"],
            "blob-read-plus-write-only-no-add-no-delete",
        )
        self.assertEqual(
            metadata["principal_separation"],
            "distinct-owner-bound-bootstrap-and-runtime-principals",
        )


if __name__ == "__main__":
    unittest.main()
