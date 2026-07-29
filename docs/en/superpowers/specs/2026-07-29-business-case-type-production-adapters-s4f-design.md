# BusinessCaseType Production Adapters S4f

Status: `S4F_PARTIAL_IMPLEMENTATION_DESIGN_OFFLINE`
Date: 29 July 2026
Scope: decided production adapters without live provider access

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-production-adapters-s4f
leading_issue: https://github.com/notariat8/NaC/issues/704
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-29-business-case-type-production-adapters-s4f.md
review_gates:
  - Secrets
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4F-01
  - AC-S4F-02
  - AC-S4F-03
  - AC-S4F-04
  - AC-S4F-05
  - AC-S4F-06
  - AC-S4F-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_production_adapters tests.test_sqlite_evidence_staging_outbox tests.test_business_case_type_production_adapters_contract tests.test_business_case_type_production_adapters_cli
  - python3 scripts/validate_business_case_type_production_adapters.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/quality_gate.py --profile strict
  - git diff --check
```

## Goal

S4f replaces the placeholders identified by S4e with offline-verified adapter
implementations wherever the platform decision already exists. The slice
performs no provider call, enables no runtime, and makes no production
readiness claim.

## Implemented Adapters

1. A GitHub issue-comment verifier binds owner, association, immutable
   canonical comment, issue, and every S4d hash. The SHA-256 verified `gh` image
   executes as a sealed Linux `memfd`; stdout is bounded before completion and
   stderr is discarded.
2. A certificate write-identity factory binds tenant, client ID, certificate
   content, and private-key content and passes only verified bytes to the token
   provider.
3. A `urllib` HTTP port blocks redirects, foreign hosts, non-v1.0 paths, dot
   segments, encoded separators, disallowed methods, automatic retries, and raw
   provider error bodies.
4. A SQLite outbox persists canonical evidence events atomically, across
   restarts, and with sequence/hash binding. On open, routing columns are
   checked globally against hash-bound event content.

## Deliberately Open Adapters

- The central production outbox remains PostgreSQL according to the target
  architecture. S4f provides only a restart-safe local SQLite staging
  boundary. Promotion, central acknowledgement, retention, and local cleanup
  require a separate PostgreSQL contract. Without that acknowledgement the
  local outbox cannot mark a mutation complete.
- The broker product and signature/anchor method remain explicit architecture
  decisions. S4f does not create pretend adapters.
- The Azure Blob WORM journal exists; its production management/data-plane
  transport and irreversible policy lock remain owner-gated.
- A dedicated Entra write identity, its site grant, and provider-side readback
  of both bindings remain live gates.

The completion status is therefore
`S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE`, not `S4E_READY_OFFLINE`, not
`RUNTIME_READY`, and not `LIVE_READY`.

## Security Boundaries

- `notary_team_01` remains the only allowed workspace.
- The provisioning app cannot write business-case data.
- BFF, provisioning, and writer remain separate principals.
- No adapter follows redirects or retries automatically.
- Provider failures reduce to stable reason codes.
- Tokens, certificate paths, principal IDs, comments, and provider bodies are
  never returned.
- Tests use injected local fakes and temporary SQLite files only.

## Acceptance Criteria

- **AC-S4F-01:** Provisioning, writer, and BFF identities remain separate.
- **AC-S4F-02:** The Graph HTTP port blocks every deviation from the bound
  Graph-v1.0 write edge, including path-normalization and percent-encoding
  bypasses and raw or encoded control characters.
- **AC-S4F-03:** The owner verifier accepts exactly one immutable canonical
  owner comment, executes only a sealed hash-verified binary image with bounded
  output, and returns no raw data.
- **AC-S4F-04:** The local SQLite staging outbox survives restarts and enforces
  sequence, hash chain, routing-column binding, deduplication, and atomic
  transactions. It exposes no
  completion, acknowledgement, promotion, or cleanup operation.
  File and directory require exact `0600` and `0700` modes. Only explicitly
  allowlisted local Linux filesystems are accepted; unknown filesystems are
  rejected. Detection of local synced directories is not implemented yet and
  remains a runtime blocker.
- **AC-S4F-05:** Central PostgreSQL outbox with promotion, acknowledgement, retention, and local
  cleanup, broker
  product, signature/anchor method, provider-side identity and site-grant
  readback, Azure WORM REST transport, irreversible WORM policy lock, dedicated
  Entra writer identity with site grant, local synced-directory detection, and owner-gated live activation each
  remain an explicit blocker.
- **AC-S4F-06:** Status output reports only
  `S4F_PARTIAL_ADAPTERS_VERIFIED_OFFLINE`; production readiness, runtime
  composition, and live authorization remain `false`.
- **AC-S4F-07:** Tests, contracts, validators, strict gate, and independent
  review pass.
