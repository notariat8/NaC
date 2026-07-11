# Notarial Process/Ontology Contract

Status: S1/S2 implemented offline on 2026-07-11 under
[Issue #610](https://github.com/notariat8/NaC/issues/610); S3-S7 open.

This decision note describes the implemented domain product-model contract for
the M365/SharePoint MVP. The machine-readable contract is
[workflows/contracts/notarial-process-ontology.contract.json](../../../workflows/contracts/notarial-process-ontology.contract.json)
and is evaluated with `nac kg process-ontology-contract`.

## Identity And Validity

- The inventory contains 20 canonical `BusinessCaseTypeId` values and two
  historical aliases. Aliases are not new canonical identities.
- The repository-versioned use-case catalog remains authoritative.
- The viewer-independent `Vorgangsartenregister` is the required SharePoint
  runtime projection. `BusinessCaseTypeId` is unique, indexed and associated
  with `LifecycleStatus`, `Selectable` and `CatalogVersion` there.
- `Akten.VorgangstypId` is the additive indexed text projection of the same
  identity.
- `Akten.Vorgangstyp` remains an unchanged legacy Choice. S2 plans no Choice
  extension, conversion or other patch of that field.
- `Prozessregister` is optional. When a row exists,
  `ProcessKey == BusinessCaseTypeId`. `NacProcessId` remains the technical row
  identity.
- `NacBpmnModelId`, `BpmnDriveItemId`, `BpmnXmlSha256`, `BpmnGitPath`,
  `BpmnGitCommitSha`, `NacBpmnVersion` and `BpmnContentMode` are nullable in
  `Prozessregister`.
- A missing `Prozessregister`, missing BPMN model or disabled viewer does not
  invalidate a canonical business-case type. Only the specific BPMN/viewer
  operation is blocked.

SharePoint remains the operational MVP store for metadata, tasks, document
pointers, deputy grants and redacted audit events. The ontology remains a
versioned product-model and projection contract, not a runtime store or global
reasoner on the request path.

## Offline Boundaries

S1 and S2 are implemented exclusively offline:

- no Microsoft Graph requests
- no SharePoint writes
- no SharePoint schema changes
- no matter values or document full text in the repository
- no secrets and no central knowledge-graph folder
- Microsoft Graph REST v1.0 remains the only future M365 data boundary; SDKs,
  legacy SharePoint APIs and Graph beta remain blocked

The
[process ontology validator](../../../scripts/validate_notarial_process_ontology_contract.py)
checks these boundaries.

## Schema Gap And Apply Plan

`nac kg process-ontology-schema-gap` compares the v2 contract with the current
SharePoint MVP schema at
[deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json](../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json).
The v0.2 result identifies:

- the required `Vorgangsartenregister`
- the additive `Akten.VorgangstypId` text column
- additional process-instance field gaps
- the optional `Prozessregister` and optional `BPMN Models` library as
  separate viewer projections that are not part of the required S2 apply plan
- the protected fingerprint of the unchanged legacy
  `Akten.Vorgangstyp` Choice

`nac kg process-ontology-schema-apply-plan` produces 33 fully local Graph REST
request templates for the required default S2 scope. The plan contains
idempotency checks, preconditions, expected success statuses, snapshots and
additive recovery boundaries. It contains neither `Prozessregister` nor `BPMN
Models`, contains no patch for `Akten.Vorgangstyp` and executes no request.
The two viewer artifacts are prepared only through the separate optional
viewer provisioning plan.

The
[schema-gap](../../../scripts/validate_process_ontology_sharepoint_schema_gap.py)
and
[apply-plan](../../../scripts/validate_process_ontology_sharepoint_schema_apply_plan.py)
validators check these semantics.

## Readiness, Execution Contract And Dry Run

`nac kg process-ontology-schema-apply-readiness` expands the 33 plan steps for
two workspaces into 66 workspace apply units. Site and list IDs, dynamic
resolutions, `Sites.Manage.All`, ordering, idempotency and recovery evidence
are checked offline. `OWNER_GATE_REQUIRED` is not live approval.

`nac kg process-ontology-schema-apply-execution-contract` and
`nac kg process-ontology-schema-apply-runner-dry-run` bind the same 66 units to
preflight, future mutation and readback plans. These artifacts also execute no
Graph requests, write nothing to SharePoint and change no schema.

The
[readiness validator](../../../scripts/validate_process_ontology_sharepoint_schema_apply_readiness.py)
checks workspace expansion. The execution contract sets the binding status
`BLOCKED_PENDING_S6_S7_APPROVAL`.

## Open Slices

S1 Contract and S2 Schema Plan are implemented offline. S3 Runtime, S4
MCP/Graph, S5 Migration, S6 Immutable Evidence and S7 Live Approval remain
open. No live schema apply, backfill, cutover or rollback may run before S6/S7
are implemented and receive dual approval.
