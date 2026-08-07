# M365 BFF Performance Acceptance

Status: Issue #735 implements the owner-bound live CLI and composition path
offline. It binds the reproducible WORM baseline before any irreversible lock,
coordination infrastructure, Azure Monitor, the dedicated Blob lease, and
exactly 500 synthetic GETs to one later owner approval. This slice creates no
Azure resource and performs no live call.

The machine-readable sources are the
[acceptance contract](../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)
and the
[verification contract](../../../workflows/verification-contracts/m365-bff-performance-acceptance.verification.json).
The exact mode is `endpoint_scoped_conservative_measurement`.

## Claim Boundary

This lane measures one synthetic GET endpoint only. It neither collects nor claims a
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

The local boundary is
`src/nac_bff/azure_performance_lease_broker_client.py`; the server-side broker
and durable state machine are in `src/nac_bff/azure_performance_lease_broker.py`
and `src/nac_bff/azure_performance_lease_broker_storage.py`. Lease storage, BFF
storage, and WORM evidence storage must be separate. The broker API may expose
only:

1. `acquire(-1)` with a UUID persisted first
2. `assert_held`
3. `release`

The persistent state machine is exactly `ACQUIRE_INTENT`,
`ACQUIRE_IN_FLIGHT`, `HELD`, `RELEASE_INTENT`, `RELEASED`, `LOST`. Before each target
dispatch, the same lease ID must be confirmed as held on the same bound blob.
Resume requires the same lease ID, target binding, and lease binding.
Every `assert_held` receipt is checked before clock, Monitor, or target work for
exact `HELD`, lease binding, target binding, and state digest. If a previously
held lease is authoritatively absent, the broker first persists terminal
`LOST`.

A lost or foreign lease and any binding drift block without dispatch.
Automatic reacquire, lease break, and blob delete are forbidden in the broker
and local adapter. The Function system-assigned identity may internally create the exact bound
zero-byte block blob once with `If-None-Match: *`, or inspect an existing blob
with `HEAD`. The broker generates the private Azure lease ID and returns no
lease ID, Storage token, or Storage URL to the local runner. An outcome may
become `PASSED` only after `RELEASED` is
durably stored. `HELD`,
an uncertain release outcome, or a merely sent release is insufficient.
The final release receipt must state exact `RELEASED`; final evidence stores it
as `lease_release_lifecycle_state` and separately binds
`lease_release_state_evidence_sha256`. Its
`target_binding_sha256` and `lease_binding_sha256` must match the measurement.
A lifecycle-state hash without the exact state and matching target binding is
not release proof.
The lease binding and `SHA256(lifecycle_state)` must also match the receipt
exactly. If the release response is lost and the lease is subsequently absent,
the state is conservatively persisted as terminal `LOST`; `RELEASED` is never
inferred from absence alone.

Before `acquire`, a canonical lease-acquisition safety envelope must validate
the complete infrastructure `SAFE` evidence and bind its coordination storage
resource ID, Function system identity, and provisioning caller to the exact
`lease_binding_sha256`, target binding, and signed activation ticket. The local
runner requests only `api://funktion8.de/nac-bff/.default`. The BFF accepts only
the fixed `Performance.Lease` app role; the RS256 ticket is valid for at most 60
seconds and binds exactly one operation plus owner, tenant, audience, actor,
commit, tree, Function package, plan, target, blob path, and nonce. Only the
Function system-assigned identity requests `https://storage.azure.com/.default` server-side. Any
mismatch blocks before broker state and Storage HTTP.
After a real process restart, infrastructure is re-attested read-only.
Serialized safety evidence alone authorizes nothing because the process-bound
capability is not serialized. Only fresh re-attestation preserving the same
owner, tenant, both principals, target, and lease binding may reconcile the existing
lease; stale pre-restart evidence cannot authorize another mutation.

The offline IaC is under
`deploy/runtime/azure/nac-bff-performance-coordination`. It binds the Function
system-assigned identity, the distinct provisioning caller, Function package, ticket certificate,
and the authoritative Function, VNet, and two distinct subnet resource IDs. The Flex
Function uses its dedicated `/27` integration subnet; the coordination Blob endpoint
uses the separate private-endpoint subnet and `privatelink.blob.core.windows.net`.
Public Storage network access is disabled. Shared keys, public
blobs, and delete, owner, or container DataActions remain excluded. Only the
Function system-assigned identity receives `blobs/read` and `blobs/write` on the exact container and
blob path; the local caller receives no Storage DataAction. Because Azure
`write` also covers overwrite and lease break, ABAC and the fixed broker API
jointly enforce the narrower operation boundary. The container metadata uses
exactly `nac.azure-bff-performance-coordination/v3`. Before acquire, the exact
`Performance.Lease` assignment and hash-bound Function settings are configured
and read back without exposing their values.
The role-assignment ID is stably bound to the authoritative Function resource
ID, while its principal is resolved from the current system-assigned identity.
ARM does not permit the principal ID that is resolved only at deployment time
to participate in the role-assignment name. Identity rotation is therefore
deliberately fail-closed: Azure must not update an existing role assignment to
another principal. Effective RBAC readback indexes every visible role
assignment at every inspected ancestor scope, not only assignments for the
expected principal. A stale assignment to a previous Function system identity
blocks the run. A stale assignment is neither
deleted nor rolled back automatically; before reassignment after identity
rotation, removing it requires a separately owner-approved and evidence-bound
cleanup.
The existing Function runtime UAMI remains separately bound to Graph, host
storage, and Application Insights. A separate, complete effective-RBAC readback
must prove exactly zero effective coordination-Storage DataActions for it,
regardless of role name or built-in, custom, direct, group, or inherited source.

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
is preceded by create-once restart receipts: the first successful run persists
the original `nameAvailable=true` receipt before the first deployment and an
exact `Succeeded` deployment receipt immediately after coordination deployment.
On restart with a complete receipt pair, a fresh GET of the same deterministic
deployment is validated before any provider mutation. Owner, target, source,
parameter, and hash bindings must match; this path performs exactly zero name
probes and zero deployment creates, then repeats all safety readbacks freshly.
`Running`, `Failed`, missing, replaced, incomplete, tampered, or mismatched
receipts block. If a crash leaves only the original name receipt, the fresh-name
path may continue only after a new current `nameAvailable=true` probe; otherwise
it blocks without redeployment. Historical receipt state alone never authorizes
a deployment. The strict temporal relation is
`original observed < started <= completed < current reconciliation observed`.
The postdeployment readback
must prove its exact resource ID, location, effective tags, and complete
storage/network configuration: public network disabled, default `Deny`, bypass
`None`, no IP, VNet, or resource-access rule, exactly one Blob private endpoint
on the owner-bound private-endpoint subnet, one `privatelink.blob.core.windows.net`
zone group, and one link to the owner-bound VNet. The Function readback must show
the distinct owner-bound Flex integration subnet. Shared keys and public blobs
remain disabled, with TLS 1.2 and HTTPS only. Blob versioning and Blob/container
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
account, blob service, and container must prove the exact bootstrap and runtime identities,
all transitive Entra groups, role, DataActions, condition, and scope; any
broader direct, group-based, or inherited data-plane assignment, and every
effective control-plane assignment, blocks bootstrap and lease acquire. The
infrastructure safety evidence uses exactly
`nac.azure-bff-performance-infrastructure-safety-evidence/v8`. A
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
release. An early cleanup release is likewise bound first by an atomic
`nac.m365-bff-performance-release-recovery/v1` checkpoint. After process
restart this checkpoint is reconciled before any new acquire and is cleared
only after an exact `RELEASED` receipt. A crash-safe resume may reconcile release only with the same lease ID
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

This PR performs no live action: no Azure resource action, Blob or lease
mutation, Monitor read, or target dispatch. The implemented live CLI path,
`nac m365 teams-sharepoint bff-performance-acceptance`, remains closed by the
two flags `--owner-approved` and `--execute-live-acceptance`, each required
exactly once, plus the immutable owner gate. It executes only after a fresh
hash-bound owner approval. Direct adapter calls fail before token, network, or
state access unless they receive the exact bounded capability issued after
immutable owner-comment and sealed infrastructure-safety verification; every
Blob call, Monitor read, and target GET requires this fresh owner-bound
capability.
