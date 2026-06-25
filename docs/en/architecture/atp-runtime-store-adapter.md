# ATP Runtime Store Adapter

Status: owner-free contract-first interface, testable without live OCI and
without schema apply.

`RuntimeStoreAdapter` defines the narrow runtime boundary for tenants, user
bindings, matter anchors, process instances, process events and audit events.
The first implementation is `InMemoryRuntimeStore`; it is a deterministic test
adapter, not a productive ATP integration.

## Contract Shape

- Subject-matter state is carried as versioned JSON payloads.
- Process events and audit events are append-only.
- The adapter stores no secrets, no raw mandate data and no productive mandate
  data.
- No live OCI. No schema apply. No productive graph activation.
- The deferred graph projection is derived from `process_events` later and is
  only marked as deferred graph projection here.

This slice is intentionally disjoint from ATP schema or deployment PRs. A later
ATP adapter can implement the same contract without this PR creating database
objects or touching mandate data.
