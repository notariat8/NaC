# ATP Runtime Graph Projection

Status: owner-free contract-first slice, no OCI apply.

This contract extends the ATP runtime store with a testable graph projection from
`process_events`. The projection creates a mandate-data-free metadata view for the
demo, reviews and a later Oracle Graph activation.

## Purpose

Runtime events remain the append-only source. The graph view derives:

- Nodes for the process instance, gates and external systems.
- Edges for event gates, external touchpoints and dependencies.
- Parallel groups for business steps that may start at the same time.
- duration bands for hours, days, weeks or months.
- critical path entries for steps that are expected to drive completion.

## Guardrails

- No live OCI.
- No schema apply.
- No secrets.
- No mandate data.
- No productive XNP/SNP action.
- No raw browser identifiers as business output.

## Oracle Graph Studio Boundary

The first implementation is deliberately a Python projection from approved
runtime metadata. Oracle Graph Studio, property graph, PGQL and RDF/OWL are only
target and analysis terms here. Graph Studio is not a runtime UI dependency and
not a productive activation.

A later Oracle Graph or PGQL use needs a separate owner apply and cost gate,
including role approval such as `GRAPH_DEVELOPER`.
