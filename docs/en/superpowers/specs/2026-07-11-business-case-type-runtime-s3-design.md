# BusinessCaseType Runtime S3 Design

Status: in implementation; completion requires successful code and contract validation
Date: July 11, 2026
Scope: deterministic, viewer-independent offline runtime for `BusinessCaseTypeId`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-runtime-s3
leading_issue: https://github.com/notariat8/NaC/issues/612
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-11-business-case-type-runtime-s3.md
acceptance_ids:
  - AC-S3-01
  - AC-S3-02
  - AC-S3-03
  - AC-S3-04
  - AC-S3-05
  - AC-S3-06
validation_commands:
  - python3 -m unittest tests.test_business_case_type_runtime tests.test_business_case_type_cache tests.test_business_case_type_cli tests.test_business_case_type_id_contract tests.test_business_case_type_id_cli tests.test_business_case_type_id_schema_plan tests.test_notary_kg
  - python3 scripts/validate_business_case_type_runtime.py
  - python3 scripts/validate_notarial_business_case_inventory.py
  - python3 scripts/validate_notarial_process_ontology_contract.py
  - python3 scripts/nac.py kg business-case-type-get --help
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/validate_gantt_progress.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Purpose

S3 will implement the `business_case_type_get` domain read edge entirely
offline.
The runtime deterministically decides whether an exact `BusinessCaseTypeId` is
eligible for canonical assignment or whether a direct legacy alias may only
be resolved for a bounded read or migration purpose. Microsoft Graph,
authentication, credentials and tenant access belong to S4.

## Authoritative Catalog Snapshot

The runtime loads an immutable, repository-versioned snapshot. It contains
canonical IDs, direct aliases, `LifecycleStatus`, `Selectable`, contract
version and a `catalog_version` value. `catalog_version` is the SHA-256 over
canonically serialized IDs, alias rules and runtime lifecycle fields. The
inventory schema version and timestamps are not the catalog version.

The runtime lifecycle is independent. A planning value such as
`source_status="open"` must not silently produce `LifecycleStatus="active"` or
`Selectable=true`. Entries without explicit approval are not selectable for
new matters.

Loading fails closed for exact syntax, length, uniqueness, direct alias
targets, collisions, chains, cycles, self-targets and unknown targets. Input
is not trimmed, lowercased, Unicode-normalized or URL-decoded.

## Lookup Purposes And Results

The API distinguishes at least:

- `canonical_assignment`: only an exact canonical, active and selectable ID is
  allowed; aliases are invalid.
- `legacy_read`: exactly one direct alias may be resolved; the result is not
  selectable and requires audit.
- `migration`: exactly one direct alias may be resolved as explicit migration
  evidence and remains audit-required.

Results use the disjoint states `VALID`, `INVALID` and
`VALIDATION_UNAVAILABLE` with structured reason codes. Raw transport responses
are neither returned nor stored.

## Registry Validation

The read-only port returns every page of an exact ID lookup. The runtime then
requires:

1. exactly one row in total,
2. exact `BusinessCaseTypeId`,
3. exact `CatalogVersion`,
4. `LifecycleStatus == "active"`,
5. `Selectable is True` as a Boolean,
6. a non-empty row ETag,
7. selected registry metadata only.

Zero or multiple rows, paging failures, missing or incorrectly typed fields,
version drift and unknown status values never produce `VALID`.

## Cache State Machine

The registry cache uses key
`(site_id, BusinessCaseTypeId, CatalogVersion)`, an injected monotonic clock,
bounded capacity, thread protection and single-flight revalidation.

- Below 300 seconds, a positive entry is `FRESH`.
- At 300 seconds, synchronous revalidation is required. A mutation remains
  blocked on timeout or transport failure.
- Below 900 seconds, a read-only view may expose stale metadata only as
  `VALIDATION_UNAVAILABLE`; it must not derive `VALID` from it.
- At 900 seconds, the entry is `HARD_EXPIRED` and unusable.
- Deterministic negative results are held for no more than 30 seconds.
  Timeout, authentication, transport and 5xx failures are not negative-cached.
- `304 Not Modified` is valid only with a matching previous positive ETag.
- Catalog-version or unexpected ETag changes atomically invalidate the site's
  registry partition and increment its generation. Older in-flight requests
  must not repopulate the cache afterward.

The cache contains only ID, lifecycle, `Selectable`, `CatalogVersion`, ETag and
time values, never matter, person, document or raw Graph data.

## Viewer Isolation

Registry and viewer metadata use separate classes, entry types, storage maps,
locks, generations, transport ports and invalidation functions.
`business_case_type_get` for type validity neither imports nor reads a viewer
port. Outage, duplicates or drift in `Prozessregister` or BPMN metadata do not
change type validity.

## Offline Boundary

S3 provides fake or fixture transports only. It has no tenant, token,
certificate, Microsoft Graph or live HTTP option. The production Graph REST
v1.0 adapter, response headers/ETags and paging belong to S4.

## Acceptance Criteria

- **AC-S3-01:** Canonical IDs and direct known aliases resolve
  deterministically; unknown IDs, spelling variants, alias chains, cycles and
  retired/nonselectable entries fail closed.
- **AC-S3-02:** Exactly one registry row with the matching ID and
  `CatalogVersion` is required; zero rows, duplicates, timeout and version
  drift do not produce a valid type.
- **AC-S3-03:** The registry cache enforces revalidation, hard expiry, negative
  TTL and site-wide invalidation on ETag or version drift.
- **AC-S3-04:** The viewer cache is technically and semantically separate and
  is never read for type validity.
- **AC-S3-05:** ETag/Not-Modified behavior is tested deterministically; the
  cache contains no matter, document or person data.
- **AC-S3-06:** Central CLI, standalone validator, DE/EN documentation, strict
  gate and independent review pass without Graph, credential or tenant access.
## Non-Goals

- no Microsoft Graph adapter or MCP server,
- no SharePoint or Entra live action,
- no matter creation, correction or migration,
- no persistent cache,
- no viewer, BPMN or process-register dependency for type validity.
