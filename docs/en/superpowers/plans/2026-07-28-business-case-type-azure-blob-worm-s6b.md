# BusinessCaseType Azure Blob WORM S6b Implementation Plan

Status: `S6B_AZURE_WORM_ADAPTER_READY_OFFLINE`
Live status: `BLOCKED_PENDING_S7_APPROVAL`
Leading issue: [#693](https://github.com/notariat8/NaC/issues/693)
Spec: [BusinessCaseType Azure Blob WORM S6b Design](../specs/2026-07-28-business-case-type-azure-blob-worm-s6b-design.md)
Domain contract: [business-case-type-azure-blob-worm-s6b.contract.json](../../../../../workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json)
Lock contract: [azure-blob-worm-irreversible-lock-s6b.contract.json](../../../../../workflows/contracts/azure-blob-worm-irreversible-lock-s6b.contract.json)

## Plan -> Review -> Fix

1. **Tests first:** capture pre-Put timestamp, retention and overflow negatives,
   future S6a timestamps, response loss, real same-blob concurrency, fresh
   provider readback, and 201/412 version discovery.
2. **AC-S6B-01:** preserve unchanged `WormJournalPort` signatures and complete
   canonical readback.
3. **AC-S6B-02:** accept only the S6a `worm-commit` key; bind HTTP `201` to raw `version_id` from
   `x-ms-version-id`; on `412`, use List Blob Versions and GET with raw
   `versionid`. The transport port has no hash selector.
4. **AC-S6B-03:** perform every potentially failing calculation before Put and
   model fake `retention_until` from `created_at`. The exact version must prove
   `Locked`, at least `3653` days, legal-hold capability, and CMK.
5. **AC-S6B-04:** freshly read and domain-hash tenant, subscription, and storage
   resource context; redact and block stale metadata and tenant transfer. The
   sources are `subscription().tenantId`, `subscription().id`, and
   `resourceId('Microsoft.Storage/storageAccounts', storageAccountName)`.
6. **AC-S6B-05:** build the dedicated Bicep baseline with blob `add/action` plus
   `read` and separate management reads for container, immutability policy,
   and encryption scope. Exclude blob `write`, delete, Owner, Contributor, and
   broadening of an existing identity.
7. **AC-S6B-06:** network, Azure, credentials, tenant writes, live lock, and
   live factory remain zero; S7 remains `BLOCKED_PENDING_S7_APPROVAL`.
8. **AC-S6B-07:** align domain, verification and lock contracts, paired DE/EN
   documents, validator, and focused tests. The pure lock plan binds target,
   provider context, policy, ETag, request hash, operator/approver, and pre/post
   readback without executing anything live.
9. **Review:** independently inspect missing, ambiguous and foreign versions,
   malformed `201`/`412`, overflow before Put, provider transfer, RBAC
   negatives, redaction, and target/ETag/request-hash drift.
10. **Fix and acceptance:** rerun focused tests, validator, spec traceability,
    parity, links, and diff checks.

## Integration And Compile Step

Track B does not edit or revert central index, architecture, CLI, or quality
gate files. Existing central adoption is preserved. Pinned Bicep compilation in
CI remains mandatory before merge:

```bash
az bicep build --file deploy/runtime/azure/immutable-evidence/main.bicep --stdout
```

`az bicep`, `bicep`, and `npx bicep` are unavailable locally. No local compile
success is claimed.

## Irreversible Lock

S6b performs no lock. A later owner-gated S7 step must freshly read the exact
target/provider context and policy, verify `Unlocked`, at least `3653` days,
and ETag, approve the canonical request hash, then read back the same context
with a new ETag and `Locked`. Any target, ETag, or request-hash deviation
blocks.

## Focused Validation

```bash
python3 -m unittest tests.test_immutable_evidence tests.test_azure_blob_worm tests.test_azure_blob_worm_contract
python3 scripts/validate_business_case_type_azure_blob_worm.py
python3 scripts/validate_spec_traceability.py
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
git diff --check
```
