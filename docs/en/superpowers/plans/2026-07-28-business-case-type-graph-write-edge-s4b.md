# BusinessCaseType Graph Write Edge S4b Implementation Plan

**Status:** implemented offline; protected-PR integration pending
**Spec:** [BusinessCaseType Graph Write Edge S4b Design](../specs/2026-07-28-business-case-type-graph-write-edge-s4b-design.md)
**Leading Issue:** [GitHub #694](https://github.com/notariat8/NaC/issues/694)
**Delivery Mode:** Protected PR
**Risk Gates:** Privacy, Human Approval, External Service
**Thresholds:** Live Graph Calls = 0; Tenant Writes = 0; Credential Reads = 0; Live Factories = 0

## Goal

A dedicated offline S4b edge plans and orchestrates five bounded
BusinessCaseType write operations with a separate write identity, create
deduplication, ETag concurrency, S5 hash binding, and injected
evidence/reconciliation hooks.

## Plan Review Fix

The initial plan represented create idempotency only through a local hash. The
review required an additional GET against the already unique SharePoint
fields `NacCaseId` and `NacTaskId`; ambiguity becomes sticky reconciliation.
It also established that a successful readback after an uncertain write does
not close reconciliation automatically. Contract and negative tests bind
these corrections. The safety fix pass adds complete canonical execute-time revalidation, `$top=2` with `nextLink` as ambiguity, strict actual-field readbacks, durably acknowledged process-wide reconciliation, and fixed redacted
transport errors. The renewed fix pass replaces plain `clear` as a release
condition with persistent intent generations plus closure proof and binds PATCH
5xx readback exclusively to `plan.mutation.item_id`. The final safety pass makes persisted `closed` terminal even when downstream
closure confirmation fails and binds every target hash to workspace, site, and
both list IDs regardless of the active operation.

## Work Packages

- [x] **WP1 – Tests first:** synthetic fixtures and red tests for five
  operations, binding drift, legacy gate, S5 hash, dedupe, ETag, 412, and
  reconciliation, paging, 409/412, plan manipulation, restart fail-closed, and
  error redaction, a fresh hook instance over a shared store, a physically
  closed intent with lost confirmation, inactive-list drift in both directions,
  and a foreign PATCH 5xx response ID.
- [x] **WP2 – Domain:** closed `BusinessCaseTypeMutation` with exact field
  sets and canonical S5 verification.
- [x] **WP3 – Plan:** immutable workspace/site/list/role/purpose/approval/
  identity binding, target hash over workspace, site, and both list IDs,
  canonical plan hash, complete execute-time revalidation, and exact Graph v1.0
  targets.
- [x] **WP4 – Edge:** dedupe/freshness, intent, one write, outcome, readback,
  strict readback, and durably acknowledged process-wide sticky reconciliation
  with persistent intent generation, terminal monotone closure, and closure proof
  through injected ports.
- [x] **WP5 – Contract:** S4b domain/verification contracts, standalone
  validator, and DE/EN spec/plan.
- [x] **WP6 – Review/Fix:** full scope diff, focused tests, validator,
  `compileall`, traceability, language parity, and link checks; all safety
  findings fixed.
- [ ] **WP7 – Integration:** the lead agent updates shared index, quality
  gate, and CLI surfaces and runs protected-PR gates.

## Not Included

- Live factory, HTTP client, or credential loader,
- permission, schema, or tenant write,
- change to the BFF UAMI,
- shared CLI, README, index, GANTT, agent-context, or S6a files,
- automatic reconciliation closure or production S6 composition.

## Validation

1. focused unit and contract tests,
2. S4b standalone validator and `compileall`,
3. spec traceability, language parity, and document links,
4. scope and whitespace diff,
5. independent implementation review before handoff.
