# Process-Ontology SharePoint Schema Apply Execution Contract

This decision note describes the last offline edge before a later owner-gated
SharePoint schema apply.

## Purpose

`nac kg process-ontology-schema-apply-execution-contract --format json` takes
the existing apply plan and apply readiness and turns them into an
execution-near contract:

- both notary workspaces are covered
- all workspace apply units stay visible
- eight execution phases order preflight, optional lists, columns, choice
  extensions, readback and evidence
- Graph REST v1 remains the only data plane
- `Sites.Manage.All` and the application-owner path remain mandatory
- a later live runner would additionally have to require `--owner-approved`,
  `--execute-live-schema-apply` and `--write-redacted-evidence`

## Boundaries

The contract itself executes nothing:

- no Graph requests
- no SharePoint writes
- no schema changes
- no tokens, auth headers or secrets
- no raw Graph responses in evidence
- no automatic rollbacks

Any later live execution must fail closed on ambiguous idempotency, missing IDs,
unexpected status codes or missing permission.

## Follow-Up

The next technical follow-up would be a dry-run runner that emits concrete
planned requests and evidence files from this contract, still without live
writes. Only after that does a separate owner gate for real SharePoint schema
changes make sense.

The validator
[scripts/validate_process_ontology_sharepoint_schema_apply_execution_contract.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_execution_contract.py)
checks this boundary in the strict quality gate.
