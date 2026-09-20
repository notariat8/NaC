# Windows-Native Current-State Diagnostics for Teams and BFF Access — Implementation Plan

Status: German and English specifications approved; `plan -> review -> fix` complete; plan approval pending; implementation, provider access, and merge blocked

Date: 20 September 2026

Specification: [Windows-Native Current-State Diagnostics for Teams and BFF Access](../specs/2026-09-20-m365-current-state-access-diagnostic-design.md)

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Draft PR: [#749](https://github.com/notariat8/NaC/pull/749)

Delivery Mode: Protected PR

Risk Gate: Human Approval

## Outcome and Boundary

The implementation delivers an independent, Windows-native, read-only
diagnostic path for `notary_team_01` and the “NaC Vorgangsansicht” Teams app.
It classifies exactly one of four causes:

- `SPFX_SUBJECT_MISSING`;
- `BFF_REQUEST_NOT_OBSERVED`;
- `BFF_AUTHENTICATION_REJECTED_401`;
- `BFF_AUTHORIZATION_REJECTED_403`.

The path starts from the merged state of PR #747, does not replace the
terminal Issue #739 run, and creates no Issue #632 live approval. The
implementation phase uses only synthetic ports and local fixtures. It does not
authorize login, credential, network, Microsoft, tenant, or provider access,
retry, deployment, #739 release, #632 live execution, or merge.

After green local and remote validation, work stops before the sole real
read-only run. That later run requires a new owner approval exactly bound to
the final commit, tree, PR, checks, contract, toolchain, resolver, account,
principal, privacy receipt, and scope.

## Binding Architecture Decisions

1. **Independent path:** New modules import or read no #739 or #632 artifacts,
   journals, approvals, gates, or run state.
2. **Pure classification:** A side-effect-free core function receives only the
   closed, redacted snapshot projection and returns exactly one class or a
   stable blocking code.
3. **Authorization before I/O:** The final gate runs before the port factory.
   The immutable run authorization is revalidated before every provider read.
4. **Closed ports:** Only the seven ports named in the specification may be
   created. There is no general Graph, Azure, SharePoint, or search interface.
5. **Windows security binding:** Resolver, privacy receipt, client observation,
   target binding, approval, and run gate use the existing Windows security
   backend to bind canonical path, SID, DACL, file and volume IDs,
   reparse/hardlink state, size, and hash.
6. **One-time consumption:** The protected run gate transitions atomically
   from `unused` to `consumed` before port-factory creation. Replay, parallel
   start, and a crash after consumption remain blocked.
7. **Two genuine acquisitions:** Snapshots 1 and 2 have separate acquisition
   envelopes, sequences, and provider-read receipts. Only their RFC 8785
   canonical decision projections may be byte-identical; a reused receipt is
   not a second read.
8. **No credential contents:** Token, secret, header, cache, or credential-store
   contents and their hashes are never read. Only allowlisted non-content OS
   metadata is permitted while the credential-write guard is active.
9. **No AI runtime:** The diagnostic path invokes no model and creates no new
   AI-SBOM component. The existing AI-SBOM is validated only.

## Fixed CLI Surface

The product surface remains under the existing `nac m365 teams-sharepoint`
hierarchy and gains exactly two subcommands:

```text
nac m365 teams-sharepoint current-state-access-diagnostic-preflight
nac m365 teams-sharepoint current-state-access-diagnostic-run-read-only
```

`current-state-access-diagnostic-preflight` performs only local binding and
security checks and must not create provider ports.
`current-state-access-diagnostic-run-read-only` may be implemented and tested
synthetically, but production use remains blocked until the later exactly
bound approval. Both commands accept only paths to protected local contract
artifacts. Real tenant, account, principal, team, channel, tab, site, app,
Function, or correlation values are not CLI arguments. There are no flags for
login, device code, browser authentication, refresh, retry, force, redirect,
deployment, recovery, or write.

## Change Surfaces

| Surface | Planned artifacts | Purpose |
| --- | --- | --- |
| Verification contract | `workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml` | closed bindings, phases, counters, error codes, port matrix, and AC matrix |
| Validator and quality gate | `scripts/validate_m365_current_state_access_diagnostic.py`, `scripts/quality_gate.py` | require contract, files, CLI, tests, and Windows matrix |
| Core and gate | `src/nac_bff/current_state_access_diagnostic.py`, `src/nac_bff/current_state_access_gate.py` | pure classification and post-merge, GitHub, governance, and privacy authorization |
| Ports, adapters, and composition | `src/nac_bff/current_state_access_ports.py`, `src/nac_bff/current_state_access_adapters.py`, `src/nac_bff/current_state_access_composition.py` | closed ports, narrow production read adapters, port factory behind gate, and two separate acquisitions |
| CLI | `src/nac_cli/cli.py` | local preflight and separately blocked read-only run |
| Tests | `tests/test_m365_current_state_access_diagnostic.py`, `tests/test_m365_current_state_access_gate.py`, `tests/test_nac_cli.py`, `tests/test_windows_offline_cli_portability.py` | positive, negative, security, replay, parity, and Windows tests |
| Documentation | `docs/de/cli.md`, `docs/en/cli.md`, `docs/de/m365-current-state-access-diagnostic.md`, `docs/en/m365-current-state-access-diagnostic.md` | operation, boundaries, error classes, and later approval chain |
| Context and CI | `agent-context/index.json`, `.github/workflows/windows-portability.yml` | on-demand contract and mandatory Windows test matrix |
| Traceability | German/English specification and plan, `workflows/contracts/spec-traceability.contract.json`, `scripts/validate_spec_traceability.py`, `tests/test_spec_traceability.py` | connect issue, plan links, ACs, files, and evidence |

Other files are added only when an initially failing test proves a direct
in-scope dependency and the plan is synchronized before commit. No Gantt
change is planned because the path causes no roadmap, scope, or milestone
change.

## Test-First Implementation Sequence

### 1. Verification contract and validator

**Initially red:** The contract is absent, permits unknown fields, does not map
all AC-748-01 through AC-748-08, allows provider reads without the gate, or
registers no real Windows test in the quality gate. The general spec
traceability validator also gains red cases for a missing or nonexistent plan
path, wrong language path, unpaired German/English plans, changed
issue/spec/AC binding, and a plan without concrete validation commands or a
complete AC evidence matrix.

**Then green:** Create a closed YAML schema with exact base, target, toolchain,
resolver, account/principal, DPA, approval, snapshot, counter, and check
bindings. Register the validator in `scripts/quality_gate.py` and treat empty or
skipped test suites as failures.

### 2. Pure classification

**Initially red:** One fixture for each of the four target classes plus
negative cases for a missing client receipt, 2xx, other HTTP status,
conflicting data, multiple possible classes, and unknown fields.

**Then green:** Implement an immutable typed snapshot projection and pure
classification function. Incomplete or ambiguous input returns a stable
blocking code, never a guess.

### 3. Post-merge, GitHub, and governance gate

**Initially red:** Wrong PR, unmerged PR #747, wrong merge commit or tree,
diagnostic HEAD that is not a descendant, missing mandatory check, changed
resolver/account/principal, same-principal alias used as a second person,
uncited external two-person duty, invalid `OWNER_SOLO_APPROVAL`,
`four_eyes_satisfied=true`, or invalid privacy receipt.

**Then green:** Use attested environment-scrubbed Git for local ancestry and
tree verification. All GitHub reads run under the credential-write guard via
the established read channel. An absent external two-person duty permits
`OWNER_SOLO_APPROVAL`; an applicable concretely cited duty with only one
principal blocks with `BLOCKED_SINGLE_PRINCIPAL`.

### 4. Windows-protected local evidence and run gate

**Initially red:** Wrong owner/SID, broadly writable DACL, reparse point,
hardlink, path/file/volume-ID or hash change, unattested Git, Python, Node, or
provider binary, unscrubbed environment, writable credential or config store,
missing or changed DPA receipt, parallel start, approval replay, crash after
consumption, and every forbidden `port_factory`, `network_read`, or
`evidence_sink_write` counter value.

**Then green:** Use the existing Windows security backend; add no simplified
path check. Atomically consume the one-shot gate before port-factory creation.
For every deviation, port, network, login, credential, and mutation counters
remain zero.

### 5. Closed ports and synthetic adapters

**Initially red:** Extra port, general search, unbound resource, changed
window, credential content, raw response, personal field, redirect, or
mutation.

**Then green:** Define protocols for `ClientObservationReceiptPort`,
`TeamsTabMetadataReadPort`, `SharePointAppCatalogReadPort`,
`EntraApiPermissionReadPort`, `AzureFunctionMetadataReadPort`,
`AzureFunctionRequestLogReadPort`, and `SharePointAccessDecisionReadPort`.
Fake adapters return only allowlisted Booleans, closed enums, opaque digests,
and receipts. Also implement the seven narrow production adapters in
`src/nac_bff/current_state_access_adapters.py`: Graph, SharePoint, and Entra
reads use an injected attested no-redirect/no-retry transport; ARM and
Application Insights/Log Analytics reads use an injected attested Azure CLI
transport capability restricted to read-only commands; the SharePoint access
decision uses the existing bound synthetic-list reader. No adapter acquires,
refreshes, exports, or persists credentials. Production adapters are tested
only with fake transports in this phase and are not executed. Production
composition and every adapter remain behind the same immutable run
authorization and credential-write guard.

### 6. Double snapshot acquisition

**Initially red:** Only one snapshot, swapped or reused sequence, same
provider-read receipt, changed target/window/correlation binding, provenance
drift, unknown field, PII, different canonical projection, or authorization
drift before the second read.

**Then green:** Perform two complete acquisitions in sequence, reauthorize
before every port read, and persist separate envelopes. Canonicalize and
compare only the allowlisted decision projection under RFC 8785. Release a
result only for identical SHA-256 values and exactly one diagnostic class.

### 7. CLI and composition

**Initially red:** Preflight creates a port factory, production run starts
without final approval, CLI accepts real tenant values or a prohibited
login/retry/write option, or an adapter is directly reachable.

**Then green:** Register both fixed subcommands, return stable exit codes and
redacted JSON, and permit factory creation only after a successful gate. No
import starts I/O.

### 8. Documentation, traceability, and Windows CI

Update German and English CLI documentation and runbooks synchronously.
`agent-context/index.json` references the specification, plan, and verification
contract. The mandatory workflow executes the real new test suite on Windows
and proves the closed zero-side-effect matrix. AI-SBOM, license, privacy, link,
language, and spec-traceability validators remain green.

### 9. `implement -> review -> fix`

Review the complete `main...HEAD` diff after implementation. Independent
reviews cover at least scope/layers, governance/privacy, validation/Windows,
and German/English parity. Resolve findings with forward commits; do not
rewrite history. Only then run the full suite, Graft, strict doctor, push, and
remote CI.

## AC-to-Evidence Matrix

| AC | Primary implementation | Mandatory evidence |
| --- | --- | --- |
| AC-748-01 | synchronized German/English specification, plan, CLI, and runbooks | language parity, links, and independent docs review |
| AC-748-02 | final gate validator for PR #747, merge commit/tree, and Git ancestry | positive base fixture plus wrong PR/merge/tree/ancestry |
| AC-748-03 | separate modules, contracts, gates, and artifacts | import/path negative tests against every #739/#632 access |
| AC-748-04 | resolver, principal, DPA, approval, and per-read authorization | complete governance negative matrix and drift before read 2 |
| AC-748-05 | pure closed classification | four positive classes plus ambiguity/incompleteness matrix |
| AC-748-06 | two envelopes, independent receipts, and RFC 8785 projection | identity test plus sequence, receipt, window, PII, and drift tests |
| AC-748-07 | Windows backend, credential-write guard, and one-shot gate | zero-side-effect counters, parallel, replay, and crash tests on Windows |
| AC-748-08 | validator, quality gate, traceability, docs, and CI | full suite, Graft, strict doctor, complete diff, and remote checks |

## Local Validation Order After Implementation

```text
python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py
python -m unittest discover -s tests -p test_m365_current_state_access_gate.py
python -m unittest discover -s tests -p test_nac_cli.py
python -m unittest discover -s tests -p test_windows_offline_cli_portability.py
python -m unittest discover -s tests -p test_spec_traceability.py
python scripts/validate_m365_current_state_access_diagnostic.py
python scripts/validate_spec_traceability.py
python scripts/validate_language_parity.py
python scripts/validate_doc_links.py
python -m unittest discover -s tests
graft build
graft check
python scripts/nac.py doctor --profile strict
git status --short
git diff --check origin/main...HEAD
git diff --name-status origin/main...HEAD
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff origin/main...HEAD
```

The real read-only composition is exercised only with fakes in this sequence.
A green local run is not provider approval.

## Planned Commit Sequence

1. `test(issue-748): define diagnostic contract and negative matrix`
2. `feat(issue-748): add gated current-state diagnostic core`
3. `docs(issue-748): document Windows read-only diagnostic`
4. `fix(issue-748): address implementation review findings`

The actual number may be smaller when that keeps an atomic change clearer.
Every commit remains within the approved Issue #748 scope; no force push.

## Definition of Done for the Implementation Phase

- all AC-748-01 through AC-748-08 have executable evidence;
- exactly the four target classes are deterministically distinguishable;
- #739 remains terminal and #632 remains untouched;
- gate and per-read authorization run before every external access;
- two independent redacted snapshots are required;
- login, credential, retry, redirect, mutation, and deployment counters are
  closed and zero;
- the complete local Windows suite, Graft, and strict doctor are green;
- `main...HEAD` is fully reviewed, the workspace is clean, and PR #749 remains
  draft;
- all mandatory remote checks are green;
- the expected checks are `Privacy and Secrets Guard / secret-scan`,
  `Privacy and Secrets Guard / privacy-lint`, `NaC Quality Gate / quality-gate`,
  and `NaC Windows Portability / windows-offline-cli`;
- a new exact owner approval exists before the real read-only run.

## Review Gate

This plan was reviewed independently for scope, governance, validation, and
German/English parity; findings were fixed and the result was re-reviewed with
no findings. It does not yet authorize contract, test, or code changes or any
external access. Explicit plan approval is required; only then does test-first
implementation begin.
