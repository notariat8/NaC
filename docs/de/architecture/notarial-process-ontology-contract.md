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
