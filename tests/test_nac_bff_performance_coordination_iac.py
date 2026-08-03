from copy import deepcopy
import json
from pathlib import Path
import re
import unittest

import scripts.validate_nac_bff_performance_coordination_arm as arm_validator


REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_ROOT = (
    REPO_ROOT
    / "deploy"
    / "runtime"
    / "azure"
    / "nac-bff-performance-coordination"
)
ARM_VALIDATOR = REPO_ROOT / "scripts" / "validate_nac_bff_performance_coordination_arm.py"
QUALITY_GATE = REPO_ROOT / ".github" / "workflows" / "quality-gate.yml"
COMPILED_TEMPLATE = INFRA_ROOT / "compiled" / "main.json"
COMPILED_PARAMETERS = INFRA_ROOT / "compiled" / "main.example.json"


def read_infra(name: str) -> str:
    path = INFRA_ROOT / name
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} is missing")
    return path.read_text(encoding="utf-8")


class NaCBffPerformanceCoordinationIacTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = read_infra("main.bicep")
        cls.example_parameters = read_infra("main.example.bicepparam")

    def test_storage_is_dedicated_from_bff_and_worm(self) -> None:
        for parameter in (
            "param storageAccountName string",
            "param bffStorageAccountResourceId string",
            "param wormStorageAccountResourceId string",
        ):
            self.assertIn(parameter, self.template)
        for marker in (
            "var bffStorageAccountName = last(bffStorageAccountResourceIdSegments)",
            "var wormStorageAccountName = last(wormStorageAccountResourceIdSegments)",
            "toLower(coordinationStorageAccountResourceId) != toLower(validatedBffStorageAccountResourceId)",
            "toLower(coordinationStorageAccountResourceId) != toLower(validatedWormStorageAccountResourceId)",
            "toLower(validatedBffStorageAccountResourceId) != toLower(validatedWormStorageAccountResourceId)",
            "toLower(storageAccountName) != toLower(bffStorageAccountName)",
            "toLower(storageAccountName) != toLower(wormStorageAccountName)",
            "toLower(bffStorageAccountName) != toLower(wormStorageAccountName)",
        ):
            self.assertIn(marker, self.template)
        self.assertIn(
            "fail('Performance coordination, BFF, and WORM storage accounts must be pairwise distinct.')",
            self.template,
        )
        self.assertIn("workload: 'nac-bff-performance-coordination'", self.template)
        self.assertNotIn("immutableStorageWithVersioning", self.template)
        self.assertNotIn("immutabilityPolicies", self.template)

    def test_authoritative_storage_resource_ids_are_validated_and_output(self) -> None:
        for marker in (
            "length(bffStorageAccountResourceIdSegments) == 9",
            "length(wormStorageAccountResourceIdSegments) == 9",
            "bffStorageAccountResourceIdSegments[2] == subscriptionId",
            "wormStorageAccountResourceIdSegments[2] == subscriptionId",
            "toLower(bffStorageAccountResourceIdSegments[6]) == 'microsoft.storage'",
            "toLower(wormStorageAccountResourceIdSegments[7]) == 'storageaccounts'",
            "fail('BFF storage account resource ID is not an authoritative",
            "fail('WORM storage account resource ID is not an authoritative",
            "output bffStorageAccountResourceIdBinding string = validatedBffStorageAccountResourceId",
            "output wormStorageAccountResourceIdBinding string = validatedWormStorageAccountResourceId",
        ):
            self.assertIn(marker, self.template)

    def test_deployment_scope_is_fail_closed_inside_template(self) -> None:
        for marker in (
            "param tenantId string",
            "param subscriptionId string",
            "param resourceGroupName string",
            "tenant().tenantId == tenantId",
            "subscription().subscriptionId == subscriptionId",
            "resourceGroup().name == resourceGroupName",
            "fail('Performance coordination deployment scope does not match",
            "output deploymentScopeBinding string = validatedDeploymentScope",
        ):
            self.assertIn(marker, self.template)
        for marker in (
            "param tenantId = '870c862b-56f7-4c9b-b0d9-f1f7d32c835c'",
            "param subscriptionId = '37cd9645-6cb9-4278-88ee-e80377cd951c'",
            "param resourceGroupName = 'rg-nac-bff-test'",
        ):
            self.assertIn(marker, self.example_parameters)

    def test_storage_disables_shared_keys_public_blobs_and_open_network(self) -> None:
        for marker in (
            "allowBlobPublicAccess: false",
            "allowCrossTenantReplication: false",
            "allowSharedKeyAccess: false",
            "defaultToOAuthAuthentication: true",
            "isHnsEnabled: false",
            "minimumTlsVersion: 'TLS1_2'",
            "supportsHttpsTrafficOnly: true",
            "publicAccess: 'None'",
            "defaultAction: 'Deny'",
            "value: allowedClientIpAddress",
            "resourceAccessRules: []",
        ):
            self.assertIn(marker, self.template)
        lowered = self.template.lower()
        for forbidden in (
            "listkeys(",
            "sharedaccesssignature",
            "connectionstring",
            "@secure",
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
            "output requiredLeaseBlobType string = 'BlockBlob'",
            "output requiredLeaseBlobContentLength int = 0",
            "output blobBootstrapRequired bool = true",
            "output blobBootstrapExecutedByTemplate bool = false",
        ):
            self.assertIn(marker, self.template)
        self.assertRegex(
            self.template,
            r"@minLength\(64\)\s*@maxLength\(64\)\s*param targetBindingSha256 string",
        )

    def test_existing_provisioner_gets_only_blob_add_read_and_write_data_actions(self) -> None:
        self.assertIn("param provisionerPrincipalId string", self.template)
        self.assertIn("principalId: provisionerPrincipalId", self.template)
        self.assertNotIn("Microsoft.ManagedIdentity", self.template)
        role_match = re.search(
            r"resource leaseDataRole .*?\n\}\n\nresource provisionerLeaseBinding",
            self.template,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(role_match)
        role = role_match.group(0)
        expected = {
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
        }
        for action in expected:
            self.assertIn(action, self.template)
            self.assertIn(f"          '{action}'", role)
        self.assertIn("actions: []", role)
        self.assertIn("notDataActions: []", role)
        for forbidden in (
            "/blobs/delete",
            "/blobs/manageOwnership/action",
            "/blobs/modifyPermissions/action",
            "/blobs/runAsSuperUser/action",
            "/containers/write",
            "/containers/delete",
        ):
            self.assertNotIn(forbidden, role)
        for broad_role_id in (
            "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
            "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
        ):
            self.assertNotIn(broad_role_id, self.template)

    def test_abac_condition_is_exact_container_and_blob_path(self) -> None:
        for marker in (
            "conditionVersion: '2.0'",
            "scope: leaseContainer",
            "containers:name] StringEquals \\'${containerName}\\'",
            "containers/blobs:path] StringEquals \\'${leaseBlobPath}\\'",
        ):
            self.assertIn(marker, self.template)
        self.assertNotIn("StringLike", self.template)
        self.assertNotIn("StringStartsWith", self.template)
        self.assertNotIn("Blob.List", self.template)

    def test_azure_write_capability_and_defense_in_depth_are_truthful(self) -> None:
        for marker in (
            "Azure blob add authorizes creation; blob write authorizes overwrite and lease acquire/release/break.",
            "not Azure-enforced filtering",
            "azure_blob_write_authorization: 'includes-create-overwrite-lease-and-break'",
            "operation_restriction_boundary: 'sealed-app-api-defense-in-depth-not-azure-enforced'",
            "output azureRbacOperationRestrictionEnforced bool = false",
            "'blob-create'",
            "'blob-overwrite'",
            "'lease-break'",
            "'dedicated-storage-account'",
            "'exact-container-and-blob-path-abac'",
            "'sealed-bootstrap-and-runtime-application-apis'",
        ):
            self.assertIn(marker, self.template)
        self.assertNotIn("blocked-in-app-api", self.template)
        self.assertNotIn("x-ms-lease-action", self.template)

    def test_single_principal_boundary_is_explicit_without_fake_rbac_split(self) -> None:
        self.assertIn(
            "used by both bootstrap and runtime",
            self.template,
        )
        self.assertIn(
            "principal_separation: 'single-owner-bound-bootstrap-and-runtime-principal'",
            self.template,
        )
        self.assertIn(
            "output principalSeparationMode string = 'SINGLE_OWNER_BOUND_PRINCIPAL_FOR_BOOTSTRAP_AND_RUNTIME'",
            self.template,
        )
        self.assertEqual(self.template.count("resource provisionerLeaseBinding"), 1)

    def test_names_role_assignments_and_outputs_are_deterministic(self) -> None:
        for marker in (
            "uniqueString(subscription().tenantId, resourceGroup().id, validatedStorageAccountName)",
            "var leaseDataRoleDefinitionGuid = guid(",
            "guid(leaseContainer.id, provisionerPrincipalId, leaseDataRole.id, leaseBlobPath)",
            "output storageAccountResourceId string = storageAccount.id",
            "output leaseContainerResourceId string = leaseContainer.id",
            "output leaseBlobPath string = leaseBlobPath",
            "output targetBindingSha256 string = targetBindingSha256",
            "output leaseDataRoleDefinitionId string = leaseDataRole.id",
            "output provisionerLeaseRoleAssignmentId string = provisionerLeaseBinding.id",
            "output exactLeaseBlobCondition string = exactLeaseBlobCondition",
        ):
            self.assertIn(marker, self.template)
        self.assertNotIn("newGuid(", self.template)
        self.assertNotIn("utcNow(", self.template)
        self.assertNotIn("output provisionerPrincipalId", self.template)
        self.assertNotIn("output allowedClientIpAddress", self.template)

    def test_example_parameters_are_synthetic_complete_and_isolated(self) -> None:
        required = (
            "using './main.bicep'",
            "param storageAccountName = 'stnacperflease001'",
            "param bffStorageAccountResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/storageAccounts/stnacbffoffline001'",
            "param wormStorageAccountResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-worm/providers/Microsoft.Storage/storageAccounts/stnacwormoffline001'",
            "param provisionerPrincipalId = '11111111-2222-4333-8444-555555555555'",
            "param allowedClientIpAddress = '203.0.113.10'",
            "param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'",
        )
        for marker in required:
            self.assertIn(marker, self.example_parameters)
        self.assertIn(
            "blobs/write also permits overwrite and",
            self.example_parameters,
        )
        self.assertIn(
            "Account/path scope and sealed APIs provide defense-in-depth",
            self.example_parameters,
        )
        account_values = [
            "stnacperflease001",
            *re.findall(r"/storageAccounts/([^']+)'", self.example_parameters),
        ]
        self.assertEqual(len(account_values), 3)
        self.assertEqual(len(set(account_values)), 3)

    def test_ci_compiles_and_validates_emitted_arm_with_pinned_bicep(self) -> None:
        workflow = QUALITY_GATE.read_text(encoding="utf-8")
        for marker in (
            "az bicep install --version v0.45.6",
            "az bicep uninstall",
            "az bicep install --version v0.45.15",
            "az bicep build --file deploy/runtime/azure/nac-bff-performance-coordination/main.bicep --stdout > /tmp/nac-bff-performance-coordination-main.json",
            "az bicep build-params --file deploy/runtime/azure/nac-bff-performance-coordination/main.example.bicepparam --stdout > /tmp/nac-bff-performance-coordination-main-params.json",
            "cmp /tmp/nac-bff-performance-coordination-main.json deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.json",
            "cmp /tmp/nac-bff-performance-coordination-main-params.json deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.example.json",
            "python scripts/validate_nac_bff_performance_coordination_arm.py /tmp/nac-bff-performance-coordination-main.json /tmp/nac-bff-performance-coordination-main-params.json",
        ):
            self.assertIn(marker, workflow)

    def test_canonical_compiled_template_and_parameters_are_committed(self) -> None:
        template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        parameters = json.loads(COMPILED_PARAMETERS.read_text(encoding="utf-8"))

        self.assertEqual(arm_validator.validate_template(template), [])
        self.assertEqual(
            arm_validator.validate_parameters_artifact(parameters, template), []
        )
        self.assertEqual(
            template["metadata"]["_generator"]["version"],
            arm_validator.EXPECTED_BICEP_VERSION,
        )

    def test_emitted_arm_validator_asserts_exact_rbac_and_id_bindings(self) -> None:
        validator = ARM_VALIDATOR.read_text(encoding="utf-8")
        for marker in (
            '"bffStorageAccountResourceId"',
            '"wormStorageAccountResourceId"',
            '"Microsoft.Authorization/roleDefinitions": 1',
            '"Microsoft.Authorization/roleAssignments": 1',
            '"custom role DataActions are not exactly add/read/write"',
            '"role assignment scope is not the exact lease container"',
            '"role assignment does not use the exact path condition"',
            '"exact lease condition expression differs"',
            '"compiled parameter artifact embeds a different ARM template"',
            '"validated storage account isolation guard differs"',
            '"networkAcls.resourceAccessRules must be exactly empty"',
            '"parameter schemas differ from the bound coordination contract"',
            '"blob service resource name differs"',
            '"lease container resource name differs"',
            '"custom role resource name differs"',
            '"output key/value/type set differs from the emitted contract"',
            '"bffStorageAccountResourceIdBinding"',
            '"wormStorageAccountResourceIdBinding"',
        ):
            self.assertIn(marker, validator)

    def test_emitted_arm_validator_rejects_changed_resource_api_versions(
        self,
    ) -> None:
        for resource_type in arm_validator.EXPECTED_RESOURCE_API_VERSIONS:
            with self.subTest(resource_type=resource_type):
                template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
                resource = next(
                    item
                    for item in template["resources"]
                    if item["type"] == resource_type
                )
                resource["apiVersion"] = "1900-01-01"

                self.assertIn(
                    f"{resource_type} apiVersion differs",
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_removed_and_extra_dependencies(
        self,
    ) -> None:
        removed = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        role_assignment = next(
            resource
            for resource in removed["resources"]
            if resource["type"] == "Microsoft.Authorization/roleAssignments"
        )
        role_assignment["dependsOn"].pop()

        added = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        storage = next(
            resource
            for resource in added["resources"]
            if resource["type"] == "Microsoft.Storage/storageAccounts"
        )
        storage["dependsOn"] = ["[resourceGroup().id]"]

        for name, template, expected_error in (
            (
                "removed dependency",
                removed,
                "Microsoft.Authorization/roleAssignments dependsOn set differs",
            ),
            (
                "extra dependency",
                added,
                "Microsoft.Storage/storageAccounts dependsOn set differs",
            ),
        ):
            with self.subTest(name=name):
                self.assertIn(
                    expected_error,
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_output_contract_mutations(self) -> None:
        added = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        added["outputs"]["unexpectedOutput"] = {
            "type": "string",
            "value": "unexpected",
        }

        changed_value = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        changed_value["outputs"]["contractSchemaVersion"]["value"] = "v2"

        changed_type = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        changed_type["outputs"]["requiredLeaseBlobContentLength"]["type"] = (
            "string"
        )

        for name, template in (
            ("added output", added),
            ("changed output value", changed_value),
            ("changed output type", changed_type),
        ):
            with self.subTest(name=name):
                self.assertIn(
                    "output key/value/type set differs from the emitted contract",
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_rbac_mutations(self) -> None:
        role = {
            "name": arm_validator.EXPECTED_ROLE_DEFINITION_NAME,
            "properties": {
                "type": "CustomRole",
                "permissions": [
                    {
                        "actions": [],
                        "notActions": [],
                        "dataActions": sorted(arm_validator.EXPECTED_DATA_ACTIONS),
                        "notDataActions": [],
                    }
                ],
                "assignableScopes": ["[resourceGroup().id]"],
            }
        }
        errors: list[str] = []
        arm_validator._validate_role_definition(role, errors)
        self.assertEqual(errors, [])

        mutated_role = deepcopy(role)
        mutated_role["properties"]["permissions"][0]["dataActions"].append(
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete"
        )
        errors = []
        arm_validator._validate_role_definition(mutated_role, errors)
        self.assertIn(
            "custom role DataActions are not exactly add/read/write", errors
        )

        assignment = {
            "scope": arm_validator.EXPECTED_ROLE_ASSIGNMENT_SCOPE,
            "name": arm_validator.EXPECTED_ROLE_ASSIGNMENT_NAME,
            "properties": {
                "condition": arm_validator.EXPECTED_ROLE_ASSIGNMENT_CONDITION,
                "conditionVersion": "2.0",
                "principalId": arm_validator.EXPECTED_ROLE_ASSIGNMENT_PRINCIPAL,
                "principalType": "ServicePrincipal",
                "roleDefinitionId": arm_validator.EXPECTED_ROLE_ASSIGNMENT_ROLE,
            },
        }
        errors = []
        arm_validator._validate_role_assignment(assignment, errors)
        self.assertEqual(errors, [])
        mutated_assignment = deepcopy(assignment)
        mutated_assignment["properties"]["condition"] = "[parameters('condition')]"
        errors = []
        arm_validator._validate_role_assignment(mutated_assignment, errors)
        self.assertIn(
            "role assignment does not use the exact path condition", errors
        )

        widened_condition = deepcopy(assignment)
        widened_condition["properties"]["condition"] = (
            "[or(variables('exactLeaseBlobCondition'), true())]"
        )
        errors = []
        arm_validator._validate_role_assignment(widened_condition, errors)
        self.assertIn(
            "role assignment does not use the exact path condition", errors
        )

        widened_scope = deepcopy(assignment)
        widened_scope["scope"] = (
            "[if(true(), resourceGroup().id, "
            "resourceId('Microsoft.Storage/storageAccounts/blobServices/containers', "
            "variables('validatedStorageAccountName'), 'default', "
            "variables('containerName')))]"
        )
        errors = []
        arm_validator._validate_role_assignment(widened_scope, errors)
        self.assertIn(
            "role assignment scope is not the exact lease container", errors
        )

    def test_emitted_arm_validator_rejects_widened_condition_variable(self) -> None:
        variables = {
            "blobReadDataAction": (
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
            ),
            "blobAddDataAction": (
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action"
            ),
            "blobWriteDataAction": (
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
            ),
            "exactLeaseBlobCondition": (
                arm_validator.EXPECTED_EXACT_LEASE_CONDITION[:-1] + " OR true)]"
            ),
        }
        errors: list[str] = []
        arm_validator._validate_id_binding_variables(variables, errors)
        self.assertIn("exact lease condition expression differs", errors)

    def test_emitted_arm_validator_rejects_removed_deployment_scope_guard(self) -> None:
        template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        template["variables"]["validatedDeploymentScope"] = (
            "[format('{0}/{1}/{2}', parameters('tenantId'), "
            "parameters('subscriptionId'), parameters('resourceGroupName'))]"
        )

        self.assertIn(
            "validated deployment scope guard differs",
            arm_validator.validate_template(template),
        )

    def test_emitted_arm_validator_rejects_unconditional_true_guards(self) -> None:
        cases = (
            (
                "validatedDeploymentScope",
                arm_validator.EXPECTED_VALIDATED_DEPLOYMENT_SCOPE,
                ", format('{0}/{1}/{2}'",
                "validated deployment scope guard differs",
            ),
            (
                "validatedStorageAccountName",
                arm_validator.EXPECTED_VALIDATED_STORAGE_ACCOUNT_NAME,
                ", parameters('storageAccountName'), fail(",
                "validated storage account isolation guard differs",
            ),
        )
        for variable_name, expression, success_branch, expected_error in cases:
            with self.subTest(variable_name=variable_name):
                template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
                guard, remainder = expression.rsplit(success_branch, 1)
                template["variables"][variable_name] = (
                    guard.replace("[if(", "[if(or(true(), ", 1)
                    + ")"
                    + success_branch
                    + remainder
                )

                self.assertIn("true()", template["variables"][variable_name])
                self.assertIn("fail(", template["variables"][variable_name])
                self.assertIn(
                    expected_error,
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_pairwise_isolation_mutations(self) -> None:
        mutations = (
            (
                "BFF/WORM resource ID comparison",
                "not(equals(toLower(variables('validatedBffStorageAccountResourceId')), "
                "toLower(variables('validatedWormStorageAccountResourceId'))))",
            ),
            (
                "BFF/WORM account name comparison",
                "not(equals(toLower(variables('bffStorageAccountName')), "
                "toLower(variables('wormStorageAccountName'))))",
            ),
        )
        for name, comparison in mutations:
            with self.subTest(name=name):
                template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
                expression = template["variables"]["validatedStorageAccountName"]
                self.assertIn(comparison, expression)
                template["variables"]["validatedStorageAccountName"] = (
                    expression.replace(comparison, "true()", 1)
                )

                self.assertIn(
                    "validated storage account isolation guard differs",
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_resource_access_rule_mutations(
        self,
    ) -> None:
        for name, replacement in (
            ("missing property", None),
            (
                "non-empty property",
                [
                    {
                        "tenantId": "00000000-0000-0000-0000-000000000000",
                        "resourceId": "[resourceGroup().id]",
                    }
                ],
            ),
        ):
            with self.subTest(name=name):
                template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
                storage = next(
                    resource
                    for resource in template["resources"]
                    if resource["type"] == "Microsoft.Storage/storageAccounts"
                )
                network_acls = storage["properties"]["networkAcls"]
                if replacement is None:
                    network_acls.pop("resourceAccessRules")
                else:
                    network_acls["resourceAccessRules"] = replacement

                self.assertIn(
                    "networkAcls.resourceAccessRules must be exactly empty",
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_exact_parameter_schema_mutations(self) -> None:
        cases = (
            (
                "widened location allowed values",
                "@allowed([\n  'germanywestcentral'\n])",
                "@allowed([\n  'germanywestcentral'\n  'westeurope'\n])",
                "allowedValues",
                ["germanywestcentral", "westeurope"],
            ),
            (
                "altered location default",
                "param location string = 'germanywestcentral'",
                "param location string = 'westeurope'",
                "defaultValue",
                "westeurope",
            ),
            (
                "altered tags default",
                "param tags object = {}",
                "param tags object = { owner: 'caller' }",
                "defaultValue",
                {"owner": "caller"},
            ),
        )
        for name, source_old, source_new, schema_key, schema_value in cases:
            with self.subTest(name=name):
                mutated_source = self.template.replace(source_old, source_new, 1)
                self.assertNotEqual(mutated_source, self.template)
                self.assertIn(source_new, mutated_source)

                template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
                parameter_name = "tags" if "tags" in name else "location"
                template["parameters"][parameter_name][schema_key] = schema_value

                self.assertIn(
                    "parameter schemas differ from the bound coordination contract",
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_retargeted_storage_resource(self) -> None:
        template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        storage = next(
            resource
            for resource in template["resources"]
            if resource["type"] == "Microsoft.Storage/storageAccounts"
        )
        storage["name"] = "[parameters('storageAccountName')]"

        self.assertIn(
            "storage resource name is not the validated account name",
            arm_validator.validate_template(template),
        )

    def test_emitted_arm_validator_rejects_changed_storage_location(self) -> None:
        template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        storage = next(
            resource
            for resource in template["resources"]
            if resource["type"] == "Microsoft.Storage/storageAccounts"
        )
        storage["location"] = "[resourceGroup().location]"

        self.assertIn(
            "storage resource location is not the bound location parameter",
            arm_validator.validate_template(template),
        )

    def test_emitted_arm_validator_rejects_security_resource_expression_mutations(
        self,
    ) -> None:
        cases = (
            (
                "Microsoft.Storage/storageAccounts",
                "name",
                "[if(true(), parameters('storageAccountName'), "
                "variables('validatedStorageAccountName'))]",
                "storage resource name is not the validated account name",
            ),
            (
                "Microsoft.Storage/storageAccounts",
                "location",
                "[if(true(), resourceGroup().location, parameters('location'))]",
                "storage resource location is not the bound location parameter",
            ),
            (
                "Microsoft.Storage/storageAccounts/blobServices",
                "name",
                "[if(true(), 'unbound/default', format('{0}/{1}', "
                "variables('validatedStorageAccountName'), 'default'))]",
                "blob service resource name differs",
            ),
            (
                "Microsoft.Storage/storageAccounts/blobServices/containers",
                "name",
                "[if(true(), 'unbound/default/container', format('{0}/{1}/{2}', "
                "variables('validatedStorageAccountName'), 'default', "
                "variables('containerName')))]",
                "lease container resource name differs",
            ),
            (
                "Microsoft.Authorization/roleDefinitions",
                "name",
                "[if(true(), guid('unbound'), "
                "variables('leaseDataRoleDefinitionGuid'))]",
                "custom role resource name differs",
            ),
            (
                "Microsoft.Authorization/roleAssignments",
                "name",
                "[if(true(), guid('unbound'), "
                + arm_validator.EXPECTED_ROLE_ASSIGNMENT_NAME[1:-1]
                + ")]",
                "role assignment deterministic name differs",
            ),
        )
        for resource_type, field, expression, expected_error in cases:
            with self.subTest(resource_type=resource_type, field=field):
                template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
                resource = next(
                    item
                    for item in template["resources"]
                    if item["type"] == resource_type
                )
                resource[field] = expression

                self.assertIn("true()", expression)
                self.assertIn(
                    expected_error,
                    arm_validator.validate_template(template),
                )

    def test_emitted_arm_validator_rejects_widened_assignable_scope(self) -> None:
        template = json.loads(COMPILED_TEMPLATE.read_text(encoding="utf-8"))
        role = next(
            resource
            for resource in template["resources"]
            if resource["type"] == "Microsoft.Authorization/roleDefinitions"
        )
        role["properties"]["assignableScopes"] = [
            "[if(true(), subscription().id, resourceGroup().id)]"
        ]

        self.assertIn(
            "custom role assignable scope is not the exact resource group",
            arm_validator.validate_template(template),
        )

    def test_parameter_artifact_validator_rejects_drift(self) -> None:
        template = {"parameters": {}}
        artifact = {
            "parametersJson": json.dumps(
                {
                    "$schema": (
                        "https://schema.management.azure.com/schemas/2019-04-01/"
                        "deploymentParameters.json#"
                    ),
                    "contentVersion": "1.0.0.0",
                    "parameters": {
                        name: {"value": value}
                        for name, value in (
                            arm_validator.EXPECTED_EXAMPLE_PARAMETERS.items()
                        )
                    },
                }
            ),
            "templateJson": json.dumps(template),
            "templateSpecId": None,
        }
        self.assertEqual(
            arm_validator.validate_parameters_artifact(artifact, template), []
        )
        drifted = deepcopy(artifact)
        drifted["templateJson"] = json.dumps({"parameters": {"widened": {}}})
        self.assertIn(
            "compiled parameter artifact embeds a different ARM template",
            arm_validator.validate_parameters_artifact(drifted, template),
        )


if __name__ == "__main__":
    unittest.main()
