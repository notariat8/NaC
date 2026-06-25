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

## First Anchors

- `tenants`
- `users`
- `sessions`
- `matters`
- `process_templates`
- `process_instances`
- `process_events`
- `audit_events`

At this stage, these anchors may only hold safe metadata. Raw data from
matters, deeds, IDs, powers of attorney, register lookups or land-register data
requires a separate design, protection and apply gate.

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

The next technical track can derive a non-destructive ATP schema for the anchors
from this contract. After that, NaC can add a write path for demo metadata and
later a graph projection.
