from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = (
    ROOT
    / "workflows/contracts/business-case-type-graph-write-composition-s4c.contract.json"
)
VERIFICATION_PATH = (
    ROOT
    / "workflows/verification-contracts/business-case-type-graph-write-composition-s4c.verification.json"
)

ACCEPTANCE_IDS = [f"AC-S4C-{index:02d}" for index in range(1, 9)]
TRANSITIONS = [
    "clear_absent_to_clear_open_intent",
    "clear_retryable_to_clear_open_new_authorization_intent",
    "clear_open_outcome_event_only",
    "clear_open_to_required_open",
    "clear_open_to_clear_closed_or_retryable_verified_readback",
    "required_open_non_closing_readback_event_only",
    "required_open_closure_or_replay_blocked",
    "closed_terminal_replay_blocked",
]


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def validate_domain_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "schemaVersion": (
            "nac.business-case-type-graph-write-composition-s4c/v0.1"
        ),
        "title": "BusinessCaseType offline Graph write composition S4c",
        "issue": "https://github.com/notariat8/NaC/issues/698",
        "status": "S4C_COMPOSITION_READY_OFFLINE",
        "extendsContract": (
            "workflows/contracts/"
            "business-case-type-graph-write-edge-s4b.contract.json"
        ),
        "acceptanceIdsExact": ACCEPTANCE_IDS,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"domain.{key}")

    state = contract.get("stateStore", {})
    for key, value in {
        "engineExact": "sqlite3",
        "scopeExact": "local_single_host_runtime",
        "transactionModeExact": "BEGIN IMMEDIATE",
        "journalModeExact": "DELETE",
        "synchronousModeExact": "FULL",
        "foreignKeysExact": True,
        "trustedSchemaExact": False,
        "busyTimeoutMillisecondsExact": 0,
        "directoryModeOctal": "0700",
        "requiredFileModeOctal": "0600",
        "filesystemEnvelopeExact": (
            "local_posix_single_host_process_restart"
        ),
        "networkOrSyncedFilesystemAllowed": False,
        "powerKernelHardwareOrHostLossDurabilityClaimed": False,
        "stateAndEventCommitAtomic": True,
        "transitionsExact": TRANSITIONS,
        "maximumDatabaseBytes": 16777216,
    }.items():
        if state.get(key) != value:
            errors.append(f"domain.stateStore.{key}")

    transport = contract.get("transport", {})
    for key, value in {
        "baseUrlExact": "https://graph.microsoft.com/v1.0",
        "methodsExact": ["GET", "POST", "PATCH"],
        "redirectsAllowed": False,
        "automaticRetries": 0,
        "oneHttpAttemptPerTransportCall": True,
        "edgeOnlyCallerContract": True,
        "collectionPathsBoundAtConstruction": 2,
        "planShaVerifiedByTransport": False,
        "maximumResponseBytes": 1048576,
        "graphBetaAllowed": False,
        "foreignHostsAllowed": False,
        "sharePointRestAllowed": False,
        "graphSdkAllowed": False,
        "pnpAllowed": False,
    }.items():
        if transport.get(key) != value:
            errors.append(f"domain.transport.{key}")

    credential = contract.get("credentialBoundary", {})
    for key, value in {
        "tokenProviderCalledOnlyByTransport": True,
        "preTransportBlockedTokenProviderCalls": 0,
        "externalCredentialStoreReads": 0,
        "syntheticTokenProviderCallsReportedSeparately": True,
        "environmentProviderIncluded": False,
        "managedIdentityFactoryIncluded": False,
        "certificateFactoryIncluded": False,
    }.items():
        if credential.get(key) != value:
            errors.append(f"domain.credentialBoundary.{key}")

    offline = contract.get("offlineCompletion", {})
    for key, value in {
        "statusExact": "S4C_COMPOSITION_READY_OFFLINE",
        "socketOrDnsCallsExact": 0,
        "externalCredentialStoreReadsExact": 0,
        "liveGraphCallsExact": 0,
        "tenantWritesExact": 0,
        "centralDurabilityClaimed": False,
        "productionReadyClaimed": False,
        "syntheticTokenProviderCallsReported": True,
    }.items():
        if offline.get(key) != value:
            errors.append(f"domain.offlineCompletion.{key}")

    for section_name, actual, expected_values in (
        (
            "composition",
            contract.get("composition", {}),
            {
                "planBuilderExact": "BusinessCaseTypeWritePlanBuilder",
                "edgeExact": "BusinessCaseTypeGraphWriteEdge",
                "stateAdapterExact": "SqliteMutationEvidenceHook",
                "transportAdapterExact": "GraphRestV1WriteTransport",
                "credentialPortExact": "GraphWriteAccessTokenProvider",
                "operationsInheritedUnchanged": True,
                "liveFactoryIncluded": False,
                "environmentReads": 0,
                "credentialFileReads": 0,
            },
        ),
        (
            "stateStore",
            state,
            {
                "centralMultiInstanceDurabilityClaimed": False,
                "compareAndSwapFieldsExact": [
                    "execution_key",
                    "intent_generation",
                    "closed_generation",
                    "authorization_run_identity",
                ],
                "symlinkDatabaseAllowed": False,
                "corruptUnreadableOrOversizedBehaviorExact": (
                    "fail_closed_unavailable"
                ),
                "rawPayloadStored": False,
                "parentDirectoryFsyncAfterCreate": True,
                "cleanCloseSidecarsExact": 0,
            },
        ),
        (
            "transport",
            transport,
            {
                "responseJsonShapeExact": "object_or_empty",
                "allowedResponseHeadersExact": [
                    "ETag",
                    "Location",
                    "Retry-After",
                ],
                "networkPortInjected": True,
            },
        ),
        (
            "credentialBoundary",
            credential,
            {
                "providerErrorTextPersistedOrReturned": False,
            },
        ),
        (
            "redaction",
            contract.get("redaction", {}),
            {
                "allowlistedEvidenceFieldsExact": [
                    "schema_version",
                    "mutation_id",
                    "execution_key",
                    "operation",
                    "target_binding_hash",
                    "plan_sha256",
                    "authorization_run_identity",
                    "result_code",
                    "s5_operation_hash",
                    "http_status",
                    "intent_generation",
                    "expected_intent_generation",
                    "prior_authorization_run_identity",
                    "close_intent",
                    "completion_state",
                ],
                "forbiddenPersistedDataExact": [
                    "access_token",
                    "approval_ref",
                    "certificate",
                    "field_values",
                    "headers",
                    "item_id",
                    "private_key",
                    "request_body",
                    "response_body",
                    "site_id",
                    "list_id",
                    "url",
                ],
                "recursiveAllowlistRequired": True,
            },
        ),
        (
            "crashRecovery",
            contract.get("crashRecovery", {}),
            {
                "windowsExact": [
                    "intent_before_transport",
                    "transport_before_outcome",
                    "outcome_before_readback",
                    "closure_before_acknowledgement",
                    "corrupt_or_unreadable_state",
                ],
                "automaticReplayAfterRestart": False,
                "openOrUncertainStateBehaviorExact": (
                    "block_until_external_reconciliation"
                ),
                "durableClosedStateBehaviorExact": (
                    "terminal_replay_block"
                ),
            },
        ),
    ):
        for key, value in expected_values.items():
            if actual.get(key) != value:
                errors.append(f"domain.{section_name}.{key}")

    if contract.get("outOfScopeExact") != [
        "central_multi_instance_state",
        "credential_factory",
        "entra_permission_change",
        "live_execute_command",
        "live_graph_call",
        "live_reconciliation",
        "s6_worm_publisher_composition",
        "tenant_write",
        "write_identity_provisioning",
    ]:
        errors.append("domain.outOfScopeExact")
    return errors


def validate_verification_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    exact = {
        "schemaVersion": "nac.verification-contract/v0.1",
        "id": "business-case-type-graph-write-composition-s4c",
        "title": (
            "BusinessCaseType offline Graph write composition S4c verification"
        ),
        "issue": "https://github.com/notariat8/NaC/issues/698",
        "appliesWhen": {
            "paths": [
                "src/nac_m365_graph/business_case_type_write_composition.py",
                "src/nac_m365_graph/business_case_type_write_state.py",
                "src/nac_m365_graph/business_case_type_write_transport.py",
                "src/nac_m365_graph/business_case_type_write_composition_smoke.py",
                "src/nac_cli/cli.py",
                "scripts/validate_business_case_type_graph_write_composition.py",
                (
                    "tests/fixtures/"
                    "business-case-type-graph-write-composition/"
                    "sitecustomize.py"
                ),
                "tests/test_business_case_type_graph_write_composition.py",
                "tests/test_business_case_type_graph_write_state_store.py",
                "tests/test_business_case_type_graph_write_http_transport.py",
                "tests/test_business_case_type_graph_write_credentials.py",
                "tests/test_business_case_type_graph_write_crash_recovery.py",
                (
                    "tests/"
                    "test_business_case_type_graph_write_composition_contract.py"
                ),
                "tests/test_business_case_type_graph_write_composition_cli.py",
                (
                    "workflows/contracts/"
                    "business-case-type-graph-write-composition-s4c.contract.json"
                ),
                (
                    "workflows/verification-contracts/"
                    "business-case-type-graph-write-composition-s4c.verification.json"
                ),
            ]
        },
        "requiredContext": [
            "AGENTS.md",
            (
                "docs/de/superpowers/specs/2026-07-29-"
                "business-case-type-graph-write-composition-s4c-design.md"
            ),
            (
                "docs/de/superpowers/plans/2026-07-29-"
                "business-case-type-graph-write-composition-s4c.md"
            ),
            (
                "workflows/contracts/"
                "business-case-type-graph-write-edge-s4b.contract.json"
            ),
            (
                "workflows/contracts/"
                "business-case-type-graph-write-composition-s4c.contract.json"
            ),
        ],
        "requiredEvidence": [
            "All eight AC-S4C acceptance IDs are present in spec, contract, validator and tests.",
            "SQLite state and event transitions are atomic and generation-CAS protected within the local POSIX single-host process-restart envelope.",
            "Crash/restart tests prove open and uncertain state blocks automatic replay.",
            "Two-connection tests cover the complete absent/open/required/retryable/closed transition matrix, busy handling and duplicate phases.",
            "Graph transport tests prove exact v1.0 origin, both construction-bound collections, methods, headers, response limits, no redirects and one HTTP attempt per transport call.",
            "Credential tests distinguish token-provider calls from external credential-store reads and prove zero token-provider calls for pre-transport blocks.",
            "Persistent and returned evidence contains only allowlisted redacted technical fields.",
            "Offline smoke reports S4C_COMPOSITION_READY_OFFLINE with socket/DNS, external credential-store, live Graph and tenant counters at zero and synthetic token-provider calls separate.",
            "Independent base...head review has no unresolved findings.",
        ],
        "invariants": [
            "The historical S4b zero-live contract remains unchanged.",
            "Exactly five S4b operations remain allowed.",
            "No environment, token file, certificate file or credential store is read.",
            "No live Graph, SharePoint, Teams, Entra or tenant write is performed.",
            "Local SQLite durability is not represented as central or production durability.",
            "Live factory, write identity, S6/WORM composition and external reconciliation remain owner-gated.",
        ],
        "thresholds": {
            "liveGraphCalls": 0,
            "tenantWrites": 0,
            "automaticRetries": 0,
            "unresolvedReviewFindings": 0,
            "socketOrDnsCalls": 0,
            "externalCredentialStoreReads": 0,
        },
        "passCondition": {
            "allChecksPass": True,
            "statusExact": "S4C_COMPOSITION_READY_OFFLINE",
        },
        "failureBehavior": {
            "mode": "fail_closed",
            "mergeAllowed": False,
            "liveRetryAllowed": False,
            "ownerInputRequiredForLiveBoundary": True,
        },
    }
    for key, value in exact.items():
        if contract.get(key) != value:
            errors.append(f"verification.{key}")

    checks = contract.get("checks")
    expected_checks = [
        "python3 -m unittest tests.test_business_case_type_graph_write_composition tests.test_business_case_type_graph_write_state_store tests.test_business_case_type_graph_write_http_transport tests.test_business_case_type_graph_write_credentials tests.test_business_case_type_graph_write_crash_recovery tests.test_business_case_type_graph_write_composition_contract tests.test_business_case_type_graph_write_composition_cli",
        "python3 scripts/validate_business_case_type_graph_write_composition.py",
        "python3 scripts/nac.py contracts verify",
        "python3 scripts/validate_spec_traceability.py",
        "python3 scripts/validate_language_parity.py",
        "python3 scripts/validate_doc_links.py",
        "git diff --check",
        "python3 -m compileall -q src scripts tests",
        "python3 scripts/quality_gate.py --profile strict",
    ]
    if checks != expected_checks:
        errors.append("verification.checks")
    return errors


def validate_implementation() -> list[str]:
    errors: list[str] = []
    required_sources = {
        "src/nac_m365_graph/business_case_type_write_state.py": (
            "class SqliteMutationEvidenceHook"
        ),
        "src/nac_m365_graph/business_case_type_write_transport.py": (
            "class GraphRestV1WriteTransport"
        ),
        "src/nac_m365_graph/business_case_type_write_composition.py": (
            "class BusinessCaseTypeWriteComposition"
        ),
        "src/nac_m365_graph/business_case_type_write_composition_smoke.py": (
            "S4C_COMPOSITION_READY_OFFLINE"
        ),
    }
    for relative, marker in required_sources.items():
        path = ROOT / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"implementation.missing.{relative}")
            continue
        if marker not in text:
            errors.append(f"implementation.marker.{relative}")
    return errors


def main() -> int:
    errors = [
        *validate_domain_contract(_load(DOMAIN_PATH)),
        *validate_verification_contract(_load(VERIFICATION_PATH)),
        *validate_implementation(),
    ]
    if errors:
        print(json.dumps({"errors": sorted(errors), "status": "FAILED"}))
        return 1
    print("business-case-type Graph write composition S4c: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
