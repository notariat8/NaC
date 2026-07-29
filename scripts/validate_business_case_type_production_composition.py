from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = (
    ROOT
    / "workflows/contracts/business-case-type-production-composition-s4g.contract.json"
)
VERIFICATION_PATH = (
    ROOT
    / "workflows/verification-contracts/"
    "business-case-type-production-composition-s4g.verification.json"
)
STATUS = "S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE"
LIVE_STATUS = (
    "BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION"
)
ISSUE = "https://github.com/notariat8/NaC/issues/708"
ACCEPTANCE_IDS = [f"AC-S4G-{index:02d}" for index in range(1, 9)]
BLOCKERS = [
    "central_postgresql_promotion_ack_retention_cleanup",
    "broker_product_owner_decision",
    "signature_anchor_owner_decision",
    "durable_reconciliation_store",
    "irreversible_worm_policy_lock",
    "owner_gated_live_activation",
]


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def validate_domain_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_top = {
        "schemaVersion": (
            "nac.business-case-type-production-composition-s4g/v0.1"
        ),
        "title": "BusinessCaseType production edge composition S4g",
        "issue": ISSUE,
        "status": STATUS,
        "liveStatus": LIVE_STATUS,
        "acceptanceIdsExact": ACCEPTANCE_IDS,
        "remainingBlockersExact": BLOCKERS,
    }
    for key, value in expected_top.items():
        if contract.get(key) != value:
            errors.append(f"domain.{key}")

    expected_sections = {
        "compositionEnvelope": {
            "workspaceIdExact": "notary_team_01",
            "offlineOnly": True,
            "ancestorContractsSha256BoundExact": [
                "s4d_contract_sha256",
                "s4f_contract_sha256",
                "s6b_contract_sha256",
            ],
            "componentBindingsSha256Exact": [
                "identity_inspector_implementation_sha256",
                "owner_verifier_sha256",
                "write_token_factory_sha256",
                "graph_http_transport_sha256",
                "azure_worm_transport_sha256",
                "worm_target_binding_sha256",
            ],
            "runtimeFactoryConstructed": False,
            "writerCredentialsRead": False,
            "bindingSourceExact": (
                "domain_separated_repository_file_sha256"
            ),
            "wormTargetBindingStateExact": "offline_unconfigured",
            "attestationBindingsSha256Exact": [
                "identity_inspection_sha256"
            ],
        },
        "identityInspector": {
            "adapterExact": (
                "BusinessCaseTypeWriteIdentityInspectionAdapter"
            ),
            "portExact": "SnapshotIdentityInspectionPort",
            "modeExact": "read_only_snapshot_validation",
            "principalsExact": ["provisioner", "writer", "bff"],
            "applicationIdFieldExact": "app_id",
            "servicePrincipalObjectIdFieldExact": (
                "service_principal_object_id"
            ),
            "applicationIdsPairwiseDistinctRequired": True,
            "servicePrincipalObjectIdsPairwiseDistinctRequired": True,
            "applicationIdAndObjectIdNamespacesSeparateRequired": True,
            "principalBindingsSha256Required": True,
            "siteBindingSha256Required": True,
            "businessWriterPrincipalExact": "writer",
            "writeTokenSourcePrincipalExact": "writer",
            "writerGraphApplicationRolesExact": ["Sites.Selected"],
            "writerSiteRolesExact": ["write"],
            "bffGraphApplicationRolesExact": ["Sites.Selected"],
            "bffSiteRolesExact": ["read"],
            "provisionerBusinessWriteAllowed": False,
            "providerMutationAllowed": False,
            "plaintextIdentifiersReturned": False,
        },
        "localSqliteLayout": {
            "scopeExact": "trusted_local_single_host_only",
            "mutationStoreRoleExact": "mutation_state",
            "mutationDatabaseNameExact": "mutation-state.sqlite3",
            "evidenceStoreRoleExact": "evidence_staging",
            "evidenceDatabaseNameExact": "evidence-staging.sqlite3",
            "distinctCanonicalPathsRequired": True,
            "sameDatabaseFileAllowed": False,
            "sameRoleAllowed": False,
            "absolutePathsRequired": True,
            "commonTrustedRootRequired": True,
            "rootModeOctalExact": "0700",
            "databaseModeOctalExact": "0600",
            "databasePrecreationAllowed": True,
            "existingDatabaseModeOctalExact": "0600",
            "existingDatabaseHardlinkCountExact": 1,
            "symlinkedRootOrDatabaseAllowed": False,
            "syncedRootAllowed": False,
            "remoteFilesystemAllowed": False,
            "unknownFilesystemAllowed": False,
            "centralTruth": False,
            "canCloseMutation": False,
        },
        "azureWormRestTransport": {
            "adapterExact": "AzureBlobWormRestTransport",
            "portExact": "AzureBlobWormTransport",
            "managementHostExact": "management.azure.com",
            "blobHostOwnerBound": True,
            "httpsOnly": True,
            "managementApiVersionExact": "2023-05-01",
            "subscriptionApiVersionExact": "2022-12-01",
            "blobApiVersionExact": "2023-11-03",
            "methodsExact": ["GET", "PUT"],
            "managementTokenProviderInjected": True,
            "blobTokenProviderInjected": True,
            "httpPortInjected": True,
            "foreignHostsAllowed": False,
            "redirectsAllowed": False,
            "automaticRetries": 0,
            "maximumRequestBytes": 4194304,
            "maximumResponseBytes": 4194304,
            "createPreconditionHeaderExact": "If-None-Match: *",
            "createSuccessStatusExact": 201,
            "createConflictStatusExact": 412,
            "createVersionHeaderExact": "x-ms-version-id",
            "idempotencyBoundToS6bOperationKey": True,
            "exactVersionReadbackRequired": True,
            "providerContextReadbackRequired": True,
            "lockedPolicyReadbackRequired": True,
            "policyMutationAllowed": False,
            "irreversibleLockOperationAllowed": False,
            "deleteOperationAllowed": False,
            "rawTokenUrlOrProviderBodyReturned": False,
        },
        "offlineCompletion": {
            "statusExact": STATUS,
            "liveStatusExact": LIVE_STATUS,
            "productionReadinessClaimed": False,
            "productionDurabilityClaimed": False,
            "runtimeFactoryConstructed": False,
            "liveWriteAuthorized": False,
            "socketOrDnsCallsExact": 0,
            "externalCredentialStoreReadsExact": 0,
            "graphCallsExact": 0,
            "azureCallsExact": 0,
            "tenantWritesExact": 0,
            "wormLockActionsExact": 0,
        },
    }
    for section, expected in expected_sections.items():
        if contract.get(section) != expected:
            errors.append(f"domain.{section}")

    if contract.get("extendsContractsExact") != [
        "workflows/contracts/"
        "business-case-type-live-write-boundary-s4d.contract.json",
        "workflows/contracts/"
        "business-case-type-production-adapters-s4f.contract.json",
        "workflows/contracts/"
        "business-case-type-azure-blob-worm-s6b.contract.json",
    ]:
        errors.append("domain.extendsContractsExact")

    required_out_of_scope = {
        "broker_selection_or_deployment",
        "central_postgresql_promotion_ack_retention_or_cleanup",
        "durable_reconciliation_implementation",
        "irreversible_worm_policy_lock",
        "live_graph_azure_or_tenant_action",
        "owner_gated_live_activation",
        "signature_anchor_selection_or_deployment",
    }
    if not required_out_of_scope.issubset(
        set(contract.get("outOfScopeExact", []))
    ):
        errors.append("domain.outOfScopeExact")
    return errors


def validate_verification_contract(
    contract: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    expected_top = {
        "schemaVersion": "nac.verification-contract/v0.1",
        "id": "business-case-type-production-composition-s4g",
        "title": (
            "BusinessCaseType production edge composition S4g verification"
        ),
        "issue": ISSUE,
    }
    for key, value in expected_top.items():
        if contract.get(key) != value:
            errors.append(f"verification.{key}")
    for key in (
        "appliesWhen",
        "requiredContext",
        "checks",
        "requiredEvidence",
        "invariants",
        "thresholds",
        "passCondition",
        "failureBehavior",
    ):
        if not contract.get(key):
            errors.append(f"verification.{key}")

    if contract.get("thresholds") != {
        "socketOrDnsCalls": 0,
        "externalCredentialStoreReads": 0,
        "graphCalls": 0,
        "azureCalls": 0,
        "tenantWrites": 0,
        "wormLockActions": 0,
        "unresolvedP1OrP2Findings": 0,
    }:
        errors.append("verification.thresholds")
    if contract.get("passCondition") != {
        "allChecksPass": True,
        "statusExact": STATUS,
        "liveStatusExact": LIVE_STATUS,
        "productionReadinessClaimed": False,
        "productionDurabilityClaimed": False,
        "runtimeFactoryConstructed": False,
        "liveWriteAuthorized": False,
    }:
        errors.append("verification.passCondition")
    if contract.get("failureBehavior") != {
        "mode": "fail_closed",
        "mergeAllowed": False,
        "runtimeConstructionAllowed": False,
        "writerCredentialReadAllowed": False,
        "liveRetryAllowed": False,
        "ownerInputRequiredForLiveActivation": True,
    }:
        errors.append("verification.failureBehavior")

    evidence = "\n".join(contract.get("requiredEvidence", []))
    for marker in (
        "app_id",
        "service_principal_object_id",
        "domain-separated hashes",
        "exact in-memory SnapshotIdentityInspectionPort",
        "namespaces are disjoint",
        "distinct canonical SQLite paths",
        "st_nlink equal to one",
        "distinct device/inode identities",
        "PostgreSQL promotion/ack/retention/cleanup",
        "irreversible WORM lock",
        LIVE_STATUS,
    ):
        if marker not in evidence:
            errors.append(f"verification.requiredEvidence:{marker}")
    return errors


def main() -> int:
    errors = [
        *validate_domain_contract(_load(DOMAIN_PATH)),
        *validate_verification_contract(_load(VERIFICATION_PATH)),
    ]
    if errors:
        print(
            "BusinessCaseType S4g production composition contract "
            "validation failed:"
        )
        for error in errors:
            print(f"- {error}")
        return 1
    print("BusinessCaseType S4g production composition contracts: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
