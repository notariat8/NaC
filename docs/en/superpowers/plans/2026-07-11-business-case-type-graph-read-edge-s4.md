# BusinessCaseType Graph Read Edge S4 Implementation Plan

**Status:** in progress; runtime implemented on the branch; WP1-WP8 complete; WP9 open until gates, Protected PR, and remote CI

**Spec:** [BusinessCaseType Graph Read Edge S4 Design](../specs/2026-07-11-business-case-type-graph-read-edge-s4-design.md)
**Leading Issue:** [GitHub #616](https://github.com/notariat8/NaC/issues/616)
**Delivery Mode:** Protected PR
**Risk Gate:** External Service; closed in S4, `allowed_live_graph_calls=0`

## Goal

Build the GET-only Graph v1.0 adapter from `nac_m365_graph` to the existing
`notary_kg` domain port in this implementation slice. The implemented branch
defines request binding, paging, local ETag semantics, redaction, offline CLI,
and evidence; runtime code is implemented on the branch. S3 remains unchanged and S4b
writes remain out of scope.

## Acceptance Mapping to Issue #616

- **AC-S4-01:** The adapter generates only Graph REST v1.0 GETs for the bound site/list and selects exactly id, eTag, BusinessCaseTypeId, LifecycleStatus, Selectable, and CatalogVersion.
- **AC-S4-02:** Paging is complete only after a validated end; foreign hosts/bases/sites/lists, loops, invalid payloads, and page/item limit breaches never produce a valid type.
- **AC-S4-03:** After a complete read, an identical row ETag is mapped locally to NOT_MODIFIED; different ETags return the new row. A row ETag is never misused as collection If-None-Match.
- **AC-S4-04:** An incorrect site, list, operation, role, or runtime permission is blocked before transport; the contract allows only Sites.Selected and no schema/provisioning rights.
- **AC-S4-05:** Graph responses are strictly typed and reduced to the registry fields; viewer, process, matter, document, and person fields do not affect type validity.
- **AC-S4-06:** HTTP/transport errors are mapped to fixed redacted reason codes; tokens, paths, IDs, Graph bodies, and matter values appear in neither results nor exceptions/evidence.
- **AC-S4-07:** The central CLI, domain/verification contract, standalone validator, fake Graph tests, DE/EN documentation, strict gate, and independent base...head review pass.

## Work Packages for This Implementation Slice

- [x] **WP1 – Adapter boundary:** implement an adapter only under
  `src/nac_m365_graph` that satisfies the unchanged
  `BusinessCaseTypeRegistryReadPort` from `notary_kg` and returns only
  `RegistryFetchResult`.
- [x] **WP2 – Scope gate:** check immutable site/list binding, operation/role
  matrix, `Sites.Selected`, and the existing site read grant before every
  transport; block all broader or provisioning-related permissions.
- [x] **WP3 – Request plan:** generate only Graph REST v1.0 `GET` for the bound
  items collection with the exact filter and exactly six selected item and
  registry fields.
- [x] **WP4 – Paging:** structurally validate next links for HTTPS, host, v1.0
  base, site, list, collection, projection, and identical BusinessCaseTypeId and CatalogVersion filters; enforce a complete end, loop
  detection, and fixed page/item limits fail closed.
- [x] **WP5 – Parsing and ETag:** strictly type every page, discard foreign
  fields, and locally check one matching row for ETag equality only after a
  complete collection read; set no collection `If-None-Match` header.
- [x] **WP6 – Redaction:** reduce HTTP/transport failures to the fixed domain
  allowlist and ensure results, exceptions, logs, and evidence carry no
  tokens, paths, IDs, bodies, or matter values.
- [x] **WP7 – Offline CLI:** implement the central
  `nac m365 teams-sharepoint business-case-type-read-plan` command as a redacted planner with
  no credentials, HTTP, DNS, or live client.
- [x] **WP8 – Verification:** integrate the domain/verification contract and
  standalone validator; add fake Graph tests for all positive and negative
  paging, scope, typing, redaction, and ETag boundaries.
- [ ] **WP9 – Completion:** synchronize DE/EN documentation and agent context
  within the then-approved scope, run the strict gate, independently review
  the complete `base...head` diff, fix findings, and prepare a Protected PR
  with green remote checks.

## Mandatory Negative Cases

Fake Graph tests block at least an incorrect method or Graph version, mismatched
site/list/operation/role/permission, missing site read grant, foreign next-link
host or base, site/list or filter changes, redirect, relative URL, paging loop,
incomplete end, invalid payload, incorrect field types, zero/multiple rows,
and page/item limit breaches. A partial read may produce neither `OK`,
`NOT_MODIFIED`, nor a valid type.

The ETag tests additionally prove that the complete read precedes the local
comparison, that only one exactly matching row can produce `NOT_MODIFIED`, and
that no request carries a row ETag as collection `If-None-Match`.

## Validation Order

1. focused fake Graph, adapter, and CLI tests,
2. standalone S4 validator and `nac contracts verify`,
3. CLI help and offline/no-credential/no-HTTP evidence,
4. spec traceability, language parity, and links,
5. `python3 scripts/nac.py doctor --profile strict`,
6. `git diff --check`, complete `base...head` review, and remote CI.

The concrete commands are binding in the spec traceability manifest. All listed planning, runtime, contract, and CLI checks run in this
implementation slice.

## Completion Rule

S4 is implemented only after all seven ACs pass, the strict gate succeeds, an
independent review is clear, and the Protected PR checks are green. This
implemented branch state opens neither External Service nor Human Approval and allows
exactly zero live Graph calls. S4b remains a separate issue for later writes;
S3 is not silently extended.
