# NaC Workflows

Dieser Ordner ist die Ausführungsschicht für Geschäftsprozesse im
Notariatsbetrieb. Er ist von [plugins/](../plugins) und
[usecases/](../usecases) getrennt.

## Grenze

- [plugins/](../plugins) enthält installierbare Marketplace- oder
  Workspace-Begleitpakete.
- [workflows/](.) enthält wiederverwendbare Workflow-Logik für
  Notariatsabläufe.
- [usecases/](../usecases) enthält konkrete notarielle Geschäftsszenarien,
  die Plugins und Workflows miteinander verbinden.

## Geplante Struktur

- `skills/`: installierbare oder repo-lokale Skills für LLM-seitige
  Bedienführung.
- `python/`: deterministische Python-Workflowmodule für Validierung,
  Idempotenz, Ausführungsplanung und Nachweis-Metadaten.
- `contracts/`: Workflow-Eingabe-/Ausgabeverträge, Freigaben, Datenklassen
  und Plugin-Abhängigkeiten.

Kein Workflow darf echte Secrets oder echte personenbezogene Daten speichern.
Workflow-Ausführung muss über Git, Pull Requests, Freigaben und
Nachweis-Metadaten reviewfähig bleiben.
