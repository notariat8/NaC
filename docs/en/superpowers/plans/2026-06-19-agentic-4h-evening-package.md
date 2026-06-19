# Agentic 4h Evening Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare four hours of owner-light NaC work that can run in parallel without OCI writes, secret reads, mandate data, or full workspace access.

**Architecture:** The package splits work into independent lanes that can each produce a protected PR or a batched owner gate. The coordinator keeps GitHub as the source of truth, records time through the NaC time ledger, and stops only at Design, Release, Apply, Secret, destructive Git, or live-data gates.

**Tech Stack:** GitHub PRs/issues/projects, NaC Python unit tests, `scripts/quality_gate.py`, `nac time-ledger`, OCI read-only CLI evidence where already approved.

---

## Start Window

- Prepared at: 2026-06-19 17:12 CEST.
- Intended start: 2026-06-19 17:42 CEST.
- Runtime budget: 4 hours.
- Hard end target: 2026-06-19 21:42 CEST.
- Codex thread wake-up: not available in this session. If this thread is inactive at the start time, the package is ready but will not self-start.

## Active Inputs

- Open PR: `notariat8/NaC#189`, mandatory server-side session store for `/workspace`.
- Recent merged queue: Q2T-Q2V and related release-memory tracks.
- Existing queue reference: `docs/en/superpowers/plans/2026-06-19-agentic-8h-current-queue.md`.
- Current guardrail: no OCI writes, no secret values, no full workspace, no mandate data.

## Parallel Lanes

### Lane 1: PR #189 Follow-Up And Release Packet

**Objective:** Keep PR #189 review-ready and prepare the next release gate text only after merge.

**Files:**
- Read: `src/nac_identity/oidc_session.py`
- Read: `src/nac_web/server.py`
- Read: `tests/test_nac_web.py`
- Read: `docs/en/authenticated-webapp-operating-model.md`

- [ ] **Step 1: Read PR state**

Run:

```bash
gh pr view 189 --repo notariat8/NaC --json state,mergeStateStatus,headRefOid,baseRefName,headRefName,url
gh pr checks 189 --repo notariat8/NaC
```

Expected:

- PR is open until owner merge.
- Checks are passing before asking for review.

- [ ] **Step 2: Do not release before merge**

Rule:

```text
If PR #189 is not merged, do not request OCI DevOps build, Resource Manager variable refresh, or release approval.
```

- [ ] **Step 3: Prepare post-merge release gate**

If PR #189 is merged, get the merge commit:

```bash
gh pr view 189 --repo notariat8/NaC --json mergeCommit
```

Prepare this exact gate with the actual commit:

```text
Owner Release Approval for PR189 OCI DevOps build and Function deploy of notariat8/NaC@<merge_commit_sha> with NAC_RELEASE_COMMIT=<merge_commit_sha>
```

Stop before running the release.

### Lane 2: Workspace/Auth Track B Design Prep

**Objective:** Prepare the next protected PR for explicit role/case/purpose gate reason classes and redacted audit contract, without implementing new runtime access.

**Files:**
- Read: `src/nac_identity/role_case_gate.py`
- Read: `src/nac_web/server.py`
- Read: `tests/test_nac_web.py`
- Read: `tests/test_oci_tenant_identity.py`
- Modify only after design approval: narrow tests and role/case gate code.

- [ ] **Step 1: Inspect current gate reasons**

Run:

```bash
rg -n "role_missing|tenant_mismatch|case_missing|purpose_missing|four_eyes|evaluate_role_case_gate" src tests docs/en docs/de
```

Expected:

- Current gate reasons are found in `src/nac_identity/role_case_gate.py` and `/workspace` rendering.

- [ ] **Step 2: Prepare owner design gate**

Use this gate text:

```text
Owner Design Approval for next Workspace/Auth Track B: formalize the /workspace role-case-purpose gate as a metadata-only authorization contract with explicit reason classes, optional four-eyes requirement, redacted audit evidence, and no exposure of tenant hints, case IDs, session IDs, claims, emails, provider details or mandate content; fail closed, protected PR, no OCI writes.
```

- [ ] **Step 3: Prepare test targets only**

Draft test names, do not implement before design approval:

```text
tests.test_nac_web.NaCLocalWebTests.test_workspace_redacts_gate_reason_context_values
tests.test_oci_tenant_identity.NaCOciTenantIdentityTests.test_role_case_gate_returns_explicit_safe_reason_classes
```

Stop before code edits unless the owner gives the design approval.

### Lane 3: Onboarding Track C Customer Status Prep

**Objective:** Improve the customer-facing onboarding status after admin review using existing safe status fields only.

**Files:**
- Read: `src/nac_identity/onboarding_requests.py`
- Read: `src/nac_web/server.py`
- Read: `tests/test_nac_web.py`
- Read: `tests/test_onboarding_requests.py`

- [ ] **Step 1: Inspect existing request status fields**

Run:

```bash
rg -n "request_status|invitation_status|review|onboarding/requests|admin/onboarding" src tests docs/en docs/de
```

Expected:

- Existing fields are enough to show customer-safe review progress.

- [ ] **Step 2: Prepare owner design gate**

Use this gate text:

```text
Owner Design Approval for next Onboarding Track C: improve the customer-facing request status page after admin review using only existing request_status and invitation_status fields and customer-safe copy; show that review is documented and invitation remains pending; no customer mail dispatch, no mandate data, no internal provider or admin terminology.
```

- [ ] **Step 3: Prepare stop checks**

Do not implement anything that:

```text
- sends customer mail,
- creates invitation dispatch,
- adds lifecycle states without contract,
- exposes provider, OCI, admin, secret, or internal operator terminology to customers.
```

### Lane 4: Hygiene, Baseline, And Context Pack

**Objective:** Keep the 4h run auditable and avoid repeated owner prompts for routine evidence.

**Files:**
- Read: `docs/en/superpowers/plans/2026-06-19-agentic-8h-current-queue.md`
- Read: `docs/de/superpowers/plans/2026-06-19-agentic-8h-current-queue.md`
- Read: `out/observability/codex-time-ledger.jsonl` only if needed; do not commit output.

- [ ] **Step 1: Start time ledger session**

Run:

```bash
PYTHONPATH=src /home/ubuntu/.venvs/nac/bin/nac time-ledger add --session-id 2026-06-19-agentic-4h-evening --task "4h evening agentic package" --phase start --category other --notes "Package start; no OCI writes, no secrets, no mandate data."
```

Expected:

- Ledger writes to `out/observability/codex-time-ledger.jsonl`.
- The file remains untracked.

- [ ] **Step 2: Baseline checks**

Run:

```bash
git status --short --branch
git diff --check
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

If socket tests fail in sandbox with `PermissionError`, rerun the same command outside the sandbox as verification, not as product work.

- [ ] **Step 3: Branch hygiene audit**

Run:

```bash
git branch --merged main
git branch -r --merged origin/main
```

Output only an exact cleanup gate. Do not delete branches without owner approval.

## Batched Owner Packet

At the end of the 4h window, produce one packet:

```text
1. PR #189 status and, if merged, the exact release gate.
2. One recommended design gate: Track B or Track C, with rationale.
3. Branch cleanup gate with exact branch list, if any.
4. Verification evidence and time-ledger summary.
```

## Hard Stop Lines

Stop before:

- OCI DevOps build or Function deploy.
- Resource Manager variable refresh, plan, or apply.
- Any secret value, Vault secret read, or new secret OCID.
- Branch deletion, force push, reset, or destructive Git action.
- Live token exchange behavior change.
- Full workspace access, mandate data, document lists, uploads, or real case access.

## Verification Commands

Use these before declaring the package ready:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
git diff --check
git status --short --branch
```

