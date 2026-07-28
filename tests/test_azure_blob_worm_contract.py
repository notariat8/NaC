from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOMAIN = (
    ROOT
    / "workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json"
)
LOCK = (
    ROOT
    / "workflows/contracts/azure-blob-worm-irreversible-lock-s6b.contract.json"
)
VERIFICATION = (
    ROOT
    / "workflows/verification-contracts/business-case-type-azure-blob-worm-s6b.verification.json"
)
VALIDATOR = ROOT / "scripts/validate_business_case_type_azure_blob_worm.py"
EXPECTED_ACCEPTANCE = [f"AC-S6B-{index:02d}" for index in range(1, 8)]


class AzureBlobWormContractTests(unittest.TestCase):
    def test_domain_verification_and_lock_contracts_share_boundary(self) -> None:
        domain = json.loads(DOMAIN.read_text(encoding="utf-8"))
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))

        self.assertEqual(domain["status"], "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE")
        self.assertEqual(
            domain["slice"]["live_status_exact"],
            "BLOCKED_PENDING_S7_APPROVAL",
        )
        self.assertEqual(
            [item["id"] for item in domain["acceptance_criteria"]],
            EXPECTED_ACCEPTANCE,
        )
        self.assertEqual(verification["acceptance_ids"], EXPECTED_ACCEPTANCE)
        self.assertFalse(domain["slice"]["live_factory_wiring"])
        self.assertEqual(domain["slice"]["allowed_network_calls"], 0)
        self.assertEqual(domain["slice"]["allowed_azure_calls"], 0)
        self.assertEqual(domain["slice"]["allowed_credential_reads"], 0)
        self.assertEqual(domain["container_policy"]["minimum_retention_days"], 3653)
        receipt = domain["version_bound_receipt"]
        self.assertEqual(receipt["blob_locator_bits"], 128)
        self.assertEqual(receipt["version_binding_bits"], 128)
        self.assertFalse(receipt["conflict_response_version_id_allowed"])
        self.assertTrue(receipt["public_readback_exact_version_required"])
        provider_tenant = domain["provider_tenant_evidence"]
        self.assertEqual(
            provider_tenant["source_exact"],
            "azure-subscription-resource-tenant-readback",
        )
        self.assertTrue(provider_tenant["fresh_transport_readback_required"])
        self.assertFalse(provider_tenant["plaintext_allowed"])
        baseline = domain["bicep_baseline"]
        self.assertFalse(baseline["immutability_policy_state_property_emitted"])
        self.assertEqual(
            baseline["expected_post_deploy_readback_state"], "Unlocked"
        )
        self.assertEqual(
            baseline["writer_data_actions_exact"],
            [
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            ],
        )
        self.assertEqual(
            baseline["writer_management_actions_exact"],
            [
                "Microsoft.Storage/storageAccounts/blobServices/containers/read",
                "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/read",
                "Microsoft.Storage/storageAccounts/encryptionScopes/read",
            ],
        )
        self.assertFalse(baseline["writer_delete_action_allowed"])
        self.assertFalse(baseline["writer_blob_write_action_allowed"])
        self.assertEqual(
            baseline["identity_name_binding_inputs_exact"],
            [
                "subscription().tenantId",
                "resourceGroup().id",
                "storageAccountName",
            ],
        )
        self.assertFalse(baseline["provider_binding_hashes_emitted_by_template"])
        self.assertEqual(
            baseline["provider_binding_material_source_exact"],
            "runtime-readback-not-template-metadata",
        )
        self.assertEqual(
            baseline["custom_role_definition_scope_exact"],
            "resource_group",
        )
        self.assertEqual(
            lock["operation"]["operation_exact"],
            "POST immutabilityPolicies/default/lock",
        )
        self.assertEqual(lock["operation"]["api_version_exact"], "2023-05-01")
        self.assertTrue(lock["preconditions"]["if_match_etag_required"])
        self.assertTrue(lock["preconditions"]["prepared_request_sha256_required"])
        self.assertTrue(lock["dual_control"]["operator_approver_distinct"])
        self.assertFalse(lock["execution"]["performed_by_s6b"])
        compilation = verification["bicep_compilation"]
        self.assertFalse(compilation["compiled_claim"])
        self.assertTrue(compilation["ci_compile_required"])

    def test_de_and_en_specs_and_plans_are_paired(self) -> None:
        relative_paths = (
            "superpowers/specs/2026-07-28-business-case-type-azure-blob-worm-s6b-design.md",
            "superpowers/plans/2026-07-28-business-case-type-azure-blob-worm-s6b.md",
        )
        for relative_path in relative_paths:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / "docs/de" / relative_path).is_file())
                self.assertTrue((ROOT / "docs/en" / relative_path).is_file())

    def test_dedicated_bicep_baseline_declares_reviewed_controls(self) -> None:
        text = (
            ROOT / "deploy/runtime/azure/immutable-evidence/main.bicep"
        ).read_text(encoding="utf-8")

        for marker in (
            "allowSharedKeyAccess: false",
            "allowCrossTenantReplication: false",
            "defaultToOAuthAuthentication: true",
            "isVersioningEnabled: true",
            "var immutableRetentionDays = 3653",
            "immutabilityPeriodSinceCreationInDays: immutableRetentionDays",
            "requireInfrastructureEncryption: true",
            "keySource: 'Microsoft.Keyvault'",
            "Microsoft.ManagedIdentity/userAssignedIdentities",
            "e147488a-f6f5-4113-8e2d-b22465e65bf6",
            "Microsoft.Authorization/roleDefinitions@2022-04-01",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            "Microsoft.Storage/storageAccounts/blobServices/containers/read",
            "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/read",
            "Microsoft.Storage/storageAccounts/encryptionScopes/read",
            "subscription().tenantId",
            "subscription().id",
            "var targetIsolationSuffix = uniqueString(subscription().tenantId, resourceGroup().id, storageAccountName)",
            "var keyVaultName = 'kv-nacw-${targetIsolationSuffix}'",
            "var cmkIdentityName = 'id-nac-worm-cmk-${targetIsolationSuffix}'",
            "var writerIdentityName = 'id-nac-worm-writer-${targetIsolationSuffix}'",
            "azure-subscription-resource-tenant-readback",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertNotIn("state: 'Unlocked'", text)
        self.assertNotIn("state: 'Locked'", text)
        self.assertNotIn("param tenantBindingSha256", text)
        self.assertNotIn("uniqueString(resourceGroup().id)", text)
        self.assertNotIn("sha256(", text)
        self.assertNotIn("scope: subscription()", text)
        self.assertNotIn("provider_tenant_binding_sha256:", text)
        self.assertNotIn("provider_subscription_binding_sha256:", text)
        self.assertNotIn("provider_resource_binding_sha256:", text)
        self.assertNotIn("provider_context_binding_sha256:", text)
        self.assertIn(
            "provider_binding_material: 'runtime-readback-not-template-metadata'",
            text,
        )
        self.assertNotIn("/delete'", text)
        self.assertNotIn("/blobs/write'", text)
        self.assertNotIn("ba92f5b4-2d11-453d-a403-e96b0029c9fe", text)
        self.assertNotIn("b7e6dc6d-f1e8-4753-8033-0f276bb0955b", text)

    def test_central_cli_reports_provider_free_s6b_readiness(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "scripts/nac.py",
                "kg",
                "business-case-type-azure-worm-readiness",
                "--format",
                "json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        output = json.loads(completed.stdout)
        self.assertEqual(output["status"], "S6B_AZURE_WORM_ADAPTER_READY_OFFLINE")
        self.assertEqual(output["authoritative_evidence_copy"], "azure_blob_immutable_storage")
        self.assertEqual(output["publisher_location"], "onprem")
        self.assertEqual(output["minimum_retention_days"], 3653)
        self.assertFalse(output["writer_delete_allowed"])
        self.assertEqual(output["irreversible_lock_status"], "PREPARED_OFFLINE_NOT_EXECUTED")
        for field in ("network_calls", "provider_calls", "tenant_writes", "credential_reads", "lock_actions"):
            self.assertEqual(output[field], 0)

    def test_ci_compiles_s6b_bicep_with_pinned_toolchain(self) -> None:
        workflow = (ROOT / ".github/workflows/quality-gate.yml").read_text(encoding="utf-8")
        self.assertIn("az bicep install --version v0.45.6", workflow)
        self.assertIn(
            "az bicep build --file deploy/runtime/azure/immutable-evidence/main.bicep --stdout",
            workflow,
        )

    def test_architecture_keeps_runtime_onprem_and_worm_copy_in_azure(self) -> None:
        contract = json.loads(
            (ROOT / "workflows/contracts/microsoft-first-onprem-target-architecture.contract.json").read_text(encoding="utf-8")
        )
        self.assertEqual(contract["decisions"]["worm_publisher_location"], "onprem")
        self.assertEqual(contract["decisions"]["worm_authoritative_copy"], "azure_blob_immutable_storage")
        self.assertFalse(contract["layer_boundaries"]["audit"]["workflow_runtime_authority"])

    def test_standalone_validator_passes(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "validate_azure_blob_worm",
            VALIDATOR,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertEqual(module.main(), 0)


if __name__ == "__main__":
    unittest.main()
