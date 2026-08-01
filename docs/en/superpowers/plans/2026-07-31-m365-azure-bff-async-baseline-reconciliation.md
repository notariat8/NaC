# Implementation Plan For Asynchronous Azure BFF Baseline Reconciliation

Leading issue: [#719](https://github.com/notariat8/NaC/issues/719)
Spec: [M365 Azure BFF reconciliation of an asynchronously completed baseline](../specs/2026-07-31-m365-azure-bff-async-baseline-reconciliation-design.md)
Acceptance: `AC-719-01` through `AC-719-06`

1. Bind Issue #719, DE/EN specs, DE/EN plans, CLI documentation, and
   `AC-719-01` through `AC-719-06`.
2. Preserve the existing `RESOURCE_GROUP_ONLY` path unchanged as the
   fail-closed legacy #717 classification for an exactly empty resource
   inventory.
3. Securely read the prepared manifest, Bicep/ARM template, and parameter
   snapshot and cross-check their activation, commit, tree, and byte hashes;
   inspect the approved Git tree directly and verify its tree manifest and
   Bicep blob against the prepared bytes, disable replace refs, and verify
   every archived blob against its Git blob ID; derive the canonical baseline
   expectation and its SHA-256.
4. Permit `BICEP_BASELINE_EXACT` only for exactly seven expected top-level
   resources with complete ID, type, kind, SKU, name, region, tag, Smart
   Detection, output, and managed identity bindings.
5. Verify deployment name, `Succeeded`, `Incremental`, template and parameter
   hashes, and exactly twelve successful ARM deployment operations with the
   expected type distribution and exact target ARM IDs; read all twelve
   target resources and verify their Bicep properties as exact objects; use an
   exactly bound Azure Resource Graph POST to compare the complete resource and
   authorization-resource set in the target scope with inventory plus deployment
   targets.
6. Reject partial inventory, additional resources, invalid prepared inputs,
   and any resource, identity, deployment, operation, or snapshot drift with
   stable fail-closed error codes.
7. Collect each complete provider snapshot read-only twice, read the inventory
   twice within each snapshot as well, and accept only byte-identical
   canonical observations.
8. Limit inspection, without local mutation or Azure or tenant writes, to
   `MIDRUN_RECONCILIATION_REQUIRED`, redacted hashes, and the canonical #719
   owner comment.
9. Bind #719 terminalization to `BICEP_BASELINE_EXACT`,
   `baseline_expectation_sha256`, `prepared_inputs_manifest_sha256`,
   `bicep_snapshot_sha256`, and `bicep_parameters_snapshot_sha256`, as well
   as all existing state, ledger, lock, provider, and reconciler hashes.
10. Permit only `TERMINALIZE_AND_RELEASE_LOCK_ONLY`, finish step 2 with
    `EXTERNAL_PROCESS_INTERRUPTED_AFTER_WRITE`, set the run to
    `FAILED_PARTIAL`, and release all three lock journals append-only.
11. Explicitly exclude resume, provider writes, retry, rollback, delete, and
    retroactive `PASSED`; continue torn local terminalization only with the
    identical immutable #719 binding; immediately before the first local
   mutation, read the complete provider observation again and compare it with
   the owner-bound hash; verify all three current journal byte sequences before
   every mutation and during recovery against original or deterministically
   derived release hashes; repair partial journal appends only when they are a
   strict prefix of the expected release record and only after complete runtime,
   state, path, and descriptor revalidation; additionally bind commit, tree, and
   runtime files to the approved Git blob digests with replace refs disabled.
12. Run focused tests, the contract validator, spec traceability, language,
    link, and strict gates, independently review the complete `base...head`
    diff, resolve P1/P2 findings, and deliver through a protected PR.
