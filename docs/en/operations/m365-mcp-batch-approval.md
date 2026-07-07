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

After runtime or MCP changes, the agent renders the complete gate offline:

```bash
python3 scripts/nac.py batch-approval m365 --batch-mode release-gate --workspace-id notary_team_01 --correlation-id <correlation-id> --format json
```

The renderer performs no GitHub or Graph write action. It emits the copyable
owner approval and exactly one leading live command:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-run \
  --owner-approved \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --format json
```

The one-shot runner remains owner-gated and internally covers `runtime-smoke`,
`runtime-metadata`, `mcp-smoke-suite --mcp-suite-cleanup`,
`mcp-smoke-leftover-cleanup --mcp-leftover-dry-run` and
`release-gate-evidence --release-gate-require-runtime-artifacts`.
`runtime-smoke` and `runtime-metadata` are read-only, the MCP Smoke Suite writes
and deletes one synthetic matter, and the leftover dry-run only reads the match
count. `release-gate-evidence` runs offline at the end and reads only local
redacted artifacts. `runtime-smoke` and `runtime-metadata` write their own
redacted runtime artifacts so the completion report can return
`complete_release_gate_artifacts`. The individual commands remain a diagnostic
and fallback path when a runner step must be reproduced in isolation.

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
evidence export, workspace clean state and concrete result in the final
status. The MCP Smoke Suite remains the diagnostic/component path when only
that step must be reproduced in isolation. If a synthetic leftover remains
after the run, the agent must immediately prepare the owner-gated
`mcp-smoke-leftover-cleanup` path.

When `release-gate-run` is used, the runner creates the redacted completion
report in the same owner-gated run. The following offline exporter remains only
for diagnostics or re-exporting existing artifacts:

```bash
python3 scripts/nac.py m365 teams-sharepoint release-gate-evidence \
  --mcp-smoke-workspace-id notary_team_01 \
  --mcp-smoke-correlation-id <correlation-id> \
  --release-gate-require-runtime-artifacts \
  --format json
```

The exporter performs no Graph request. It reads the local redacted artifacts
`runtime-smoke.redacted.json`, `runtime-metadata.redacted.json`,
`mcp-smoke-suite.redacted.json` and
`mcp-smoke-leftover-cleanup.redacted.json` and writes
`out/m365/teams-sharepoint/release-gate-evidence.redacted.md`. Optional
runtime artifacts can be attached with `--release-gate-runtime-smoke-artifact`
and `--release-gate-runtime-metadata-artifact`; when they are missing, the
runtime steps outside the release-gate batch are documented as `NOT_ATTACHED`.
In the release-gate batch, export blocks when runtime artifacts are missing.

## Completion Rule

After an approved batch, the agent is done only when all approved actions have
run, checks are green, local branches are cleaned up and the target branch is
synchronized. If another agent-executable step is still open, the agent keeps
working. If owner input is required, the agent names the exact next copyable
approval text.
