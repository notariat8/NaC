# Notarkammer Demo Runtime Seed

Status: owner-free contract-first slice, no OCI apply.

The demo runtime seed connects the mandate-data-free real-estate purchase
fixture with the ATP runtime store adapter. It writes demo metadata only for
tenant, matter, process instance, process events and audit. The runtime graph
projection can derive a visible graph view with XNP/SNP gates, external
boundaries, parallel groups, duration bands and the critical path from those
process events.

The seed is the first concrete fixture for `runtime_graph_metadata_v0`. The
fixture contains a structured `runtime_event_profile`; the seed writes
append-only `process_events` from it, including dependencies, duration bands,
parallel groups, external boundary labels and the critical path.

## Boundaries

- No mandate data.
- No productive XNP/SNP action.
- No OCI apply.
- No secrets.
- No real register or land-register data.

The seed is a demo and test contract. Productive storage in ATP remains a
separate owner-gated boundary.
