# ADR: Stable BusinessCaseTypeId

Status: proposal for review, offline, no live apply
Issue: [GitHub #605](https://github.com/notariat8/NaC/issues/605)
Date: 2026-07-10

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
around one identity. This issue changes no code, contract, schema, tenant or
policy.

## Decision

`BusinessCaseTypeId` is the canonical, immutable text identifier of a notarial
business-case type. For every canonical business-case type, exactly this
identity holds:

```text
BusinessCaseTypeId == Prozessregister.ProcessKey == Akten.VorgangstypId
```

- The value is the approved canonical use-case slug in lowercase kebab-case
  (`^[a-z0-9]+(?:-[a-z0-9]+)*$`, no more than 128 characters).
- Comparison and storage are exact. Runtime input with different casing,
  whitespace or silent normalization is rejected.
- A published identifier is never renamed or reused. A domain successor gets
  a new identifier; the old entry becomes unselectable or retired.
- `Prozessregister.ProcessKey` is indexed and unique. There is exactly one
  current registry row per `BusinessCaseTypeId`. `NacProcessId` remains the
  technical row identity and is not a second domain key.
- BPMN versions and model pointers reference `ProcessKey`; they do not create
  additional business-case identities.
- `Akten.VorgangstypId` is planned as a new indexed single-line text column.
  `Akten.Vorgangstyp` is not converted in place from Choice to text.

The ontology term `BusinessCaseType` is therefore the domain class, the
repo-versioned catalog is its leading definition, and `Prozessregister` is
only the approved runtime projection. No second `BusinessCaseType` Choice
column is introduced.

## Canonical And Alias Rules

An identifier is valid at runtime only when the reviewed repository catalog
marks it canonical and not retired. Once `Prozessregister` is operationally
enabled, exactly one additional row with the same `ProcessKey` and
`ProcessStatus=Approved` must exist. Missing, duplicate, `Draft`,
`ReviewRequired` or `Retired` rows block selection and process assignment.

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

Before `case_create`, a correction of the business-case type or process
routing, the runtime checks in this order:

1. Syntax and exact spelling of `BusinessCaseTypeId`.
2. A canonical, non-retired entry approved for new matters in the
   repo-versioned catalog.
3. After registry projection activation: exactly one approved
   `Prozessregister` row with the identical `ProcessKey` and matching
   `CatalogVersion`.
4. For an existing matter: no conflict between `VorgangstypId` and a legacy
   Choice that is still being read.

Any error, timeout, unknown status, catalog/registry version drift, duplicate
or expired cache entry blocks mutation and routing. A read-only view may report
`validation_unavailable`, but it must not treat the value as valid.

The runtime cache contains only `BusinessCaseTypeId`, status,
`CatalogVersion`, row ETag and timestamps, never matter or document data. Its
key is `(siteId, BusinessCaseTypeId, CatalogVersion)`. It revalidates after
five minutes; after no more than 15 minutes without successful revalidation,
the entry is unusable. Graph ETags are used for conditional reads where the
endpoint supports them; otherwise, returned row ETags are compared. A version
change or ETag conflict invalidates the complete affected site cache. Negative
results are held for no more than 30 seconds.

## Legacy Choice Transition

The migration is implemented as an explicit state sequence:

| Phase | Read behavior | Write behavior | Exit criterion |
| --- | --- | --- | --- |
| `inventory` | legacy unchanged | no writes | redacted inventory scan and unambiguous mapping table |
| `column_ready` | legacy leads | optional `VorgangstypId`, no live automation | owner-gated schema readback confirms indexed text |
| `dual` | new ID first, legacy fallback | new ID always; legacy only with an unambiguous old value | backfill complete, zero conflicts |
| `canonical` | `VorgangstypId` only | `VorgangstypId` only | at least one release without legacy fallback |
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

## Backfill And Rollback

The future backfill starts with a read-only dry run. It classifies every matter
as `already_canonical`, `mappable`, `conflict`, `unknown` or `missing` and
publishes only redacted counts and hashes. The owner-gated write run is paged
and idempotent, writes only `VorgangstypId`, uses the current item ETag with
`If-Match`, and skips concurrently changed items. Unknown or conflicting
values are never guessed; they enter a manual reconciliation queue. Cutover is
allowed only with 100 percent of matters classified, zero open conflicts,
complete readback and stored audit evidence.

Rollback deletes neither columns nor values. Before canonical cutover, the
runtime can return to legacy reads because dual-write retained representable
Choice values. After a business-case type without a legacy Choice has been
used, rollback blocks its writes and routing; it must not invent a substitute.
The runtime version, migration manifest, catalog version and cache return
together to the last verified state. Any later column cleanup is a separate
owner gate.

## Permissions, Audit And Evidence

- Runtime reads and matter-metadata access use the existing per-site
  `Sites.Selected` runtime application. They receive no schema administration
  rights.
- `Sites.Manage.All` remains exclusive to the controlled, owner-gated
  provisioning path. Microsoft documents it as the least-privileged permission
  for [updating a column definition](https://learn.microsoft.com/en-us/graph/api/columndefinition-update?view=graph-rest-1.0).
- Runtime and backfill read only selected metadata fields through Microsoft
  Graph REST v1.0. No SharePoint file content, raw Graph responses, tokens or
  matter payloads are persisted.
- Every validation rejection, alias translation, correction, backfill write,
  ETag collision and cutover creates a correlation ID and redacted
  `AuditJournalLite` evidence with actor/tool ID, time, action, result code,
  `BusinessCaseTypeId`, catalog version and registry ETag.
- If the audit path is not ready before a mutation, no write occurs. If the
  audit append fails after a SharePoint write, the operation is blocked as
  `reconciliation_required` and read back before further processing.

Evidence follows the
[audit-proof event-stream policy](../../../policies/revisionssicherheit-eventstream-policy.yaml)
and contains no personal data, matter numbers or document content.

## Explicit Implementation Slices

This ADR approves no slice; every slice requires review and suitable tests
before a live apply can be considered.

| Slice | Required change | Acceptance edge |
| --- | --- | --- |
| S1 Contract | align ontology, inventory and viewer contracts on `BusinessCaseTypeId`, `ProcessKey`, lifecycle, `CatalogVersion` and alias invariants | validators reject aliases, duplicates, retired entries and contract drift offline |
| S2 Schema plan | plan indexed text `Akten.VorgangstypId`; make `Prozessregister.ProcessKey` unique; leave legacy Choice unchanged | dry run, readiness and rollback plan; still no live apply |
| S3 Runtime | implement canonical validation, registry reconciliation, ETag/version cache and fail-closed reason codes | unit and negative tests for timeout, drift, duplicate, alias and cache expiry |
| S4 MCP/Graph | constrain `case_create`, correction/backfill paths and `process_register_list` to selected fields, paging, ETags and site scope | fake-Graph smokes prove no file reads, raw responses or broad rights |
| S5 Migration | implement redacted inventory dry run, idempotent backfill, conflict queue, readback and cutover gate | synthetic fixtures cover all five classes and ETag conflicts |
| S6 Audit/evidence | add correlation, `AuditJournalLite`, redacted artifacts, retention and reconciliation | evidence validator checks counts, hashes, privacy flags and complete readback |
| S7 Live approval | prepare a separate owner-gated schema/backfill apply with least privilege and no cleanup | complete PR diff, rollback rehearsal and explicit owner approval |

## Acceptance Criteria And Verification

- `AC-605-01`: All three projections use exactly the same stable identifier;
  `ProcessKey` is unique.
- `AC-605-02`: Alias, retired, drift, duplicate and cache failures block
  fail-closed.
- `AC-605-03`: Dual-read/write, backfill, cutover and rollback are bounded,
  ETag-protected and avoid in-place Choice conversion.
- `AC-605-04`: Runtime, provisioning and audit are separated by least privilege
  and data minimization.
- `AC-605-05`: S1 through S7 identify code, schema, MCP and evidence work before
  any live apply.
- `AC-605-06`: German and English ADRs and internal links are valid.

For this documentation-only proposal, run:

```bash
python3 scripts/validate_language_parity.py
python3 scripts/validate_doc_links.py
```

Later implementation pull requests must also pass the affected contract
validators and the [strict quality gate](../quality-gate.md).
