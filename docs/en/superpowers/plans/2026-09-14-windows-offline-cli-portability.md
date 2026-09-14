# Windows Offline CLI Portability – Implementation Plan

Status: Plan approved by owner, internal reviews passed, implementation in progress

Date: 14 September 2026
Spec: [Windows Offline CLI Portability](../specs/2026-09-14-windows-offline-cli-portability-design.md)
Leading issue: [#744](https://github.com/notariat8/NaC/issues/744)
Delivery Mode: Protected PR
Risk Gate: Human Approval

## Objective

The central `nac` CLI and the defined local M365/SPFx checks become importable
and executable on native Windows with Python 3.11. The existing Linux security
backend remains the only execution path for live activation, recovery, and
reconciliation. Windows blocks those edges with
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE` and `writes_started: false` before
credentials, state, locks, subprocesses, network, tenant, or provider access.

## Change Surfaces

| Surface | Planned artifacts | Purpose |
| --- | --- | --- |
| Portable contracts and calls | `src/nac_bff/azure_activation_contract.py`, `src/nac_bff/azure_activation_facade.py` | Platform-neutral types, error code, trusted capability evaluation, and side-effect-free public lazy-load wrappers |
| Linux live backend | `src/nac_bff/azure_activation_runner.py`, `src/nac_bff/azure_activation_composition.py` | Import types from the contract; expose the backend only through the portable facade; preserve existing Linux security logic |
| Existing Windows live branches | `src/nac_bff/azure_live_commands.py`, `src/nac_bff/azure_live_commands_win.py`, `src/nac_bff/azure_activation_attestations.py` | Disable or make Windows subprocess, mutex, and live-attestation paths unreachable while preserving offline imports |
| Central CLI | `src/nac_cli/cli.py` | Windows block before every live/recovery/reconciliation import and side-effect edge; keep offline routes reachable |
| Production adapters | `src/nac_m365_graph/business_case_type_production_adapters.py` | Make imports portable while completely blocking sealed GitHub execution without POSIX capabilities |
| Contracts and validators | Live-activation contract/verification/validator plus S4f production-adapter contract/verification/validator | Enforce the actual Linux-live/Windows-offline contract and the blocked S4f execution path |
| Tests | `tests/test_windows_offline_cli_portability.py`, `tests/test_spfx_bff_catalog_readback_regression.py`, and the exact activation/reconciliation/S4f suites | Cover AC-744-01 through AC-744-06 with Windows negative and Linux regression evidence |
| CI | `.github/workflows/windows-portability.yml` | Non-optional Windows job with Python 3.11 and a stable check context |
| Documentation and context | DE/EN CLI docs, DE/EN minimum requirements, former Windows Light spec, and `agent-context/index.json` | State the support boundary unambiguously as Windows offline/Linux live and make it discoverable |

The exact file list may change during test-driven implementation only within
these surfaces. Any additional policy, roadmap, plugin, provider, or live-
execution surface stops implementation and requires renewed scope review.

## Order: Test → Implementation → Review → Fix

### 1. Capture Reproducible Red Windows Contracts

- Start `tests/test_windows_offline_cli_portability.py` with the complete
  offline and negative matrices from the spec.
- Real Windows smokes use Python 3.11 and the committed default artifacts;
  `fcntl` and `pwd` are not injected as fake modules.
- Every new and used fixture is exclusively synthetic and contains no real
  tenant, customer, matter, person, or credential data. Tests verify this
  provenance and content boundary.
- Credential, state, lock, subprocess, network, tenant, and provider edges use
  failing guards. Successful offline cases must prove exactly zero calls to
  those guards.
- Record the known import failures and existing green Linux contracts before
  changing code. Only the expected platform break may be red.

The reproducible native Windows red run is:

```powershell
python -m unittest tests.test_windows_offline_cli_portability
```

Before implementation, only the documented POSIX import boundaries are
accepted as failures. No test may reach any of the seven side-effect edges;
any additional failure stops implementation.

Capture the unchanged POSIX baseline on Linux with this fast regression subset
and the authoritative complete strict gate:

```bash
python -m unittest tests.test_nac_bff_azure_activation_cli tests.test_nac_bff_azure_live_commands tests.test_business_case_type_production_adapters
graft build
python scripts/nac.py doctor --profile strict
```

The targeted unit-test command is only the fast regression subset;
`doctor --profile strict` with complete test discovery is the authoritative
Linux-wide proof.

### 2. Implement the Portable Activation Facade

- Move `ActivationStepError`, `ActivationContext`, and
  `LiveActivationRequest` from the runner to `azure_activation_contract.py`.
- Preserve existing public import paths through pure re-exports where needed;
  no consumer may load POSIX primitives early as a result.
- Implement a deny-by-default capability function based exclusively on trusted
  runtime properties. CLI, request, environment, and configuration values are
  not platform authority.
- Produce the stable redacted platform error centrally and block unknown
  platforms and incomplete capabilities.
- `azure_activation_facade.py` exposes the public callables
  `run_azure_bff_live_activation`, `reconcile_azure_bff_live_activation_lock`,
  `build_live_activation_execution_port`,
  `build_interruption_reconciliation_ports`, and
  `build_function_deployment_reconciliation_ports`. Every wrapper evaluates
  runtime capabilities first and dynamically imports runner or composition on
  Linux only afterward.
- CLI and portable consumers move to the contract or facade. The Linux runner
  remains internally importable for existing security tests; Windows never
  loads it as a portable API.

### 3. Separate the Linux Backend Without a Security Delta

- `azure_activation_runner.py` remains the owner of existing POSIX execution
  and loads `pwd`, `fcntl`, `memfd`, ownership, locking, and no-follow
  primitives only as backend prerequisites.
- `azure_activation_composition.py` imports portable types from the contract;
  the facade loads composition and runner only after a successful gate.
- Ownership checks, host-global locking, sealed `memfd` execution,
  binary/toolchain binding, ledger, evidence, recovery, and pre-write gates are
  neither reimplemented nor weakened.
- Backend import or capability failures remain terminal; there is no Windows
  fallback and no no-op lock.
- Live admission requires Linux and every existing `memfd`, `/proc`, ownership,
  locking, namespace, and no-follow capability. macOS, other POSIX systems, and
  unknown platforms remain blocked for live, recovery, and reconciliation
  without complete evidence.

### 4. Block Every Public CLI and Python Edge Early

- In `src/nac_cli/cli.py`, check the four spec edges—live activation,
  finalization recovery, interruption reconciliation, and function-deployment
  reconciliation—before owner-state resolution, repository state, backend
  import, or any other side-effect edge.
- For every recognized Windows command, the platform error takes precedence
  over missing owner arguments, detailed parser validation, and approval
  validation.
- The corresponding Python functions and composition factories use the same
  capability boundary.
- POSIX retains every existing owner gate. The platform check may neither
  create approval nor convert existing approval errors into permitted
  execution.
- The platform-error payload contains exactly `schema_version`, `status`,
  `error`, and `writes_started`; `status` is `BLOCKED`, `error` contains only
  the stable code, and `writes_started` is `false`. Absolute user paths, SID,
  login, tokens, environment, and provider responses remain excluded.

### 5. Make Production Adapters Portably Importable

- Remove the module-level `fcntl` dependency from the portable import edge or
  encapsulate it unambiguously as an unavailable backend capability.
- Sealed GitHub CLI execution remains bound to Linux `memfd`, `/proc/self/fd`,
  ownership checks, seals, `pass_fds`, and binary binding.
- Without complete POSIX capability, block with the shared platform code before
  secret, state, lock, subprocess, network, tenant, or provider access.
- Guards assert zero calls to `gh`, `gh.exe`, Azure CLI, and Microsoft 365 CLI;
  no executable resolved through `PATH` is accepted as a substitute.
- Synchronize the S4f production-adapter contract, verification contract,
  validator, contract tests, and CLI tests with portable offline status and the
  shared blocked-platform code. `VERIFIED_OFFLINE` must not claim a live-
  capable adapter instance on Windows.

### 6. Close Existing Windows Live Branches

- In `azure_live_commands.py`, block every Windows dispatch to direct
  subprocess execution before launch.
- Keep `azure_live_commands_win.py` at most as a disabled historical
  implementation with no reachable product edge, or remove it when no
  contract or test reference needs it.
- Keep `azure_activation_attestations.py` importable for portable offline
  information, but do not let it attest Windows live executability.
- Explicitly audit `src/nac_m365_graph/sealed_toolchain.py` and the Windows
  branch in `src/nac_m365_graph/mvp_test_environment_deploy.py` for additional
  live reachability. Change code there only if an active Windows live edge is
  demonstrated.
- Validators and negative tests must reject every active Windows subprocess,
  mutex, or live-attestation edge.

### 7. Correct Contract, Validator, and Documentation

- Change the live-activation contract so Linux with complete security
  capabilities is the only live backend and Windows owns only the portable
  offline facade. Remove the current
  unimplemented claim of an enabled Windows Light runner with a global mutex
  and handle-based live execution, or mark it explicitly as disabled future
  scope.
- Verification contract and validator must enforce the shared error code,
  `writes_started: false`, trusted platform detection, zero side-effect edges,
  and unchanged Linux invariants.
- The live validator registers `azure_activation_contract.py`,
  `azure_activation_facade.py`, `test_windows_offline_cli_portability.py`, and
  `windows-portability.yml` as required sources. The S4f validator registers
  the portable adapter import and its platform block. Both validators receive
  negative validator tests for contract or workflow drift.
- The validator structurally verifies: Windows is exactly offline-only; live,
  recovery, and reconciliation are blocked there; Linux with complete
  security capabilities remains the only
  live backend; the old Windows Light runner is disabled; no active contract
  field advertises handle-based Windows execution or a Windows mutex; error
  code and `writes_started: false` are exact.
- The validator also verifies workflow name `NaC Windows Portability`, job
  `windows-offline-cli`, `windows-latest`, Python 3.11, the exact test command,
  absence of `continue-on-error`, secrets, login, and live commands, and
  coverage markers for every public edge and all seven prohibited side-effect
  categories. A validator test must fail if any of those markers is weakened.
- DE/EN CLI documentation and minimum requirements receive a short, identical
  support matrix: Windows `offline`; Linux with every required security
  capability `offline + live`; Windows, other POSIX systems without complete
  capabilities, and unknown platforms `blocked` for live/recovery/
  reconciliation.
- Mark the former DE/EN Windows Light spec as superseded by #744 for the
  current delivery scope; it must no longer imply current Windows live support.
- Add spec, plan, code, contract, validator, tests, and CI to
  `agent-context/index.json`. Do not make artificial policy, SBOM, or Gantt
  changes; only check the existing Windows/Python SBOM entries and record the
  result in PR evidence.

### 8. Add Native Windows CI

- Add `.github/workflows/windows-portability.yml` with workflow name
  `NaC Windows Portability`, PR/push triggers without path filters, and job name
  `windows-offline-cli`.
- Run on `windows-latest`, configure Python 3.11, install the repository without
  a new dependency, and run at least
  `python -m unittest tests.test_windows_offline_cli_portability
  tests.test_spfx_bff_catalog_readback_regression`.
- No `continue-on-error`, secret, sign-in, or live smoke.
- The resulting check context
  `NaC Windows Portability / windows-offline-cli` must pass on the PR. After
  the context has appeared for the first time, adding it to branch protection
  or the repository ruleset requires a separate exact owner/admin gate. Only
  after that approval is the configuration changed and then verified read-only
  to confirm that the context is actually required.
- Real child-process smokes use a poisoned sentinel `PATH`, isolated temporary
  home/credential/config locations, child-emitted import tracing, and network/
  subprocess guards installed inside the child. In-process call counts augment
  these proofs but do not replace them.

### 9. Implementation Review and Fix Loop

- Send the complete working diff to isolated read-only reviews: platform/policy
  for the fail-closed boundary, validation for AC/CI coverage, and docs for
  DE/EN parity.
- Every finding includes severity, affected edge, and concrete evidence.
- Fix blocking and medium findings before acceptance, then ask the same
  reviewers to verify the corrections.
- Do not perform tenant, provider, credential, live, recovery, or
  reconciliation actions during review.

### 10. Local and Remote Acceptance

- Windows: `python -m unittest tests.test_windows_offline_cli_portability
  tests.test_spfx_bff_catalog_readback_regression`.
- Linux activation: `python -m unittest
  tests.test_nac_bff_azure_activation_cli tests.test_nac_bff_azure_live_commands
  tests.test_nac_bff_azure_activation_composition
  tests.test_nac_bff_azure_activation_runner
  tests.test_nac_bff_azure_interruption_reconciliation
  tests.test_nac_bff_azure_function_deployment_reconciliation
  tests.test_m365_azure_bff_live_activation_contract
  tests.test_spfx_bff_catalog_readback_regression`.
- Linux S4f: `python -m unittest
  tests.test_business_case_type_production_adapters
  tests.test_business_case_type_production_adapters_contract
  tests.test_business_case_type_production_adapters_cli
  tests.test_sqlite_evidence_staging_outbox`.
- Then run `python scripts/validate_m365_azure_bff_live_activation.py`,
  `python scripts/validate_business_case_type_production_adapters.py`, both
  agent-context validators, `graft build`, `graft check`, and
  `python scripts/nac.py doctor --profile strict`.
- Spec traceability, language parity, link validation, and every registered
  contract validator must pass.
- Before push and PR completion, inspect the file list, commit list, and full
  `origin/main...HEAD` diff; remove unauthorized scope.
- Commit and—as a visible YELLOW/batch-approved action—push
  `codex/744-windows-offline-cli`; then create a protected PR with `Closes
  #744` under the same clearly bounded approval, without auto-merge.
- After the Windows context first succeeds, present the exact branch-
  protection/ruleset change as a separate owner/admin gate. Without approval,
  make no governance mutation and do not complete AC-744-07.
- After approval, add the context as a required check and verify the
  configuration read-only; only then use `gh pr checks --required --watch`.
- Wait for the four exact remote check contexts: Windows Portability, Secret
  Scan, Privacy Lint, and NaC Quality Gate. The PR is review-ready only when all
  pass; merge remains separately owner/role gated.
- Before merge or completion of the Protected PR delivery mode, human-approval
  evidence must traceably identify a role permitted by the role model,
  especially `prozessverantwortung` or `freigabeverantwortung`. If that proof
  is absent, stop and do not merge.

## AC-to-Evidence Matrix

| AC | Primary evidence | Additional evidence |
| --- | --- | --- |
| AC-744-01 | Windows test: real import plus three help invocations on Python 3.11 | `NaC Windows Portability / windows-offline-cli` |
| AC-744-02 | Parameterized Windows smokes for `validate`, `plan`, and `bpmn-viewer-plan` with exit/status/guard assertions | Exclusively synthetic default artifacts and POSIX backend absent |
| AC-744-03 | Parameterized live edges with platform code, `writes_started is False`, and zero calls for credentials, state, locks, subprocesses, network, tenant, and provider | Redaction assertions and backend absent from `sys.modules` |
| AC-744-04 | Parameterized recovery/reconciliation edges and manipulated platform hints | Same zero side-effect edges as AC-744-03 |
| AC-744-05 | Production-adapter import and sealed-execution block on Windows | Zero invocations of `gh`, `gh.exe`, Azure CLI, and M365 CLI |
| AC-744-06 | Exactly listed Linux activation, runner, composition, reconciliation, SPFx, and S4f suites | Both contracts and validators plus strict doctor |
| AC-744-07 | Traceability/language/link validators, Graft, and strict doctor | Full `origin/main...HEAD` review and four successful remote checks |

## Stop Conditions

Implementation stops and requests new owner input if:

- a safe Windows offline facade would require weakening a POSIX live security
  contract;
- a new package, external provider, tenant access, or credential/secret action
  becomes necessary;
- scope expands to Windows live activation or Windows recovery;
- the complete PR diff contains unrelated or unauthorized scope;
- mandatory remote checks fail and remediation would fall outside the approved
  #744 surfaces.
- the new Windows context must be added as a required check after its first run
  but exact owner/admin approval for that branch-protection/ruleset change is
  absent.

## Outside This Plan

No app-catalog upload, SharePoint deployment, Graph/Azure/M365 read or write,
sign-in, credential read, recovery execution, Windows live backend, merge, or
automatic approval.
