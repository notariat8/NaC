# BusinessCaseType Graph Write Composition S4c Implementation Plan

**Issue:** [#698](https://github.com/notariat8/NaC/issues/698)
**Spec:** [S4c Design](../specs/2026-07-29-business-case-type-graph-write-composition-s4c-design.md)
**Status:** Implemented offline; live write owner-gated

## Work Packages

- [x] **WP1 – Contracts:** S4c domain and verification contracts, validator and
  spec traceability for `AC-S4C-01` through `AC-S4C-08`.
- [x] **WP2 – State:** SQLite adapter with atomic state/event commit,
  full transition matrix, two-connection CAS, authorization-run binding and a
  local POSIX process-restart envelope.
- [x] **WP3 – Transport:** Graph v1.0 adapter with injected token and HTTP ports,
  redirect/host/method/body limits and no automatic retry.
- [x] **WP4 – Composition:** pure DI root without environment, credential or
  live factory.
- [x] **WP5 – Offline Smoke:** temporary state and fake HTTP for all five
  operations with zero socket/DNS, external credential, live Graph and tenant
  activity; synthetic token-provider calls are reported separately.
- [x] **WP6 – Crash/Negative Tests:** restart windows, corruption, CAS
  conflicts, busy/timeout, pre-transport blocks without token-provider calls
  and redacted provider failures.
- [x] **WP7 – Docs/Context:** synchronize DE/EN CLI, architecture, contract
  indexes, agent context and roadmap.
- [x] **WP8 – Completion:** focused tests, validator, contracts, compileall,
  spec traceability, language parity, links, strict gate and independent review.

## Order

1. Independently review the plan and close findings.
2. Implement state and transport in parallel with disjoint write sets.
3. Integrate composition, smoke and CLI in the main run.
4. Perform a full `base...head` review.
5. Merge only after green local and remote CI.

Live factory, real credentials and tenant writes remain separately owner-gated
after S4c.
