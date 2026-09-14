# Windows Offline CLI Portability

Status: Spec and implementation plan approved by owner, implementation in progress

Date: 14 September 2026
Leading issue: [#744](https://github.com/notariat8/NaC/issues/744)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: windows-offline-cli-portability
leading_issue: https://github.com/notariat8/NaC/issues/744
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-09-14-windows-offline-cli-portability.md
review_gates:
  - Security
  - Platform
  - Validation
  - Human Approval
acceptance_ids:
  - AC-744-01
  - AC-744-02
  - AC-744-03
  - AC-744-04
  - AC-744-05
  - AC-744-06
  - AC-744-07
validation_commands:
  - python -m unittest tests.test_windows_offline_cli_portability
  - python -m unittest tests.test_spfx_bff_catalog_readback_regression
  - python -m unittest tests.test_nac_bff_azure_activation_cli tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_composition tests.test_nac_bff_azure_activation_runner tests.test_nac_bff_azure_interruption_reconciliation tests.test_nac_bff_azure_function_deployment_reconciliation tests.test_m365_azure_bff_live_activation_contract tests.test_spfx_bff_catalog_readback_regression
  - python -m unittest tests.test_business_case_type_production_adapters tests.test_business_case_type_production_adapters_contract tests.test_business_case_type_production_adapters_cli tests.test_sqlite_evidence_staging_outbox
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git diff --name-status origin/main...HEAD
  - git log --oneline origin/main..HEAD
  - git diff origin/main...HEAD
  - git diff --check origin/main...HEAD
  - gh pr checks --required --watch
```

## Starting Point

The central `nac` CLI currently cannot even be imported on Windows for purely
offline checks. POSIX-only imports such as `fcntl` and `pwd` are loaded during
module import although their hardened live functions are never invoked. Local
M365 and SPFx checks therefore fail before command selection.

The existing live activation path is deliberately bound to POSIX security
mechanisms such as sealed in-memory binaries, ownership checks, and
process-wide locks. Those guarantees must not be weakened by a superficially
compatible Windows substitute.

## Decision

NaC receives a portable offline facade and a dynamically separated POSIX live
backend. The facade contains only platform-neutral contracts, data types,
error codes, and capability decisions. The POSIX backend is loaded only after
the facade has classified the requested operation as permitted on the current
platform.

Windows thereby supports the central CLI and local M365/SPFx checks. Live
activation and recovery remain explicitly blocked on Windows and terminate
with the stable, redacted error code
`PLATFORM_SECURITY_BACKEND_UNAVAILABLE`. This termination must happen before
reading credentials, touching state or lock files, starting subprocesses, or
performing network or provider access.

## Scope

- Portable, side-effect-free activation contracts and capability evaluation in
  a platform-neutral importable module under
  [`src/nac_bff/`](../../../../src/nac_bff/).
- A portable callable facade for the public live, recovery, and reconciliation
  entries; it rejects first and dynamically loads the Linux backend only after
  successful capability evaluation.
- Dynamic loading of the existing POSIX live backend only behind a successful
  platform and capability evaluation.
- Importability of the central [`nac` CLI](../../../../src/nac_cli/cli.py) and
  the local M365/SPFx offline smokes defined below on native Windows and
  Python 3.11.
- Importability of the M365 production adapters on Windows while their
  POSIX-bound sealed execution remains fail closed.
- Windows CI for imports, help, offline checks, and negative live/recovery
  tests, plus unchanged Linux verification of the POSIX backend.
- Traceable links among the issue, spec, plan, AC IDs, and validation evidence.

## Non-Goals

- No Windows live activation and no Windows recovery.
- No replacement of `memfd`, `fcntl`, `pwd`, POSIX ownership checks, mount
  namespaces, or binary binding with weaker Windows mechanisms.
- No `gh.exe`, Azure CLI, Microsoft 365 CLI, or other subprocess fallback for
  blocked Windows live paths.
- No credential request or sign-in.
- No tenant action, read or write, and no provider action.
- No app catalog installation or SharePoint deployment.
- No change to owner gates, locking semantics, hash/binary bindings, ledger,
  evidence, or approval contracts.
- No reactivation of the archived OCI release path.

## Architecture

### Portable Offline Facade

A new platform-neutral contract module, intended as
`src/nac_bff/azure_activation_contract.py`, owns at least:

- the stable data types `ActivationStepError`, `ActivationContext`, and
  `LiveActivationRequest` where shared by the CLI, tests, and composition;
- the stable error code `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`;
- a pure capability decision with no file, process, credential, network, or
  provider access;
- an unambiguous classification of offline, live, and recovery operations.

Importing the facade must not transitively load any POSIX-only module.
The platform decision comes exclusively from trusted runtime detection.
Request, CLI, configuration, and environment values may neither override it
nor impersonate a POSIX capability.

A separate portable callable module, intended as
`src/nac_bff/azure_activation_facade.py`, owns the public functions named in
the negative-test matrix. On a disallowed platform it returns the shared error
without loading runner or composition. On admitted Linux it imports the
existing implementations only after capability evaluation.

### POSIX Live Backend

The existing hardened live runner remains the only backend for live activation
and recovery. Its security guarantees remain unchanged. The composition layer
loads it dynamically and only when the portable capability evaluation has
admitted the current platform. Failure to load or validate the backend is
terminal and fail closed.
Runtime admission is narrower than the module name: live execution is allowed
only on Linux with all required `memfd`, `/proc`, ownership, locking,
namespace, and no-follow capabilities. Without complete evidence, other POSIX
systems are treated as not live-capable just like Windows.

### Production Adapters

[`business_case_type_production_adapters.py`](../../../../src/nac_m365_graph/business_case_type_production_adapters.py)
must no longer treat `fcntl` as a prerequisite for mere module import. The
actual sealed GitHub execution remains bound to the existing Linux `memfd`
path. If that platform capability is absent, the same stable platform error is
returned before secret or subprocess access. No weaker Windows execution path
is introduced.

## Execution Flows

### Windows Offline

1. Python loads the central CLI and portable facade.
2. The parser selects an offline command, such as a local M365/SPFx contract
   check.
3. Only local, non-secret inputs and repository artifacts are processed.
4. The command returns its normal result; the POSIX live backend was never
   imported or loaded.

The mandatory Windows offline matrix uses the committed default artifacts
[`nac-mvp.teams-sharepoint.json`](../../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json)
and
[`nac-bpmn-viewer.provisioning.json`](../../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json):

| Invocation | Expectation |
| --- | --- |
| `python -c "import nac_cli.cli"` | Exit `0`; no import of `fcntl`, `pwd`, or the POSIX live backend |
| `python scripts/nac.py --help` | Exit `0` |
| `python scripts/nac.py m365 --help` | Exit `0` |
| `python scripts/nac.py m365 teams-sharepoint --help` | Exit `0` |
| `python scripts/nac.py m365 teams-sharepoint validate --format json` | Exit `0`; `status: PASSED` |
| `python scripts/nac.py m365 teams-sharepoint plan --format json` | Exit `0`; `status: PASSED` |
| `python scripts/nac.py m365 teams-sharepoint bpmn-viewer-plan --format json` | Exit `0`; `status: PASSED`; `mutates_tenant_now: false` and `live_apply_implemented: false` |

Every matrix case must additionally prove zero credential, network, and
provider calls and that the POSIX live backend was not loaded.

### Windows Live or Windows Recovery

1. Python loads the central CLI and portable facade.
2. Capability evaluation identifies a live or recovery operation on Windows.
3. Execution terminates with `PLATFORM_SECURITY_BACKEND_UNAVAILABLE` and
   `writes_started: false`.
4. No credential, state, lock, subprocess, network, or provider access occurred
   first; the POSIX live backend was not loaded.

The finite negative-test matrix covers these public edges:

| Class | Public edge |
| --- | --- |
| CLI live | `m365 teams-sharepoint bff-azure-activate-live` |
| CLI recovery | `m365 teams-sharepoint bff-azure-activation-recovery` |
| CLI reconciliation | `m365 teams-sharepoint bff-azure-activation-interruption-reconcile` |
| CLI reconciliation | `m365 teams-sharepoint bff-azure-function-deployment-reconcile` |
| Python live | `nac_bff.azure_activation_facade`: `run_azure_bff_live_activation` and `build_live_activation_execution_port` |
| Python recovery | `nac_bff.azure_activation_facade`: `reconcile_azure_bff_live_activation_lock` |
| Python reconciliation | `nac_bff.azure_activation_facade`: `build_interruption_reconciliation_ports` and `build_function_deployment_reconciliation_ports` |

Every case expects the same error code, `writes_started is False`, exactly zero
calls to every prohibited side-effect edge, and a POSIX backend absent from
`sys.modules`. A manipulated platform or capability hint from a request, CLI,
configuration, or environment value is included as an additional negative
case.
For all four CLI edges, this platform rejection takes precedence over missing
owner arguments, detailed parser validation, and approval validation. Error
precedence is therefore identical for every recognized public command on
Windows.

### POSIX Live

1. The portable facade classifies the operation and admits the existing POSIX
   security backend.
2. The composition layer loads the backend dynamically.
3. All existing owner, attestation, locking, ownership, binary-binding, ledger,
   and evidence checks remain effective.
4. Existing live validators and negative tests must continue to pass
   unchanged.

## Error and Security Contract

- The public platform error is stable, structured, and redacted.
- For this platform rejection, the CLI payload has exactly the keys
  `schema_version`, `status`, `error`, and `writes_started`; `status` is
  `BLOCKED` and `error` contains only `code`.
- The error contains no credential paths, tokens, environment values, or
  provider responses.
- `writes_started` is always `false` for the Windows platform rejection.
- Unknown platforms, missing backend capabilities, or security-backend import
  errors are not interpreted as offline approval.
- Tests instrument every prohibited side-effect edge and fail if Windows live
  activation or recovery reaches any of them.

## CI and Validation Design

A native Windows CI lane verifies at least:

- import of the central CLI and its M365/SPFx dependencies;
- help and parser paths without POSIX import failures;
- selected offline M365/SPFx validators;
- negative live and recovery tests with guard doubles for credentials, state,
  locks, subprocesses, network, and providers;
- the stable error code and `writes_started: false`;
- production-adapter importability without activating sealed execution.

It runs as the GitHub Actions job `windows-offline-cli` in the workflow
`NaC Windows Portability` on `windows-latest` with Python 3.11. The stable
check context is `NaC Windows Portability / windows-offline-cli` and must pass
in the protected PR. The lane runs
`python -m unittest tests.test_windows_offline_cli_portability`; that test
module maps AC-744-01 through AC-744-05 completely and parametrically. All
fixtures are exclusively synthetic and contain no tenant, customer, matter, or
credential data.

The existing Linux lane continues to test the real POSIX live backend and its
complete security contracts. Windows success must neither replace nor bypass
Linux gates. Both lanes are treated as mandatory quality gates in the
protected PR.

## Acceptance Criteria

- **AC-744-01:** On `windows-latest` with Python 3.11, the central `nac` CLI
  passes the import and all three help invocations defined by the Windows
  offline matrix without `fcntl`, `pwd`, or other POSIX import errors.
- **AC-744-02:** `validate`, `plan`, and `bpmn-viewer-plan` pass on Windows with
  the defined default artifacts, exit codes, and status values; they do not
  load the POSIX live backend or reach a credential, network, tenant, or
  provider edge.
- **AC-744-03:** Every Windows live edge named in the negative-test matrix terminates stably with
  `PLATFORM_SECURITY_BACKEND_UNAVAILABLE`, `writes_started: false`, and no
  credential, state, lock, subprocess, network, or provider access.
- **AC-744-04:** Every Windows recovery and reconciliation edge named in the
  negative-test matrix satisfies the same fail-closed boundary as AC-744-03;
  platform hints from untrusted inputs cannot bypass the block.
- **AC-744-05:** Production adapters import on Windows; their POSIX-bound
  sealed execution remains blocked before every side-effect edge named in
  AC-744-03. Guards confirm zero invocations of `gh`, `gh.exe`, Azure CLI, and
  Microsoft 365 CLI.
- **AC-744-06:** POSIX live and recovery contracts, including ownership checks,
  `fcntl` locking, sealed `memfd` execution, binary/toolchain binding,
  recovery, and pre-write guards pass in the Linux lane through the existing
  complete activation and production-adapter suites. Those security tests are
  neither deleted, renamed, nor weakened.
- **AC-744-07:** Spec traceability, German/English parity, Windows CI, Linux CI,
  and the strict NaC quality gate pass. The file and commit lists are reviewed;
  the complete output of `git diff origin/main...HEAD` receives content review,
  and `git diff --check origin/main...HEAD` passes.
  `gh pr checks --required --watch` confirms at least
  `NaC Windows Portability / windows-offline-cli`,
  `Privacy and Secrets Guard / secret-scan`,
  `Privacy and Secrets Guard / privacy-lint`, and
  `NaC Quality Gate / quality-gate` as successful.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| A transitive import still loads the POSIX backend on Windows. | Import-isolation test and guards against `fcntl`, `pwd`, and the backend module. |
| An early CLI helper accesses state or credentials before capability evaluation. | Instrument side-effect edges with failing test doubles and explicitly test ordering. |
| Separation unintentionally changes Linux live behavior. | Run existing Linux contract tests unchanged and do not reimplement backend logic. |
| An optional import is mistaken for security approval. | Capability evaluation is explicitly deny by default; backend failures are terminal. |
| Documentation suggests Windows live capability. | CLI and operations documentation describe Windows exclusively as an offline facade. |

## Delivery and Operation

Implementation proceeds exclusively through a protected pull request to the
target branch. Before review, the complete file list, commit list, and
`base...head` diff are inspected. There is no automatic merge and no live
activation within this issue.

After this spec is approved, the implementation plan is created in both
languages, linked in the traceability block, and maps every AC to a concrete
test, validator, or remote check. Human-approval evidence must traceably name
an approval role permitted by the role model.

The change introduces no new runtime dependency or external provider, so no
SBOM/AI-SBOM extension is planned. It changes neither roadmap, product scope,
nor milestone and therefore needs no artificial Gantt update.
Before PR completion, the evidence also records that the existing Windows and
Python entries in the SBOM/AI-SBOM were checked and that no component or
boundary delta exists.

## Related Artifacts

- [Windows Light Runner – Design Spec](2026-08-09-windows-light-runner-design.md)
- [`m365-azure-bff-live-activation.contract.json`](../../../../workflows/contracts/m365-azure-bff-live-activation.contract.json)
- [CLI documentation](../../cli.md)
- [Minimum requirements](../../minimum-requirements.md)
- [`technology-policy.yaml`](../../../../policies/technology-policy.yaml)
- [`data-protection-policy.yaml`](../../../../policies/data-protection-policy.yaml)
