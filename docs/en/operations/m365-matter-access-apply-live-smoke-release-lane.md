# M365 Matter Access Apply Live-Smoke Release Lane

This release-lane standard deliberately separates the owner-gated
`matter-access-apply-smoke` from the normal M365 Runtime Release Gate. The
smoke writes real synthetic SharePoint list items to `Vertretungsfreigaben`
and `AuditJournalLite`, reads them back, deletes them in the same run and
stores only redacted evidence. Therefore it is not a silent default in the
one-shot runner.

The `matter-access-apply-smoke` is an owner-gated release lane: not a silent
default, not automatically attached to evidence and not started without the
prepared approval text.

## Purpose

The live smoke proves that the future apply path for timeboxed deputy grants is
not only planned offline, but can write, read and clean up through Graph REST
in the workspace.

It complements, but does not replace:

- `matter-access-apply-readiness`
- `matter-access-apply-request-plan`
- `matter-access-apply-policy-smoke`
- the normal `release-gate-run` with `mvp_release_readiness=READY`

## Trigger

Run the live smoke separately when at least one of these conditions applies:

- the apply path for `grant_request` or `audit_append` changed
- the SharePoint list model for `Vertretungsfreigaben` or `AuditJournalLite`
  changed
- runtime credentials, app permissions or Graph REST boundaries changed
- a real synthetic write-read-cleanup must be proven before domain acceptance

An agent must not infer this smoke automatically from a normal release gate.
The live smoke always needs explicit owner approval.

## Preconditions

- local `main` is current
- the normal M365 Runtime Release Gate is `PASSED`
- `release-readiness` reports `mvp_release_readiness=READY`
- `matter-access-apply-policy-smoke` reports `5/5` negative cases and
  fail-closed behavior before Graph writes
- the target workspace is explicitly approved, normally `notary_team_01` in
  the MVP
- only synthetic IDs with prefixes `NAC-SMOKE-GRANT-` and
  `NAC-SMOKE-MATTER-` are used

## Approval Text

```text
Freigabe: Matter-Access Apply Live-Smoke im Workspace notary_team_01 owner-approved ausführen, inklusive synthetischer Vertretungsfreigabe, Audit-Event, Readback, Cleanup und redigiertem Evidence-Artefakt.
```

## Command

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-smoke \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --format json
```

The default artifact path is:

```text
out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json
```

After a successful run, the command also automatically archives the redacted
live-smoke artifact in a correlation-based retention folder:

```text
out/m365/teams-sharepoint/matter-access-apply-live-smokes/<correlation-id>/
```

That folder contains at least:

```text
matter-access-apply-smoke.redacted.json
matter-access-apply-live-smoke-retention.redacted.json
matter-access-apply-live-smoke-retention.redacted.md
```

The root index is stored at:

```text
out/m365/teams-sharepoint/matter-access-apply-live-smokes/matter-access-apply-live-smoke-retention-index.redacted.json
```

Existing redacted artifacts can be retained offline:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-live-smoke-retain \
  --matter-access-apply-live-smoke-artifact out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json \
  --format json
```

The offline index is locally filterable and performs no Graph request:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-live-smoke-retention-index \
  --matter-access-apply-live-smoke-correlation-id <correlation-id> \
  --format json
```

Retention also checks the shape of the redacted live-smoke artifact. The
recursive shape check blocks before copying when forbidden raw fields or
sensitive markers such as raw Graph paths, raw responses, write payloads,
tokens, secrets or matter payloads appear. An accepted artifact reports
`redaction_shape_status=PASSED` and
`sourceArtifactRedactionShapeChecked=true`.
The retention index and readiness evidence aggregate this shape check through
`redaction_shape_status_counts` and
`redaction_shape_legacy_missing_count`; older retention runs without embedded
shape evidence are explicitly shown as `NOT_EVALUATED` and block readiness
until a current run is retained.
In that case the JSON evidence sets `redaction_shape_upgrade_required=true` and
returns `upgrade_advice.status=UPGRADE_REQUIRED` with a local
`matter-access-apply-live-smoke-retain` re-retention command for the already
redacted live-smoke artifact; this upgrade advice performs no Graph or tenant
action.

Retained evidence can be evaluated offline as `READY`/`NOT_READY` before
acceptance. The readiness command reads only the local redacted retention index
and performs no Graph or tenant action:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-live-smoke-retention-readiness \
  --matter-access-apply-live-smoke-correlation-id <correlation-id> \
  --matter-access-apply-live-smoke-write-readiness \
  --format json
```

With `--matter-access-apply-live-smoke-write-readiness`, it also writes:

```text
matter-access-apply-live-smoke-retention-readiness.redacted.json
matter-access-apply-live-smoke-retention-readiness.redacted.md
```

An existing owner-gated artifact can then be explicitly attached to release
gate evidence:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-evidence \
  --release-gate-matter-access-apply-smoke-artifact out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json \
  --format json
```

Without this parameter, `matter_access_apply_smoke` intentionally remains
`NOT_ATTACHED` in `release-gate-evidence`; existing default files are not
picked up automatically.

## Acceptance Criteria

- `status=PASSED`
- `write_tools=["grant_request", "audit_append"]`
- `write_lists=["Vertretungsfreigaben", "AuditJournalLite"]`
- `executed_graph_requests=true`
- `executed_graph_writes=true`
- `sharepoint_item_writes_executed=true`
- `planned_write_count=2`
- `grant_read_value_count=1`
- `audit_read_value_count=1`
- `cleanup_requested=true`
- `grant_cleanup_read_after_value_count=0`
- `audit_cleanup_read_after_value_count=0`
- `tenant_mutation_allowed=false`
- `team_membership_mutation_allowed=false`
- `sharepoint_item_permission_mutation_allowed=false`
- `stores_tokens_or_secrets=false`
- `stores_matter_payloads=false`
- `raw_graph_path_stored=false`
- `raw_graph_response_stored=false`
- `raw_write_payload_stored=false`
- `reads_sharepoint_file_content=false`
- Retention: `retention_executes_graph_requests=false`
- Retention: `retention_tenant_writes_executed=false`
- Retention: `redaction_shape_status=PASSED`
- Retention: `sourceArtifactRedactionShapeChecked=true`
- Retention: correlation-based folder and root index exist
- Readiness: `status=READY`
- Readiness: `executes_graph_requests=false`
- Readiness: `tenant_writes_executed=false`

## Failure Behavior

If the smoke is not `PASSED`, the release lane is blocked. If cleanup or
cleanup readback fails, no approval continues. If the smoke passed but the
correlation-based retention is not `PASSED`, the command also does not return a
successful completion. If retention readiness reports `NOT_READY`, no business
acceptance is claimed. The next step is a separate owner-gated cleanup action
with redacted leftover evidence or an offline retention fix; productive matter
IDs must not be used as fallback targets.

## Boundaries

This standard does not allow productive deputy grants, Teams membership
changes, SharePoint item permission mutations, SharePoint file content reads,
Graph beta, SDK or PnP use, or storage of tokens, secrets, raw responses,
concrete Graph paths or matter payloads.
