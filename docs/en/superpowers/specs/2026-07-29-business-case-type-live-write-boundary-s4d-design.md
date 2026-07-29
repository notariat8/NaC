# BusinessCaseType Live Write Boundary S4d

Status: `S4D_DESIGN_READY_OFFLINE`
Date: 29 July 2026
Scope: owner-gated production boundary without live tenant execution

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-live-write-boundary-s4d
leading_issue: https://github.com/notariat8/NaC/issues/700
risk_gate: Human Approval
delivery_mode: Protected PR
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4D-01
  - AC-S4D-02
  - AC-S4D-03
  - AC-S4D-04
  - AC-S4D-05
  - AC-S4D-06
  - AC-S4D-07
  - AC-S4D-08
validation_commands:
  - python3 -m unittest tests.test_business_case_type_live_write_boundary tests.test_business_case_type_live_write_boundary_contract tests.test_business_case_type_live_write_boundary_cli
  - python3 scripts/validate_business_case_type_live_write_boundary.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Goal

S4d composes the existing S4c write edge with a separate owner-gated write
identity, canonical S6 evidence and the S6b WORM port. The BFF remains strictly
read-only. The offline slice provides no live factory and performs no Entra,
credential, Azure or tenant change.

The completion status is `S4D_READY_OFFLINE`. `READY_FOR_LIVE` is allowed only
after production identity, outbox, broker, signature, WORM and reconciliation
adapters have been proven by a later bound owner gate.

## Bindings

An immutable `LiveWriteApprovalAttestation` binds at least:

- Git commit and tree,
- S4d domain and verification contracts,
- plan, toolchain and step sequence,
- evidence policy plus tenant, workspace, site, matter/task list and Graph
  v1.0 target boundary,
- write principal and separate BFF read principal.

All static bindings are validated before credential or transport access. An
injected `WriteIdentityInspectionPort` then uses a separate owner-bound
read-only inspection credential and transport boundary to freshly verify:

- write identity: exactly `Sites.Selected` and site role `write`,
- BFF UAMI: exactly `Sites.Selected` and site role `read`,
- distinct principals on the same bound target site,
- no broader Graph roles.

Only after that readback may the injected `WriteIdentityFactoryPort` supply
the business-write token provider. Static drift causes zero credential access;
inspection credentials are used only for the authenticated current-state
readback. The broadly privileged provisioning app is not reused as the
business-data write identity.

The owner attestation uses a cycle-free `plan_binding_sha256`: the complete
canonical plan is bound with a normalized approval reference. The execution
process rebuilds the plan from the approved envelope, injects the typed
`owner-approval-v1-<sha256>` reference and exactly revalidates both
`plan_binding_sha256` and the final `plan_sha256`.

## Evidence And Crash Semantics

`S4dMutationEvidenceHook` implements the existing S4b
`MutationEvidenceHook`. It delegates local generation-CAS state to S4c and
maintains a canonical S6 chain for the exact operations `case_create`,
`case_status_update`, `task_create`, `task_update` and
`business_case_type_backfill`.

The fail-closed sequence is:

1. static owner, hash, target and principal gate,
2. fresh identity and permission readback,
3. dedupe or ETag preflight,
4. local SQLite intent with generation CAS,
5. canonical S6 intent and verified outbox readback,
6. exactly one Graph write attempt,
7. local and canonical outcome,
8. exact Graph readback and canonical readback,
9. broker acknowledgements, signature anchor with readback, Azure WORM commit
   with independent version readback and persisted `complete_publication`,
10. local closure only after a fully validated publisher result with exact
    event and acknowledgement counts plus anchor, signature and WORM binding.

A failure before step 6 causes zero write attempts. If step 5 fails after the
local intent, sticky `reconciliation_required` is already persisted. Every
failure from step 6 also leaves intent and reconciliation sticky and open.
Automatic mutation replay is forbidden; only later dual-control reconciliation
may continue evidence publication or closure.

S4c SQLite and the future central evidence outbox are two persistence systems,
so S4d does not claim an atomic distributed transaction. The ordering instead
ensures every crash window either ends before mutation or leaves an open state
that blocks replay.

## Privacy

Outputs and persisted technical metadata use recursive allowlists. Allowed
values are statuses, stable reason codes, operations, counters, booleans and
SHA-256 references. Raw tenant, site, list, app, principal, matter, task or item
IDs, URLs, mutation fields, ETags, HTTP headers, tokens, certificates, keys,
file paths, provider attestation contents and exception text are forbidden.

## Acceptance Criteria

- **AC-S4D-01:** Local SQLite replay safety and S6/S6b publication are
  composed; local closure occurs only after verified WORM readback.
- **AC-S4D-02:** Write and BFF identities remain separate and exactly limited
  to `Sites.Selected/write` and `Sites.Selected/read`.
- **AC-S4D-03:** Static drift blocks before credentials; fresh provider
  readback blocks before mutation.
- **AC-S4D-04:** Crash and failure injection prove sticky reconciliation and
  zero automatic mutation replay.
- **AC-S4D-05:** Results, failures and evidence contain only the defined
  redaction allowlist.
- **AC-S4D-06:** A synthetic offline one-shot smoke covers all five operations
  with zero external credential, socket, DNS, Graph, Azure and tenant activity.
- **AC-S4D-07:** A canonical owner comment binds commit, contracts, plan,
  target, principals, toolchain, step sequence and evidence policy.
- **AC-S4D-08:** Domain and verification contracts, validator, tests,
  documentation, strict gate and CI pass; the slice remains `READY_OFFLINE`.

## Out Of Scope

- Entra app, permission, site grant, credential or certificate changes,
- production adapters or live factory,
- live Graph, Azure, SharePoint or Teams actions,
- production data or other workspaces,
- automatic retries, rollbacks, deletions or reconciliation.

## Independent-review safety rework

`LiveWriteApprovalAttestation` is an unverified candidate only. It is not
self-authorizing. Before identity readback, a separate
`OwnerApprovalVerifierPort` must verify the immutable owner comment, issue
#700, owner allowlist, and verifier principal. S4d includes only a synthetic
offline adapter; a production GitHub readback adapter and live factory remain
explicitly absent.

Final plan revalidation runs before owner verification, identity inspection,
credential construction, and transport. Identity inspection additionally
carries its source, second-precision observation time, inspection-principal
binding, and owner-approval digest. The current offline contract accepts only
`synthetic-offline-owner-bound-readback` and makes no production Entra or Graph
readback claim.

S6 v0.2 binds every chain to mutation, execution key, operation, target, final
plan, authorization run, and optional S5 operation hash. A verified readback
also requires the SHA-256 digest of the canonical provider state. An existing
phase is reused only when its reconstructed event is byte-identical; a foreign
or stale chain makes the local intent sticky `reconciliation_required` and
cannot close it.

