# BusinessCaseType Graph Write Composition S4c Design

Status: `S4C_DESIGN`
Date: 29 July 2026
Scope: production-shaped but strictly offline local runtime composition

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-graph-write-composition-s4c
leading_issue: https://github.com/notariat8/NaC/issues/698
risk_gate: Privacy
delivery_mode: Protected PR
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S4C-01
  - AC-S4C-02
  - AC-S4C-03
  - AC-S4C-04
  - AC-S4C-05
  - AC-S4C-06
  - AC-S4C-07
  - AC-S4C-08
validation_commands:
  - python3 -m unittest tests.test_business_case_type_graph_write_composition tests.test_business_case_type_graph_write_state_store tests.test_business_case_type_graph_write_http_transport tests.test_business_case_type_graph_write_credentials tests.test_business_case_type_graph_write_crash_recovery tests.test_business_case_type_graph_write_composition_contract tests.test_business_case_type_graph_write_composition_cli
  - python3 scripts/validate_business_case_type_graph_write_composition.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 -m compileall -q src/nac_m365_graph/business_case_type_write_state.py src/nac_m365_graph/business_case_type_write_transport.py src/nac_m365_graph/business_case_type_write_composition.py src/nac_m365_graph/business_case_type_write_composition_smoke.py scripts/validate_business_case_type_graph_write_composition.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Purpose And Boundary

S4c wires the unchanged S4b write edge to a locally persistent state/evidence
adapter, an exact Microsoft Graph REST v1.0 transport and an explicit
dependency-injection composition. The slice adds no business operation and
weakens no S4b boundary.

S4c is not a live path. Its offline smoke uses temporary SQLite state and a
scripted HTTP port. It reads no environment, token or certificate and performs
no DNS, socket, Graph or tenant action. Central multi-instance durability,
S6/WORM publication, real approval verification, a write identity and a live
factory remain separate later gates.

## Local Persistence Adapter

The store uses SQLite only for technical, redacted execution state. The key is
the S4b hash over target binding and mutation ID. A state transition and its
event are written in the same `BEGIN IMMEDIATE` transaction.

The guaranteed durability envelope is explicitly a local POSIX filesystem path
on one host, not OneDrive, NFS or another network filesystem. The directory
mode is `0700` and the database mode is `0600`; symlinks and foreign owners are
rejected. SQLite uses `journal_mode=DELETE`, `synchronous=FULL`,
`foreign_keys=ON`, `trusted_schema=OFF` and `busy_timeout=0`. The parent
directory is synchronized after initial creation. A same-owner transient
`-journal` file is permitted only during a SQLite transaction; no sidecar
remains after a clean close. The tested and claimed boundary is process crash
plus reopen on the same host. Kernel, power, hardware, filesystem or host loss
and central multi-instance durability are outside the guarantee.

Every transition applies compare-and-swap to the expected generation and
`authorization_run_identity`. The allowed matrix is:

| Source | Action | CAS predicate | Result |
| --- | --- | --- | --- |
| `clear + absent`, generation `0/0` | `intent` | expected `0`, no prior run identity | `clear + open`, generation `1/0` |
| `clear + retryable`, generation `n/n` | `intent` | expected `n`, exact prior identity, distinct new identity | `clear + open`, generation `n+1/n` |
| `clear + open`, generation `n/c` | `outcome` | same generation/identity, no identical phase event | state unchanged, event appended |
| `clear + open`, generation `n/c` | `reconciliation_required` | same generation/identity | `required + open`, generation `n/c` |
| `clear + open`, generation `n/c` | verified `readback` | same generation/identity, terminal or retryable closure | `clear + closed|retryable`, generation `n/n` |
| `required + open`, generation `n/c` | non-closing `readback` | same generation/identity, `close_intent=false` | state unchanged, event appended |
| `required + open` | closure/replay | always | blocked |
| `closed` | any mutation | always | terminally blocked |

Concurrent first intents, duplicate phase events, wrong generations, equal
retry identities, busy/timeout and commit failures return `false` or
`unavailable` without partial commit. An open intent is committed before
transport and read back through a fresh connection.

The database is not opened through symlinks, receives restrictive permissions
and enforces fixed size and schema limits. Only allowlisted technical hashes,
operation, generations, HTTP status and stable result codes are persisted.
Field values, site/list/item IDs, URLs, headers, bodies, tokens, certificates
and raw approval references are forbidden.

## HTTP And Credential Boundary

The composition root gives the transport only to
`BusinessCaseTypeGraphWriteEdge`; other callers are outside the contract. The
transport is also constructed with the two exact collection paths derived from
the already validated target and accepts requests only below them. The existing
`GraphWriteTransport` port cannot itself verify a plan SHA, so that claim is not
made. It permits `GET`, `POST` and `PATCH` below
`https://graph.microsoft.com/v1.0`. Graph beta, foreign hosts, SharePoint REST,
PnP, redirects and automatic retries are blocked.

Only the transport knows the injected access-token provider, and it is called
only after successful plan, authorization and persistence checks. Every
`transport.request` performs exactly one HTTP attempt; one complete edge run
may therefore contain multiple transport calls from its S4b plan. S4c includes
no environment, managed-identity or certificate factory. The HTTP port receives
canonical request bytes and returns status, bounded object-shaped JSON and
allowlisted response headers. Provider failures are mapped to stable results
without exception text or raw data.

## Crash Recovery

Fault injection covers at least:

1. intent persisted before transport,
2. uncertain transport effect before outcome,
3. outcome persisted before readback,
4. closure persisted before acknowledgement,
5. corrupt, oversized or unreadable state.

A restart must never cause an automatic second write. Open or uncertain state
remains blocked until a later external reconciliation process supplies closure
proof. That process is outside S4c.

## Acceptance Criteria

- **AC-S4C-01:** One composition root wires the unchanged S4b builder and edge
  to state, HTTP and credential ports; exactly five operations remain allowed.
- **AC-S4C-02:** State and redacted event commit atomically within the defined
  local POSIX/SQLite process-restart envelope with generation CAS,
  authorization-run binding, locking and fail-closed file/schema/size checks.
- **AC-S4C-03:** Only the edge may use the transport bounded to both target
  collections; it permits only Graph v1.0 requests,
  `GET`/`POST`/`PATCH`, exact headers, bounded object JSON, no redirects and
  exactly one HTTP attempt per transport call.
- **AC-S4C-04:** Only the transport may call the injected token provider.
  Blocks before first transport cause zero token-provider calls; the offline
  smoke may use synthetic token-provider calls but performs no external
  credential-store, environment or file reads.
- **AC-S4C-05:** Persistence, results and failures use recursive allowlists and
  contain no target, payload, approval or credential raw data.
- **AC-S4C-06:** Dedupe, ETag/`If-Match`, S5 hash, execution key and
  authorization-run identity remain unchanged.
- **AC-S4C-07:** Crash/restart tests prove open or uncertain state blocks replay
  and a durably closed generation stays terminal after lost acknowledgement.
- **AC-S4C-08:** Completion is only `S4C_COMPOSITION_READY_OFFLINE` with zero
  socket/DNS/live-Graph, external credential-store and tenant activity.
  Synthetic token-provider calls are counted separately; central or production
  durability is not claimed.

## Out Of Scope

- a real write identity, Entra app, permission or site grant,
- environment, managed-identity, secret or certificate factories,
- live Graph, SharePoint or Teams calls,
- central multi-instance state or distributed locking,
- S6/WORM publisher composition,
- live execute, reconcile or cleanup commands.
