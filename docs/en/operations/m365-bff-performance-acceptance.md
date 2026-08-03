# M365 BFF Performance Acceptance

Status: offline plan, safety runtime and verification contract implemented;
the Microsoft 365/Azure preflight adapters and live CLI command remain
fail-closed and owner-gated.

This standard defines a capacity-gated acceptance lane for the activated M365
BFF read endpoint. The machine-readable source is
[m365-bff-performance-acceptance.contract.json](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json),
with its verification harness in
[m365-bff-performance-acceptance.verification.json](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).

## Fixed Route

The business target is immutable:

| Field | Exact value |
| --- | --- |
| Scheme | `https` |
| Host | `func-nac-bff-test-funktion8.azurewebsites.net` |
| Method | `GET` |
| Workspace | `notary_team_01` |
| Matter | `NAC-SYN-MATTER-001` |
| Path | `/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot` |
| Query | `purpose=view_synthetic_matter_workspace` |
| Wire schema | `nac.workbench.snapshot/v1` |

Redirects, alternate targets, cleartext HTTP and cache-busting changes are
forbidden. Every dispatched response must be exactly HTTP `200`, validate as
`nac.workbench.snapshot/v1` and be no larger than `128 KiB`. Bodies are validated
in memory and never retained.
The transport uses the same canonical exact-shape validator as the server-side
workbench projection. Unknown top-level or nested fields abort the lane. The
hashed instance-epoch header is emitted only for a successful response from
this exact workbench route, never for health, authentication or error responses.

## Capacity Preflight

Live execution is `BLOCKED` unless current authoritative evidence identifies
the tenant's SharePoint service tier and verifies both its request allowance
and resource-unit allowance. Estimates, defaults and inferred tiers are not
authoritative evidence.

The preflight also measures baseline tenant request and RU load and derives the
test allocation from a conservative RU-per-request upper bound. Baseline plus
planned test load must stay at or below `50%` of both verified allowances in
every allowance window defined by the authoritative tier. The lower resulting
rate controls every phase. Evidence older than 24 hours, evidence bound to
another tenant/workspace, or an unavailable allowance leaves status `BLOCKED`.
The authoritative attestation is read and validated again before every target
dispatch and after every idle phase. The owner gate binds the initially approved
hash; state and final evidence additionally bind the latest valid hash. A
refreshed attestation may not change the approved capacity policy.

The Azure preflight reads Azure Monitor and requires:

- `AlwaysReadyUnits=0`
- projected and observed acceptance execution units at or below the inclusive
  cap of `120,000 GB-s`
- continued monitor availability during and after the run

These are read-only checks. They do not permit a capacity, permission,
configuration or infrastructure change.
Azure Monitor evidence has its own source hash and is not represented as the
SharePoint capacity source.

## Global Dispatch Budget

Exactly one inclusive global ceiling applies across all phases:

```text
maximum target dispatches = 50,000
```

One successful complete acceptance run consumes exactly this bound allocation;
if the capacity preflight cannot admit it safely, the run remains `BLOCKED`.
Every target attempt counts, including attempts that time out,
fail authentication, redirect, throttle or trigger an abort. A sequence is
reserved atomically before network dispatch. No request is sent when the next
sequence would exceed `50,000`.

Client retries and automatic redirect following are disabled. There is no
unconditional 50,000-request phase and no unconditional requirement to finish
50,000 requests within two hours.

## Phases

The owner-bound phase planner allocates all phase budgets in advance. Their sum
must be at most `50,000`, and every rate is capped by the verified 50% request
and RU allowances.

| Phase | Safety-bound behavior |
| --- | --- |
| `cold_epoch_baseline` | Dispatch exactly one bound baseline request. |
| `cold_epoch_candidate` | Observe 20 minutes of runner idle time, then dispatch exactly one request; do not restart infrastructure. |
| `capacity_bounded_volume` | Dispatch 37,758 requests at no more than one request/second and at most twelve active hours. |
| `sustained_2h` | Run for at most two active hours at no more than 1.5 requests/second. |
| `soak_24h` | Run for at most 24 active hours, no faster than one request/minute and at most 1,440 dispatches. |

Accepted error rate is `0%`. Every request has a `20,000 ms` latency ceiling.
Volume and sustained phases require p95 at or below `2,000 ms` and p99 at or
below `5,000 ms`; soak requires p95 at or below `1,500 ms` and p99 at or below
`3,000 ms`. These metrics remain aggregate-only.

Phases are sequential and do not use catch-up bursts. A restart-safe state
persists the global sequence, consumed allocation and all contract, activation,
target, capacity and phase-plan hashes. Every checkpoint is durably written
before the next dispatch, bound to a SHA-256 sidecar and read back immediately.
On restart this store is the only resume source. Resume cannot lower counters, reuse a
sequence or increase an approved allocation.
A fatal response state is persisted before terminalization. After a crash, that
state is terminalized as failed without another target dispatch.

## Cold-Start Classification

The 20-minute idle observation alone does not prove a platform cold start.
`cold_start_classification` is `VERIFIED` only when authoritative server
telemetry proves that the server instance or server start epoch changed between
the bound baseline and the measured request.

When that change is absent, unchanged, unavailable or unprovable, the only
allowed classification is `INCONCLUSIVE`. Raw instance and start-epoch values
are never retained. Infrastructure is never restarted to force a result.

## Abort Behavior

The lane aborts without retry on:

- authentication failure or challenge
- any redirect response or `Location` signal
- any throttle status or throttle signal
- scheme, host, port, path, query, DNS, certificate or target-binding drift
- non-`200` status, schema failure or response above `128 KiB`
- request or aggregate phase-latency threshold breach
- exhaustion of the global dispatch, verified request/RU or Azure execution-unit budget
- stale or unavailable capacity or Azure Monitor evidence
- state corruption or evidence-redaction failure

An abort does not trigger rollback, deletion, permission or credential changes,
infrastructure restart, scaling or reconfiguration.
Capacity and Azure Monitor aborts are persisted as a terminal failed phase
before any possible resume. If the check fails before the first monitor
observation, only the two monitor aggregates are `null` in the failure artifact;
a `PASSED` artifact may never contain those null values.

## Aggregate Evidence

Evidence is redacted JSON plus semantically matching Markdown and contains
aggregates only: phase counts and metrics, global dispatch count, verified
allowance fractions used, Azure execution units, Always Ready units, cold-start
classification, the instance/epoch-change boolean, hash bindings and an abort
reason code, plus the final checkpoint hash. The evidence writer accepts an
artifact only when its aggregates are semantically consistent with the final
checkpoint that was read back immediately.

Evidence stores no per-request record, raw header, body, body hash, URL, path,
host, query, token, cookie, credential, tenant ID, user ID, server instance ID,
start epoch, provider response or Azure Monitor response. Unknown evidence
fields reject the artifact.

## Activation And Owner Gate

The offline planning command is implemented:

```text
nac m365 teams-sharepoint bff-performance-acceptance-plan --expected-activation-hash <sha256> --format json
```

A future live command remains bound to redacted activation evidence whose final
status is exactly `PASSED`. The owner approval binds the activation, contract,
fixed target, capacity preflight, phase plan and correlation ID. The planned
activation receipt must also match the current Azure BFF binding: function host,
workspace, and synthetic matter are checked against the fixed performance
target. A successful final artifact is valid only for the canonical phase plan
with exactly `50,000` target dispatches. The planned
command name is:

```text
nac m365 teams-sharepoint bff-performance-acceptance
```

It is activated only after the three live preflight adapters are implemented.
The safety runtime invokes its owner/activation verifier, capacity provider,
runtime monitor and exact fixed-transport verifier itself; `run()` does not
accept caller-constructed authorization or capacity objects.
Missing or mismatched
activation, owner, capacity or target bindings block before target dispatch.
