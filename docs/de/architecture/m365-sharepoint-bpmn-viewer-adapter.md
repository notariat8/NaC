# M365 SharePoint BPMN Viewer Adapter

## Zweck

Der Adapter liefert eine sichtbare, ausschließlich lesende Vorgangsansicht für die synthetische Testumgebung `notary_team_01`. Die Oberfläche ist ein paketierbares SharePoint Framework Web Part mit **SPFx 1.23.2**, **Heft** und `bpmn-js/lib/Viewer`. Sie läuft als `SharePointWebPart` und `TeamsTab`.

Der Modus ist **viewer-only**. Er modelliert oder speichert keine BPMN-Datei, startet keinen Workflow, schreibt nicht nach SharePoint und verarbeitet keine echten Mandatsdaten.

## Daten- und Identitätsgrenze

Die dynamische Datenkante ist fest auf folgenden Pfad begrenzt:

```text
SPFx/Teams -> AadHttpClient -> NaC M365 BFF -> Microsoft Graph REST v1.0
```

Das Webpart fordert ausschließlich den delegierten BFF-Scope `Matter.Read` für die Ressource `api://funktion8.de/nac-bff` an. Der feste MVP-Endpunkt ist `https://func-nac-bff-test-funktion8.azurewebsites.net`. Das Webpart erhält keine Microsoft-Graph-Berechtigung, enthält keinen `MSGraphClient` und kennt keine Site-, Listen- oder Graph-Pfade.

Der BFF validiert Entra-Token, Tenant, Audience, Scope, Workspace, Akte, Zweck, Rolle und aktive Vertretung serverseitig. An den Browser geht nur das redigierte synthetische DTO. BPMN-XML bleibt ein hashgebundenes Paket-Asset; Vorgang, Status, Aufgaben und Frist kommen nicht aus einer statischen Paket-Fixture.

## Paket- und Buildvertrag

Der Paketquellbaum liegt unter `spfx/nac-bpmn-viewer`. `package-lock.json` ist verpflichtender Teil des Quellvertrags. Der reproduzierbare Build verwendet:

```bash
npm ci
npm run build
```

`npm run build` führt den Heft-Produktionsbuild und `heft package-solution --production` aus. Das erzeugte Paket liegt unter `sharepoint/solution/nac-bpmn-viewer.sppkg`.

`node_modules`, `lib`, `dist`, `temp` und `sharepoint/solution` bleiben ignoriert und untracked. Rekursive Source-Scans betreten diese Pfade nicht.

## Bereitstellungsgrenze

Die App-Catalog-Bereitstellung ist bis zur erfolgreichen BFF-Aktivierung **DEFERRED**. Erst das konsolidierte Aktivierungs-Gate darf Upload und **site-scoped** Installation ausschließlich für `notary_team_01` freigeben. `skipFeatureDeployment=false` erzwingt dann die Site-Installation; tenant-weite Bereitstellung und jede Installation in einem anderen Workspace bleiben gesperrt.

Die Paketdefinition enthält genau eine Web-API-Anforderung: `NaC M365 BFF` / `Matter.Read`. Zusätzliche delegierte Scopes, Graph-Rechte, produktive Daten, weitere Sites und Schreibzugriffe sind nicht erlaubt.

## UI- und DOM-Vertrag

- `data-nac-component="test-workspace"` kennzeichnet die Testoberfläche.
- `Synthetische Testdaten` kennzeichnet die Datenklasse sichtbar.
- `Keine Mandatsdaten` bestätigt die Laufzeitgrenze.
- Ein abweichender `workspaceId` schlägt geschlossen mit `Workspace nicht freigegeben.` fehl.
- Fehlerhafte, zu große oder abweichende BFF-Antworten werden nicht gerendert.

## Verträge und Nachweis

Verbindlich sind der [Viewer-Adapter-Vertrag](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json), das [SPFx-Paketartefakt](../../../deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json) und die [Runtime-Readiness](../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.runtime-readiness.json).

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
python3 -m unittest tests.test_m365_bpmn_viewer_runtime_readiness
python3 -m unittest tests.test_m365_sharepoint_bpmn_viewer_adapter
```
