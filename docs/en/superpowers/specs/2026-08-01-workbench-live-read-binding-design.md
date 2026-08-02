# Workbench Live Read Binding

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: workbench-live-read-binding
leading_issue: https://github.com/notariat8/NaC/issues/725
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-08-01-workbench-live-read-binding.md
review_gates:
  - Privacy
  - Workflow
  - External Service
acceptance_ids:
  - AC-1
  - AC-2
  - AC-3
  - AC-4
  - AC-5
  - AC-6
  - AC-7
  - AC-8
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_workbench_endpoint
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_live_graph_ports tests.test_nac_bff_azure_function_host
  - cd spfx/nac-bpmn-viewer && npm run build
  - cd spfx/nac-bpmn-viewer && npm run workbench:capture
  - cd spfx/nac-bpmn-viewer && npm run workbench:live:capture
  - python3 scripts/validate_workbench_live_read_binding.py
  - python3 scripts/nac.py frontend workbench-verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
```

## Goal

Bind the generic Workbench foundation to the existing SPFx/Teams host through
a dedicated, short-lived read endpoint of the Azure BFF. Authorization, role
decisions, projection and redaction attestation remain server-side. The browser
receives neither Graph nor MCP access.

## Acceptance criteria

- **AC-1:** Before any port or Graph call, the BFF enforces the exact synthetic allowlist for tenant, `notary_team_01`, `NAC-SYN-MATTER-001` and the single query purpose. Tenant and subject originate exclusively from validated Entra token claims.
- **AC-2:** Assigned/deputy decisions contain server-bound role, decision ID/version, subject and a lease of at most five minutes. Missing, invalid, wrong-tenant or insufficient-scope tokens return exact `401 AUTHENTICATION_REQUIRED`; authenticated authorization, target and query denials return the exact identifier-free `403 ACCESS_DENIED` body. No response exposes actor/role/decision headers; every response carries `Cache-Control: no-store`.
- **AC-3:** Redaction attestation verifies the complete projected content and binds policy, classifier, timestamp and the normative canonical SHA-256 defined by `workbench-live-read-binding.contract.json`; Python and TypeScript golden wire/Unicode fixtures must produce the same digest.
- **AC-4:** Matter, tasks and BPMN reference come from existing authoritative ports. Unsupported attention, decision and agent states stay empty and are not inferred from deadlines or tasks.
- **AC-5:** The SPFx client uses only `AadHttpClient`, bounds chunked responses without `Content-Length` to 131,072 bytes, and verifies contract, content binding, expected subject from authenticated page context, a fixed UI role allowlist, workspace, matter and purpose. Page context is never a BFF authorization input.
- **AC-6:** The React host loads and refreshes before expiry, discards stale data on every failure and uses a monotonic request generation so delayed or abort-ignoring responses cannot overwrite newer state. Loading, deny and unavailable states are deterministic.
- **AC-7:** The existing BPMN detail view and v0.2 endpoint remain compatible; Workbench becomes the primary read-only work surface.
- **AC-8:** Assigned, deputy, deny, wrong tenant/subject/purpose/workspace/matter, non-synthetic targets, redaction failure, 128 KiB/256 UTF-16 limits, deny-only capabilities, expiry, overlapping refreshes, unmount and abort-ignoring transports are automated; desktop/mobile evidence and strict gate pass.

## Server boundary

The new path is
`GET /v1/workspaces/{workspace_id}/matters/{matter_id}/workbench-snapshot`.
It uses the same validated Entra dependency, existing `Matter.Read` scope and
exactly one allowed `purpose` query parameter. A dedicated domain orchestrator first checks the fixed synthetic allowlist, decides access, then reads fixed Graph projections
and the package-bound BPMN model, and only then builds the snapshot. Serialized
UTF-8 bytes are returned unchanged.

Token authentication failures, including wrong tenant or missing scope, share
the exact neutral `401` body. Only after successful authentication do business
denial, target and query cases share the exact neutral `403` body. Success,
denial and error responses are `no-store`. The
access decision gains the decision metadata required by Workbench. Assigned
roles are derived from the unique matter assignment. Deputy decisions bind the
grant, audit record, role and the exact allowlisted synthetic reason
`Synthetische Urlaubsvertretung`; free-form reasons are rejected before every
data port. Grant validity additionally limits the snapshot lease.

## Data and redaction boundary

The primary privacy boundary is the fixed synthetic allowlist before every
Graph read; redaction scanning is defense in depth. The redaction verifier
accepts only the allowlisted projected structure, recursively
scans for prohibited sensitive text shapes and attests the exact canonical
projection hash. Evidence initially contains only the non-authoritative,
hash-bound BPMN model reference.

## Browser boundary

The SPFx host obtains the expected subject ID from authenticated SharePoint page
context only for a consistency check. Server authorization uses validated token
claims exclusively. The role must belong to a fixed compiled UI allowlist while
the business decision remains server-side. Every load has a monotonic generation;
only the latest active generation may commit state after complete binding checks.
Expiry, abort, parse, hash, scope or network failures immediately discard the
previous snapshot.

## Normative contract

[workbench-live-read-binding.contract.json](../../../../workflows/contracts/workbench-live-read-binding.contract.json)
versions the route, target allowlist, claims authority, deny/cache semantics,
wire limits and canonical hash construction. The content digest covers the
entire top-level object except `redaction`; object keys are recursively sorted
by Unicode code point, arrays preserve order, strings are not normalized and
JSON is serialized without whitespace as UTF-8. The live DTO contains no
numbers, so cross-language number canonicalization is outside this contract.

## Delivery boundary

The slice ends with a protected PR, remote CI and deployment readiness. Live
deployment occurs only from reviewed `main`, only in `notary_team_01`, and only
with existing permissions.
