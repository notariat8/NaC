# Parallel Operation With Version Binding

## Goal

This document regulates mixed operation when old and new process versions must
run at the same time in a legally robust and audit-proof way.

Core principle: **the process version valid at matter start remains binding for
that matter.**

## Binding Rules

1. Every new matter receives a process-version reference (`process_version`) at
   start.
2. `process_version` points to an approved release tag in the organization fork.
3. Running matters do not automatically move to later releases.
4. New releases apply only to matters started after approval.
5. Exceptions, such as manually moving a matter to a new version, require a
   documented individual decision.

## Minimum Metadata Per Matter

- `request_id`
- `process_domain`, for example `notary`, `invoice` or `tax`
- `process_version`, for example `v1.6.2`
- `version_bound_at`, timestamp of binding
- `bound_by_role`, role or person that started the matter
- `compliance_basis`, optional internal policy or external reference

## Audit Evidence

For every matter, it must be reproducible:

- which process version applied,
- when and why that version was bound,
- which approvals existed for that version,
- whether and why a documented exception existed.

## Flow When A Central Update Arrives During Running Matters

1. The upstream update is assessed in the organization fork through a sync PR.
2. A new organization release is approved.
3. Already running matters keep the old `process_version`.
4. New matters use the new release.
5. Reporting and audit separate old and new matters.

## Example: Notary Opens A File For A Client

- 10:15: file `NOT-2026-0042` starts with `process_version=v1.4.0`.
- 12:30: release `v1.5.0` is approved.
- 13:00: new file `NOT-2026-0043` starts with `process_version=v1.5.0`.
- Result:
  - `NOT-2026-0042` finishes compliantly on `v1.4.0`.
  - `NOT-2026-0043` follows the new flow on `v1.5.0`.

Running matters therefore remain stable and new matters use the updated
standard.

## Move Rule For Special Cases

Moving a running matter to a new version is allowed only when:

- subject-matter and regulatory effects have been checked,
- the decision is documented by an authorized role,
- the move itself is archived as a traceable evidence step.
