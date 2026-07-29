# BusinessCaseType Graph Write Edge S4b Design

Status: `S4B_OFFLINE_ONLY`; production composition remains out of scope
Date: July 28, 2026
Scope: bounded Graph write planning and synthetic fake-Graph execution

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-graph-write-edge-s4b
leading_issue: https://github.com/notariat8/NaC/issues/694
risk_gate: Privacy
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4B-01
  - AC-S4B-02
  - AC-S4B-03
  - AC-S4B-04
  - AC-S4B-05
  - AC-S4B-06
  - AC-S4B-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_graph_write_edge tests.test_business_case_type_graph_write_edge_contract tests.test_business_case_type_graph_write_edge_cli tests.test_business_case_type_graph_write_edge_graph_contract tests.test_business_case_type_graph_write_edge_reconciliation tests.test_business_case_type_graph_write_edge_schema
  - python3 scripts/validate_business_case_type_graph_write_edge.py
  - python3 -m compileall -q src/notary_kg/business_case_type_mutation.py src/nac_m365_graph/business_case_type_write_plan.py src/nac_m365_graph/business_case_type_write_edge.py src/nac_m365_graph/business_case_type_write_dry_run.py scripts/validate_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge_contract.py tests/test_business_case_type_graph_write_edge_cli.py tests/test_business_case_type_graph_write_edge_graph_contract.py tests/test_business_case_type_graph_write_edge_reconciliation.py tests/test_business_case_type_graph_write_edge_schema.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
```

## Purpose And Boundary

S4b adds a dedicated `BusinessCaseTypeMutation` and a port-injected Graph
write edge for `case_create`, `case_status_update`, `task_create`,
`task_update`, and `business_case_type_backfill`. The
[domain contract](../../../../workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json)
is the normative boundary.

The slice contains no live factory, HTTP client, credentials,
environment/token/certificate reads, or tenant write. Transport and evidence
are protocols; tests use synthetic in-memory fakes only.

## Exact Operations

| Operation | Method | List | Fields |
| --- | --- | --- | --- |
| `case_create` | `POST` | `Akten` | `NacCaseId`, `Aktenzeichen`, `Vorgangstyp`, `VorgangstypId`, `Status`, `NotarTeam`, `Vertraulichkeitsstufe`, `NacWorkflowVersion`, `KgVersion` |
| `case_status_update` | `PATCH` | `Akten` | `Status` only |
| `task_create` | `POST` | `AufgabenFristen` | `NacTaskId`, `NacCaseId`, `BpmnStepCode`, `Status`, `RequiresNotaryApproval`, optional `DueDate` |
| `task_update` | `PATCH` | `AufgabenFristen` | a non-empty subset of `Status`, `DueDate`, `RequiresNotaryApproval`, `BlockedReason` |
| `business_case_type_backfill` | `PATCH` | `Akten` | `VorgangstypId` only |

All field values are validated against the production SharePoint schema before
planning. Choice values must be members of their closed choice sets,
`RequiresNotaryApproval` is the only Boolean field, and `DueDate` must be a
timezone-aware ISO timestamp. In particular, `bool` must not pass as an
integer or text value for other field types.

All targets are exactly below
`https://graph.microsoft.com/v1.0/sites/{site-id}/lists/{list-id}/items`.
Beta, Graph SDK, SharePoint REST, and PnP are forbidden.

While `Akten.Vorgangstyp` remains required, `case_create` accepts only the four
legacy-mappable types `immobilienkaufvertrag`,
`unterschriftsbeglaubigung`, `online-gmbh-gruendung`, and
`handelsregisteranmeldung`. `VorgangstypId` must equal that value exactly.

## Binding And Identities

A planner is immutably bound to one workspace, site, both lists, and two
different principal references. Runtime context must repeat the exact site,
list, role, purpose, approved operation, and approval. Any drift blocks before
transport. The target-binding hash always includes workspace, site, Akten list
ID, and AufgabenFristen list ID; drift in the inactive list also blocks. The builder deeply freezes mutation and requests and binds the full
plan to a canonical SHA-256. Before every execution, mutation, S5 hashes,
target, list, URLs, method, fields, authorization, approval, and dedupe/
freshness requests are reconstructed against the bound builder; any
manipulation blocks without transport.

The future write identity is contract-only: `Sites.Selected` with site grant
`write`. The existing BFF UAMI remains unchanged at `Sites.Selected` with site
grant `read`. Both identities must differ. This slice grants no permission and
creates no credential.

## Idempotency And Concurrency

Before intent, `case_create` performs a GET for unique `NacCaseId`;
`task_create` does the same for `NacTaskId`. The dedupe GET uses only the
documented query options `expand` and `$filter`; top-level `$select` and
`$top` are not sent. The local parser accepts at most two matches. Any
`@odata.nextLink` is ambiguous and requires reconciliation without POST. Zero
matches permit one POST attempt. An exact match triggers a fresh GET of the
concrete item after the intent has been durably opened. Only its bound item ID,
non-empty ETag, and exact fields return `DEDUPLICATED` without POST. Multiple
matches, payload drift, or a failed fresh readback create sticky
reconciliation. For HTTP 409, the same dedupe and concrete-item readback
decides without a POST retry.

Every PATCH freshly reads the target item with mutation fields only. Only an ETag exactly matching the
expected ETag is used as `If-Match`. There is at most one PATCH attempt. HTTP
412 is never retried. Its readback may return `PRECONDITION_FAILED` or
`PRECONDITION_FAILED_ALREADY_APPLIED` only from HTTP 200, the exact bound item
ID, a non-empty ETag, valid response shape, and actual mutation fields. A wrong
status or shape requires reconciliation and never emits false
`verified_not_applied` evidence. Other negative provider responses likewise use
strict readback to distinguish `WRITE_REJECTED`,
`WRITE_REJECTED_STATE_ALREADY_APPLIED`, and reconciliation. For PATCH 5xx,
the readback item ID always comes from `plan.mutation.item_id`; a foreign `id`
in the response body is ignored and never enters evidence. Only POST may use a
valid response item ID for readback.

## S5 Hash Binding

Backfill accepts only an S5 single operation. The edge recomputes the S5
idempotency key from manifest hash, record-ref hash, target
`BusinessCaseTypeId`, and current ETag. It also verifies the canonical SHA-256
of the full S5 operation containing `record_ref_hash`, `field`, `value`,
`if_match`, and `idempotency_key`. Only then may it plan a
`VorgangstypId` PATCH.

## Evidence And Reconciliation

The evidence hook and its authoritative process-wide persistent state store
are injected. For every execution key composed of `target_binding_hash` and
`mutation_id`, the store tracks `reconciliation_state`, `intent_state`,
`intent_generation`, and `closed_generation`. Mutation-ID-only lookup is
forbidden. Before write, the edge must read back the atomically opened next
intent generation as `open`. Only `clear + absent` or a previously verified
`retryable` state may start. `closed` is terminal for that execution key.

Normal order is exactly `intent -> write -> outcome -> readback`. Only an
atomically acknowledged verified readback may close the same intent generation
with `closed_generation == intent_generation`. An uncertain transport result,
provider 5xx, missing create item, failed outcome hook, or unverified readback
leaves the intent open; evidence order is then
`intent -> outcome -> reconciliation_required -> readback`.

If reconciliation-marker acknowledgement fails, the previously durable intent
remains provably open. Even if a fresh hook instance over the same store later
reports `reconciliation_state=clear`, `intent_state=open` blocks every further
write before transport. Only an external reconciliation process may close the
exact open generation with persistent closure proof. A successful readback on
an uncertain path, plain `clear`, or a local in-memory marker is never enough.

If atomic closure physically persists but its downstream state confirmation is
unavailable, the current execution returns persistence failure. A fresh builder,
hook, and edge still observe terminal `closed` and block before all transport;
the mutation can never be released for a second write.

Preflight, dedupe, and freshness transport errors return only fixed structured
reason codes; exception type, message, URL, headers, and body are never
exposed. Evidence contains only the
operation, mutation/target hashes, technical result codes, and optional S5
operation hash, never raw site, list, item, or field values.

HTTP 401, 403, 408, and 429 are not retried automatically in the same run. Only
when strict readback proves that the write was not applied is the generation
closed as `retryable`. A later, separately authorized run may restart after
authentication refresh for 401/403. Uncertain results remain sticky open; HTTP
412 remains terminal without retry.

## Acceptance Criteria

- **AC-S4B-01:** Exact Graph v1.0 method, target, field, authorization, approval,
  request, workspace, site, and both list bindings are canonically revalidated
  before every execution; field types and choices match the production
  SharePoint schema, and inactive-list drift blocks too.
- **AC-S4B-02:** Role, purpose, approval, site, list, or write-grant drift
  blocks before transport.
- **AC-S4B-03:** Documented dedupe query, local two-match limit, `nextLink` as
  ambiguity, fresh concrete-item readback, fresh exact PATCH ETag, strict
  readback, and no retry on HTTP 412.
- **AC-S4B-04:** Backfill writes only `VorgangstypId` and binds the canonical
  S5 single operation.
- **AC-S4B-05:** Target-bound execution keys, persistent intent generations,
  and closure proofs remain fail-closed across fresh hook instances:
  `clear + open` and terminal `closed` block replay; verified `retryable`
  permits only a later, separately authorized run.
- **AC-S4B-06:** Zero live calls, credentials, factories, and tenant writes;
  BFF UAMI remains `Sites.Selected/read`.
- **AC-S4B-07:** Contract, validator, fake-Graph tests, DE/EN traceability, and
  review agree.
