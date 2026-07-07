# M365 Matter Access Delegation

Status: contract-first, offline, no live tenant action
Last content update: 2026-07-07

## Purpose

This page defines how NaC binds matter visibility to the assigned notary team
and how deputy access is planned as a timeboxed, reasoned and auditable
exception. Storage remains Teams/SharePoint through Microsoft Graph REST v1.0.
Legacy SharePoint APIs, SDKs, PnP, Graph Beta, SharePoint file-content reads
and secret storage remain blocked.

The machine-readable contract is
[workflows/contracts/m365-matter-access-delegation.contract.json](../../../workflows/contracts/m365-matter-access-delegation.contract.json).

## Decision

The MVP does not use one blanket team for all staff and does not create a team
per matter. The default is one private team per notary team. A matter points in
`Akten` to `NotarTeam`, `FederfuehrenderNotar` and `Sachbearbeitung`.
Deputy access is an exception and is represented in `Vertretungsfreigaben`:

- `Reason` is required.
- `ValidFrom` and `ValidUntil` are required.
- `ValidUntil` must be after `ValidFrom`.
- `ApprovedBy` and `AuditCorrelationId` are required.
- `Status` stays limited to `Aktiv`, `Abgelaufen` or `Widerrufen`.
- `GrantedRole` stays limited to `NotarVertretung`,
  `SachbearbeitungVertretung` or `NurLesen`.

The first implementation does not mutate Teams membership and does not apply
SharePoint item permissions. It only renders the offline plan through:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-plan --format json
```

## MCP Boundary

The leading runtime edge remains `teams-sharepoint-data-mcp`.
`grant_request` plans a future write to `Vertretungsfreigaben`.
`audit_append` plans the matching evidence in `AuditJournalLite`.
`case_get` reads matter metadata, and `document_list` reads document pointers
only.

All tools stay behind role, matter and purpose binding. Write-side deputy plans
also need explicit write approval and a future owner gate before productive
apply.

## Graph REST Plan

`matter-access-plan` renders six request-plan operations per workspace:

| Operation | List | Method | Purpose |
| --- | --- | --- | --- |
| `read_primary_matter_assignment` | `Akten` | `GET` | read primary assignment |
| `read_active_deputy_grants` | `Vertretungsfreigaben` | `GET` | check active deputy access |
| `write_deputy_grant_request` | `Vertretungsfreigaben` | `POST` | plan a future grant |
| `revoke_deputy_grant` | `Vertretungsfreigaben` | `PATCH` | plan a future revocation |
| `append_access_audit_event` | `AuditJournalLite` | `POST` | plan evidence |
| `read_delegation_audit_events` | `AuditJournalLite` | `GET` | read audit metadata |

All paths stay under `/sites/{site-id}/...`, execute no Graph requests now and
read no SharePoint file content.

## Blocked

- blanket matter visibility for all staff,
- permanent deputy access without expiry,
- deputy access without reason or audit,
- automated approval by agents,
- Teams or group membership mutation without owner gate,
- SharePoint file content or raw matter payloads in this contract,
- legacy SharePoint REST, CSOM, PnP, Microsoft Graph SDK or Graph Beta.
