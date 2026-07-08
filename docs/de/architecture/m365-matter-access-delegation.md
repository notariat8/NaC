# M365-Mandatszugriffsdelegation

Status: Contract-first, offline, keine Live-Tenant-Aktion
Letzte Inhaltsänderung: 2026-07-08

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

Die spätere Apply-Grenze für zeitbegrenzte Vertretungsfreigaben wird separat
ohne Live-Apply geprüft:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-readiness --mcp-smoke-workspace-id notary_team_01 --format json
```

Ein konkreter redigierter Apply-Request-Plan für eine spätere
owner-gated Freigabe wird weiterhin ohne Live-Apply gerendert:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-request-plan --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
```

Negative Apply-Policy-Fälle werden offline ohne Microsoft-Graph-Aufruf geprüft:

```bash
python3 scripts/nac.py m365 teams-sharepoint matter-access-apply-policy-smoke --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
```

`matter-access-smoke` schreibt standardmäßig
`out/m365/teams-sharepoint/matter-access-delegation-smoke.redacted.json`.
Das Artefakt enthält nur Counts, Aktionsnamen, Correlation-ID und
Privacy-Attestierungen. Es speichert keine Mandats-Rohdaten, keine Tokens,
keine SharePoint-Dateiinhalte und keine konkreten Graph-Pfade. Im
`release-gate-run` wird der Smoke vor den Live-Runtime-Schritten ausgeführt und
als optionaler Evidence-Step an `release-gate-evidence` und den Artifact-Index
angehängt.

`matter-access-apply-readiness` schreibt standardmäßig
`out/m365/teams-sharepoint/matter-access-apply-readiness.redacted.json`. Das
Artefakt prüft, ob `grant_request` und `audit_append` als künftige
owner-gated Graph-REST-Schreibkante bereit sind: explizite Write-Approval,
Rollen-/Akten-/Zweckgate, Grund, Gültigkeitsfenster, Approver,
Audit-Correlation und Privacy-Grenze. Es führt keine Graph Requests aus,
schreibt keine SharePoint-Items und speichert keine konkreten Graph-Pfade.

`matter-access-apply-request-plan` schreibt standardmäßig
`out/m365/teams-sharepoint/matter-access-apply-request-plan.redacted.json`.
Das Artefakt bündelt die geplanten MCP-Schreibkanten `grant_request` und
`audit_append` als späteren Owner-Apply-Auftrag. Es speichert nur Hashes,
Feldnamen, Listenrollen und Privacy-Flags: keine konkreten Graph-Pfade, keine
Graph-Rohantworten, keine Tokens, keine Nutzerdaten im Klartext und keine
Mandats-Payloads. Der Befehl führt keine Graph Requests aus und schreibt keine
SharePoint-Items.

`matter-access-apply-policy-smoke` schreibt standardmäßig
`out/m365/teams-sharepoint/matter-access-apply-policy-smoke.redacted.json`.
Das Artefakt prüft negative Apply-Fälle: fehlende Begründung, abgelaufene
Vertretung, falscher Workspace, fehlendes Cleanup und fehlender
Audit-Readback. Der Smoke nutzt nur einen Fake-Graph-Client, führt keine echten
Graph Requests aus, schreibt keine SharePoint-Items und speichert keine
konkreten Graph-Pfade, Rohantworten, Nutzerdaten, Gründe, Tokens oder
Mandats-Payloads.

`matter-access-apply-smoke` ist die vorbereitete owner-gated Live-Kante für
eine echte synthetische Vertretungsfreigabe. Der Befehl schreibt nur
synthetische Items mit `NAC-SMOKE-GRANT-` und `NAC-SMOKE-MATTER-` in
`Vertretungsfreigaben` und `AuditJournalLite`, liest genau diese Items zurück
und löscht sie im selben Lauf wieder. Das Artefakt
`out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json` speichert
nur Hashes, Feldnamen, Counts, Cleanup-Status und Privacy-Flags; konkrete
Graph-Pfade, Graph-Rohantworten, Nutzerdaten, Gründe, Tokens und Secrets
werden nicht gespeichert. Ohne explizites `--owner-approved` ist der Befehl
blockiert.

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
