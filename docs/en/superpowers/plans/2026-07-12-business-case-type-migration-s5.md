# BusinessCaseType Migration S5 Implementation Plan

**Status:** implemented offline on the branch; WP1-WP8 complete; WP9 open until review, strict gate, and Protected PR
**Spec:** [BusinessCaseType Migration S5 Design](../specs/2026-07-12-business-case-type-migration-s5-design.md)
**Leading Issue:** [GitHub #618](https://github.com/notariat8/NaC/issues/618)
**Delivery Mode:** Protected PR
**Risk Gate:** Privacy
**Review Gates:** Privacy, External Service and Human Approval closed
**Thresholds:** Allowed live calls = 0; Allowed tenant writes = 0

## Goal

Implement complete S5 migration logic as a deterministic offline runtime with
a synthetic bundle, persistent local quarantine, central CLI and executable
contracts. The plan ends before every Microsoft Graph, tenant, schema,
backfill, cutover, rollback or cleanup action.

## Acceptance Mapping

- **AC-S5-01:** seven disjoint inventory classes and fail-closed mapping.
- **AC-S5-02:** canonically hashed manifest and snapshot binding.
- **AC-S5-03:** idempotent `VorgangstypId` plan with ETag and quarantine.
- **AC-S5-04:** two stable final scans and strict cutover readiness.
- **AC-S5-05:** deterministic pinned N/N-1 profile evaluation without claiming runtime execution.
- **AC-S5-06:** fixed rollback ordering and blocked forward recovery.
- **AC-S5-07:** CLI, contracts, validator, tests, docs, gates and review.

## Work Packages

- [x] **WP1 - Prepare governance synchronization:** synchronize the S4
  runtime implemented in PR #617 across both S4 contracts, standalone validator,
  DE/EN spec and plan, ADR, agent context, roadmap and Gantts; register S4 and
  S5 in `contracts validate/verify`. S4 WP9 and Issue #616 remain open until
  this Protected PR is merged with green remote CI.
- [x] **WP2 - Domain model and classification:** implement bundle types, exact
  four-value baseline, separate versioned legacy-Choice mapping, disjoint
  decision table, canonical hashes and page boundaries.
- [x] **WP3 - Backfill plan and quarantine:** implement fixed ordering and page
  size, idempotent `VorgangstypId` operations, ETag binding and crash-safe
  content-addressed quarantine without a close/delete path.
- [x] **WP4 - Manifest and snapshots:** implement matter, registry and optional
  process-register snapshots including `not_provisioned`, row ETags, nullable
  BPMN links, Git HEAD and version bindings.
- [x] **WP5 - Final scans, profile evaluation and recovery:** implement two
  independently captured scan page sets, complete manifest binding, the
  900-second stability rule, local N/N-1 profile evaluation, separately pinned
  candidate profiles, six-step rollback with later mandatory executable N-1
  validation, and S6/S7-blocked forward recovery.
- [x] **WP6 - CLI and fixtures:** integrate the central
  `business-case-type-migration-dry-run` entry point and fixtures for all
  seven classes, clean cutover, process-register `present`/
  `not_provisioned`, paging drift, replay and quarantine retry/conflict.
- [x] **WP7 - Contracts and verification:** add domain/verification contract,
  standalone validator, both contract READMEs, `contracts validate/verify`,
  agent verification-contract, decision and invariant indexes, escaped-newline rejection in the traceability validator, strict gate and
  DE/EN quality-gate documentation.
- [x] **WP8 - Tests:** cover the decision table, baseline/mapping drift, hash
  stability, page order/boundaries/duplicates, idempotency, quarantine crash
  reconciliation, ETag conflicts, scan timing, N/N-1 cases, rollback order,
  path boundaries, linked/detached Git-HEAD resolution, output atomicity, redaction and no-live behavior.
- [ ] **WP9 - Completion:** review the complete `base...head` diff, run
  independent security/governance review, fix findings and prepare a Protected
  PR with green remote checks.

## Parallelization

After plan approval, three disjoint streams run in parallel:

1. domain classification, mapping and backfill plan,
2. snapshots, quarantine, scans, replay and recovery,
3. contracts, CLI, fixtures, validator and governance integration.

The primary run integrates the streams, resolves overlaps in
`src/nac_cli/cli.py`, `scripts/quality_gate.py` and indexes, and runs full
validation.

## Validation Order

1. focused S5 domain, CLI and contract tests,
2. S5 standalone validator and existing S3/S4 regression tests,
3. CLI help and `nac contracts verify`,
4. spec traceability, language parity, links, Gantt and agent context,
5. full strict gate,
6. `git diff --check`, complete `base...head` reviews and remote CI.

## Completion Rule

S5 is implemented only after all seven ACs, local and remote validation,
independent reviews and Protected PR checks pass. Live mutations remain
blocked by S6 and S7 even after S5 completes.
