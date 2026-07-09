# Process-Ontology SharePoint Schema Apply Runner Dry Run

This decision note describes the offline dry-run before a later owner-gated
SharePoint schema apply.

## Purpose

`nac kg process-ontology-schema-apply-runner-dry-run --format json` turns the
apply plan, apply readiness and execution contract into concrete planned steps:

- preflight request per workspace apply unit
- planned later mutation request with body shape
- planned readback request
- stop-rule plan for failed preflights, unexpected status codes and ambiguous
  readbacks

The dry-run makes the later live sequence reviewable without changing the
tenant.

## Boundaries

The dry-run is offline-only:

- no Graph requests
- no SharePoint writes
- no schema changes
- no request headers
- no tokens or secrets
- no raw Graph responses

The next step can be a redacted dry-run artifact. A real live apply remains a
separate owner gate.

The validator
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py)
checks this boundary in the strict quality gate.
