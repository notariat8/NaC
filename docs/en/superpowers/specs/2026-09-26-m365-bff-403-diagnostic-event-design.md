# Internal BFF diagnostic event for the Teams 403

Status: design approved; specification submitted for owner review; no implementation

Date: September 26, 2026

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Baseline: branch `codex/748-bff-request-log-triage`, commit
`d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b`. This forward-looking
specification supplements the [historical request-log triage](https://github.com/notariat8/NaC/blob/d92b47e0a67b6e5bc2f4387742c84ddfe9d2518b/docs/en/superpowers/specs/2026-09-25-m365-bff-request-log-triage-design.md) without changing its receipts,
contract or approval state.

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-403-diagnostic-event
leading_issue: https://github.com/notariat8/NaC/issues/748
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
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py
  - python -m unittest discover -s tests -p test_nac_bff_azure_function_host.py
  - python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Purpose and evidence boundary

The existing client receipts show an available SPFx subject and HTTP 403 for
the bound workbench GET. They do not establish whether the Azure platform or
which Python branch produced the response. The [workbench endpoint](../../../../src/nac_bff/workbench_endpoint.py) collapses scope mismatch,
access-decision port failure and invalid or denied access decisions into the
same public `ACCESS_DENIED` response. This is an intentional information
boundary.

For a **new, separately approved future reproduction**, a protected,
structured BFF event shall identify the coarse internal branch that produced
a 403. It is not an authorization fix, does not reconstruct the historical
run, and an `ACCESS_DECISION_REJECTED` result alone does not establish the
specific Graph or role defect.

## Scope and design decision

1. Only the fixed workbench-snapshot GET for the synthetic test workspace
   `notary_team_01` is in scope. A closed internal reason is determined at
   the decision boundary. Allowed classes are `REQUEST_SCOPE_REJECTED`,
   `ACCESS_DECISION_UNAVAILABLE`, `ACCESS_DECISION_REJECTED`, and
   `DENIAL_UNCLASSIFIED`. A denial or error within the [live access-decision adapter](../../../../src/nac_bff/live_access_decision.py) initially remains
   grouped as `ACCESS_DECISION_REJECTED`; its deliberately neutral public
   decision is not opened up.
2. The [FastAPI adapter](../../../../src/nac_bff/fastapi_adapter.py) continues
   to return the byte-identical 403 body
   `{"status":403,"error":{"code":"ACCESS_DENIED"}}`. The internal reason
   never appears in the status, body, headers or SPFx receipt. Diagnostic
   sink failure must not grant access or alter the response, access-decision
   port or provider call; missing telemetry is **not** positive evidence.
   The endpoint passes the internal class only through request-local,
   non-serialized state to a sink invoked once. If a 403 arises before the
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
5. The sink is inactive by default. Future activation is limited to the
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

## Risks and rejected approaches

An HTTP-middleware-only event could report only an unclassified 403 and
would be too weak for the Teams incident. A reason code in the client
response would break the deliberately neutral security boundary. Fine-grained
Graph, case, person or deputy-grant reasons in telemetry would needlessly
increase privacy and inference risk. The design therefore starts with coarse
internal classes. If the future reproduction yields only
`ACCESS_DECISION_REJECTED`, a further specifically approved read-only check
is required; that class must not be reported as the complete cause or as a
resolved Teams incident.

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
  exist; #739, #632 and the historical #748 run are not unlocked.
- **AC-748-BD-06:** DE/EN specification, later plan, new contract,
  traceability, synthetic tests and local/remote gates are checked in sync
  before publication. The commands above are validation targets, not
  claims of completed checks.

## Non-goals

No new login, credential or Microsoft access, token refresh,
Azure/BFF/SPFx deployment, role or permission change, real diagnosis or
approval of another live run occurs in this design phase. The event is not
a new AI feature or a new `nac` CLI user function; if later implementation
adds an operator-facing action, that requires a separate CLI contract and
normal SBOM/license review.
