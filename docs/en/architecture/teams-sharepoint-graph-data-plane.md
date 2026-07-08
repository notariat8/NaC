# Teams SharePoint Graph Data Plane

Status: final MVP data-plane decision
Last content update: 2026-07-06

## Purpose

This page defines the first Microsoft 365 data store for NaC. The MVP does not
start with an isolated SharePoint site. It starts with one Microsoft Teams team
per notary team. That team provides a Microsoft 365 group and a connected
SharePoint team site. NaC uses that SharePoint site for lists, document
libraries and document pointers.

OCI/ATP is no longer the active MVP data store. The former OCI/ATP architecture
is kept as a legacy archive and recovery option, but it is not the default path
for provisioning, runtime, quality gates or agent workflows.

Access and provisioning run exclusively through
[Microsoft Graph REST](https://learn.microsoft.com/en-us/graph/overview) or
through MCP servers that also use Microsoft Graph REST internally. Legacy
SharePoint APIs, CSOM, PnP, Microsoft Graph SDKs and server-side Office
automation are blocked for this data plane.

Exception: CLI for Microsoft 365 may be used as an owner-gated admin
accelerator for setup, login, Entra app bootstrap and Graph smoke tests. It is
not a runtime dependency and may only use `m365 request` against `@graph` or
Microsoft Graph v1.0 in the data path. The concrete runbook lives at
[docs/en/runbooks/m365-cli-admin-accelerator.md](../runbooks/m365-cli-admin-accelerator.md).

## Decision

The MVP uses this model:

```text
Microsoft Teams team per notary team
  -> Microsoft 365 group
    -> SharePoint team site
      -> lists, document libraries, files and metadata
```

Two workspaces are planned for the first pilot:

- `NaC-Notar-01`
- `NaC-Notar-02`

Each workspace contains only the lead notary and the assigned clerk. Substitution
is not handled through blanket access. It is handled through a time-limited,
reasoned and audited `Vertretungsfreigaben` list. Later technical changes to
team membership remain owner-gated.

## Why Teams First

Teams is the more natural work surface for users. The connected SharePoint site
still remains the actual data store. Microsoft documents that every team is
associated with a Microsoft 365 group and that the group has the same ID as the
team. The group SharePoint site can be reached through Graph, for example with
`GET /groups/{group-id}/sites/root`.

This reduces later friction:

- Teams provides workspace, channels, notifications and user context.
- The Microsoft 365 group provides membership and group anchor.
- SharePoint provides lists, document libraries, versioning and files.
- NaC provides role, matter, purpose, substitution and audit logic.

## MVP Data Model

The declarative schema lives in
[deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json](../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json).

Each connected SharePoint site receives:

| List or library | Purpose |
| --- | --- |
| `Akten` | matter metadata, case type, status, deadline and NaC versions |
| `Beteiligte` | participant metadata without raw identity-card data |
| `AufgabenFristen` | BPMN steps, tasks, assignees and deadlines |
| `Vertretungsfreigaben` | time-limited substitutions with reason, duration, approval and audit |
| `AuditJournalLite` | starter audit without WORM claim |
| `DokumentRegister` | document pointers, hashes, versions and track-changes state |
| `AktenDokumente` | document library for matter-adjacent documents |
| `Vorlagen` | document library for approved templates |

Important: `AuditJournalLite` is not a final tamper-proof journal. It is starter
evidence. Real immutability still requires a later append-only journal or
WORM-capable storage.

The concrete role, matter and deputy boundary is defined in
[M365 Matter Access Delegation](m365-matter-access-delegation.md). The offline
command `nac m365 teams-sharepoint matter-access-plan --format json` renders
Graph REST request plans for primary assignment, active deputy access, grant,
revocation and audit without live tenant action.

## BPMN Viewer Projection

A later
[M365 SharePoint BPMN Viewer Adapter](m365-sharepoint-bpmn-viewer-adapter.md)
may use this data plane as a read-only display projection. The target is an
SPFx web part with `bpmn-js` in viewer-only mode that shows approved BPMN XML
models and reviewed process-register or task metadata.

The adapter does not change the data-plane decision: Microsoft Graph REST
remains mandatory, and legacy SharePoint APIs, CSOM, PnP and SDKs remain
blocked. The adapter must not write BPMN models, execute workflows or read
matter document contents or mandate payloads.

The optional SharePoint surface is deliberately not part of the required MVP
schema. It is described in
[deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json](../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json)
and rendered only as a plan through `nac m365 teams-sharepoint
bpmn-viewer-plan --format json`. Runtime readiness for SPFx packaging, the App
Catalog and the later `.bpmn` Graph content read is checked separately with
`nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json`. A
later apply, App Catalog upload or live content read needs a separate owner
gate.

## Graph REST Boundary

Only raw HTTPS calls against `https://graph.microsoft.com/v1.0` are allowed.
The provisioner and later MCP servers must not use an SDK abstraction.

Allowed Graph endpoints in the MVP:

- `POST /teams`
- `GET /teams/{team-id}`
- `GET /teams/{team-id}/channels`
- `GET /teams/{team-id}/channels/{channel-id}/filesFolder`
- `GET /groups/{group-id}/sites/root`
- `GET /sites/{site-id}/lists`
- `POST /sites/{site-id}/lists`
- `GET /sites/{site-id}/lists/{list-id}/columns`
- `POST /sites/{site-id}/lists/{list-id}/columns`
- `GET /sites/{site-id}/drives`

The `filesFolder` call matters because Microsoft documents that the SharePoint
site of the general channel can be delayed after team creation and that this
call can trigger provisioning.

For admin smoke tests, CLI for Microsoft 365 may only be used like this:

```bash
m365 request --url "@graph/organization" --method get --output json
```

`m365 spo`, `@spo`, `@graphbeta` and all URLs with SharePoint legacy REST remain
blocked.

## Permissions

For bootstrap, the target permissions are:

- `Team.Create`, when NaC should create teams,
- `Sites.Manage.All`, to provision lists and columns in the connected
  SharePoint site.

For discovery, `Group.Read.All` or `Team.ReadBasic.All` may be required if
teams are resolved by name instead of known IDs.

For later runtime access, `Sites.Selected` is the target. The bootstrap
permission is broad and must not become the long-lived runtime app. After setup,
a separate runtime app should access only the approved sites.

## Privileged Changes Through App/API

Next iteration: standard users work without Microsoft 365 admin permissions.
Privileged changes to Teams, SharePoint lists, site permissions, memberships and
schema run through a controlled provisioning app or NaC API. Direct app
ownership follows the Microsoft Graph boundary: app owners can be individual
users, the associated service principal or another service principal, but not an
Entra group. A small group such as `nac_platform_admins` is therefore the
governance and operations group, not the direct `owners/$ref` entry of the app.

This is safer than permanent admin permissions for standard users, but it does
not replace human subject-matter responsibility. Teams still needs human team
owners. Notarial and substitution decisions remain matter-bound, reasoned,
time-limited and audited. The app is the technical change path, not the
subject-matter approval.

The dedicated technical bootstrap owner user `technical_owner_user` may be used as a
non-personal creation anchor when Microsoft Teams requires a user in the owner
member list for `POST /teams`. This user is not a replacement for the
provisioning app and must not be the sole team owner, must not hold permanent
Microsoft 365 admin roles, and needs an explicit license/usage-boundary review
before production use. At least one real licensed human team owner remains
mandatory.

Roadmap item for the next iteration:

- dedicated `NaC M365 Provisioning` app separate from the runtime app,
- direct technical app ownership through `technical_owner_user` or a service principal,
- governance and four-eyes control through `nac_platform_admins`,
- optional technical bootstrap owner user `technical_owner_user` only as a creation anchor,
- privileged mutations only through a Graph REST API with owner gate,
- runtime app then limited to `Sites.Selected` per approved site,
- drift and export evidence before and after privileged changes.

## Provisioning

The product operating edge runs through the central `nac` CLI. The internal
compatibility provisioner still lives at
[scripts/provision_teams_sharepoint_graph.py](../../../scripts/provision_teams_sharepoint_graph.py),
but product documentation does not present it as the operator edge.

The CLI supports this workflow:

```bash
python3 scripts/nac.py m365 teams-sharepoint plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-apply --owner-approved --format json
python3 scripts/nac.py m365 teams-sharepoint drift --format json
python3 scripts/nac.py m365 teams-sharepoint export --format json
```

`plan` and `privileged-plan` must work without Microsoft access.
`privileged-plan` uses
[deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json](../../../deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json)
and the non-secret provisioned state to expose the next iteration as a Graph
REST operation list before any live apply. `privileged-apply`, `drift` and
`export` need environment variables for tenant, app and credential. The M365
layer does not store tokens, secret values or raw data in the repository.

`runtime-smoke` and `runtime-metadata` use the declarative MVP schema as the
expectation source. The smoke reads only site, list and library metadata with
the runtime app through Microsoft Graph REST v1.0 and fails when a list or
document library required by the schema is missing. This verifies
`Sites.Selected` baseline access and schema drift without reading list items,
files or matter data.

## MCP Boundary

The later runtime server is `teams-sharepoint-data-mcp`. It may only use Graph
REST endpoints and needs the NaC role, matter and purpose gate before every
write action.

The first skeleton lives in
[workflows/contracts/teams-sharepoint-data-mcp.contract.json](../../../workflows/contracts/teams-sharepoint-data-mcp.contract.json)
and the Python module `nac_m365_graph.mcp_runtime`. The local stdio adapter
lives in `nac_m365_graph.mcp_stdio`. It uses MCP protocol version `2025-11-25`,
speaks newline-delimited JSON-RPC over stdin/stdout and does not
execute Graph requests yet. The adapter stores no tokens or secrets and reads
no files. It only creates auditable Graph REST request plans behind an open
role, matter and purpose gate. The central operating edge exposes the safe tool
manifest without Microsoft 365 access:

```bash
nac m365 teams-sharepoint mcp-manifest --format json
```

The local MCP adapter starts with:

```bash
nac m365 teams-sharepoint mcp-stdio
```

`mcp-manifest` is discovery for tool boundaries. `mcp-stdio` is the local
runtime edge for MCP clients such as AIQ/Codex. The default remains
`request_planning_only`: `tools/call` returns `structuredContent.requestPlan`
with method, Graph v1.0 path and payload, sets `executesGraphRequests` to
`false` and returns gate violations as MCP tool errors.

The metadata tools `notarial_interface_inventory_list` and
`notarial_interface_boundary_check` also remain offline. They only read the
local NaC contract for the notarial interface inventory and call neither
Microsoft Graph nor BNotK systems. The repeatable offline smoke for this
boundary is:

```bash
nac m365 teams-sharepoint mcp-inventory-smoke --format json
```

By default, it writes
`out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json` and checks the
inventory list, a boundary check for a metadata-only operation, a boundary
check for an owner-gated operation and a closed role, matter and purpose gate.
The artifact stores no BNotK HTML content, raw XSD data, credentials, tokens,
message payloads or matter data. `release-gate-evidence` can optionally
reference this redacted artifact with `--release-gate-inventory-artifact` in
manual exports. The owner-gated `release-gate-run` executes this offline smoke
automatically before live steps and references the redacted artifact in
`release-gate-evidence`.

The matter visibility and deputy-access boundary is defined in the separate
[M365 Matter Access Delegation](m365-matter-access-delegation.md) contract.
`matter-access-plan` renders the request plan without live tenant action;
`matter-access-smoke` creates the matching redacted offline evidence:

```bash
nac m365 teams-sharepoint matter-access-smoke --mcp-smoke-workspace-id notary_team_01 --format json
nac m365 teams-sharepoint matter-access-apply-readiness --mcp-smoke-workspace-id notary_team_01 --format json
nac m365 teams-sharepoint matter-access-apply-request-plan --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
nac m365 teams-sharepoint matter-access-apply-smoke --owner-approved --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
```

By default, the smoke writes
`out/m365/teams-sharepoint/matter-access-delegation-smoke.redacted.json`. It
checks six request-plan operations per workspace, three owner-gated write-side
deputy plans, the request-plan-only MCP tool contracts and the privacy boundary
without Graph execution. `release-gate-run` executes it automatically before
the live steps and attaches the artifact as optional evidence to
`release-gate-evidence` and the artifact index.

`matter-access-apply-readiness` also writes
`out/m365/teams-sharepoint/matter-access-apply-readiness.redacted.json` and
checks offline whether the future apply edge for `grant_request` and
`audit_append` is owner-gated, write-approved, timeboxed, reasoned and
auditable. `release-gate-run` also creates this artifact automatically before
live steps and attaches it optionally to evidence and the artifact index.

`matter-access-apply-request-plan` writes the concrete redacted owner-apply
request to
`out/m365/teams-sharepoint/matter-access-apply-request-plan.redacted.json`.
The plan bundles `grant_request` and `audit_append`, stores only hashes, field
names, list roles and privacy flags, and executes no Graph requests or
SharePoint item writes.

`matter-access-apply-smoke` is the owner-gated live smoke. It writes a
synthetic timeboxed deputy grant through `grant_request`, appends a synthetic
audit event through `audit_append`, reads both items back and deletes them in
the same run. The smoke is limited to `NAC-SMOKE-GRANT-` and
`NAC-SMOKE-MATTER-` and stores only hashes, request shapes, counts, cleanup
status and privacy flags in the artifact.

The first owner-gated live-read mode starts explicitly:

```bash
nac m365 teams-sharepoint mcp-stdio --owner-approved --mcp-live-read
```

This mode needs the runtime Graph configuration
`M365_RUNTIME_GRAPH_ACCESS_TOKEN` or `M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE`, or
`M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID` and `M365_RUNTIME_CLIENT_SECRET`.
The preferred runtime path uses `M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID`,
`M365_RUNTIME_CLIENT_CERTIFICATE_PATH` and `M365_RUNTIME_CLIENT_KEY_PATH`
instead; for an encrypted key it also uses
`M365_RUNTIME_CLIENT_KEY_PASSWORD`. It executes only Graph REST `GET` for
`case_get` and `document_list`. Write tools, team or membership mutations,
SharePoint schema changes and file content remain blocked. Successful live
reads return the request plan and the Graph response in
`structuredContent.graphResponse`.

The owner-gated smoke for this live-read mode does not run through a long-lived
MCP stdio process. It uses a single CLI invocation:

```bash
nac m365 teams-sharepoint mcp-live-read-smoke --owner-approved --mcp-smoke-tool case_get --mcp-smoke-case-id <case-id>
```

By default, the smoke writes
`out/m365/teams-sharepoint/mcp-live-read-smoke.redacted.json`. This artifact
stores only status, tool, workspace, case-id hash, request-plan hash, response
shape and counters. Raw Graph responses, cleartext case IDs, Graph paths, field
values, tokens, secrets and file content are not stored.

A positive write-read smoke is deliberately not a permanently enabled MCP live
write mode. It runs as a single owner-gated operator command:

```bash
nac m365 teams-sharepoint mcp-positive-write-read-smoke --owner-approved
```

The command plans `case_create` through the MCP contract, writes exactly one
synthetic `Akten` item through Microsoft Graph REST v1.0 and then reads the
same synthetic matter through the existing `case_get` live read. The redacted
artifact is written by default to
`out/m365/teams-sharepoint/mcp-positive-write-read-smoke.redacted.json`. It
stores no raw case ID, raw payloads, raw responses, tokens or file content.

Synthetic smoke matters are removed through a separate owner-gated cleanup
command:

```bash
nac m365 teams-sharepoint mcp-smoke-cleanup --owner-approved --mcp-smoke-case-id <case-id>
```

Cleanup accepts only exact case IDs with the `NAC-SMOKE-WRITE-READ-` prefix,
reads exactly one matching `Akten` item before deletion, deletes that item
through Microsoft Graph REST v1.0 `DELETE` and verifies afterwards that no
match is returned. Unbounded list dumps, prefix mass deletion, raw responses,
tokens and file content remain blocked.

For full runtime/MCP release gates, `release-gate-run` is the leading one-shot
operating path. For an isolated MCP component or diagnostic run, the suite is
available as well:

```bash
nac m365 teams-sharepoint mcp-smoke-suite --owner-approved --mcp-suite-cleanup
```

The suite creates a synthetic case ID only in process memory, executes
`case_create` and `case_get`, and cleans up the same synthetic matter in the
same run when `--mcp-suite-cleanup` is set. The suite artifact also stores only
redacted hashes, status and counter information.

Initial tool boundaries:

- `case_get`
- `case_create`
- `case_update_status`
- `task_create`
- `grant_request`
- `audit_append`
- `document_list`

## Non-Goals

Not part of the MVP:

- one team per case,
- private channel per case,
- item-level permissions as the default model,
- Teams chat files as subject-matter document truth,
- agents that mutate teams, lists or columns by themselves,
- productive membership changes without owner gate,
- a full WORM or audit-proof claim through SharePoint lists.

## Next Steps

1. Keep contract and schema in the quality gate.
2. Use the Graph REST provisioner first for `plan` and schema validation.
3. Configure the Entra app and admin consent outside the repository.
4. Run a first smoke against `NaC-Notar-01`.
5. Build the application-owned privileged M365 change path as the next iteration.
6. Then extend `teams-sharepoint-data-mcp` from local `mcp-stdio` and request planning to owner-gated live execution.
