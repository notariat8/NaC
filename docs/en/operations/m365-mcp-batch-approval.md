# M365 MCP Batch Approval

This runbook groups recurring approvals for the active M365 MVP lane. The goal
is that agents fully prepare several independent PRs and smoke preparations
instead of waiting for owner input after each small step.

The active MVP lane remains Entra ID, Microsoft Teams, Microsoft 365 group,
SharePoint team site and Microsoft Graph REST or MCP. Legacy SharePoint APIs,
SharePoint SDKs and the archived OCI path are outside this runbook.

## No Owner Gate

The agent executes these steps autonomously:

- Create a GitHub issue with scope, acceptance criteria, risk and validation.
- Create a feature branch from the current `main`.
- Prepare code, tests, CLI surface, MCP contracts and documentation.
- Run local validators and repository quality gates.
- Open the PR, watch checks and fix check failures.
- Read read-only metadata as long as no secrets, tokens or real matter data are
  exposed.
- Produce a batch status with all prepared PRs, check results and exact
  approval text.

An agent does not end the work block with an open technical next step when that
step is executable without an owner gate.

## Owner Gates

These steps remain explicitly owner-gated:

- Merge PRs into `main`.
- Delete GitHub branches after merge when this is part of an approved batch.
- Run live write actions in the M365 tenant, even when only synthetic test
  matters are used.
- Run live delete actions in the M365 tenant.
- Change Entra app permissions, consent, certificates, secrets or credential
  flows.
- Change Teams, groups, sites, lists, columns, roles, membership or permissions
  in the live tenant.
- Process real matter data, personal data or confidential documents.

## Batch Packet

A batch packet includes at least this information for each PR:

| Field | Content |
| --- | --- |
| PR | number, title and branch |
| Scope | functional and technical scope |
| Checks | local validators and GitHub checks |
| Live tenant | `no live action`, `read-only` or the concrete write/delete action |
| Risk | relevant data, permission, tenant or operating boundary |
| Approval text | copyable owner approval |

The agent may prepare several PRs in parallel. It collects approvals only when
the PRs are review-ready or when a real owner gate is reached.

## Merge Approval

For a pure merge batch, one concrete sentence is enough:

```text
Freigabe: PRs #383, #385 mergen und Branches nach Merge aufräumen.
```

After this approval, the agent completes the approved merges, remote checks,
local synchronization and branch cleanup. It stops only on merge conflict,
failed check, permission error or unexpected scope.

## Live Smoke Approval

Live smokes are approved separately from the merge batch because they can write
or delete in the M365 tenant. For synthetic test matters, the standard text is:

```text
Freigabe: M365 MCP Smoke Suite live mit synthetischer Testakte im Workspace notary_team_01 ausführen, positive write-read und Cleanup im gleichen Lauf.
```

The technical run uses the central `nac` CLI:

```bash
python3 scripts/nac.py m365 teams-sharepoint mcp-smoke-suite \
  --owner-approved \
  --mcp-suite-cleanup \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --format json
```

The run may only create or clean synthetic IDs with the
`NAC-SMOKE-WRITE-READ-` prefix. Evidence is stored redacted; tokens, secrets,
raw data from real matters and complete personal content are not logged.

## Runtime Release Gate Approval

After runtime or MCP changes, the agent renders the complete gate offline.
`batch-approval m365 --batch-mode release-gate` renders the MVP Go/No-Go
standard by default: one-shot runner, redacted audit pack as self-compare,
redacted MVP readiness status and
`--release-gate-readiness-require-audit-pack`.

```bash
python3 scripts/nac.py batch-approval m365 --batch-mode release-gate --workspace-id notary_team_01 --correlation-id <correlation-id> --format json
```

When the audit pack should compare against a baseline instead of the current
run itself, the optional baseline parameter is enough; audit pack and readiness
stay implied in the release-gate batch mode:

```bash
python3 scripts/nac.py batch-approval m365 \
  --batch-mode release-gate \
  --workspace-id notary_team_01 \
  --correlation-id <correlation-id> \
  --release-gate-compare-left <baseline-correlation-id> \
  --format json
```

The renderer performs no GitHub or Graph write action. It emits the copyable
owner approval and exactly one leading live command in the MVP Go/No-Go
standard:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-run \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-write-audit-pack \
  --release-gate-write-readiness \
  --release-gate-readiness-require-audit-pack \
  --format json
```

The one-shot runner remains owner-gated and internally covers
`mcp-inventory-smoke`, `runtime-certificate-expiry-monitor`, `runtime-smoke`,
`runtime-metadata`, `mcp-smoke-suite --mcp-suite-cleanup`,
`mcp-smoke-leftover-cleanup --mcp-leftover-dry-run` and
`release-gate-evidence --release-gate-require-runtime-artifacts`.
`mcp-inventory-smoke` and `runtime-certificate-expiry-monitor` are offline,
`runtime-smoke` and `runtime-metadata` are read-only, the MCP Smoke Suite
writes and deletes one synthetic matter, and the leftover dry-run only reads
the match count.
`release-gate-evidence` runs offline at the end and reads only local redacted
artifacts. The expiry monitor, `runtime-smoke` and `runtime-metadata` write
their own redacted runtime artifacts so the completion report can return
`complete_release_gate_artifacts`. `mcp-inventory-smoke` writes a redacted
inventory artifact and attaches it to the completion report automatically. The
individual command remains a diagnostic and fallback path when that runner step
must be reproduced in isolation.

After a successful live gate, the offline `release-readiness` command
summarizes the latest or selected retention run into a compact MVP acceptance
status:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-readiness \
  --release-gate-readiness-correlation-id <correlation-id> \
  --release-gate-readiness-require-audit-pack \
  --format json
```

The status reads only redacted local retention, evidence and audit-pack
artifacts. It performs no Graph request, tenant write, delete or SharePoint
content read.
With `--release-gate-write-readiness`, the one-shot runner can write this
status directly for the current correlation ID; the standalone command remains
the diagnostic and re-run path for existing retention runs.

For post-gate evidence, the offline `release-gate-post-run-report` command
bundles that readiness status, the comparison with the explicit or
automatically previous complete `PASSED` baseline for the same workspace ID,
and a redacted GitHub comment draft:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-post-run-report \
  --release-gate-readiness-correlation-id <correlation-id> \
  --format json
```

The comment draft is written only as a local Markdown artifact; the command
posts nothing to GitHub and performs no Graph request, tenant write, delete or
SharePoint content read.
Existing post-gate reports can then be indexed offline:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-post-run-report-index \
  --release-gate-post-run-report-query <search-text> \
  --format json
```

The index reads only local `release-gate-post-run-report.redacted.json` files
and filters by correlation ID, baseline, status or free-text query. With
`release-gate-post-run-report-index-artifact`, the same view can be archived as
redacted JSON and Markdown evidence;
`--release-gate-post-run-report-index-output` and
`--release-gate-post-run-report-index-json-output` set the target paths.

## MVP Go/No-Go Acceptance Criterion

`release-readiness` is the binding MVP Go/No-Go acceptance criterion for the
M365 runtime path. An M365 MVP runtime approval is only `READY` when the
one-shot runner writes the audit pack and readiness status in the same
owner-gated execution and the output contains `mvp_release_readiness=READY` and
`release_gate_readiness=READY`.

The standard approval run therefore always uses these flags:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-run \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-write-audit-pack \
  --release-gate-write-readiness \
  --release-gate-readiness-require-audit-pack \
  --format json
```

No MVP approval is based only on `mcp-smoke-suite`, `runtime-smoke` or console
output. These individual commands remain diagnostic and reproduction paths; the
approval decision is bound to the redacted retention index,
`release-gate-evidence`, audit pack and `release-readiness`.

## Runtime Certificate Rotation Approval

After a `runtime-certificate-readiness` warning, the agent renders the complete
certificate rotation package offline:

```bash
python3 scripts/nac.py batch-approval m365 \
  --batch-mode runtime-certificate-rotation \
  --workspace-id notary_team_01 \
  --correlation-id <correlation-id> \
  --format json
```

The renderer performs no GitHub or Graph write action and reads no certificate,
private-key or secret files. It bundles the required owner gates in one
copyable approval text: generate a local runtime certificate, upload the public
certificate to Entra, update the local runtime credential boundary, run
`release-gate-run` live, refresh non-secret runtime evidence through a PR,
remove the stale Entra credential, delete the local old-certificate archive and
log out the local delegated M365 CLI session.
The embedded `release-gate-run` renders the same MVP Go/No-Go standard as
`batch-approval m365 --batch-mode release-gate`: redacted audit pack, redacted
MVP readiness status and audit-pack requirement for READY.

## Standard Runtime Evidence For MCP/Runtime Changes

`release-gate-run` is the standard runtime evidence after a merged change set
when that change touches one of these surfaces:

- `teams-sharepoint-data-mcp` contract, tool boundaries or adapter behavior,
- `nac_m365_graph` runtime, Graph client, smoke or cleanup modules,
- central `nac` CLI surface for M365 MCP smokes,
- runtime Graph configuration, certificate path or Sites.Selected access,
- runbook or operator changes that affect the live write/read/cleanup path.

The evidence run must not start automatically without approval. It remains a
separate owner gate because the internally covered
`mcp-smoke-suite --mcp-suite-cleanup` step writes and deletes a synthetic matter
in the live tenant. After approval, the agent must complete the run end to end:
runtime smoke, runtime metadata, write, read, cleanup, leftover dry-run,
certificate expiry monitor, runtime env bootstrap, evidence export, workspace
clean state and concrete result in the final
status. The MCP Smoke Suite remains the diagnostic/component path when only
that step must be reproduced in isolation. If a synthetic leftover remains
after the run, the agent must immediately prepare the owner-gated
`mcp-smoke-leftover-cleanup` path.

When `release-gate-run` is used, the runner creates the redacted completion
report in the same owner-gated run and also copies the existing redacted
artifacts to `out/m365/teams-sharepoint/release-gates/<correlation-id>/`. That
folder also contains `release-gate-retention-index.redacted.json`, so multiple
gate runs remain auditable side by side while `out/m365/teams-sharepoint/`
continues to hold the latest overwritten state. After the retention step, the
runner refreshes the completion report, evidence JSON and artifact index with
the retention path and copies those refreshed artifacts into the run folder
again. The following offline exporter remains only for diagnostics or
re-exporting existing artifacts:

Optionally, the same runner can write a redacted offline audit pack and then
the redacted MVP readiness status directly:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-run \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-write-audit-pack \
  --release-gate-compare-left <baseline-correlation-id> \
  --release-gate-write-readiness \
  --release-gate-readiness-require-audit-pack \
  --release-gate-write-post-run-report \
  --release-gate-write-post-run-report-index \
  --format json
```

The right comparison side defaults to the just archived run. When
`--release-gate-compare-left` is omitted, the runner packages the current run
against itself. `--release-gate-audit-pack-dir` can set the target directory.
The audit-pack step runs only after successful retention and stays offline;
Graph requests, tenant writes, deletes and SharePoint content reads are
excluded.
With `--release-gate-write-post-run-report`, the runner then writes the
redacted offline post-gate report and local GitHub evidence comment draft
directly. The switch implies the audit pack, readiness and audit-pack
requirement for readiness; without `--release-gate-compare-left`, it uses the
previous complete `PASSED` run for the same workspace ID as the baseline.
`release-gate-post-run-report-index` then lists those archived reports offline
by correlation ID, baseline, status and local paths; the artifact mode writes a
redacted index copy for audit packages.
With `--release-gate-write-post-run-report-index`, the one-shot runner creates
that index copy directly in the same run. The switch implies
`--release-gate-write-post-run-report` and remains a local offline artifact
step without Graph, GitHub or tenant write access.

The local audit overview runs offline through:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-list \
  --format json
```

The command reads only local retention-index and evidence JSON files under
`out/m365/teams-sharepoint/release-gates/` and emits correlation ID, status,
timestamp, workspace, artifact counts and local evidence paths. It performs no
Graph request, tenant write or delete.

The local comparison of two archived runs is also offline:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-compare \
  --release-gate-compare-left <left-correlation-id> \
  --release-gate-compare-right <right-correlation-id> \
  --format json
```

`--release-gate-compare-left` and `--release-gate-compare-right` accept
correlation IDs, run folders or direct
`release-gate-retention-index.redacted.json` paths. The comparison reports
status, timestamp, artifact, missing-attachment and evidence-path differences,
but reads no SharePoint file content and performs no Graph request, tenant
write or delete.

A versionable comparison evidence artifact is written offline with the same
input:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-compare-artifact \
  --release-gate-compare-left <left-correlation-id> \
  --release-gate-compare-right <right-correlation-id> \
  --format json
```

Without explicit paths, the command writes
`release-gate-retention-compare.redacted.md` and
`release-gate-retention-compare.redacted.json` under
`out/m365/teams-sharepoint/release-gate-comparisons/<left>__<right>/`.
`--release-gate-compare-output` and `--release-gate-compare-json-output` set
custom targets. The export remains redacted and offline.

The local index for existing comparison evidence also runs offline:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-compare-index \
  --release-gate-compare-query <search-text> \
  --format json
```

The command reads only local
`release-gate-retention-compare.redacted.json` files under
`out/m365/teams-sharepoint/release-gate-comparisons/` and emits left/right
correlation ID, timestamp, status, difference counts and local report/JSON
paths. `--release-gate-compare-left`, `--release-gate-compare-right`,
`--release-gate-compare-status` and `--release-gate-compare-query` filter the
index. It performs no Graph request, tenant write or delete and reads no
SharePoint file content.

A versionable index evidence artifact is written offline with the same
filters:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-compare-index-artifact \
  --release-gate-compare-query <search-text> \
  --format json
```

Without explicit paths, the command writes
`release-gate-retention-compare-index.redacted.md` and
`release-gate-retention-compare-index.redacted.json` under
`out/m365/teams-sharepoint/release-gate-comparison-indexes/<filter>/`.
`--release-gate-compare-index-output` and
`--release-gate-compare-index-json-output` set custom targets. The export
remains redacted and offline.

The full offline audit pack bundles the retention list, comparison, comparison
index and manifest into one target directory:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-retention-audit-pack \
  --release-gate-compare-left <left-correlation-id> \
  --release-gate-compare-right <right-correlation-id> \
  --format json
```

Without an explicit target directory, the command writes under
`out/m365/teams-sharepoint/release-gate-audit-packs/<filter>/`.
`--release-gate-audit-pack-dir` sets a custom target directory. The package
contains `release-gate-retention-audit-pack.redacted.md/json`,
`release-gate-retention-list.redacted.md/json`, the comparison under
`comparisons/<left>__<right>/` and the filtered comparison index. It reads only
local redacted retention and evidence artifacts and performs no Graph request,
tenant write, delete or SharePoint content read.

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-evidence \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-require-runtime-artifacts \
  --format json
```

The exporter performs no Graph request. It reads the local redacted artifacts
`runtime-certificate-expiry-monitor.redacted.json`,
`runtime-env-bootstrap.redacted.json`,
`runtime-smoke.redacted.json`, `runtime-metadata.redacted.json`,
`mcp-smoke-suite.redacted.json` and
`mcp-smoke-leftover-cleanup.redacted.json` and writes
`out/m365/teams-sharepoint/release-gate-evidence.redacted.md`. Optional
runtime artifacts can be attached with
`--release-gate-runtime-certificate-expiry-artifact`,
`--release-gate-runtime-env-bootstrap-artifact`,
`--release-gate-runtime-smoke-artifact` and
`--release-gate-runtime-metadata-artifact`; when they are missing, the runtime
steps outside the release-gate batch are documented as `NOT_ATTACHED`. In the
release-gate batch, export blocks when runtime artifacts are missing.

Before live steps, `release-gate-run` internally uses the offline
`mcp-inventory-smoke` and offline `runtime-env-bootstrap`:
`mcp-inventory-smoke` checks the metadata-only interface-inventory boundary
without Graph or credential access and writes
`out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json`. Tenant and
runtime client IDs are resolved from the non-secret runtime-smoke state only as
child-process environment, and local certificate/private-key paths are passed
only to the live child processes. The runner writes
`out/m365/teams-sharepoint/runtime-env-bootstrap.redacted.json` and attaches it
to `release-gate-evidence` and the artifact index. The artifact
contains no tenant ID, client ID, certificate thumbprints, certificate body,
private-key data, tokens or secret values.

## Completion Rule

After an approved batch, the agent is done only when all approved actions have
run, checks are green, local branches are cleaned up and the target branch is
synchronized. If another agent-executable step is still open, the agent keeps
working. If owner input is required, the agent names the exact next copyable
approval text.
