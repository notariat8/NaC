#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_path = str(SRC)
if src_path in sys.path:
    sys.path.remove(src_path)
sys.path.insert(0, src_path)

from nac_m365_graph.business_case_type_live_write_smoke import (  # noqa: E402
    build_business_case_type_live_write_smoke,
)


CONTRACT = (
    ROOT
    / "workflows/contracts/"
    "business-case-type-live-write-boundary-s4d.contract.json"
)
VERIFICATION = (
    ROOT
    / "workflows/verification-contracts/"
    "business-case-type-live-write-boundary-s4d.verification.json"
)
ACCEPTANCE_IDS = [f"AC-S4D-{index:02d}" for index in range(1, 9)]
OPERATIONS = [
    "case_create",
    "case_status_update",
    "task_create",
    "task_update",
    "business_case_type_backfill",
]


def validate() -> list[str]:
    errors: list[str] = []
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    except Exception:
        return ["S4d contract pair is not readable JSON"]

    if (
        contract.get("schemaVersion")
        != "nac.business-case-type-live-write-boundary-s4d/v0.1"
        or contract.get("status") != "S4D_READY_OFFLINE"
        or contract.get("acceptanceIdsExact") != ACCEPTANCE_IDS
    ):
        errors.append("S4d domain contract header or acceptance IDs drift")
    owner_gate = contract.get("ownerGate", {})
    if (
        owner_gate.get("approvalRefPatternExact")
        != "owner-approval-v1-<sha256>"
        or owner_gate.get("staticDriftCredentialCalls") != 0
        or owner_gate.get("liveRunnerIncluded") is not False
        or owner_gate.get("approvalVerificationRequiredBeforeIdentityReadback") is not True
        or owner_gate.get("approvalCandidateSelfAuthorizing") is not False
        or owner_gate.get("finalPlanRevalidationBeforeOwnerVerification") is not True
    ):
        errors.append("S4d owner gate drift")
    target = contract.get("targetBinding", {})
    if (
        target.get("workspaceIdExact") != "notary_team_01"
        or target.get("graphBaseUrlExact")
        != "https://graph.microsoft.com/v1.0"
        or target.get("fieldsExact")
        != [
            "tenant_binding_sha256",
            "workspace_id",
            "site_id",
            "akten_list_id",
            "aufgaben_list_id",
            "graph_base_url",
        ]
    ):
        errors.append("S4d target binding drift")
    identity = contract.get("identityBoundary", {})
    if (
        identity.get("writeIdentityPermissionExact")
        != ["Sites.Selected"]
        or identity.get("writeSiteRoleExact") != ["write"]
        or identity.get("bffPermissionExact") != ["Sites.Selected"]
        or identity.get("bffSiteRoleExact") != ["read"]
        or identity.get("writeAndBffPrincipalsDistinct") is not True
        or identity.get("broaderRolesAllowed") is not False
        or identity.get("provisioningAppReuseAllowed") is not False
        or identity.get("inspectionSourceExact")
        != "synthetic-offline-owner-bound-readback"
        or identity.get("inspectionObservedAtRequired") is not True
        or identity.get("inspectionPrincipalOwnerBound") is not True
    ):
        errors.append("S4d identity least-privilege boundary drift")
    evidence = contract.get("evidenceComposition", {})
    if (
        evidence.get("eventSchemaExact")
        != "nac.immutable-evidence-event/v0.2"
        or evidence.get("operationsExact") != OPERATIONS
        or evidence.get("automaticMutationReplay") is not False
        or evidence.get("distributedAtomicityClaimed") is not False
        or evidence.get("successfulReadbackProviderStateSha256Required") is not True
        or evidence.get("existingPhaseReuseExact")
        != "byte_identical_event_only"
        or evidence.get("foreignCorrelationChainClosesLocalIntent") is not False
    ):
        errors.append("S4d evidence composition drift")
    offline = contract.get("offlineCompletion", {})
    for field in (
        "socketOrDnsCallsExact",
        "externalCredentialStoreReadsExact",
        "liveGraphCallsExact",
        "azureLiveCallsExact",
        "tenantWritesExact",
    ):
        if offline.get(field) != 0:
            errors.append(f"S4d offline counter drift: {field}")
    if (
        offline.get("statusExact") != "S4D_READY_OFFLINE"
        or offline.get("productionDurabilityClaimed") is not False
        or offline.get("productionIdentityAdapterIncluded") is not False
    ):
        errors.append("S4d offline completion claim drift")

    if (
        verification.get("id")
        != "business-case-type-live-write-boundary-s4d"
        or verification.get("passCondition", {}).get("statusExact")
        != "S4D_READY_OFFLINE"
        or verification.get("failureBehavior", {}).get("mode")
        != "fail_closed"
    ):
        errors.append("S4d verification contract drift")

    required_sources = {
        "src/nac_m365_graph/business_case_type_live_write_gate.py": [
            "owner-approval-v1-",
            "OwnerApprovalVerifierPort",
            "github_issue_owner_comment",
            "Sites.Selected",
            "broader Graph role detected",
        ],
        "src/nac_m365_graph/business_case_type_live_write_evidence.py": [
            "S4dMutationEvidenceHook",
            "_validated_publication_result",
            "canonical outbox phase belongs to another mutation",
            "provider_state_sha256",
            "worm_readback_verified",
        ],
        "src/nac_m365_graph/business_case_type_live_write_boundary.py": [
            "live_target_binding_sha256",
            "approval_plan_binding_sha256",
            "final plan revalidation drift",
            "identity_readback_not_exact",
        ],
        "src/nac_runtime/immutable_evidence.py": [
            "nac.immutable-evidence-event/v0.2",
            "S4D_LIVE_WRITE_ACTIONS",
            "operation_binding_sha256",
        ],
    }
    for relative, markers in required_sources.items():
        path = ROOT / relative
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative} misses marker {marker}")

    if not errors:
        with tempfile.TemporaryDirectory() as directory:
            result = build_business_case_type_live_write_smoke(
                database_path=Path(directory) / "state.sqlite"
            )
        if (
            result.get("status") != "S4D_READY_OFFLINE"
            or [item.get("operation") for item in result.get("operations", [])]
            != OPERATIONS
            or any(
                item.get("status") != "S4D_WRITE_VERIFIED"
                for item in result.get("operations", [])
            )
        ):
            errors.append("S4d offline one-shot smoke failed")
        summary = result.get("summary", {})
        for field in (
            "socket_or_dns_calls",
            "external_credential_store_reads",
            "live_graph_calls",
            "azure_live_calls",
            "tenant_writes",
        ):
            if summary.get(field) != 0:
                errors.append(f"S4d smoke counter drift: {field}")
        for fault in (
            "plan_sha",
            "owner_verification",
            "identity_provenance",
        ):
            with tempfile.TemporaryDirectory() as directory:
                blocked = build_business_case_type_live_write_smoke(
                    database_path=Path(directory) / "state.sqlite",
                    fault=fault,
                )
            blocked_summary = blocked.get("summary", {})
            if (
                blocked.get("status") != "BLOCKED"
                or blocked_summary.get("identity_factory_calls") != 0
                or blocked_summary.get("synthetic_http_port_calls") != 0
                or blocked_summary.get("tenant_writes") != 0
            ):
                errors.append(f"S4d fail-closed smoke failed: {fault}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("BusinessCaseType live write boundary S4d validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
