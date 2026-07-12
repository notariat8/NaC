# BusinessCaseType Migration S5 Design

Status: implemented offline on the branch; completion after review, strict gate, and Protected PR
Date: 12 July 2026
Scope: deterministic, fully offline migration from the legacy Choice to the stable `BusinessCaseTypeId`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: business-case-type-migration-s5
leading_issue: https://github.com/notariat8/NaC/issues/618
risk_gate: Privacy
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-12-business-case-type-migration-s5.md
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-S5-01
  - AC-S5-02
  - AC-S5-03
  - AC-S5-04
  - AC-S5-05
  - AC-S5-06
  - AC-S5-07
validation_commands:
  - python3 -m unittest tests.test_business_case_type_migration tests.test_business_case_type_migration_quarantine tests.test_business_case_type_migration_cli tests.test_business_case_type_migration_contract
  - python3 -m unittest tests.test_business_case_type_runtime tests.test_business_case_type_cache tests.test_business_case_type_graph_read_edge tests.test_business_case_type_graph_read_edge_cli tests.test_business_case_type_graph_read_edge_contract tests.test_business_case_type_cli
  - python3 scripts/validate_business_case_type_migration.py
  - python3 scripts/nac.py kg business-case-type-migration-dry-run --help
  - python3 scripts/nac.py contracts verify
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/validate_gantt_progress.py
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Purpose And Boundary

S5 implements migration logic as a local Python domain runtime. It reads only
schema-validated synthetic fixtures below
`tests/fixtures/business-case-type-migration/`, creates deterministic plans
and redacted evidence, and performs no Microsoft Graph, SharePoint, Entra,
HTTP, DNS or tenant action. S4b writes, S6 immutable evidence and S7 live
approval remain separate scopes. Every real backfill, cutover, rollback or
reconciliation closure remains blocked without S6 and S7. Allowed live calls
and allowed tenant writes are exactly zero.

## Input Model And Data Minimization

The static mapping table is separately versioned at
`workflows/migrations/business-case-type/legacy-choice.mapping.json`. It is
not the historical slug-alias map from S3. The offline bundle binds its
canonical hash, a catalog version, completely numbered synthetic matter pages,
registry and optional process-register snapshots and two final scans. Every
final scan carries its own independently captured paged row set; its summary
and hash are reconstructed exclusively from those pages. Both registry
snapshots must contain exactly every canonical ID in the bound runtime catalog.
Each fixture additionally carries a separate `post_scan_observed_at` timestamp
and independently materialized `post_scan_registry_snapshot` and
`post_scan_process_snapshot` objects. The timestamp must be strictly after
scan two; these post-scan snapshots are not reused from the manifest snapshots.
Profiles for local N/N-1 capability evaluation live independently of scenario
fixtures at `workflows/migrations/business-case-type/runtime-candidates.json`;
the bundle binds the registry hash and evaluation scenarios.

The fixture root declares `data_classification="synthetic"` and
`contains_production_data=false`; record references match
`synref-[a-z0-9-]+`. A row contains only `record_ref`, `snapshot_etag`,
`current_etag`, `legacy_choice`, `business_case_type_id` and
`read_status`. Documents, persons, free text, raw Graph responses, tokens and
resolvable matter references are forbidden.
ETags, snapshot fields, local BPMN links, and approval references use narrow synthetic grammars; approval references are stored in the manifest only as hashes.

Stdout publishes status, the `S5_OFFLINE_ONLY` scope, live-cutover status
`BLOCKED_PENDING_S6_S7_APPROVAL`, both zero-live boundaries, fixed reason
codes, class counts and top-level hashes. The redacted artifact may additionally contain the operation plan,
`record_ref_hash`, target ID, `if_match`, idempotency key, page hashes,
quarantine IDs and scan, profile-evaluation and recovery results. A final
`readiness_evidence_hash` binds the base manifest, backfill plan, evaluation
scenarios, profile-evaluation result, and reconciled quarantine index.
Quarantine contains only pseudonymous hashes, ETags, classification, manifest
hash and fixture-bound RFC-3339 UTC timestamps. It is persistent but not
audit-proof. Its filesystem lock remains held from reconciliation through the
readiness decision and output commit. Existing files are read nonblocking;
records are limited to 16 KiB, the index to 32 MiB, and a records directory to
100128 entries.

## Deterministic Classification

Every row contains all six defined keys. The two business values are either
JSON `null` or non-empty strings; empty or whitespace-only strings are
`unresolved`. Missing keys, invalid `record_ref` or duplicate references
across page boundaries invalidate the complete bundle. The canonical
top-level page set must exactly equal the second final-scan page set, so
readiness always classifies the same final observed population.

The disjoint normative evaluation order is:

1. `read_status != "complete"` or an invalid business-field type yields
   `unresolved`.
2. Missing, empty or differing snapshot/current ETags yield `etag_skipped`.
3. Both business values `null` yields `missing`.
4. When both values are set, only a known canonical ID with the same known
   legacy mapping yields `already_canonical`; every other case is
   `conflict`.
5. With only the new ID set, a known canonical ID yields
   `already_canonical`; otherwise `unknown`.
6. With only legacy set, an exact mapping yields `mappable`; otherwise
   `unknown`.

Thus every validly shaped row receives exactly one of `already_canonical`,
`mappable`, `conflict`, `unknown`, `missing`, `etag_skipped` or
`unresolved`. Values are never trimmed, normalized, lower-cased or guessed.

Mapping sources equal exactly, with no additions, the four frozen legacy
Choices `immobilienkaufvertrag`, `unterschriftsbeglaubigung`,
`online-gmbh-gruendung` and `handelsregisteranmeldung`. Legacy Choice and canonical ID are separate typed namespaces; identical
strings across the two namespaces are explicitly valid identity mappings.
Every legacy Choice has exactly one direct canonical target. Duplicate sources,
multiple targets, unknown targets, additional sources or incomplete baseline
coverage block the bundle. S3 alias-chain and self-target rules do not apply to
these typed identity mappings. Mapping version and manifest bind the canonical
baseline fingerprint.

## Backfill Plan And Quarantine

Input pages are complete and numbered: `page_number` starts at 1 and is
contiguous, `page_count` is identical on every page, and only the last page
has `complete=true`. At most 1,000 pages, 100 rows per page and 100,000 rows
in total are accepted. Invalid or incomplete pages and cross-page duplicates
produce no partial result.

Only `mappable` creates a planned operation. It sets only
`VorgangstypId`, binds the current item ETag as future `If-Match`, and has a
stable idempotency key derived from manifest hash, `record_ref_hash`, target
ID and ETag. `already_canonical` creates a no-op. The five blocker classes
are quarantined without mutation. Operations are sorted by
`record_ref_hash` independently of input page boundaries and repaginated
with fixed page size 100. Every page carries `page_number`,
`operation_count` and a canonical page hash; the plan binds the ordered page
hashes.

`record_ref_hash` is SHA-256 of the exact fixture reference. `record_id` is
SHA-256 of manifest hash, `record_ref_hash`, classification and current ETag.
`observed_at` comes from the fixture and is excluded from identity. The writer creates and syncs a temporary record in the target directory. It
publishes via an atomic hard link with no-overwrite semantics. If the
destination exists, bytes are compared: identical is a no-op, divergent
content blocks; an existing destination is never replaced. The temporary file
and directory are then synced and cleaned up. It then rebuilds
the index only from complete readable content-addressed records and atomically
replaces the index. Startup reconciliation indexes complete orphan records;
references to missing or invalid records block. Identical records are no-ops,
while divergent content under the same ID blocks. Partial failures yield
`artifact_write_failed` and never partial success. S5 has no close/delete
operation.

## Manifest And Snapshots

The migration manifest binds at least:

- repository commit, `CatalogVersion`, mapping, schema, runtime and contract N
  versions, and the pinned N-1 profile that is not yet executable-validated,
- hashed site, schema and list bindings,
- canonical hash and row count for all matter pages including relevant field
  values and item ETags,
  The hash retains page number, page count, complete flag, page boundaries, and technically sorted rows within each page; different paging yields a different manifest hash.
- complete `Vorgangsartenregister` snapshot with row ETags,
- `Prozessregister` as `present` with row ETags and nullable BPMN links, or
  explicitly as `not_provisioned`,
- mapping hash, hashed synthetic role-approval references and all snapshot hashes.

Hashes use exactly `json.dumps(value, sort_keys=True, separators=(",", ":"),
ensure_ascii=True, allow_nan=False)` and SHA-256 over the UTF-8 bytes. Only JSON
null, Boolean, integer, string, list and object are allowed; floats are
forbidden. Input collections are sorted by stable technical keys before
hashing.

## Stable Final Scans And Cutover Readiness

The scan hash covers the complete canonical page shape, including page number,
page count, completion flag, and all six strictly typed synthetic row fields
sorted by `record_ref`. Cutover readiness is
`READY` only when every record is `already_canonical` and all
five blocker classes have exactly zero counts, both paged scans are complete,
have distinct scan IDs, mark migration writes frozen, are at least 900 seconds
apart, and have identical count and hash.

Any difference returns `BLOCKED` and requires two new complete scans. A
non-empty reconciled append-only quarantine also blocks `READY`. Registry and
process snapshots are recomputed after scan two; both complete scan page sets,
their summaries, `post_scan_observed_at`, and the post-scan snapshots are
bound into the manifest hash.

## N/N-1 Profile Evaluation

`runtime-candidates.json` pins candidate IDs, contract versions, profiles and
expected profile hashes outside every scenario fixture; the domain contract
also binds the hash of that registry. A local `MigrationReplayPort` evaluates
the same four hard-coded profile scenarios for
N and N-1: read `VorgangstypId`, ignore additive registry fields, treat
unknown IDs fail-closed, and display new types without a legacy Choice
read-only. Every candidate is bound by candidate ID, contract version and
SHA-256 of its local replay profile.

Results contain the profile evaluator decision and fixed reason code for every
candidate and scenario; fixture Boolean assertions are not capability
evidence. Any failed scenario or profile-hash drift blocks offline readiness.
Evidence executes neither candidate runtime nor binary, deployment, or release
action and claims only static contract compatibility of the pinned profile.
Executable N/N-1 validation remains mandatory before any switch.

## Rollback And Forward Recovery

The rollback plan has immutable ordering:

1. Stop matter creation, correction, backfill, cutover and dependent routing.
2. Preserve rollback intent, current snapshots/ETags and quarantine through
   the immutable S6 evidence that is still to be implemented.
3. Disable the canonical-write flag and invalidate registry/process caches.
4. Switch to an approved N-1 candidate only after separate executable validation.
5. Restore registry/process projections only when needed and only with ETag
   binding against the manifest-bound snapshot; retain columns and canonical
   values.
6. Run readback and a complete rescan, and reopen only unambiguously mappable
   legacy writes.

Forward recovery redeploys N, reloads catalog and registries, requires the
immutable S6 outbox that is still to be implemented and plans its idempotent
replay, requires all quarantine cases to be resolved and runs two new stable
scans. It creates no legacy substitutes and performs no action in S5. Both
plans report `BLOCKED_PENDING_S6_S7_APPROVAL`.

## Central CLI

The entry point is:

```text
nac kg business-case-type-migration-dry-run
```

Relative paths resolve against `--repo-root`. `--fixture` must be a regular
file below `tests/fixtures/business-case-type-migration/`; a symlink escaping
that boundary is rejected. `--quarantine-state` and `--output` are canonically resolved, may contain no
symlink component, and are distinct non-overlapping targets below the
canonically resolved `out/notary-kg/`. `--output` defaults to
`out/notary-kg/business-case-type-migration-s5.redacted.json`; the quarantine
directory is required. The central CLI delegates only these paths to
`notary_kg.cli`; domain I/O does not live in `nac_cli`.

The current repository commit is read from Git metadata without a subprocess
and bound into the manifest. Resolution supports a `.git` directory or linked
worktree `.git` file, symbolic or detached HEAD, and loose or `packed-refs`.
Unreadable, unborn or ambiguous HEAD yields `repository_state_unavailable`.
Fixture reads are bounded to 4 MiB before reading, regular Git admin files to
1 MiB, and `packed-refs` to 8 MiB.
Dirty-worktree state is not part of this hash; Protected-PR and strict gates
remain authoritative. All timestamps come from
the fixture, normalized as UTC seconds with `Z`; wall-clock time is not read.

The command accepts no site, tenant, token, certificate, URL, Graph,
credential, apply, cutover, rollback or cleanup option. `READY` is qualified
S5 offline readiness only, always includes the blocked live-cutover status, and
exits 0; a validly evaluated `BLOCKED` exits 2. Shape, contract, hash or persistence errors exit 1. The redacted output artifact uses the same
temporary-file, sync and atomic-replace protocol as the index under a
destination-specific filesystem lock. Rollback occurs only while the target
still matches this writer's replacement inode; a declared
`.<name>.previous` recovery marker is deterministically reconciled on the
next locked start. Allowed error codes are `fixture_invalid`, `contract_invalid`
, `artifact_write_failed` and `repository_state_unavailable`; business
blockers use the seven class names plus
`scan_unstable`, `profile_evaluation_failed` and `blocked_pending_s6_s7`.

## Acceptance Criteria

- **AC-S5-01:** Every synthetic matter is deterministically assigned to
  exactly one of seven classes; ambiguous, unknown, empty or conflicting
  values fail closed.
- **AC-S5-02:** The base manifest binds all versions, independently captured
  final scans and snapshots, including item/row ETags, nullable BPMN links and
  explicit `not_provisioned`. The final evidence anchor additionally binds
  the backfill plan, scenarios, profile evaluation and quarantine index.
- **AC-S5-03:** The backfill plan is paged and idempotent, plans only
  `VorgangstypId` with current item ETag/`If-Match`, and persistently places
  all five blocker classes in local quarantine. It performs no Graph, tenant, registry,
process-register or matter writes; only the declared local redacted artifacts
are written.
- **AC-S5-04:** S5 offline readiness requires only `already_canonical`,
  exactly zero blocker classes, full registry coverage, an empty reconciled
  quarantine, and two independently captured identical complete scans with
  frozen writes at least 15 minutes apart.
- **AC-S5-05:** Pinned N/N-1 profile evaluation checks reading
  `VorgangstypId`, ignoring additive registry fields, failing closed for
  unknown IDs and read-only display of new types without a legacy Choice,
  without claiming executable runtime validation.
- **AC-S5-06:** Rollback follows the fixed six-step order and deletes no
  columns or values; forward recovery uses no legacy substitutes and remains
  blocked without S6/S7.
- **AC-S5-07:** Central CLI, domain/verification contract, validator,
  synthetic tests, DE/EN documentation, strict gate and independent
  `base...head` review pass with exactly zero live calls.

## Non-Goals

- no live Graph, tenant write or credential use,
- no schema apply, backfill write, cutover, rollback or cleanup,
- no claim of audit-proof evidence before S6,
- no reconciliation closure or quarantine deletion,
- no production matter, person or document data.
