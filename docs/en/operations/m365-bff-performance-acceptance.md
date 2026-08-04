# M365 BFF Performance Acceptance

Status: Issue #733 defines an offline contract and offline adapters for Azure
Monitor and a dedicated Azure Blob lease. No live CLI command or live action is
implemented.
Issue #735 additionally binds the reproducible WORM baseline, before any
irreversible policy lock, and the coordination infrastructure to the same
future owner approval. This offline slice creates no Azure resource.

The machine-readable sources are the
[acceptance contract](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)
and the
[verification contract](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).
The exact mode is `endpoint_scoped_conservative_measurement`.

## Claim Boundary

This lane measures one synthetic GET endpoint only. It does not claim a
tenant-wide SharePoint baseline, tenant-wide request allowance, or tenant-wide
resource-unit allowance. The status of all three claims is explicitly
`NOT_CLAIMED`.

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
| 3 | `endpoint_scoped_sample` | 90 | 10 seconds |
| 4 | `sustained_2h` | 120 | 60 seconds |
| 5 | `soak_24h` | 288 | 300 seconds |

Client concurrency is always `1`, with an inclusive maximum of `6` target
dispatches per minute. Catch-up bursts, parallel phases, and replay of completed
phases are forbidden. Every reserved attempt counts; an uncertain in-flight
outcome is not sent again after a crash.
Immediately before the HTTP call, the runner durably stores
`transport_boundary_crossed` and increments
`completed_network_dispatch_count`. A crash after dispatch therefore cannot
lower the final Monitor floor. Target drift or another deterministic failure
after reservation but before that boundary is instead completed as one failed
attempt with zero network dispatches, so its terminal evidence remains valid.

Cold-start classification is `VERIFIED` only when the bound server instance or
start epoch demonstrably changed. Every other outcome is `INCONCLUSIVE`. Raw
instance and epoch values are not stored, and infrastructure is not restarted
for the measurement.

## Azure Monitor

The offline adapter is
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
- no dimension filter; unfiltered app-wide rollup

Each metric must return exactly one dimensionless `Total` series per
partition. The value therefore remains a conservative app-wide rollup and is
not attributed to one endpoint or instance. Each ARM request must align to UTC
minutes, span between `60` and
`86,400` seconds, and have ended at least `300` seconds before observation.
Longer observation ranges are partitioned without gaps into requests of at
most 24 hours and then cumulatively bound. Every returned series must contain
the complete `PT1M` grid for its partition. Unknown
fields, missing or multiple series, dimension values, duplicate timestamps,
and unsettled windows block.

The final settled window starts at the owner-bound `monitor_window_anchor` and
must cover through terminal measurement: `monitor_window_end_utc` is at or
after `measurement_finished_at_utc`, and `monitor_observed_at_utc` is only after
that window end plus the `300`-second settlement delay. Final evidence binds
these timestamps and `monitor_settlement_delay_seconds`.
An earlier settled window is insufficient even when all values are below the
cap.

For a successful run, Monitor must show at least all `500` GETs. For a failed
run, the minimum is not the number of reserved attempts but
`completed_network_dispatch_count`: only requests that reached the HTTP
transport are required. A token or target-binding failure before HTTP can
therefore terminalize with zero and still release the lease with evidence.

The static projection for the complete run is exactly `30,000 GB-s`. Before
each dispatch, the remaining projection covers the remaining GETs plus up to
`30` dispatched requests not yet settled in Monitor, corresponding to five
minutes of ingestion lag at no more than six dispatches per minute. Every
safety observation binds this conservative
`projected_remaining_execution_units_gb_seconds` value. The inner measurement
evidence may still contain this reserve. Only the outer completion evidence,
created after final settlement, must bind projected remaining to exactly zero;
the separately named static full-run projection remains `30,000 GB-s`.
The app-wide observed delta plus projected remaining GETs must not exceed the
inclusive `120,000 GB-s` cap. Every Always Ready metric must be exactly zero.
The same cap applies after final settlement; a cap breach or unavailable
observation fails closed.
This is an execution-consumption guardrail, not a monetary cost estimate.
Monetary cost is `NOT_CLAIMED`: function execution-count charges, Azure Monitor
query or ingestion charges, Blob storage and transactions, networking, taxes,
credits, free grants, and current pricing are deliberately outside this claim.

## Exclusive Lease

The dedicated offline adapter is
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
Automatic reacquire, lease break, and blob delete are forbidden in the runtime
adapter. A separate bootstrap adapter may create the exact bound zero-byte
block blob once with `If-None-Match: *`, or inspect an existing blob only with
`HEAD`. Overwrite is forbidden; the strong response ETag becomes part of the
later lease binding. An outcome may become `PASSED` only after `RELEASED` is
durably stored. `HELD`,
an uncertain release outcome, or a merely sent release is insufficient.
The final release receipt must state exact `RELEASED`; final evidence stores it
as `lease_release_lifecycle_state` and separately binds
`lease_release_state_evidence_sha256`. Its
`target_binding_sha256` and `lease_binding_sha256` must match the measurement.
A lifecycle-state hash without the exact state and matching target binding is
not release proof.

Before `acquire`, a canonical lease-acquisition safety envelope must validate
the complete infrastructure `SAFE` evidence and bind its coordination storage
resource ID and provisioner principal to the exact `lease_binding_sha256`,
strong ETag, target binding, and token subject (`oid`). The envelope digest and
lease digest are runtime execution bindings. The lease adapter accepts neither
a raw nor a merely decoded JWT. The token provider must return a sealed result
binding scope, identity, `oid`, `tid`, `nbf`, and `exp`; `alg:none` is rejected
before state or HTTP. The `oid` and `tid` claims are checked against owner-bound
evidence. In addition, `aud` must equal `https://storage.azure.com` and
the numeric time claims must satisfy `nbf <= trusted_clock < exp`. Any mismatch
blocks before state and without an acquire request.
After a real process restart, infrastructure is re-attested read-only.
Serialized safety evidence alone authorizes nothing because the process-bound
capability is not serialized. Only fresh re-attestation preserving the same
owner, tenant, principal, target, and lease binding may reconcile the existing
lease; stale pre-restart evidence cannot authorize another mutation.

The offline IaC is under
`deploy/runtime/azure/nac-bff-performance-coordination`. It binds the existing
Entra service principal by object ID, allows only one explicit client IP on the
storage endpoint, and sets the network default to `Deny`. Shared keys, public
blobs, and delete, owner, or container DataActions remain excluded. The
exact-path role includes `blobs/add/action` for the one-time conditional
creation, `blobs/read` for readback, and `blobs/write` for lease operations.
Azure also authorizes overwrite and lease break through the write DataAction.
ABAC therefore fixes the path while
the sealed application API fixes the operation: bootstrap only uses
conditional `PUT` or `HEAD`; runtime only acquires, asserts, and releases. The
strong ETag is then carried into the runtime binding. The blob token is
requested only for scope `https://storage.azure.com/.default`.

## Owner Gate And Evidence

The combined infrastructure and live acceptance requires exactly one owner
approval. Before provisioning it binds all deterministic inputs:

- `approved_commit_sha`
- `approved_tree_sha`
- `toolchain_attestations_sha256`
- `contract_sha256`
- `phase_plan_sha256`
- `measurement_policy_sha256`
- `monitor_policy_sha256`
- `lease_policy_sha256`
- `lease_bootstrap_policy_sha256`
- `infrastructure_safety_policy_sha256`
- `infrastructure_source_sha256`
- `infrastructure_parameters_sha256`
- `infrastructure_binding_sha256`
- `worm_baseline_binding_sha256`
- `worm_baseline_compiled_arm_sha256`
- `worm_baseline_parameters_sha256`
- `worm_baseline_source_sha256`
- `deployment_sequence_sha256`
- `target_binding_sha256`
- `expected_activation_hash`
- `correlation_id`
- `monitor_window_anchor_utc`
- `monitor_window_anchor_sha256`

`infrastructure_source_sha256` binds both the Bicep sources and the canonical
ARM/parameter artifacts compiled with Bicep `0.45.15.27210`. CI must reproduce
both artifacts byte-for-byte, and the later live path uses only that bound
output.

The WORM baseline is created before the coordination infrastructure in the
same `rg-nac-bff-test` resource group and is then read back. The bound sequence
must not set an irreversible immutability lock. Such a lock remains a separate
future governance decision.

The whole-minute UTC `monitor_window_anchor` bounds the earliest monitor
observation. Immediately before the first lease or monitor network call,
commit, tree, toolchain, contract, infrastructure sources, and parameters are
remeasured from their actual sources. Drift blocks before network access.
The TOCTOU boundary continues during execution: the target binding is checked
immediately before every target dispatch, and the sealed Azure CLI toolchain is
remeasured immediately before every subprocess. The Monitor command boundary
revalidates the target after token acquisition and constructs the request only
from the previously captured approved endpoint. It
accepts only argv-only `az rest --method get` with the exact canonical URL
generated by the read-only adapter; a body, method drift, reordered query, or
additional query parameter is blocked. Every Monitor read consumes its own
owner- and policy-bound capability before token or network access; at most
`2048` reads are allowed. This budget is separate from the durable 500-GET
ledger. The generic Azure CLI adapter rejects Monitor metrics URLs; only the
dedicated consuming Monitor method may execute them. Target GET, Blob
bootstrap, and lease acquire each consume their capability before token
acquisition or state persistence. Delegated M365 tokens are cryptographically
validated against Entra RS256, resource, and scopes before sealing.
The parameters additionally bind the exact tenant, subscription, resource
group `rg-nac-bff-test`, `Incremental` deployment mode,
`germanywestcentral` location, and the canonical effective tag set formed from
owner tags plus the seven immutable NaC coordination tags.
The actual resource IDs of the existing BFF storage and WORM evidence storage
are also bound in advance. The predeployment name check must prove that the
coordination account does not yet exist. A separate postdeployment readback
must prove its exact resource ID, location, effective tags, and complete
storage/network configuration: public network enabled, default `Deny`, bypass
`None`, exactly one allowed IP rule, no VNet or resource-access rule, no shared
keys or public blobs, TLS 1.2, and HTTPS only. Blob versioning and Blob/container
delete retention must be disabled. The lease container must have
`publicAccess=None` and exactly the bound metadata for schema, synthetic
classification, lock path, Blob type, bootstrap, authorization boundary, and
principal separation. The name check, bound deployment receipt, and
postdeployment/RBAC readbacks must occur in that order and carry the same owner
binding and internally generated one-use nonce. Nonce reuse is rejected. Every
readback binds the actual sealed executable, argv, toolchain, and run session;
trusted verification time is generated internally. The predeployment proof may be at most 30 minutes old; postdeployment
and RBAC proofs may be at most five minutes old, with at most 30 seconds of
future skew. After deployment, complete Effective RBAC/ABAC readback must start
at the tenant-root management group matching the owner tenant and prove the
subscription's authoritative ordered management-group ancestry. It covers
tenant root, the management-group chain, subscription, resource group, storage
account, blob service, and container must prove the exact provisioner identity,
all transitive Entra groups, role, DataActions, condition, and scope; any
broader direct, group-based, or inherited data-plane assignment, and every
effective control-plane assignment, blocks bootstrap and lease acquire. A
caller-selected Azure scope mismatch blocks before network access, and the
Bicep template independently fails when its actual tenant, subscription, or
resource group differs from those bound parameter values.

The approval permits exactly the custom-role definition and assignment bound
by this infrastructure plan. Credential changes and every other permission
change not bound by the source, parameter, and infrastructure hashes remain
forbidden.

The actual ETag and derived `lease_binding_sha256` only exist after the bound
bootstrap readback. State and evidence must bind both before the first target
dispatch. Any deterministic mismatch blocks before network access; readback
drift blocks before measurement. Monitor, lease, and infrastructure bindings
remain separate from each other and from WORM evidence.
The offline gate deliberately returns only `owner_execution_bindings`. Only the
canonically validated `SAFE` readback adds
`infrastructure_safety_evidence_sha256` to form complete runtime execution
bindings. The post-bootstrap composition additionally binds
`lease_binding_sha256` and
`lease_acquisition_safety_evidence_sha256`. This composition must match exactly before lease acquire;
caller-supplied hashes are never copied into final evidence without that
verification. Immediately after the complete readback, commit, tree, contract,
toolchain, infrastructure sources, and parameters are measured again; any
drift blocks before lease acquire. A nonblocking local process fence covers the complete measurement
and finalization lifecycle for one state path, so a second process blocks before
owner verification or network access.
The public readback adapter itself produces verifier-ready ARM, Graph, and
effective-RBAC envelopes from fixed allowlisted calls. Its subprocess environment
is sanitized and bound, and the Azure CLI executable is remeasured immediately
before every subprocess. Privately handcrafted evidence is not a production
path.

The measurement engine first emits only evidence with
`final_acceptance_scope: MEASUREMENT_ONLY_LEASE_RELEASE_PENDING`. Only the
runtime wrapper may emit final
`nac.m365-bff-performance-final-evidence/v1` evidence with status `PASSED`
after independently confirming state `RELEASED`. The terminal measurement is
first persisted as `nac.m365-bff-performance-terminal-measurement/v1`, before
the final Monitor read. A failed or unsettled Monitor read therefore retains
both this checkpoint and the held lease; resume repeats only the final Monitor
read, never the owner preflight, acquisition, runner, or target traffic. After
the settled-window coverage, monitor attestation, target and hash bindings, and
zero-remaining execution budget are validated, a durable
`nac.m365-bff-performance-pending-finalization/v1` record is written before
release. A crash-safe resume may reconcile release only with the same lease ID
and exact target binding; it may not acquire, reread Monitor, or dispatch the
target.
Authoritative checkpoints are opened with `O_NOFOLLOW` and validated with
`fstat` on that same descriptor; atomic replacement uses a directory descriptor
whose owner and mode were already validated. Symlinks or unsafe parent
directories block.
If the runner raises at a clean checkpoint, the same held lease is retained
until the runner either resumes or durably terminalizes that checkpoint as
`FAILED`; the wrapper never releases first and leaves resumable measurement
state behind.
Terminal finalization requires an exact `RELEASED` receipt, and the final
Monitor proof must include at least the 500 bound on-demand executions for
`PASSED`, or the nested durable `completed_network_dispatch_count` for
`FAILED`. Final validation cross-binds this derived minimum and the nested
measurement status to the final Monitor attestation. JSON
and Markdown are each written atomically with a directory `fsync`. A final
`nac.m365-bff-performance-completion-manifest/v1` written last binds both exact
file hashes and the final evidence hash and is the sole commit point; without a
valid manifest no final evidence exists. The pending record is cleared only
after that manifest. A crash between terminal measurement and final persistence
therefore
cannot leave a false final pass or replay test traffic.
The 500-execution floor applies only to `PASSED`. A valid early `FAILED` run
requires at least its actually dispatched attempts in the final Monitor read,
still durably releases the same lease, and writes redacted final failure
evidence.
A later invocation first repeats the current owner-bound and infrastructure-safety
preflight, then validates and returns completed final evidence without lease,
Monitor, or target network actions.

Evidence contains only redacted aggregates, gate and readback bindings, app-wide
monitor deltas, projected remaining budget, phase aggregates, abort code, and
final lease state. It explicitly retains `tenant-wide SharePoint baseline:
NOT_CLAIMED`, `tenant-wide SharePoint request allowance: NOT_CLAIMED`,
`tenant-wide SharePoint resource-unit allowance: NOT_CLAIMED`, and
`monetary cost: NOT_CLAIMED`. Per-request records, raw responses, URLs,
headers, bodies, tokens,
tenant/user/instance/epoch values, and the raw lease ID are forbidden.

## Live Boundary

The existing plan command remains offline and sends zero requests:

```text
nac m365 teams-sharepoint bff-performance-acceptance-plan
```

Issue #733 implements the adapters for offline verification, but activates no
live CLI command, Azure resource action, Blob or lease mutation, Monitor read,
or target dispatch. Direct adapter calls fail before token, network, or state
access unless they receive the exact bounded capability issued after immutable
owner-comment and sealed infrastructure-safety verification. A later live
composition requires that fresh owner-bound capability for every Blob call,
Monitor read, and target GET.
