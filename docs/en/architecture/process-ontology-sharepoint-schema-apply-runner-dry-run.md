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

`nac kg process-ontology-schema-apply-runner-dry-run-artifact --format json`
also writes redacted evidence files:

- `out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.json`
- `out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.md`

The artifact includes all 68 dry-run steps as a redacted index. Site IDs are
collapsed back to `{site-id}`, request headers are not stored, and planned
mutation bodies are represented only as body-shape key lists.

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

The validators
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py)
and
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py)
check this boundary in the strict quality gate.
