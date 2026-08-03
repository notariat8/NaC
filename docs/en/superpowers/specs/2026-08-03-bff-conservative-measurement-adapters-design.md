# Conservative BFF Measurement with Azure Monitor and Blob Lease

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: bff-conservative-measurement-adapters
leading_issue: https://github.com/notariat8/NaC/issues/733
risk_gate: External Service
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-08-03-bff-conservative-measurement-adapters.md
review_gates:
  - Privacy
  - Workflow
  - External Service
  - Human Approval
acceptance_ids:
  - AC-733-01
  - AC-733-02
  - AC-733-03
  - AC-733-04
  - AC-733-05
  - AC-733-06
  - AC-733-07
  - AC-733-08
validation_commands:
  - PYTHONPATH=src python3 -m unittest tests.test_nac_bff_azure_performance_acceptance tests.test_nac_bff_azure_performance_monitor tests.test_nac_bff_azure_performance_lease tests.test_nac_bff_azure_performance_runtime tests.test_nac_bff_azure_performance_owner_gate tests.test_nac_bff_azure_performance_infrastructure_safety tests.test_nac_bff_azure_live_commands tests.test_nac_bff_performance_coordination_iac
  - python3 scripts/validate_m365_azure_bff_performance_acceptance.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
```

## Goal

The performance lane measures only the behavior of the fixed synthetic BFF
endpoint. It establishes neither a tenant-wide SharePoint baseline nor a claim
about general SharePoint capacity. The canonical statements remain separate:
`tenant_wide_sharepoint_baseline_claim: NOT_CLAIMED`,
`tenant_wide_sharepoint_request_allowance_claim: NOT_CLAIMED`,
`tenant_wide_sharepoint_resource_unit_allowance_claim: NOT_CLAIMED`, and
`monetary_cost_claim: NOT_CLAIMED`. A successful run uses exactly 500 requests,
at most one concurrent request and no more than six dispatches per minute. The
first throttling, authentication, redirect, schema, lease, or monitor failure
ends the run without a retry.

## Acceptance criteria

- **AC-733-01:** Mode and evidence state `endpoint_scoped_conservative_measurement`; baseline, request allowance, resource-unit allowance, and monetary cost are each `NOT_CLAIMED`.
- **AC-733-02:** The deterministic plan stays bounded to 500 synthetic reads, concurrency one and at most six requests per minute. Results make no tenant-wide baseline claim.
- **AC-733-03:** The Azure Monitor adapter reads only the five fixed Flex Consumption metrics for the bound Function App ARM resource ID with API `2023-10-01`, `Total` and a fixed time window.
- **AC-733-04:** The lease adapter exposes only `acquire`, `assert_held` and `release` for a precreated dedicated blob. Break, delete, change and renew are not implemented.
- **AC-733-05:** Monitor, measurement, lease, bootstrap, and infrastructure-safety policies plus Bicep sources, canonical compiled ARM artifacts, and infrastructure parameters are separately hash-bound. Only a complete `SAFE` readback adds `infrastructure_safety_evidence_sha256`; ETag and lease binding are then created by bound Blob readback.
- **AC-733-06:** Resume uses the same target binding and lease ID. A foreign, lost or unprovable lease stops before the next BFF dispatch.
- **AC-733-07:** Evidence contains aggregates and hash bindings only, with no token, lease ID, URL, tenant/user ID or response content.
- **AC-733-08:** Infrastructure and live execution remain offline until one commit-, tree-, toolchain-, policy-, monitor- and lease-bound owner approval.

## Measurement boundary

The exact allocations are one cold baseline, one cold candidate, 90 endpoint
sample reads ten seconds apart, 120 reads across two hours and 288 reads during
the 24-hour soak. Their sum is 500. Every phase is open-loop paced without
catch-up, retries or automatic concurrency. A conservative 30,000 GB-s Azure
reserve (`500 * 2 GB * 30 s`) is projected over remaining work. Before each
dispatch the calculation includes that dispatch, and evidence binds
`projected_remaining_execution_units_gb_seconds`; it is exactly zero in
successful terminal measurement evidence. The static full-run projection
remains 30,000 GB-s. Azure Monitor
metrics prove only execution count and consumption for the single Function
App. HTTP responses and throttling signals prove only endpoint behavior during
this run.

## Monitor boundary

The adapter uses Azure Monitor Metrics REST API `2023-10-01` through the sealed
Azure CLI REST boundary. It accepts only `OnDemandFunctionExecutionUnits`,
`OnDemandFunctionExecutionCount`, `AlwaysReadyFunctionExecutionUnits`,
`AlwaysReadyUnits` and `AlwaysReadyFunctionExecutionCount`, each using `Total`
and `PT1M`. `metricnamespace=Microsoft.Web/sites`,
`AutoAdjustTimegrain=false` and `ValidateDimensions=true` are fixed. A dimension
filter is forbidden; each metric must return exactly one dimensionless,
app-wide `Total` series per partition. The cumulative run starts at the
owner-bound UTC minute anchor; final metrics are read only after at least 300
seconds of settlement. Dimension values, multiple or missing series, duplicate
minutes, changed timespans, or adjusted time grains block. Execution Units are
divided by exactly `1,024,000`
to obtain GB-s. Missing, negative, non-finite or unknown values block. The delta
is a conservative app-wide upper bound and is never attributed solely to the
test.

The final settled window must extend from the owner-bound anchor until
`monitor_window_end_utc` is at or after `measurement_finished_at_utc`; it is
read only after that end plus the settlement delay. Window start, end,
observation time, and `monitor_settlement_delay_seconds` are bound into final
evidence. A settled window ending before terminal measurement cannot support
acceptance.

## Lease boundary

A separate storage account and container `nac-bff-performance-leases` are
isolated from BFF deployment storage and WORM evidence. The sole blob path is
`locks/<target_binding_sha256>.lock`. Provisioning creates it before a run; the
runtime cannot create or delete it. The data-plane adapter uses Blob REST
`2023-11-03`, an infinite lease (`-1`) and a proposed UUID. Runner identity,
token audience `https://storage.azure.com/.default`, container scope,
`blobs/add/action`, `blobs/read`, and `blobs/write` DataActions, absence of
delete/owner/container rights, and an ABAC condition for the exact blob path are attested before
acquire. `assert_held` is a conditional `HEAD` using `If-Match` and
`x-ms-lease-id`; only `200`, `locked`, `leased`, `infinite` and the bound ETag
succeed. Because Azure RBAC does not separate lease break from blob write, the
absence of break/delete methods, exact header allowlists, the sealed HTTP
boundary and hash-bound owner approval form the additional safety boundary.

## Crash and resume

The runtime durably stores `ACQUIRE_INTENT` and `ACQUIRE_IN_FLIGHT` before its
single acquire. Only successful same-ID `assert_held` establishes `HELD`. A
crash after remote acquire is resolved only with that assertion; every other
result blocks without a second acquire. Every target dispatch requires the
lease. Terminal measurement is followed by `RELEASE_INTENT`, release and
readback. An uncertain release is classified by same-ID HEAD; if still held,
exactly one state-bound release reconciliation is allowed. Only durably stored
`RELEASED` permits final `PASSED` evidence. Break, reacquire and lease-ID changes
remain forbidden and require a dedicated recovery contract.
The release receipt must carry exact `RELEASED` plus the matching
`target_binding_sha256` and lease binding. A lifecycle-state hash without those
exact values is not proof of release.

## Owner binding

The canonical preimage contains exactly action, commit, tree, toolchain hash,
contract hash, activation hash, target, phase-plan, measurement, monitor, lease
and bootstrap-policy hashes, infrastructure-source, parameter and binding
hashes, correlation ID and owner login. Parameters bind the three separate
storage accounts, provisioner object ID, client IP, target binding, tenant,
subscription, resource group, `Incremental` mode, location, and canonical
tags. The approval permits exactly that bound custom-role definition and assignment;
other permission or credential changes remain forbidden.

The actual BFF and WORM storage resource IDs are part of the owner preimage.
Before deployment, ARM readback confirms those IDs and a name-availability check
proves that the coordination account is absent. After deployment, effective
direct, transitive-group, and inherited RBAC/ABAC assignments from tenant root
through the management-group chain to the container are verified against the
provisioner, role, DataActions, condition, and target path. CI must reproduce
the canonical ARM artifacts byte-for-byte with Bicep `0.45.15.27210`. The
strong Blob ETag and derived lease binding are then durably bound to state and
evidence before any monitor, lease, or BFF request.
The offline gate returns owner bindings only. Runtime verifies the complete
execution-binding set only after adding the safety-evidence digest. A local
nonblocking process fence covers one state path from preflight through final
evidence and blocks concurrent same-process-state execution before network.

The TOCTOU defense remeasures source-bound approval inputs immediately before
the first external command, verifies the target binding immediately before
every target dispatch, and remeasures the sealed Azure CLI toolchain
immediately before every subprocess. The command boundary admits only argv-only
`az rest --method get` using the exact canonical Monitor URL generated by the
adapter; method, body, query order, or extra-parameter drift blocks.

Before lease release, the terminal measurement is durably captured before the
final Monitor read. A failed final read retains the held lease and resumes by
repeating only that read. The final monitor attestation and execution cap are
then revalidated against settled-window coverage and zero projected remaining
work and stored in `pending-finalization` before release. Crash recovery may
reconcile release only with the same lease ID and target binding; acquire and
target dispatch are not repeated. Terminal finalization requires the exact
`RELEASED` receipt and at least 500 final on-demand executions, writes redacted
JSON and Markdown atomically, and then writes a completion manifest as the sole
commit point. The pending record is cleared only after that manifest. Completed final evidence
is an idempotent, validated, network-free readback.
