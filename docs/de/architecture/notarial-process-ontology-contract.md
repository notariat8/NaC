# Notarieller Prozess-/Ontologie-Vertrag

Diese Decision Note fixiert den fachlichen Produktmodell-Vertrag für den
M365-/SharePoint-MVP.

Der maschinenlesbare Vertrag liegt in
[workflows/contracts/notarial-process-ontology.contract.json](../../../workflows/contracts/notarial-process-ontology.contract.json)
und wird mit `nac kg process-ontology-contract --format json` geprüft.

## Zweck

Der Vertrag ist die fachliche Kante zwischen Geschäftsvorfall-Inventar,
BPMN-Prozessmodell, Ontologie-Projektion, SharePoint-Datenhaltung und
Agenten-Runtime. Er beantwortet nicht mehr nur, ob SharePoint technisch
funktioniert, sondern welche Produktobjekte NaC für notarielle Workflows
kanonisch kennt:

- Geschäftsvorfalltypen
- Vorgänge und Status
- Beteiligte, Rollen und Rollenbindungen
- Prozessphasen, Aufgaben, Fristen, Gates und Entscheidungen
- Dokumenttypen, Dokumentzeiger und Versionen
- Evidence-Zeiger und Audit-Events
- zeitlich begrenzte Vertretungsfreigaben
- BPMN-Modellzeiger

## Entscheidungen

- SharePoint bleibt operative MVP-Datenhaltung für Metadaten, Aufgaben,
  Dokumentzeiger, Vertretungsfreigaben und redigierte Audit-Ereignisse.
- Die Ontologie ist ein versionierter Produktmodell- und Projektionsvertrag,
  kein Runtime-Store und kein globaler Reasoner auf dem Request-Pfad.
- Alle Geschäftsvorfälle aus dem Inventar werden für Sizing und Index gezählt;
  tiefe BPMN-/Ontologie-Modellierung darf trotzdem selektiv bleiben.
- Microsoft 365 bleibt über Microsoft Graph REST v1.0 angebunden. SDKs, alte
  SharePoint-APIs und Graph beta bleiben für diese Kante blockiert.
- `Prozessregister` und `BPMN Models` sind optionale spätere SharePoint-
  Projektionen und benötigen vor Live-Nutzung eine owner-gated Schema-Aktion.

## Grenzen

Dieser Slice ist offline-only:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperation
- keine SharePoint-Schemaänderung
- keine Mandatswerte im Repo
- keine Dokumentvolltexte
- keine Secrets
- kein zentraler Knowledge-Graph-Ordner
- kein produktiver BPMN-Modeler oder Workflow-Engine-Apply

Der Validator
[scripts/validate_notarial_process_ontology_contract.py](../../../scripts/validate_notarial_process_ontology_contract.py)
prüft diese Grenzen im strikten Quality Gate als
`notarial_process_ontology_contract`.

## SharePoint-Schema-Gap-Review

`nac kg process-ontology-schema-gap --format json` vergleicht diesen Vertrag mit
dem aktuellen SharePoint-MVP-Schema
[deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json](../../../deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json).

Der Review erzeugt nur Plan-Daten. Er führt keine Graph-Requests aus, schreibt
nichts nach SharePoint und ändert kein Schema. Der aktuelle erwartete Befund ist:

- alle sechs erforderlichen MVP-Listen sind vorhanden
- konkrete Prozessinstanz-Feldlücken bleiben offen, z.B.
  `ProcessInstanceId`, `CurrentPhase`, `BpmnModelRef`,
  `EvidencePointerId` und `RoleBindingId`
- `Akten.Vorgangstyp` deckt noch nicht alle Geschäftsvorfälle aus dem Inventar
  als Choice-Werte ab
- `Prozessregister` und `BPMN Models` sind optionale spätere Projektionen und
  fehlen im aktuellen MVP-Schema bewusst noch

Der Validator
[scripts/validate_process_ontology_sharepoint_schema_gap.py](../../../scripts/validate_process_ontology_sharepoint_schema_gap.py)
prüft diese Gap-Liste im strikten Quality Gate als
`process_ontology_sharepoint_schema_gap`.

## SharePoint-Schema-Apply-Plan

`nac kg process-ontology-schema-apply-plan --format json` leitet aus dem
Schema-Gap-Review eine konkrete, aber weiterhin rein lokale Graph-REST-
Schrittfolge ab. Der Plan enthält je Gap genau einen Schritt:

- optionale Listen-/Bibliotheksanlage über `POST /sites/{site-id}/lists`
- fehlende Spalten über `POST /sites/{site-id}/lists/{list-id}/columns`
- Choice-Erweiterungen über
  `PATCH /sites/{site-id}/lists/{list-id}/columns/{column-id}`

Der Apply-Plan enthält nur Request-Templates, Idempotenzprüfungen,
Preconditions und erwartete Erfolgsstatus. Er führt keine Graph-Requests aus,
schreibt nichts nach SharePoint und ändert kein Schema. Ein späterer Live-Apply
bleibt owner-gated und darf nur über Microsoft Graph REST erfolgen.

Der Validator
[scripts/validate_process_ontology_sharepoint_schema_apply_plan.py](../../../scripts/validate_process_ontology_sharepoint_schema_apply_plan.py)
prüft den Plan im strikten Quality Gate als
`process_ontology_sharepoint_schema_apply_plan`.
