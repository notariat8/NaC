# BusinessCaseType Runtime S3 Implementation Plan

**Spec:** [BusinessCaseType Runtime S3 Design](../specs/2026-07-11-business-case-type-runtime-s3-design.md)
**Leading Issue:** [GitHub #612](https://github.com/notariat8/NaC/issues/612)
**Delivery Mode:** Protected PR
**Risk Gate:** Privacy

## Goal

Implement viewer-independent `BusinessCaseTypeId` validity as a deterministic
Python runtime with fixture transport, separate caches, central CLI and an
executable verification contract. The plan ends before every Graph, Entra,
credential or tenant edge.

## Acceptance Mapping to Issue #612

- **AC-S3-01:** ID/alias resolution, variant and lifecycle blockers.
- **AC-S3-02:** registry cardinality, row shape, version and status.
- **AC-S3-03:** registry TTLs and site-wide invalidation.
- **AC-S3-04:** strict viewer isolation from type validity.
- **AC-S3-05:** ETag/Not-Modified behavior and data minimization.
- **AC-S3-06:** central CLI, documentation, validator, strict gate and review.

## Work Packages

- [ ] **WP1 – Governance and traceability:** connect spec, plan, ADR links,
  agent context and roadmap to `AC-S3-01` through `AC-S3-06`.
- [ ] **WP2 – Snapshot and catalog:** implement content-based
  `CatalogVersion`, explicit runtime lifecycle and fail-closed alias/ID
  invariants.
- [ ] **WP3 – Read port and registry validation:** implement a read-only
  Protocol, paged fixture results and complete row validation.
- [ ] **WP4 – Cache:** implement registry cache with 300/900/30-second
  boundaries, ETag, generation, single flight and monotonic clock plus a
  separate viewer cache.
- [ ] **WP5 – API and CLI:** provide `business_case_type_get` and
  `nac kg business-case-type-get` using fixture transport only.
- [ ] **WP6 – Contracts and verification:** integrate domain contract,
  verification contract, standalone validator, `nac contracts verify` and the
  strict gate.
- [ ] **WP7 – Tests:** cover positive and negative boundaries for IDs,
  aliases, paging, registry shape, TTL limits, 304, generations, concurrency,
  data minimization and viewer isolation.
- [ ] **WP8 – Completion:** review the full diff, run independent review, fix
  findings and prepare a Protected PR with green remote checks.

## Validation Order

1. focused runtime, cache, contract, CLI and regression tests,
2. S3, inventory and ontology validators,
3. CLI help and `nac contracts verify`,
4. spec traceability, language parity, links and Gantt,
5. `python3 scripts/nac.py doctor --profile strict`,
6. `git diff --check`, full `base...head` review and remote CI.

The concrete commands listed in the spec manifest are binding.

## Completion Rule

Board and ADR status remain `in progress` during implementation. S3 is marked
implemented only after `AC-S3-06`, the strict gate, independent review and
green Protected PR checks pass. S4 is a separate follow-up scope for Microsoft
Graph REST v1.0 and must not silently expand S3.
