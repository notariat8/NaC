# BusinessCaseType Graph Read Edge S4 Design

Status: runtime implemented offline in PR #617; governance synchronization remains open in the S5 PR until remote CI is green; S4b writes remain open
Date: July 11, 2026
Scope: offline-planned Microsoft Graph v1.0 read edge between `nac_m365_graph` and the existing `notary_kg` domain port

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-graph-read-edge-s4
leading_issue: https://github.com/notariat8/NaC/issues/616
risk_gate: External Service
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-11-business-case-type-graph-read-edge-s4.md
acceptance_ids:
  - AC-S4-01
  - AC-S4-02
  - AC-S4-03
  - AC-S4-04
  - AC-S4-05
  - AC-S4-06
  - AC-S4-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_graph_read_edge tests.test_business_case_type_graph_read_edge_cli tests.test_business_case_type_graph_read_edge_contract
  - python3 scripts/validate_business_case_type_graph_read_edge.py
  - python3 scripts/nac.py m365 teams-sharepoint business-case-type-read-plan --help
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Purpose and Layer Boundary

S4 adds exactly one adapter under `src/nac_m365_graph` to the viewer-independent
`BusinessCaseTypeRegistryReadPort` implemented in S3. The adapter reduces
Microsoft Graph responses to `BusinessCaseTypeRegistryRow` and returns only
`RegistryFetchResult` to `notary_kg`. The domain validity decision, registry
cache, and its state machine remain owned by S3 and are not changed by this
slice.

This slice is GET-only and planned offline. It makes no live request, loads no
credentials, and changes neither Entra nor SharePoint. S4b writes for
`case_create`, correction, and backfill are a separate follow-up scope.

## Bound Request

An adapter instance is immutably bound to:

- Graph base `https://graph.microsoft.com/v1.0`,
- exactly one approved `site_id`,
- exactly one approved `list_id` for `Vorgangsartenregister`,
- exactly one operation from `case_create_validation`,
  `matter_type_correction_validation`, `backfill_validation`, or
  `optional_process_read`,
- one role allowed for that operation,
- application permission exactly `Sites.Selected` and an existing read grant
  for the site.

Site, list, operation, role, and permission are checked before an HTTP request
is built or handed to a transport. A mismatch fails closed without transport.
`Sites.Read.All`, `Sites.ReadWrite.All`, `Sites.Manage.All`,
`Files.Read.All`, delegated permissions, and schema or provisioning rights are
not allowed for this edge.

## Graph Request and Data Minimization

The adapter may plan only `GET` against the bound collection
`/sites/{site-id}/lists/{list-id}/items` under Graph REST v1.0. The initial
request filters by the exact `BusinessCaseTypeId` and `CatalogVersion` and selects exactly `id` and
`eTag` at item level. It expands exactly `BusinessCaseTypeId`,
`LifecycleStatus`, `Selectable`, and `CatalogVersion` from `fields`. No other
properties are copied into domain objects, persisted, or emitted as evidence.

Viewer, process, matter, document, and person fields do not affect type
validity. `optional_process_read` is only a bound operation permission for a
later, separate process read; it does not add process or viewer fields to this
registry request.

## Complete Paging

A result is complete only at a validated collection end. Before every
follow-up GET, each `@odata.nextLink` is parsed canonically and must continue
to address:

1. HTTPS and host `graph.microsoft.com`,
2. base `/v1.0`,
3. the same bound site and list,
4. the same items collection and field projection,
5. the identical `BusinessCaseTypeId` and `CatalogVersion` filters.

Redirects, relative or user-controlled hosts, Graph beta, different sites or
lists, and changed projections are forbidden. Visited canonical next links
are tracked. A loop, invalid payload, or breach of the fixed page or item
limit never returns partial `OK`; it returns a redacted `UNAVAILABLE` with
`pages_complete=false`. Each HTTP response is bounded to 1 MiB before JSON parsing; exceeding that limit also fails closed.

## ETag Semantics

The adapter always reads the filtered collection completely. Only after a
validated end may it locally compare the `eTag` of exactly one fully typed,
exactly matching row with the prior positive ETag supplied by S3. Equality
returns `RegistryFetchResult.NOT_MODIFIED`; a different ETag returns the new
row in a complete `OK` result.

A row ETag is never sent as a collection `If-None-Match` header. S4 therefore
adds neither general HTTP 304 handling nor an inferred collection-not-modified
state without a stable item endpoint. Zero, multiple, or incomplete rows can
never produce `NOT_MODIFIED`.

## Redacted Failures and Evidence

The Graph edge emits only the fixed codes already allowed by the domain port:
`transport_authentication_failed`, `transport_authorization_failed`,
`transport_rate_limited`, `transport_timeout`, and `transport_unavailable`.
Unknown HTTP statuses, invalid payloads, paging violations, loops, and limit
breaches reduce to `transport_unavailable`.
`fixture_transport_unavailable` remains exclusive to the S3 fixture path.

Exceptions, results, logs, and evidence contain no token, concrete Graph path,
site/list/item ID, Graph body, matter value, or credential metadata. Only
fixed reason codes, counters within the limits, Boolean gate results, contract
version, and redacted correlation references are allowed.

## Offline CLI

In this implementation slice, the central `nac` CLI receives
`nac m365 teams-sharepoint business-case-type-read-plan`. It produces only a redacted offline
plan containing method, Graph version, logical resource binding, selected
field names, limits, and gate results. The command accepts or reads no tokens,
certificates, or secret files, instantiates no live Graph client, and performs
neither HTTP nor DNS.

## Acceptance Criteria

- **AC-S4-01:** The adapter generates only Graph REST v1.0 GETs for the bound site/list and selects exactly id, eTag, BusinessCaseTypeId, LifecycleStatus, Selectable, and CatalogVersion.
- **AC-S4-02:** Paging is complete only after a validated end; foreign hosts/bases/sites/lists, loops, invalid payloads, and page/item limit breaches never produce a valid type.
- **AC-S4-03:** After a complete read, an identical row ETag is mapped locally to NOT_MODIFIED; different ETags return the new row. A row ETag is never misused as collection If-None-Match.
- **AC-S4-04:** An incorrect site, list, operation, role, or runtime permission is blocked before transport; the contract allows only Sites.Selected and no schema/provisioning rights.
- **AC-S4-05:** Graph responses are strictly typed and reduced to the registry fields; viewer, process, matter, document, and person fields do not affect type validity.
- **AC-S4-06:** HTTP/transport errors are mapped to fixed redacted reason codes; tokens, paths, IDs, Graph bodies, and matter values appear in neither results nor exceptions/evidence.
- **AC-S4-07:** The central CLI, domain/verification contract, standalone validator, fake Graph tests, DE/EN documentation, strict gate, and independent base...head review pass.

## Non-Goals

- no change to the S3 runtime, its domain decisions, or caches,
- no live Graph, tenant, credential, or Entra action,
- no Graph, SharePoint, MCP, schema, or provisioning writes,
- no S4b write plan and no execution of `case_create`, correction, or backfill,
- no SharePoint REST, PnP, Graph SDK, or Graph beta,
- no process-register, BPMN, or viewer dependency for type validity.
