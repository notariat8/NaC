# Ontologie-Scale-Budget

Diese Decision Note beschreibt den Offline-Smoke für Ontologie-Sizing über alle
bekannten notariellen Geschäftsvorfälle.

## Zweck

`nac kg ontology-scale-budget --format json` prüft, ob die aktuelle
SharePoint-/Ontologie-Grenze auch dann tragfähig bleibt, wenn nicht nur zwei
oder drei Vorgänge, sondern das vollständige Geschäftsvorfall-Inventar in das
Sizing eingeht.

Der Smoke zählt und bewertet:

- alle Geschäftsvorfälle aus dem dünnen Inventar
- vorhandene BPMN-Quellen und BPMN-Flow-Nodes
- geschätzte Ontologie-Projektionsknoten je Vorgang
- geschätzte Ontologie-Projektionskanten je Vorgang
- Runtime-Grenzen für Graph-Reads und SharePoint-Listen je User-Aktion

## Entscheidung

SharePoint bleibt für den MVP der operative Datenspeicher. Die Ontologie bleibt
ein versionierter Projektions- und Sizing-Vertrag im Repo, nicht die
produktive Runtime-Datenbank.

Der Smoke erlaubt tiefe BPMN-/Ontologie-Modellierung nur als selektiven
Folgeschritt. Er verhindert nicht, dass alle Geschäftsvorfälle im Sizing
berücksichtigt werden.

## Grenzen

Der Scale-Smoke ist offline-only:

- keine Microsoft-Graph-Requests
- keine SharePoint-Schreiboperation
- keine SharePoint-Schemaänderung
- keine Dokumentinhaltslesung
- keine Mandatswerte in Git oder Ontologie
- keine Secrets
- kein zentraler `knowledge-graph/`-Ordner
- kein Runtime-Ontologie-Reasoning im User-Request-Pfad

Der Validator
[scripts/validate_notarial_ontology_scale_budget.py](../../../scripts/validate_notarial_ontology_scale_budget.py)
prüft diese Grenzen im strikten Quality Gate.
