# NoC Workflows

This directory is the execution layer for notary-office business processes. It
is separate from `plugins/` and from `usecases/`.

## Boundary

- `plugins/` contains installable Marketplace or workspace companion packages.
- `workflows/` contains reusable workflow logic for notary-office operations.
- `usecases/` contains concrete notarial business scenarios that bind plugins
  and workflows together.

## Planned Layout

- `skills/`: installable or repo-local skills that guide LLM-facing operation.
- `python/`: deterministic Python workflow modules for validation, idempotency,
  execution planning, and evidence metadata.
- `contracts/`: workflow input/output contracts, approvals, data classes, and
  plugin dependencies.

No workflow may store real secrets or real personal data. Workflow execution
must remain reviewable through Git, pull requests, approvals, and evidence
metadata.
