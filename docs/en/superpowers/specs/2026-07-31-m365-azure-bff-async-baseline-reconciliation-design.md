# M365 Azure BFF Reconciliation Of An Asynchronously Completed Baseline

Status: offline safety rework for a protected PR
Date: 31 July 2026
Scope: read-only classification and separate terminalization of the interrupted run bound to Issue #719

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-azure-bff-async-baseline-reconciliation-719
leading_issue: https://github.com/notariat8/NaC/issues/719
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-31-m365-azure-bff-async-baseline-reconciliation.md
review_gates:
  - External Service
  - Human Approval
acceptance_ids:
  - AC-719-01
  - AC-719-02
  - AC-719-03
  - AC-719-04
  - AC-719-05
  - AC-719-06
validation_commands:
  - python3 -m unittest tests.test_nac_bff_azure_interruption_baseline tests.test_nac_bff_azure_interruption_reconciliation tests.test_nac_bff_azure_live_commands tests.test_nac_bff_azure_activation_cli tests.test_m365_azure_bff_live_activation_contract
  - python3 scripts/validate_m365_azure_bff_live_activation.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/quality_gate.py --profile strict
  - git diff --check
```

## Initial State

The BFF run bound to Issue #719 was externally terminated by an operator
timeout during `ensure_resource_group`. The persisted runner state still
contains exactly step 1 as `PASSED`, step 2 as `RUNNING`, six valid
hash-chained ledger events, and the three `target`, `legacy`, and
`legacy_host` journals as `HELD`.

After the process ended, the ARM/Bicep deployment that had already started
continued asynchronously to completion. The resource group is `Succeeded`
and contains the complete expected baseline. This provider state must neither
retroactively set persisted step 2 to `PASSED` nor permit resume.

## Separate Provider Classifications

`RESOURCE_GROUP_ONLY` remains unchanged as the legacy classification from
Issue [#717](https://github.com/notariat8/NaC/issues/717). It fail-closed
accepts only the successful resource group with an exactly empty resource
inventory. Its terminalization remains bound to an immutable owner comment in
Issue #717 and carries no baseline hash fields.

`BICEP_BASELINE_EXACT` is the separate classification for Issue
[#719](https://github.com/notariat8/NaC/issues/719). It is not a generic
allowance for non-empty resource groups. It applies only when prepared inputs
are present and fully hash-bound, and when the provider inventory, ARM
deployment, and deployment operations are derived exactly from those inputs.
Every other classification and every mixed state is rejected fail-closed.

## Prepared Hash Bindings

The baseline expectation is derived exclusively from artifacts already
prepared in the run directory:

- `prepared/prepared-inputs.redacted.json` binds the activation hash, approved
  commit and tree, and the prepared-input digests.
- `prepared/main.json` is the unchanged Bicep/ARM template snapshot.
- `prepared/main.parameters.json` is the unchanged parameter snapshot.

The approved commit and tree are additionally read directly through the trusted resolved local Git binary. The resulting tree-manifest hash and the blob hash of `deploy/runtime/azure/nac-bff/infra/compiled/main.json` must exactly match the prepared manifest and `prepared/main.json`. Git replace refs are disabled for every read; listing and archive address only the approved tree object hash, and each archived blob is rechecked against its Git blob ID. Self-consistent prepared files therefore cannot assert false Git provenance. All nine bound Bicep parameters are checked for their exact key set and values.

The SHA-256 of the raw prepared manifest,
`prepared_inputs_manifest_sha256`, the template snapshot hash
`bicep_snapshot_sha256`, and the parameter snapshot hash
`bicep_parameters_snapshot_sha256` must match both the manifest values and
the actual bytes. Template metadata, the canonical resource graph, deployment
name, canonically normalized parameters, and the exact operation-type
distribution form the canonical baseline expectation. Its SHA-256 is
`baseline_expectation_sha256`.

Missing, partial, or syntactically invalid prepared artifacts return
`INTERRUPTION_BASELINE_BINDING_INVALID`. Mismatched activation, commit, tree,
manifest, template, or parameter bindings return
`INTERRUPTION_BASELINE_BINDING_MISMATCH`.

## Exact Baseline

The top-level inventory contains exactly seven resources, neither fewer nor
additional:

1. Storage Account (`Microsoft.Storage/storageAccounts`)
2. Log Analytics Workspace (`Microsoft.OperationalInsights/workspaces`)
3. App Service Plan (`Microsoft.Web/serverfarms`)
4. User Assigned Managed Identity (`Microsoft.ManagedIdentity/userAssignedIdentities`)
5. Application Insights Component (`Microsoft.Insights/components`)
6. Function App (`Microsoft.Web/sites`)
7. Smart Detection Action Group (`Microsoft.Insights/actionGroups`)

Each resource must match the expected full ARM ID, type, deterministically
derived name, resource group, region, tags, and expected `kind` and SKU. The Smart Detection Action
Group is the only global resource and has no workload tags. Deployment outputs
must exactly bind the Function App ID and host name and the resource, client,
and principal IDs of the User Assigned Managed Identity.
The User Assigned Managed Identity and the Function App identity assignment are
also read explicitly through narrow read-only commands. Tenant, client, and
principal IDs and the single `UserAssigned` assignment must match inventory and
deployment outputs.

The ARM deployment must be `Succeeded`, `Incremental`, and bound to the
prepared template and parameter hashes. It has exactly twelve successful
deployment operations with this type distribution:

- two `Microsoft.Authorization/roleAssignments`
- one operation each for `Microsoft.Insights/components`,
  `Microsoft.Insights/components/currentBillingFeatures`,
  `Microsoft.ManagedIdentity/userAssignedIdentities`,
  `Microsoft.OperationalInsights/workspaces`,
  `Microsoft.Storage/storageAccounts`,
  `Microsoft.Storage/storageAccounts/blobServices`,
  `Microsoft.Storage/storageAccounts/blobServices/containers`,
  `Microsoft.Web/serverfarms`, `Microsoft.Web/sites`, and
  `Microsoft.Web/sites/config`

Each deployment operation must additionally target the exact expected top-level, child, or role-assignment ARM ID. The Smart Detection action group is read directly; its enabled state and all expected email, SMS, webhook, Azure app push, and voice receivers must match exactly. All twelve deployment target resources are also read directly through read-only commands. An exactly bound Azure Resource Graph POST additionally enumerates all resources and authorization resources in the target scope. Its set must equal the union of inventory and deployment targets exactly; neither extra child resources nor additional role assignments are allowed. Storage security settings, blob retention, container public access, workspace and Insights authentication, Function App configuration, app settings, and both role assignments must equal the Bicep target state as exact property objects; only a redacted target-hash, count, and result summary leaves the observation port.

Partial inventory, additional resources, an incorrect operation count, failed
operations, or ID, target-ID, kind, SKU, type, name, region, tag, Smart
Detection, deployment, output, or managed identity drift returns
`PROVIDER_OBSERVATION_INVALID`.

## Double Read-Only Observation

Each snapshot reads Azure state only: account, the three expected providers,
resource group and resource inventory, and, for a non-empty inventory, the
bound deployment, its operations, the User Assigned Managed Identity, and the
Function App identity assignment. The inventory is read a second time
within each snapshot. The complete snapshot is then collected again. Both
canonical observations must be byte-identical and produce the same
`provider_observation_sha256`; otherwise the result is
`PROVIDER_OBSERVATION_DRIFT`.

Inspection mutates neither local artifacts nor Azure or tenant state. It emits
`MIDRUN_RECONCILIATION_REQUIRED`, redacted observation and binding hashes, and
the canonical owner comment. It is neither terminalization nor a success
classification.

## Separate #719 Terminalization

The old #632 live approval identifies the interrupted run only. For
`BICEP_BASELINE_EXACT`, `--confirm-terminalize-and-release` additionally
requires an immutable owner comment from Issue #719. Compared with the legacy
#717 binding, its canonical body adds exactly:

- `provider_classification` with `BICEP_BASELINE_EXACT`
- `baseline_expectation_sha256`
- `prepared_inputs_manifest_sha256`
- `bicep_snapshot_sha256`
- `bicep_parameters_snapshot_sha256`

All existing state, ledger, lock, provider, reconciler, and owner bindings
remain mandatory. The action remains exactly
`TERMINALIZE_AND_RELEASE_LOCK_ONLY`. Before the first local mutation, state,
locks, prepared inputs, owner comment, and the double provider observation are
rechecked under an exclusive `flock`. Immediately before the first local
mutation, a third read-only provider observation is collected and compared
with the owner-bound observation hash. The current bytes of all three journals are likewise checked against the owner-bound lock hashes; recovery accepts only the `RELEASED` hash deterministically derived from the original `HELD` journal.

The only permitted terminalization finishes step 2 as `FAILED` with
`EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE`, sets the run to
`FAILED_PARTIAL`, persists terminal evidence, writes
`MIDRUN_RELEASE_IN_PROGRESS`, and append-only adds `RELEASED` to all three
lock journals. There is no resume, provider write, automatic retry, rollback,
delete, or retroactive success classification. A torn release may be
continued idempotently only with the same immutable #719 binding. A partial
journal append is recoverable only when it is a strict byte prefix of the
deterministically expected `RELEASED` record. After runtime, state, path, and
descriptor revalidation, only that tail is truncated to the owner-bound
initial state; unknown tails block fail-closed.

## Acceptance Criteria

- **AC-719-01:** `RESOURCE_GROUP_ONLY` remains unchanged and fail-closed,
  limited to the empty legacy #717 inventory and the #717 terminalization
  binding.
- **AC-719-02:** `BICEP_BASELINE_EXACT` is classified only from the commit-,
  tree-, and activation-bound prepared manifest, template and parameter
  snapshots, and the canonical baseline expectation.
- **AC-719-03:** Only exactly seven expected top-level resources and twelve
  successful ARM deployment operations are accepted; partial inventory,
  additional resources, and ID, type, region, tag, identity, deployment, or
  snapshot drift block with stable error codes.
- **AC-719-04:** Inspection performs two identical read-only provider
  observations without local mutation and generates a canonical #719 owner
  comment containing all baseline hashes.
- **AC-719-05:** The separate owner decision permits only
  `TERMINALIZE_AND_RELEASE_LOCK_ONLY` into terminal state `FAILED_PARTIAL`;
  resume, Azure or tenant writes, retry, rollback, delete, and `PASSED` remain
  forbidden.
- **AC-719-06:** Focused tests, the contract validator, spec traceability,
  language, link, and strict gates, independent review, and remote CI pass.
