# One-off BFF request-log triage – implementation plan

Status: plan approved; local test-first implementation in progress; no real-read authorization

Date: September 25, 2026

Leading issue: [#748](https://github.com/notariat8/NaC/issues/748)

Approved spec: [BFF request-log triage](../specs/2026-09-25-m365-bff-request-log-triage-design.md)

Baseline of the app deployed in Teams: `main` commit
`862c87e1e378657f0066faed1bd36b830be2146d`, tree
`3b1cfe5a4cfd7972912b961bfad46b713469f9fa`. The local
implementation is isolated on `codex/748-bff-request-log-triage` from this
`main` baseline. The full diff must be reviewed before any later push.
Nothing is silently added to PR #754.

Delivery mode: Protected PR. Risk gate: Human Approval. This plan is not
evidence of a real Microsoft read.

## Goal and hard boundary

The two protected client receipts and the closed UTC window from
`2026-09-25T10:42:03.397Z` to `2026-09-25T10:42:10.487Z` prepare a
*possible* single Application Insights request-log match. The established
client 403 and available SPFx subject prove neither Function ingress nor
the cause of the access decision. A later correlation-bound 403 log match
may yield only `FUNCTION_TELEMETRY_MATCH_403`. Without proven app ID, query
projection, correlation column, and no-refresh capability the real read
remains blocked. An absent log row must never become
`BFF_REQUEST_NOT_OBSERVED`.

Separate approval for test-first implementation has been given; the
implementation remains local and inactive. Login, token
refresh, credential access, provider read, deployment, #739 quarantine
release, and #632 live execution are excluded.

## Approved local implementation

1. **Test-first and separate contract surface.** First add synthetic
   positive and negative cases for all six ACs in
   `tests/test_m365_historical_bff_request_log_triage.py`. A separate,
   forward-versioned contract at
   `workflows/verification-contracts/m365-bff-request-log-triage.verification.json`
   records the closed resource, allowed fields, zero-effect counters, and
   terminal blockers. The historical
   [#748 verification contract](../../../../workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml)
   and [read-driver resource contract](../../../../workflows/contracts/m365-current-state-read-driver-resources.contract.json)
   remain unchanged and are referenced only by file digest. The formal
   two-snapshot diagnostic is not replaced.
2. **Offline receipts and target binding.** The new validator
   `scripts/validate_m365_bff_request_log_triage.py` verifies SHA-256
   `ed89c1171a02fc79c80314512375c7db84be2fce1528c7ba6596d7c24d805e40`
   and `daf4cc55f0f95f38b118155d8bef33d36a0a68809848ba96b049f1f129b80bda`,
   companion relation, fixed millisecond window, and existing correlation
   hash without emitting the raw value. Inputs come only from protected,
   repository-external files. Target evidence must unambiguously bind the
   actual Application Insights app ID to `func-nac-bff-test-funktion8`,
   `notary_team_01`, tenant, and read permission; hostname or Bicep-name
   inference remains blocked.
3. **Query and correlation gate.** Only separately proven telemetry schema
   with a demonstrably captured correlation column permits a byte-hashed,
   fixed KQL template. Until then the gate yields
   `BLOCKED_QUERY_PROJECTION_UNPROVEN`; missing target binding yields
   `BLOCKED_TARGET_UNBOUND`. Time, path, or HTTP class alone never matches.
   Zero, multiple, or non-uniquely correlated hits yield
   `BLOCKED_CORRELATION_UNPROVEN` or `BLOCKED_AMBIGUOUS_MATCH`. A synthetic
   positive fixture does not unlock a production port.
4. **Bound transport and output.** A later, separately approved port may
   perform only one GET to `/v1/apps/{app_id}/query`, with a fixed query and
   no body, redirect, retry, pagination, or additional provider request.
   Before any port access it binds commit, tree, contract, resolver,
   principal, target, DPA/AVV evidence, toolchain, account, and no-refresh
   property. Without a concretely cited applicable external two-person duty,
   `OWNER_SOLO_APPROVAL` applies with `four_eyes_satisfied=false`. Where a
   cited duty applies, qualified approvals from two distinct natural
   `principal_id` values are required; with only one, use
   `BLOCKED_SINGLE_PRINCIPAL`. Output contains only `request_observed`, `http_class`, and
   `request_correlation_binding_sha256`; raw rows, URLs, headers, IDs,
   tokens, and extra fields block before storage or output. Authentication
   challenges, oversized responses, and data that cannot be fully redacted
   also block. The local
   implementation remains inactive without separately proven
   authentication and real-read approval. A later entry point is added
   only as a fixed subcommand of the central `nac` CLI; free URL, KQL,
   target, or token parameters remain forbidden. Until separate real-read
   approval, this entry point may emit only offline preflight and its
   blockers.
5. **Traceability and review.** DE/EN spec and plan, new contract,
   validator, and tests share the same AC IDs. Test-first extend the
   spec-traceability check to enforce plan-path and AC equality for this
   `spec_id`. DE/EN indexes and the diagnostic guide link to the new path
   only upon delivery; AI-SBOM/SBOM change only if an actual new AI or
   runtime component is added. Independent policy, documentation, and
   validation reviews inspect privacy, zero effects, and DE/EN parity;
   then run `implement -> review -> fix`.

## Evidence matrix

| AC | Planned local proof | Fail-closed counterexample |
| --- | --- | --- |
| AC-748-TG-01 | Hash, companion, UTC, and correlation-hash fixtures | Changed or surplus receipt fields |
| AC-748-TG-02 | Target evidence binds app ID, Function, tenant, and permission | Hostname, template name, or freely selected app ID only |
| AC-748-TG-03 | Fixed query bytes, digest, and schema/projection proof | Template ID only or `projection_proven=false` |
| AC-748-TG-04 | Exactly one complete correlated synthetic 403 hit | Zero/multiple hits, time-only match, other class, extra field, oversized or unredactable response |
| AC-748-TG-05 | Fakes allow protected local receipt reads but count zero network/provider/credential/login/refresh effects during preparation and at most one later GET | Credential open, refresh, POST, redirect, retry, paging, body, authentication challenge |
| AC-748-TG-06 | DE/EN spec/plan parity and AC traceability | Historical #748, #739, #632, or PR #754 path used as authorization |

Negative tests must also show that `OWNER_SOLO_APPROVAL` is not four-eyes
approval, accounts of one principal are not two people, and a concretely
cited applicable two-person duty with only one principal yields
`BLOCKED_SINGLE_PRINCIPAL`.

## Checks and stopping points

For this plan: validate DE/EN links, language parity, spec traceability,
and Graft; correct documentation review findings. The planned
implementation tests are not passing evidence today.

For the approved local implementation: focused synthetic tests,
`python -m unittest discover -s tests`, `graft build`, `graft check`, and
`python scripts/nac.py doctor --profile strict`; then the complete
`main...HEAD` file and commit diff, separate review, and required remote CI
in protected-PR mode. A passing local or remote test authorizes no provider
read. An actual GET requires a proven closed target/query/correlation/auth
channel and new exact one-shot approval; any gap stops without retry.
