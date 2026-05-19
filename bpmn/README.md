# BPMN Quellmodelle

Dieser Ordner enthält die fachlich verbindlichen BPMN-2.0-Quellmodelle
(`*.bpmn`). Für fachliche Prozesse gilt: BPMN ist die Quelle, `bpmn-js` ist die
geplante visuelle Bearbeitungsschicht, Python prüft deterministisch.

## Regeln

- BPMN-Dateien sind die fachliche Prozessquelle.
- Python-Implementierung in `src/business_os/`, `src/notary_kg/` und
  [scripts/](../scripts) muss auf diese Modelle referenzierbar sein.
- Mermaid-Diagramme sind zusätzliche Übersichten und ersetzen keine BPMN-Quelle.
- bpmn-js darf BPMN bearbeiten, aber nicht allein Governance, Datenschutz oder
  Freigabe entscheiden.
- NaC-spezifische bpmn-js-Attribute stehen in [nac-moddle.json](nac-moddle.json)
  und werden in [nac-bpmn-profile.md](nac-bpmn-profile.md) erklärt.
- `scripts/validate_bpmn_models.py` ist die deterministische Prüfung für BPMN-
  XML, NaC-Attribute, Sequenzflüsse und bpmn-js-taugliche Profilmodelle.

## Erste Modelle

- [immobilienkaufvertrag.bpmn](immobilienkaufvertrag.bpmn): erstes
  bpmn-js-taugliches NaC-Profilmodell mit BPMNDI-Diagrammfläche.
- [invoice-process.bpmn](invoice-process.bpmn), [bookkeeping-process.bpmn](bookkeeping-process.bpmn)
  und [onboarding-entry.bpmn](onboarding-entry.bpmn): ältere Referenzmodelle,
  die weiterhin strukturell validiert werden.
