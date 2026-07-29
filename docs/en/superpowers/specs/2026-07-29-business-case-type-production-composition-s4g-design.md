# BusinessCaseType Production Edge Composition S4g

Delivery status: `IMPLEMENTED_OFFLINE_PENDING_PROTECTED_PR`

Status: `S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE`
Live status: `BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`
Date: 29 July 2026
Scope: production-shaped offline composition without live action

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-production-composition-s4g
leading_issue: https://github.com/notariat8/NaC/issues/708
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-29-business-case-type-production-composition-s4g.md
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4G-01
  - AC-S4G-02
  - AC-S4G-03
  - AC-S4G-04
  - AC-S4G-05
  - AC-S4G-06
  - AC-S4G-07
  - AC-S4G-08
validation_commands:
  - python3 -m unittest tests.test_business_case_type_production_composition tests.test_business_case_type_write_identity_inspection tests.test_azure_blob_worm_rest_transport tests.test_business_case_type_production_composition_cli tests.test_business_case_type_production_composition_contract
  - python3 scripts/validate_business_case_type_production_composition.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - git diff --check
  - python3 -m compileall -q src scripts tests
  - python3 scripts/quality_gate.py --profile strict
```

## Goal

S4g binds the existing offline S4d, S4f, and S6b boundaries into a
production-shaped composition envelope. It verifies the form of a future
production edge but does not construct a runtime factory, read writer
credentials, or authorize a provider or tenant write.

The only positive completion status is
`S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE`. Independently, the live
status remains
`BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`.

## Bound Composition

The composition envelope binds workspace `notary_team_01`, the actual S4d,
S4f, and S6b contract files, and domain-separated repository implementation
hashes for the identity inspector, owner verifier, writer token factory, Graph
transport, and Azure WORM REST transport. The WORM target remains explicitly
offline-unconfigured. The offline assessment returns no hashes,
principal IDs, paths, tokens, URLs, or provider bodies.

## Identity Inspector

`BusinessCaseTypeWriteIdentityInspectionAdapter` validates only a read-only
snapshot from the exact in-memory `SnapshotIdentityInspectionPort`; every other
injected port is rejected before `readback()`. Implementation and snapshot
attestation hashes are bound separately. Provisioner, writer, and BFF
carry separate `app_id` and `service_principal_object_id` fields. Each set must
be independently pairwise distinct, and the complete namespaces must be
globally disjoint. No application ID may equal any service-principal object
ID; each principal pair is bound independently by SHA-256.

The writer has exactly the `Sites.Selected` Graph application role and exactly
`write` at the bound site. The BFF has exactly `Sites.Selected` and exactly
`read`. Both the business-case writer and token source must be the writer
identity. The provisioner cannot take either role. The inspector changes
neither Entra nor site grants.

## Separate SQLite Paths

Mutation state uses `mutation-state.sqlite3`; local evidence staging uses
`evidence-staging.sqlite3`. They must be separate absolute canonical paths
under the same trusted local single-host root. The root requires exact mode
`0700`. Databases that do not yet exist are allowed for precreation assessment;
existing databases must be regular files owned by the current user with exact
mode `0600`, `st_nlink == 1`, and distinct device/inode identities.

The assessment returns `BLOCKED` for the same file or role, symlinks, synced
directories, remote or unknown filesystems, and weaker modes. Both SQLite
stores are local staging boundaries, are not central truth, and cannot close a
mutation.

## Azure WORM REST Transport

`AzureBlobWormRestTransport` implements the existing
`AzureBlobWormTransport` through injected management and Blob token ports and
an injected HTTP port. It binds HTTPS, `management.azure.com`, the owner-bound
Blob host, management API `2023-05-01`, subscription API `2022-12-01`, and
Blob API `2023-11-03`.

Only `GET` and `PUT` are allowed. Redirects, automatic retries, foreign hosts,
and requests or responses over 4 MiB are rejected. Create is create-only with
`If-None-Match: *`, status `201` or conflict `412`, and bound
`x-ms-version-id` readback. Provider context, Locked policy, and the exact Blob
version must be read and verified. The transport exposes neither `DELETE` nor
a management- or data-plane operation that sets or locks the immutability
policy.

The production shape of the port is verified only with injected local fakes.
This performs zero socket/DNS, credential-store, Graph, Azure, or tenant
activity.

## Remaining Blockers

Each of these remains an independent mandatory blocker:

- central PostgreSQL promotion with acknowledgement, retention, and local cleanup
- broker product decision and implementation
- owner decision and implementation for the signature/anchor
- durable reconciliation store
- irreversible Azure WORM policy lock
- owner-gated live activation

Without evidence for all six, runtime-factory construction is blocked before
writer credentials are read. Local SQLite persistence or a successful Azure
REST fake replaces neither central acknowledgement nor the WORM lock.

## Acceptance Criteria

- **AC-S4G-01:** The production-shaped composition is verified offline with
  exactly zero socket, DNS, credential-store, Graph, Azure, or tenant activity.
- **AC-S4G-02:** Provisioner, writer, and BFF are pairwise distinct and
  hash-bound both by their three `app_id` values and independently by their
  three `service_principal_object_id` values.
- **AC-S4G-03:** Writer remains exactly `Sites.Selected/write`, BFF exactly
  `Sites.Selected/read`, and only writer may be the business-case writer and
  token source.
- **AC-S4G-04:** Mutation state and evidence staging use separate trusted
  SQLite paths; identical, weakly protected, synced, remote, unknown, or
  symlink-based paths fail closed.
- **AC-S4G-05:** The Azure WORM REST transport is bound to hosts, API versions,
  methods, headers, sizes, idempotency, and exact readback and can never lock
  the policy.
- **AC-S4G-06:** Missing PostgreSQL acknowledgement, broker decision, signature
  anchor decision, or durable reconciliation blocks runtime construction
  before credential reads.
- **AC-S4G-07:** Status and evidence report only
  `S4G_PRODUCTION_EDGE_COMPOSITION_VERIFIED_OFFLINE` and
  `BLOCKED_PENDING_CENTRAL_EVIDENCE_AND_OWNER_GATED_ACTIVATION`; they claim no
  production readiness, production durability, or live authorization.
- **AC-S4G-08:** Focused tests, validators, contracts, the strict gate, and
  independent review pass.
