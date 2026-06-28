# ATP Runtime Storage Contract

This contract extracts the first implementation track from the ATP graph target
model. It does not activate a productive schema or graph feature. It defines
which runtime objects NaC may keep in ATP and how those objects can later be
projected into a graph or ontology view.

The machine-readable contract is
`workflows/contracts/atp-runtime-storage.contract.json`.

## Decision

Git remains the source of truth for code, IaC, governance, BPMN templates and
synthetic demo data. ATP becomes the runtime data plane for tenants, user
bindings, sessions, matters, process instances, process events and audit
metadata.

This is not a purely relational subject-matter decision. The model keeps three
layers separate:

1. Transactional anchors for stable IDs, status and tenant boundaries.
2. Versioned JSON payloads for domain status and gate metadata.
3. Graph projections for dependencies, parallelism, critical paths, XNP/SNP
   gates, document references, deadlines, roles and audit relationships.

## Data Model Slice v0.1

The first binding data-model slice is `runtime_graph_metadata_v0`. It only
covers safe runtime metadata for the first `immobilienkaufvertrag` path. ATP
remains the source:

- transactional anchors for tenant, matter, process instance, append-only
  process events and audit metadata;
- versioned JSON payloads for status, gates, duration bands, external system
  boundaries and redacted audit references;
- derived graph and ontology candidates for dependencies, parallel groups,
  critical path and external gate touchpoints.

Oracle Graph Studio is not part of runtime in this slice. It remains a later
analysis and modeling tool behind a separate owner, apply and cost gate.

## First Anchors

- `tenants`
- `user_bindings`
- `sessions`
- `matters`
- `process_templates`
- `process_instances`
- `process_events`
- `audit_events`

At this stage, these anchors may only hold safe metadata. Raw data from
matters, deeds, IDs, powers of attorney, register lookups or land-register data
requires a separate design, protection and apply gate.

## v0.1 Implementation Boundary

The `runtime_graph_metadata_v0` slice does not implement every target anchor
through the same adapter surface:

- `tenants`, `user_bindings`, `matters`, `process_instances`,
  `process_events` and `audit_events` are the first `RuntimeStoreAdapter`
  boundary for graph status and tests.
- `process_templates` is a schema-artifact anchor, but the v0.1 adapter only
  carries the approved template reference in the `process_instances` payload.
  A dedicated template adapter method remains deferred.
- `sessions` belong to the ATP runtime target model, but are externalized from
  this graph slice: the portal-session path runs through
  `nac_identity.session_store.AtpSessionStore` and
  [atp-onboarding-request-store.sql](../../../deploy/database/atp-onboarding-request-store.sql).

This keeps process graph projection scoped to `process_events` and prevents
auth/session-revocation logic from being mixed into matter status.

## Schema Artifact

The first technical schema slice is captured as a non-destructive artifact in
`deploy/database/atp-runtime-anchor-schema.sql`. The artifact is not an apply
request. It describes idempotent runtime anchors for:

- `nac_tenants`
- `nac_user_bindings`
- `nac_matters`
- `nac_process_templates`
- `nac_process_instances`
- `nac_process_events`
- `nac_audit_events`

Every tenant-scoped runtime table carries a tenant boundary. Domain status
details are stored as validated JSON payloads so they can later be projected
into a graph or ontology view. Process events are append-oriented; they do not
replace audit approval and contain no raw matter data.

## JSON Payload Rules

Every runtime payload needs at least:

- a schema version,
- a payload type,
- a redaction class,
- a reference to the approved template version when the payload belongs to a
  process.

Allowed initial payload types are status, gate, duration, external-gate and
audit metadata. Productive matter content is not part of this contract.

## Graph Projection

The graph projection is a contract first. It describes which nodes and edges may
be derived from transactional anchors and JSON payloads. It does not activate
Graph Studio or a productive graph pipeline.

Important nodes:

- `Tenant`
- `UserBinding`
- `Matter`
- `ProcessTemplate`
- `ProcessInstance`
- `ProcessStep`
- `Gate`
- `ExternalSystem`
- `DocumentReference`
- `Deadline`
- `FeeEvent`
- `AuditEvent`

Important edges:

- `depends_on`
- `parallel_with`
- `critical_path_of`
- `sent_to`
- `received_from`
- `requires`
- `blocks`
- `fee_basis_for`
- `audited_by`

## Guardrails

- No productive schema apply through this PR.
- No productive graph activation through this PR.
- No matter data in Git.
- No secret values in Git or chat.
- No OCI write without a separate owner apply gate.

## Next Track

The next technical track remains metadata-only until
[private-operating-frame-gate.md](private-operating-frame-gate.md) is met.
Only after that may NaC design a separate ATP private-payload schema. Until
then, NaC may only expand non-destructive anchors, demo metadata and graph
projections without raw matter data.
