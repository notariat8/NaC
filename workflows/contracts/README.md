# Workflow-Verträge

Dieser Ordner ist für Workflow-Verträge reserviert. Ein Vertrag beschreibt
die Grenze zwischen einem notariellen Usecase, einem oder mehreren Plugins und
deterministischer Workflow-Ausführung.

Jeder Vertrag soll definieren:

- Eingabeschema
- Ausgabeschema
- erforderliche Rollen
- erforderliche Freigaben
- erforderliche Plugin-Gates
- Datenklasse
- Form des Nachweisdatensatzes

## Implementierte Verträge

- [workflows/contracts/kg-editor.contract.json](kg-editor.contract.json):
  KG-Editor-Vertrag zum Rendern usecase-lokaler
  [knowledge-graph.graph.json](../../usecases/immobilienkaufvertrag/knowledge-graph.graph.json)
  Dateien als sichere Formulare, Checklisten und Patch-Vorschläge, ohne
  `value`-Felder für Fachpersonal offenzulegen.
- [workflows/contracts/bpmn-js-editor.contract.json](bpmn-js-editor.contract.json):
  BPMN-js-Editor-Vertrag für visuell bearbeitbare BPMN-2.0-Prozessmodelle mit
  NaC-Properties, Python-Validierung und Pull-Request-Freigabe.
- [workflows/contracts/local-web-preview.contract.json](local-web-preview.contract.json):
  lokaler Webserver-Vertrag für grafische BPMN- und KG-Ausgaben ohne Cloud-
  oder Mandatsdatenpflicht.
