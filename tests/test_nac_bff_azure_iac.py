from pathlib import Path
import json
import re
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_ROOT = REPO_ROOT / "deploy" / "runtime" / "azure" / "nac-bff" / "infra"


def read_infra(name: str) -> str:
    path = INFRA_ROOT / name
    if not path.is_file():
        raise AssertionError(f"{path.relative_to(REPO_ROOT)} is missing")
    return path.read_text(encoding="utf-8")


class NaCBffAzureIacContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.template = read_infra("main.bicep")
        cls.example_parameters = read_infra("main.example.bicepparam")
        cls.quality_workflow = (
            REPO_ROOT / ".github/workflows/quality-gate.yml"
        ).read_text(encoding="utf-8")

    def test_ci_recompiles_and_compares_pinned_bicep_outputs(self) -> None:
        required = (
            "az bicep install --version v0.45.6",
            "az bicep build --file deploy/runtime/azure/nac-bff/infra/main.bicep --stdout",
            "az bicep build-params --file deploy/runtime/azure/nac-bff/infra/main.example.bicepparam --stdout",
            "cmp /tmp/nac-bff-main.json deploy/runtime/azure/nac-bff/infra/compiled/main.json",
            "cmp /tmp/nac-bff-main-params.json deploy/runtime/azure/nac-bff/infra/compiled/main.example.json",
        )
        for marker in required:
            self.assertIn(marker, self.quality_workflow)
        for name in ("compiled/main.json", "compiled/main.example.json"):
            self.assertIsInstance(json.loads(read_infra(name)), dict)

    def test_template_is_resource_group_scoped_and_region_pinned(self) -> None:
        self.assertIn("targetScope = 'resourceGroup'", self.template)
        self.assertRegex(
            self.template,
            r"@allowed\(\[\s*'germanywestcentral'\s*\]\)\s*"
            r"param location string = 'germanywestcentral'",
        )
        self.assertNotIn("Microsoft.Resources/resourceGroups@", self.template)

    def test_fixed_hostname_baseline_is_test_only(self) -> None:
        self.assertRegex(
            self.template,
            r"@allowed\(\[\s*'test'\s*\]\)\s*"
            r"param environmentName string = 'test'",
        )
        self.assertNotIn("'dev'", self.template)
        self.assertNotIn("'prod'", self.template)

    def test_function_hostname_is_fixed_for_spfx_cutover(self) -> None:
        self.assertRegex(
            self.template,
            r"@allowed\(\[\s*'func-nac-bff-test-funktion8'\s*\]\)\s*"
            r"param functionAppName string = 'func-nac-bff-test-funktion8'",
        )
        self.assertEqual(self.template.count("name: functionAppName"), 1)
        self.assertNotIn("var functionAppName", self.template)
        self.assertIn(
            "param functionAppName = 'func-nac-bff-test-funktion8'",
            self.example_parameters,
        )

    def test_baseline_contains_required_azure_native_resources(self) -> None:
        required_resource_types = [
            "Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31",
            "Microsoft.Storage/storageAccounts@2023-05-01",
            "Microsoft.OperationalInsights/workspaces@2023-09-01",
            "Microsoft.Insights/components@2020-02-02",
            "Microsoft.Web/serverfarms@2024-04-01",
            "Microsoft.Web/sites@2024-04-01",
        ]

        for resource_type in required_resource_types:
            with self.subTest(resource_type=resource_type):
                self.assertIn(resource_type, self.template)

        self.assertGreaterEqual(self.template.count("tags: resourceTags"), 6)
        self.assertIn("param tags object = {}", self.template)

    def test_flex_consumption_runtime_has_bounded_low_cost_defaults(self) -> None:
        required_terms = [
            "name: 'FC1'",
            "tier: 'FlexConsumption'",
            "reserved: true",
            "alwaysOn: false",
            "name: 'python'",
            "version: '3.12'",
            "instanceMemoryMB: 2048",
            "maximumInstanceCount: maximumInstanceCount",
            "perInstanceConcurrency: httpPerInstanceConcurrency",
            "name: 'Standard_LRS'",
            "retentionInDays: 30",
            "immediatePurgeDataOn30Days: true",
            "dailyQuotaGb: 1",
            "Cap: json('0.1')",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.template)

        self.assertNotIn("alwaysReady", self.template)
        self.assertNotIn("FUNCTIONS_WORKER_RUNTIME", self.template)
        self.assertEqual(self.template.count("functionAppConfig:"), 1)
        self.assertRegex(
            self.template,
            r"@minValue\(1\)\s*@maxValue\(10\)\s*"
            r"param maximumInstanceCount int = 4",
        )
        self.assertRegex(
            self.template,
            r"@minValue\(1\)\s*@maxValue\(32\)\s*"
            r"param httpPerInstanceConcurrency int = 16",
        )

    def test_platform_health_probe_uses_liveness_endpoint(self) -> None:
        self.assertEqual(self.template.count("healthCheckPath: '/healthz'"), 1)
        self.assertNotIn("healthCheckPath: '/readyz'", self.template)

    def test_storage_uses_identity_protected_public_endpoint_without_vnet(self) -> None:
        required_terms = [
            "publicNetworkAccess: 'Enabled'",
            "bypass: 'None'",
            "defaultAction: 'Allow'",
            "ipRules: []",
            "virtualNetworkRules: []",
            "allowBlobPublicAccess: false",
            "allowSharedKeyAccess: false",
            "defaultToOAuthAuthentication: true",
            "minimumTlsVersion: 'TLS1_2'",
            "supportsHttpsTrafficOnly: true",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.template)

        self.assertNotIn("serviceEndpoints:", self.template)
        self.assertNotIn("Microsoft.Network/", self.template)
        self.assertNotIn("virtualNetworkSubnetId", self.template)
        self.assertNotIn("privateEndpoint", self.template)
        self.assertNotIn("bypass: 'AzureServices'", self.template)
        self.assertNotIn("defaultAction: 'Deny'", self.template)

    def test_storage_and_telemetry_use_user_assigned_identity(self) -> None:
        required_terms = [
            "type: 'SystemAssigned, UserAssigned'",
            "type: 'UserAssignedIdentity'",
            "userAssignedIdentityResourceId: managedIdentity.id",
            "allowSharedKeyAccess: false",
            "defaultToOAuthAuthentication: true",
            "DisableLocalAuth: true",
            "AzureWebJobsStorage__accountName: storageAccount.name",
            "AzureWebJobsStorage__clientId: managedIdentity.properties.clientId",
            "AzureWebJobsStorage__credential: 'managedidentity'",
            "APPLICATIONINSIGHTS_AUTHENTICATION_STRING:",
            "Authorization=AAD",
            "output functionAppSystemAssignedPrincipalId string",
        ]

        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.template)

        expected_role_ids = {
            "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
            "3913510d-42f4-4e42-8a64-420c390055eb",
        }
        for role_id in expected_role_ids:
            self.assertIn(role_id, self.template)
        self.assertNotIn("974c5e8b-45b9-4653-ba55-5f855dd0fb88", self.template)
        self.assertNotIn("0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3", self.template)


    def test_non_secret_runtime_configuration_is_validated_and_wired(self) -> None:
        parameter_patterns = [
            r"@minLength\(36\)\s*@maxLength\(36\)\s*param m365TenantId string",
            r"@minLength\(7\)\s*@maxLength\(256\)\s*param bffApiAudience string",
            r"@allowed\(\[\s*'Matter\.Read'\s*\]\)\s*param bffRequiredDelegatedScope string",
        ]
        for pattern in parameter_patterns:
            with self.subTest(pattern=pattern):
                self.assertRegex(self.template, pattern)

        required_settings = [
            "M365_TENANT_ID: m365TenantId",
            "NAC_BFF_TENANT_ID: m365TenantId",
            "NAC_BFF_AUDIENCE: bffApiAudience",
            "NAC_BFF_REQUIRED_SCOPE: bffRequiredDelegatedScope",
            "M365_RUNTIME_CLIENT_ID: managedIdentity.properties.clientId",
            "AZURE_CLIENT_ID: managedIdentity.properties.clientId",
        ]
        for setting in required_settings:
            with self.subTest(setting=setting):
                self.assertEqual(self.template.count(setting), 1)

    def test_cors_allowlist_is_fixed_to_exact_synthetic_hosts(self) -> None:
        expected = (
            "https://funktion8.sharepoint.com",
            "https://teams.microsoft.com",
            "https://teams.cloud.microsoft",
        )
        self.assertEqual(self.template.count("var corsAllowedOrigins = ["), 1)
        self.assertNotIn("param corsAllowedOrigins", self.template)
        for origin in expected:
            with self.subTest(origin=origin):
                self.assertEqual(self.template.count(origin), 1)
        self.assertEqual(self.template.count("allowedOrigins: corsAllowedOrigins"), 1)
        self.assertIn("supportCredentials: false", self.template)
        self.assertNotIn("azurewebsites.net", self.template.lower())
        self.assertNotIn("param corsAllowedOrigins", self.example_parameters)

    def test_template_contains_no_secrets_or_entra_graph_provisioning(self) -> None:
        lowered = self.template.lower()
        forbidden_terms = [
            "@secure",
            "listkeys(",
            "listcredentials(",
            "storageaccountconnectionstring",
            "azurewebjobsstorage:",
            "client_secret",
            "clientsecret",
            "password",
            "sharedaccesssignature",
            "microsoft.graph/",
            "microsoftgraph",
            "applications@",
            "serviceprincipals@",
            "approleassignments@",
        ]

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, lowered)

        self.assertNotRegex(lowered, r"output\s+\w*(key|secret|token|credential)\w*\s")

    def test_template_outputs_identity_ids_required_for_graph_activation(self) -> None:
        source = self.template
        self.assertIn(
            "output managedIdentityClientId string = managedIdentity.properties.clientId",
            source,
        )
        self.assertIn(
            "output managedIdentityPrincipalId string = managedIdentity.properties.principalId",
            source,
        )

    def test_example_parameters_are_synthetic_and_complete(self) -> None:
        required_terms = [
            "using './main.bicep'",
            "param location = 'germanywestcentral'",
            "param environmentName = 'test'",
            "param m365TenantId = '00000000-0000-0000-0000-000000000001'",
            "param bffApiAudience = '00000000-0000-0000-0000-000000000002'",
            "param bffRequiredDelegatedScope = 'Matter.Read'",
            "param functionAppName = 'func-nac-bff-test-funktion8'",
            "param maximumInstanceCount = 4",
            "param httpPerInstanceConcurrency = 16",
            "param tags = {",
        ]
        for term in required_terms:
            with self.subTest(term=term):
                self.assertIn(term, self.example_parameters)
        self.assertNotIn("corsAllowedOrigins", self.example_parameters)
        self.assertNotIn("/subscriptions/", self.example_parameters.lower())


if __name__ == "__main__":
    unittest.main()
