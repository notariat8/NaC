# Agentic 8h Current Queue

> **Status:** June 20, 2026. This queue does not replace the general operating
> rules in `2026-06-18-agentic-8h-work-packages.md`; it updates the work state
> after the now-closed Q2Q-Q2V, Track A-C, and release-lane tracks.

## Goal

Codex should be able to prepare several NaC work packages in parallel without
interrupting the owner every 20 minutes for routine evidence. Owner gates are
batched and requested only when they are genuinely required by product scope or
governance.

## Current State

- NaC `main` is clean and synchronized with GitHub.
- `oci-landing-zone` `main` is clean and synchronized with GitHub.
- `www-n8` `main` is clean and synchronized with GitHub.
- There are no open PRs in the three repositories.
- The earlier 8h plan inputs `NaC#163`, `NaC#171` and
  `oci-landing-zone#89` are no longer open.
- Q2Q through Q2V have landed or been closed.
- Track A landed through PR #189 and is released: `/workspace` requires a
  server-side session-store record in addition to a signed cookie.
- Track B landed through PR #191: role/case/purpose gate audit reasons are
  explicit and redacted.
- Track C landed through PR #192: the customer-facing onboarding request status
  reflects documented review state without sending invitations or exposing
  internal terminology.
- Read-only branch hygiene currently shows no merged remote cleanup branches
  beyond `main`.

## Owner-Free Work Lanes

These lanes may be prepared without asking the owner:

1. **Read-only Evidence**
   - Read GitHub PR, issue and branch status.
   - Read OCI status as long as no secrets are read and no writes are performed.
   - Check release-lane context and release memory against the current repos.
   - Release memory is verified in NaC; the release-lane context pack is
     verified in the `oci-landing-zone` repository.

2. **Local Baseline**
   - Run `scripts/quality_gate.py --profile strict`.
   - Run `python -m unittest discover -s tests`.
   - Check `git diff --check` and `git status --short --branch`.
   - Sandbox-related local socket failures may be retried outside the sandbox
     as verification retries.

3. **Design And Test Preparation**
   - Read existing specs, tests and contracts.
   - Prepare concrete next owner design gate texts.
   - Prepare red/green tests for already approved designs.
   - Do not implement new product or security scope without owner design
     approval.

4. **Branch Hygiene Audit**
   - List merged or superseded branches only.
   - Prepare an exact cleanup gate text.
   - Do not delete branches before explicit owner approval.

## Current Cleanup Candidates

The June 20 read-only audit shows no merged remote cleanup branches beyond
`origin/main` in NaC or `oci-landing-zone`.

## Next Domain Tracks As Gate Candidates

No pre-approved next domain track is currently open in the repository. The next
feature/security boundary must be introduced by an owner design gate before
implementation starts.

Owner-free work may still continue on:

- release-memory and release-lane evidence checks,
- local baseline and quality-gate verification,
- read-only live smoke evidence,
- branch hygiene audits,
- concrete gate-text preparation for a new owner-selected domain track.

## Batched Owner Packet

After all owner-free lanes are prepared, the owner should not be interrupted by
intermediate questions. Instead, Codex produces exactly one packet:

```text
1. Evidence summary for the current live/runtime state.
2. Branch cleanup gate with exact branch list, only if read-only audit finds
   merged branches.
3. One recommended next owner design gate, only if a concrete next domain track
   has been selected.
4. Optional release gate only for a concretely checked commit.
```

## Hard Stop Lines

Codex stops before:

- Design decisions for new product or security scope.
- OCI DevOps release, build or deploy.
- Resource Manager variable refresh, plan or apply.
- Secret values, new secret OCIDs or Vault reads without a gate.
- Branch deletion or destructive Git actions.
- Full workspace, mandate data, document lists, uploads or real case access.

## Verification

Before completing this queue update:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

Execution can be recorded with `nac time-ledger run`.

Release-lane-specific evidence:

```bash
cd /home/ubuntu/src/private/NaC
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_release_lane_context_memory

cd /home/ubuntu/src/oci-landing-zone
PYTHONPATH=. /home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_release_lane_context_pack
```
