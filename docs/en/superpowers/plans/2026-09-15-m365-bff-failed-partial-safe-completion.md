# Safe Completion of the Partial M365 BFF Activation - Implementation Plan

Status: Offline implementation in progress; expanded governance scope requires renewed hash-bound approval; acceptance `BLOCKED`

Date: 15 September 2026
Specification: [Safe Completion of the Partial M365 BFF Activation](../specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md)
Leading issue: [#746](https://github.com/notariat8/NaC/issues/746)
Draft PR: [#747](https://github.com/notariat8/NaC/pull/747)
Delivery Mode: Protected PR
Risk Gate: Human Approval

## Outcome and Boundary

The implementation delivers a verifiable offline orchestration and operations
contract for safely completing the partial activation documented in #739. It
does not invent a second reconciler: the existing central CLI edge
`nac m365 teams-sharepoint bff-azure-function-deployment-reconcile`, its
contract, validator, and tests remain the sole execution edge for inspection
and a later, separately approved local journal release.

This plan authorizes only repository changes, static validation, and synthetic
tests. It does not authorize a real read-only provider inspection, the local
quarantine release from issue #739, a new live run from issue #632,
authentication, or any tenant, provider, or credential write.

## Change Surfaces

| Surface | Planned artifacts | Purpose |
| --- | --- | --- |
| Issue-#746 contract | `workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml` | Normalize provenance, phases, gates, platforms, error codes, and the AC matrix |
| Narrow validator | `scripts/validate_m365_bff_failed_partial_safe_completion.py` | Enforce structure, the existing #739 edge, negative evidence, and complete AC mapping |
| Validator and operations tests | `tests/test_m365_bff_failed_partial_safe_completion.py` | Cover contract drift, gate replay, redaction, the zero-write boundary, and journal crash windows test-first |
| Existing regressions | existing #739, live CLI, and Windows portability tests | Prove the reconciler, ARM allowlist, release algorithm, and Windows fail-closed boundary remain unchanged |
| DE/EN documentation | specification and plan; CLI docs only if a gap is proven | Keep the operator sequence and separate approvals understandable |
| Traceability | `nac-spec-traceability` manifest in the DE/EN specification | Connect the issue, specifications, plans, ACs, and validation commands |
| AI SBOM | `sbom/ai/nac-ai-sbom-draft.json`, `sbom/ai/nac-ai-sbom-export-mapping.json` | Register the new agentic verification contract with its human-review, provider, evidence, and privacy boundaries; no release export |
| Account-to-principal governance | workflow, root `AGENTS.md`, DE/EN role model, access/role policies, identity registry and schema, onboarding, validator, and tests | Bring the repair already present in the PR fully into scope and traceability; account strings must not fake principal separation |

Changes to the production reconciler, ARM allowlist, release algorithm,
tenant/provider adapters, credentials, Teams UI, or permissions are not
planned. If a red test proves a defect there, implementation stops; the defect
is submitted separately with a new scope and risk-gate review.

## Binding Phase and Gate Table

These phases describe orchestration and are not new persisted run states. The
old run remains `FAILED_PARTIAL`.

| Phase | Permitted inputs | Permitted action | Success | Otherwise | Mutation |
| --- | --- | --- | --- | --- | --- |
| 0 Spec/plan | approved specification commit and repository evidence | static validation, synthetic tests, protected PR | `OFFLINE_PLAN_VERIFIED` | `BLOCKED` | Git/PR artifacts only |
| 1 POSIX preflight | fresh local #739 artifacts on a supported POSIX host | read bindings and integrity | `POSIX_READY` | `BLOCKED` | none |
| 2 Provider inspection | `POSIX_READY`, permitted network targets, existing authentication context | two bound ARM GET snapshots | `FUNCTION_DEPLOYMENT_NOT_APPLIED` | `BLOCKED` | none |
| 3 Local journal release | phase-2 evidence and a new exact #739 owner comment | `--confirm-release-quarantine` | `LOCK_JOURNALS_RELEASED` | `BLOCKED` | three deterministic append-only `RELEASED` records |
| 4 New offline gate | clean new commit/tree after phase 3 | create a new #632 activation package | `NEW_OFFLINE_OWNER_GATE_REQUIRED` | `BLOCKED` | local offline evidence |
| 5 Live run | new, exactly hash-bound #632 approval | exactly one controlled live run | existing live-contract states | `BLOCKED` or an existing error state | only as separately approved |

Only phase 0 is executed against repository and PR artifacts in this PR.
Phases 1 through 5 are not invoked against the current #739 artifacts or any
credential, network, tenant, or provider state. Their contracts, success
paths, and blocking paths are exercised offline using synthetic fixtures and
ports only. Specification approval is not a valid input for phase 3 or 5.

## Platform and Command Matrix

| Platform ID | Commands | Purpose | Permitted side-effect edges |
| --- | --- | --- | --- |
| `windows_native` | Windows portability suite, issue-#746 test, and portable validators | Offline import, static contract, early fail-closed behavior | no credential, state, lock, network, subprocess, tenant, or provider edge |
| `posix_local` | targeted #739/live-CLI tests, issue-#746 test, and activation validator | POSIX security and regression contracts | synthetic local fixtures only; no real provider calls |
| `ubuntu_remote_ci` | Graft, strict doctor, and full CI tests | authoritative Linux aggregate evidence | CI source access; no secrets, logins, or live calls |
| `post_pr_remote` | structured PR check query and complete `base...head` diff | prove protected delivery | read-only GitHub metadata |

On Windows, live, recovery, and both reconciliation edges continue to return
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE`, `status: BLOCKED`, and
`writes_started: false` before reaching a forbidden side-effect edge.

## Machine-Readable Validation Assignment

The following IDs are the binding resolution of the command and AC matrices.
Every command belongs to exactly one platform; `acceptance_ids` and
`remote_evidence` make its evidence machine-readable.

```nac-validation-matrix
schema_version: nac.issue-746-validation-plan/v0.1
commands:
  - id: spec_traceability
    platform: windows_native
    command: python scripts/validate_spec_traceability.py
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: language_parity
    platform: windows_native
    command: python scripts/validate_language_parity.py
    acceptance_ids: [AC-746-01]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: doc_links
    platform: windows_native
    command: python scripts/validate_doc_links.py
    acceptance_ids: [AC-746-01, AC-746-07]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: issue746_validator
    platform: windows_native
    command: python scripts/validate_m365_bff_failed_partial_safe_completion.py
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: ai_sbom
    platform: ubuntu_remote_ci
    command: python scripts/validate_ai_sbom.py
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: ai_sbom_export_mapping
    platform: ubuntu_remote_ci
    command: python scripts/validate_ai_sbom_export_mapping.py
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: issue746_windows_tests
    platform: windows_native
    command: python -m unittest tests.test_windows_offline_cli_portability tests.test_spfx_bff_catalog_readback_regression tests.test_m365_bff_failed_partial_safe_completion
    acceptance_ids: [AC-746-02, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: issue746_posix_tests
    platform: posix_local
    command: PYTHONPATH=src python3 -m unittest tests.test_m365_bff_failed_partial_safe_completion tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
    acceptance_ids: [AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: activation_validator
    platform: posix_local
    command: python scripts/validate_m365_azure_bff_live_activation.py
    acceptance_ids: [AC-746-03, AC-746-04, AC-746-05, AC-746-06]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: graft_build
    platform: ubuntu_remote_ci
    command: graft build
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: graft_check
    platform: ubuntu_remote_ci
    command: graft check
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: strict_doctor
    platform: ubuntu_remote_ci
    command: python scripts/nac.py doctor --profile strict
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: fetch_main
    platform: post_pr_remote
    command: git fetch --no-tags --prune origin main
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [fresh origin/main]
  - id: diff_files
    platform: post_pr_remote
    command: git diff --name-status origin/main...HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [complete file list]
  - id: diff_commits
    platform: post_pr_remote
    command: git log --oneline origin/main..HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [complete commit list]
  - id: diff_patch
    platform: post_pr_remote
    command: git diff origin/main...HEAD
    acceptance_ids: [AC-746-01, AC-746-07, AC-746-08]
    remote_evidence: [complete base...head patch]
  - id: diff_whitespace
    platform: post_pr_remote
    command: git diff --check origin/main...HEAD
    acceptance_ids: [AC-746-07]
    remote_evidence: [complete base...head whitespace check]
  - id: pr_checks_watch
    platform: post_pr_remote
    command: gh pr checks 747 --watch
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [Privacy and Secrets Guard / secret-scan, Privacy and Secrets Guard / privacy-lint, NaC Quality Gate / quality-gate, NaC Windows Portability / windows-offline-cli]
  - id: pr_checks_enforced
    platform: post_pr_remote
    command: python scripts/validate_m365_bff_failed_partial_safe_completion.py --verify-pr-checks --expected-pr 747 --expected-head-from-local-git HEAD --protected-identity-resolver-file <repo-external-json> --protected-identity-resolver-sha256 <sha256> --operator-account-id <provider-qualified-operator-account> --owner-solo-approval-reference <issue-746-comment-url>
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [exact required check names and successful states]
```

Every `commands` entry is additionally materialized in the planned
verification contract with `scope` and `side_effect_class`. Permitted values
are:

- `scope: repository_static` and `side_effect_class: local_read_or_synthetic`
  for `windows_native` and `posix_local`;
- `scope: repository_aggregate` and `side_effect_class: ci_read_or_synthetic`
  for `ubuntu_remote_ci`;
- `scope: pr_747_expected_head` and
  `side_effect_class: github_read_only` for `post_pr_remote`.

A different or missing assignment blocks the #746 validator. On this host the
canonical `python` command is executed with the Python 3.11 interpreter
provided by the Codex workspace because no supported interpreter is available
on the process `PATH`; CI must continue to resolve `python` reproducibly from
its configured Python 3.11.

## Test-First Sequence

### 1. Issue-#746 contract and initially red validator tests

- Add a dedicated verification contract with a stable schema version,
  `leading_issue`, specification/plan paths, all AC IDs, four platform IDs,
  and the complete phase/gate table.
- First make tests red for missing AC mappings, merged #632/#739 gates, a
  GitHub issue presented as runtime state, and a permitted Windows live edge.
- Store only canonical identifiers and hash requirements; no real tenant or
  subscription IDs, hostnames, credential values, raw responses, or local
  secret paths.

### 2. Enforce provenance and three non-interchangeable approvals

- Normalize #620, #632, #739, and #743 with distinct roles; GitHub references
  are provenance, never current product state.
- Require three distinct gate IDs: `SPEC_746_APPROVAL`,
  `ISSUE_739_QUARANTINE_RELEASE`, and `ISSUE_632_NEW_LIVE_RUN`.
- Negative tests vary issue, login, author association, comment body, or
  comment hash and expect `BLOCKED` before mutation.
- Old #632/#739 comments, the specification comment, and cross-issue replay
  must explicitly fail.

### 3. Model the complete local POSIX preflight

- Require state, evidence, ledger, three lock journals, prepared manifest,
  function ZIP, activation/correlation binding, commit, tree, target, and
  toolchain/binaries.
- Check existence, ownership/permissions, no-follow, canonical path, and hash
  binding before network or provider access.
- Remove or alter each binding in turn; expect `BLOCKED`, a provider-read count
  of `0`, and a write count of `0`.

### 4. Bind the read-only decision table to the existing #739 edge

- Validate the exact CLI name and the existing double ARM GET inspection.
- Only two identical, fully allowlisted projections with
  `FUNCTION_DEPLOYMENT_NOT_APPLIED` may complete phase 2 successfully.
- A deployment signal, missing/unknown field, snapshot drift, redirect,
  authentication error, network block, timeout, or non-redactable output
  yields `BLOCKED`.
- Synthetic ports prove `provider_write_calls: 0`, `tenant_write_calls: 0`,
  and `credential_write_calls: 0`.

### 5. Verify the redaction and output contract

- Permit only status, a stable error code, defined counters, and canonical
  hashes.
- Inject unique synthetic sentinels into provider response, exception,
  standard output, standard error, log, temporary artifact, and proposed
  approval text, telemetry, and shell history; no sentinel may reach an output
  sink.
- Unknown or not safely redactable fields block at every individual sink.

### 5a. Make Status, Error-Code, and Counter Semantics Exact

- The historical run remains `FAILED_PARTIAL`; its existing public field
  `writes_started: true` means only that the old run had started write steps
  before reconciliation. It is not a write counter for the current inspection.
- Successful pure inspection continues to return exactly
  `FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED`, two equal snapshots, and the
  classification `FUNCTION_DEPLOYMENT_NOT_APPLIED`.
- The existing `stable_error_codes_exact` contract section remains exact at
  least for the owner/release gates:
  `FUNCTION_DEPLOYMENT_CONFIRMATION_REQUIRED`,
  `FUNCTION_DEPLOYMENT_APPROVAL_ARGUMENTS_REQUIRED`,
  `FUNCTION_DEPLOYMENT_APPROVAL_ARGUMENTS_INVALID`,
  `FUNCTION_DEPLOYMENT_APPROVAL_INVALID`,
  `FUNCTION_DEPLOYMENT_APPROVAL_MISMATCH`,
  `FUNCTION_DEPLOYMENT_RECONCILIATION_UNSUPPORTED`,
  `FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_DRIFT`,
  `AZURE_FUNCTION_DEPLOYMENT_NOT_APPLIED_NOT_PROVEN`,
  `FUNCTION_DEPLOYMENT_LOCAL_ARTIFACT_CHANGED`,
  `FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED`, and
  `OWNER_COMMENT_VERIFICATION_FAILED`. The full allowed set is not derived
  from this subset: the new validator structurally links
  `stable_error_codes_exact`, `_OBSERVATION_ERROR_CODES`, every literal or
  dynamically reachable `_blocked` branch in the existing #739 module, and
  `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`. Any case-unbound addition, removal,
  or emission of a foreign code blocks.
- Test/validation evidence only, not the public runtime payload, receives
  separate counters and byte snapshots:
  `current_invocation_local_mutation_count`, `provider_read_snapshot_count`,
  `provider_write_count`, `tenant_write_count`, `credential_write_count`,
  `lock_call_count`, `network_call_count`, `subprocess_count`, plus before/after
  hashes for state, evidence, ledger, marker, and all three journals.
- On a preflight block all counters are `0` and all bytes are unchanged. During
  inspection, local and all write counters are `0`, exactly two snapshots are
  permitted, and network/subprocess use is allowed only by the existing narrow
  adapter contract. During a later approved journal mutation, only the three
  deterministic local appends are permitted; provider, tenant, and credential
  writes remain `0`.

### 5b. Protect Credential State at the Real Adapter Contract

- Before phase 2, capture the existing Azure CLI configuration tree with
  no-follow, owner, byte, and metadata binding. Execution receives only a
  private, read-only bound snapshot; host credential and configuration files
  must not be writable.
- Interactive login, device code, token refresh, cache creation, configuration
  rewrite, or any other persistence must fail closed before or at the adapter.
  Before/after hashes and host-state metadata must remain identical.
- The new test
  `test_credential_config_boundary_blocks_refresh_and_preserves_host_state`
  uses only synthetic credential sentinels and a fake Azure process attempting
  refresh/cache writes; it expects `BLOCKED`, `credential_write_count: 0`, no
  sentinel sink, and unchanged host bytes.
- If the existing adapter cannot prove this guarantee, phase 2 remains
  blocked. A production-code change is submitted as a separate scope and
  risk-gate finding and is not silently added to #746.

### 6. Regressively verify journal release and crash windows

- Write no new release code. The existing tests
  `test_exact_approval_releases_locks_without_changing_failed_run`,
  `test_wrong_owner_or_hash_never_releases_a_lock`, and
  `test_crash_after_lock_append_is_recovered_idempotently` are mandatory
  evidence.
- Require three crash windows: before the first append, after a true prefix of
  the three deterministic appends, and after all three appends before return.
- Only the same unchanged #739 approval hash may idempotently complete a true
  prefix. An unknown tail, different order, or different approval blocks; the
  old run remains `FAILED_PARTIAL`.

### 7. Complete regressions, traceability, and review

- Windows keeps offline import available; live, recovery, interruption, and
  function-deployment reconciliation block before parser details and backend.
- POSIX security semantics, ARM allowlist, and #739 tests remain unchanged and
  green. A production-code or allowlist change is a scope stop.
- Keep DE/EN plan and specification manifest synchronized. Every AC row maps
  artifact, platform, positive/negative test, status/error code, local command,
  and remote evidence.
- Scope, policy, validation, and DE/EN parity reviews inspect the complete
  `base...head` diff; high/medium findings are fixed and re-reviewed.
- No Gantt change: this planning stage changes no roadmap, milestone, or pilot
  status.

## Binding New Test Methods and Case IDs

The new issue-#746 validator requires the following exact methods in
`tests/test_m365_bff_failed_partial_safe_completion.py` and maps them to the
ACs. Matrix methods must execute every listed case ID as a named subtest; a
module or method name alone is insufficient.

| Method | Required case IDs | AC |
| --- | --- | --- |
| `test_contract_maps_every_acceptance_id_to_platform_command_and_evidence` | `AC-746-01` through `AC-746-08` | all |
| `test_provenance_roles_are_distinct_and_not_runtime_state` | `issue620_parent`, `issue632_live_contract`, `issue739_current_trail`, `issue743_historical_interruption` | AC-746-02 |
| `test_approval_replay_matrix_blocks_before_mutation` | `old_632_comment`, `old_739_comment`, `spec_746_comment`, `wrong_issue`, `wrong_login`, `wrong_author_association`, `changed_body`, `changed_hash`, `cross_issue_replay`, `owner_approved`, `owner_approval_reference`, `approval_body_sha256` | AC-746-02, AC-746-06, AC-746-08 |
| `test_registry_approval_mode_is_source_bound_before_release` | `missing_process_role`, `missing_approval_role`, `inactive_identity`, `login_registry_mismatch`, `missing_operator`, `association_only`, `no_external_requirement_single_principal`, `binding_external_requirement_single_principal`, `binding_external_requirement_same_principal_accounts`, `binding_external_requirement_distinct_principals`, `incomplete_requirement_assessment`, `unsupported_requirement_source_type` | AC-746-06, AC-746-08 |
| `test_preflight_binding_drift_matrix_blocks_before_provider` | `action`, `activation_hash`, `state_sha256`, `evidence_sha256`, `ledger_head_sha256`, `target_lock_sha256`, `legacy_lock_sha256`, `legacy_host_lock_sha256`, `provider_observation_sha256`, `failed_step`, `failed_step_started_at_utc`, `prepared_inputs_manifest_sha256`, `function_package_sha256`, `reconciler_commit`, `reconciler_tree`, `reconciler_toolchain_sha256`, `required_owner_login`, `correlation_id`, `target`, `binary`, `owner_permissions`, `nofollow_path`, `concurrent_lock` | AC-746-03 |
| `test_double_snapshot_accepts_only_stable_not_applied` | `stable_not_applied` | AC-746-04 |
| `test_provider_decision_block_matrix_has_zero_writes` | `deployment_applied`, `missing_field`, `unknown_field`, `snapshot_drift`, `redirect`, `auth_error`, `network_block`, `timeout`, `non_redactable` | AC-746-04, AC-746-08 |
| `test_redaction_sentinel_matrix_never_reaches_any_sink` | `provider_response`, `exception`, `stdout`, `stderr`, `log`, `temporary_artifact`, `approval_text`, `telemetry`, `shell_history`, each with `unknown_field` | AC-746-04, AC-746-06, AC-746-08 |
| `test_credential_config_boundary_blocks_refresh_and_preserves_host_state` | `interactive_login`, `device_code`, `token_refresh`, `cache_create`, `config_rewrite`, `host_bytes_changed`, `host_metadata_changed` | AC-746-04, AC-746-08 |
| `test_status_error_counter_and_hash_matrix_is_exact` | `historic_writes_started_not_current_write`, `inspection_required_status`, `not_applied_classification`, `stable_contract_codes_exact`, `observation_codes_exact`, `all_blocked_branches_case_bound`, `foreign_code_rejected`, `error_platform_backend_unavailable`, `preflight_all_counters_zero`, `inspection_two_snapshots_zero_mutations`, `release_three_local_appends_only`, `state_hash_unchanged`, `evidence_hash_unchanged`, `ledger_hash_unchanged`, `marker_hash_expected`, `three_journal_hashes_expected`, `network_and_subprocess_counts_bounded` | AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-08 |
| `test_windows_matrix_blocks_before_every_side_effect_edge` | `live`, `recovery`, `interruption_reconciliation`, `function_deployment_reconciliation`; each with `credential`, `state`, `lock`, `network`, `subprocess`, `tenant`, `provider` | AC-746-05 |
| `test_crash_before_first_append_keeps_all_journals_held` | `before_first_append` | AC-746-06 |
| `test_crash_after_true_prefix_completes_only_with_same_approval` | `after_first_append`, `after_second_append`, `changed_approval`, `unknown_tail`, `wrong_order` | AC-746-06 |
| `test_crash_after_all_appends_returns_idempotent_release` | `after_third_append_before_return`, `same_approval_replay` | AC-746-06 |
| `test_owner_comment_loader_verifies_live_canonical_provenance` | canonical final-head-bound owner comment plus body, login, association, and URL drift | AC-746-02, AC-746-08 |
| `test_protected_evidence_loader_rejects_unsafe_posix_inputs` | exact mode `0600`, size, JSON/UTF-8 boundaries, leaf/parent symlink rejection, and parent replacement while the directory descriptor is held | AC-746-02, AC-746-08 |
| `test_protected_identity_resolver_requires_three_same_principal_accounts` | repository-external resolver, exactly three active account bindings, one shared principal, role, and qualification | AC-746-02, AC-746-08 |
| `test_unknown_tail_and_wrong_order_block_without_further_release` | `unknown_tail`, `wrong_order`, byte-identical artifacts after blocked retry | AC-746-06 |
| `test_remote_verifier_errors_are_stable_and_redacted` | Git/PR read and JSON failures return stable codes without raw diagnostics | AC-746-02, AC-746-07, AC-746-08 |
| `test_verify_pr_checks_cli_requires_and_forwards_all_identity_inputs` | resolver path, resolver digest, operator account, and owner comment are jointly required and forwarded unchanged | AC-746-02, AC-746-07, AC-746-08 |
| `test_required_remote_checks_match_exact_context_names` | `pr_747`, `local_head_source`, `wrong_local_head`, `secret_scan`, `privacy_lint`, `quality_gate`, `windows_offline_cli`, `missing`, `duplicate`, `non_success`, `skipped`, `cancelled`, `renamed` | AC-746-07, AC-746-08 |
| `test_ai_sbom_registers_issue746_agentic_contract_without_release_export` | `human_review_owner`, `provider_boundary`, `evidence_binding`, `privacy_boundary`, `release_export_disabled` | AC-746-07, AC-746-08 |

The three exactly named #739 regression tests from step 6 also remain
mandatory. The new crash-window evidence adds “before the first append” and
“after all three appends before return” without changing the existing release
algorithm.

## AC Evidence Matrix

| AC | Artifacts | Platform | Positive test | Negative test | Expected result | Local | Remote |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC-746-01 | DE/EN specification and plan, normalized tables | Windows, Ubuntu | language validator and parity review | divergent gate row | equal or `BLOCKED` | `language_parity`, `doc_links`, `diff_patch` | `NaC Quality Gate / quality-gate`, review |
| AC-746-02 | issue-#746 contract | Windows, POSIX | distinct issue roles | old comment, wrong issue, replay | `BLOCKED`, writes `0` | `issue746_validator`, `issue746_windows_tests`, `issue746_posix_tests` | `NaC Quality Gate / quality-gate` |
| AC-746-03 | contract, existing #739 reconciler | POSIX | complete binding matrix | missing/divergent binding | `POSIX_READY` or `BLOCKED`, reads `0` on failure | `issue746_posix_tests`, `activation_validator` | `NaC Quality Gate / quality-gate` |
| AC-746-04 | reconciler, live contract, validator | POSIX | two identical NOT_APPLIED snapshots | Applied, Unknown, Drift, Redirect, Auth/Policy/Timeout | only `FUNCTION_DEPLOYMENT_NOT_APPLIED` or `BLOCKED`; writes `0` | `issue746_posix_tests`, `activation_validator` | `NaC Quality Gate / quality-gate` |
| AC-746-05 | Windows facade and portability suite | Windows | offline import | four blocked edges | platform code, writes `0` | `issue746_windows_tests`, `activation_validator` | `NaC Windows Portability / windows-offline-cli` |
| AC-746-06 | plan, contract, validator, tests | all | complete matrix | replay, sentinel, drift, three crash windows | defined success or `BLOCKED` | `issue746_validator`, `issue746_windows_tests`, `issue746_posix_tests`, `activation_validator` | Quality/Windows per command matrix |
| AC-746-07 | both specification manifests | all | links, ACs, commands resolve | missing plan/AC/command | green or `BLOCKED` | `spec_traceability`, `doc_links`, `graft_build`, `graft_check`, `strict_doctor`, all `post_pr_remote` IDs | exact structured PR checks |
| AC-746-08 | complete PR diff and guards | all | offline artifacts, synthetic tests | real tenant/provider/credential/live call | counts `0` | `issue746_validator`, both issue-#746 test IDs, `strict_doctor`, all diff/PR IDs | all four exact required checks |

## Validation Commands

Native Windows offline validation:

```powershell
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python scripts/validate_m365_bff_failed_partial_safe_completion.py
python -m unittest tests.test_windows_offline_cli_portability tests.test_spfx_bff_catalog_readback_regression tests.test_m365_bff_failed_partial_safe_completion
```

Supported POSIX/Ubuntu path using synthetic ports only:

```bash
PYTHONPATH=src python3 -m unittest tests.test_m365_bff_failed_partial_safe_completion tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli
python scripts/validate_m365_azure_bff_live_activation.py
python scripts/validate_ai_sbom.py
python scripts/validate_ai_sbom_export_mapping.py
graft build
graft check
python scripts/nac.py doctor --profile strict
```

Protected PR evidence:

```bash
git fetch --no-tags --prune origin main
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
git diff origin/main...HEAD
git diff --check origin/main...HEAD
gh pr checks 747 --watch
python scripts/validate_m365_bff_failed_partial_safe_completion.py --verify-pr-checks --expected-pr 747 --expected-head-from-local-git HEAD --protected-identity-resolver-file <repo-external-json> --protected-identity-resolver-sha256 <sha256> --operator-account-id <provider-qualified-operator-account> --owner-solo-approval-reference <issue-746-comment-url>
```

Required contexts include at least `Privacy and Secrets Guard / secret-scan`,
`Privacy and Secrets Guard / privacy-lint`, `NaC Quality Gate / quality-gate`,
and, for the Windows boundary, `NaC Windows Portability / windows-offline-cli`.
Missing, skipped, cancelled, or renamed means not passed.
The final command obtains the expected SHA only through an internal read-only
`git rev-parse HEAD`, then reads PR #747 with
`gh pr view 747 --json number,headRefOid,statusCheckRollup,reviewDecision,latestReviews` and enforces exactly
one instance of every required context, successful state, and
`local HEAD == headRefOid`. It must not copy the expected SHA from the same PR
response.

## Binding Acceptance Gate

Specification approval at commit `012c441b...` authorizes writing and reviewing
this plan, but it is not a #739 release or #632 live approval. Before later
implementation acceptance, a repository-external, access-controlled identity
resolver must resolve the real gate identities and prove active
`prozessverantwortung` plus the `process_design` qualification for solo-owner
authority. The versioned public registry contains unmistakably synthetic
examples only. The protected resolver must bind exactly three active known
accounts to the same principal; multiple accounts of the same principal never
satisfy four-eyes or separation of duties.
Issue #746 has no applicable statutory, regulatory, contractual, or binding
security obligation requiring two different natural persons with a concrete
source reference and scope. The active principal holding the owner role and
qualification may
therefore record an audit-proof `OWNER_SOLO_APPROVAL`. This decision is not
four-eyes approval. A role label or GitHub association alone does not create a
two-person obligation.

If such an external obligation is bound as applicable, it must carry a source
type, stable source ID, concrete citation, version, canonical digest, and scope.
When only one qualified principal is then
available, the result is `BLOCKED_SINGLE_PRINCIPAL`; different accounts of that
principal do not change the result. Only two active, appropriately qualified,
distinct principals may produce `FOUR_EYES_APPROVAL`. Incomplete or unknown
source evidence blocks as `BLOCKED_REQUIREMENT_ASSESSMENT_INVALID`.

`required_owner_login` is only a hash-bound provider transport attribute. It
grants no governance authority. For acceptance, the provider-qualified account
is resolved through the registry to an active principal with
`prozessverantwortung` and `process_design`. Whether an additional distinct
principal with `freigabeverantwortung` is required is decided solely by the
source-bound two-person assessment described above.

The protected resolver remains outside the repository, must be owned by the
executing POSIX user with exact mode `0600`, is traversed component by component
through held directory descriptors and read through a no-follow leaf descriptor,
is bounded to 128 KiB, rejects duplicate JSON keys, and is bound by SHA-256 to the
final-head-bound owner comment. Account and principal IDs appear there only as
purpose-separated SHA-256 bindings; raw resolver values remain in memory only.
Neither real account identifiers nor resolver contents may enter the repository,
CI output, or evidence. Provider-identity resolution remains separate evidence
for every later issue-#739 quarantine
release or issue-#632 live run; the PR gate replaces neither separate gate.

The original scope approved at `012c441b...` does not cover the combined
account-to-principal repair and the now complete artifact allowlist. This
expanded scope requires renewed approval bound to the exact implementation
commit.

The credential, redaction, #739 hash, and dynamic error-code matrices remain
`pending` rather than passed until executable evidence exists. The offline
contract may be structurally valid while its acceptance remains `BLOCKED`.

## Stop Conditions

Implementation stops for a change outside the offline artifacts, a required
production-code fix, real runtime/provider data in the repository or GitHub,
missing DE/EN parity, incomplete AC mapping, a red required check, or an
attempt to use specification approval as a #739 or #632 gate.

After `implement -> review -> fix`, the PR ends before any real reconciliation.
The next approval is submitted separately only from fresh, redacted,
hash-bound evidence.
