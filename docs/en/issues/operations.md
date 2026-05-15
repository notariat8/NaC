# Access And Issue Operations In The Organization

## Goal

This document describes an implementable model for:

- a shared task overview across multiple repositories,
- strict visibility per file or repository,
- role and permission maintenance for employees, clients and auditors.

## Basic Rule

In GitHub, permissions are assigned at **repository level**, not at issue level.

Consequence:

- A user who cannot see a repository cannot see its issues.
- A shared overview across many repositories is provided through an
  organization project.

Compliance addition:

- Issues are the **operational layer**.
- Audit-proof storage is provided through a separate immutable event journal.
- Details: [docs/en/eventstream/revisionssicherheit.md](../eventstream/revisionssicherheit.md)

## Repository Types In The Organization

1. `core-repo`
   - central rules, standards and shared workflows
2. `domain-repo`
   - subject-matter domain context, for example notary office
3. `case-repo`
   - individual file or proceeding, for example `case-notary-2026-0042`

## Roles And Technical Assignment

Subject-matter roles are maintained in
[policies/role-model-policy.yaml](../../../policies/role-model-policy.yaml).
GitHub logins are mapped to technical roles in
[policies/github-identity-registry.json](../../../policies/github-identity-registry.json).
Repository and issue visibility plus guest access are bindingly defined in
[policies/access-control-policy.yaml](../../../policies/access-control-policy.yaml).

Technical teams in the GitHub organization:

- `team-notaries-all`: all notaries with full visibility over all notary files
- `team-notary-ops`: operational notary-office staff
- `team-tax`, `team-law`, `team-software`, `team-carpentry` per vertical
- `team-audit-readonly`: internal audit view, read-only

External users:

- Client as guest user, `outside collaborator`, only on their `case-repo`.
- External auditor as guest user, read-only only on approved `case-repo` or
  audit repository.

## Permission Matrix, Recommended

| Role/group | core-repo | domain-repo | case-repo, own file | case-repo, other file |
| --- | --- | --- | --- | --- |
| `notar_fachlich` | write/maintain | write/maintain | maintain | no access |
| `sachbearbeitung_notary` | read/triage | write | write | no access |
| `prozessverantwortung` | maintain | maintain | maintain | read, optional |
| internal `revision_audit` | read | read | read | read, approved only |
| `mandant_gast` | no access | no access | read or triage | no access |
| external `auditor_gast` | no access | no access | read, approved | no access |

Notes:

- Notaries with overall responsibility receive team access to all notary
  `case-repo` repositories.
- Employees without a repository task receive no access to that repository and
  cannot see its issues.

## Shared Issue Overview Across Repositories

Use a GitHub organization project as central task view.

Recommended fields:

- `case_id`
- `domain`
- `repo_type`, one of `core`, `domain`, `case`
- `impact_level`
- `decision_type`
- `due_date`

Recommended views:

- `my_tasks`: `assignee = @me`
- `notary_all_cases`: `domain = notary`
- `audit_view`: `impact_level in (medium, high)` and
  `decision_type = requires_approval`
- `client_case_view`: only issues of the respective `case-repo`

Important:

- The project shows only issues from repositories the user can already access.
- This creates a central overview without permission leakage.

## Standard Flow: Create New File

1. Create `case-repo` according to naming standard, for example
   `case-notary-2026-0042`.
2. Use repository template for files: issue templates, labels, protection
   rules.
3. Set team permissions:
   - `team-notaries-all` at least `maintain`,
   - responsible staff `write`.
4. Add client as guest user: `read` or `triage` according to policy.
5. Add auditor, where required, as guest user with `read`.
6. Create start issues from template:
   - `intake`
   - `identity_check`
   - `document_preparation`
   - `approval_gate`
   - `execution_tracking`
7. Assign issues to the organization project and fill mandatory fields.
8. Document `process_version` for the matter through version binding.

## Maintenance Process For Roles And Rights

Maintenance locations:

- subject-matter decision: [policies/role-model-policy.yaml](../../../policies/role-model-policy.yaml)
- technical login assignment: [policies/github-identity-registry.json](../../../policies/github-identity-registry.json)
- access model and guest rules: [policies/access-control-policy.yaml](../../../policies/access-control-policy.yaml)
- operating flow and rights procedure: this document

Maintenance cycle:

1. Monthly role review with process owner.
2. Quarterly recertification for guest access.
3. Immediate adjustment after role change, offboarding or incident.

## Minimum Controls

- no direct changes on `main`
- PR and review for all process changes
- CODEOWNERS per domain or case
- environment gates for approval-required steps
- regular audit-log review for guest access, repository permissions and
  approvals
