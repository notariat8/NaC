# Windows-Native Current-State Diagnostics for Teams and BFF Access

Status: Repository and synthetic implementation complete; acceptance, merge, SPFx deployment, and the real provider run each remain separately approval-gated

Date: 20 September 2026

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Starting point: merge commit `80bf813375d7fc2ab292dfdbcc1db447fdb6684a`,
tree `007e277ca5643f7cb63355961fd0422d92fd4b87`, merged
[PR #747](https://github.com/notariat8/NaC/pull/747)

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-current-state-access-diagnostic
plan: docs/en/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md
leading_issue: https://github.com/notariat8/NaC/issues/748
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Secrets
  - Platform
  - Policy
affected_artifacts:
  - docs/de/superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md
  - docs/en/superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md
  - docs/de/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md
  - docs/en/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md
  - docs/de/cli.md
  - docs/en/cli.md
  - docs/de/quality-gate.md
  - docs/en/quality-gate.md
  - docs/de/m365-current-state-access-diagnostic.md
  - docs/en/m365-current-state-access-diagnostic.md
  - agent-context/index.json
  - .github/workflows/windows-portability.yml
  - assets/docs/generic-workbench/VIS-721-manifest.json
  - workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml
  - workflows/contracts/spec-traceability.contract.json
  - scripts/validate_m365_current_state_access_diagnostic.py
  - scripts/validate_generic_workbench_foundation.py
  - scripts/validate_spec_traceability.py
  - scripts/quality_gate.py
  - src/nac_bff/current_state_access_diagnostic.py
  - src/nac_bff/current_state_access_gate.py
  - src/nac_bff/current_state_access_ports.py
  - src/nac_bff/current_state_access_adapters.py
  - src/nac_bff/current_state_access_composition.py
  - src/nac_bff/current_state_access_client_receipt.py
  - src/nac_bff/activation_security_backend.py
  - src/nac_bff/azure_live_commands_win.py
  - src/nac_cli/cli.py
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.tsx
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.test.tsx
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacWorkbenchHost.styles.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.test.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientObservationReceipt.ts
  - spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/ClientObservationReceipt.test.ts
  - spfx/nac-bpmn-viewer/scripts/generate-workbench-live-read-visual-fixture.cjs
  - spfx/nac-bpmn-viewer/scripts/capture-workbench-live-read-visual-evidence.cjs
  - scripts/validate_workbench_live_read_binding.py
  - workflows/contracts/workbench-live-read-binding.contract.json
  - assets/docs/workbench-live-read-binding/VIS-725-01-desktop-ready.png
  - assets/docs/workbench-live-read-binding/VIS-725-02-narrow-spfx-ready.png
  - assets/docs/workbench-live-read-binding/VIS-725-03-mobile-ready.png
  - assets/docs/workbench-live-read-binding/VIS-725-04-loading.png
  - assets/docs/workbench-live-read-binding/VIS-725-05-deny.png
  - assets/docs/workbench-live-read-binding/VIS-725-06-unavailable.png
  - assets/docs/workbench-live-read-binding/VIS-725-manifest.json
  - docs/de/sbom-for-ai.md
  - docs/en/sbom-for-ai.md
  - tests/test_m365_current_state_access_diagnostic.py
  - tests/test_m365_current_state_access_client_receipt.py
  - tests/test_m365_current_state_access_gate.py
  - tests/test_spec_traceability.py
  - tests/test_validate_generic_workbench_foundation.py
  - tests/test_validate_workbench_live_read_binding.py
  - tests/test_nac_cli.py
  - tests/test_windows_offline_cli_portability.py
acceptance_ids:
  - AC-748-01
  - AC-748-02
  - AC-748-03
  - AC-748-04
  - AC-748-05
  - AC-748-06
  - AC-748-07
  - AC-748-08
validation_commands:
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/validate_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_client_receipt.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
  - python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
  - python -m unittest discover -s tests -p test_nac_cli.py
  - python -m unittest discover -s tests -p test_windows_offline_cli_portability.py
  - python -m unittest discover -s tests -p test_spec_traceability.py
  - cd spfx/nac-bpmn-viewer && npm run build
  - powershell -NoProfile -Command "$genericRoot = Join-Path $env:TEMP 'nac-generic-workbench'; Push-Location spfx/nac-bpmn-viewer; try { npm run workbench:capture -- $genericRoot } finally { Pop-Location }"
  - powershell -NoProfile -Command "$liveRoot = Join-Path $env:TEMP 'nac-workbench-live-read'; Push-Location spfx/nac-bpmn-viewer; try { npm run workbench:live:capture -- $liveRoot } finally { Pop-Location }"
  - powershell -NoProfile -Command "python scripts/validate_generic_workbench_foundation.py --generated-evidence-root (Join-Path $env:TEMP 'nac-generic-workbench')"
  - powershell -NoProfile -Command "python scripts/validate_workbench_live_read_binding.py --generated-evidence-root (Join-Path $env:TEMP 'nac-workbench-live-read')"
  - python -m unittest discover -s tests
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git status --short
  - git diff --check origin/main...HEAD
  - git diff --name-status origin/main...HEAD
  - git diff --stat origin/main...HEAD
  - git diff origin/main...HEAD
  - git log --oneline origin/main..HEAD
```

## Purpose

This specification defines a new read-only diagnostic path for the synthetic
workspace `notary_team_01` and the Teams app “NaC Vorgangsansicht”. The path
must reproducibly map the visible message “Kein Zugriff auf diesen
Arbeitsbereich” to one of four classes:

1. `SPFX_SUBJECT_MISSING`: the SPFx component receives no usable Entra user ID
   and therefore starts no BFF request.
2. `BFF_REQUEST_NOT_OBSERVED`: a user and UI context exists, but no matching
   BFF request is proven in the exactly bound observation window.
3. `BFF_AUTHENTICATION_REJECTED_401`: the BFF receives a request but rejects
   authentication.
4. `BFF_AUTHORIZATION_REJECTED_403`: the BFF accepts the identity but rejects
   business authorization or the bound request context.

The diagnostic is not a repair. It produces only redacted, hash-bound decision
evidence for a later separate fix and, if needed, activation assignment.

## Trust and Provenance Boundary

The new path is not a successor phase inside the old Issue #739 run chain. The
state `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` remains terminal with
`retry_allowed=false` and `next_phase=null`.

In particular, the diagnostic path must not:

- read, rebuild, or derive lost #739 artifacts from GitHub, model knowledge, or
  provider data;
- release or change a #739 journal;
- build an Issue #632 package or authorize a live run;
- reuse an old #746, #739, or #632 approval;
- infer successful or failed deployment from historical issue text.

The only shared provenance is documentary: Issue #748 references merged PR
#747 as its starting point and expressly retains the terminal old run. The new
path receives operational inputs only from its own final commit, tree,
contract, resolver, and owner gate.

## Evaluated Approaches

### A. New independent current-state diagnostic path — selected

An independent contract inspects only the present target state. It binds the
merged starting point correctly, requires a new approval before provider
access, and produces two redacted comparison snapshots. This preserves #739
provenance, enables unambiguous classification, and prevents premature tenant
mutation.

### B. Extend the terminal #739 path — rejected

A provider phase after `FUNCTION_DEPLOYMENT_PROVENANCE_LOST` would contradict
the merged verification contract and suggest that lost evidence could be
reconstructed. That is prohibited.

### C. Manual diagnostics with individual Azure, Graph, and browser commands — rejected

Ad-hoc reads would have no shared commit, principal, toolchain, or snapshot
binding. They could mutate credentials or caches, disclose unredacted data,
and would not be reproducible. They are not a substitute for the productive
diagnostic contract.

## Post-Merge Binding

The existing Issue #746 gate requires local HEAD to equal the former PR head.
That equality cannot hold after a merge commit. The new contract models this
relationship instead:

```text
approved_base_merge_commit = 80bf813375d7fc2ab292dfdbcc1db447fdb6684a
approved_base_tree         = 007e277ca5643f7cb63355961fd0422d92fd4b87
merged_pr                  = 747
merged_pr_head             = 25962846903b672d3bc5b5507f6c76089256891d
merged_pr_merge_commit     = approved_base_merge_commit
diagnostic_final_head      = final commit from Issue #748
diagnostic_final_tree      = tree of that final commit
```

The gate proves through GitHub semantics that PR #747 is merged and that its
merge commit equals the approved starting point. The final diagnostic HEAD
must descend from that base on the Issue #748 branch. It need not and must not
be falsely equated with the historical PR head.

Before the first external read, the gate binds at least:

- repository `notariat8/NaC`, Issue #748, and the new draft PR;
- base merge commit and base tree;
- final diagnostic commit and tree;
- complete `main...HEAD` scope and mandatory checks;
- verification contract and validator;
- Windows security backend and attested toolchain;
- protected repository-external resolver and its SHA-256;
- operator account and stable principal;
- exact canonical `OWNER_SOLO_APPROVAL` comment;
- workspace `notary_team_01`, Teams app, and permitted target resources.

A concrete, applicable, cited external two-person obligation produces
`BLOCKED_SINGLE_PRINCIPAL` when only one principal is available. Without such
an obligation, `OWNER_SOLO_APPROVAL` is permitted and expressly is not
four-eyes approval.

## Evidence Ports and Permitted Read Operations

The productive diagnostic path has a closed port list. An adapter may execute
only the operation below; general directory, tenant, resource, or log search is
prohibited:

| Port | Permitted read | Reduced output |
| --- | --- | --- |
| `ClientObservationReceiptPort` | read an existing repository-external protected host-context receipt for the fixed observation window | UI state and Boolean `spfx_subject_available` |
| `TeamsTabMetadataReadPort` | Microsoft Graph GET for the exactly bound team, channel, and tab | app/tab contract match as Boolean and opaque version binding |
| `SharePointAppCatalogReadPort` | SharePoint/Graph GET for the exactly bound site and solution | deployed package version, package digest, and API-permission match |
| `EntraApiPermissionReadPort` | Graph GET for the pre-bound API and SPFx service principals | tenant, audience, scope, and preauthorization matches as Booleans |
| `AzureFunctionMetadataReadPort` | Azure Resource Manager GET for the exactly bound Function App | deployment/configuration class and bound digests |
| `AzureFunctionRequestLogReadPort` | Application Insights/Log Analytics read for the completed fixed window and correlation binding | request observed, 401, 403, or other status as a closed enum |
| `SharePointAccessDecisionReadPort` | Graph/SharePoint GET only for bound synthetic matter, role, delegation, and audit rows | Boolean matches for the server-side access decision only |

Real IDs and resource names originate only in the protected external target and
resolver contract and appear in neither CLI arguments nor GitHub, CI, or
persisted diagnostic output. Every port receives an immutable authorization
capability containing the provider-qualified `account_id`, provider, tenant,
concrete account permission, target resource, principal, and run binding. A
different account of the same principal blocks; principal equivalence does not
extend provider permission.

The client receipt is created before the provider run from an
operator-triggered Teams/SPFx host context. It may contain only the constant
neutral UI state `no_access`, the Boolean `spfx_subject_available`, closed UTC
window bounds, a canonically derived window binding, and the SHA-256 binding
of a random correlation ID. Object IDs, subject values, names, email
addresses, tenant data, tokens, headers, request contents, and other personal
or authenticating data are prohibited; unknown fields block.

The correlation ID is generated exactly once with cryptographically secure
browser randomness when observation starts. If an SPFx subject is available,
the existing BFF request uses exactly that ephemeral raw value as
`X-Correlation-ID`; if no subject is available, the raw value never leaves the
client. In both cases, the receipt persists only the SHA-256 binding. If Web
Crypto is unavailable, the state is not terminally closed, or the raw value
cannot be discarded after single use, no receipt is produced and the later
path blocks with `BLOCKED_CLIENT_OBSERVATION_UNAVAILABLE`.

### Selected Repository-External Transfer Path

The browser cannot write an arbitrary local directory. The selected path is
therefore two-stage and entirely local:

1. After the terminal neutral error state, the web part offers an explicitly
   operator-triggered download of a canonical JSON file with a fixed,
   person-free filename. There is no automatic download, network transfer, or
   telemetry.
2. A dedicated offline `nac` CLI surface validates size, UTF-8, exact field
   set, time window, hash formats, and privacy prohibitions, then exclusively
   materializes the receipt in a repository-external, SID/DACL-protected Issue
   #748 input directory. It does not overwrite an existing receipt and performs
   no login, network, or provider access.

A localhost bridge service is rejected because it adds process, CORS, and
attack surface. Clipboard, DevTools, and manual transcription are rejected for
lack of durability, binding, and reproducibility. If the actually deployed
SPFx package and source binding cannot be proven read-only, the later run still
ends with `BLOCKED_DEPLOYED_CLIENT_BINDING_UNAVAILABLE` instead of guessing a
class.

The observation window is fixed and closed before diagnostic reads begin. No
new Teams, browser, or BFF request is triggered during the two provider
captures. Both captures independently read the same historical window bounds
and correlation binding. Direct BFF smoke requests are outside this contract
because they would change the state being investigated.

## Privacy, DPA, and Local Evidence Boundary

Although the workspace is synthetic, the later real run processes pseudonymous
operator and authorization metadata. Before port factory and network access,
the gate therefore binds a repository-external SID/DACL-protected privacy
receipt containing:

- an applicable and valid DPA status; non-applicability is permitted only when
  a specifically cited superior legal or policy basis establishes that
  exception for this exact SaaS-processing scope;
- provider, tenant, purpose, and permitted data extent;
- exactly `policies/data-protection-policy.yaml` and its digest recomputed from
  the bound repository blob;
- a separate protected DPA agreement evidence document whose digest is bound
  by the receipt and whose effective status, validity window, Microsoft
  provider, tenant, and target are rechecked before every read;
- retention and deletion period for diagnostic evidence;
- approval status for exactly Issue #748 and the one read-only run.

A missing or changed receipt produces `BLOCKED_DPA_AVV_BINDING` before any port
is created. The receipt itself and real contract details are not stored in Git
or GitHub.

A pre-opened, repository-external, SID/DACL-protected evidence sink is the only
permitted local mutation. The provider process receives only its handle as a
write capability; ordinary file, credential, cache, and configuration stores
remain technically non-writable through the Windows security backend.
Allowlisted, non-content credential/configuration metadata is bound unchanged
before and after the run. It may include only owner/SID/DACL, file and volume
ID, reparse/hardlink status, size, timestamps, USN, or equivalent non-content
OS metadata. Credential contents, token values, credential-store bytes, and
their hashes must not be read, copied, exported, persisted, or compared. If
this OS-enforced restriction cannot be established, the run blocks before the
first read. Self-reported counters alone are insufficient.

A stable principal ID and its unsalted hash are not persisted. The local
evidence sink uses a random one-time run nonce and a run-bound HMAC binding
protected only there. Public result surfaces contain neither that binding nor
resolver, account, or principal values, only the diagnostic class,
contract/artifact digest, and zero-side-effect status.

The evidence sink also contains a repository-external SID/DACL-protected run
gate entry. It binds approval digest, final commit and tree, contract,
resolver, provider-qualified account, principal, and scope, and is atomically
changed from `unused` to `consumed` before port factory. An already consumed,
parallel, or post-crash ambiguous entry blocks without resumption. A new nonce
does not make an old approval reusable. Parallel invocation, sequential
repeat, crash after consume, replay of the same approval, and a new nonce with
an old approval are mandatory negative tests with `port_factory=0`,
`network_read=0`, and all mutation counters `0`. A new attempt requires a new
exactly bound run-gate entry and a new approval.

## Governance Negative Matrix

The verification contract and tests must model at least these cases in
machine-readable form:

| Case | Expected result before port/network access |
| --- | --- |
| multiple provider-qualified accounts with the same `principal_id` | never four-eyes; no independent approver |
| uncited, inapplicable, or role-label-only two-person claim | reject as requirement; invent no duty |
| permitted solo decision | `OWNER_SOLO_APPROVAL` and `four_eyes_satisfied=false` |
| concretely cited applicable two-person duty with one principal | `BLOCKED_SINGLE_PRINCIPAL`, `port_factory=0`, `network_read=0`, all mutation counters `0` |
| different provider account of the same principal from the bound operator | `BLOCKED_ACCOUNT_BINDING`, no extension of account permission |

This matrix is part of AC-748-04 and must not be implemented only as prose or
role labels.

## Phase Model

### Phase 0: repository implementation

Specification, plan, contract, CLI, ports, validators, tests, and documentation
are implemented on Windows against synthetic fixtures only. Provider, network,
login, credential, deployment, #739, and #632 counters remain zero. The draft
PR is pushed only after local validation and evaluated by mandatory remote CI.

### Phase 1: final diagnostic gate

After green CI, a new `OWNER_SOLO_APPROVAL` evidence record is bound exactly to
the final diagnostic HEAD. Specification or plan approval is insufficient.
Missing resolver, provider-qualified operator account, principal, concrete read
permission, DPA binding, GitHub semantics, or mandatory checks block before port
factory, credential, and network access.

### Phase 2: local Windows preflight

In a sanitized environment, the preflight verifies commit, tree, scope,
contract, toolchain, Windows handles, file and volume IDs, SID, DACL, reparse
points, resolver, provider-qualified account, principal, concrete read
permission, DPA receipt, and approval. It also proves that no #739 or #632
artifact is used as input and that only the pre-bound protected external
evidence sink is writable.

### Phase 3: one read-only diagnostic run

A separately approved run uses existing authentication contexts only. Login,
device code, browser authentication, credential export, token import,
token refresh, credential write, cache creation, and configuration change are blocked. If an
adapter cannot technically prove freedom from writes, it blocks before
provider access.

The run captures exactly two snapshots with the same target binding and the
same observation-window contract. Every provider port revalidates run
authorization before every read. A redirect, authentication requirement,
unknown field, unexpected mutation, or unredactable response ends the run
without retry.

### Phase 4: diagnostic result

Only two byte-identically canonicalized snapshot projections with the same
SHA-256 produce one of the four permitted diagnostic classes. Every other
state returns `BLOCKED` with a narrow error code and `retry_allowed=false`.

The result authorizes only creation of a new fix plan. It authorizes no
productive change and no second diagnostic or live run.

## Snapshot Contract

Raw responses are reduced immediately in memory to a closed allowlist. Only
classifications, Boolean proofs, completely defined counters,
observation-window boundaries, and opaque run-bound bindings may be persisted.
Tokens, headers, clear names, email addresses, real object IDs, tenant content,
and account-to-principal mappings must not be persisted.

Each of exactly two independent captures creates an `acquisition_envelope`.
Its sequence number and capture time may differ. Both envelopes, however,
reference the same already closed window boundaries, client receipt, and
correlation binding. A `decision_projection` is derived from each envelope.
Only that completely closed projection must be byte-identical and have the
same SHA-256. This proves two real reads rather than hashing the same stored
bytes twice.

The complete permitted contract is:

```yaml
schema_version: nac.m365-current-state-access-diagnostic/v0.1
acquisition_envelope:
  sequence: enum-1-2
  acquired_at_utc: canonical-utc-timestamp
  provider_read_receipt_sha256: sha256-hex
decision_projection:
  target:
    workspace_id: notary_team_01
    app_id: nac-vorgangsansicht
  bindings:
    final_head_sha256: sha256-hex
    final_tree_sha256: sha256-hex
    contract_sha256: sha256-hex
    resolver_sha256: sha256-hex
    account_run_binding: opaque-run-hmac
    principal_run_binding: opaque-run-hmac
    dpa_avv_binding_sha256: sha256-hex
  observation_window:
    start_utc: canonical-utc-timestamp
    end_utc: canonical-utc-timestamp
    window_binding_sha256: sha256-hex
    client_receipt_sha256: sha256-hex
    request_correlation_binding_sha256: sha256-hex
  observations:
    spfx_subject_available: boolean
    matching_bff_request_observed: boolean
    bff_http_class: enum-none-401-403
    delegated_scope_contract_matches: boolean
    access_decision_evidence_matches: boolean
  classification: enum-four-diagnostic-codes
  side_effect_counters:
    port_factory: nonnegative-integer
    network_read: nonnegative-integer
    run_gate_consume_write: nonnegative-integer
    result_evidence_write: nonnegative-integer
    login: 0
    device_code: 0
    browser_authentication: 0
    token_refresh: 0
    token_import: 0
    credential_export: 0
    credential_write: 0
    cache_write: 0
    configuration_write: 0
    redirect_follow: 0
    retry: 0
    second_real_run: 0
    tenant_write: 0
    provider_write: 0
    deployment: 0
    issue_739_release: 0
    issue_632_authorization: 0
decision_projection_sha256: sha256-hex
```

The type notation above describes the schema; real evidence contains only
calculated bindings and concrete enum values. `port_factory`, `network_read`,
`run_gate_consume_write`, and `result_evidence_write` are checked against the exact permitted values in the
verification contract. `network_read` counts only Microsoft provider-port
reads within an acquisition. The mandatory local Git and
credential-write-guarded GitHub gate revalidations run separately before every
port read and are not declared as Microsoft reads. Every other operational
counter must be zero. An
unknown key or disallowed count blocks canonicalization.

For `decision_projection_sha256`, only the fully closed `decision_projection`
object is canonicalized as UTF-8 JSON under RFC 8785 and hashed with SHA-256.
`schema_version`, the complete `acquisition_envelope`, and the hash field itself
are excluded. The first capture must use sequence `1` and the second sequence
`2`; their provider-read receipts must differ. `acquired_at_utc` may be equal
or different because of clock resolution, but must be after the window end,
within approval validity, and consistent with sequence order. Target, bindings,
window, observations, classification, and every counter in both decision
projections must be byte-identical.

Different window boundaries, client receipts, correlation bindings, or target
bindings, swapped or reused sequences, identical provider-read receipts, and
equal payloads with different bound window or projection provenance are
mandatory negative cases. A permitted difference in `acquired_at_utc` alone is
not projection drift. The fields
`issue_739_release` and `issue_632_authorization` are local zero invariants
only; checking them imports or reads no old modules, journals, comments, or
artifacts.

## Classification Logic

The order is binding and prevents ambiguous diagnoses:

1. If the protected client receipt for the read-only-bound actually deployed
   SPFx version proves `spfx_subject_available=false`, the result is
   `SPFX_SUBJECT_MISSING`. The two captures may then read only client, package,
   and no-request proof; a direct BFF request remains prohibited.
2. If the same client contract proves `spfx_subject_available=true` but no
   matching BFF request is proven in the closed bound window, the result is
   `BFF_REQUEST_NOT_OBSERVED`.
3. If a matching request with HTTP 401 is proven, the result is
   `BFF_AUTHENTICATION_REJECTED_401`.
4. If a matching request with HTTP 403 is proven, the result is
   `BFF_AUTHORIZATION_REJECTED_403`.
5. A missing client receipt, unprovable deployed client version, multiple
   classes, 2xx, other status codes, or conflicting data are not a diagnosis;
   they produce a narrow `BLOCKED_*` state.

The UI remains deliberately neutral. The finer class appears only in redacted
operator evidence and never as a personal-detail message in Teams.

## CLI Surface

Product documentation exposes only a new central `nac` CLI surface. The
implementation plan will align the exact command name with the existing
`m365 teams-sharepoint` hierarchy. Direct Python scripts remain internal test
or compatibility surfaces.

The CLI contract strictly separates:

- purely local contract and preflight validation;
- later, separately approved read-only execution;
- emission of a redacted result.

There is no `--force`, `--login`, `--retry`, `--deploy`, `--release`, or other
mutation flag.

## Error and Stop Conditions

The system stops fail-closed before the next phase on:

- wrong repository, issue, PR, branch, commit, tree, or scope;
- missing or changed mandatory remote check;
- dirty worktree or unattested Git/toolchain binary;
- missing, incorrectly protected, or changed resolver;
- wrong provider-qualified account, provider, tenant, concrete account
  permission, target resource, principal, or approval body;
- missing or changed DPA, client receipt, package, window, or correlation
  binding;
- applicable external two-person obligation with only one principal;
- credential, login, refresh, cache, or configuration-write requirement;
- redirect, unknown provider field, or unredactable response;
- snapshot difference or multiple possible diagnostic classes;
- observed or possible mutation;
- missing OS-enforced write restriction to the single protected evidence sink;
- any deviation from the phase- and classification-specific exact permitted
  values for `port_factory`, `network_read`, `run_gate_consume_write`, or
  `result_evidence_write`, and any
  other operational counter with a non-zero value;
- any attempt to use #739 or #632 as input or downstream effect.

A blocked run authorizes no retry. A new real attempt requires a new approval
bound to the final HEAD and snapshot contract.

## Acceptance Criteria

- **AC-748-01 — Language and design parity:** German and English specifications
  and the later plan describe the same independent current-state scope, four
  diagnostic classes, gates, stop conditions, and non-goals.
- **AC-748-02 — Correct post-merge binding:** The gate proves the relationship
  between merged PR #747, merge commit, base tree, and final Issue #748 HEAD
  without equating the merge commit and historical PR head.
- **AC-748-03 — Terminal provenance remains terminal:** No #739 or #632
  artifact, comment, or gate is an operational input; the new path cannot open
  quarantine release, packaging, or live action.
- **AC-748-04 — Authorization before every read:** Resolver, principal,
  provider-qualified account, provider, tenant, concrete account permission,
  target resource, `OWNER_SOLO_APPROVAL`, `four_eyes_satisfied=false`, DPA
  binding, commit, tree, contract, toolchain, and checks are revalidated before
  the port factory and before every provider read. The complete governance
  negative matrix is mandatory.
- **AC-748-05 — Deterministic classification:** Synthetic positive and negative
  tests distinguish exactly `SPFX_SUBJECT_MISSING`,
  `BFF_REQUEST_NOT_OBSERVED`, `BFF_AUTHENTICATION_REJECTED_401`, and
  `BFF_AUTHORIZATION_REJECTED_403`; ambiguous states block.
- **AC-748-06 — Double redacted evidence:** Exactly two allowlisted, canonical,
  independent acquisition envelopes with the same window, client,
  correlation, and target binding plus two canonical identical decision
  projections are required. Unknown fields, personal data, sequence replay,
  reused provider-read receipts, bound window/projection-provenance drift,
  redirects, or hash differences block.
- **AC-748-07 — Zero side effects:** Windows tests prove that login,
  device-code, browser-authentication, token-refresh, token-import,
  credential-export, credential, cache, configuration, redirect, retry,
  tenant, provider, deployment, #739, and #632 counters stay zero in all local
  and read-only phases. Only exactly bounded port, read, and evidence-sink
  counters may reach their contract values; the Windows backend enforces the
  host write block independently of self-reported counters. The run gate,
  atomically consumed before port factory, blocks parallel and replay runs.
- **AC-748-08 — Complete traceability:** Issue, DE/EN specification, DE/EN
  plan, verification contract, CLI, validators, tests, documentation, AI-SBOM
  decision, and local and remote evidence are connected through a
  machine-readable AC evidence matrix; complete file, commit, and patch lists
  for `main...HEAD` are reviewed before any later merge recommendation.
  Mandatory checks are `secret-scan`, `privacy-lint`, `quality-gate`, and
  `NaC Windows Portability / windows-offline-cli`.

## Binding AC Evidence and Windows Matrix

For every AC, the verification contract records machine-readable `artifacts`,
`validators`, `positive_tests`, `negative_cases`, `expected_result`, and
`required_remote_checks`. The validator blocks missing files, empty test sets,
unknown case IDs, and unregistered quality-gate steps.

| AC | Primary evidence | Mandatory negative clusters |
| --- | --- | --- |
| AC-748-01 | DE/EN parity plus independent docs review | missing section, different class, different gate |
| AC-748-02 | GitHub merge semantics and Git ancestry | wrong PR, PR not merged, wrong merge commit/tree, diagnostic HEAD not a descendant |
| AC-748-03 | independent module/import boundary | any #739/#632 artifact, journal, comment, module, or gate access |
| AC-748-04 | gate, resolver, account/principal, and DPA matrix | same-principal aliases, different bound account, uncited duty, solo approval as four-eyes, `BLOCKED_SINGLE_PRINCIPAL`, drift before second read |
| AC-748-05 | four positive classification fixtures | missing client receipt, 2xx, other status, multiple classes, conflicting data |
| AC-748-06 | two independent envelopes and identical projection hashes | different window/target/correlation binding, swapped or reused sequence, reused provider-read receipt, bound window/projection-provenance drift, unknown field, PII |
| AC-748-07 | Windows security backend, atomic run gate, and closed counter matrix | login, device code, browser auth, refresh, import, export, credential/cache/config write, redirect, retry, parallel or repeated run, crash after consume, approval replay, every mutation |
| AC-748-08 | validator registration, strict doctor, complete diff, and remote checks | missing quality-gate step, empty test suite, missing Windows check, scope drift |

The mandatory Windows workflow extends its matrix with at least:

- wrong resolver owner or SID;
- inherited or widened DACL;
- symlink, junction, or other reparse point;
- hardlink, file replacement, or changed file or volume ID;
- hash change after preflight;
- resolver, approval, account, or principal change between reads;
- unattested Git, Python, Node, or provider binary;
- unsanitized environment or writable credential/configuration store;
- missing or changed DPA receipt;
- every disallowed port, network, or evidence-sink count.

`scripts/quality_gate.py` registers the new feature validator explicitly.
`python scripts/nac.py doctor --profile strict` counts as evidence only after
the validator proves this registration and a non-empty test-case matrix.
Before the first commit, untracked files are checked through
`git status --short`; later PR acceptance additionally reviews the file,
commit, stat, and complete patch views for `origin/main...HEAD`.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Old #739 run is effectively resumed | Independent contract without #739 inputs; negative tests block every reference as run input |
| Merge commit is compared incorrectly with PR head | Explicit GitHub merge relationship plus ancestry proof for diagnostic HEAD |
| Principal equivalence improperly extends a provider account | Bind provider-qualified account, tenant, concrete permission, and target before every read |
| Ad-hoc provider reads bypass the gate | Port factory and every read require the same run authorization |
| Authentication library writes cache or refreshes token | Technical credential-write guard; otherwise block before provider access |
| Pseudonymous identity metadata lacks a DPA binding | Protected privacy receipt and `BLOCKED_DPA_AVV_BINDING` before port factory |
| Principal hash becomes publicly correlatable | Random run-bound HMAC only in the protected local evidence sink |
| Evidence writes open general host write access | Pre-opened single sink handle; OS-enforced denial for every other store |
| Personal data enters evidence | Closed allowlist, immediate in-memory redaction, and negative fixtures |
| Client subject cannot be proven through a privacy-minimal host receipt | Explicit local receipt download plus protected offline CLI materialization; block narrowly when Web Crypto, closed window, or deployed-package binding is missing |
| Browser download initially resides in an ordinary user folder | The download is transport only; exact validation and exclusive materialization in the external SID/DACL-protected input directory creates the authoritative receipt |
| Correlation ID would be persisted as a header or identifier | Raw value remains ephemeral, is used at most once for the existing BFF request, and only its SHA-256 binding enters the receipt |
| Two different temporal states are compared | Bound observation window, identical target binding, and snapshot hash comparison |
| UI reveals internal authorization detail | Teams message remains neutral; detailed class only in protected operator evidence |
| Diagnostic is mistaken for fix approval | Result authorizes only a new fix plan |

## AI-SBOM Decision

The diagnostic path and client receipt add no model call and no AI capability.
The AI-SBOM is updated synchronously with the negative decision: deterministic
local SPFx and CLI processing, with no new model, provider, or personal-data AI
flow. Adding an artificial AI component is a non-goal.

## Non-Goals

- no resumption or reconstruction of the Issue #739 run;
- no #739 quarantine release and no Issue #632 authorization;
- no deployment, Issue #632 activation/live run, recovery, rollback, cleanup,
  or retry; exactly one later separately approved read-only Issue #748
  diagnostic run remains in this specification's scope;
- no tenant, Entra, Azure, Graph, Teams, SharePoint, App Catalog, or BFF write;
- no new or broader role, permission, or API grant;
- no login, credential creation, credential change, or credential conversion;
- no storage of real identity mappings, tokens, headers, personal tenant data,
  or matter data;
- no weakening of the neutral Teams error message;
- no POSIX, WSL, Docker, SBX, or Linux build dependency for local Windows
  development;
- no merge or force-push in the specification step.

## Review Gate

The owner approved the base specification and base plan. The client-receipt
extension described here is written as a German/English design and synchronized
German/English plan. Explicit review approval of this exact two-stage local
transfer path is required before changing SPFx, CLI, contract, validators,
tests, documentation, or AI-SBOM. The subsequent test-first implementation in
Draft PR #749 proceeds through `implement -> review -> fix`; its repository and
CI authorization still includes no real provider access.

This specification approval will still not authorize provider access. The
later real read-only diagnostic run requires its own exact binding to final
HEAD, tree, resolver, principal, toolchain, checks, and scope after
implementation, review, push, and green CI.
