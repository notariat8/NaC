# Runtime Status Wiring Runbook

Status: owner-free contract-first boundary, no OCI Apply.

This runbook describes how the current notariat8 portal start for the first
Immobilienkaufvertrag moves safely from demo status to the later ATP runtime
store. It is not a deployment or database migration plan.

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

## Later ATP Path

ATP becomes the runtime data store for tenants, user bindings, matters, process
instances, process events and audit metadata. The first product-adjacent wiring
does not replace the contract; it replaces only the adapter:

- `RuntimeStoreAdapter` remains the functional boundary.
- `process_events` stay append-only.
- The graph projection continues to be derived from events.
- Browser output contains no internal IDs, no provider details, no claims, no
  email addresses and no session values.
- The full workspace remains closed until a separate owner-gated boundary is
  approved functionally and technically.

## ATP Metadata Seam

The protected first matter status can be prepared for the later ATP source
through environment switches without triggering a database migration, wallet or
secret change, or OCI Apply:

- `NAC_FIRST_MATTER_RUNTIME_SOURCE` activates the ATP metadata seam only for the
  values `atp`, `atp-json`, `atp_metadata` or `atp-runtime-metadata`.
- `NAC_FIRST_MATTER_RUNTIME_OBJECT_KEY` optionally overrides the logical runtime
  object key. Without a value,
  `runtime/notarkammer-first/immobilienkaufvertrag.metadata.json` is used.
- `NAC_FIRST_MATTER_RUNTIME_PAYLOAD_COLUMN` optionally overrides the JSON payload
  column. Without a value, `payload_json` is used.
- If the ATP row reader is not available yet, the route does not serve packaged
  fallback data and remains fail-closed.

## Fail-closed Rules

The status path must fail-closed stay closed if any of these conditions occurs:

- Runtime store unavailable.
- ATP metadata seam active without an approved row reader.
- Process instance or events missing.
- Graph projection cannot be built from events.
- Status model contains mandate data.
- Presenter would expose internal identifiers, provider details or access
  values.
- Productive XNP/SNP action would be required.

## Owner Gates

These steps still require explicit approval:

- ATP schema migration.
- ATP wallet, credential or secret changes.
- OCI Function configuration or Resource Manager Apply.
- Productive XNP/SNP action.
- Writing real mandate data.

Without those approvals, the path remains a safe demo and contract-first path:
no mandate data, no OCI Apply, no productive XNP action.
