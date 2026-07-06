# Omnigraph As Optional Ontology Projection

Status: architecture decision note
Last content update: 2026-07-06

## Decision

[ModernRelay/omnigraph](https://github.com/ModernRelay/omnigraph) is tracked
for NaC as an optional candidate for a later ontology and agent-context
projection. It is not part of the M365 MVP, not the leading data store, not a
BPMN engine and not a replacement for Microsoft Graph REST, SharePoint, Teams
or NeMo Agent Toolkit / AI-Q.

The active MVP decision remains:

- BPMN 2.0 is the subject-matter process source.
- Usecase-local knowledge graphs remain the canonical ontology baseline.
- Teams, Microsoft 365 group and SharePoint team site are the first data
  plane.
- Microsoft Graph REST or MCP servers based on Graph REST are the integration
  boundary.
- NeMo Agent Toolkit / AI-Q remains the leading agentic runtime.

## Classification

Omnigraph conceptually fits NaC because it addresses graph context, agent
branches, policy boundaries and retrieval over structured graph data. For
long-running notarial workflows it may later help agents answer questions
about process status, open information, evidence, roles, document pointers and
critical BPMN gates.

The right placement is a derived projection:

```text
BPMN + usecase-local KG + SharePoint metadata + audit events
  -> nac-ontology-graph-mcp
    -> optional Omnigraph projection
      -> NeMo/AI-Q agents read context
```

Omnigraph must not hold raw matter data, document contents, identity-card data,
registry or land-register payloads, or secrets. Access, substitution, purpose
binding and write approvals remain in the NaC role, matter, purpose and
substitution gate.

## BPMN Relevance

Omnigraph is only indirectly relevant for BPMN. It can project BPMN models
into queryable nodes and edges, for example:

- `ProcessTemplate`
- `BpmnTask`
- `Gate`
- `Role`
- `DataClass`
- `EvidenceRequirement`
- `DocumentPointer`
- `Matter`
- `ProcessInstance`
- `AccessGrant`
- `AuditEvent`

That supports questions such as:

- Which BPMN gates block completion?
- Which evidence is missing for the next step?
- Which role may approve a task?
- Which document pointers belong to which gate?

Omnigraph does not replace BPMN token semantics, bpmn-js, NaC validators, pull
request review or human approvals.

## MVP Boundaries

Not allowed for the MVP:

- Omnigraph as the leading data store,
- Omnigraph as a SharePoint replacement,
- Omnigraph as a BPMN engine,
- Omnigraph as the sole authorization decision,
- bulk-copying Outlook, Teams, OneDrive or SharePoint into agent memory,
- productive raw-payload projection without the private-payload gate.

## Evaluation Path

A later evaluation is useful once the M365 data plane is stable and a first
NeMo/AI-Q workflow runs through `nac-workflow-mcp`,
`nac-access-grant-mcp` and `nac-audit-evidence-mcp`.

The evaluation must start read-only:

1. Export a synthetic usecase KG and a BPMN model into an
   Omnigraph-compatible schema.
2. Import only demo or template data.
3. Query open information, evidence, critical path and role binding.
4. Compare results against existing NaC validators.
5. Decide whether `nac-ontology-graph-mcp` gets an Omnigraph backend option.

Any productive use then needs its own contract, validator, security review and
owner gate.
