# Python Workflows

This folder is reserved for deterministic Python workflow modules. Python is
the execution and validation layer for repeatable notary-office workflows.

Python workflows must provide:

- schema-backed inputs and outputs
- idempotency keys
- approval gates
- dry-run or plan-preview mode
- metadata-only evidence records
- no storage of real secrets or real personal data
