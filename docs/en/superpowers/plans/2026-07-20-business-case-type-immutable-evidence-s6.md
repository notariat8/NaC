# BusinessCaseType Immutable Evidence S6a Implementation Plan

**Status:** offline implementation active; live mutations remain blocked
**Spec:** [BusinessCaseType Immutable Evidence S6a Design](../specs/2026-07-20-business-case-type-immutable-evidence-s6-design.md)
**Leading Issue:** [GitHub #687](https://github.com/notariat8/NaC/issues/687)
**Delivery Mode:** Protected PR
**Risk Gates:** Privacy, Human Approval, External Service
**Thresholds:** Network Calls = 0; Provider Calls = 0; Tenant Calls = 0; Tenant Writes = 0; Credential Reads = 0; Live Mutations = 0; Production WORM Claim = false

## Objective

S6a implements a redacted, deterministic evidence core for BusinessCaseType
mutations using synthetic in-memory adapters only. S6b provider adapters and
S7 live approval remain separate.

## Acceptance Mapping

- **AC-S6-01:** Exact phase order, contiguous sequence and SHA-256 chain.
- **AC-S6-02:** Persisted intent, outcome/readback, operation and delivery
  keys, plus persisted tenant, principal-key and ordered event-hash-sequence
  bindings.
- **AC-S6-03:** Correlation, actor, operator and approver bind to the same
  tenant; actor, operator and approver use the same principal-key binding
  hash. Mismatches fail closed.
- **AC-S6-04:** Port contracts require deterministic chain-head-bound
  idempotency keys for anchor/WORM, write-ahead progress and crash-safe resume.
- **AC-S6-05:** At least ten years of retention and legal-hold metadata.
- **AC-S6-06:** Principal-key-bound pre-claim authorization and event-hash
  prefix are atomically consumed into a complete publication sequence;
  completed replay checks chain length and provider bindings.
- **AC-S6-07:** Exact offline/live status and all six zero counters.
- **AC-S6-08:** Negative gates, including external
  `ImmutableEvidenceError`, fail closed without provider details.

## Work Packages

- [x] **WP1 – Scope:** inspect the S3 catalog and runtime as implementation
  sources; add no live functions.
- [x] **WP2 – Envelope:** synchronize 20 canonical slugs, the real
  CatalogVersion, `delivery_key_sha256`, tenant-bound HMAC ETags and every
  persisted principal/security binding.
- [x] **WP3 – Ports:** document final `ReconciliationStorePort`
  operations, optional `require` bindings, persisted pre-claim authorization
  and ordered event-hash prefix, their atomic claim consumption into a complete
  sequence, publication progress, dual-control resume and deterministic
  anchor/WORM idempotency.
- [x] **WP4 – Completion:** validate completed result and progress against the
  current chain length, acknowledgements, head and anchor/signature/WORM
  bindings.
- [x] **WP5 – Error boundary:** reduce every external port error, including
  `ImmutableEvidenceError`, to fixed redacted messages.
- [x] **WP6 – Contract/docs:** synchronize contract, validator and DE/EN
  spec/plan.
- [x] **WP7 – Completion:** focused validator, contract, parity and
  traceability checks plus diff review.

## Excluded

- production adapters or new live functions,
- Graph, SharePoint, Entra or Azure calls,
- live schema apply, backfill, cutover, rollback or cleanup,
- any claim of audit-proof production storage.

## Validation

1. S6 standalone validator and focused contract test,
2. `nac contracts verify`,
3. language parity and spec traceability,
4. `git diff --check` limited to the six S6 files.
