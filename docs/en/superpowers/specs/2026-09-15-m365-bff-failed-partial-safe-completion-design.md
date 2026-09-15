# Safe Completion of the Partial M365 BFF Activation

Status: Draft for owner review

Date: 15 September 2026
Leading issue: [#746](https://github.com/notariat8/NaC/issues/746)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-failed-partial-safe-completion
leading_issue: https://github.com/notariat8/NaC/issues/746
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Platform
  - Security
affected_artifacts:
  - docs/de/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - docs/en/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
acceptance_ids:
  - AC-746-01
  - AC-746-02
  - AC-746-03
  - AC-746-04
  - AC-746-05
  - AC-746-06
  - AC-746-07
  - AC-746-08
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/validate_m365_azure_bff_live_activation.py
  - python -m unittest tests.test_windows_offline_cli_portability
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git fetch --no-tags --prune origin main
  - git diff --name-status origin/main...HEAD
  - git log --oneline origin/main..HEAD
  - git diff origin/main...HEAD
  - git diff --check origin/main...HEAD
  - gh pr checks --watch
  - gh pr checks --json name,state,workflow,bucket
```

## Purpose and Boundary

This specification defines the safe path from the current partial state to the
possibility of a new, separately approved live run for the exclusively
synthetic workspace `notary_team_01`. It does not itself authorize a provider
write, a local lock release, a live retry, or generation of a valid live
approval.

The visible Teams message `Kein Zugriff auf diesen Arbeitsbereich` must not be
fixed through a UI bypass. Completion must prove the unchanged chain
`Teams/SPFx -> AadHttpClient -> Entra-protected BFF -> server-side access gate
-> Microsoft Graph REST v1.0`. Until then, the message remains an expected
fail-closed result.

## Documented Provenance and Starting Hypothesis to Be Verified

GitHub surfaces are not product or runtime state. The following statements are
historical provenance and form only the starting hypothesis. Current local and
provider state remains `UNVERIFIED` and therefore `BLOCKED` until the bound
local artifacts and double read-only inspection freshly pass. Four existing
issues have distinct roles:

- [#620](https://github.com/notariat8/NaC/issues/620) remains the parent for the
  visible M365 MVP test environment. Its 19 July run ended at step 6
  `grant_target_site_read` as `FAILED_PARTIAL`; its lock and ledger were closed
  in an orderly way. This run is historical provenance only.
- [#632](https://github.com/notariat8/NaC/issues/632) remains the governing live
  activation contract and the contract-defined approval surface for a later new
  live run.
- [#739](https://github.com/notariat8/NaC/issues/739) holds the current live-run
  documentation trail and the separate local step-7 release gate. The latest
  documented run `nac-bff-live-20260908-issue739-v4` passed
  steps 1 through 6 and terminated at step 7 `deploy_function_package` with
  `AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS`. All three lock journals remained
  quarantined.
- [#743](https://github.com/notariat8/NaC/issues/743) records an older
  interruption for which the issue reports missing secure local state. Its
  evidence must not be mixed
  with the current #739 run trail or used to reconstruct missing bindings.

The repository already contains the narrow
`bff-azure-function-deployment-reconcile` inspection, which requires no new
owner gate. It is limited to the
exact terminal step-7 shape and accepts only two equal ARM snapshots constrained
to the target Function with the classification
`FUNCTION_DEPLOYMENT_NOT_APPLIED`. This specification does not broaden that
security boundary; it places the command in a complete closure sequence.

## Evaluated Approaches

### A. Read-only reconciliation followed by a new run

The supported POSIX host first checks every local binding, then allowed network
reachability, and only then the exactly allowlisted read-only provider state.
Only an unambiguous classification may advance to a separate local quarantine
release and later to a new offline owner gate. This is the selected approach
because it preserves old evidence and binds every mutation to a new narrow
owner gate.

### B. Immediate idempotent full rerun

A new twelve-step run could reuse existing resources. Until the current lock,
step-7 evidence, and provider state are unambiguously reconciled, this would
bypass the existing quarantine. The approach remains blocked.

### C. Manual rebuild or cleanup

Manual deletion, permission changes, or redeployment could simplify the target
state but would destroy provenance and exceed the approved no-rollback and
no-deletion boundary. This approach is outside the design.

## Selected Orchestration Sequence

The labels in the following diagram are orchestration phases, not new persisted
run states. The old run state remains `FAILED_PARTIAL` throughout.

```text
LOCAL_PRECHECK
  -> BLOCKED
  -> POSIX_READY
       -> NETWORK_BLOCKED
       -> READ_ONLY_RECONCILIATION
            -> BLOCKED
            -> FUNCTION_DEPLOYMENT_NOT_APPLIED
                 -> OWNER_GATE_REQUIRED_FOR_LOCAL_RELEASE
                 -> LOCK_JOURNALS_RELEASED
                      -> NEW_OFFLINE_OWNER_GATE_REQUIRED
                      -> LIVE_RUN_SEPARATELY_APPROVED
```

`LOCK_JOURNALS_RELEASED` means only that the three local lock journals for the
proven-not-applied step-7 deployment were released append-only. The old run
remains `FAILED_PARTIAL`; state, evidence, ledger, and provider state remain
unchanged. This status is neither `PASSED` nor a live approval.

## Phase 1: Local POSIX Preflight

Before credential, network, or provider access, local validation must establish
at least:

1. a supported POSIX operating system with the existing `flock`, `O_NOFOLLOW`,
   descriptor, ownership, and permission semantics;
2. a clean Git worktree and exact commit and tree;
3. the exact activation, correlation, approval, and target binding of the
   current #739 run;
4. byte-exact state, evidence, ledger, prepared-manifest, Function ZIP, and
   journal integrity;
5. exact toolchain and binary bindings without symlink, path, or late-load
   drift;
6. no concurrent lock ownership.

Windows remains blocked for live, recovery, and provider reconciliation before
all such access with `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`. The portable
Windows offline CLI may provide only static validation and plan views.

## Phase 2: Network and Provider Reconciliation

The centrally managed NVIDIA sandbox policy is an external prerequisite. Before
a new owner gate, only the three narrowly bound targets documented in #739 are
checked: the Function host, SCM host, and Azure CLI blob host. A local allow
rule, wildcard bypass, or broader policy change is outside this work.

After the read-only network check succeeds, only the existing step-7 inspection
may run with an already established authenticated context. It must not start
interactive authentication, create, change, or persist credential material, or
change a permission. It reads the documented ARM endpoints for the exact target
Function twice. Only a stable snapshot proving `FUNCTION_DEPLOYMENT_NOT_APPLIED` is
eligible. An observed deployment, a missing field, drift between snapshots, a
redirect, an authentication or policy error, or a provider result that cannot
be allowlisted returns `BLOCKED`.

Output contains only status, stable error codes, counters, and canonical hashes.
Strict allowlists apply to standard output, standard error, logs, temporary
artifacts, exceptions, telemetry, shell history, and approval comments. Raw
responses, IDs, URLs, tokens, credential values, local secret paths, personal
data, and matter data must not be included there, transmitted to GitHub, or
added to the repository; unknown or unredactable fields block.

## Phase 3: Separate Local Quarantine Release

The inspection that requires no new owner gate may not change any file. Only a
new immutable comment in Issue #739 by the exactly verified owner login `ofunk`,
with an allowed author association and the exact action
`RELEASE_QUARANTINE_FOR_NOT_APPLIED_FUNCTION_DEPLOYMENT`, authorizes a separately
identified operator to invoke the existing reconciler with
`--confirm-release-quarantine`. This gate binds the comment body and its hash,
as well as state, evidence, ledger, lock, provider, prepared-input,
Function-package, commit, tree, and toolchain hashes.

The only mutation is appending a `RELEASED` record to each of the three journals
in a crash-safe, append-only manner.
There is no Azure, Entra, Graph, SharePoint, Teams, App Catalog, or credential
write. Unknown journal tails or any drift block. A torn append may continue
idempotently only under the same unchanged approval binding.

## Phase 4: New Live Run as Its Own Gate

After the quarantine release is proven, a complete offline owner gate is
generated from a new clean commit and tree on the supported POSIX host. It
remains bound to the existing contract-defined Issue #632 surface, the exactly
verified owner login, and an allowed author association. Old #632 or #739
comments are not approval for this run.

The later live approval must bind at least the new activation hash, commit,
tree, target, permission, step sequence, provisioner bootstrap, and toolchain,
plus the unchanged no-rollback and no-deletion rule. Exactly one controlled
live run may start only after separate owner approval. All existing stop, lock,
evidence, redaction, and readback rules remain unchanged.

The three approvals are not interchangeable: approval of this design
specification is neither approval of the local quarantine mutation nor approval
of the later live run.

## Acceptance Criteria

- **AC-746-01:** This English translation and the leading German specification
  document the same starting state, approaches, trust boundaries, stop
  conditions, and separate gates.
- **AC-746-02:** #620, #739, and #743 are connected as separate provenance
  trails together with the governing #632 live-activation contract; neither
  old evidence nor an old owner comment is treated as current success, current
  state, or new approval.
- **AC-746-03:** On a supported POSIX host, the closure path checks the exact
  local state, ledger, all lock journals, prepared inputs, package, commit,
  tree, toolchain, and target binding before provider access; missing or
  conflicting bindings return `BLOCKED`.
- **AC-746-04:** Provider inspection remains entirely read-only, target-bound,
  observed twice, and redacted. Only `FUNCTION_DEPLOYMENT_NOT_APPLIED` allows
  transition to the separate local release gate.
- **AC-746-05:** Windows live, recovery, and reconciliation paths stop before
  credential, state, network, or provider access with
  `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`; POSIX security semantics are not
  weakened.
- **AC-746-06:** The implementation plan created after specification approval
  describes test-first the POSIX/Windows matrix, reconciliation decision table,
  stable error codes, redaction, crash windows, and exact gate transitions as an
  orchestration and operations plan that reuses the existing #739 CLI,
  contracts, and tests. Reconciler code, ARM allowlist, and release algorithm
  remain unchanged absent a separately evidenced defect. Negative tests cover
  replay of old #632 or #739 comments, reuse of specification approval, wrong
  issue, wrong login or author association, changed comment body or hash,
  binding drift, and continuation of a partial journal append only under the
  identical approval.
- **AC-746-07:** Spec traceability connects the issue, DE/EN specification, the
  later DE/EN plan, every AC ID, and concrete local and remote validation.
- **AC-746-08:** This draft PR performs no tenant, provider, credential, or live
  action. Local quarantine release and a new live run remain two separate,
  hash-bound owner gates.

## Validation Model

The manifest commands are not one platform-independent list to be executed
together. The native Windows path runs only the portable offline and
fail-closed suite. The POSIX BFF suite, activation validator, Graft, and strict
doctor run on the supported POSIX or `ubuntu-latest` path. The later plan must
record this assignment for every command in machine-readable form as
`windows_native`, `posix_local`, `ubuntu_remote_ci`, or `post_pr_remote`.

The plan must also maintain an AC evidence matrix:

`AC ID -> artifacts -> platform -> positive test -> negative test -> expected
status/error code -> local command -> remote check/evidence`.

At least one Issue #746-specific validator, or an equivalently narrow mapping to
exact existing test methods, validates provenance separation, preflight order,
zero write counters, redaction sentinels, every blocked branch, and all three
journal crash windows. A raw module or validator-name listing is insufficient.
The existing M365 live-activation validator is regression evidence but alone is
not evidence for every AC-746 criterion.

AC-746-01 additionally requires an independent semantic DE/EN review or a
shared normalized machine-readable state and gate table; the general language
parity validator alone is insufficient. AC-746-02 requires a redacted,
hash-bound provenance reference to the immutable GitHub comments or equivalent
owner-free read-only GitHub evidence; issue surfaces themselves explicitly
remain non-product state.

Before merge, the complete file list, commit list, and `base...head` diff are
reviewed. At minimum, `Privacy and Secrets Guard / secret-scan`, `Privacy and
Secrets Guard / privacy-lint`, and `NaC Quality Gate / quality-gate` must pass
remotely under those exact names. Missing, skipped, cancelled, or differently
named substitute checks block; the later `post_pr_remote` evidence evaluates
the structured check listing deterministically. Until the plan, implementation,
and this evidence exist, AC-746-01 through AC-746-08 remain open; the current
draft makes no acceptance claim.

## Stop Conditions

The sequence stops without mutation on an unsupported platform, dirty worktree,
missing or changed run binding, state, ledger, or lock integrity failure,
toolchain or binary drift, network-policy block, credential error, unknown
provider response, snapshot drift, an observed or not safely excluded
deployment, evidence that cannot be redacted, or failed independent review.

## Non-Goals

- no live retry or provider write in this PR;
- no resume, rollback, deletion, or manual unlock;
- no new or broader permission;
- no local bypass of central network policy;
- no Teams UI change that suppresses a legitimate denial;
- no claim that the Function App executes the new package;
- no production data or extension to another workspace.

## Review Gate

After independent scope, policy, validation, and language review, the owner must
explicitly approve this written specification. Only then is the DE/EN
implementation plan created and added to the manifest.
