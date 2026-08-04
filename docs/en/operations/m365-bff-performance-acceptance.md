# M365 BFF Performance Acceptance

Status: Issue #735 implements the Azure Monitor adapter, dedicated Azure Blob
lease, and central owner-gated live CLI offline. This PR creates or changes no
Azure resource, performs no live Blob or lease access, and sends no live load
request.

The machine-readable sources are the
[acceptance contract](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)
and the
[verification contract](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).
The exact mode is `endpoint_scoped_conservative_measurement`.

## Claim Boundary

This lane measures one synthetic GET endpoint only. It does not claim a
tenant-wide SharePoint baseline, tenant-wide request allowance, tenant-wide
resource-unit allowance, or tenant-wide monetary baseline. The status of all
four claims is explicitly `NOT_CLAIMED`.

Results must not be extrapolated to other endpoints or to tenant SharePoint
capacity. Azure Monitor values are conservatively used app-wide deltas for the
bound Function App. They are not attribution to the measured endpoint and are
not a SharePoint capacity source.

## Fixed Target

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

Redirects, alternate hosts, cleartext HTTP, cache busting, and automatic
retries are forbidden. Every response must be HTTP `200`, match the exact wire
schema, and remain at or below `128 KiB`. Neither body nor body hash is stored.

## Fixed Measurement Plan

One complete run sends exactly `500` synthetic GETs. The phase allocations are
`1, 1, 90, 120, 288`; the repeating intervals are `10, 60, 300` seconds.

| Order | Phase | GETs | Interval |
| --- | --- | ---: | ---: |
| 1 | `cold_epoch_baseline` | 1 | immediate |
| 2 | `cold_epoch_candidate` | 1 | after 1,200 seconds of runner idle time |
| 3 | `interval_10s` | 90 | 10 seconds |
| 4 | `interval_60s` | 120 | 60 seconds |
| 5 | `interval_300s` | 288 | 300 seconds |

Client concurrency is always `1`, with an inclusive maximum of `6` target
dispatches per minute. Catch-up bursts, parallel phases, and replay of completed
phases are forbidden. Every reserved attempt counts; an uncertain in-flight
outcome is not sent again after a crash.

Cold-start classification is `VERIFIED` only when the bound server instance or
start epoch demonstrably changed. Every other outcome is `INCONCLUSIVE`. Raw
instance and epoch values are not stored, and infrastructure is not restarted
for the measurement.

## Azure Monitor

The offline-implemented adapter is
`src/nac_bff/azure_performance_monitor.py`. It plans only a read-only ARM GET
against the fixed `Microsoft.Insights/metrics` path for the bound Function App.
Exactly these settings are allowed:

- API version `2023-10-01`
- namespace `Microsoft.Web/sites`
- `OnDemandFunctionExecutionUnits`
- `OnDemandFunctionExecutionCount`
- `AlwaysReadyFunctionExecutionUnits`
- `AlwaysReadyUnits`
- `AlwaysReadyFunctionExecutionCount`
- aggregation `Total` and interval `PT1M`
- dimension filter `Instance eq '*'`

Each metric is the sum of every `Total` point across all unique `Instance`
series. Windows must align to UTC minutes, span between `60` and `86,400`
seconds, and have ended at least `300` seconds before observation. Unknown
fields, missing series, duplicate instances or timestamps, and unsettled
windows block.

The static projection for the complete run is exactly `30,000 GB-s`. Before
each dispatch, the remaining projection is proportional to the remaining GETs.
The app-wide observed delta plus projected remaining GETs must not exceed the
inclusive `120,000 GB-s` cap. Every Always Ready metric must be exactly zero.
The same cap applies after final settlement; a cap breach or unavailable
observation fails closed.

## Exclusive Lease

The dedicated, offline-implemented adapter is
`src/nac_bff/azure_performance_lease.py`. Lease storage, BFF storage, and WORM
evidence storage must be separate. The adapter may expose only:

1. `acquire(-1)` with a UUID persisted first
2. `assert_held`
3. `release`

The persistent state machine is exactly `ACQUIRE_INTENT`,
`ACQUIRE_IN_FLIGHT`, `HELD`, `RELEASE_INTENT`, `RELEASED`. Before each target
dispatch, the same lease ID must be confirmed as held on the same bound blob.
Resume requires the same lease ID, target binding, and lease binding.

A lost or foreign lease and any binding drift block without dispatch.
Automatic reacquire, lease break, blob delete, and blob create are forbidden.
An outcome may become `PASSED` only after `RELEASED` is durably stored. `HELD`,
an uncertain release outcome, or a merely sent release is insufficient.

## Owner Gate And Evidence

Exactly one immutable owner approval jointly binds unlocked WORM baseline
deployment, dedicated coordination infrastructure deployment, runtime
execution, and redacted evidence. Partial approvals, stage-specific approvals,
and caller-supplied hashes are rejected before the first write. The approval
binds these fields:

- `approved_commit_sha`
- `approved_tree_sha`
- `toolchain_attestations_sha256`
- `activation_evidence_sha256`
- `contract_sha256`
- `phase_plan_sha256`
- `measurement_policy_sha256`
- `monitor_binding_sha256`
- `lease_binding_sha256`
- `target_binding_sha256`
- `worm_baseline_source_sha256`
- `worm_baseline_parameters_sha256`
- `coordination_source_sha256`
- `coordination_parameters_sha256`
- `runtime_composition_sha256`
- `evidence_policy_sha256`
- `infrastructure_binding_sha256`

Any mismatch blocks before the first write. Monitor, lease, target, source,
parameter, runtime, evidence, and infrastructure bindings remain separate and
must all match the immutable comment.

Evidence contains only redacted aggregates, the nine gate bindings, app-wide
monitor deltas, projected remaining budget, phase aggregates, abort code, and
final lease state. It explicitly retains `tenant-wide SharePoint baseline:
NOT_CLAIMED` and `tenant-wide monetary baseline: NOT_CLAIMED`. Per-request
records, raw responses, URLs, headers, bodies, tokens, tenant/user/instance/epoch
values, and the raw lease ID are forbidden.

## Bound Live Package

The existing plan command remains offline and sends zero requests:

```text
nac m365 teams-sharepoint bff-performance-acceptance-plan
```

The centrally composed live command is implemented offline:

```text
nac m365 teams-sharepoint bff-performance-acceptance
```

After verification of the same immutable owner approval, the fixed order is:
deploy and read back the unlocked WORM baseline, deploy and read back the
coordination infrastructure including RBAC, bootstrap the coordination Blob,
acquire the lease, execute exactly `500` synthetic GETs, finalize Azure
Monitor, release the lease, and write redacted evidence. Each stage is a
precondition for the next; partial deployment or binding drift fails closed.

The WORM baseline is deployed unlocked only. An irreversible WORM policy lock
is outside this lane and remains separately owner-gated. In this PR, Azure
resource creations or changes, live Blob or lease operations, synthetic target
dispatches, and irreversible WORM locks are each exactly `0`.
