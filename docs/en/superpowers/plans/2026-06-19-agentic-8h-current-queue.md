# Agentic 8h Current Queue

> **Status:** June 19, 2026. This queue does not replace the general operating
> rules in `2026-06-18-agentic-8h-work-packages.md`; it updates the work state
> after the now-closed Q2Q-Q2V and release-lane tracks.

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

These branches are merged according to the current read-only audit and may be
proposed as a cleanup gate.

NaC:

```text
agent/178-q2t-session-store-adapter
agent/179-q2u-workspace-binding-normalizers
agent/181-q2v-onboarding-review-audit
agent/release-memory-parity-check
```

OCI Landing Zone:

```text
agent/93-owner-gate-text-normalizer
agent/release-memory-parity-check
```

`www-n8`: no visible cleanup branches.

## Next Domain Tracks As Gate Candidates

### Track A: Server Session Store Required For `/workspace`

Owner gate:

```text
Owner Design Approval for next Workspace/Auth Track A: make the server-side session-store mandatory for /workspace and every route beyond protected start; a signed cookie alone is no longer sufficient, missing/unavailable/revoked/expired store records fail closed, audit remains redacted metadata-only, no full workspace, no mandate data, no OCI writes.
```

Stop lines:

- No productive store adapter.
- No Vault or secret access.
- No OCI runtime configuration.
- No live session migration.

### Track B: Sharpen Role/Case/Purpose Gate Audit

Owner gate:

```text
Owner Design Approval for next Workspace/Auth Track B: formalize the /workspace role-case-purpose gate as a metadata-only authorization contract with explicit reason classes, optional four-eyes requirement, redacted audit evidence, and no exposure of tenant hints, case IDs, session IDs, claims, emails, provider details or mandate content; fail closed, protected PR, no OCI writes.
```

Stop lines:

- No real tenant or case lookups.
- No real case identifiers in browser or log output.
- No productive IdP role or group changes.

### Track C: Customer Status After Admin Review

Owner gate:

```text
Owner Design Approval for next Onboarding Track C: improve the customer-facing request status page after admin review using only existing request_status and invitation_status fields and customer-safe copy; show that review is documented and invitation remains pending; no customer mail dispatch, no mandate data, no internal provider or admin terminology.
```

Stop lines:

- No customer mail dispatch.
- No invitation sending.
- No new lifecycle states without a contract.
- No internal provider or admin terminology in customer HTML.

## Batched Owner Packet

After all owner-free lanes are prepared, the owner should not be interrupted by
intermediate questions. Instead, Codex produces exactly one packet:

```text
1. Branch cleanup gate with exact branch list.
2. One recommended next owner design gate.
3. Optional release gate only for a concretely checked commit.
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
