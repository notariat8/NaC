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

`nac kg process-ontology-schema-apply-artifact-index --format json` writes a
second redacted index over existing dry-run artifacts. The index is
metadata-only: it contains paths, schema/status values, step counts, redaction
flags and the `required_for_live_apply_readiness` marker, but no request
details. If the default folder does not yet contain a dry-run artifact, the
command creates that default artifact offline first.

`nac kg process-ontology-schema-apply-live-readiness-gate --format json`
writes a final offline gate before a later real SharePoint schema apply. The
gate checks that the execution contract, workspace readiness, runner dry-run,
redacted artifact index, redaction boundary and owner gate are complete. The
command also writes the redacted artifact index when it is not yet present in
the selected artifact folder.

`nac kg process-ontology-schema-apply-owner-gated-live-plan --format json`
writes the next offline contract for the later live execution. The plan contains
the concrete approval text, required flags, forbidden flags, stop rules, phase
plan and minimum evidence set. It explicitly declares the future live runner as
not implemented yet and remains `offline_only`.

`nac kg process-ontology-schema-apply-owner-gated-runner-contract --format json`
then writes the execution-near runner contract. It binds the later
`nac kg process-ontology-schema-apply-live` command to 68 planned runner steps,
owner gate, required flags, stop-before-mutation rules and redacted evidence.
This contract also does not implement the live runner yet and executes no Graph
requests.

## Boundaries

The dry-run is offline-only:

- no Graph requests
- no SharePoint writes
- no schema changes
- no request headers
- no tokens or secrets
- no raw Graph responses

The next step can be a redacted dry-run artifact. A real live apply remains a
separate owner gate. The live-readiness gate also executes no Graph requests,
writes no SharePoint data and changes no schema; it only proves that the later
offline evidence is complete and redacted. The owner-gated live plan also
executes no Graph requests; it only makes the later execution edge reviewable.
The runner contract also remains offline and is the last interface boundary
before the actual runner implementation.

The validators
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run.py)
,
[scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact.py)
and
[scripts/validate_process_ontology_sharepoint_schema_apply_artifact_index.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_artifact_index.py)
and
[scripts/validate_process_ontology_sharepoint_schema_apply_live_readiness_gate.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_live_readiness_gate.py)
and
[scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan.py)
and
[scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract.py)
check this boundary in the strict quality gate.
