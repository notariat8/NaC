# Contributing

Vielen Dank fuer Beitraege zum Musterrepo.

## Grundregeln

- Aenderungen nur ueber Branch und Pull Request.
- Jede Aenderung braucht Zweck und Auswirkungsbeschreibung.
- Konzeptaenderungen muessen Cursor- und VS-Code-Copilot-Pfade synchron aktualisieren.
- Technikvorgaben aus `policies/technology-policy.yaml` sind verbindlich.

## Vorgehen

1. Issue erstellen oder aus Backlog waehlen.
2. Branch erstellen.
3. Aenderung umsetzen und lokal pruefen.
4. Pull Request mit Nachweis und Review-Anforderung erstellen.

## Mindestchecks

- `python -m business_os validate-all --repo-root .`
- `python -m unittest discover -s tests -p "test_*.py"`

## Fachliche Beitraege

- BPMN-2.0 ist die fachliche Quellnotation.
- Mermaid nur fuer Uebersichten.
