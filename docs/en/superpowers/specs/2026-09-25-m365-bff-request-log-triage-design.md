# One-off BFF request-log triage for the Teams 403

Status: spec and plan approved; local test-first implementation in progress; no provider read

Date: September 25, 2026

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Baseline of the deployed Teams app: `main` commit
`862c87e1e378657f0066faed1bd36b830be2146d`, tree
`3b1cfe5a4cfd7972912b961bfad46b713469f9fa`. This design is a
separate forward change and does not modify the historical
[#748 diagnostic specification](2026-09-20-m365-current-state-access-diagnostic-design.md)
or the [read-driver release design](2026-09-23-m365-current-state-read-driver-design.md).

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-bff-request-log-triage
leading_issue: https://github.com/notariat8/NaC/issues/748
plan: docs/en/superpowers/plans/2026-09-25-m365-bff-request-log-triage.md
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - External Service
  - Human Approval
  - Privacy
  - Secrets
  - Policy
acceptance_ids:
  - AC-748-TG-01
  - AC-748-TG-02
  - AC-748-TG-03
  - AC-748-TG-04
  - AC-748-TG-05
  - AC-748-TG-06
validation_commands:
  - python scripts/validate_m365_bff_request_log_triage.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python -m unittest discover -s tests -p test_m365_historical_bff_request_log_triage.py
  - graft check
  - python scripts/nac.py doctor --profile strict
```

## Purpose and established starting point

The two locally available client receipts with SHA-256
`ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40`
and `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`
belong to the closed window `2026-09-25T10:42:03.397Z` through
`2026-09-25T10:42:10.487Z`. They establish
`spfx_subject_available=true` and an HTTP 403 response received by the
client for the fixed workbench-snapshot GET. They establish neither Azure
Function ingress nor a particular BFF access rule. The receipt contents,
raw correlation value, and personal data remain outside the repository.

This triage is intended to determine with minimal additional work whether
*one unambiguously correlation-bound record* can be proven in already
existing Function request telemetry. It is neither the formal two-snapshot
diagnostic nor a new Teams observation or a fix.

## Scope and design decisions

1. A separate, forward-versioned triage contract remains distinct from the
   historical [verification contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml)
   and [resource contract](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json).
   Their `projection_proven=false`, no-refresh block, two acquisitions, and
   approvals are not silently changed.
2. The only prospective provider read is a GET in the Application Insights
   v1 query family `/v1/apps/{app_id}/query` for the bound test Function
   `func-nac-bff-test-funktion8` in workspace `notary_team_01`. The actual
   `{app_id}` must **not** be inferred from the Function hostname or a Bicep
   naming template. Protected, repository-external target evidence must
   unambiguously connect the app ID, Function, tenant, and permission;
   otherwise the state is `BLOCKED_TARGET_UNBOUND`.
3. The query requires a versioned, byte-hashed, fixed parameterized template.
   It may use only the stated millisecond window, fixed workbench-snapshot
   path, GET, and a demonstrably captured correlation column. Free-form
   KQL, target IDs, windows, search terms, or response URLs are forbidden.
   The present resource contract names only a query template ID and contains
   **no** compiled or schema-proven KQL. Until actual telemetry schema and
   projection bindings have separate proof, the state is
   `BLOCKED_QUERY_PROJECTION_UNPROVEN`.
4. The random client correlation value survives only as SHA-256 in the
   protected receipt. A later candidate may compare it only inside a
   protected process. A time or path hit alone is not correlation. If the
   header is not demonstrably captured in request telemetry, the comparison
   is unavailable, or multiple hits exist, use `BLOCKED_CORRELATION_UNPROVEN`
   or `BLOCKED_AMBIGUOUS_MATCH`.
5. The fixed output projection contains only `request_observed`,
   `http_class`, and `request_correlation_binding_sha256`. Raw rows, URLs,
   headers, cleartext correlation, tokens, account or tenant IDs, and extra
   fields must not be emitted or stored. Unknown fields, oversize responses,
   redirects, authentication challenges, and data that cannot be redacted
   block. Allow at most one GET, no body, paging, automatic retry, or new
   Teams request.
6. Local preparation must not open credentials or make network or provider
   calls. A later real read would require a proven existing authentication
   context with **zero** token refresh, protected DPA/AVV, target, and
   account/principal bindings, plus a separate exact one-shot authorization.
   Without a concretely cited applicable external two-person duty,
   `OWNER_SOLO_APPROVAL` is allowed and is not four-eyes approval; multiple
   accounts of the same principal never count as two people. With a
   concretely cited applicable duty and only one principal, the result is
   `BLOCKED_SINGLE_PRINCIPAL`. Any future silent refresh would be a
   separately approved RED credential operation under its own forward
   contract, not part of this triage. This specification authorizes no
   login, token refresh, release, deployment, or provider write.

## Result boundary

One unambiguous, protected log hit with HTTP 403 would support only
`FUNCTION_TELEMETRY_MATCH_403`: the Function monitoring path saw a matching
request. It does **not** prove that the Python endpoint produced the reply
or which business access rule applied. Without unambiguous
correlation-bound and fully redacted telemetry the result is `BLOCKED`;
an absent row cannot be emitted as `BFF_REQUEST_NOT_OBSERVED` or success.
Only a separately authorized follow-up could distinguish Azure edge from
the BFF access decision.

## Acceptance criteria and test plan

- **AC-748-TG-01:** Verify both existing file hashes, companion binding,
  exact UTC bounds, and correlation hash offline; drift or extra receipt
  fields blocks.
- **AC-748-TG-02:** Accept only protected target evidence uniquely linking
  the Application Insights app ID to the Function and tenant; inferred names
  and free target selection fail.
- **AC-748-TG-03:** Require a fixed hashed query template and proven telemetry
  schema; the current bare template ID and `projection_proven=false` remain
  blocked.
- **AC-748-TG-04:** Zero, multiple, uncorrelated, or incomplete hits,
  unexpected HTTP classes, and surplus output fields fail closed. Synthetic
  tests show that a timestamp alone is not a match.
- **AC-748-TG-05:** Synthetic negative tests prove zero network, provider,
  credential, login, and refresh activity during local preparation; later
  transport bounds are one GET and zero redirects, retries, paging, bodies,
  and writes.
- **AC-748-TG-06:** DE/EN specification, later plan, separate triage
  contract, validator, tests, and traceability agree. Neither the historical
  #748 classification nor #739, #632, or PR #754 gains live authorization.
  Future test and strict commands listed here are targets, not claims that
  they have already passed.

## Risks and non-goals

The telemetry schema, real Application Insights app ID, capture of the
correlation header, and authentication capability are **not proven** without
provider access. These gaps remain blockers, not dummy values. No real
Microsoft query, tenant or credential access, new login, token refresh,
BFF or SPFx deployment, role or permission change, or production fix in
this phase.
