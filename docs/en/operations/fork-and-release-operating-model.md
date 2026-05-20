# Fork-And-Release Operating Model

## Goal

This document describes the binding operating model for organizations that use
the central `NaC` repository as a reference:

- a central upstream as reference standard,
- an organization fork as binding operating state,
- optional domain repositories for subject-matter subprocesses with independent
  release cycles.

The model separates reference maintenance, local control and controlled
adoption of new process versions.

## Repository Topology

### 1. Central Reference Repository, Upstream

- Contains generic and domain-specific pattern processes.
- Publishes versioned releases.
- Accepts quality-assured return flows from organization forks.

### 2. Organization Fork, Binding Operating State

- Is the operational truth for the respective organization.
- Maintains local policies, approvals and role binding.
- Adopts upstream changes only through a controlled sync PR.

### 3. Optional Domain Repositories

- Are created only when a domain needs independent release cycles.
- Remain coupled to the organization fork through issue references and release
  references.
- Must satisfy the same minimum controls: PR, review, evidence and versioning.

## Responsibilities

- `upstream_maintainer`: maintains reference modules and release history.
- `enterprise_process_owner`: decides when upstream releases are adopted into
  the fork.
- `enterprise_reviewer`: checks impact, compliance and rollout risk.
- `enterprise_approver`: approves adoption for productive use.
- `domain_owner` optional: owns a domain repository including local approval
  rules.

## Binding Sync Flow

1. Upstream publishes an approved release: tag plus changelog.
2. The organization creates a sync branch in the fork, for example
   `sync/upstream-2026-03`.
3. The upstream change is adopted into the sync branch.
4. Impact assessment and tests are documented.
5. The sync PR is reviewed and approved.
6. After merge, the organization fork creates its own release.
7. Rollout is controlled for new matters; running matters remain unchanged.

## Branch And Tag Convention

- No direct changes on `main`.
- Sync branches start with `sync/upstream-`.
- Hotfix branches start with `hotfix/`.
- Productive process releases use `vMAJOR.MINOR.PATCH`.
- Optional subject-matter closure tags such as `close/YYYY-MM`.

Recommendation: for evidence, always use the `v*` release as technical
reference, even if a subject-matter closure tag exists in parallel.

## When To Use A Domain Repository Instead Of Only A Fork

A dedicated domain repository is useful when at least two of the following
criteria apply:

- its own approval process with a different responsibility structure,
- significantly higher change frequency than the core model,
- separate compliance evidence or external review paths,
- its own deployment or automation scheme.

If these criteria do not apply, the process stays in the organization fork.

## Return Flow To Upstream

Return flow is optional and only happens as a separate upstream PR:

- with subject-matter rationale,
- with evidence from pilot or operation,
- without organization-specific internal or confidential data.

This keeps the reference model able to learn without losing local control.
