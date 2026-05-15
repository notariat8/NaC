# Release And Sync Playbook

## Purpose

This playbook standardizes how an organization fork adopts, checks and approves
new versions from the central upstream.

## Adoption Cycle

- Standard cycle: monthly or quarterly.
- Out-of-cycle only for security-critical or compliance-critical changes.
- Only approved upstream releases are adopted, not unchecked intermediate
  states.

## Roles In The Adoption Process

- `sync_owner`: manages the complete adoption cycle.
- `reviewer_fachlich`: checks subject-matter effects.
- `reviewer_compliance`: checks regulatory risks.
- `approver`: gives the final go for productive use.

## Standard Flow Per Release

1. Identify upstream release: `v*` plus changelog.
2. Create sync branch: `sync/upstream-YYYY-MM`.
3. Adopt the upstream state.
4. Capture impact assessment: subject-matter, technical, regulatory.
5. Execute tests and validation.
6. Open sync PR with evidence.
7. Review and approve according to role model.
8. Merge into organization `main`.
9. Tag organization release `v*` and start rollout.

## Mandatory Contents Of A Sync PR

- Reference to upstream release ID.
- Summary of relevant changes.
- Impact classification: `low`, `medium`, `high`.
- Test evidence: validation, relevant regressions, pilot case.
- Rollout decision:
  - immediately active for new matters,
  - active only after pilot,
  - postponed.

## PR Gates, Minimum

- no direct push to `main`,
- at least one subject-matter review,
- additional compliance review for `medium/high impact`,
- successful validation of affected process files,
- documented owner for the rollout decision.

## Rollback Rule

If a new release creates unacceptable risks in pilot or operation:

1. Stop rollout for new matters immediately.
2. Return to the last approved release for new matters.
3. Document incident and decision path as an issue.
4. Correct through hotfix or next sync PR.

Running matters remain on their start version and are not retroactively moved.

## Artifacts And Evidence

Every adoption creates at least:

- sync PR with approval history,
- release tag in the organization fork,
- SBOM artifact where required by policy,
- decision entry for rollout and start of applicability.
