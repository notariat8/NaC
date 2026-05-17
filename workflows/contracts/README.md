# Workflow-Vertraege

Dieser Ordner ist fuer Workflow-Vertraege reserviert. Ein Vertrag beschreibt
die Grenze zwischen einem notariellen Usecase, einem oder mehreren Plugins und
deterministischer Workflow-Ausfuehrung.

Jeder Vertrag soll definieren:

- Eingabeschema
- Ausgabeschema
- erforderliche Rollen
- erforderliche Freigaben
- erforderliche Plugin-Gates
- Datenklasse
- Form des Nachweisdatensatzes

## Implementierte Vertraege

- [workflows/contracts/kg-editor.contract.json](kg-editor.contract.json):
  KG-Editor-Vertrag zum Rendern usecase-lokaler
  [knowledge-graph.graph.json](../../usecases/immobilienkaufvertrag/knowledge-graph.graph.json)
  Dateien als sichere Formulare, Checklisten und Patch-Vorschlaege, ohne
  `value`-Felder fuer Fachpersonal offenzulegen.
