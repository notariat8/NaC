# M365-Mandatszugriffsdelegation

Status: Contract-first, offline, keine Live-Tenant-Aktion
Letzte Inhaltsänderung: 2026-07-07

## Zweck

Diese Seite definiert, wie NaC die Sichtbarkeit einer Akte an das zuständige
Notariatsteam bindet und wie Vertretungen zeitlich begrenzt, begründet und
auditierbar geplant werden. Die Datenhaltung bleibt Teams/SharePoint über
Microsoft Graph REST v1.0. Alte SharePoint-APIs, SDKs, PnP, Graph Beta,
SharePoint-Dateiinhaltslesezugriffe und Secret-Speicherung bleiben gesperrt.

Der maschinenlesbare Vertrag liegt in
[workflows/contracts/m365-matter-access-delegation.contract.json](../../../workflows/contracts/m365-matter-access-delegation.contract.json).

## Entscheidung

Der MVP nutzt keine allgemeine Freigabe für alle Mitarbeitenden und kein Team
pro Akte. Standard ist ein privates Team pro Notariatsteam. Die Akte verweist in
`Akten` auf `NotarTeam`, `FederfuehrenderNotar` und `Sachbearbeitung`.
Vertretung ist eine Ausnahme und wird in `Vertretungsfreigaben` abgebildet:

- `Reason` ist Pflicht.
- `ValidFrom` und `ValidUntil` sind Pflicht.
- `ValidUntil` muss nach `ValidFrom` liegen.
- `ApprovedBy` und `AuditCorrelationId` sind Pflicht.
- `Status` bleibt auf `Aktiv`, `Abgelaufen` oder `Widerrufen` begrenzt.
- `GrantedRole` bleibt auf `NotarVertretung`,
  `SachbearbeitungVertretung` oder `NurLesen` begrenzt.

Die erste Implementierung führt keine Teams-Mitgliedschaftsänderung und keine
SharePoint-Item-Permissions aus. Sie rendert nur den Offline-Plan über:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-plan --format json
```

Der redigierte Offline-Nachweis für diesen Plan läuft über:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-smoke --mcp-smoke-workspace-id notary_team_01 --format json
```

`matter-access-smoke` schreibt standardmäßig
`out/m365/teams-sharepoint/matter-access-delegation-smoke.redacted.json`.
Das Artefakt enthält nur Counts, Aktionsnamen, Correlation-ID und
Privacy-Attestierungen. Es speichert keine Mandats-Rohdaten, keine Tokens,
keine SharePoint-Dateiinhalte und keine konkreten Graph-Pfade. Im
`release-gate-run` wird der Smoke vor den Live-Runtime-Schritten ausgeführt und
als optionaler Evidence-Step an `release-gate-evidence` und den Artifact-Index
angehängt.

## MCP-Grenze

Die führende Runtime-Kante bleibt `teams-sharepoint-data-mcp`.
`grant_request` plant später einen Schreibvorgang in `Vertretungsfreigaben`.
`audit_append` plant den passenden Nachweis in `AuditJournalLite`.
`case_get` liest Aktenmetadaten, `document_list` liest nur Dokument-Pointer.

Alle Werkzeuge bleiben hinter Rollen-, Akten- und Zweckbindung. Schreibende
Vertretungspläne brauchen zusätzlich eine explizite Write-Approval und vor
produktivem Apply ein Owner-Gate.

## Graph REST Plan

`matter-access-plan` rendert pro Workspace sechs Request-Plan-Operationen:

| Operation | Liste | Methode | Zweck |
| --- | --- | --- | --- |
| `read_primary_matter_assignment` | `Akten` | `GET` | Primärzuständigkeit lesen |
| `read_active_deputy_grants` | `Vertretungsfreigaben` | `GET` | aktive Vertretung prüfen |
| `write_deputy_grant_request` | `Vertretungsfreigaben` | `POST` | künftige Freigabe planen |
| `revoke_deputy_grant` | `Vertretungsfreigaben` | `PATCH` | künftigen Widerruf planen |
| `append_access_audit_event` | `AuditJournalLite` | `POST` | Nachweis planen |
| `read_delegation_audit_events` | `AuditJournalLite` | `GET` | Audit-Metadaten lesen |

Alle Pfade bleiben unter `/sites/{site-id}/...`, führen jetzt keine Graph
Requests aus und lesen keine SharePoint-Dateiinhalte.

## Gesperrt

- allgemeine Akteneinsicht für alle Mitarbeitenden,
- dauerhafte Vertretung ohne Ablauf,
- Vertretung ohne Grund oder Audit,
- automatische Freigabe durch Agenten,
- Teams- oder Gruppenmitgliedschaftsänderung ohne Owner-Gate,
- SharePoint-Dateiinhalte oder Mandats-Rohdaten in diesem Contract,
- Legacy SharePoint REST, CSOM, PnP, Microsoft Graph SDK oder Graph Beta.
