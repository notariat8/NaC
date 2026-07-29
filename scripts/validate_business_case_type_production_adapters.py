from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = ROOT / "workflows/contracts/business-case-type-production-adapters-s4f.contract.json"
VERIFICATION_PATH = ROOT / "workflows/verification-contracts/business-case-type-production-adapters-s4f.verification.json"
STATUS = "S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE"
ACCEPTANCE_IDS = [f"AC-S4F-{index:02d}" for index in range(1, 8)]
BLOCKERS = [
    "azure_blob_worm_policy_lock",
    "azure_blob_worm_rest_transport",
    "broker_product_owner_decision",
    "central_postgresql_outbox_promotion_ack_retention_cleanup",
    "dedicated_entra_write_identity_and_site_grant",
    "durable_reconciliation_store",
    "production_identity_inspection_readback",
    "synced_filesystem_runtime_detection",
    "signature_anchor_owner_decision",
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
        "schemaVersion": "nac.business-case-type-production-adapters-s4f/v0.1",
        "title": "BusinessCaseType partial production adapter implementations S4f",
        "issue": "https://github.com/notariat8/NaC/issues/704",
        "status": STATUS,
        "acceptanceIdsExact": ACCEPTANCE_IDS,
        "remainingBlockersExact": BLOCKERS,
    }
    for key, value in expected_top.items():
        if contract.get(key) != value:
            errors.append(f"domain.{key}")
    exact_sections = {
        "graphTransport": {
            "baseUrlExact": "https://graph.microsoft.com/v1.0",
            "methodsExact": ["GET", "POST", "PATCH"],
            "redirectsAllowed": False,
            "automaticRetries": 0,
            "maximumResponseBytes": 1048576,
            "errorResponseBodiesReturned": False,
            "foreignHostsAllowed": False,
            "graphBetaAllowed": False,
            "sharePointRestAllowed": False,
            "graphSdkAllowed": False,
            "pnpAllowed": False,
        },
        "ownerVerification": {
            "sourceExact": "github_issue_owner_comment",
            "issueExact": "https://github.com/notariat8/NaC/issues/700",
            "canonicalCommentRequired": True,
            "exactlyOneUnmodifiedMatchRequired": True,
            "ownerAllowlistHashBound": True,
            "verifierPrincipalHashBound": True,
            "attestationExpectedFieldComparisonRequired": True,
            "binaryExecutionExact": "verified_open_file_descriptor",
            "rawCommentReturned": False,
        },
        "writeIdentity": {
            "factoryExact": "CertificateWriteIdentityFactory",
            "permissionExact": "Sites.Selected",
            "siteRoleExact": "write",
            "broaderRolesAllowed": False,
            "certificateClientIdPrincipalBindingRequired": True,
            "completeIdentityContextValidationRequired": True,
            "freshInspectionReadbackRequired": True,
            "providerSideIdentityReadbackImplemented": False,
            "providerSideIdentityReadbackRequiredBeforeRuntime": True,
        },
        "localStagingOutbox": {
            "adapterExact": "SqliteEvidenceStagingOutbox",
            "engineExact": "sqlite3",
            "scopeExact": "local_single_host_staging_only",
            "centralTruth": False,
            "canCloseMutation": False,
            "promotionSupported": False,
            "centralAcknowledgementSupported": False,
            "cleanupSupported": False,
            "restartSafe": True,
            "transactionModeExact": "BEGIN IMMEDIATE",
            "journalModeExact": "DELETE",
            "synchronousModeExact": "FULL",
            "requiredFileModeOctal": "0600",
            "requiredDirectoryModeOctal": "0700",
            "filesystemPolicyExact": "explicit_linux_local_allowlist",
            "unknownFilesystemAllowed": False,
            "syncedFilesystemDetectionImplemented": False,
            "parentDirectoryFsyncAfterCreate": True,
            "maximumDatabaseBytes": 8388608,
            "sequenceHashTransitionValidationRequired": True,
        },
        "offlineCompletion": {
            "statusExact": STATUS,
            "productionReadinessClaimed": False,
            "runtimeCompositionEnabled": False,
            "liveWriteAuthorized": False,
            "socketOrDnsCallsExact": 0,
            "externalCredentialStoreReadsExact": 0,
            "graphCallsExact": 0,
            "azureCallsExact": 0,
            "tenantWritesExact": 0,
        },
    }
    for section, expected in exact_sections.items():
        if contract.get(section) != expected:
            errors.append(f"domain.{section}")
    if contract.get("offlineVerifiedAdaptersExact") != [
        "CertificateWriteIdentityFactory",
        "GitHubS4dOwnerApprovalVerifier",
        "SqliteEvidenceStagingOutbox",
        "UrllibNoRedirectGraphHttpPort",
    ]:
        errors.append("domain.offlineVerifiedAdaptersExact")
    if contract.get("extendsContractsExact") != [
        "workflows/contracts/business-case-type-live-write-boundary-s4d.contract.json",
        "workflows/contracts/business-case-type-live-write-readiness-s4e.contract.json",
        "workflows/contracts/business-case-type-immutable-evidence-s6.contract.json",
    ]:
        errors.append("domain.extendsContractsExact")
    required_out_of_scope = {
        "azure_blob_worm_deployment_or_lock",
        "central_postgresql_outbox_or_promotion",
        "live_graph_or_tenant_write",
        "production_identity_readback",
        "runtime_composition",
    }
    if not required_out_of_scope.issubset(set(contract.get("outOfScopeExact", []))):
        errors.append("domain.outOfScopeExact")
    return errors


def validate_verification_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, value in {
        "schemaVersion": "nac.verification-contract/v0.1",
        "id": "business-case-type-production-adapters-s4f",
        "title": "BusinessCaseType partial production adapter implementations S4f verification",
        "issue": "https://github.com/notariat8/NaC/issues/704",
    }.items():
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
        "unresolvedP1OrP2Findings": 0,
    }:
        errors.append("verification.thresholds")
    if contract.get("passCondition") != {
        "allChecksPass": True,
        "statusExact": STATUS,
        "productionReadinessClaimed": False,
        "runtimeCompositionEnabled": False,
        "liveWriteAuthorized": False,
    }:
        errors.append("verification.passCondition")
    if contract.get("failureBehavior") != {
        "mode": "fail_closed",
        "mergeAllowed": False,
        "liveRetryAllowed": False,
        "ownerInputRequiredForLiveBoundary": True,
    }:
        errors.append("verification.failureBehavior")
    evidence = "\n".join(contract.get("requiredEvidence", []))
    for marker in (
        "PostgreSQL promotion/ack/retention/local cleanup",
        "identity readback",
        "irreversible lock",
        "no production-readiness",
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
        print("BusinessCaseType S4f production adapter contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("BusinessCaseType S4f production adapter contracts: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
