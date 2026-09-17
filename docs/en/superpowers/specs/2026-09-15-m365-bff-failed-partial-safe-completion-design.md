# Safe Windows Completion of the Partial M365 BFF Activation

Status: specification and plan approved by the owner; local Windows implementation in progress; operational execution blocked

Date: 17 September 2026

Leading issue: [#746](https://github.com/notariat8/NaC/issues/746)

Implementation plan to be revised: [Safe Completion of the Partial M365 BFF Activation](../plans/2026-09-15-m365-bff-failed-partial-safe-completion.md)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-failed-partial-safe-completion
leading_issue: https://github.com/notariat8/NaC/issues/746
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Platform
  - Security
affected_artifacts:
  - .github/workflows/governance-policy-sync.yml
  - .github/workflows/windows-portability.yml
  - agent-context/index.json
  - AGENTS.md
  - assets/docs/generic-workbench/VIS-721-manifest.json
  - docs/de/cli.md
  - docs/de/minimum-requirements.md
  - docs/de/role-model.md
  - docs/de/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
  - docs/de/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - docs/en/cli.md
  - docs/en/minimum-requirements.md
  - docs/en/role-model.md
  - docs/en/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md
  - docs/en/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md
  - policies/access-control-policy.yaml
  - policies/github-identity-registry.json
  - policies/github-identity-registry.schema.json
  - policies/process-policy.yaml
  - policies/role-model-policy.yaml
  - sbom/ai/nac-ai-sbom-draft.json
  - sbom/ai/nac-ai-sbom-export-mapping.json
  - scripts/onboarding_wizard.py
  - scripts/quality_gate.py
  - scripts/validate_agent_authentication_boundary.py
  - scripts/validate_business_case_type_azure_blob_worm.py
  - scripts/validate_business_case_type_graph_write_edge.py
  - scripts/validate_generic_workbench_foundation.py
  - scripts/validate_graft_context_layer.py
  - scripts/validate_identity_registry.py
  - scripts/validate_m365_azure_bff_live_activation.py
  - scripts/validate_m365_azure_bff_performance_acceptance.py
  - scripts/validate_m365_bff_failed_partial_safe_completion.py
  - scripts/validate_m365_release_readiness_gate.py
  - scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - scripts/validate_microsoft_first_onprem_target_architecture.py
  - scripts/validate_notarial_application_interface_inventory.py
  - scripts/validate_xnotar_xjustiz_package_boundary.py
  - src/nac_ai_sbom/export_mapping.py
  - src/nac_bff/activation_security_backend.py
  - src/nac_bff/activation_security_linux.py
  - src/nac_bff/activation_security_windows.py
  - src/nac_bff/approved_git_tree.py
  - src/nac_bff/azure_activation_attestations.py
  - src/nac_bff/azure_activation_composition.py
  - src/nac_bff/azure_activation_contract.py
  - src/nac_bff/azure_activation_provisioner_bootstrap.py
  - src/nac_bff/azure_activation_runner.py
  - src/nac_bff/azure_activation.py
  - src/nac_bff/azure_interruption_baseline.py
  - src/nac_bff/azure_interruption_reconciliation.py
  - src/nac_bff/azure_live_commands_win.py
  - src/nac_bff/azure_live_commands.py
  - src/nac_bff/azure_performance_acceptance.py
  - src/nac_bff/azure_performance_authorization.py
  - src/nac_bff/azure_performance_infrastructure_safety.py
  - src/nac_bff/azure_performance_lease_broker_auth.py
  - src/nac_bff/azure_performance_lease.py
  - src/nac_bff/azure_performance_owner_gate.py
  - src/nac_bff/azure_performance_runtime.py
  - src/nac_bff/azure_performance_storage_ports.py
  - src/nac_cli/cli.py
  - src/nac_m365_graph/business_case_type_production_adapters.py
  - src/nac_m365_graph/business_case_type_production_composition.py
  - src/nac_m365_graph/business_case_type_write_state.py
  - src/nac_m365_graph/mvp_test_environment_deploy.py
  - src/nac_m365_graph/node_runtime_integrity.py
  - src/nac_m365_graph/sealed_toolchain.py
  - src/nac_m365_graph/spfx_site_deployment.py
  - src/nac_runtime/platform_file_lock.py
  - src/nac_runtime/sqlite_evidence_staging_outbox.py
  - src/notary_kg/business_case_type_migration_quarantine.py
  - src/notary_kg/business_case_type_migration_runner.py
  - src/notary_kg/pilot_checklist.py
  - src/notary_kg/workflow_contract.py
  - tests/test_activation_security_backend.py
  - tests/test_activation_security_windows.py
  - tests/test_agent_authentication_boundary.py
  - tests/test_business_case_type_graph_write_composition.py
  - tests/test_business_case_type_graph_write_crash_recovery.py
  - tests/test_business_case_type_graph_write_state_store.py
  - tests/test_business_case_type_migration_cli.py
  - tests/test_business_case_type_migration_quarantine.py
  - tests/test_business_case_type_production_adapters.py
  - tests/test_business_case_type_production_composition.py
  - tests/test_codex_agent_context_index_audit.py
  - tests/test_graft_context_layer.py
  - tests/test_identity_registry.py
  - tests/test_m365_azure_bff_live_activation_contract.py
  - tests/test_m365_bff_failed_partial_safe_completion.py
  - tests/test_m365_mvp_test_environment_deploy.py
  - tests/test_m365_sharepoint_bpmn_viewer_adapter.py
  - tests/test_nac_bff_approved_git_tree.py
  - tests/test_nac_bff_azure_activation_attestations.py
  - tests/test_nac_bff_azure_activation_composition.py
  - tests/test_nac_bff_azure_activation_owner_gate.py
  - tests/test_nac_bff_azure_activation_provisioner_bootstrap.py
  - tests/test_nac_bff_azure_activation_runner.py
  - tests/test_nac_bff_azure_function_deployment_reconciliation.py
  - tests/test_nac_bff_azure_interruption_baseline.py
  - tests/test_nac_bff_azure_interruption_reconciliation.py
  - tests/test_nac_bff_azure_live_commands.py
  - tests/test_nac_bff_azure_performance_acceptance.py
  - tests/test_nac_bff_azure_performance_authorization.py
  - tests/test_nac_bff_azure_performance_infrastructure_safety.py
  - tests/test_nac_bff_azure_performance_lease_broker_auth.py
  - tests/test_nac_bff_azure_performance_owner_gate.py
  - tests/test_nac_bff_azure_performance_runtime.py
  - tests/test_nac_bff_azure_performance_storage_ports.py
  - tests/test_nac_m365_node_runtime_integrity.py
  - tests/test_nac_m365_sealed_toolchain.py
  - tests/test_notarkammer_demo_runtime_seed.py
  - tests/test_notary_kg.py
  - tests/test_platform_file_lock.py
  - tests/test_sqlite_evidence_staging_outbox.py
  - tests/test_validate_generic_workbench_foundation.py
  - tests/test_validate_windows_offline_cli_portability.py
  - tests/test_windows_offline_cli_portability.py
  - tests/test_xnotar_xjustiz_package_boundary.py
  - workflows/contracts/m365-azure-bff-live-activation.contract.json
  - workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml
  - workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml
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
  - python scripts/validate_ai_sbom.py
  - python scripts/validate_m365_bff_failed_partial_safe_completion.py
  - python scripts/validate_m365_azure_bff_live_activation.py
  - python -m unittest discover -s tests -p test_activation_security*.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git diff --check origin/main...HEAD
```

## Purpose and Boundary

This specification replaces the local POSIX prerequisite in the previous
Issue #746 design with a complete native Windows path. Every mandatory local
development, build, test, packaging, reconciliation, approval, and deployment-
control step must work on the Windows 11 workstation. WSL, Docker, SBX, a Linux
VM, or a separate Linux runner is neither a prerequisite nor a fallback.

Linux remains allowed only inside the Azure target environment. The Azure
Function may run as `functionapp,linux`, and Azure OneDeploy may materialize
Linux-native dependencies in the bound remote build. This creates no local
Linux dependency.

The specification also defines the safe path from the documented partial state
to a possible new, separately approved live run for the exclusively synthetic
workspace `notary_team_01`. It does not itself authorize a provider write, the
Issue #739 quarantine release, a live retry, or an Issue #632 live run.

The visible Teams message `Kein Zugriff auf diesen Arbeitsbereich` must not be
fixed through a UI bypass. Completion must prove the chain
`Teams/SPFx -> AadHttpClient -> Entra-protected BFF -> server-side access gate
-> Microsoft Graph REST v1.0`.

## Binding Platform Boundary

```yaml
local_development_platform: windows
local_build_platform: windows
local_test_platform: windows
local_packaging_platform: windows
local_reconciliation_platform: windows
local_deployment_control_platform: windows
local_live_activation_control_platform: windows
wsl_required: false
docker_required: false
linux_host_required: false
posix_runner_required: false
azure_function_runtime:
  linux_allowed: true
azure_remote_build:
  linux_allowed: true
linux_ci:
  allowed: true
  required_gate: false
  may_block_windows_delivery: false
```

An optional Linux CI run may check compatibility with the permitted Azure Linux
runtime only. It does not replace Windows evidence and must not independently
block Windows delivery.

The [Microsoft-first, on-prem AI target architecture](../../architecture/microsoft-first-onprem-target-architecture.md)
remains unchanged: Microsoft 365 forms the user, identity, and data edge; local
NaC workstations and development run on Windows; Azure services may use their
managed Linux runtime.

## Provenance and Current Starting State

GitHub surfaces are not product or runtime state. The following issues have
separate roles:

- [#620](https://github.com/notariat8/NaC/issues/620) is historical provenance
  for the visible M365 MVP test environment.
- [#632](https://github.com/notariat8/NaC/issues/632) remains the governing
  contract and separate approval surface for a new live run.
- [#739](https://github.com/notariat8/NaC/issues/739) contains the current
  quarantined run trail. The documented run
  `nac-bff-live-20260908-issue739-v4` ended at step 7
  `deploy_function_package` with
  `AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS`.
- [#743](https://github.com/notariat8/NaC/issues/743) is a different historical
  interruption and must not be used to reconstruct #739.
- [#744](https://github.com/notariat8/NaC/issues/744) introduced the portable
  Windows offline CLI and the current Linux-only live restriction. That
  restriction remains fail-closed until the Windows implementation is
  validated, but is no longer the target architecture.
- [#746](https://github.com/notariat8/NaC/issues/746) governs the secure Windows
  migration and later completion chain.

Old evidence or old comments are not current approval. Local and provider state
remains `UNVERIFIED` and therefore `BLOCKED` until the new Windows preflight and
double read-only inspection freshly pass.

## Evaluated Approaches

### A. Windows-native control path with an Azure Linux target — selected

The complete local flow is secured on Windows. The controller creates bound
input packages and controls Azure, Entra, Graph, SharePoint, and M365 from
Windows. The Azure Function and its remote build may use Linux. This approach
matches the available development environment and avoids an additional
operating platform.

### B. Separate POSIX runner — rejected

A Linux computer, WSL, VM, or SBX would merely preserve the previous
implementation limitation. Credentials, working state, and evidence would have
to cross an additional host boundary. NaC does not require this, and it
conflicts with the binding local Windows platform.

### C. Manual cleanup or immediate rerun — rejected

Manual unlocking, deletion, permission changes, or a full rerun before
reconciliation would bypass the #739 provenance and quarantine. This approach
remains blocked.

## Windows Security Backend

### Unified platform contract

`PlatformSecurityBackend` encapsulates security-sensitive platform operations.
The Windows backend is binding for local NaC development and control. A Linux
backend may remain as an optional compatibility reference, but no local product
path may depend on it.

The existing Windows Light Runner implementation is not reactivated unchanged.
Its concepts are reused only where they meet the following guarantees.

### Files, paths, SID, and ACL

Security-sensitive files are opened through Windows handles. Before use, the
controller verifies:

- an absolute, canonical path;
- the relevant path chain for unexpected reparse points;
- the final path through the open handle;
- local volume, file, and size binding;
- owner SID and DACL;
- no write permission for unapproved principals;
- denied write and delete sharing during measurement and use;
- SHA-256 from the already open handle.

The repository-external identity resolver is no longer bound to POSIX mode
`0600`; it is bound to the current user SID, a restrictive Windows DACL, its
canonical path, and its SHA-256. Real account-to-principal mappings do not enter
Git, public logs, or comments.

State, ledger, evidence, and journals are written in the same protected
directory, flushed, and atomically replaced or extended append-only.

### Complete toolchain attestation

The system does not measure only a `.cmd` wrapper. It binds the complete
executable chain:

```text
launcher/wrapper -> interpreter -> CLI entry point -> package/module
```

This applies to Azure CLI, M365 CLI, Python, Node, npm/pnpm, Heft, and Bicep.
Hard-coded Linux paths are removed from the local contract. Any unexpected
wrapper, interpreter, entry point, or package hash blocks before network
access.

### Process boundary

Security-sensitive programs start without shell interpolation, with an
explicit argument list, fixed working directory, minimal environment allowlist,
and bounded output. The process is created suspended, assigned through a real
process handle to a Windows Job Object, and resumed only afterward. The Job
Object uses at least `KILL_ON_JOB_CLOSE`. Permitted child processes follow the
attested CLI chain; unknown processes block.

Where possible, the controller starts the bound Python or Node interpreter
directly with the attested entry point instead of executing `.cmd` through a
general shell. Tokens and credentials appear in neither arguments nor logs or
evidence.

On Windows, provider-adjacent Python processes receive a low-integrity token
before the first thread resume; this allows the established authentication
context to be read while preventing writes to normally protected credential or
configuration stores. Node-based M365 processes use the attested Node
permission mode without file-write permission while runtime files remain bound
through Windows handles. Windows loader failures are returned as redacted error
codes and must never open a modal system dialog.

### Locking and crash detection

Every run holds:

1. a Windows named mutex restricted by DACL to the current user SID;
2. an exclusively opened, hash-bound lock and state journal.

The mutex handle remains open until the run ends. `WAIT_ABANDONED` is not a
successful normal lock acquisition; it produces `RECOVERY_REQUIRED`.
Automatic resume or a second live run is excluded.

### Credential boundary

The controller uses only an already established authentication context. It
does not copy, export, hash, or persist credentials. Login, device code,
browser authentication, token refresh, cache creation, or configuration rewrite
blocks reconciliation with `BLOCKED_AUTHENTICATION_REQUIRED`. Provider access
starts only after the complete local preflight.

### Command allowlist

The security boundary consists of exact command schemas, bound target
resources, arguments, artifacts, toolchain hashes, Windows ACLs, and readbacks.
Unknown flags, other tenants, subscriptions, sites, or resources are rejected
before process start. A local Linux sandbox is not part of the design.

## Phased Completion Chain

```text
WINDOWS_IMPLEMENTATION_READY
  -> ISSUE_746_OWNER_SOLO_APPROVAL
  -> WINDOWS_PREFLIGHT_READY
  -> READ_ONLY_RECONCILIATION
  -> TWO_IDENTICAL_NOT_APPLIED_SNAPSHOTS
  -> ISSUE_739_QUARANTINE_RELEASE
  -> ISSUE_632_OFFLINE_PACKAGE
  -> ISSUE_632_LIVE_APPROVAL
  -> ONE_WINDOWS_CONTROLLED_LIVE_RUN
  -> READ_ONLY_POST_VERIFY
```

Each phase authorizes only the next phase. A blocked run authorizes no retry.

### Phase 0: Windows implementation

Only repository artifacts are changed first, validated locally on Windows,
committed, pushed to PR #747, and checked by mandatory Windows CI. There is no
provider, tenant, credential, or live access. After successful CI, the commit,
tree, verification contract, Windows backend, toolchain, resolver, and operator
principal are bound.

### Phase 1: new Issue #746 approval

A new `OWNER_SOLO_APPROVAL` binds the final implementation state because
earlier approvals point to different commits. The approval permits only the
Windows preflight and narrowly allowlisted read-only reconciliation. It is
neither the #739 quarantine release nor the #632 live approval.

### Phase 2: local Windows preflight

Before credential, network, or provider access, the preflight verifies commit,
tree, #739 state, evidence, ledger, three journals, prepared manifest, Function
and SPFx packages, toolchain, SID, ACL, reparse points, target and approval
binding, and concurrent runs. On drift, network, provider, tenant, and
credential counters remain zero.

### Phase 3: read-only provider reconciliation

Using the already established authentication context, only the narrowly bound
step-7 question is inspected. Exactly two allowlisted, redacted, canonical
provider snapshots are produced. Only two identical snapshots classified as
`FUNCTION_DEPLOYMENT_NOT_APPLIED` with zero write counters open the #739 gate.
A redirect, authentication requirement, unknown field, drift, observed
deployment, or unredactable output blocks.

### Phase 4: separate #739 quarantine release

A new, exactly bound Issue #739 comment authorizes only the deterministic,
append-only addition of a `RELEASED` record to the three local journals. The
historical run remains `FAILED_PARTIAL`; state, evidence, and ledger are not
rewritten. A partial append may be completed idempotently only with the same
unchanged approval.

### Phase 5: new #632 offline package

After journal release, Windows produces a new activation package for all twelve
existing steps. It binds commit, tree, Windows backend, toolchain, Function,
SPFx, and Bicep artifacts, target resources, and readbacks. Package creation is
offline.

### Phase 6: independent #632 live approval

A new Issue #632 comment binds the complete package and authorizes exactly one
live run. #746 and #739 comments cannot be reused. Any code, contract,
toolchain, or package change invalidates the approval.

### Phase 7: exactly one Windows-controlled live run

The run starts on the Windows workstation. Azure may materialize the Function
package internally as a Linux runtime. The controller repeats the prewrite
check, executes only the twelve bound steps, validates each readback, and stops
at the first failure. There is no automatic retry.

### Phase 8: read-only final verification

After the run, the Function, Entra API, `Matter.Read`, managed identity,
`Sites.Selected`, SharePoint site permission, SPFx and App Catalog state,
Teams-to-BFF connection, and permitted and denied synthetic access are checked
read-only. Only then may redacted completion evidence be documented.

## Governance and Identity

Provider accounts resolve through the protected external resolver to stable
principals. Different accounts of the same principal are one person and do not
satisfy a four-eyes separation.

Without a concretely cited applicable statutory, regulatory, contractual, or
binding security obligation requiring two different natural persons,
`OWNER_SOLO_APPROVAL` applies. If such an obligation is bound with source,
version, digest, and scope and only one principal is available,
`BLOCKED_SINGLE_PRINCIPAL` applies. A role label or `four_eyes` alone is not
source evidence.

## Acceptance Criteria

- **AC-746-01 — DE/EN parity:** The German and English specifications describe
  the same platform boundary, starting state, security backend, phases, stop
  conditions, and separate gates.
- **AC-746-02 — Provenance separation:** #620, #632, #739, #743, #744, and #746
  remain separate; old evidence and comments are neither current state nor new
  approval.
- **AC-746-03 — Windows preflight:** All local bindings, SID and ACL checks, and
  reparse-point checks run on Windows before network access. Every deliberate
  drift returns `BLOCKED` with zero side-effect counters.
- **AC-746-04 — Double read-only reconciliation:** Exactly two bound, redacted
  snapshots and only `FUNCTION_DEPLOYMENT_NOT_APPLIED` open the separate #739
  gate; provider, tenant, and credential write counters remain zero.
- **AC-746-05 — Complete Windows security backend:** Live, recovery, and
  reconciliation are available on Windows only with proven handle, ACL,
  reparse, toolchain, Job Object, mutex, and journal security. Merely removing
  the existing platform block is prohibited.
- **AC-746-06 — Replay and crash safety:** The three approvals are not
  interchangeable; wrong issue, principal, commit, tree, contract, body, or
  artifact binding blocks. An abandoned mutex and partial appends never cause
  an automatic live retry.
- **AC-746-07 — Windows validation and traceability:** Issue, DE/EN
  specification, DE/EN plan, AC IDs, files, positive and negative tests, and
  local and remote evidence are connected. Mandatory CI runs on Windows; Linux
  CI remains optional and non-blocking.
- **AC-746-08 — No premature live action:** Design, plan, and implementation PR
  perform no quarantine release, login, provider, tenant, credential, or live
  action. #739 and #632 remain separate hash-bound owner gates.

## Validation Model

The plan created after specification approval maintains this matrix for every
AC:

`AC ID -> artifacts -> Windows positive test -> Windows negative test ->
expected status/error code -> local command -> remote check/evidence`.

Mandatory evidence includes at least:

- file-handle, file-ID, volume-ID, and hash binding;
- SID, DACL, and reparse-point negative tests;
- complete launcher, interpreter, and package attestation;
- suspended process creation and Job Object assignment;
- mutex, abandoned-mutex, and three journal crash windows;
- replay matrix for #746, #739, and #632;
- credential, redaction, and unknown-field sentinels;
- two identical read-only snapshots with zero write counters;
- Windows SPFx build and Windows Function input package;
- Windows-native CLI, Graft, and strict-doctor checks;
- spec traceability, DE/EN parity, governance sync, privacy, and secret scan.

Before a later merge, the complete file list, commit list, and `base...head`
diff are reviewed. At minimum, `Privacy and Secrets Guard / secret-scan`,
`Privacy and Secrets Guard / privacy-lint`, `NaC Quality Gate / quality-gate`,
and the mandatory Windows gate must pass. PR #747 remains a draft pending
separate merge approval.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Replacement between hash verification and process start | Keep handle open, deny write/delete sharing, bind file/volume ID, and verify process image |
| Manipulated wrapper or interpreter | Complete launcher/interpreter/package attestation |
| Reparse-point or junction redirection | Verify the relevant path chain and final handle path |
| Overly broad ACL | Block before credential, network, and provider access |
| Unexpected CLI child processes | Attested process structure and Windows Job Object |
| Credential-cache mutation | Adapter boundary and before/after checks; block when write freedom cannot be proven |
| Crash with abandoned mutex | `RECOVERY_REQUIRED`, no automatic run |
| Windows/Azure Linux package drift | Deterministic Windows input package and bound Azure remote build |
| Linux CI accidentally becomes mandatory | Machine-readable `required_gate: false` and `may_block_windows_delivery: false` |

## Stop Conditions

The sequence stops fail-closed on a dirty worktree, missing or changed binding,
state, ledger, or journal failure, disallowed SID or ACL, reparse point,
toolchain drift, concurrent or abandoned lock, network block, authentication
requirement, credential mutation, unknown provider response, snapshot drift,
observed or not safely excluded deployment, unredactable output, or failed
mandatory gate.

A blocked run authorizes no retry.

## Non-Goals

- no migration of the Azure Function from Linux to Windows;
- no removal of Azure OneDeploy remote build;
- no WSL, Docker, SBX, local Linux VM, or separate POSIX runner;
- no general local sandbox product;
- no general tenant administration;
- no new or broader Azure, Entra, Graph, SharePoint, Teams, or App Catalog
  permission;
- no change to the twelve functional activation steps;
- no UI bypass of a legitimate access denial;
- no rewriting of historical evidence;
- no automatic resume, rollback, deletion, unlock, or retry;
- no merge or force-push of PR #747;
- no storage of real identity mappings, tokens, credentials, personal tenant
  data, or matter data in the repository or public logs.

## Review Gate

The owner approved the four design sections: platform boundary, Windows
security backend, completion chain, and scope and acceptance criteria. This
written DE/EN specification must still be reviewed and approved separately
before the implementation plan is revised or code changes begin.

Specification approval replaces neither the later final-head-bound Issue #746
`OWNER_SOLO_APPROVAL`, the Issue #739 quarantine release, nor the Issue #632
live approval. Until the complete Windows backend is implemented, the existing
runtime block remains fail-closed.
