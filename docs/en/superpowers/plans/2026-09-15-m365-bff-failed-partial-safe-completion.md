# Windows-Native Completion of the Partial M365 BFF Activation — Implementation Plan

Status: specification and plan approved by the owner; local `plan -> review -> fix` completed; implementation validated locally; operational execution blocked

Date: 17 September 2026

Specification: [Safe Windows Completion of the Partial M365 BFF Activation](../specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md)

Leading issue: [#746](https://github.com/notariat8/NaC/issues/746)

Draft PR: [#747](https://github.com/notariat8/NaC/pull/747)

Delivery mode: Protected PR

Risk gate: Human Approval

## Outcome and Boundary

The implementation delivers a completely Windows-native local development,
build, test, packaging, reconciliation, recovery, and activation-control path.
Linux remains allowed only as the managed Azure Function runtime, Azure remote
build environment, and an optional non-blocking compatibility test.

This plan authorizes only repository changes, local Windows validation,
synthetic tests, a separate local commit, and, after later explicit approval, a
push to PR #747. It does not currently authorize:

- authentication or credential changes;
- tenant or provider access;
- Issue #739 quarantine release;
- generation of an operationally valid Issue #632 live approval;
- live activation, retry, rollback, deletion, or unlock;
- merge or force-push.

Until the Windows security backend is fully implemented and validated, the
existing platform block remains fail-closed.

## Implementation Principles

1. **Test first:** Every new Windows capability begins with a positive test and
   at least one fail-closed negative test.
2. **No weakening:** Linux primitives are not merely removed; they are replaced
   by verifiable Windows guarantees.
3. **Backend injection:** Runner and reconciler do not access `fcntl`, `/proc`,
   Unix UIDs, or raw Windows APIs directly; they use a narrow platform contract.
4. **Windows is authoritative:** Every mandatory local and remote gate must
   work on Windows. Linux CI is optional.
5. **No provider action during implementation:** Real adapters are tested only
   with synthetic ports, fake processes, and sentinel data.
6. **Preserve existing provenance:** Historical #739 state, ledger, and journal
   artifacts are neither rewritten nor reconstructed.
7. **One gate per effect:** #746 reconciliation, #739 journal release, and #632
   live run remain non-interchangeable.
8. **Loss is terminal:** When the exactly bound #739 original artifacts are
   completely lost, the local path ends with
   `FUNCTION_DEPLOYMENT_PROVENANCE_LOST`; no provider reconciliation or
   approval phase may follow.

## Change Surfaces

| Surface | Planned artifacts | Purpose |
| --- | --- | --- |
| Platform contract | `src/nac_bff/azure_activation_contract.py`, new `src/nac_bff/activation_security_backend.py` | Define backend protocol, capabilities, stable error codes, and selection |
| Windows backend | new `src/nac_bff/activation_security_windows.py` | Handle, SID/ACL, reparse, process, Job Object, mutex, and flush semantics |
| Optional Linux backend | new `src/nac_bff/activation_security_linux.py` | Isolate existing Linux semantics without creating a local dependency |
| Runner/recovery | `src/nac_bff/azure_activation_runner.py`, `src/nac_bff/azure_activation_facade.py` | Route file, lock, state, evidence, and recovery operations through the backend |
| Toolchain/processes | `src/nac_bff/azure_activation_attestations.py`, `src/nac_bff/azure_live_commands.py`, `src/nac_bff/azure_live_commands_win.py`, `src/nac_m365_graph/sealed_toolchain.py` | Complete Windows launcher/interpreter/package binding and secure process launch |
| Reconciliation | existing Function-deployment and interruption-reconciliation modules, new `src/nac_bff/issue746_reconciliation_gate.py` | Windows preflight, productive #746 gate, double read-only snapshots, and zero-write boundary |
| CLI/composition | `src/nac_cli/cli.py`, `src/nac_m365_graph/mvp_test_environment_deploy.py`, `src/nac_bff/azure_activation_composition.py` | Enforce #746 authorization before the factory and again before every provider read; keep live and recovery blocked |
| Resolver/governance | `src/nac_identity/governance_registry.py`, Issue #746 validator, and verification contract | Shared principal logic, SID/DACL rather than POSIX `0600`, and no second-account separation |
| Contracts | `workflows/contracts/m365-azure-bff-live-activation.contract.json`, both M365 verification contracts | Windows target, optional Azure Linux runtime, gate and evidence matrix |
| Tests | new backend tests and existing #632/#739/#744/#746 tests | Positive Windows paths, negative matrix, replay, and crash windows |
| Developer tooling | `scripts/startup_check.py`, minimum requirements, SBOM | Prove working Windows Python `>=3.11` and Windows Graft as mandatory |
| Documentation | DE/EN CLI, minimum requirements, #632/#744/#746 specification and plan | Remove Linux-only target assumption and explain migration status |
| CI | `.github/workflows/windows-portability.yml`, quality-gate configuration | Mandatory Windows gate; Linux compatibility optional and not independently blocking |
| Traceability | `agent-context/index.json`, specification manifests, AI SBOM | Connect issue, ACs, files, tests, and remote evidence |

New filenames are plan requirements. If implementation reveals a clearer split
without changing scope, the plan must be synchronized before commit; parallel
duplicate implementations are prohibited.

## Binding Phase and Gate Table

| Phase | Input | Allowed action | Success | Blocks on | Mutation |
| --- | --- | --- | --- | --- | --- |
| 0 Implementation | approved specification `8a51727c` and plan approval | code, tests, contracts, docs, local Windows validation | `WINDOWS_IMPLEMENTATION_READY` | red mandatory gate | repository only |
| 1 PR evidence | clean implementation commit | push after separate approval, Windows CI, complete PR diff | `WINDOWS_REMOTE_CI_READY` | missing/red check or scope drift | GitHub branch/PR |
| 2 #746 gate | final commit/tree, contract, backend, toolchain, resolver, and principal binding | new `OWNER_SOLO_APPROVAL` | `WINDOWS_RECONCILIATION_APPROVED` | binding or governance error | GitHub comment |
| 3a Windows preflight | unchanged #739 artifacts | read local bindings only | `WINDOWS_PREFLIGHT_READY` | drift, ACL/reparse/lock/toolchain error | none |
| 3b terminal provenance loss | DACL/SID-protected local owner record, protected resolver, stable principal, exact issue/action/run/hash/correlation/path/inventory binding, and complete absence at the expected locations | local existence and binding checks only | `status=BLOCKED`, `reason_code=FUNCTION_DEPLOYMENT_PROVENANCE_LOST`, `terminal=true`, `retry_allowed=false`, `next_phase=null`, exit `2` | any mismatch, partial inventory, uninspectable storage, or existing artifacts at the bound expected locations | none; closed enumerated operational counters `0` |
| 4 Provider inspection | successful preflight, existing non-writing auth context | exactly two bound read-only snapshots | `FUNCTION_DEPLOYMENT_NOT_APPLIED` | auth requirement, drift, unknown output, deployment | none |
| 5 #739 gate | identical snapshot hashes and new exact approval | three deterministic journal appends | `LOCK_JOURNALS_RELEASED` | replay, tail, hash, or order error | three local appends only |
| 6 #632 package | clean bound state after phase 5 | Windows-native offline packaging | `ISSUE_632_PACKAGE_READY` | build or binding error | local offline artifacts |
| 7 #632 gate | complete package and new exact approval | authorize exactly one live run | `LIVE_RUN_APPROVED` | any drift | GitHub comment |
| 8 Live run | valid #632 approval | control twelve bound steps from Windows | existing live-contract status | first error | approved plan only |
| 9 Post-verify | terminal live status | read-only target state and access checks | `PASSED` or bound error | ambiguous readback | redacted evidence |

Only phase 0 and local synthetic validation run in the current implementation
turn. Every later phase has its own gate.
Phase 3b is not an alternative gate for phase 3a but a terminal end state; it
cannot open phases 4 through 9.

## Target Contract of the Windows Security Backend

The backend protocol provides at least these capabilities:

```text
capabilities()
current_operator_binding()
inspect_private_path(path, purpose)
open_bound_read(path, expected_binding)
atomic_write(path, bytes)
append_and_flush(path, bytes)
acquire_run_lock(target_binding)
launch_attested_process(spec)
inspect_process_image(process_handle)
```

Concrete returns are typed, redactable records containing no credentials or
clear-text identities. Required bindings include:

- canonical path hash;
- file and volume ID;
- size and SHA-256;
- owner SID hash;
- security descriptor/DACL hash;
- reparse-point status;
- launcher, interpreter, entry-point, and package hashes;
- Job Object and image binding for processes;
- mutex-name hash, journal hash, and `normal`/`abandoned` state for locks.

## Test-First Implementation Sequence

### 1. Verification contract and initially red plan/contract tests

**Files:**

- `workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml`
- `workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml`
- `workflows/contracts/m365-azure-bff-live-activation.contract.json`
- `tests/test_m365_bff_failed_partial_safe_completion.py`
- `tests/test_m365_azure_bff_live_activation_contract.py`
- `scripts/validate_m365_bff_failed_partial_safe_completion.py`

**Red first:**

- Windows is not the authoritative local platform;
- `posix_local` or `ubuntu_remote_ci` is a mandatory gate;
- a Linux path is required for local build or live control;
- Windows reconciliation remains categorically blocked;
- resolver requires POSIX mode `0600`;
- #746, #739, or #632 gates are interchangeable.

**Then green:**

- raise schema version;
- materialize `windows_native` and `windows_remote_ci` as mandatory platforms;
- record `azure_linux_runtime_optional` as target compatibility, not a local
  gate;
- connect all eight ACs and phases 0 through 9 in machine-readable form;
- define stable Windows error codes and zero-side-effect counters.

### 2. Backend protocol and Linux isolation

**Files:**

- new `src/nac_bff/activation_security_backend.py`
- new `src/nac_bff/activation_security_linux.py`
- `src/nac_bff/azure_activation_contract.py`
- new `tests/test_activation_security_backend.py`

**Red first:** Backend selection must not be forgeable through CLI flags,
environment, or configuration; incomplete capabilities must block with
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE`.

**Then green:** Move existing Linux checks into the optional Linux backend;
trusted runtime properties select the backend; facade, runner, and adapters
receive it explicitly or through a small factory.

### 3. Windows file, path, SID, and ACL primitives

**Files:**

- new `src/nac_bff/activation_security_windows.py`
- new `tests/test_activation_security_windows.py`

**Windows APIs:** `CreateFileW`, `GetFinalPathNameByHandleW`,
`GetFileInformationByHandleEx`, `GetSecurityInfo`, `GetNamedSecurityInfoW`,
`FlushFileBuffers`, and `ReplaceFileW` or `MoveFileExW`.

**Red first:** relative paths, junctions/reparse points, unexpected owners,
broad writable ACEs, remote or non-NTFS volumes, file-ID change, write/delete
sharing, and hash drift.

**Then green:** Handle-based measurement and typed `BoundFileSnapshot`
evidence. No PowerShell `Get-Acl`, `icacls` parsing, or additional `pywin32`
dependency; narrowly wrap Windows APIs through `ctypes`.

### 4. Windows locking, atomic writes, and crash windows

**Files:**

- Windows backend;
- `src/nac_bff/azure_activation_runner.py`;
- runner, recovery, and journal tests.

**Red first:** second process, lost mutex handle, `WAIT_ABANDONED`, crash before
the first append, after the first or second append, and after the third append
before return.

**Then green:** named mutex protected by DACL plus exclusive journal handle;
`WAIT_ABANDONED -> RECOVERY_REQUIRED`; `WriteFile`/`FlushFileBuffers`; atomic
replace; idempotent journal continuation only with the identical #739 approval.
The runner then contains no direct `fcntl` assumption.

### 5. Attested Windows process launch

**Files:**

- Windows backend;
- `src/nac_bff/azure_live_commands_win.py`;
- `src/nac_bff/azure_live_commands.py`;
- new process and toolchain tests.

**Red first:** process starts before Job assignment, PID is used as a handle,
unknown child process, shell interpolation, environment leak, image change,
timeout, oversized output, or non-allowlisted exit code.

**Then green:** `CreateProcessW` with `CREATE_SUSPENDED`, real process and thread
handles, `AssignProcessToJobObject`, `KILL_ON_JOB_CLOSE`, then `ResumeThread`,
attested child-process structure, fixed argument list and working directory,
minimal environment allowlist, and redacted bounded output.
The Python provider path applies low integrity before `ResumeThread`; the
Node/M365 path starts in an attested Node permission mode without file-write
permission. Inherited Windows error dialogs are disabled so every loader
failure ends fail-closed as a redacted code only.

The old Windows Light Runner code is not retained in parallel. Reusable parts
are migrated; the faulty stub is then removed or reduced to a compatibility
export backed by the new implementation.

### 6. Complete Windows toolchain attestation

**Files:**

- `src/nac_bff/azure_activation_attestations.py`;
- `src/nac_m365_graph/sealed_toolchain.py`;
- `src/nac_bff/azure_live_commands.py`;
- attestation and negative tests.

For Azure CLI, M365 CLI, Python, Node, npm/pnpm, Heft, and Bicep, bind launcher,
interpreter, entry point, and package base. A `.cmd` file alone is never
sufficient. Where possible, start the interpreter and entry point directly,
without a general shell.

Hard-coded `/usr/bin`, `/tmp`, and `linux-x64` paths disappear from the
mandatory local contract. Linux artifacts may belong only to the Azure target
package or optional compatibility test.

### 7. Integrate runner, facade, CLI, and twelve activation steps

**Files:**

- `src/nac_bff/azure_activation_runner.py`;
- `src/nac_bff/azure_activation_facade.py`;
- `src/nac_bff/azure_activation_composition.py`;
- `src/nac_cli/cli.py`;
- `src/nac_m365_graph/mvp_test_environment_deploy.py`;
- existing runner, CLI, and composition tests.

Offline commands remain importable unchanged. Only bound read-only interruption
and Function-deployment reconciliation uses the Windows backend for provider
reads. Live and recovery remain blocked under #746 even when all backend
capabilities exist. All twelve steps, their order, target resources, and
readbacks remain unchanged.

### 8. Credential-write-free reconciliation and two snapshots

**Files:** `src/nac_bff/issue746_reconciliation_gate.py`, existing
reconciliation modules, CLI/composition, verification contract, adapter, and
sentinel tests.

The real adapter has no implicit login or refresh path. Before the first
provider read, the resolver, operator principal, final HEAD/tree, PR #747, all
required checks, and the unchanged #746 `OWNER_SOLO_APPROVAL` comment must form
the same authorization. The CLI and both port factories require it, and the
runtime verifier checks its canonical digest again before every provider
subprocess. If the channel cannot technically guarantee freedom from credential
or cache writes, it blocks before provider access.

Synthetic tests attempt login, device code, refresh, cache creation, and config
rewrite and expect blocking without credential mutation. Two provider responses
are immediately reduced to the same allowlisted canonical projection. Only
identical hashes classified as `FUNCTION_DEPLOYMENT_NOT_APPLIED` open the
separate #739 gate.

**Terminal loss path:** Before the productive #746 gate and before the port
factory, a dedicated local CLI path reads a repository-external owner
confirmation record bound by Windows SID/DACL and SHA-256 plus the existing
protected identity resolver. The resolver must map the confirming account to
an active `OWNER_SOLO_APPROVAL` principal with the process role and
qualification. The record binds the resolver hash in use and is itself the sole
owner-confirmation evidence for this terminal path; old #632/#739 or #746
comments are neither required nor sufficient. The record is the trusted source
of expected values and binds
action `CONFIRM_FUNCTION_DEPLOYMENT_PROVENANCE_LOST`, Issue `739`, run ID
`nac-bff-live-20260908-issue739-v4`, activation hash, correlation ID, canonical
run path, the original target/legacy lock-binding hashes, complete expected
artifact inventory, resolver, operator account, and principal hashes, and the
exact terminal contract. The ordinary run arguments are only a
second comparison channel and must not determine expected values or path.

The path verifies only local facts: every record, resolver, principal, and run
binding; absence of the canonical hash directory; and absence of the three
lock journals formed from the original target/legacy lock hashes bound in the
confirmation record. It builds neither a current activation plan nor a Function
package and starts no subprocess. Only the complete expected inventory counts
as bound; a partial or uninspectable inventory at the bound expected locations
and any mismatch yield a narrow binding or state error. Positive and
negative tests prove the exact `BLOCKED` result plus reason, terminal, retry,
next-phase fields, and exit `2`. Sentinel tests forbid every GitHub, DNS/HTTP/
network, subprocess, credential, provider, tenant, live, recovery, retry,
packaging, #739 release, #632 authorization, file-write, and journal path. The
contract enumerates those counters as a closed set; every counter remains `0`.

### 9. Windows resolver and approval bindings

**Files:** `src/nac_identity/governance_registry.py`, productive #746 gate,
Issue #746 validator, verification contract, resolver fixtures, and tests.

Bind the protected external resolver to canonical path, file/volume ID,
SHA-256, user SID, and DACL. Public evidence contains purpose-separated hashes
only. The three known accounts must continue to resolve to the same principal
and cannot approve one another.

Replay tests cover wrong issue, author association, principal, body/hash,
commit, tree, contract, toolchain, resolver, snapshot, and package.

### 10. Windows packaging for Function and SPFx

**Files:** packaging and build adapters, SPFx configuration, contracts, and
tests.

- SPFx/Heft builds completely on Windows from the exact lockfile.
- The Function input package is produced deterministically on Windows.
- Linux-native Function dependencies are produced only by the bound Azure
  OneDeploy remote build.
- Local build and hashing must not depend on WSL, Docker, or Linux.
- Repeated builds from identical inputs produce identical bound input artifacts
  or use documented deterministic normalization.

### 11. Windows developer tools and CI

**Files:**

- `scripts/startup_check.py`;
- DE/EN minimum requirements and CLI documentation;
- `.github/workflows/windows-portability.yml`;
- quality-gate and SBOM artifacts.

The Windows portability job and local activation validator prove a native
Python interpreter `>=3.11`, Node `>=24`, the
pinned Graft CLI, and required build tools. A broken launcher that cannot
resolve its standard library or package dependencies is unavailable. There is
no Linux fallback.

The current local Graft 0.18.0 installation cannot run because its `dotenv`
dependency is unresolved. Implementation must establish a reproducible working
Windows installation or central tool resolution and then run `graft build` and
`graft check` natively. Reinstallation or mutation outside the repository is a
separate tool-installation step and is not performed silently.

Mandatory remote evidence:

- Windows backend unit and integration tests;
- Windows CLI and validators;
- Windows SPFx build;
- Windows Function input package;
- privacy, secret scan, governance sync, and quality gate.

Linux CI may verify Azure Linux compatibility, but is not a replacement and
must not independently block Windows delivery.

### 11.1 Subsequent Strict Doctor Windows Clusters

The native full suite exposed additional POSIX assumptions in existing
security and persistence paths. They belong to AC-746-05 and
AC-746-07 because Windows completion is reliable only when its direct
consumers also operate natively and fail closed:

- Git-tree, reconciliation, activation, live, and performance paths;
- business-case composition, quarantine, migration, and SQLite outbox;
- M365 Node, sealed toolchain, SPFx, and MVP deployment paths;
- repository-local validators, canonical paths, and Windows test fixtures.

The port replaces POSIX file-descriptor, UID, mode, signal, pass_fds, and
symlink assumptions with the bound Windows security backend. SID, DACL, file
ID, hash, hardlink, reparse, locking, toolchain, and fail-closed checks remain
fully enforced. Focused regressions run before the full suite, Graft, and
Strict Doctor; a red shard must not be hidden by an isolated green test.

### 12. Documentation, traceability, and AI SBOM

Synchronize DE/EN:

- #632 Windows Light Runner specification;
- #744 Windows Offline specification and plan;
- #746 specification and plan;
- CLI and minimum requirements;
- `agent-context/index.json`;
- AI SBOM and verification contracts.

#744 remains documented as a historical safe interim state. Its Windows block
is marked superseded only after the green Windows implementation; historical
commit and issue statements are not rewritten.

### 13. Implement -> Review -> Fix

After implementation, review the complete `origin/main...HEAD` diff, not only
the last commit. Review at least:

- scope and specification compliance;
- Windows API and handle lifecycles;
- ACL, reparse, and TOCTOU boundaries;
- credential, privacy, and redaction boundaries;
- twelve activation steps and target binding;
- replay, crash, and recovery paths;
- DE/EN parity;
- Windows CI as a mandatory gate;
- no real identity, tenant, or credential data in the diff.

Every finding is fixed and revalidated before implementation acceptance.

## Machine-Readable Validation Mapping

```nac-validation-matrix
schema_version: nac.issue-746-validation-plan/v0.2
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
  - id: issue746_validator
    platform: windows_native
    command: python scripts/validate_m365_bff_failed_partial_safe_completion.py
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: windows_security_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_activation_security*.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_bff_regression_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_nac_bff_azure_*.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: issue746_gate_tests
    platform: windows_native
    command: python -m unittest tests.test_issue746_reconciliation_gate
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_business_case_regression_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_business_case_type_*.py
    acceptance_ids: [AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_m365_regression_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_m365_*.py
    acceptance_ids: [AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_sqlite_outbox_tests
    platform: windows_native
    command: python -m unittest discover -s tests -p test_sqlite_evidence_staging_outbox.py
    acceptance_ids: [AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: issue746_windows_tests
    platform: windows_native
    command: python -m unittest tests.test_windows_offline_cli_portability tests.test_m365_bff_failed_partial_safe_completion tests.test_m365_azure_bff_live_activation_contract tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_activation_cli
    acceptance_ids: [AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: activation_validator
    platform: windows_native
    command: python scripts/validate_m365_azure_bff_live_activation.py
    acceptance_ids: [AC-746-03, AC-746-04, AC-746-05, AC-746-06]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: spfx_windows_build
    platform: windows_native
    command: npm --prefix spfx/nac-bpmn-viewer run build
    acceptance_ids: [AC-746-05, AC-746-07]
    remote_evidence: [SPFx BPMN Viewer / spfx-bpmn-viewer]
  - id: graft_build
    platform: windows_native
    command: graft build
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: graft_check
    platform: windows_native
    command: graft check
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: strict_doctor
    platform: windows_native
    command: python scripts/nac.py doctor --profile strict
    acceptance_ids: [AC-746-01, AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: windows_ci_security_tests
    platform: windows_remote_ci
    command: python -m unittest discover -s tests -p test_activation_security*.py
    acceptance_ids: [AC-746-03, AC-746-05, AC-746-06, AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_activation_tests
    platform: windows_remote_ci
    command: python -m unittest tests.test_windows_offline_cli_portability tests.test_spfx_bff_catalog_readback_regression tests.test_m365_bff_failed_partial_safe_completion tests.test_m365_azure_bff_live_activation_contract tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_nac_bff_azure_activation_cli
    acceptance_ids: [AC-746-02, AC-746-03, AC-746-04, AC-746-05, AC-746-06, AC-746-07, AC-746-08]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_spfx_build
    platform: windows_remote_ci
    command: npm --prefix spfx/nac-bpmn-viewer run build
    acceptance_ids: [AC-746-05, AC-746-07]
    remote_evidence: [SPFx BPMN Viewer / spfx-bpmn-viewer]
  - id: windows_ci_graft
    platform: windows_remote_ci
    command: graft build
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_graft_check
    platform: windows_remote_ci
    command: graft check
    acceptance_ids: [AC-746-07]
    remote_evidence: [NaC Windows Portability / windows-offline-cli]
  - id: windows_ci_doctor
    platform: windows_remote_ci
    command: python scripts/nac.py doctor --profile strict
    acceptance_ids: [AC-746-01, AC-746-03, AC-746-05, AC-746-07, AC-746-08]
    remote_evidence: [NaC Quality Gate / quality-gate]
  - id: remote_checks
    platform: post_pr_remote
    command: authenticated GitHub connector check listing for PR 747 at exact HEAD
    acceptance_ids: [AC-746-07, AC-746-08]
    remote_evidence: [Privacy and Secrets Guard / secret-scan, Privacy and Secrets Guard / privacy-lint, NaC Quality Gate / quality-gate, NaC Windows Portability / windows-offline-cli, SPFx BPMN Viewer / spfx-bpmn-viewer]
  - id: full_diff
    platform: windows_native
    command: git diff origin/main...HEAD
    acceptance_ids: [AC-746-01, AC-746-07, AC-746-08]
    remote_evidence: [complete base...head patch]
```

The verification contract adds `scope` and `side_effect_class` to every entry.
`windows_native` is `local_read_or_synthetic`, `windows_remote_ci` is
`ci_read_or_synthetic`, and `post_pr_remote` is `github_read_only`. No
validation command has live authority.

## AC Evidence Matrix

| AC | Primary artifacts | Positive evidence | Negative evidence | Expected result |
| --- | --- | --- | --- | --- |
| AC-746-01 | DE/EN specification and plan, contract | parity validator and normalized gate table | missing or changed section | `BLOCKED` |
| AC-746-02 | provenance and approval matrix, protected local confirmation record | exact #739 run, principal, and complete expected inventory absent from bound expected locations | partial or uninspectable inventory at those locations, wrong principal, run, issue, action, hash, correlation ID, or path | `BLOCKED` + `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` only for the exact confirmed loss case |
| AC-746-03 | Windows backend, runner, preflight | complete binding before network | drift per field, ACL, reparse, lock | all side-effect counters `0` |
| AC-746-04 | reconciler and snapshot projection | two identical `NOT_APPLIED` snapshots | drift, redirect, auth requirement, unknown field | zero write counters |
| AC-746-05 | backend, toolchain, Job Object | complete Windows capabilities | missing individual capability | `PLATFORM_SECURITY_BACKEND_UNAVAILABLE` or narrow Windows code |
| AC-746-06 | gate, mutex, and journal tests | identical approval completes true prefix | different hash, tail, order, abandoned lock | no retry |
| AC-746-07 | traceability, tooling, CI | Windows gates and complete matrix pass | missing Windows check or Linux-only requirement | `BLOCKED` |
| AC-746-08 | closed counter schema and PR diff | terminal result with `next_phase=null`, exit `2`, and every counter `0` | call to GitHub, network/DNS/HTTP, subprocess, credential, provider, tenant, live, recovery/retry, packaging, #739 release, #632 authorization, file, or journal write | `BLOCKED`, terminal, no next phase |

## Planned Commit Sequence

1. `test(m365): bind Windows activation security contract`
2. `feat(m365): add Windows activation security backend`
3. `feat(m365): run reconciliation and activation control on Windows`
4. `build(m365): make Windows packaging and CI authoritative`
5. `docs(m365): synchronize Windows issue 746 evidence`

Before each commit, verify the file and test set. A commit may combine multiple
steps if no review boundary is lost; history is not rewritten or force-pushed.

## Plan Review Findings and Fixes

The local `plan -> review -> fix` pass corrected these findings:

1. **POSIX remained authoritative in the old plan.** All mandatory local and CI
   evidence now runs on Windows; Linux is only an Azure target or optional
   compatibility test.
2. **The previous Windows Light Runner was not a sufficient security backend.**
   The plan requires real process handles, suspended creation, correct Job
   assignment, persistent mutex handle, reparse and ACL checks, and complete
   toolchain binding.
3. **Runner file operations were missing from the platform boundary.** File,
   lock, journal, atomic-write, and recovery operations are part of the backend
   contract.
4. **Credential write freedom was only measured after the fact.** The plan
   requires an adapter that technically blocks login, refresh, and cache writes
   before provider access; otherwise reconciliation remains blocked.
5. **The resolver still depended on POSIX `0600`.** SID, DACL, file/volume ID,
   and hash binding replace the POSIX mode.
6. **Windows build did not yet imply Windows tooling.** Python, Graft, SPFx, and
   Function packaging are now mandatory Windows gates.
7. **GitHub CLI was treated as mandatory.** Remote check evaluation uses the
   existing authenticated GitHub connector; `gh` remains optional and starts no
   authentication. The productive #746 boundary accepts only two semantic reads
   bounded to the repository, PR, and comment from a trusted-host-injected
   channel. Without that channel it blocks before the Azure factory; a 401
   triggers neither login nor retry.
8. **Windows CI existed only in prose, not as its own platform row.** Security,
   activation, SPFx, Graft, and doctor runs now have explicit
   `windows_remote_ci` entries.
9. **The #746 validator was hard-coded to the previous POSIX artifact list and
   local `gh` commands.** Validator, verification contract, and tests now use
   the same semantic channel interface and the approved Windows command matrix.

After these fixes, the plan has no known mandatory local Linux dependency and
no premature operational authorization.

## Implementation Definition of Done

Implementation is ready for owner acceptance only when:

- all eight ACs have positive and negative Windows evidence;
- Windows SPFx build and Function input package are reproducible;
- Graft and strict doctor pass natively on Windows;
- no Linux or POSIX requirement remains in a local or mandatory CI path;
- DE/EN documentation, contracts, traceability, and AI SBOM are synchronized;
- the complete `origin/main...HEAD` diff and commit list are reviewed;
- the worktree is clean and the branch is push-ready without history rewrite;
- no login, provider, tenant, credential, #739, or #632 live access has
  occurred.

Only then is separate push approval, or an already valid delivery
authorization, evaluated. The later operational flow then requires new
final-head-bound gates for #746, #739, and #632.
