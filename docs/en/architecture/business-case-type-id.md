# ADR: Stable BusinessCaseTypeId

Status: accepted; S1/S2/S3 implemented offline, S4 read edge in progress, no live apply
Issues: [GitHub #610](https://github.com/notariat8/NaC/issues/610), [GitHub #612](https://github.com/notariat8/NaC/issues/612), [GitHub #616](https://github.com/notariat8/NaC/issues/616)
Date: 2026-07-11

## Context

The versioned use-case catalog exposes the domain entity `BusinessCaseType`.
The active SharePoint MVP list `Akten` currently projects it as the required
four-value Choice `Vorgangstyp`. Every additional business-case type would
therefore require a privileged Choice schema update in every workspace. The
optional BPMN viewer plan already defines the indexed text key
`Prozessregister.ProcessKey` instead.

This decision reconciles the
[notarial process ontology contract](../../../workflows/contracts/notarial-process-ontology.contract.json)
and the
[BPMN viewer adapter contract](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json)
around one identity. The current boundaries are checked by the
[process ontology validator](../../../scripts/validate_notarial_process_ontology_contract.py)
and the
[BPMN viewer adapter validator](../../../scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py).
Issue #610 implements S1 and S2 exclusively offline in contracts, validators,
inventory and schema planning. It executed no Graph requests, changed no
tenant and applied no SharePoint schema live. S3 is being implemented offline
under Issue #612 according to the
[S3 spec](../superpowers/specs/2026-07-11-business-case-type-runtime-s3-design.md)
and
[S3 implementation plan](../superpowers/plans/2026-07-11-business-case-type-runtime-s3.md).
Its status remains `in progress` until code, contract, negative-test,
strict-gate and Protected-PR evidence passes. S4 through S7 remain open.

## Decision

`BusinessCaseTypeId` is the canonical, immutable text identifier of a notarial
business-case type. For every canonical business-case type, exactly this
identity holds:

```text
BusinessCaseTypeId == Vorgangsartenregister.BusinessCaseTypeId
                   == Akten.VorgangstypId

When a process row exists:
BusinessCaseTypeId == Prozessregister.ProcessKey
```

- The value is the approved canonical use-case slug in lowercase kebab-case
  (`^[a-z0-9]+(?:-[a-z0-9]+)*$`, no more than 128 characters).
- Comparison and storage are exact. Runtime input with different casing,
  whitespace or silent normalization is rejected.
- A published identifier is never renamed or reused. A domain successor gets
  a new identifier; the old entry becomes unselectable or retired.
- `Vorgangsartenregister` is a thin, viewer-independent runtime projection with
  unique indexed `BusinessCaseTypeId`, `LifecycleStatus`, `Selectable` and
  `CatalogVersion`. It has no required BPMN, model or viewer fields and is read
  through `business_case_type_get`.
- `Prozessregister` remains optional. When a row exists, `ProcessKey` is
  indexed, unique and identical to `BusinessCaseTypeId`. `NacProcessId` remains
  the technical row identity; `NacBpmnModelId`, `BpmnDriveItemId` and other
  BPMN links are nullable.
- A missing `Prozessregister` row, missing BPMN model or disabled viewer does
  not invalidate a canonical business-case type. Only the specific BPMN- or
  viewer-dependent operation is blocked.
- `Akten.VorgangstypId` is planned as a new indexed single-line text column.
  `Akten.Vorgangstyp` is not converted in place from Choice to text.

The ontology term `BusinessCaseType` is therefore the domain class, the
repo-versioned catalog is its leading definition, `Vorgangsartenregister` is
its minimal runtime projection, and `Prozessregister` is an optional
process/viewer projection. No second `BusinessCaseType` Choice column is
introduced.

## Canonical And Alias Rules

An identifier is valid at runtime only when the reviewed repository catalog
marks it canonical and not retired and exactly one matching row with the same
`CatalogVersion` exists in `Vorgangsartenregister`. Missing, duplicate,
unselectable or retired type rows block matter assignment. `Prozessregister`
is checked only for a process/viewer operation: an existing row with a
different `ProcessKey` blocks that operation, but its absence blocks neither
canonical validity nor `case_create`.

Legacy aliases such as `grundstueckskaufvertrag` and `testament` remain
historical translations only:

- An alias is never a `BusinessCaseTypeId`, `ProcessKey` or `VorgangstypId`
  and cannot be selected for a new matter.
- Every alias points directly to exactly one canonical identifier. Chains,
  cycles, ambiguous targets and collisions with canonical IDs are invalid.
- Alias translation is allowed only for existing-data migration or a bounded
  legacy read and emits an audit event.
- An alias is not silently promoted to a new identity. That change requires a
  separate architecture decision and migration.

## Fail-Closed Validation And Cache

Before `case_create` or a correction of the business-case type, the runtime
uses the viewer-independent lookup and checks in this order:

1. Syntax and exact spelling of `BusinessCaseTypeId`.
2. A canonical, non-retired entry approved for new matters in the
   repo-versioned catalog.
3. Exactly one selectable, non-retired `Vorgangsartenregister` row with the
   identical `BusinessCaseTypeId` and matching `CatalogVersion`.
4. For an existing matter: no conflict between `VorgangstypId` and a legacy
   Choice that is still being read.

Any error, timeout, unknown status, catalog/registry version drift, duplicate
or expired cache entry blocks the mutation. A read-only view may report
`validation_unavailable`, but it must not treat the value as valid. Only a
specific BPMN-/viewer-dependent operation additionally loads
`Prozessregister`; missing or unapproved process or BPMN metadata blocks only
that operation.

The runtime cache contains only `BusinessCaseTypeId`, status,
`CatalogVersion`, row ETag and timestamps from `Vorgangsartenregister`, never
matter or document data. Its key is `(siteId, BusinessCaseTypeId,
CatalogVersion)`. It revalidates after five minutes; after no more than 15
minutes without successful revalidation, the entry is unusable. Graph ETags
are used for conditional reads where the endpoint supports them; otherwise,
returned row ETags are compared. A version change or ETag conflict invalidates
the complete affected site cache. Negative results are held for no more than
30 seconds. Process/viewer metadata has a separate cache and is never consulted
for `BusinessCaseTypeId` validity.

## Legacy Choice Transition

The migration is implemented as an explicit state sequence:

| Phase | Read behavior | Write behavior | Exit criterion |
| --- | --- | --- | --- |
| `inventory` | legacy unchanged | no writes | redacted inventory scan and unambiguous mapping table |
| `column_ready` | legacy leads | optional `VorgangstypId`, no live automation | owner-gated schema readback confirms indexed text |
| `dual` | new ID first, legacy fallback | new ID always; legacy only with an unambiguous old value | zero `unknown`, `missing`, `conflict`, `etag_skipped` or `unresolved`; stable final scans |
| `canonical` | `VorgangstypId` only | `VorgangstypId` only | at least one release with verified N-1 compatibility and no legacy fallback |
| `retired_legacy` | legacy for audit history only | legacy blocked | separate cleanup approval |

During dual-read, if both fields match through the static mapping table,
`VorgangstypId` wins. If the new ID is absent, the legacy value may be
translated only until the documented deadline. A conflict, empty value or
unknown Choice blocks. During dual-write, the legacy value is set only when
the frozen Choice list can represent it. While `Vorgangstyp` remains required,
new matters stay limited to those representable values; only a separately
approved schema change may make the field optional.

`dual` is limited to no more than two releases or 90 calendar days after
activation, whichever happens first. The migration manifest records the
start, deadline and responsible owner. An extension requires review and a
reasoned new decision; indefinite dual operation is not allowed.

## Backfill, Snapshots And Recovery

The future backfill starts with a read-only dry run. It classifies every matter
as `already_canonical`, `mappable`, `conflict`, `unknown`, `missing`,
`etag_skipped` or `unresolved` and publishes only redacted counts and hashes.
The owner-gated write run is paged and idempotent, writes only
`VorgangstypId`, uses the current item ETag with `If-Match`, and places
concurrently changed items in persistent quarantine. Values are never guessed.

The migration manifest binds the repository commit and `CatalogVersion`,
schema and list IDs, paged `Akten` snapshots with item ETags, the complete
`Vorgangsartenregister` snapshot, and a `Prozessregister` snapshot with row
ETags and nullable BPMN links. A missing `Prozessregister` is explicitly
recorded as `not_provisioned`. The manifest also binds runtime/contract version
N, the tested N-1 candidate, mapping version, role approvals and snapshot
hashes.

Cutover is allowed only when every matter is `already_canonical` and the counts
for `unknown`, `missing`, `conflict`, `etag_skipped` and `unresolved` are
exactly zero. Two complete scans then run at least 15 minutes apart while
migration writes are frozen. Item count and the hash over item ID, relevant
field values and ETags must be identical; any difference restarts the check.
Registry and process-register snapshots are rebound immediately before
approval.

N-1 compatibility is a cutover prerequisite: the previous runtime candidate
must read `VorgangstypId`, ignore additive registry fields, treat unknown IDs
fail-closed, and display new types without a legacy Choice as read-only. No
live cutover is allowed without a passing N/N-1 replay.

Rollback deletes neither columns nor values and runs strictly in this order:

1. Stop matter creation, correction, backfill, cutover and dependent routing.
2. Immutably store the rollback intent, current snapshots/ETags and quarantine.
3. Disable the canonical-write flag and invalidate registry/process caches.
4. Switch to the tested N-1 candidate.
5. Restore registry/process projections only when needed and only with ETag
   guards to the bound snapshot; retain columns and canonical values.
6. Run readback and a complete rescan; reopen only unambiguously representable
   legacy writes.

Forward recovery does not introduce legacy substitutes. It redeploys N, loads
catalog and registries afresh, replays the immutable outbox idempotently,
resolves every quarantine case and repeats both stable final scans. Any later
column cleanup remains a separate owner gate.

## Permissions, Immutable Evidence And Privacy

- Runtime reads and matter-metadata access use the existing per-site
  `Sites.Selected` runtime application. They receive no schema administration
  rights.
- `Sites.Manage.All` remains exclusive to the controlled, owner-gated
  provisioning path. Microsoft documents it as the least-privileged permission
  for [updating a column definition](https://learn.microsoft.com/en-us/graph/api/columndefinition-update?view=graph-rest-1.0).
- Runtime and backfill read only selected metadata fields through Microsoft
  Graph REST v1.0. No SharePoint file content, raw Graph responses, tokens or
  matter payloads are persisted.
- `AuditJournalLite` is only a mutable operational projection and is not
  audit-proof evidence. Before every live mutation, an intent must be written
  to a durable append-only outbox and transferred through a broker, hash chain,
  signature/anchor and WORM store under the
  [audit-proof event-stream policy](../../../policies/revisionssicherheit-eventstream-policy.yaml);
  outcome and readback follow as separate events.
- Live schema, backfill, correction, cutover and rollback mutations are
  prohibited while the outbox, immutable event stream, readback or persistent
  reconciliation quarantine is unavailable. A failure after the SharePoint
  write remains persistently blocked as `reconciliation_required`; only a
  separately approved reconciliation closure may release it.
- Evidence contains correlation ID, pseudonymous `ActorRef`, tool/role ID,
  action, result code, `BusinessCaseTypeId`, catalog/manifest version, and
  registry, process-register and item ETags. Matter numbers and document
  content remain excluded.
- `ActorRef` remains personal data despite pseudonymization. It is produced as
  a tenant-bound HMAC of the Entra object ID with a key version; the key and
  resolvable mapping stay separated outside the repository, event and
  SharePoint. The event and `ActorRef` have at least ten years of immutable
  retention plus legal hold. Only `revision_audit` may access pseudonymous
  events; resolution requires a documented purpose and dual approval by
  `revision_audit` and `freigabeverantwortung`. Monthly access reviews and each
  resolution access are themselves logged immutably.

## Roles And Separation Of Duties

The implementation binds these operation roles to qualified principals from
the existing role model; `automation` may execute but never approve.

| Operation | Execution | Approval | Mandatory separation |
| --- | --- | --- | --- |
| Mapping | `MappingAuthor` | `MappingApprover` | author and approver are different principals |
| Backfill | `BackfillOperator` | `MappingApprover` and `ReleaseApprover` | operator was neither mapping author nor approver |
| Single correction | `MatterCorrector` | `CorrectionApprover` | correction of own mapping/backfill writes is prohibited |
| Reconciliation | `ReconciliationOperator` | `ReconciliationApprover` | writer cannot close quarantine |
| Cutover | `CutoverOperator` | `ProcessOwner` and `ReleaseApprover` | both approvers and operator are distinct; operator is not the backfill operator |
| Rollback | `RollbackOperator` | `RollbackApprover` | executor and approver are distinct; approval is manifest- and snapshot-bound |
| Actor resolution | `EvidenceCustodian` | `revision_audit` and `freigabeverantwortung` | dual purpose approval, no runtime principal |

Negative authorization tests block at least wrong role, self-approval, missing
distinct principals, wrong site/matter, expired or different-manifest approval,
correction by mapping/backfill author, quarantine closure by the writer,
cutover by the backfill operator, rollback without independent approval, and
`ActorRef` resolution without dual purpose approval.

## Explicit Implementation Slices

This ADR is accepted. Issue #610 implemented S1 and S2 offline on 2026-07-11.
S3 through S7 remain open and each requires review and suitable tests before a
live apply can be considered.

| Slice | Status | Required change | Acceptance edge |
| --- | --- | --- | --- |
| S1 Contract | implemented offline in #610 | align ontology, inventory and viewer contracts on independent `Vorgangsartenregister`, optional `Prozessregister`, nullable BPMN links and alias invariants | validators prove viewer-independent type validity and block drift offline |
| S2 Schema plan | implemented offline in #610 | plan `Akten.VorgangstypId` and `Vorgangsartenregister` in the required default; keep `Prozessregister` and `BPMN Models` in separate optional viewer provisioning; leave legacy Choice unchanged | 33 plan steps and 66 workspace apply units; dry run, readiness, snapshot and rollback plan; `BLOCKED_PENDING_S6_S7_APPROVAL` |
| S3 Runtime | implemented offline in #614 | implement `business_case_type_get`, content-based `CatalogVersion`, explicit runtime lifecycle, purpose-bound aliases and separate registry/viewer ETag caches offline | spec, domain/verification contracts, validator, CLI, negative tests, strict gate, independent review and Protected PR checks pass without Graph/tenant access |
| S4 Graph Read Edge | in progress in #616; S4b writes open | constrain `case_create`, correction/backfill paths and optional process reads by selected fields, paging, ETag, site scope and operation roles | negative authorization and fake-Graph smokes prove no broad rights or viewer coupling |
| S5 Migration | open | implement inventory dry run, idempotent backfill, persistent quarantine, registry/process snapshots, stable final scans and N-1 replay | all seven classes, ETag conflicts, rollback order and forward recovery pass |
| S6 Immutable evidence | open | implement durable outbox, broker/WORM events, correlation, pseudonymous ActorRef, retention, access review and reconciliation | every live mutation stays blocked without complete intent/outcome/readback evidence |
| S7 Live approval | open | prepare separate owner-gated schema/backfill apply with separation of duties and no cleanup | complete PR diff, N/N-1 rollback rehearsal, negative authorization and explicit dual approval |

## Acceptance Criteria And Verification

- `AC-610-01`: All three projections use the same stable identifier where they
  exist; type validity remains viewer-independent.
- `AC-610-02`: Alias, retired, drift, duplicate and cache failures block
  fail-closed.
- `AC-610-03`: Dual-read/write, backfill, cutover and rollback are bounded,
  ETag-protected, proven by stable final scans and avoid in-place Choice
  conversion.
- `AC-610-04`: Runtime, provisioning and audit are constrained by least
  privilege and separation of duties; negative authorization tests are
  mandatory.
- `AC-610-05`: S1 through S7 identify code, schema, MCP and evidence work before
  any live apply.
- `AC-610-06`: German and English ADRs and internal links are valid.
- `AC-610-07`: `AuditJournalLite` is not an audit-proof source; live mutation
  remains prohibited without an immutable outbox/event stream and persistent
  quarantine.
- `AC-610-08`: Snapshots bind `Vorgangsartenregister`, `Prozessregister` and
  ETags; N-1 rollback and forward recovery are tested before cutover.
- `AC-610-09`: `ActorRef` is treated as personal data, pseudonymized, resolved
  only for a defined purpose and protected for at least ten years.

For the offline implemented S1/S2 artifacts, run:

```bash
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
```

Later implementation pull requests must also pass the affected contract
validators and the [strict quality gate](../quality-gate.md).

## S4 Graph Read Edge (#616)

The active S4 read edge binds Graph REST v1.0 `GET` immutably to the site, `Vorgangsartenregister`, operation and role. Only `Sites.Selected` and an existing site grant `read` are allowed; paging must preserve the `BusinessCaseTypeId` and `CatalogVersion` filters. Row ETags are compared locally only after a complete read and are never sent as collection `If-None-Match`. Results remain redacted and viewer-isolated. The entry point is `nac m365 teams-sharepoint business-case-type-read-plan`; it is offline and loads no credentials, HTTP, DNS or Graph client. S4b writes remain open.

Traceability: **AC-S4-01:** exact GET/projection path; **AC-S4-02:** complete same-filter paging; **AC-S4-03:** local ETag evaluation; **AC-S4-04:** exact permission/grant binding; **AC-S4-05:** strict typing and viewer isolation; **AC-S4-06:** redaction; **AC-S4-07:** CLI, contracts, validator, tests, documentation and gates.
