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
            "param bffStorageAccountName string",
            "param wormStorageAccountName string",
        ):
            self.assertIn(parameter, self.template)
        self.assertIn(
            "storageAccountName != bffStorageAccountName && storageAccountName != wormStorageAccountName",
            self.template,
        )
        self.assertIn("fail('Performance coordination storage must be dedicated", self.template)
        self.assertIn("workload: 'nac-bff-performance-coordination'", self.template)
        self.assertNotIn("immutableStorageWithVersioning", self.template)
        self.assertNotIn("immutabilityPolicies", self.template)

    def test_storage_disables_shared_keys_and_public_blobs(self) -> None:
        for marker in (
            "allowBlobPublicAccess: false",
            "allowCrossTenantReplication: false",
            "allowSharedKeyAccess: false",
            "defaultToOAuthAuthentication: true",
            "isHnsEnabled: false",
            "minimumTlsVersion: 'TLS1_2'",
            "supportsHttpsTrafficOnly: true",
            "publicAccess: 'None'",
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

    def test_precreated_blob_contract_matches_runtime_path(self) -> None:
        for marker in (
            "var containerName = 'nac-bff-performance-leases'",
            "var leaseBlobPath = 'locks/${targetBindingSha256}.lock'",
            "param precreatedLeaseBlobETag string",
            "lease_blob_type: 'BlockBlob'",
            "lease_blob_content_length: '0'",
            "lease_blob_precreation: 'required-before-runtime'",
            "output precreatedLeaseBlobContentLength int = 0",
            "output blobCreationIncluded bool = false",
        ):
            self.assertIn(marker, self.template)
        self.assertRegex(
            self.template,
            r"@minLength\(64\)\s*@maxLength\(64\)\s*param targetBindingSha256 string",
        )

    def test_existing_provisioner_gets_only_blob_read_and_write(self) -> None:
        self.assertRegex(
            self.template,
            r"resource provisionerIdentity .* existing = \{",
        )
        role_match = re.search(
            r"resource leaseDataRole .*?\n\}\n\nresource provisionerLeaseBinding",
            self.template,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(role_match)
        role = role_match.group(0)
        expected = {
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
        }
        for action in expected:
            self.assertIn(action, self.template)
            self.assertIn(f"          '{action}'", role)
        self.assertIn("actions: []", role)
        self.assertIn("notDataActions: []", role)
        for forbidden in (
            "/blobs/add/action",
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

    def test_lease_break_residual_is_explicit_and_app_blocked(self) -> None:
        self.assertIn(
            "lease_break_boundary: 'shares-write-data-action-blocked-in-app-api'",
            self.template,
        )
        self.assertIn(
            "output leaseBreakAuthorizationBoundary string = 'SHARES_WRITE_DATA_ACTION_BLOCKED_IN_APP_API'",
            self.template,
        )
        self.assertNotIn("x-ms-lease-action", self.template)

    def test_names_role_assignments_and_outputs_are_deterministic(self) -> None:
        for marker in (
            "uniqueString(subscription().tenantId, resourceGroup().id, validatedStorageAccountName)",
            "var leaseDataRoleDefinitionGuid = guid(",
            "guid(leaseContainer.id, provisionerIdentity.id, leaseDataRole.id, leaseBlobPath)",
            "output storageAccountResourceId string = storageAccount.id",
            "output leaseContainerResourceId string = leaseContainer.id",
            "output leaseBlobPath string = leaseBlobPath",
            "output targetBindingSha256 string = targetBindingSha256",
            "output provisionerIdentityResourceId string = provisionerIdentity.id",
            "output leaseDataRoleDefinitionId string = leaseDataRole.id",
            "output provisionerLeaseRoleAssignmentId string = provisionerLeaseBinding.id",
            "output exactLeaseBlobCondition string = exactLeaseBlobCondition",
        ):
            self.assertIn(marker, self.template)
        self.assertNotIn("newGuid(", self.template)
        self.assertNotIn("utcNow(", self.template)

    def test_example_parameters_are_synthetic_complete_and_isolated(self) -> None:
        required = (
            "using './main.bicep'",
            "param storageAccountName = 'stnacperflease001'",
            "param bffStorageAccountName = 'stnacbffoffline001'",
            "param wormStorageAccountName = 'stnacwormoffline001'",
            "param provisionerIdentityName = 'id-nac-bff-performance-provisioner-test'",
            "param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'",
            "param precreatedLeaseBlobETag = '\"0x8DBABCDEF012345\"'",
        )
        for marker in required:
            self.assertIn(marker, self.example_parameters)
        account_values = re.findall(
            r"param (?:storageAccountName|bffStorageAccountName|wormStorageAccountName) = '([^']+)'",
            self.example_parameters,
        )
        self.assertEqual(len(account_values), 3)
        self.assertEqual(len(set(account_values)), 3)


if __name__ == "__main__":
    unittest.main()
