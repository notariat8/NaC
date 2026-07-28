# BusinessCaseType Immutable Evidence S6a Design

Status: `S6_OFFLINE_FOUNDATION`; live execution remains `BLOCKED_PENDING_S7_APPROVAL`
Date: 20 July 2026
Scope: canonical, redacted and entirely synthetic offline foundation for mutation evidence

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-immutable-evidence-s6
leading_issue: https://github.com/notariat8/NaC/issues/687
risk_gate: Privacy
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S6-01
  - AC-S6-02
  - AC-S6-03
  - AC-S6-04
  - AC-S6-05
  - AC-S6-06
  - AC-S6-07
  - AC-S6-08
validation_commands:
  - python3 -m unittest tests.test_immutable_evidence tests.test_business_case_type_immutable_evidence tests.test_business_case_type_immutable_evidence_cli tests.test_business_case_type_immutable_evidence_contract
  - python3 scripts/validate_business_case_type_immutable_evidence.py
  - python3 scripts/nac.py kg business-case-type-evidence-dry-run --format json
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Purpose And Boundary

S6a defines the evidence core for later schema, backfill, correction, cutover
and rollback mutations. Local synthetic in-memory adapters alone verify
ordering, hash chaining, identity bindings, restart-safe publication and
reconciliation. It performs no mutation, network, provider, tenant or
credential access and introduces no live functions.

The result is only `S6_OFFLINE_FOUNDATION`. It is neither production approval
nor proof of WORM, signatures, anchors, retention, persistence or audit-proof
operation. Every live step remains `BLOCKED_PENDING_S7_APPROVAL`;
`AuditJournalLite` remains an operational projection.

## Canonical Evidence Envelope

An event uses `nac.immutable-evidence-event/v0.1`. Its base fields include
`correlation_id`, `actor_ref`, `actor_principal_ref`,
`tenant_binding_sha256`, `principal_key_binding_sha256`, tool, role, action,
the S3 catalog binding, manifest, retention, privacy and ETags. The
operation-wide `idempotency_key_sha256` stays stable across the chain. The
event-specific `delivery_key_sha256` binds the complete canonical event except
for `event_id` and `delivery_key_sha256` itself and cannot be reused.

`reconciliation_closed` persists `result_code`, operator and approver
ActorRefs, `operator_principal_ref`, `operator_tenant_binding_sha256`,
`operator_principal_key_binding_sha256`, `approver_principal_ref`,
`approver_tenant_binding_sha256` and
`approver_principal_key_binding_sha256`.

ASCII JSON with sorted keys, compact separators, no NaN and no floating-point
values is the only canonical serialization. SHA-256 over exactly those bytes
forms the event hash. Sequences start at one, are contiguous and bind exactly
the predecessor through `previous_event_sha256`. Correlation, actor, both
security bindings, domain binding, idempotency, retention and privacy are
immutable within a chain.

Tool and role come from fixed runtime registries. Business-case type and
catalog version come exactly from `BusinessCaseTypeCatalog.from_repo`: 20
canonical S3 slugs and only the SHA-256 `CatalogVersion`
`fcf1c7ba1a35980f5f1d371381ae5c218cd3ce94372f2c1df821f2ad40d2fab0`.
ETags are stored only as
`hmac-sha256:k<positive_integer>:<64_lowercase_hex>`. The HMAC uses
`nac.etag-evidence.v1\u0000`, a separate key of at least 32 bytes, a positive
key version and tenant binding
`SHA-256(nac.tenant-binding.v1\u0000,tenant_id)`.

## Intent, Outcome And Readback

The normal path is exactly `intent -> outcome -> readback`. Persisted intent
must precede a mutation. Outcome records only the write attempt; readback is a
separate observation. Missing or uncertain outcome, missing readback or
missing downstream evidence blocks completion and blind retry fail closed.
After `write-state-uncertain`, `reconciliation_required` must occur first.

## Actor, Correlation And Principal Binding

`ActorRef` is a tenant- and key-version-bound HMAC-SHA256 value formatted as
`actor-v1-k<version>-<64hex>`. The separate stable principal reference is
`HMAC-SHA256(principal_key, nac.principal-ref.v1\u0000 || tenant_id || actor_object_id)`
and is persisted as `principal-v1-<64hex>`.

Two non-reversible security bindings are also persisted:

- `tenant_binding_sha256 = SHA-256(nac.tenant-binding.v1\u0000 || tenant_id)`,
- `principal_key_binding_sha256 = SHA-256(nac.principal-key-binding.v1\u0000 || principal_key)`.

Correlation and actor must have the same tenant binding. Actor, operator and
approver must use the same tenant and the same principal-key binding hash.
Different tenants or principal keys fail closed during event creation,
closure, claim and retry authorization. Operator and approver must still be
different stable principals. Raw identities and key material are never stored
or returned.

## Production Ports Without Production Adapters

S6a freezes five ports without production effect: `OutboxPort`, `BrokerPort`,
`SignatureAnchorPort`, `WormJournalPort` and `ReconciliationStorePort`.

The broker acknowledges every event with a unique opaque reference bound to
event ID, event hash, operation key and delivery key.
`SignatureAnchorPort.anchor(records, *, idempotency_key_sha256)` and
`WormJournalPort.commit(records, anchor, *, idempotency_key_sha256)` each
require a deterministic chain-head-bound operation key:

`SHA-256(nac.immutable-evidence-publication-operation.v1\u0000 || operation || chain_head_sha256)`

The operation names are exactly `signature-anchor` and `worm-commit`. The same
key must return the same receipt during crash-safe resume. Anchor and WORM
readbacks remain separate calls; every provider reference is normalized to an
opaque SHA-256 reference.

## Restart-Safe Publication And Reconciliation

`ReconciliationStorePort` contains exactly `claim_publication`,
`advance_publication`, `complete_publication`,
`authorize_publication_retry`, `require`, `close` and `is_required`.
`claim_publication` requires `claim_id`, `tenant_binding_sha256`,
`principal_key_binding_sha256` and the non-empty ordered `event_sha256s`
sequence, whose last item must equal the chain head. `require` accepts both
security bindings and `event_sha256s` as optional keyword-only fields.

A pre-claim requirement with reason `evidence-publication-incomplete`
persists both security bindings, the complete currently available ordered
event-hash prefix, `retry_authorized=false` and an empty
`retry_authorizations` list. The prefix may be empty before the outbox
snapshot. Dual-control authorization is first persisted in this requirement.
Retry remains fail closed without a principal-key binding. The first matching
claim must exactly extend the prefix, copies authorizations and their count into
publication state, persists the complete ordered sequence and removes the
consumed requirement in the same atomic state change. Reclaims require the
exact same sequence.

Before every possible external side effect, one write-ahead stage is
persisted: `outbox-snapshot`, `broker-in-flight`, `broker-complete`,
`anchor-in-flight`, `anchor-readback-in-flight`,
`anchor-readback-complete`, `worm-commit-in-flight`,
`worm-readback-in-flight`, `worm-readback-complete`. Persisted
`publication_progress` contains exactly the stage, acknowledged event hashes
and anchor, signature and WORM receipt hashes. Acknowledgements are
append-only; persisted references cannot be replaced.

An interrupted claim stays blocked. Only `authorize_publication_retry` with
distinct operator and approver principals bound to the same tenant and
principal key permits resuming the same chain head and progress. Already
acknowledged broker events are skipped.

A completed claim returns `status`, `result` and `publication_progress`.
Before idempotent replay, the stored chain length is checked against the
current actual event count, `broker_ack_count` against progress length, the
last acknowledged hash against the chain head, the
`worm-readback-complete` stage, and all anchor, signature and WORM bindings.
Only then may the stored result be returned without provider calls.

Every external port failure, including an `ImmutableEvidenceError` raised by
a port, is fully redacted at the boundary. Provider details are neither
returned nor persisted. The only allowed messages are
`evidence publication state is unavailable` and
`evidence publication requires reconciliation`. Only the trusted internal
reconciliation-state error remains distinguishable.

## Retention, Legal Hold And Access

Every event declares at least ten years of retention and
`legal_hold_capable=true`. Production policy readbacks, deletion protection,
monthly access reviews and separation of duties remain later gates. S6a
claims none of those proofs.

## Negative Gates

No successful completion occurs for tampering, duplicates, sequence or phase
errors, wrong predecessors, factory/snapshot drift, incomplete evidence,
sensitive fields, retention downgrade, invalid ETag HMAC, missing or
incorrectly bound receipts, claim/progress/completion drift, a different
actual chain length, non-deterministic anchor/WORM keys, unauthorized retry,
identical dual-control principals, a foreign tenant, a different principal
key or disclosure of external failure details.

## Status And Evidence

The CLI smoke creates synthetic normal and reconciliation chains only.
Redacted output names technical hashes, phases, event count, reconciliation
status and missing production ports. All six counters `network_calls`,
`provider_calls`, `tenant_calls`, `tenant_writes`, `credential_reads` and
`live_mutations` are zero; `production_worm_claim=false`.

## Acceptance Criteria

- **AC-S6-01:** Canonical envelope, strict phases, contiguous sequence and a
  SHA-256 chain.
- **AC-S6-02:** Intent before mutation, outcome and readback afterwards, plus
  immutable operation, delivery, tenant and principal-key bindings; retry only
  after authorized resume.
- **AC-S6-03:** Correlation, actor, operator and approver bind to the same
  persisted tenant; all three principals bind to the same principal key.
  Mismatches fail closed.
- **AC-S6-04:** Explicit ports require deterministic chain-head-bound
  anchor/WORM idempotency, independent readbacks and restart-safe publication
  claims.
- **AC-S6-05:** At least ten years of retention and legal-hold capability are
  declared; production control proofs remain pending.
- **AC-S6-06:** Principal-key-bound pre-claim retry authorization and the
  ordered event-hash prefix are persisted; claim must exactly extend the prefix
  and atomically consumes it into a complete publication sequence. Completed
  replay validates actual chain length and provider bindings.
- **AC-S6-07:** Offline/live status and all six zero counters are exact; no
  production or WORM claim is made.
- **AC-S6-08:** Unbound pre-claim retry, prefix/sequence drift and every other
  negative binding, resume, progress and port-failure case fail closed without
  leaking details.

## Non-Goals

- no PostgreSQL, broker, signature, anchor or WORM connection,
- no Graph, SharePoint, Entra, Azure, network or credential access,
- no production or resolvable matter, person or document data,
- no live schema apply, backfill, cutover, rollback or cleanup,
- no S7 approval and no claim of audit-proof production operation.
