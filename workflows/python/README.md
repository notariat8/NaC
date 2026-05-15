# Python Workflows

Status: active development

This folder is the deterministic Python workflow layer. Python is the execution
and validation layer for repeatable notary-office workflows.

Python workflows must provide:

- schema-backed inputs and outputs
- idempotency keys
- approval gates
- dry-run or plan-preview mode
- metadata-only evidence records
- no storage of real secrets or real personal data

## Implemented Runtime Surface

The first implemented runtime is [src/notary_kg/](../../src/notary_kg). It reads
the usecase-local static notarial KG files and exposes executable
readiness/status views.

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
```

## Next Development Step

The next workflow increment is a contract generator that reads one KG case and
creates a workflow contract skeleton under `workflows/contracts/` without real
mandate data.
