# Runtime Status Wiring Runbook

Status: owner-free contract-first boundary, no productive cloud apply.

This runbook describes how the current notariat8 portal start for the first
Immobilienkaufvertrag moves safely from demo status to the later M365/SharePoint
runtime and event journal. It is not a deployment, database or SharePoint apply
plan.

## Current Safe Path

The current path remains fully mandate-data-free:

1. `notarkammer-first-immobilienkaufvertrag.metadata.json` provides the demo
   metadata.
2. `InMemoryRuntimeStore` stores the data only as a test and demo adapter.
3. The demo runtime seed creates tenant, matter, process and audit metadata.
4. `process_events` stay append-only.
5. The runtime graph projection is derived from process events.
6. The runtime status read model condenses the process view.
7. The presenter creates browser-safe text.
8. `/workspace` and `/workspace/immobilienkaufvertrag` show only the start
   status.

The visible demo explains BPMN, XNP/SNP, completion, duration bands and the
critical path without loading real parties, file contents, register data or
land-register data.

## Later M365/Event-Journal Path

M365/SharePoint lists and a later event journal become the runtime data stores
for tenants, user bindings, matters, process instances, process events and
audit metadata. The first product-adjacent wiring does not replace the contract;
it replaces only the adapter:

- `RuntimeStoreAdapter` remains the functional boundary.
- `process_events` stay append-only.
- The graph projection continues to be derived from events.
- Browser output contains no internal IDs, no provider details, no claims, no
  email addresses and no session values.
- The full workspace remains closed until a separate owner-gated boundary is
  approved functionally and technically.

## M365/JSON Metadata Seam

The active metadata seam stays database-free and can later be connected to a
Graph/SharePoint source for the first matter status. Old ATP values are no
longer wired; they fail closed as archived. The protected first matter status
can be checked through environment switches without triggering a database
migration, wallet or secret change, or cloud apply:

- `NAC_FIRST_MATTER_RUNTIME_SOURCE` activates the metadata seam for the values
  `json`, `metadata-json`, `sharepoint`, `m365` or `m365-sharepoint`.
- `NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY` optionally overrides the logical runtime
  object key. Without a value, `DEMO-PROCESS-IMMOBILIENKAUF-01` is used.
- `NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN` optionally overrides the JSON payload
  column. Without a value, `payload_json` is used.
- The reader later uses Graph REST or an MCP server that wraps Graph REST
  internally. Direct old SharePoint APIs, SDK-only access and Oracle ATP readers
  are not part of the active path.
- If the reader is not available yet or an archived ATP source is selected, the
  route does not serve packaged fallback data and remains fail-closed.

## Fail-closed Rules

The status path must fail-closed stay closed if any of these conditions occurs:

- Runtime store unavailable.
- Metadata seam active without an approved reader.
- Archived ATP source selected.
- Process instance or events missing.
- Graph projection cannot be built from events.
- Status model contains mandate data.
- Presenter would expose internal identifiers, provider details or access
  values.
- Productive XNP/SNP action would be required.

## Owner Gates

These steps still require explicit approval:

- M365/SharePoint list provisioning.
- Graph permission changes.
- Serverless Function configuration.
- Productive XNP/SNP action.
- Writing real mandate data.

Without those approvals, the path remains a safe demo and contract-first path:
no mandate data, no productive cloud apply, no productive XNP action.
