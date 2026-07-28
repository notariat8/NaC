#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_path = str(SRC)
if src_path in sys.path:
    sys.path.remove(src_path)
sys.path.insert(0, src_path)

from nac_runtime.azure_blob_worm import (  # noqa: E402
    LIVE_STATUS,
    S6B_STATUS,
    AzureBlobContainerPolicy,
    AzureBlobImmutabilityPolicySnapshot,
    AzureBlobProviderContext,
    AzureBlobWormError,
    AzureBlobWormJournal,
    FakeAzureBlobWormTransport,
    azure_provider_context_binding_sha256,
    minimum_retention_days,
    prepare_irreversible_lock_plan,
    verify_irreversible_lock_evidence,
    worm_commit_idempotency_key,
)
from nac_runtime.immutable_evidence import (  # noqa: E402
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    ZERO_HASH,
    EvidenceRecord,
    InMemoryEvidenceOutbox,
    WormJournalPort,
    _publication_operation_key,
    actor_ref,
    build_event,
    correlation_ref,
    typed_identifier_registry,
)


DOMAIN = ROOT / "workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json"
LOCK = ROOT / "workflows/contracts/azure-blob-worm-irreversible-lock-s6b.contract.json"
VERIFICATION = ROOT / "workflows/verification-contracts/business-case-type-azure-blob-worm-s6b.verification.json"
BICEP = ROOT / "deploy/runtime/azure/immutable-evidence/main.bicep"
BICEP_PARAMS = ROOT / "deploy/runtime/azure/immutable-evidence/main.bicepparam"
MODULE = ROOT / "src/nac_runtime/azure_blob_worm.py"
QUALITY_GATE = ROOT / "scripts/quality_gate.py"
CENTRAL_CLI = ROOT / "src/nac_cli/cli.py"
KG_CLI = ROOT / "src/notary_kg/cli.py"
CI_WORKFLOW = ROOT / ".github/workflows/quality-gate.yml"
AGENT_CONTEXT = ROOT / "agent-context/index.json"
ARCHITECTURE_CONTRACT = ROOT / "workflows/contracts/microsoft-first-onprem-target-architecture.contract.json"
DOCS = [
    ROOT / "docs/de/superpowers/specs/2026-07-28-business-case-type-azure-blob-worm-s6b-design.md",
    ROOT / "docs/en/superpowers/specs/2026-07-28-business-case-type-azure-blob-worm-s6b-design.md",
    ROOT / "docs/de/superpowers/plans/2026-07-28-business-case-type-azure-blob-worm-s6b.md",
    ROOT / "docs/en/superpowers/plans/2026-07-28-business-case-type-azure-blob-worm-s6b.md",
]
EXPECTED_ACCEPTANCE = [f"AC-S6B-{index:02d}" for index in range(1, 8)]
CMK_REF_SHA256 = "c" * 64
PROVIDER_TENANT_ID = "44444444-4444-4444-8444-444444444444"
PROVIDER_SUBSCRIPTION_ID = "/subscriptions/55555555-5555-4555-8555-555555555555"
PROVIDER_RESOURCE_ID = (
    PROVIDER_SUBSCRIPTION_ID
    + "/resourceGroups/rg-nac-worm/providers/Microsoft.Storage/"
    + "storageAccounts/stnacwormoffline001"
)
PROVIDER_CONTEXT = AzureBlobProviderContext(
    tenant_id=PROVIDER_TENANT_ID,
    subscription_resource_id=PROVIDER_SUBSCRIPTION_ID,
    resource_id=PROVIDER_RESOURCE_ID,
    readback_source="azure-subscription-resource-tenant-readback",
)
PROVIDER_TENANT_BINDING_SHA256 = hashlib.sha256(
    ("nac.azure-provider-tenant.v1|" + PROVIDER_TENANT_ID).encode("ascii")
).hexdigest()
PROVIDER_SUBSCRIPTION_BINDING_SHA256 = hashlib.sha256(
    (
        "nac.azure-subscription-resource.v1|" + PROVIDER_SUBSCRIPTION_ID
    ).encode("ascii")
).hexdigest()
PROVIDER_RESOURCE_BINDING_SHA256 = hashlib.sha256(
    ("nac.azure-storage-resource.v1|" + PROVIDER_RESOURCE_ID).encode("ascii")
).hexdigest()
PROVIDER_CONTEXT_BINDING_SHA256 = azure_provider_context_binding_sha256(
    PROVIDER_CONTEXT
)
EXPECTED_BICEP_MARKERS = [
    "allowBlobPublicAccess: false",
    "allowCrossTenantReplication: false",
    "allowSharedKeyAccess: false",
    "defaultToOAuthAuthentication: true",
    "publicNetworkAccess: 'Disabled'",
    "requireInfrastructureEncryption: true",
    "isVersioningEnabled: true",
    "immutableStorageWithVersioning:",
    "var immutableRetentionDays = 3653",
    "immutabilityPeriodSinceCreationInDays: immutableRetentionDays",
    "keySource: 'Microsoft.Keyvault'",
    "source: 'Microsoft.KeyVault'",
    "Microsoft.ManagedIdentity/userAssignedIdentities",
    "Microsoft.Authorization/roleDefinitions@2022-04-01",
    "e147488a-f6f5-4113-8e2d-b22465e65bf6",
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
    "Microsoft.Storage/storageAccounts/blobServices/containers/read",
    "Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/read",
    "Microsoft.Storage/storageAccounts/encryptionScopes/read",
    "subscription().tenantId",
    "var targetIsolationSuffix = uniqueString(subscription().tenantId, resourceGroup().id, storageAccountName)",
    "providerTenantBindingSha256",
    "providerSubscriptionBindingSha256",
    "providerResourceBindingSha256",
    "providerContextBindingSha256",
    "azure-subscription-resource-tenant-readback",
]


def main() -> int:
    errors: list[str] = []
    domain = _load(DOMAIN, errors)
    lock = _load(LOCK, errors)
    verification = _load(VERIFICATION, errors)
    if errors:
        return _finish(errors)

    _validate_contracts(domain, lock, verification, errors)
    _validate_port_and_smoke(errors)
    _validate_lock_plan(errors)
    _validate_source(errors)
    _validate_bicep(errors)
    _validate_docs(errors)
    _validate_central_integration(errors)
    return _finish(errors)


def _validate_contracts(
    domain: dict[str, object],
    lock: dict[str, object],
    verification: dict[str, object],
    errors: list[str],
) -> None:
    _expect(domain.get("status") == S6B_STATUS, "domain status drift", errors)
    _expect(verification.get("status") == S6B_STATUS, "verification status drift", errors)
    _expect(lock.get("status") == "PREPARED_OFFLINE_NOT_EXECUTED", "lock status drift", errors)
    slice_contract = domain.get("slice", {})
    _expect(
        isinstance(slice_contract, dict)
        and slice_contract.get("offline_only") is True
        and slice_contract.get("live_status_exact") == LIVE_STATUS
        and slice_contract.get("live_factory_wiring") is False
        and slice_contract.get("allowed_lock_actions") == 0,
        "offline or S7 boundary drift",
        errors,
    )
    for field in (
        "allowed_network_calls",
        "allowed_azure_calls",
        "allowed_credential_reads",
        "allowed_tenant_writes",
    ):
        _expect(
            isinstance(slice_contract, dict) and slice_contract.get(field) == 0,
            f"{field} must remain zero",
            errors,
        )
    acceptance = [
        item.get("id")
        for item in domain.get("acceptance_criteria", [])
        if isinstance(item, dict)
    ]
    _expect(acceptance == EXPECTED_ACCEPTANCE, "domain acceptance IDs drift", errors)
    _expect(verification.get("acceptance_ids") == EXPECTED_ACCEPTANCE, "verification acceptance IDs drift", errors)

    receipt = domain.get("version_bound_receipt", {})
    _expect(
        isinstance(receipt, dict)
        and receipt.get("blob_locator_bits") == 128
        and receipt.get("version_binding_bits") == 128
        and receipt.get("create_http_status_exact") == 201
        and receipt.get("create_version_header_exact") == "x-ms-version-id"
        and receipt.get("conflict_http_status_exact") == 412
        and receipt.get("conflict_response_version_id_allowed") is False
        and receipt.get("transport_get_selector_exact") == "raw versionid"
        and receipt.get("transport_hash_selector_allowed") is False
        and receipt.get("public_readback_exact_version_required") is True,
        "version-bound receipt contract drift",
        errors,
    )
    tenant = domain.get("provider_tenant_evidence", {})
    _expect(
        isinstance(tenant, dict)
        and tenant.get("source_exact")
        == "azure-subscription-resource-tenant-readback"
        and tenant.get("fresh_transport_readback_required") is True
        and len(tenant.get("bindings_exact", [])) == 4
        and tenant.get("plaintext_allowed") is False
        and tenant.get("free_bicep_tenant_binding_parameter_allowed") is False,
        "provider tenant evidence drift",
        errors,
    )
    baseline = domain.get("bicep_baseline", {})
    _expect(
        isinstance(baseline, dict)
        and baseline.get("immutability_policy_state_property_emitted") is False
        and baseline.get("expected_post_deploy_readback_state") == "Unlocked"
        and baseline.get("retention_days") == 3653
        and baseline.get("writer_role_kind") == "CustomRole"
        and baseline.get("writer_data_actions_exact") == [
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
        ]
        and len(baseline.get("writer_management_actions_exact", [])) == 3
        and baseline.get("writer_delete_action_allowed") is False
        and baseline.get("writer_blob_write_action_allowed") is False
        and baseline.get("identity_name_binding_inputs_exact") == [
            "subscription().tenantId",
            "resourceGroup().id",
            "storageAccountName",
        ]
        and baseline.get("compiled_claim") is False,
        "Bicep baseline contract drift",
        errors,
    )
    operation = lock.get("operation", {})
    preconditions = lock.get("preconditions", {})
    dual = lock.get("dual_control", {})
    execution = lock.get("execution", {})
    _expect(
        isinstance(operation, dict)
        and operation.get("operation_exact") == "POST immutabilityPolicies/default/lock"
        and operation.get("api_version_exact") == "2023-05-01"
        and isinstance(preconditions, dict)
        and preconditions.get("if_match_etag_required") is True
        and preconditions.get("prepared_request_sha256_required") is True
        and isinstance(dual, dict)
        and dual.get("operator_approver_distinct") is True
        and isinstance(execution, dict)
        and execution.get("performed_by_s6b") is False
        and execution.get("lock_actions") == 0,
        "irreversible lock contract drift",
        errors,
    )
    compilation = verification.get("bicep_compilation", {})
    integration = verification.get("integration_handoff", {})
    _expect(
        isinstance(compilation, dict)
        and compilation.get("local_compiler_available") is False
        and compilation.get("compiled_claim") is False
        and compilation.get("ci_compile_required") is True
        and compilation.get("ci_must_use_pinned_bicep_version") is True
        and compilation.get("compiled_result_required_before_merge") is True,
        "Bicep compilation evidence drift",
        errors,
    )
    _expect(
        isinstance(integration, dict)
        and integration.get("track_b_central_files_changed") is False
        and integration.get("central_integration_preserved") is True
        and len(integration.get("required_before_merge", [])) == 3
        and integration.get("live_factory_after_integration_allowed") is False,
        "central integration handoff drift",
        errors,
    )


def _validate_port_and_smoke(errors: list[str]) -> None:
    _expect(
        inspect.signature(AzureBlobWormJournal.commit)
        == inspect.signature(WormJournalPort.commit),
        "WormJournalPort commit signature drift",
        errors,
    )
    _expect(
        inspect.signature(AzureBlobWormJournal.readback)
        == inspect.signature(WormJournalPort.readback),
        "WormJournalPort readback signature drift",
        errors,
    )
    _expect(minimum_retention_days(10) == 3653, "10-year retention drift", errors)
    records = _records()
    head = records[-1].event_sha256
    key = worm_commit_idempotency_key(head)
    _expect(key == _publication_operation_key("worm-commit", head), "S6a key derivation drift", errors)
    tenant_binding = records[0].event["tenant_binding_sha256"]
    transport = FakeAzureBlobWormTransport(
        container_name="nac-worm-tenant-a",
        tenant_binding_sha256=tenant_binding,
        policy=AzureBlobContainerPolicy(
            default_immutability_policy_mode="Locked",
            default_retention_days=3653,
            legal_hold_capable=True,
            legal_hold_capability_source="container-policy-properties",
            encryption_scope="nac-worm-tenant-a",
            encryption_key_source="Microsoft.Keyvault",
            customer_managed_key_ref_sha256=CMK_REF_SHA256,
            provider_tenant_binding_sha256=PROVIDER_TENANT_BINDING_SHA256,
            provider_subscription_binding_sha256=(
                PROVIDER_SUBSCRIPTION_BINDING_SHA256
            ),
            provider_resource_binding_sha256=PROVIDER_RESOURCE_BINDING_SHA256,
            provider_context_binding_sha256=PROVIDER_CONTEXT_BINDING_SHA256,
            provider_context_binding_source=(
                "azure-subscription-resource-tenant-readback"
            ),
        ),
        provider_context=PROVIDER_CONTEXT,
    )
    journal = AzureBlobWormJournal(
        transport=transport,
        container_name="nac-worm-tenant-a",
        tenant_binding_sha256=tenant_binding,
        encryption_scope="nac-worm-tenant-a",
        customer_managed_key_ref_sha256=CMK_REF_SHA256,
        expected_provider_context_binding_sha256=(
            PROVIDER_CONTEXT_BINDING_SHA256
        ),
    )
    anchor = _anchor(records)
    try:
        journal.commit(records, anchor, idempotency_key_sha256="d" * 64)
    except AzureBlobWormError:
        pass
    else:
        errors.append("arbitrary operation key was accepted")
    _expect(
        transport.policy_calls == 0 and transport.put_calls == 0 and transport.get_calls == 0,
        "invalid key reached transport",
        errors,
    )
    first = journal.commit(records, anchor, idempotency_key_sha256=key)
    version = transport.blob_snapshot(first["receipt_ref"]).version_id
    second = journal.commit(records, anchor, idempotency_key_sha256=key)
    readback = journal.readback(first["receipt_ref"])
    _expect(first == second, "idempotent receipt drift", errors)
    _expect(
        readback == {**first, "retention_years": 10, "legal_hold_capable": True},
        "full readback drift",
        errors,
    )
    _expect(
        all(item["version_id"] == version for item in transport.get_history)
        and all("version_id_binding" not in item for item in transport.get_history)
        and transport.list_versions_calls >= 2,
        "create, conflict, or public readback raw version binding drift",
        errors,
    )
    _expect(
        transport.create_effects == 1
        and all(item.get("if_none_match") == "*" for item in transport.put_history),
        "create-only behavior drift",
        errors,
    )
    _expect(
        transport.network_calls == 0
        and transport.azure_calls == 0
        and transport.credential_reads == 0,
        "fake transport performed external activity",
        errors,
    )


def _validate_lock_plan(errors: list[str]) -> None:
    pre = AzureBlobImmutabilityPolicySnapshot(
        target_resource_id_sha256="1" * 64,
        provider_context_binding_sha256=PROVIDER_CONTEXT_BINDING_SHA256,
        policy_resource_id_sha256="2" * 64,
        policy_state="Unlocked",
        retention_days=3653,
        etag='"policy-etag-v1"',
    )
    plan = prepare_irreversible_lock_plan(
        pre,
        operator_ref="operator-v1-" + "3" * 64,
        approver_ref="approver-v1-" + "4" * 64,
    )
    post = replace(pre, policy_state="Locked", etag='"policy-etag-v2"')
    evidence = verify_irreversible_lock_evidence(plan, pre, post)
    _expect(evidence.get("result") == "LOCKED_READBACK_VERIFIED", "lock evidence drift", errors)
    for candidate, candidate_pre, candidate_post in (
        (plan, pre, replace(post, target_resource_id_sha256="5" * 64)),
        (plan, replace(pre, etag='"stale"'), post),
        ({**plan, "prepared_request_sha256": "6" * 64}, pre, post),
    ):
        try:
            verify_irreversible_lock_evidence(candidate, candidate_pre, candidate_post)
        except AzureBlobWormError:
            continue
        errors.append("lock target, ETag, or request-hash drift was accepted")


def _validate_source(errors: list[str]) -> None:
    module_text = _read(MODULE, errors)
    for forbidden in ("import azure", "from azure", "os.environ", "requests.", "urllib.request"):
        _expect(forbidden not in module_text, f"forbidden runtime dependency: {forbidden}", errors)
    for marker in (
        "_publication_operation_key(",
        '"worm-commit"',
        'if_none_match="*"',
        "version_id=version_id",
        "list_blob_versions(",
        "status_code == 201",
        "provider_context_binding_sha256",
        "provider_tenant_binding_sha256",
        "prepare_irreversible_lock_plan",
        "verify_irreversible_lock_evidence",
        "block_next_puts",
        "raise AzureBlobWormError(_PUBLIC_ERROR)",
    ):
        _expect(marker in module_text, f"runtime marker missing: {marker}", errors)
    for forbidden in ("version_id_binding: str", "version_id_binding="):
        _expect(
            forbidden not in module_text,
            f"hash selector remains: {forbidden}",
            errors,
        )


def _validate_bicep(errors: list[str]) -> None:
    bicep_text = _read(BICEP, errors)
    params_text = _read(BICEP_PARAMS, errors)
    for marker in EXPECTED_BICEP_MARKERS:
        _expect(marker in bicep_text, f"Bicep marker missing: {marker}", errors)
    for forbidden in (
        "state: 'Unlocked'",
        "state: 'Locked'",
        "param tenantBindingSha256",
        "/delete'",
        "/blobs/write'",
        "ba92f5b4-2d11-453d-a403-e96b0029c9fe",
        "b7e6dc6d-f1e8-4753-8033-0f276bb0955b",
    ):
        _expect(forbidden not in bicep_text, f"forbidden Bicep marker: {forbidden}", errors)
    _expect(bicep_text.count("{") == bicep_text.count("}"), "Bicep brace imbalance", errors)
    _expect(bicep_text.count("[") == bicep_text.count("]"), "Bicep bracket imbalance", errors)
    _expect("using './main.bicep'" in params_text, "Bicep parameter binding missing", errors)
    _expect("tenantBindingSha256" not in params_text, "free tenant parameter remains", errors)


def _validate_docs(errors: list[str]) -> None:
    for path in DOCS:
        text = _read(path, errors)
        _expect(all(identifier in text for identifier in EXPECTED_ACCEPTANCE), f"acceptance traceability missing: {path.relative_to(ROOT)}", errors)
        _expect(S6B_STATUS in text and LIVE_STATUS in text, f"status boundary missing: {path.relative_to(ROOT)}", errors)
        for marker in (
            "3653",
            "version_id",
            "versionid",
            "ETag",
            "CMK",
            "subscription().tenantId",
            "subscription().id",
        ):
            _expect(marker in text, f"documentation marker missing ({marker}): {path.relative_to(ROOT)}", errors)
        _expect(
            "AC-S6B-08" not in text,
            f"unexpected AC08: {path.relative_to(ROOT)}",
            errors,
        )
        _expect("3650" not in text, f"stale retention value: {path.relative_to(ROOT)}", errors)


def _records() -> tuple[EvidenceRecord, ...]:
    tenant_id = "11111111-1111-4111-8111-111111111111"
    key = b"actor-key-for-immutable-evidence"
    actor = actor_ref(
        tenant_id=tenant_id,
        actor_object_id="22222222-2222-4222-8222-222222222222",
        key_version=3,
        key=key,
        principal_key=b"stable-principal-binding-key-0001",
    )
    correlation = correlation_ref(
        tenant_id=tenant_id,
        source_object_id="33333333-3333-4333-8333-333333333333",
        key_version=3,
        key=key,
    )
    registry = typed_identifier_registry(
        business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
        catalog_versions=REGISTERED_CATALOG_VERSIONS,
    )
    outbox = InMemoryEvidenceOutbox()
    for phase in ("intent", "outcome", "readback"):
        existing = outbox.records(correlation)
        values: dict[str, Any] = {
            "correlation_id": correlation,
            "phase": phase,
            "sequence": len(existing) + 1,
            "previous_event_sha256": existing[-1].event_sha256 if existing else ZERO_HASH,
            "actor_ref_value": actor,
            "tool_id": "tool-nac-cli",
            "role_id": "role-migration-operator",
            "action": "schema_apply",
            "business_case_type_id": "immobilienkaufvertrag",
            "catalog_version": next(iter(REGISTERED_CATALOG_VERSIONS)),
            "identifier_registry": registry,
            "manifest_sha256": "a" * 64,
            "occurred_at": "2026-07-28T09:00:00Z",
            "etag_hmac_key": key,
            "etag_hmac_key_version": 1,
        }
        if phase in {"outcome", "readback"}:
            values["result_code"] = "confirmed"
            values["etags"] = {"matter": "synthetic-state-etag"}
        outbox.append(build_event(**values))
    return outbox.records(correlation)


def _anchor(records: tuple[EvidenceRecord, ...]) -> dict[str, object]:
    head = records[-1].event_sha256
    return {
        "anchor_ref": f"anchor-v1-{head}",
        "signature_ref": f"signature-v1-{head}",
        "record_count": len(records),
        "first_event_sha256": records[0].event_sha256,
        "last_event_sha256": head,
        "head_sha256": head,
    }


def _load(path: Path, errors: list[str]) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"invalid JSON: {path.relative_to(ROOT)}")
        return {}
    if type(value) is not dict:
        errors.append(f"root must be an object: {path.relative_to(ROOT)}")
        return {}
    return value


def _read(path: Path, errors: list[str]) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        errors.append(f"unreadable file: {path.relative_to(ROOT)}")
        return ""


def _expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)



def _validate_central_integration(errors: list[str]) -> None:
    required_markers = {
        QUALITY_GATE: "business_case_type_azure_blob_worm_s6b",
        CENTRAL_CLI: "validate_business_case_type_azure_blob_worm.py",
        KG_CLI: "business-case-type-azure-worm-readiness",
        CI_WORKFLOW: "az bicep build --file deploy/runtime/azure/immutable-evidence/main.bicep --stdout",
    }
    for path, marker in required_markers.items():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"missing central integration file: {path.relative_to(ROOT)}")
            continue
        _expect(marker in text, f"central integration marker missing: {marker}", errors)
    try:
        context = json.loads(AGENT_CONTEXT.read_text(encoding="utf-8"))
        architecture = json.loads(ARCHITECTURE_CONTRACT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        errors.append("central context or architecture contract unreadable")
        return
    categories = context.get("layers", [{}, {}, {"categories": []}])[2].get("categories", [])
    _expect(any(item.get("id") == "business_case_type_azure_blob_worm_s6b" for item in categories if isinstance(item, dict)), "agent context S6b category missing", errors)
    decisions = architecture.get("decisions", {})
    audit = architecture.get("layer_boundaries", {}).get("audit", {})
    _expect(decisions.get("worm_authoritative_copy") == "azure_blob_immutable_storage", "architecture WORM target drift", errors)
    _expect(decisions.get("worm_publisher_location") == "onprem", "architecture publisher location drift", errors)
    _expect(audit.get("workflow_runtime_authority") is False, "Azure WORM must not own workflow runtime", errors)


def _finish(errors: list[str]) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("business-case-type Azure Blob WORM S6b: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
