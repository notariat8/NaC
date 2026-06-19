# Agentic 8h Work Packages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define a no-wait 8h operating pack so Codex can prepare NaC work without owner input and queue only the gates that genuinely require owner approval.

**Architecture:** Split work into approval-free preparation lanes and owner-gated execution lanes. Approval-free lanes may read GitHub/OCI status, run local tests, prepare plans, prepare protected PRs for already approved designs, and produce evidence. Owner-gated lanes stop before Design, Release, Apply, Secret, destructive, or live customer-data actions.

**Tech Stack:** GitHub Issues/PRs, NaC Python unittest/quality gate, OCI CLI read-only status, OCI Resource Manager plan-only evidence, protected PR workflow.

---

## Operating Rules

- Do not ask the owner for routine read-only GitHub or OCI evidence.
- Do not ask the owner to continue between independent preparation tasks.
- Stop and queue a gate for:
  - new product or security design approval;
  - OCI DevOps release/build/deploy approval;
  - Resource Manager variable refresh or apply approval;
  - Vault/Secret material, secret OCIDs not already approved for the specific gate, or secret value access;
  - branch deletion, destructive Git action, or infrastructure destroy;
  - live token exchange behavior changes, full workspace opening, or mandate data access.
- If a sandbox/tool prompt is required for network execution, treat it as a tool limitation, not as an owner governance gate. Prefer already approved command prefixes and context-pack hotpaths before broad discovery.
- All outputs must be customer-safe: no mandate data, no credentials, no raw tokens, no OAuth state, no nonces, no session cookie values.

## Current Inputs

- Open NaC issue: [#163 Q2Q role and case gate for workspace entry](https://github.com/notariat8/NaC/issues/163).
- Open NaC PR: [#171 Release-Lane Context Pack in release memory](https://github.com/notariat8/NaC/pull/171).
- Open OCI landing-zone PR: [#89 Release-Lane Context Pack](https://github.com/notariat8/oci-landing-zone/pull/89).
- No open `www-n8` PRs at plan creation.

## Work Package A: Morning Approval Packet

**Purpose:** Produce a short morning packet that lets the owner approve or reject without repo spelunking.

**Owner input needed during execution:** None.

**Files:** No code files required. Output may be a GitHub issue comment or chat summary.

- [ ] **Step 1: Read open PR and issue status**

Run:

```bash
gh pr view 171 --repo notariat8/NaC --json number,url,title,mergeStateStatus,reviewDecision
gh pr checks 171 --repo notariat8/NaC
gh pr view 89 --repo notariat8/oci-landing-zone --json number,url,title,mergeStateStatus,reviewDecision
gh pr checks 89 --repo notariat8/oci-landing-zone
gh issue view 163 --repo notariat8/NaC --json number,title,url,body,comments,labels
```

Expected: Status and check evidence only; no writes.

- [ ] **Step 2: Summarize owner gates**

Prepare exactly these gate candidates if still current:

```text
Owner Review/Merge PR #171 and oci-landing-zone PR #89.

Owner Design Approval for Q2Q Ansatz A: design full-workspace entry as a NaC role-and-case gate: verified session plus subject-matter role plus tenant, case and purpose binding before any route beyond protected start; metadata/status first, no raw mandate content, human/four-eyes gates where required, fail-closed, protected PR, no OCI writes.
```

- [ ] **Step 3: Identify blocked vs unblocked**

Expected result:

```text
Unblocked: read-only evidence, local test scans, Q2Q design preparation, branch status audit.
Blocked until owner: merge #171/#89, Q2Q implementation PR if design is not approved, any release/apply/secret/destructive action.
```

## Work Package B: Q2Q Design Evidence Pack

**Purpose:** Prepare the Q2Q role-and-case gate design so implementation can start immediately after owner design approval.

**Owner input needed during execution:** None, unless scope contradicts issue #163.

**Files:** Read-only during preparation.

- [ ] **Step 1: Read existing auth/session/role boundary**

Run:

```bash
rg -n "evaluate_oidc_role_gate|validate_session_cookie|session_store|workspace|role_gate|case|purpose|tenant" src tests docs/de docs/en policies
```

Expected: Identify existing contracts, tests, docs, and policy anchors.

- [ ] **Step 2: Produce Q2Q design map**

Prepare this structure in the morning packet or a draft spec:

```text
Q2Q boundary:
- Input: verified server-side session status, NaC subject role, tenant binding, case/vorgang binding, purpose binding.
- Output: protected start/status metadata only, no raw mandate content.
- Fail-closed reasons: session_missing, session_revoked, role_missing, tenant_mismatch, case_missing, purpose_missing, four_eyes_required.
- Audit: reason class, timestamp class, route class; no token, claim, e-mail, subject, session-id or mandate content in browser/log payload.
```

- [ ] **Step 3: Prepare implementation file map**

Expected file map:

```text
Likely tests:
- tests/test_oci_tenant_identity.py
- tests/test_oci_functions_adapter.py

Likely source:
- src/nac_identity/oidc_role_gate.py
- src/nac_identity/oidc_session.py
- src/nac_oci_functions/adapter.py

Likely docs:
- docs/de/operations/oidc-state-log-boundary.md
- docs/de/authenticated-webapp-operating-model.md
- docs/de/superpowers/specs/<date>-q2q-role-case-gate-design.md
```

Stop before implementation if the owner has not approved Q2Q design.

## Work Package C: Local Quality And Security Baseline

**Purpose:** Keep the repo ready for quick PRs by finding test or quality drift before owner review.

**Owner input needed during execution:** None.

**Files:** No source changes unless a separate protected PR is created.

- [ ] **Step 1: Run NaC quality gate**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
```

Expected: `STATUS: PASSED`.

- [ ] **Step 2: Run full unit tests**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
```

Expected: all tests pass.

- [ ] **Step 3: Run diff and status checks**

Run:

```bash
git status --short --branch
git diff --check
```

Expected: clean or only intentional branch changes; no whitespace errors.

If a failure appears, diagnose and prepare a protected PR only if the fix is local, non-secret, and does not change product behavior without a design gate.

## Work Package D: Release-Lane Context Adoption Check

**Purpose:** After PR #89/#171 merge, verify that future release work uses the context pack and avoids repeated broad lookup friction.

**Owner input needed during execution:** PR #89/#171 must be merged first. No OCI apply.

**Files:** No source changes unless drift is found.

- [ ] **Step 1: Sync main after owner merge**

Run after owner merge:

```bash
git -C /home/ubuntu/src/oci-landing-zone switch main
git -C /home/ubuntu/src/oci-landing-zone pull --ff-only
git -C /home/ubuntu/src/private/NaC switch main
git -C /home/ubuntu/src/private/NaC pull --ff-only
```

Expected: both repos fast-forward cleanly.

- [ ] **Step 2: Validate context pack**

Run:

```bash
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_release_lane_context_pack
/home/ubuntu/.venvs/nac/bin/python -m unittest tests.test_release_lane_context_memory
```

Expected: both pass after the relevant PRs are merged.

- [ ] **Step 3: Dry-run release-memory lookup**

Read:

```text
/home/ubuntu/src/private/NaC/workflows/skills/nac-release-memory/SKILL.md
/home/ubuntu/src/private/NaC/workflows/skills/nac-release-memory/references/release-lane.md
/home/ubuntu/src/oci-landing-zone/runbooks/release-lane-context.dev.json
```

Expected: future release runs use context-pack values before broad OCI discovery.

## Work Package E: Branch And Project Hygiene Audit

**Purpose:** Prepare branch cleanup and project-status changes without deleting anything.

**Owner input needed during execution:** None for audit. Branch deletion requires owner approval.

**Files:** No source changes.

- [ ] **Step 1: List open PRs and remote branches**

Run:

```bash
gh pr list --repo notariat8/NaC --state all --limit 50 --json number,state,title,headRefName,mergedAt,url
gh pr list --repo notariat8/oci-landing-zone --state all --limit 50 --json number,state,title,headRefName,mergedAt,url
git -C /home/ubuntu/src/private/NaC branch -r
git -C /home/ubuntu/src/oci-landing-zone branch -r
```

Expected: candidate list only.

- [ ] **Step 2: Prepare cleanup gate**

Do not delete branches. Prepare a specific owner gate:

```text
Owner Approval to delete merged head branches <exact branch list> locally and remotely.
```

## Work Package F: Tomorrow Execution Queue

**Purpose:** Convert all preparation into a clear sequence for the next owner session.

**Owner input needed during execution:** None.

**Files:** No source changes.

- [ ] **Step 1: Order gates**

Expected order:

```text
1. Review/Merge PR #89 and #171.
2. Branch cleanup approval for merged context-pack branches.
3. Q2Q Design Approval from Issue #163.
4. Q2Q protected implementation PR.
5. Release approval only after PR merge and green checks.
6. Resource Manager no-apply plan only if runtime image changes.
7. Apply approval only if plan is clean and owner accepts exact changes.
```

- [ ] **Step 2: Define stop line**

Expected stop line:

```text
Stop before any OCI write, secret read, release build, branch deletion, full workspace opening, live mandate-data access, or unapproved design implementation.
```

## Verification

Before claiming this work pack is ready:

```bash
/home/ubuntu/.venvs/nac/bin/python scripts/quality_gate.py --profile strict
/home/ubuntu/.venvs/nac/bin/python -m unittest discover -s tests
git diff --check
```

Expected: quality gate pass, unit tests pass, no whitespace errors.

## Owner Morning Packet Template

```text
Stand:
- PRs:
- Checks:
- Open issue:
- Branch status:

Prepared work:
- A:
- B:
- C:

Gates needed:
- Owner Review/Merge ...
- Owner Design Approval ...
- Owner Approval to delete ...

No action taken:
- No OCI Apply
- No secret read
- No branch deletion
- No full workspace opening
- No mandate data access
```
