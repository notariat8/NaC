# Issue Taxonomy Per Repository

## Goal

This document defines which topics belong in which repository and how issues
are linked across repositories.

## Repository Types

### Upstream Repository, Central NaC

Responsible for:

- generic reference processes,
- domain-specific pattern building blocks,
- cross-cutting governance standards,
- publicly usable improvements returned from forks.

Not responsible for:

- organization-internal special cases,
- local operating decisions without reference relevance.

### Organization Fork

Responsible for:

- local process adjustments,
- release adoption from upstream,
- compliance and rollout decisions in the organization,
- binding operating state and audit evidence.

### Optional Domain Repositories

Responsible for:

- dense subject logic of individual domains, for example notary file,
- dense operational changes with their own release cadence,
- domain-specific integrations and subject-matter evidence.

## Issue Classes, Minimum Standard

- `process-change`: subject-matter process change.
- `compliance-change`: regulatory or governance-relevant change.
- `sync-upstream`: adoption of an upstream release into the fork.
- `incident`: disruption, deviation or rule violation in operation.
- `documentation`: clarification or evidence adjustment without process-logic
  change.

## Leading-Issue Rule Per Topic

- One topic has exactly one leading issue in exactly one repository.
- Related issues in other repositories are linked as derived issues.
- The status of the leading issue controls overall progress.

## Linking Standard

Every dependent issue contains:

- reference to the leading issue: `upstream`, `fork` or `domain`,
- short classification of the local effect,
- required decision date.

Recommended title prefixes:

- `[UPSTREAM]`
- `[FORK]`
- `[DOMAIN-NOTARY]`

## Example Distribution

Case: a new notary-office flow is adjusted in the central standard.

1. Upstream issue describes the reference change.
2. Fork issue `sync-upstream` plans local adoption.
3. Domain issue assesses notary-specific effects.
4. After approval, the fork issue references the productive release tag.

## Simple Status Model

- `backlog`
- `in_assessment`
- `in_implementation`
- `in_review`
- `approved`
- `released`
- `closed`

All repositories use the same status values so cross-repository reporting stays
consistent.
