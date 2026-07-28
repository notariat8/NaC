# BusinessCaseType Azure Blob WORM S6b Design

Status: `S6B_AZURE_WORM_ADAPTER_READY_OFFLINE`
Live status: `BLOCKED_PENDING_S7_APPROVAL`
Leading issue: [#693](https://github.com/notariat8/NaC/issues/693)
Domain contract: [business-case-type-azure-blob-worm-s6b.contract.json](../../../../../workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json)
Lock contract: [azure-blob-worm-irreversible-lock-s6b.contract.json](../../../../../workflows/contracts/azure-blob-worm-irreversible-lock-s6b.contract.json)
Verification contract: [business-case-type-azure-blob-worm-s6b.verification.json](../../../../../workflows/verification-contracts/business-case-type-azure-blob-worm-s6b.verification.json)
Plan: [Implementation plan](../plans/2026-07-28-business-case-type-azure-blob-worm-s6b.md)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-azure-blob-worm-s6b
leading_issue: https://github.com/notariat8/NaC/issues/693
risk_gate: External Service
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S6B-01
  - AC-S6B-02
  - AC-S6B-03
  - AC-S6B-04
  - AC-S6B-05
  - AC-S6B-06
  - AC-S6B-07
validation_commands:
  - python3 -m unittest tests.test_immutable_evidence tests.test_azure_blob_worm tests.test_azure_blob_worm_contract
  - python3 scripts/validate_business_case_type_azure_blob_worm.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
```

## Goal And Offline Boundary

`AzureBlobWormJournal` implements the unchanged `WormJournalPort` for an
authoritative Azure Blob immutable-evidence copy published from on premises.
The slice contains only port planning and `FakeAzureBlobWormTransport`: no
HTTP, Azure, credential, permission, deployment, lock, or live-factory action.
S7 remains blocked.

## AC-S6B-01: Adapter Semantics

`commit(records, anchor, *, idempotency_key_sha256)` and
`readback(receipt_ref)` remain exactly compatible with S6a. Full readback
verifies canonical bytes, chain, anchor, metadata, CMK, policy, and the exact
bound blob version. Public failures are always
`AzureBlobWormError("Azure Blob WORM operation rejected")` without cause,
context, provider text, or plaintext identifiers.

## AC-S6B-02: Create And Idempotency

The only accepted key is the canonical S6a
`_publication_operation_key("worm-commit", chain_head_sha256)`. Every Put uses
`If-None-Match: *`.

The offline REST plan models Azure realistically:

1. HTTP `201` must provide raw `x-ms-version-id`, followed by GET with that
   exact raw `versionid`.
2. HTTP `412` must not assert a version. The adapter performs List Blob
   Versions and reads every candidate by raw `versionid`.
3. Exactly one fully matching version is required. Missing, ambiguous, or
   foreign versions block.
4. Public readback resolves the hashed receipt binding locally and passes only
   raw `version_id` to the transport, never a hash selector.

Post-create response loss and real same-blob concurrency produce at most one
create effect and never overwrite.

## AC-S6B-03: Policy And Retention Evidence

All potentially failing event timestamp, retention, overflow, and policy
calculations run before Put. A valid future S6a `occurred_at` does not define
the Azure retention origin. The fake sets `created_at` at create time and
computes `retention_until` from it. Invalid or overflowing retention creates
zero effects and retry remains safe.

The exact committed version must prove:

- `Locked`, rather than only a container default;
- at least `ceil(years * 365.25)`, therefore `3653` days for ten years from
  `created_at`;
- legal-hold capability derived from `container-policy-properties`, separate
  from active `legal_hold_active` state;
- dedicated encryption scope, `Microsoft.Keyvault`, and a hashed CMK reference.

## AC-S6B-04: Provider Drift And Redaction

For commit and readback the transport freshly reads the actual provider
context: tenant ID, subscription resource ID, and storage resource ID. Only
domain-separated hash bindings enter the object, metadata, and evidence. The
Bicep baseline emits neither plaintext IDs nor self-asserted hashes. The
expected `provider_context_binding_sha256` comes from an owner-approved,
commit- and hash-bound deployment attestation; the actual value comes from an
independent fresh Azure readback. Expected and actual values must not be
derived from the same readback.

Stale container metadata, subscription or resource drift, and tenant transfer
fail closed. No plaintext tenant, subscription, or resource ID appears in
redacted evidence or public errors.

## AC-S6B-05: Dedicated Bicep Baseline

The baseline uses `Microsoft.Storage/...@2023-05-01`, emits no invalid
`immutabilityPolicy.properties.state`, and claims no local compilation. CMK,
CMK UAMI, and writer UAMI are dedicated; no existing identity is broadened.

The writer data role contains exactly:

- `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action`;
- `Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read`.

A separate management-read role at storage-account scope contains exactly:

- `Microsoft.Storage/storageAccounts/blobServices/containers/read`;
- `Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/read`;
- `Microsoft.Storage/storageAccounts/encryptionScopes/read`.

Blob `write`, delete, Owner, and Contributor are excluded.

## AC-S6B-06: Zero Live And S7

Network, Azure, credential, tenant-write, and lock counters remain zero. No
live-factory wiring exists. Status remains
`S6B_AZURE_WORM_ADAPTER_READY_OFFLINE`; without a separate owner gate and
`Locked` readback, `BLOCKED_PENDING_S7_APPROVAL` remains binding.

## AC-S6B-07: Contracts, Tests, Review, And Lock Plan

Domain, verification, and separate irreversible-lock contracts describe the
slice in machine-readable form. The lock plan is offline only and binds exact
target, provider context, policy, API/operation, ETag, request hash, distinct
operator/approver references, and pre/post readback. Target drift, stale ETag,
and request-hash drift block; no live lock edge exists.

Central adoption remains an integration step and Track B does not overwrite
it. `az bicep`, `bicep`, and `npx bicep` are unavailable locally, so there is
no local compile claim. CI must complete pinned Bicep compilation before merge.

## Acceptance

```bash
python3 -m unittest tests.test_immutable_evidence tests.test_azure_blob_worm tests.test_azure_blob_worm_contract
python3 scripts/validate_business_case_type_azure_blob_worm.py
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
git diff --check
```
