# M365 SharePoint BPMN Viewer Adapter

## Zweck

Der Adapter liefert eine sichtbare, ausschließlich lesende Vorgangsansicht für die synthetische Testumgebung `notary_team_01`. Die Oberfläche ist ein paketierbares SharePoint Framework Web Part mit **SPFx 1.23.2**, **Heft** und `bpmn-js/lib/Viewer`. Sie läuft als `SharePointWebPart` und `TeamsTab`.

Der Modus ist **viewer-only**. Er modelliert oder speichert keine BPMN-Datei, startet keinen Workflow, schreibt nicht nach SharePoint und verarbeitet keine echten Mandatsdaten.

## Paket- und Buildvertrag

Der Paketquellbaum liegt unter `spfx/nac-bpmn-viewer`. `package-lock.json` ist verpflichtender Teil des Quellvertrags. Der reproduzierbare Build verwendet:

```bash
npm ci
npm run build
```

`npm run build` führt den Heft-Produktionsbuild und `heft package-solution --production` aus. Das erzeugte Paket liegt unter `sharepoint/solution/nac-bpmn-viewer.sppkg`.

`node_modules`, `lib`, `dist`, `temp` und `sharepoint/solution` bleiben ignoriert und untracked. Rekursive Source-Scans betreten diese Pfade nicht.

## Bereitstellungsgrenze

Die aktuelle App-Catalog-Bereitstellung ist **owner-approved** und **site-scoped** ausschließlich für `notary_team_01`. `skipFeatureDeployment=false` erzwingt die Site-Installation. Tenant-weite Bereitstellung und jede Installation in einem anderen Workspace bleiben gesperrt.

Die Freigabe erlaubt Paketbau, App-Catalog-Upload und Site-Installation innerhalb dieser Grenze. Sie ist keine Freigabe für produktive Daten, neue Berechtigungen oder weitere Sites.

## Graph-freier Datenmodus

Die Laufzeitdaten stammen ausschließlich aus der paketgebundenen Fixture `package_fixture` in `fixtures/syntheticWorkspace.ts`; das BPMN XML wird aus `fixtures/sampleBpmn.ts` gebündelt.

Das SPFx-Paket fordert keine Graph Permission und enthält keinen `MSGraphClient`, `AadHttpClient`, direkten Microsoft-Graph-Aufruf, Graph SDK, PnP, CSOM oder Legacy-SharePoint-API. `webApiPermissionRequests` bleibt leer bzw. fehlt vollständig.

Die Projektion enthält nur synthetische Status-, Aufgaben-, Frist- und BPMN-Daten. **Keine Mandatsdaten** werden gelesen, angezeigt oder gespeichert.

## UI- und DOM-Vertrag

Die aktuelle UI weist ihren Paketmodus direkt aus:

- `data-nac-component="test-workspace"` kennzeichnet die Testoberfläche.
- `Synthetische Testdaten` kennzeichnet die Datenklasse sichtbar.
- `Keine Mandatsdaten` bestätigt die Laufzeitgrenze.
- Ein abweichender `workspaceId` schlägt geschlossen mit `Workspace nicht freigegeben.` fehl.

Diese Marker ersetzen den früheren Offline-Render-State-DOM-Vertrag. Die Sicherheitsprüfungen bleiben erhalten: Paketquelle, Workspace-Allowlist, Viewer-only, keine Writes, kein Graph und keine echten Mandatsdaten werden getrennt validiert.

## Verträge und Nachweis

Verbindlich sind der [Viewer-Adapter-Vertrag](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json), das [SPFx-Paketartefakt](../../../deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json) und die [Runtime-Readiness](../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.runtime-readiness.json).

Die Prüfung erfolgt über:

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
python3 -m unittest tests.test_m365_bpmn_viewer_runtime_readiness
python3 -m unittest tests.test_m365_sharepoint_bpmn_viewer_adapter
```
