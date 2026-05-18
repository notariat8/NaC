# NaC Workflows

Dieser Ordner ist die Ausfuehrungsschicht fuer Geschaeftsprozesse im
Notariatsbetrieb. Er ist von [plugins/](../plugins) und
[usecases/](../usecases) getrennt.

## Grenze

- [plugins/](../plugins) enthaelt installierbare Marketplace- oder
  Workspace-Begleitpakete.
- [workflows/](.) enthaelt wiederverwendbare Workflow-Logik fuer
  Notariatsablaeufe.
- [usecases/](../usecases) enthaelt konkrete notarielle Geschaeftsszenarien,
  die Plugins und Workflows miteinander verbinden.

## Geplante Struktur

- `skills/`: installierbare oder repo-lokale Skills fuer LLM-seitige
  Bedienfuehrung.
- `python/`: deterministische Python-Workflowmodule fuer Validierung,
  Idempotenz, Ausfuehrungsplanung und Nachweis-Metadaten.
- `contracts/`: Workflow-Eingabe-/Ausgabevertraege, Freigaben, Datenklassen
  und Plugin-Abhaengigkeiten.

Kein Workflow darf echte Secrets oder echte personenbezogene Daten speichern.
Workflow-Ausfuehrung muss ueber Git, Pull Requests, Freigaben und
Nachweis-Metadaten reviewfaehig bleiben.
