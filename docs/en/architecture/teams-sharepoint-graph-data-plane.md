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

The provisioner lives at
[scripts/provision_teams_sharepoint_graph.py](../../../scripts/provision_teams_sharepoint_graph.py).

It supports this workflow:

```bash
python3 scripts/provision_teams_sharepoint_graph.py plan
python3 scripts/provision_teams_sharepoint_graph.py privileged-plan
python3 scripts/provision_teams_sharepoint_graph.py apply --owner-approved
python3 scripts/provision_teams_sharepoint_graph.py drift
python3 scripts/provision_teams_sharepoint_graph.py export
```

`plan` and `privileged-plan` must work without Microsoft access.
`privileged-plan` uses
[deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json](../../../deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json)
and the non-secret provisioned state to expose the next iteration as a Graph
REST operation list before any live apply. `apply`, `drift` and `export` need
environment variables for tenant, app and credential. The provisioner does not
store tokens, secret values or raw data in the repository.

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
and the Python module `nac_m365_graph.mcp_runtime`. It does not execute Graph
requests yet, stores no tokens or secrets and reads no files. It only creates
auditable Graph REST request plans behind an open role, matter and purpose
gate. The central operating edge exposes the safe tool manifest without
Microsoft 365 access:

```bash
nac m365 teams-sharepoint mcp-manifest --format json
```

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
6. Then extend `teams-sharepoint-data-mcp` from request planning to owner-gated live execution.
