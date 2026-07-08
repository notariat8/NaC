# M365 SharePoint BPMN Viewer Adapter

Status: Contract-first-Entscheidung
Letzte inhaltliche Anpassung: 2026-07-08

## Zweck

NaC kann BPMN-Prozesse später in SharePoint anzeigen, ohne SharePoint zur
führenden BPMN-Quelle, zum BPMN-Modeler oder zur Workflow-Engine zu machen.
Der saubere Start ist ein read-only SPFx-Webpart mit `bpmn-js` im
viewer-only-Modus. Dieses Webpart rendert freigegebene BPMN-XML-Modelle und
optional geprüfte Status-Metadaten aus SharePoint-Listen.

Der aktive MVP-Datenpfad bleibt Teams, Microsoft-365-Gruppe und
SharePoint-Team-Site über Microsoft Graph REST. Dieser Adapter ist nur eine
Anzeige- und Navigationsfläche auf derselben M365-Arbeitsoberfläche.

## Entscheidung

Der MVP baut jetzt kein SharePoint-Plugin und keinen BPMN-Modeler. NaC legt
zunächst nur den Vertrag für einen späteren `NaC BPMN Viewer` fest:

```text
Git BPMN templates
  -> Python validation and pull request review
    -> approved BPMN model copy or pointer
      -> SharePoint document library "BPMN Models"
        -> SPFx Web Part with bpmn-js Viewer
          -> read-only process page in SharePoint
```

Das ist bewusst kleiner als ein vollwertiger Modeler. Bearbeitung bleibt im
lokalen NaC-BPMN-js-Editor und im Pull-Request-Prozess. SharePoint zeigt nur
an, was bereits freigegeben wurde.

## SharePoint-Oberfläche

Die spätere SharePoint-Site kann zwei zusätzliche Artefakte bekommen:

| Artefakt | Zweck |
| --- | --- |
| `BPMN Models` | Dokumentbibliothek für freigegebene BPMN-XML-Kopien oder Pointer |
| `Prozessregister` | Liste für Prozessname, Owner, Status, Version, Review-Datum und Modell-Link |

Das Webpart darf freigegebene BPMN-XML-Dateien lesen. Es darf keine
Akten-Dokumentinhalte, Mandatswerte, Secrets oder produktive Fachsystemdaten
lesen. Status-Overlays sind nur als geprüfte Metadaten erlaubt, zum Beispiel
aus `AufgabenFristen`, `AuditJournalLite`, `DokumentRegister` oder einem
späteren `Prozessregister`.

Für diesen MVP-Schnitt existiert nur ein optionaler Provisioning-Plan unter
`deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json`. Der Status
ist `optional_plan_only_no_live_apply`: `nac m365 teams-sharepoint
bpmn-viewer-plan --format json` rendert die geplante Bibliothek, Liste und
Spalten, führt aber keinen Live-Apply gegen Microsoft 365 aus und erweitert
nicht das verpflichtende MVP-SharePoint-Schema.

Der erste SPFx-Schnitt liegt source-only unter `spfx/nac-bpmn-viewer`. Der
Befehl `nac m365 teams-sharepoint spfx-bpmn-viewer-skeleton --format json`
rendert das Skeleton, die synthetische Render-Fixture und die
MCP-Request-Plans für `bpmn_model_get`, `process_register_list` und
`bpmn_viewer_overlay_get`. Dieser Schnitt baut kein SPFx-Paket, legt kein
`package-lock.json` an, nutzt keinen App Catalog und führt keinen Graph- oder
Tenant-Apply aus.

Der Offline-Rendervertrag `spfx-bpmn-viewer-offline-render-contract` ist in
[nac-spfx-bpmn-viewer.skeleton.json](../../../deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json),
[render-contract.fixture.json](../../../tests/fixtures/m365/spfx-bpmn-viewer/render-contract.fixture.json)
und im
[M365-SharePoint-BPMN-Viewer-Adapter-Vertrag](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json)
verdrahtet. Er kennt genau die Zustände `approved_renderable`,
`approval_missing_or_review_required`, `viewer_disabled`,
`contains_matter_data` und `invalid_mime_or_hash_missing`. Die DOM-Marker
`data-nac-render-state`, `data-nac-content-source` und
`data-nac-metadata-overlay` tragen nur den redigierten Renderstatus; das
Overlay enthält keine Akteninhalte, Mandatswerte, Credential-Materialien oder
rohen Graph-Pfade. Der CLI-Vertrag bleibt offline mit `liveTenantAccess=false`,
`appCatalogDeploy=false` und `request_plan_count=3`.

Der Prozessregister-Auswahlvertrag
`spfx-bpmn-viewer-process-register-selection-contract` bleibt ebenfalls
offline. Der Befehl
`nac m365 teams-sharepoint spfx-bpmn-viewer-process-selection --format json`
wählt aus synthetischen `Prozessregister`-Metadaten genau einen freigegebenen,
viewer-aktivierten Eintrag, verknüpft ihn mit `BPMN Models` und blockiert bei
fehlender Freigabe, deaktiviertem Viewer, nicht-`MetadataOnly`-Overlay oder
nicht renderbarem BPMN-Modell. Der Befehl liest keine SharePoint-Dateiinhalte,
führt keine Graph-Requests aus, startet keinen Workflow und deployt kein
SPFx-Paket.

Der Runtime-Readiness-Schnitt bleibt ebenfalls offline:
`nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json`
prüft die Grenzen für SPFx-Paketierung, App-Catalog-Deploy und den späteren
Graph-Content-Read freigegebener `.bpmn`-Dateien. Ein `PASSED` bedeutet hier
nur, dass die Guardrails intakt sind. Es bedeutet nicht, dass Paketierung,
App-Catalog-Upload, Tenant-Apply oder Live-BPMN-Content-Read freigegeben sind.
Diese Schritte bleiben Owner-Gates mit separatem PR, Rollback-Plan und
redigiertem Nachweis.

## Graph-REST-Grenze

Alle Zugriffe laufen über Microsoft Graph REST v1.0 oder einen MCP-Server, der
intern ebenfalls Microsoft Graph REST nutzt. Alte SharePoint-REST-APIs, CSOM,
PnP und Microsoft Graph SDKs bleiben gesperrt.

Erlaubte Endpunktfamilien für den Viewer-Vertrag:

- `GET /sites/{site-id}/drives`
- `GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/content`
- `GET /sites/{site-id}/lists/{list-id}/items`
- `GET /sites/{site-id}/lists/{list-id}/items/{item-id}`

Der Content-Read ist auf freigegebene BPMN-XML-Modelle begrenzt. Er ist keine
Freigabe zum Lesen von Akten-Dokumentinhalten oder Mandats-Payloads.
Vor einem späteren Live-Read müssen mindestens `ApprovalStatus=Approved`,
`ViewerEnabled=true`, `ContainsMatterData=false`, eine erlaubte `NacDataClass`
und der Abgleich von `BpmnXmlSha256` gegen das geladene XML erfüllt sein.

## Warum SPFx

SharePoint Online ist keine neutrale Ablage, in der moderne Seiten beliebige
HTML-/JavaScript-Apps zuverlässig ausführen sollten. Custom Script ist in
SharePoint Online aus Sicherheitsgründen eingeschränkt. Ein SPFx-Webpart ist
die passende SharePoint-Bereitstellungsform für clientseitige Komponenten.

`bpmn-js` ist geeignet, um BPMN-2.0-XML im Browser zu rendern. Für NaC wird
hier nur der Viewer genutzt. Der Modeler, Speichern, Locking, XML-Roundtrip,
Versionierung und Freigaben sind ein eigener späterer Scope.

## Gesperrt

Dieser Adapter darf nicht:

- BPMN XML schreiben oder speichern,
- Workflow-Instanzen starten oder ausführen,
- SharePoint-Schema, Teams oder Mitgliedschaften ändern,
- Akten-Dokumentinhalte oder Mandats-Payloads lesen,
- Secrets speichern,
- Custom-Script-/Loose-HTML-Einbettung als Produktpfad nutzen,
- alte SharePoint-APIs, CSOM, PnP oder Graph SDKs verwenden,
- Pull-Request-Review und Python-Validierung ersetzen.

## Verhältnis Zu MCP

Es ist jetzt kein neuer MCP-Server nötig. Wenn der Viewer später MCP nutzt,
dann über die bestehende `teams-sharepoint-data-mcp`-Grenze. Denkbare
read-only Tools sind:

- `bpmn_model_get`
- `process_register_list`
- `bpmn_viewer_overlay_get`

Diese Tools bleiben lesend, redigieren Metadaten und liefern keine
Akten-Dokumentinhalte. In der aktuellen Runtime sind sie Request-Plan-Tools;
der owner-gated Live-Read-Modus bleibt auf `case_get` und `document_list`
begrenzt.

## Verhältnis Zum BPMN-js-Editor

Der bestehende BPMN-js-Editor-Vertrag bleibt die Bearbeitungs- und
Governance-Grenze. Der SharePoint-Adapter ist eine Anzeigeprojektion für
freigegebene Modelle, nicht die Quelle, nicht der Editor, nicht der
Speicherpfad und nicht die Ausführungsengine.

## Validierung

Der Vertrag wird durch diese Checks abgesichert:

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_bpmn_viewer_runtime_readiness
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
python3 scripts/nac.py m365 teams-sharepoint spfx-bpmn-viewer-process-selection --format json
python3 -m unittest tests.test_m365_bpmn_viewer_provisioning
python3 -m unittest tests.test_m365_sharepoint_bpmn_viewer_adapter
python3 scripts/quality_gate.py --profile strict
```
