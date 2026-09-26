# Internal BFF diagnostic event for the Teams 403

Status: server-diagnosis design revision approved by the owner; synchronized DE/EN follow-on plan for review. Inactive v1 implementation published in [Draft PR #757](https://github.com/notariat8/NaC/pull/757), neither activated nor deployed.

Date: September 26, 2026

Leading issue: [#756](https://github.com/notariat8/NaC/issues/756); historical context: [#748](https://github.com/notariat8/NaC/issues/748)

Baseline: `main` commit `862c87e1e378657f0066faed1bd36b830be2146d`
on branch `codex/756-bff-403-diagnostic-event`. This forward-looking
specification supplements the [historical request-log triage](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/en/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md) without changing its receipts,
contract or approval state.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-diagnostic-event
leading_issue: https://github.com/notariat8/NaC/issues/756
plan: docs/en/superpowers/plans/2026-09-26-m365-bff-403-diagnostic-event.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - Policy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-748-BD-01
  - AC-748-BD-02
  - AC-748-BD-03
  - AC-748-BD-04
  - AC-748-BD-05
  - AC-748-BD-06
validation_commands:
  - python scripts/validate_m365_bff_403_diagnostic_event.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python -m unittest discover -s tests -p test_nac_bff_azure_function_host.py
  - python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
```

The traceability block, six existing ACs and linked implementation plan apply
**only to the published inactive v1**. That plan binds its earlier specification
approval to an older commit. Stage A/B below is a new design revision, not an
extension of that approval. The owner approved this revision on commit
`a76a1a0e9769cdf7f775e73d0812367ad408c066` and tree
`6d95fea5fbc2038068eda0602ca06693e0e47cc4` as the basis for the
synchronized DE/EN follow-on plan. The new plan is not yet approved;
implementation also requires a forward-versioned contract. Until then, the
[v1 contract](../../../../workflows/verification-contracts/m365-bff-403-diagnostic-event.verification.json)
remains unchanged.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-direct-server-diagnosis
leading_issue: https://github.com/notariat8/NaC/issues/756
plan: docs/en/superpowers/plans/2026-09-26-m365-bff-403-direct-server-diagnosis.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Privacy
  - Secrets
  - Policy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-756-SD-01
  - AC-756-SD-02
  - AC-756-SD-03
  - AC-756-SD-04
  - AC-756-SD-05
validation_commands:
  - python scripts/validate_m365_bff_403_direct_server_diagnosis.py
  - python -m unittest discover -s tests -p test_nac_bff_403_direct_server_diagnosis.py
  - python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py
  - python -m unittest discover -s tests -p test_nac_bff_live_synthetic_workspace.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - graft build
  - graft check
  - python scripts/nac.py doctor --profile strict
  - git diff --check
```

The new validator and Stage A test are **planned** implementation targets,
not checks that already exist or have passed.

## Purpose and evidence boundary

The existing client receipts show an available SPFx subject and HTTP 403 for
the bound workbench GET. They do not establish whether the Azure platform or
which Python branch produced the response. The [workbench endpoint](../../../../src/nac_bff/workbench_endpoint.py) collapses scope mismatch,
access-decision port failure and invalid or denied access decisions into the
same public `ACCESS_DENIED` response. This is an intentional information
boundary.

Diagnosis starts **with existing server state**, not another SPFx change:
first bind the BFF that is actually running and its existing request
telemetry. Only if that evidence cannot attribute or explain the denial is
the already inactive event in [Draft PR #757](https://github.com/notariat8/NaC/pull/757)
refined for a **new, separately approved future reproduction**. The current
event is neither deployed nor an authorization fix: an
`ACCESS_DECISION_REJECTED` class alone does not identify the specific Graph,
data or role defect. The historical run is not reconstructed.

## Scope and design decision

1. Only the fixed workbench-snapshot GET for the synthetic test workspace
   `notary_team_01` is in scope. The already published, **inactive v1
   implementation** determines a closed internal reason at the decision
   boundary. Its classes are `REQUEST_SCOPE_REJECTED`,
   `ACCESS_DECISION_UNAVAILABLE`, `ACCESS_DECISION_REJECTED`, and
   `DENIAL_UNCLASSIFIED`. A denial or error within the [live access-decision adapter](../../../../src/nac_bff/live_access_decision.py) initially remains
   currently grouped as `ACCESS_DECISION_REJECTED`; its deliberately neutral public
   decision is not opened up.
2. The [FastAPI adapter](../../../../src/nac_bff/fastapi_adapter.py) continues
   to return the byte-identical 403 body
   `{"status":403,"error":{"code":"ACCESS_DENIED"}}`. The internal reason
   never appears in the status, body, headers or SPFx receipt. A full or absent
   diagnostic buffer must not grant access or alter the response, access-decision
   port or provider call; missing telemetry is **not** positive evidence.
   The endpoint passes the internal class only through request-local,
   non-serialized state to a bounded, inactive in-memory buffer with no external
   callback. If a 403 arises before the
   endpoint, the HTTP boundary uses `DENIAL_UNCLASSIFIED`; multiple layers
   must not emit multiple events for the same request.
3. The event has a fixed field allowlist: schema version, bounded UTC time,
   constant route class `workbench_snapshot`, method `GET`, HTTP class `403`,
   closed reason class, and `request_correlation_binding_sha256`. No free-text
   fields exist. Raw headers or correlation values, URL, path, query, claims,
   actor, tenant or matter IDs, names, roles, grant data, Graph responses,
   exception objects and tokens stay out of the event and public logs.
4. Correlation is permitted only if exactly **one** received
   `X-Correlation-ID` header contains the one-shot `spfx-` UUID-v4 identifier
   produced by `crypto.randomUUID()`, the BFF hashes the exact received value
   in memory before any fallback generation, and a new protected client
   receipt carries the same SHA-256 binding. Duplicate, combined, missing,
   rewritten or syntactically different headers yield `UNBOUND`, never a
   guessed association. UUID syntax alone proves neither randomness nor a
   match; the protected receipt comparison is also required. The raw value
   is not persisted. The existing public fallback response must not become
   false correlation evidence.
5. The in-memory buffer is inactive by default and is not live telemetry.
   Future activation is limited to the
   bound test BFF, a short closed observation window and authorized log
   access. Before activation, the DPA/AVV basis, retention period, access
   group, package/commit/tree binding and actual telemetry capture must be
   checked. This specification authorizes neither activation nor deployment
   nor a provider read.
6. The existing [triage contract](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/workflows/verification-contracts/m365-bff-request-log-triage.verification.json)
   remains `OFFLINE_ONLY_NOT_LIVE_CAPABLE`. Its historical file hashes,
   window, open target/schema/auth bindings and
   `provider_read_authorized=false` remain unchanged. Any later live attempt
   requires a separate forward-versioned contract and its own exactly bound
   owner approval.

## Staged direct server diagnosis — design revision

**Stage A: examine existing server state.** Before any new deployment, a
separately authorized read-only channel establishes the identity of the
active test BFF, the package/version actually deployed, the bound Application
Insights resource, and its capture and retention state. The follow-on
contract must close each required metadata endpoint and its read budget, and
prove the App-ID-to-Function-to-tenant-to-existing-read-permission binding.
Only such a proven target permits a byte-hashed fixed query with the checked
three-field projection `request_observed`, `http_class`, and
`request_correlation_binding_sha256` in the observation window of the
existing protected client receipts. Historical triage allows at most one
GET, with no redirect, retry or paging; its no-refresh channel still needs
proof. The [historical triage](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/workflows/verification-contracts/m365-bff-request-log-triage.verification.json)
still has placeholders for target, query and correlation proof; it is **not**
authorization for a real query. A simultaneous HTTP 403 without an unambiguous
correlation binding does not prove that the Teams request reached the BFF.
Empty, expired or ambiguous logs are `UNPROVEN`, not “BFF request absent”. A
BFF proven not to be deployed is a separate finding and requires no
instrumented reproduction.

**Stage B: refine only when Stage A is inconclusive.** Before any activation,
the inactive v1 implementation is extended under a forward-versioned
contract with closed decision stages readable only internally:
`GRAPH_READ_UNAVAILABLE`, `CASE_BINDING_INVALID`,
`ACTOR_ASSIGNMENT_MISSING`, `DEPUTY_GRANT_INVALID`,
`GRANT_AUDIT_INVALID`, and `DECISION_PROJECTION_INVALID`. They distinguish
technical Graph access, the synthetic case/team binding, actor assignment,
deputy approval, audit binding and validation of the access decision. The
current [live access-decision adapter](../../../../src/nac_bff/live_access_decision.py)
converts every exception into a neutral denial. A forward-versioned,
request-local diagnostic result/port contract must therefore capture the
terminal decision branch **before** that collapse and pass it to the
endpoint; projection validation may add its own terminal branch. The public
`AccessDecision` outcome and provider calls remain unchanged. A global
error state shared across requests is excluded. Synthetic
negative and concurrency tests must prove that Graph failures, empty or
ambiguous case results and intermediate checks are never mislabeled as a
missing assignment or invalid grant. Unknown failures remain
`DENIAL_UNCLASSIFIED`.

The classes `ACTOR_ASSIGNMENT_MISSING`, `DEPUTY_GRANT_INVALID`, and
`GRANT_AUDIT_INVALID` permit inferences about personal assignment and
approval state despite containing no raw IDs. They are **sensitive protected
operational metadata**, not anonymous data. Before activation, the
diagnostic benefit of each class must be assessed against privacy risk, and
the named, qualified, purpose-bound readership, short retention, access
protection and DPA/AVV basis must be proven. If any such binding is missing,
the classes remain grouped as `ACCESS_DECISION_REJECTED`; no specific cause
is claimed. Explicit existence flags, concrete IDs, raw data, Graph
responses and exception text must appear neither in the event nor in Teams,
Git or public logs. The current v1 allowlist and contract remain unchanged
until the new specification, plan and contract version are approved.

Only then may a separately approved deployment, exactly bound to package,
target, principal, DPA/AVV, retention and access group, reach the existing
test BFF. Exactly **one** new Teams observation uses the existing protected
client-receipt mechanism for correlation; it needs no new SPFx feature. If
the server/receipt match or technically protected capture is not conclusive,
the run ends without a root-cause claim or automatic retry. The concrete
configuration, data, role or permission correction is derived only from a
confirmed finding and separately authorized.

## Risks and rejected approaches

An HTTP-middleware-only event could report only an unclassified 403 and
would be too weak for the Teams incident. A reason code in the client
response would break the deliberately neutral security boundary. Raw Graph,
case, person or deputy-grant data in telemetry would needlessly increase
privacy and inference risk. The proposed closed stages therefore remain
exclusively in protected server evidence and are activated only after a
documented inference assessment and DPA/AVV, retention and access-group
binding. If the result remains merely
`ACCESS_DECISION_REJECTED` or `DENIAL_UNCLASSIFIED`, it must not be reported
as the complete cause or as a resolved Teams incident.

## Acceptance criteria and intended validation

- **AC-748-BD-01:** Synthetic negative tests exercise every 403 branch and
  verify its closed internal class, including 403 before the domain endpoint.
  Unknown cases remain `DENIAL_UNCLASSIFIED`.
- **AC-748-BD-02:** The public 403 response and existing security headers
  retain identical bytes and status; no internal reason reaches Teams or
  the SPFx receipt.
- **AC-748-BD-03:** At most one allowlisted event is produced per eligible,
  bound 403. Duplicate, missing, invalid, ambiguous or unproven-random
  correlation values cannot produce a positive association; a fallback
  value never substitutes for the received evidence value.
- **AC-748-BD-04:** Sink failure, an inactive sink and uncaptured telemetry
  change neither access nor response and count as missing evidence. Tests
  verify that no raw values, IDs, URLs, queries or exception text enter the
  event.
- **AC-748-BD-05:** Activation, log read and new reproduction remain blocked
  until separate target, contract, DPA/AVV, authorization and owner bindings
  exist; #739, #632 and the historical #748 run are not unlocked. Stages A/B
  do not extend this v1 acceptance criterion and receive their own criteria
  in a later follow-on plan.
- **AC-748-BD-06:** DE/EN specification, existing v1 plan and contract,
  traceability, synthetic tests and local/remote gates are checked in sync
  for each publication. The commands above are validation targets, not
  claims of completed checks.

### New design revision, not yet approved for implementation

- **AC-756-SD-01:** A follow-on contract binds the active test BFF, package
  version, App ID, Function, tenant, existing permission, individually allowed
  metadata endpoints and read budgets before every read; missing bindings
  block rather than select another tenant or a free-form query.
- **AC-756-SD-02:** The historical query remains byte-hashed, restricted to
  exactly three output fields and at most one GET without redirect, retry or
  paging. Only a server finding unambiguously correlated with the protected
  receipt supports a root-cause claim; empty, expired or ambiguous logs
  remain `UNPROVEN`.
- **AC-756-SD-03:** A forward-versioned, request-local diagnostic result/port
  contract classifies terminal denial branches only. Negative and concurrency
  tests exclude false attribution for Graph failures, empty or ambiguous
  results and intermediate checks. The public response and access-decision
  and provider semantics remain unchanged.
- **AC-756-SD-04:** Each inference-bearing class requires a documented
  privacy assessment, DPA/AVV basis, qualified readership, access protection
  and short retention. Without these bindings the coarse v1 class remains;
  raw data and personal evidence do not leave protected storage.
- **AC-756-SD-05:** A later deployment and exactly one new Teams observation
  need separate exact approvals and correlation evidence. Missing evidence
  stops without retry or root-cause claim; #739, #632 and the historical
  #748 artifacts remain untouched.

## Non-goals

No new login, credential or Microsoft access, token refresh,
Azure/BFF/SPFx deployment, role or permission change, real diagnosis or
approval of another live run occurs in this design phase. The event is not
a new AI feature or a new `nac` CLI user function; if later implementation
adds an operator-facing action, that requires a separate CLI contract and
normal SBOM/license review.
