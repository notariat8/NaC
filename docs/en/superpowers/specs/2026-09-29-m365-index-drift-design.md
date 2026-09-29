# Issue #760: Reproducible SharePoint indexes and read-only drift check

Status: design for owner review; no live execution.

## Purpose and finding

The Teams MVP configuration declares indexed SharePoint columns in
`indexed_columns`, but the provisioning plan currently sets `indexed=true`
only when `enforce_unique_values=true`. This makes the generated payload
disagree with the desired schema for three of the four columns examined in
the Teams 403 investigation. The existing runtime check detects missing
lists, not missing indexes, and the `drift` CLI edge is still a blocked MVP
placeholder. Issue #760 closes this reproducibility gap; it does not by
itself establish the complete cause of the Teams 403.

## Scope and decision

1. The existing declarative schema remains the sole desired-state source.
   Each list creates indexes only for names in `indexed_columns`, while
   `enforce_unique_values=true` still implies an index. A declared index
   without a matching column, duplicate names, or contradictory uniqueness
   requirements fails validation.
2. The `ensure_column` plan derives index status from the parent list.
   Synthetic tests cover every declared indexed column, especially
   `Akten.NacCaseId`, `Vertretungsfreigaben.NacCaseId`,
   `AuditJournalLite.NacCaseId`, and `AuditJournalLite.CorrelationId`.
3. `nac m365 teams-sharepoint drift` becomes a read-only, workspace-bound
   metadata check. It compares the site ID, list ID and list name from the
   bound provisioned state, plus expected column names and their `indexed`
   values, using fixed Microsoft Graph GET paths. It reads no list items or
   files.
4. Missing or ambiguous bindings, missing or duplicate columns,
   `indexed=false`, incomplete/paged metadata, Graph failures, and unexpected
   response shapes produce deterministic redacted failures. There is no
   automatic PATCH, deployment, or permission change. A real tenant read
   needs separate bound authorization; Issue #760 runs synthetic tests only.

This targeted correction is preferred over a full redeployment because it
repairs desired-state generation and drift detection without shipping a new
Teams app or BFF. A full rebuild with the old provisioning code would again
omit three indexes.

## Acceptance criteria

- **AC-760-1:** Schema validation rejects missing, duplicate, or
  contradictory index declarations.
- **AC-760-2:** Every column declared in `indexed_columns` has
  `indexed=true` in its creation plan; undeclared columns do not acquire an
  unintended index.
- **AC-760-3:** The drift check reports `PASSED` only when every bound list
  and indexed column matches in the selected workspace. Negative tests cover
  missing, duplicate, and unindexed columns, wrong bindings, and incomplete
  responses.
- **AC-760-4:** The drift check emits metadata GET requests and a redacted
  result only. Synthetic tests prove zero writes, zero item/file reads, and
  zero real provider calls.
- **AC-760-5:** DE/EN documentation, CLI, spec traceability, and required
  gates remain synchronized; the complete PR diff and remote CI are reviewed.

## Risks and non-goals

The previously observed permission failure on index PATCH remains a separate
tenant-apply blocker. This repository change neither grants permissions nor
sets indexes in the tenant. It also cannot prove that the Teams 403 disappears
after a later schema correction; that needs a separately authorized functional
test. No changes to #739, #632, the Teams app, BFF, or existing list items.
