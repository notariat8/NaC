#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_live_write_readiness import (  # noqa: E402
    build_business_case_type_live_write_readiness,
    current_business_case_type_live_write_readiness,
    synthetic_ready_input,
)


CONTRACT = ROOT / "workflows/contracts/business-case-type-live-write-readiness-s4e.contract.json"
VERIFICATION = ROOT / "workflows/verification-contracts/business-case-type-live-write-readiness-s4e.verification.json"
ACCEPTANCE_IDS = [f"AC-S4E-{index:02d}" for index in range(1, 8)]
BINDINGS = [
    "toolchain_binding_sha256",
    "provisioner_bootstrap_binding_sha256",
    "public_certificate_sha256",
    "worm_target_binding_sha256",
    "worm_cmk_binding_sha256",
    "worm_encryption_scope_binding_sha256",
    "worm_policy_sha256",
]
ADAPTERS = [
    "owner_verifier",
    "write_token_provider",
    "redirect_free_graph_http",
    "azure_blob_worm_transport",
    "durable_outbox",
    "broker",
    "signature_anchor",
    "reconciliation_store",
]


def validate() -> list[str]:
    errors: list[str] = []
    try:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    except Exception:
        return ["S4e contract pair is not readable JSON"]

    if (
        contract.get("schemaVersion")
        != "nac.business-case-type-live-write-readiness-s4e/v0.1"
        or contract.get("status") != "BLOCKED"
        or contract.get("acceptanceIdsExact") != ACCEPTANCE_IDS
    ):
        errors.append("S4e contract header or acceptance IDs drift")
    identity = contract.get("identityBoundary", {})
    if (
        identity.get("workspaceIdExact") != "notary_team_01"
        or identity.get("provisioningAppExecutesBusinessWrites") is not False
        or identity.get("threePrincipalsPairwiseDistinct") is not True
        or identity.get("businessWriteExecutorExact")
        != "dedicated_write_principal"
        or identity.get("writeIdentityPermissionExact") != ["Sites.Selected"]
        or identity.get("writeSiteRoleExact") != ["write"]
        or identity.get("bffPermissionExact") != ["Sites.Selected"]
        or identity.get("bffSiteRoleExact") != ["read"]
    ):
        errors.append("S4e identity boundary drift")
    if contract.get("requiredProductionAdaptersExact") != ADAPTERS:
        errors.append("S4e adapter inventory drift")
    if contract.get("requiredBindingsExact") != BINDINGS:
        errors.append("S4e binding inventory drift")
    offline = contract.get("offlineCompletion", {})
    for field in (
        "socketOrDnsCallsExact",
        "externalCredentialStoreReadsExact",
        "graphCallsExact",
        "azureCallsExact",
        "tenantWritesExact",
    ):
        if offline.get(field) != 0:
            errors.append(f"S4e offline counter drift: {field}")
    if (
        offline.get("currentStatusExact") != "BLOCKED"
        or offline.get("completeSyntheticShapeStatusExact") != "S4E_READY_OFFLINE"
        or offline.get("liveWriteAuthorized") is not False
        or offline.get("liveRunnerIncluded") is not False
        or offline.get("productionAdaptersImplemented") is not False
        or offline.get("assessmentSourceExact")
        != "contract_pinned_repository_snapshot"
        or offline.get("liveStateInspected") is not False
    ):
        errors.append("S4e offline completion claim drift")
    if (
        verification.get("id") != "business-case-type-live-write-readiness-s4e"
        or verification.get("passCondition", {}).get("currentStatusExact") != "BLOCKED"
        or verification.get("failureBehavior", {}).get("mode") != "fail_closed"
    ):
        errors.append("S4e verification contract drift")

    current = current_business_case_type_live_write_readiness()
    ready = build_business_case_type_live_write_readiness(synthetic_ready_input())
    if current.get("status") != "BLOCKED":
        errors.append("S4e current repository state must remain BLOCKED")
    if ready.get("status") != "S4E_READY_OFFLINE" or ready.get("live_write_authorized") is not False:
        errors.append("S4e synthetic reference shape drift")
    for result_name, result in (("current", current), ("ready", ready)):
        summary = result.get("summary", {})
        for field in (
            "socket_or_dns_calls",
            "external_credential_store_reads",
            "graph_calls",
            "azure_calls",
            "tenant_writes",
        ):
            if summary.get(field) != 0:
                errors.append(f"S4e {result_name} counter drift: {field}")
        encoded = json.dumps(result, sort_keys=True)
        for forbidden in ("private_key", "access_token", "client_secret"):
            if forbidden in encoded:
                errors.append(f"S4e output exposes forbidden marker: {forbidden}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("BusinessCaseType live write readiness S4e validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
