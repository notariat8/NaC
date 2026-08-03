# Implementation Plan: Conservative BFF Measurement Adapters

Issue: [#733](https://github.com/notariat8/NaC/issues/733)  
Spec: [Conservative BFF Measurement](../specs/2026-08-03-bff-conservative-measurement-adapters-design.md)  
Contract: [m365-bff-performance-acceptance.contract.json](../../../../workflows/contracts/m365-bff-performance-acceptance.contract.json)  
Status: offline implementation; live execution and provisioning blocked.

The planning boundary carries four separate statements: `tenant_wide_sharepoint_baseline_claim: NOT_CLAIMED`, `tenant_wide_sharepoint_request_allowance_claim: NOT_CLAIMED`, `tenant_wide_sharepoint_resource_unit_allowance_claim: NOT_CLAIMED`, and `monetary_cost_claim: NOT_CLAIMED`.

1. Replace tenant-wide SharePoint capacity logic completely with an immutable endpoint-bound policy and `NOT_CLAIMED` (`AC-733-01`).
2. Fix allocations to `1 + 1 + 90 + 120 + 288 = 500`, concurrency one and at most six dispatches per minute (`AC-733-02`).
3. Implement a read-only Monitor adapter with fixed resource ID, API, metrics, dimensionless app-wide rollup, aggregation, settlement and window allowlists (`AC-733-03`).
4. Implement a Blob REST lease adapter for a precreated ETag-bound blob with acquire, assert and release only (`AC-733-04`).
5. Test acquire/release crash points, same-ID resume and `PASSED` only after an exact `RELEASED` receipt bound to `target_binding_sha256` and the lease binding (`AC-733-06`).
6. Bind measurement, monitor, lease and one-shot blob-bootstrap policies, runner identity, RBAC/ABAC, infrastructure plan and parameters, commit, tree, and toolchain into exactly one combined owner gate; prove the ETag and concrete lease binding by readback (`AC-733-05`, `AC-733-08`).
7. Bind a final settled Monitor window whose `monitor_window_end_utc` covers `measurement_finished_at_utc` and whose observation follows settlement; persist `projected_remaining_execution_units_gb_seconds` for every safety observation and require it to be exactly zero in successful terminal measurement evidence (`AC-733-03`, `AC-733-07`).
8. Make every terminal outcome use a durable `pending-finalization` record, same-ID release reconciliation, exact release proof, and a last-written `completion-manifest` for crash-safe JSON/Markdown persistence.
9. Add CLI/composition negative tests proving offline mode instantiates no adapters, the exact Monitor URL is the only read command, TOCTOU remeasurement occurs immediately before each subprocess, and all gates precede provider/BFF access.
10. Synchronize contract, contract index, verification contract, validator, DE/EN documentation and CLI.
11. Run unit, command-boundary, composition, crash and RBAC-negative tests, strict gate and independent reviews; fix findings and deliver the protected PR (`AC-733-07`).
12. Before provisioning, bind the existing BFF/WORM `resource-id` values authoritatively and prove Azure name availability; after deployment, prove complete effective RBAC/ABAC inheritance including tenant root, management groups, and transitive Entra groups as `SAFE` evidence. Reproduce the ARM/parameter artifacts byte-for-byte in CI with Bicep `0.45.15.27210`.
13. After a green merge, generate exactly one hash-bound approval for provisioning, read-only readback and full live acceptance.

No plan step creates Azure resources or executes a live test.
