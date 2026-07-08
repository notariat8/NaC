# Release Checklist For Process Versions

## Purpose

This checklist is the binding approval form for versioned process packages. It
connects the tag, GitHub Release, audit artifacts and rollout decision so that a
process version can be reviewed later.

The checklist applies to:

- new or changed process packages,
- upstream syncs in organization forks,
- productive pilot approvals,
- releases used as the reference state for new matters.

It does not apply to typo fixes, internal documentation clarifications without
process impact or local test runs without approval character.

## Release Data

Before the tag is created, these details must be present in the leading issue,
pull request or release draft:

- process package or scope, for example `notary`,
  `immobilienkaufvertrag` or `unterschriftsbeglaubigung`,
- target version or tag, for example `v*`,
- start of applicability for new matters,
- rollout mode:
  - immediately active for new matters,
  - active only after pilot,
  - postponed,
- responsible roles: subject-matter review, compliance review, operational
  approval,
- fallback state for new matters if the rollout must be stopped.

## Mandatory Checks

Before tag and release, the affected checks must be freshly documented:

- `python scripts/startup_check.py --profile base --ide auto --run-tests`
- `python scripts/nac.py doctor --profile strict`
- affected BPMN, KG, plugin or QMS checks when the scope changes those areas,
- GitHub checks for privacy, secrets and quality gate,
- For M365 MVP runtime approvals: `release-readiness` as Go/No-Go evidence
  with `mvp_release_readiness=READY`, `release_gate_readiness=READY`,
  `matter_access_delegation_smoke`, `matter_access_apply_readiness` and
  `matter_access_apply_request_plan`,
- review decision according to the selected delivery mode.

If a check does not apply, document why. A missing tool is not a silent
replacement for evidence.

## Audit And Evidence Artifacts

The release links at least:

- leading issue with assignment, scope, risk gate and delivery mode,
- pull request or owner-direct evidence,
- changelog or release notes,
- test and validation evidence,
- affected process, BPMN, KG or QMS artifacts,
- SBOM or AI-SBOM artifacts when dependencies, plugins, AI surfaces or runtime
  prerequisites changed,
- privacy and secret-check evidence,
- approval decision and rollout start.

Artifacts must not contain secrets, PINs, credentials, private document content
or real matter data.

## Tag And Release Flow

1. Freeze release scope and check open blockers.
2. Run all mandatory checks freshly or document why they do not apply.
3. Capture review and approval decision in the leading issue or pull request.
4. Write changelog or release notes with affected process packages.
5. Create tag `v*` on the approved commit.
6. Create a GitHub Release from the tag and link this checklist plus evidence
   artifacts.
7. Document rollout decision for new matters.
8. For pilot operation, capture the next review date.

## Go/No-Go

A release may be treated as approved only when:

- the approved commit is unambiguous,
- the tag points to exactly that commit,
- all mandatory checks and reviews are documented,
- M365 MVP runtime changes reference redacted `release-readiness` evidence with
  `mvp_release_readiness=READY`,
- the rollout mode is known,
- a fallback state is known,
- release notes, artifacts and GitHub comments contain no secrets or real
  matter data.

If one of these criteria is missing, the state remains a candidate and is not
used as a valid process version.

## After The Release

After the release, update the leading issue with:

- tag and GitHub Release,
- start of applicability,
- rollout mode,
- link to evidence artifacts,
- open follow-up actions,
- decision whether pilot review, hotfix or regular next sync is needed.
