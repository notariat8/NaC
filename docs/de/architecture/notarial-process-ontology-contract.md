# Notarieller Prozess-/Ontologie-Vertrag

Status: S1/S2 offline implementiert am 2026-07-11 unter
[Issue #610](https://github.com/notariat8/NaC/issues/610); S3-S7 offen.

Diese Decision Note beschreibt den implementierten fachlichen
Produktmodell-Vertrag für den M365-/SharePoint-MVP. Der maschinenlesbare
Vertrag liegt in
[workflows/contracts/notarial-process-ontology.contract.json](../../../workflows/contracts/notarial-process-ontology.contract.json)
und wird mit `nac kg process-ontology-contract` geprüft.

## Identität Und Gültigkeit

- Der Bestand umfasst 20 kanonische `BusinessCaseTypeId`-Werte und zwei
  historische Aliase. Aliase sind keine neuen kanonischen Identitäten.
- Der repo-versionierte Usecase-Katalog bleibt führend.
- Das viewer-unabhängige `Vorgangsartenregister` ist die erforderliche
  SharePoint-Runtime-Projektion. `BusinessCaseTypeId` ist dort eindeutig,
  indexiert und mit `LifecycleStatus`, `Selectable` und `CatalogVersion`
  verbunden.
- `Akten.VorgangstypId` ist die additive, indexierte Textprojektion derselben
  Identität.
- `Akten.Vorgangstyp` bleibt als Legacy-Choice unverändert. S2 plant weder
  Choice-Erweiterung noch Konvertierung oder sonstigen Patch dieses Felds.
- `Prozessregister` ist optional. Wenn eine Zeile existiert, ist
  `ProcessKey == BusinessCaseTypeId`. `NacProcessId` bleibt die technische
  Zeilenidentität.
- `NacBpmnModelId`, `BpmnDriveItemId`, `BpmnXmlSha256`, `BpmnGitPath`,
  `BpmnGitCommitSha`, `NacBpmnVersion` und `BpmnContentMode` sind im
  `Prozessregister` nullable.
- Ein fehlendes `Prozessregister`, fehlendes BPMN-Modell oder deaktivierter
  Viewer macht eine kanonische Vorgangsart nicht ungültig. Nur die konkrete
  BPMN-/Viewer-Operation bleibt dann gesperrt.

SharePoint bleibt operative MVP-Datenhaltung für Metadaten, Aufgaben,
Dokumentzeiger, Vertretungsfreigaben und redigierte Audit-Ereignisse. Die
Ontologie bleibt ein versionierter Produktmodell- und Projektionsvertrag, kein
Runtime-Store und kein globaler Reasoner auf dem Request-Pfad.

## Offline-Grenzen

S1 und S2 sind ausschließlich offline implementiert:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperation
- keine SharePoint-Schemaänderung
- keine Mandatswerte oder Dokumentvolltexte im Repo
- keine Secrets und kein zentraler Knowledge-Graph-Ordner
- Microsoft Graph REST v1.0 bleibt die einzige spätere M365-Datenkante; SDKs,
  alte SharePoint-APIs und Graph beta bleiben blockiert

Der
[Prozessontologie-Validator](../../../scripts/validate_notarial_process_ontology_contract.py)
prüft diese Grenzen.

## Schema-Gap Und Apply-Plan

`nac kg process-ontology-schema-gap` vergleicht den v2-Vertrag mit dem
aktuellen SharePoint-MVP-Schema
[deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json](../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json).
Der v0.2-Befund weist aus:

- das erforderliche `Vorgangsartenregister`
- die additive Textspalte `Akten.VorgangstypId`
- weitere Prozessinstanz-Feldlücken
- das optionale `Prozessregister` und die optionale Bibliothek `BPMN Models`
  als getrennte Viewer-Projektionen, die nicht zum verpflichtenden
  S2-Apply-Plan gehören
- den geschützten Fingerprint des unveränderten Legacy-Choice
  `Akten.Vorgangstyp`

`nac kg process-ontology-schema-apply-plan` erzeugt für den verpflichtenden
Default-S2-Scope 33 rein lokale Graph-REST-Request-Templates. Der Plan enthält
Idempotenzprüfungen, Preconditions, erwartete Erfolgsstatus sowie Snapshot-
und additive Recovery-Grenzen. Er enthält weder `Prozessregister` noch `BPMN
Models`, keinen Patch für `Akten.Vorgangstyp` und führt keinen Request aus. Die
beiden Viewer-Artefakte werden ausschließlich über den separaten optionalen
Viewer-Provisioning-Plan vorbereitet.

Die Validatoren
[Schema-Gap](../../../scripts/validate_process_ontology_sharepoint_schema_gap.py)
und
[Apply-Plan](../../../scripts/validate_process_ontology_sharepoint_schema_apply_plan.py)
prüfen diese Semantik.

## Readiness, Ausführungsvertrag Und Dry-Run

`nac kg process-ontology-schema-apply-readiness` expandiert die 33
Plan-Schritte für zwei Workspaces zu 66 Workspace-Apply-Units. Site- und
Listen-IDs, dynamische Auflösungen, `Sites.Manage.All`, Reihenfolge,
Idempotenz und Recovery-Evidence werden offline geprüft. Das Ergebnis
`OWNER_GATE_REQUIRED` ist keine Live-Freigabe.

`nac kg process-ontology-schema-apply-execution-contract` und
`nac kg process-ontology-schema-apply-runner-dry-run` binden dieselben 66
Units an Preflight-, künftige Mutations- und Readback-Pläne. Auch diese
Artefakte führen keine Graph-Requests aus, schreiben nichts nach SharePoint und
ändern kein Schema.

Der
[Readiness-Validator](../../../scripts/validate_process_ontology_sharepoint_schema_apply_readiness.py)
prüft die Workspace-Expansion. Der Ausführungsvertrag setzt den verbindlichen
Status `BLOCKED_PENDING_S6_S7_APPROVAL`.

## Offene Slices

S1 Vertrag und S2 Schema-Plan sind offline implementiert. S3 Runtime, S4
MCP/Graph, S5 Migration, S6 Immutable Evidence und S7 Live-Freigabe bleiben
offen. Vor Umsetzung und dualer Freigabe von S6/S7 darf kein Live-Schema-Apply,
Backfill, Cutover oder Rollback ausgeführt werden.
