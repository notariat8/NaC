# ATP, JSON And Graph Runtime Model

Status: target-architecture decision, without OCI apply and without productive
schema apply.

## Decision

NaC uses Oracle ATP as the runtime data platform. This does not mean that the
subject-matter model becomes relational only. Inside ATP, three layers are kept
separate:

1. **Transactional anchors:** tenant, user binding, session, matter, process
   instance, event and audit evidence receive stable technical identities,
   tenant boundaries and transaction rules.
2. **Versioned JSON payloads:** subject-matter state, form state, external
   responses and gate results are stored in a versioned, validatable and
   evolvable format.
3. **Graph and ontology projections:** relationships, dependencies,
   parallelism, critical paths, XNP/SNP gates, document references, deadlines
   and roles are derived from runtime events as a graph model.

Git remains the source for code, IaC, governance and approved BPMN templates.
ATP becomes the system of record for runtime instances and their safe metadata.

## Why Not SQL-Only

A pure table model would be too rigid for NaC. Notarial matters contain
subject-matter relationships, external responses, evidence, dependencies and
parallel paths that are better expressed as graph or ontology structures:

- a real-estate purchase agreement is often blocked on the critical path by
  external responses;
- XNP/SNP, land register, registers, card readers and signatures create gates,
  not only form fields;
- one step can consume several evidence items and release several downstream
  paths;
- subject-matter terms need to remain linkable to sources, roles, document
  types and process steps.

In NaC, `schema` is therefore not a synonym for a fully relational
subject-matter model. It means a stable runtime contract for persistence,
validation, access, audit and projections.

## Why Not Graph-Only

A pure graph model would also be wrong for the first SaaS runtime boundary.
Authentication, session revocation, tenant isolation, idempotency, transactions,
locking, audit and status queries need stable transactional anchors. These
anchors must not be inferred from a freely growing graph.

The graph is therefore not a second truth next to ATP. It is a projection based
on append-only runtime events and approved templates.

## Runtime Flow

1. A BPMN template is reviewed and approved in Git.
2. A tenant activates one concrete template version.
3. A matter creates tenant, user, matter and process-instance anchors in ATP.
4. Every relevant action writes an append-only `process_event`.
5. JSON payloads hold versioned subject-matter metadata and gate results.
6. Graph projections derive relationships, parallel paths, blockers, critical
   paths and evidence relationships.
7. The UI initially reads only redacted status and demo metadata, not raw
   mandate data.

## Ontology Candidates

Initial node types:

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

Initial edge types:

- `belongs_to`
- `acts_as`
- `requires`
- `blocks`
- `produces`
- `consumes`
- `sent_to`
- `received_from`
- `signed_by`
- `depends_on`
- `parallel_with`
- `critical_path_of`
- `fee_basis_for`
- `audited_by`

These terms are not a productive schema approval. They are the decision frame
for the next contract and implementation PRs.

## Oracle Graph Positioning

Oracle describes Graph Studio as part of Oracle Autonomous AI Database
Serverless. It supports property graphs for queries and analytics and
RDF/SPARQL/OWL for knowledge graph and ontology scenarios. Graph Studio uses
Autonomous Database as the persistence layer.

For NaC this means:

- Property graph fits process dependencies, parallelism, critical paths and
  status visualization.
- RDF/OWL may later fit legal-source, ontology and terminology systems.
- Graph Studio is an analysis and modeling tool, not automatically the
  productive runtime UI.
- Activation, roles such as `GRAPH_DEVELOPER` and possible ECPU effects need a
  separate apply and cost gate.

Source: <https://www.oracle.com/de/database/integrated-graph-database/graph-faq/>

## Tenant Model

NaC does not decide on one PDB per tenant here. For the SaaS start, a shared ATP
with explicit tenant boundaries, server-side authorization, tenant binding,
audit and later database policies is the pragmatic starting point. Dedicated
databases, schemas or additional isolation models remain later options for
regulatory, contractual or scaling requirements.

## Non-Goals

- No OCI apply.
- No productive ATP schema apply.
- No Graph Studio activation.
- No productive XNP/SNP action.
- No storage of raw mandate data.
- No storage of productive mandate data in Git.

## Next Tracks

1. Define the runtime contract for relational anchors, JSON payloads and graph
   projection.
2. Model the real-estate purchase agreement as a synthetic ATP process instance
   with XNP/SNP, land-register, register, card-reader and completion gates.
3. Derive critical path, parallelism and duration bands from the graph
   projection.
4. Clarify the editor boundary: BPMN template editor via Git/PR, runtime status
   and events via ATP.
