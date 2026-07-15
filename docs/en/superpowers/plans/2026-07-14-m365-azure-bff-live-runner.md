# M365 Azure BFF Live Runner Implementation Plan

**Date:** 14 July 2026
**Activation Issue:** [#632](https://github.com/notariat8/NaC/issues/632)
**Parent Context:** [#620](https://github.com/notariat8/NaC/issues/620)
**AC IDs:** `AC-632-01` through `AC-632-08`
**Delivery Mode:** Protected PR
**Status:** `OFFLINE_READY`; neither the live runner nor live activation has been proven `PASSED`

## Goal

The live runner executes the existing hash-bound
[offline activation plan](../../../../workflows/contracts/m365-azure-bff-activation-plan.contract.json)
in exactly twelve steps. The
[live runner contract](../../../../workflows/contracts/m365-azure-bff-live-activation.contract.json)
and the
[verification contract](../../../../workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml)
bind approval, commit, tree, targets, permissions, toolchain attestations, the
target-global lock, ledger, host-wide success receipt, and redacted evidence.
Resume is explicitly disabled for the MVP until
provider-specific read-only reconciliation is implemented and independently
verified for every provider write and crash window. Offline readiness or this
plan is not live approval or proof of success.

## Traceability

- `AC-632-01`: Exact owner login `ofunk` and immutable approval snapshot from Issue #632; Issue #620 remains parent context.
- `AC-632-02`: Complete read-only duplicate and broader-permission inventory before the first provider write.
- `AC-632-03`: One host-wide target-global lock blocks concurrent runs from all worktrees and clones on the single execution host regardless of output path, activation hash, or correlation ID; cross-host coordination is not provided.
- `AC-632-04`: The Function package, site-scoped SPFx package, and Bicep snapshot are built and hash-bound before the final Git/plan gate; the parameter snapshot resolved against the created or reused Entra app ID and the full manifest are atomically bound after exact step-3 readback and before the Bicep write.
- `AC-632-05`: Entra, UAMI, `Sites.Selected`, site `read`, site-scoped SPFx, and `Matter.Read` are created or exactly reused and read back.
- `AC-632-06`: `healthz` runs before auth and `readyz` only after an authenticated read; denied/manipulated cases fail closed and PASSED requires verified restoration of the synthetic baseline. A process termination before that proof remains non-success and requires read-only reconciliation plus manual recovery; SIGKILL restoration is not claimed.
- `AC-632-07`: Ledger and evidence are hash-chained, redacted, and constrained by exact field allowlists.
- `AC-632-08`: The first partial failure stops the run; resume remains disabled for the MVP.

## Exact Binding

| Target | Exact value |
|---|---|
| Activation hash | Exact 64-character lowercase SHA-256 from the offline plan for the final clean approved commit; required owner-gate value |
| Toolchain attestations hash | Exact 64-character lowercase SHA-256 over the eight non-secret execution digests for the Azure CLI toolchain, full M365 runtime tree, M365 Node, build Python, build Node, full build-npm runtime tree, the fixed GitHub CLI, and the public provisioning certificate; required value of the same owner gate |
| Tenant | `870c862b-56f7-4c9b-b0d9-f1f7d32c835c` |
| Subscription | `37cd9645-6cb9-4278-88ee-e80377cd951c` |
| Workspace | `notary_team_01` |
| Site | `https://funktion8.sharepoint.com/sites/NaC-Notar-01` |
| Site ID | `funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,56fc9349-e123-4252-ae2a-05d5d61c9b38` |
| Team | `NaC-Notar-01` / `124f1b11-207d-4307-bfd1-ac0fd73aa90a` |
| CLI test client | `c86dded6-9723-4b8d-91f2-e0fd70e25839`, delegated allow/deny live verification only |
| Lists | `Akten=588d4a41-f538-4f37-acfb-63ff283e0910`, `AufgabenFristen=720ef1d4-8496-4ecb-aa1f-5fa4568343f2`, `Vertretungsfreigaben=ec12d339-d9b7-45e9-be45-38dadd917746`, `AuditJournalLite=327181c2-e402-48e9-bcfa-1f5081b45d9c` |
| App Catalog | Tenant catalog on `funktion8.sharepoint.com`, exactly one solution with `ProductId=b7a5417c-0dd3-4e69-87c7-95adfd7e8a58`; the record ID is uniquely resolved and checked read-only |
| SPFx solution | `nac-bpmn-viewer-client-side-solution`, version `0.2.0.0`, site-scoped, `skipFeatureDeployment=false` |
| Page | `NaC-Testumgebung.aspx`, title `NaC-Testumgebung`, layout `Article` |
| Webpart | `NacBpmnViewerWebPart` / `3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21` |
| Synthetic matter | `NAC-SYN-MATTER-001`, type `immobilienkaufvertrag`, purpose `view_synthetic_matter_workspace` |

The App Catalog record ID is neither invented nor stored permanently in the
repository. Unique `ProductId` resolution, UUID validation, and readback bind
the one permitted catalog record. Zero matches allow creation; more than one
match stops the run.

## One Consolidated Owner Gate

The runner accepts exactly one owner approval. An immutably bound comment by
exact GitHub login `ofunk` in Issue #632 must contain exactly these fields:

```json
{
  "owner-approved": true,
  "expected_activation_sha256": "<64 lowercase hex from the final clean approved commit>",
  "approved_commit_sha": "<40 lowercase hex>",
  "approved_tree_sha": "<40 lowercase hex>",
  "toolchain_attestations_sha256": "<64 lowercase hex>",
  "target_binding_sha256": "<64 lowercase hex>",
  "permission_boundary_sha256": "<64 lowercase hex>",
  "step_sequence_sha256": "<64 lowercase hex>",
  "no_automatic_rollback_or_deletion": true
}
```

The runner binds the URL, comment database ID, author, creation time, and body
SHA-256. `updatedAt` must equal `createdAt`. Approval cannot be reused for a
different hash, commit, tree, target state, permission scope, or toolchain.
There are no additional implicit or per-step approvals.

The runner receives the eight individual digests through separate required CLI
arguments, computes the combined hash, and compares it with the single
toolchain field in the approval payload.

`toolchain_attestations_sha256` is the lowercase SHA-256 of a UTF-8 canonical
JSON object containing exactly `azure_cli_toolchain_sha256`,
`m365_cli_sha256`, `m365_node_sha256`, `build_python_sha256`, `build_node_sha256`, and
`build_npm_cli_sha256`, `gh_cli_sha256`, and `provisioner_certificate_sha256`. The last value binds only the public certificate; private-key content and its digest remain excluded. Every input is a non-secret 64-character lowercase
SHA-256; keys are sorted, compact separators are used, and exactly one trailing
newline is included. Any changed input or combined hash requires a new consolidated owner
approval. Final evidence and the host-wide success receipt must contain the
same combined hash or `PASSED` is blocked.

Immediately before every local Python or Node process, executable bytes are
copied from one `O_NOFOLLOW`/`fstat`/SHA-256-verified read into sealed Linux
`memfd` files. `m365_cli_sha256` and `build_npm_cli_sha256` bind
deterministic full-tree manifests of their runtime modules rather than only
entry scripts; only npm-generated `node_modules/.bin` command shims are
excluded, and they cannot be loaded as modules. Sealed CommonJS/ESM loaders
reject unknown, changed, symlinked, or native modules and compile or evaluate
only the exact bytes reverified with `O_NOFOLLOW`, `fstat`, and SHA-256 for
every module load.
The activation hash is generated only after the final commit exists because
the offline plan binds the commit and live runner artifacts themselves; a
result hash hard-coded in that same commit would be circular and is forbidden.

## Pre-Write Gate

Before the first write, checks run in this order:

1. Validate the approval snapshot, Azure/M365 sessions, and all exact target values read-only.
2. Run a complete read-only inventory of Entra application/service-principal, UAMI role, site-grant, App Catalog, SPFx permission/install, page/webpart, and synthetic-key matches; exclude duplicates and broader permissions before any possible write.
3. Acquire the target-global nonblocking lock for tenant, subscription, and workspace regardless of output path, activation hash, or correlation ID.
4. Initialize only a new ledger; existing or partial runs cannot continue in the MVP.
5. Prebuild the Function OneDeploy package, site-scoped `.sppkg`, immutable Bicep snapshot, and resolved Bicep parameter snapshot, then hash-bind them to the commit, tree, and activation hash.
6. Require empty output from `git status --porcelain=v1 --untracked-files=all`.
7. Compare `HEAD` and `HEAD^{tree}` with the approved commit and tree.
8. Rebuild the offline plan and verify `READY` plus the expected activation hash.
9. Compute the hash a second and final time immediately before the first write.
10. Atomically write and fsync `PRE_WRITE_BINDING`, check Git status again, and invoke the first allowlisted write without any intervening repository or plan mutation.

Any mismatch stops with zero writes. Tracked changes, untracked files,
submodule drift, wrong targets, hash drift, or a held lock are not repaired
automatically.

## Execution and Permissions

The twelve steps remain in the offline plan order:

1. register three Azure providers,
2. create or reuse the exact resource group,
3. create or reuse exactly one single-tenant Entra API with `Matter.Read` and token version 2,
4. deploy the hash-bound Bicep baseline with the readback-verified API `appId`,
5. assign only `Sites.Selected` to the UAMI,
6. grant only `read` on the exact site,
7. deploy the prebuilt hash-bound Function package bytes through Flex OneDeploy with `--build-remote true`,
8. deploy the prebuilt hash-bound site-scoped `.sppkg` bytes without a live rebuild,
9. approve only `NaC M365 BFF/Matter.Read` for SPFx,
10. create or exactly reuse only the canonical synthetic matter and its records,
11. check `healthz` before auth, execute authenticated allow/deny/manipulated-input readbacks, deterministically restore the captured assigned synthetic baseline, read again with authentication, and only then check `readyz`,
12. finalize read-only convergence, duplicate absence, causal deployment-input binding, ledger, and evidence; replaying provider writes is not claimed.

Microsoft Graph access uses raw REST requests only against
`https://graph.microsoft.com/v1.0`. Graph beta, SDKs, PnP, and legacy
SharePoint APIs remain blocked. Azure Resource Manager and the already
documented M365 CLI control-plane edge run only through argv allowlists with
no shell. The UAMI may have exactly `Sites.Selected`, the site grant exactly
`read`, and SPFx exactly the delegated BFF scope `Matter.Read`.

## Ledger, Failure, and Disabled Resume

The only run states are `OFFLINE_READY`, `LIVE_APPROVED`, `FAILED_PARTIAL`,
and `PASSED`. Every step writes append-only, hash-chained, atomically renamed,
and fsynced redacted events. A provider write and local ledger are not falsely
claimed to be a distributed transaction. A crash window remains
`FAILED_PARTIAL`; the MVP neither reconciles nor continues it automatically.

The first error stops every later step. After at least one write, the state is
`FAILED_PARTIAL`. There is no automatic rollback, deletion, uninstall,
retraction, permission downgrade, or leftover cleanup. Restoring the bounded
temporarily changed synthetic test state is part of step 11 and is not provider
rollback. `--resume` is not exposed. Every resume request stops before lock,
provider read, and provider write with `RESUME_DISABLED_FOR_MVP`. Later
enablement requires provider-specific read-only reconciliation for every write
step and crash window plus independent verification. Ambiguous provider state
remains `FAILED_PARTIAL` and requires a new human decision.

## Evidence and Negative Tests

The local hash chain and success receipt detect accidental or concurrent mutation but are not cryptographically authentic against the same controlled OS user. This synthetic MVP therefore makes no formal immutable or evidentiary audit claim; that requires a separately approved external immutable store or signature lane.

Final evidence follows a strict field allowlist. It contains only status,
timestamps, hash bindings including `toolchain_attestations_sha256`, stable
error codes, HTTP status, and hashed request,
response, and resource references. Raw IDs, URLs, Graph paths, commands,
provider responses, stdout/stderr, headers, tokens, cookies, credentials,
certificates, environment values, and people, matter, document, or production
data are forbidden. Unknown fields invalidate the artifact.

The `summary` object also has an exact allowlist: `required_step_count`,
`passed_step_count`, `failed_step_count`, `duplicate_count`,
`broader_permission_count`, `automatic_rollback_count`,
`automatic_deletion_count`, `writes_started`, `ledger_hash_chain_valid`,
`prebuilt_inputs_verified`, `healthz_before_auth_passed`,
`authenticated_read_passed`, `readyz_after_authenticated_read_passed`,
`synthetic_state_restored`, and `resume_enabled`. For `PASSED`, all probe and
restoration fields must be `true` and `resume_enabled` must be `false`.

Required negative tests cover a wrong hash, dirty tree, wrong target,
duplicates, broader permissions, two racing runners, secret-sentinel leaks,
failure after the first write, invalid probe order, failed synthetic
restoration, and every resume request. Every pre-write
case proves zero writes; every partial case proves stop-on-first-error and zero
automatic rollbacks and deletions.

## Implementation Order

1. Implement CLI arguments, exact owner login `ofunk`, approval snapshot validation, and the commit/tree/hash gate.
2. Implement the target-global lock and atomic hash-chained ledger.
3. Strictly allowlist and redact Azure, Entra, Graph REST v1.0, and M365 CLI adapters.
4. Implement the complete prewrite inventory, prebuilt hash-bound packages/Bicep snapshots, and twelve steps with unique read-before-write classification and readback.
5. Implement healthz-before-auth, authenticated read, readyz-after-read, and deterministic synthetic-state restoration; keep MVP resume fail-closed and disabled.
6. Implement the evidence allowlist and every negative test.
7. Run focused tests, contract verification, spec traceability, language parity, link validation, the strict gate, and Protected PR checks.

`PASSED` may be emitted only after all twelve steps pass for the bound targets,
permissions are exact, no duplicates exist, ledger and evidence are valid, and
no automatic rollback or delete occurred.
