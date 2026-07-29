# S4b BusinessCaseType Graph Write Edge

Status: implemented offline in Issue [#694](https://github.com/notariat8/NaC/issues/694); protected-PR acceptance pending

## Goal

S4b provides a bounded fail-closed Graph write edge for exactly five operations:

- `case_create`
- `case_status_update`
- `task_create`
- `task_update`
- `business_case_type_backfill`

The detailed design is in the [S4b specification](../superpowers/specs/2026-07-28-business-case-type-graph-write-edge-s4b-design.md), and the implementation steps are in the [S4b implementation plan](../superpowers/plans/2026-07-28-business-case-type-graph-write-edge-s4b.md). The [BusinessCaseTypeId ADR](business-case-type-id.md) remains the overarching identifier decision.

## Offline Entry Point

```bash
nac m365 teams-sharepoint business-case-type-write-dry-run --operation case_create --format json
```

`--operation` accepts only the five values listed above. The command uses synthetic inputs, emits redacted structure, gate, and hash information only, and keeps these counters at zero:

- credential reads,
- live factories,
- HTTP, DNS, and Graph calls,
- tenant and SharePoint writes.

Site, list, identity, and domain field values are not emitted. The dry run plans deduplication or ETag freshness, exactly one write, and readback, but does not execute these requests.

## Identity And Safety Boundary

A later production write path requires an identity separate from the BFF UAMI. The [S4b domain contract](../../../workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json) limits it to `Sites.Selected` with site grant `write`; the BFF UAMI remains at `Sites.Selected` with site grant `read`. Create operations are deduplicated through unique keys, patch operations require fresh ETags, backfill binds canonical S5 hashes, and uncertain outcomes remain blocked in persistent reconciliation.

## Still Open

Domain, plan, edge, synthetic dry run, tests, contract, verification contract, and validator are implemented offline. The following are not implemented or approved:

- production factory and credential composition,
- Entra, permission, schema, or tenant changes,
- live Graph or SharePoint writes,
- automatic reconciliation closure,
- production S6/evidence composition.

These steps remain separately owner-gated. The offline-implemented state does not claim production write readiness.

## Verification

The [verification contract](../../../workflows/verification-contracts/business-case-type-graph-write-edge-s4b.verification.json) and [S4b validator](../../../scripts/validate_business_case_type_graph_write_edge.py) verify operations, bindings, redaction, and zero-live boundaries. The central routing surface is the [agent context index](../../../agent-context/index.json).
