# Teams-SharePoint-Graph-Datenebene

Status: finale MVP-Datenebenenentscheidung
Letzte inhaltliche Anpassung: 2026-07-06

## Zweck

Diese Seite legt die erste Microsoft-365-Datenhaltung für NaC fest. Der MVP
nutzt nicht eine isolierte SharePoint-Site als Startpunkt, sondern ein
Microsoft Teams Team pro Notar-Team. Dieses Team bringt eine
Microsoft-365-Gruppe und eine verbundene SharePoint-Team-Site mit. NaC nutzt
diese SharePoint-Site für Listen, Dokumentbibliotheken und Dokument-Pointer.

OCI/ATP ist für den MVP nicht mehr aktive Datenhaltung. Die frühere OCI-/ATP-
Architektur bleibt als Legacy-Archiv und Rückholoption erhalten, ist aber kein
Default-Pfad für Provisioning, Runtime, Quality Gate oder Agent-Workflow.

Zugriff und Provisioning laufen ausschließlich über
[Microsoft Graph REST](https://learn.microsoft.com/en-us/graph/overview) oder
über MCP-Server, die intern ebenfalls nur Microsoft Graph REST verwenden. Alte
SharePoint-APIs, CSOM, PnP, Microsoft Graph SDKs und serverseitige
Office-Automation sind für diese Datenebene gesperrt.

Ausnahme: Die CLI for Microsoft 365 darf als owner-gated Admin-Beschleuniger
für Setup, Login, Entra-App-Bootstrap und Graph-Smoke-Tests genutzt werden. Sie
ist keine Runtime-Abhängigkeit und darf im Datenpfad nur `m365 request` gegen
`@graph` beziehungsweise Microsoft Graph v1.0 verwenden. Das konkrete Runbook
liegt unter
[docs/de/runbooks/m365-cli-admin-accelerator.md](../runbooks/m365-cli-admin-accelerator.md).

## Entscheidung

Der MVP nutzt dieses Modell:

```text
Microsoft Teams Team pro Notar-Team
  -> Microsoft-365-Gruppe
    -> SharePoint-Team-Site
      -> Listen, Dokumentbibliotheken, Dateien und Metadaten
```

Für den ersten Piloten werden zwei Arbeitsräume vorgesehen:

- `NaC-Notar-01`
- `NaC-Notar-02`

Jeder Arbeitsraum enthält nur den federführenden Notar und die zugeordnete
Sachbearbeitung. Vertretung wird nicht durch pauschale Freigabe gelöst,
sondern über eine befristete, begründete und auditierte
`Vertretungsfreigaben`-Liste. Eine spätere technische Änderung der
Teammitgliedschaft bleibt owner-gated.

## Warum Teams Zuerst

Teams ist für die Nutzer die natürlichere Arbeitsfläche. Die dahinterliegende
SharePoint-Site bleibt trotzdem die eigentliche Datenhaltung. Microsoft
dokumentiert, dass jedes Team mit einer Microsoft-365-Gruppe verbunden ist und
die Gruppe dieselbe ID wie das Team hat. Die SharePoint-Site der Gruppe ist per
Graph erreichbar, zum Beispiel über `GET /groups/{group-id}/sites/root`.

Das reduziert spätere Reibung:

- Teams liefert Arbeitsraum, Kanäle, Benachrichtigung und Nutzerkontext.
- Die Microsoft-365-Gruppe liefert Mitgliedschaft und Gruppenanker.
- SharePoint liefert Listen, Dokumentbibliotheken, Versionierung und Dateien.
- NaC liefert Rollen-, Akten-, Zweck-, Vertretungs- und Auditlogik.

## MVP-Datenmodell

Das deklarative Schema liegt in
[deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json](../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json).

Jede verbundene SharePoint-Site bekommt:

| Liste oder Bibliothek | Zweck |
| --- | --- |
| `Akten` | Akten-Metadaten, Vorgangstyp, Status, Frist und NaC-Versionen |
| `Beteiligte` | Beteiligten-Metadaten ohne Ausweisrohdaten |
| `AufgabenFristen` | BPMN-Schritte, Aufgaben, Verantwortliche und Fristen |
| `Vertretungsfreigaben` | befristete Vertretungen mit Grund, Dauer, Freigabe und Audit |
| `AuditJournalLite` | Start-Audit ohne WORM-Anspruch |
| `DokumentRegister` | Dokument-Pointer, Hashes, Versionen und Track-Changes-Status |
| `AktenDokumente` | Dokumentbibliothek für aktennahe Dokumente |
| `Vorlagen` | Dokumentbibliothek für geprüfte Vorlagen |

Wichtig: `AuditJournalLite` ist kein revisionssicheres Endjournal. Es ist ein
Startnachweis. Für echte Unveränderbarkeit bleibt ein späteres append-only
Journal oder ein WORM-fähiger Speicher erforderlich.

Die konkrete Rollen-, Akten- und Vertretungsgrenze ist in
[M365-Mandatszugriffsdelegation](m365-matter-access-delegation.md)
beschrieben. Der Offline-Befehl
`nac m365 teams-sharepoint matter-access-plan --format json` rendert die
Graph-REST-Requestpläne für Primärzuständigkeit, aktive Vertretung,
Vertretungsfreigabe, Widerruf und Audit, ohne Live-Tenant-Aktion.

## BPMN-Viewer-Projektion

Ein späterer
[M365 SharePoint BPMN Viewer Adapter](m365-sharepoint-bpmn-viewer-adapter.md)
darf diese Datenebene als read-only Anzeigeprojektion nutzen. Ziel ist ein
SPFx-Webpart mit `bpmn-js` im viewer-only-Modus, das freigegebene
BPMN-XML-Modelle und geprüfte Prozessregister- oder Aufgaben-Metadaten
anzeigt.

Der Adapter ändert die Datenebenenentscheidung nicht: Microsoft Graph REST
bleibt Pflicht, alte SharePoint-APIs, CSOM, PnP und SDKs bleiben gesperrt.
Der Adapter darf keine BPMN-Modelle schreiben, keine Workflows ausführen und
keine Akten-Dokumentinhalte oder Mandats-Payloads lesen.

Die optionale SharePoint-Oberfläche ist bewusst nicht Teil des
verpflichtenden MVP-Schemas. Sie wird in
[deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json](../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json)
beschrieben und über `nac m365 teams-sharepoint bpmn-viewer-plan --format
json` nur als Plan gerendert. Die Runtime-Readiness für SPFx-Paketierung,
App Catalog und späteren `.bpmn`-Graph-Content-Read wird separat über
`nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json`
geprüft. Ein späterer Apply, App-Catalog-Upload oder Live-Content-Read braucht
ein eigenes Owner-Gate.

## Graph-REST-Grenze

Erlaubt sind nur rohe HTTPS-Aufrufe gegen `https://graph.microsoft.com/v1.0`.
Der Provisioner und spätere MCP-Server dürfen keine SDK-Abstraktion nutzen.

Erlaubte Graph-Endpunkte im MVP:

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

Der `filesFolder`-Aufruf ist wichtig, weil Microsoft dokumentiert, dass die
SharePoint-Site des General Channels nach Team-Erstellung verzögert
provisioniert werden kann und dieser Aufruf die Provisionierung anstoßen kann.

Für Admin-Smoke-Tests darf die CLI for Microsoft 365 nur so verwendet werden:

```bash
m365 request --url "@graph/organization" --method get --output json
```

Gesperrt bleiben `m365 spo`, `@spo`, `@graphbeta` und alle URLs mit
SharePoint-Legacy-REST.

## Berechtigungen

Für den Bootstrap reichen als Zielbild:

- `Team.Create`, wenn NaC Teams anlegen soll,
- `Sites.Manage.All`, um Listen und Spalten in der verbundenen SharePoint-Site
  zu provisionieren.

Optional können für Discovery `Group.Read.All` oder `Team.ReadBasic.All`
erforderlich werden, wenn Teams nicht über bekannte IDs, sondern über Namen
aufgelöst werden sollen.

Für die spätere Runtime ist `Sites.Selected` das Ziel. Das Bootstrap-Recht ist
breit und darf nicht dauerhaft die Runtime-App sein. Nach dem Setup soll eine
separate Runtime-App nur auf die freigegebenen Sites zugreifen.

## Privilegierte Änderungen Über App/API

Nächste Iteration: Standardnutzer arbeiten ohne Microsoft-365-Adminrechte.
Privilegierte Änderungen an Teams, SharePoint-Listen, Site-Permissions,
Mitgliedschaften und Schema laufen über eine kontrollierte Provisioning-App
beziehungsweise eine NaC-API. Für die direkte App-Ownership gelten die
Microsoft-Graph-Grenzen: App-Owner können einzelne Benutzer, der zugehörige
Service Principal oder ein anderer Service Principal sein, aber keine
Entra-Gruppe. Eine kleine Gruppe wie `nac_platform_admins` ist daher die
Governance- und Betriebsgruppe, nicht der direkte `owners/$ref`-Eintrag der
App.

Das ist sicherer als dauerhafte Adminrechte bei normalen Nutzern, ersetzt aber
nicht die fachliche Verantwortung echter Personen. Teams braucht weiterhin
menschliche Team-Owner; Notar- und Vertretungsentscheidungen bleiben
aktenbezogen, begründet, befristet und auditiert. Die App ist der technische
Änderungsweg, nicht die fachliche Freigabe.

Der dedizierte technische Bootstrap-Owner-User `technical_owner_user` darf dabei als
nicht-personenbezogener Erstellungsanker genutzt werden, wenn Microsoft Teams
bei `POST /teams` einen Benutzer in der Owner-Member-Liste verlangt. Dieser
User ist aber kein Ersatz für die Provisioning-App und darf nicht alleiniger
Team-Owner sein, keine dauerhaften Microsoft-365-Adminrollen tragen und vor
produktiver Nutzung braucht die Lizenz-/Nutzungsgrenze eine explizite Prüfung.
Mindestens ein echter lizenzierter menschlicher Team-Owner bleibt Pflicht.

Roadmap-Item für die nächste Iteration:

- dedizierte `NaC M365 Provisioning`-App getrennt von der Runtime-App,
- direkte technische App-Ownership über `technical_owner_user` oder Service Principal,
- Governance und Vier-Augen-Prinzip über `nac_platform_admins`,
- optionaler technischer Bootstrap-Owner-User `technical_owner_user` nur als Erstellungsanker,
- privilegierte Mutationen nur über Graph-REST-API mit Owner-Gate,
- Runtime-App danach nur mit `Sites.Selected` pro freigegebener Site,
- Drift-/Export-Nachweis vor und nach privilegierten Änderungen.

## Provisioning

Die Produktbedienkante läuft über die zentrale `nac`-CLI. Der interne
Kompatibilitäts-Provisioner steht weiterhin unter
[scripts/provision_teams_sharepoint_graph.py](../../../scripts/provision_teams_sharepoint_graph.py),
wird in Produktdokumentation aber nicht als Operator-Kante geführt.

Die CLI unterstützt diese Arbeitsweise:

```bash
python3 scripts/nac.py m365 teams-sharepoint plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-plan --format json
python3 scripts/nac.py m365 teams-sharepoint privileged-apply --owner-approved --format json
python3 scripts/nac.py m365 teams-sharepoint drift --format json
python3 scripts/nac.py m365 teams-sharepoint export --format json
```

`plan` und `privileged-plan` müssen ohne Microsoft-Zugang funktionieren.
`privileged-plan` nutzt
[deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json](../../../deploy/m365/teams-sharepoint/nac-mvp.privileged-change-path.json)
und den nicht-geheimen Provisionierungsstand, um die nächste Iteration vor
jedem Live-Apply als Graph-REST-Operationsliste sichtbar zu machen.
`privileged-apply`, `drift` und `export` brauchen Umgebungsvariablen für
Tenant, App und Credential. Die M365-Schicht speichert keine Tokens, Secrets
oder Rohdaten im Repo.

`runtime-smoke` und `runtime-metadata` verwenden das deklarative MVP-Schema als
Erwartungsquelle. Der Smoke liest mit der Runtime-App nur Site-, Listen- und
Bibliotheksmetadaten über Microsoft Graph REST v1.0 und schlägt fehl, wenn
eine laut Schema erforderliche Liste oder Dokumentbibliothek fehlt. Dadurch
prüft der Smoke Basisrechte über `Sites.Selected` und Schema-Drift, ohne
Listenelemente, Dateien oder Mandatsdaten zu lesen.

## MCP-Grenze

Der spätere Runtime-Server heißt `teams-sharepoint-data-mcp`. Er darf nur
Graph-REST-Endpunkte nutzen und braucht vor jeder schreibenden Aktion das
NaC-Rollen-, Akten- und Zweckgate.

Der erste Skeleton steht als
[workflows/contracts/teams-sharepoint-data-mcp.contract.json](../../../workflows/contracts/teams-sharepoint-data-mcp.contract.json)
und Python-Modul `nac_m365_graph.mcp_runtime` bereit. Der lokale
stdio-Adapter steht in `nac_m365_graph.mcp_stdio`. Er nutzt die
MCP-Protokollversion `2025-11-25`, spricht newline-delimited JSON-RPC über
stdin/stdout und führt noch keine Graph-Aufrufe aus. Der Adapter speichert
keine Tokens oder Secrets und liest keine Dateien. Er erzeugt nur prüfbare
Graph-REST-Request-Pläne hinter einem offenen Rollen-, Akten- und Zweckgate.
Die zentrale Bedienkante zeigt das sichere Tool-Manifest ohne
Microsoft-365-Zugang:

```bash
nac m365 teams-sharepoint mcp-manifest --format json
```

Der lokale MCP-Adapter wird so gestartet:

```bash
nac m365 teams-sharepoint mcp-stdio
```

`mcp-manifest` ist Discovery für Tool-Grenzen. `mcp-stdio` ist die lokale
Runtime-Bedienkante für MCP-Clients wie AIQ/Codex. Der Default bleibt
`request_planning_only`: `tools/call` liefert
`structuredContent.requestPlan` mit Methode, Graph-v1.0-Pfad und Payload,
setzt `executesGraphRequests` auf `false` und gibt Gate-Verstöße als MCP
Tool-Error zurück.

Die Metadaten-Tools `notarial_interface_inventory_list` und
`notarial_interface_boundary_check` bleiben ebenfalls offline. Sie lesen nur
den lokalen NaC-Vertrag zum notariellen Schnittstelleninventar und rufen weder
Microsoft Graph noch BNotK-Systeme auf. Der reproduzierbare Offline-Smoke für
diese Grenze ist:

```bash
nac m365 teams-sharepoint mcp-inventory-smoke --format json
```

Er schreibt standardmäßig
`out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json` und prüft
Inventory-Liste, Boundary-Check für eine metadata-only Operation, Boundary-
Check für eine owner-gated Operation sowie ein geschlossenes Rollen-, Akten-
und Zweckgate. Das Artefakt speichert keine BNotK-HTML-Inhalte, keine XSD-
Rohdaten, keine Credentials, keine Tokens, keine Nachrichten-Payloads und
keine Mandatsdaten. Der owner-gated `release-gate-run` führt diesen
Offline-Smoke vor den Live-Schritten automatisch aus und referenziert das
redigierte Artefakt in `release-gate-evidence`. Bei manuellem
`release-gate-evidence` kann dasselbe Artefakt weiterhin optional mit
`--release-gate-inventory-artifact` referenziert werden.

Die Mandatszugriffs- und Vertretungsfreigabegrenze ist im separaten
[M365-Mandatszugriffsdelegation](m365-matter-access-delegation.md)-Contract
definiert. `matter-access-plan` rendert den Request-Plan ohne Live-Tenant-
Aktion; `matter-access-smoke` erzeugt dazu den redigierten Offline-Nachweis:

```bash
nac m365 teams-sharepoint matter-access-smoke --mcp-smoke-workspace-id notary_team_01 --format json
nac m365 teams-sharepoint matter-access-apply-readiness --mcp-smoke-workspace-id notary_team_01 --format json
nac m365 teams-sharepoint matter-access-apply-request-plan --mcp-smoke-workspace-id notary_team_01 --mcp-smoke-correlation-id <correlation-id> --format json
```

Der Smoke schreibt standardmäßig
`out/m365/teams-sharepoint/matter-access-delegation-smoke.redacted.json`.
Er prüft sechs Request-Plan-Operationen pro Workspace, drei owner-gated
schreibende Vertretungspläne, die request-plan-only MCP-Toolverträge und die
Privacy-Grenze ohne Graph-Ausführung. `release-gate-run` führt ihn vor den
Live-Schritten automatisch aus und hängt das Artefakt als optionalen Evidence-
Step an `release-gate-evidence` und den Artifact-Index an.

`matter-access-apply-readiness` schreibt zusätzlich
`out/m365/teams-sharepoint/matter-access-apply-readiness.redacted.json` und
prüft offline, ob die künftige Apply-Kante für `grant_request` und
`audit_append` owner-gated, write-approved, befristet, begründet und
auditierbar ist. Auch dieses Artefakt wird im `release-gate-run` automatisch
vor den Live-Schritten erzeugt und optional an Evidence und Artifact-Index
angehängt.

`matter-access-apply-request-plan` schreibt den konkreten redigierten
Owner-Apply-Auftrag nach
`out/m365/teams-sharepoint/matter-access-apply-request-plan.redacted.json`.
Der Plan bündelt `grant_request` und `audit_append`, speichert nur Hashes,
Feldnamen, Listenrollen und Privacy-Flags und führt keine Graph Requests oder
SharePoint-Item-Writes aus.

Der erste owner-gated Live-Read-Modus wird explizit gestartet:

```bash
nac m365 teams-sharepoint mcp-stdio --owner-approved --mcp-live-read
```

Dieser Modus braucht die Runtime-Graph-Konfiguration
`M365_RUNTIME_GRAPH_ACCESS_TOKEN` oder `M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE`
beziehungsweise `M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID` und
`M365_RUNTIME_CLIENT_SECRET`. Der bevorzugte Runtime-Pfad nutzt stattdessen
`M365_TENANT_ID`, `M365_RUNTIME_CLIENT_ID`,
`M365_RUNTIME_CLIENT_CERTIFICATE_PATH` und `M365_RUNTIME_CLIENT_KEY_PATH`; bei
verschlüsseltem Schlüssel zusätzlich `M365_RUNTIME_CLIENT_KEY_PASSWORD`. Er
führt nur Graph-REST-`GET` für `case_get` und `document_list` aus.
Write-Tools, Team-/Mitgliedschaftsänderungen, SharePoint-Schemaänderungen und
Dateiinhalt bleiben blockiert. Erfolgreiche Live-Reads liefern neben dem
Request-Plan die Graph-Antwort in `structuredContent.graphResponse`.

Der owner-gated Smoke für diesen Live-Read-Modus läuft nicht über einen
dauerhaften MCP-stdio-Prozess, sondern über einen einzelnen CLI-Aufruf:

```bash
nac m365 teams-sharepoint mcp-live-read-smoke --owner-approved --mcp-smoke-tool case_get --mcp-smoke-case-id <case-id>
```

Der Smoke schreibt standardmäßig nach
`out/m365/teams-sharepoint/mcp-live-read-smoke.redacted.json`. Dieses Artefakt
speichert nur Status, Tool, Workspace, Hash der Case-ID, Request-Plan-Hash,
Antwortform und Zähler. Rohantworten aus Graph, Case-ID im Klartext,
Graph-Pfad, Feldwerte, Tokens, Secrets und Dateiinhalt werden nicht
gespeichert.

Ein positiver Write-Read-Smoke ist bewusst kein dauerhaft freigeschalteter
MCP-Live-Write-Modus. Er läuft als einzelner owner-gated Operator-Befehl:

```bash
nac m365 teams-sharepoint mcp-positive-write-read-smoke --owner-approved
```

Der Befehl plant `case_create` über den MCP-Vertrag, schreibt genau einen
synthetischen `Akten`-Eintrag per Microsoft Graph REST v1.0 und liest dieselbe
synthetische Akte danach mit dem vorhandenen `case_get` Live-Read wieder aus.
Das redigierte Artefakt liegt standardmäßig unter
`out/m365/teams-sharepoint/mcp-positive-write-read-smoke.redacted.json`. Es
speichert keine Roh-Case-ID, keine Rohpayloads, keine Rohantworten, keine
Tokens und keine Datei-Inhalte.

Synthetische Smoke-Akten werden über einen separaten owner-gated Cleanup-Befehl
bereinigt:

```bash
nac m365 teams-sharepoint mcp-smoke-cleanup --owner-approved --mcp-smoke-case-id <case-id>
```

Der Cleanup akzeptiert nur exakte Case-IDs mit dem Präfix
`NAC-SMOKE-WRITE-READ-`, liest vor der Löschung genau einen passenden
`Akten`-Eintrag, löscht diesen Eintrag per Microsoft Graph REST v1.0 `DELETE`
und verifiziert danach, dass kein Treffer mehr gelesen wird. Ungebundene
Listendumps, Prefix-Massenlöschungen, Rohantworten, Tokens und Datei-Inhalte
bleiben blockiert.

Für vollständige Runtime-/MCP-Release-Gates ist `release-gate-run` der
führende One-Shot-Bedienpfad. Für einen isolierten MCP-Komponenten- oder
Diagnoselauf gibt es zusätzlich die Suite:

```bash
nac m365 teams-sharepoint mcp-smoke-suite --owner-approved --mcp-suite-cleanup
```

Die Suite erzeugt eine synthetische Case-ID nur im Prozessspeicher, führt
`case_create` und `case_get` aus und bereinigt dieselbe synthetische Akte bei
gesetztem `--mcp-suite-cleanup` im selben Lauf. Das Suite-Artefakt speichert
ebenfalls nur redigierte Hashes, Status- und Zählerinformationen.

Erste Tool-Grenzen:

- `case_get`
- `case_create`
- `case_update_status`
- `task_create`
- `grant_request`
- `audit_append`
- `document_list`

## Nicht Ziele

Nicht Teil des MVP:

- ein Team pro Akte,
- Private Channel pro Akte,
- Item-Level-Permissions als Standardmodell,
- Teams-Chat-Dateien als fachliche Dokumentenwahrheit,
- Agenten, die Teams, Listen oder Spalten selbst umbauen,
- produktive Mitgliedschaftsänderungen ohne Owner-Gate,
- vollständiger WORM-/Revisionssicherheitsanspruch über SharePoint-Listen.

## Nächste Schritte

1. Contract und Schema im Quality Gate halten.
2. Graph-REST-Provisioner zunächst mit `plan` und Schema-Validierung nutzen.
3. Entra-App und Admin Consent außerhalb des Repos einrichten.
4. Einen ersten Smoke gegen `NaC-Notar-01` ausführen.
5. Application-owned privileged change path für M365 als nächste Iteration bauen.
6. Danach `teams-sharepoint-data-mcp` von lokalem `mcp-stdio` und Request-Planung auf owner-gated Live-Ausführung erweitern.
