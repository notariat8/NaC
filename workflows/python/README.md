# Python-Workflows

Status: aktive Entwicklung

Dieser Ordner ist die deterministische Python-Workflow-Schicht. Python ist die
Ausfuehrungs- und Validierungsschicht fuer wiederholbare Notariatsworkflows.

Python-Workflows muessen bereitstellen:

- schemagestuetzte Eingaben und Ausgaben
- Idempotenzschluessel
- Freigabe-Gates
- Trockenlauf- oder Planvorschau-Modus
- reine Metadaten-Nachweissaetze
- keine Speicherung echter Secrets oder echter personenbezogener Daten

## Implementierte Runtime-Oberflaeche

Die erste implementierte Runtime ist [src/notary_kg/](../../src/notary_kg). Sie
liest die usecase-lokalen statischen notariellen KG-Dateien und stellt
ausfuehrbare Readiness-/Status-Sichten sowie die erste sichere No-code-
Editor-View bereit.

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

## Naechster Entwicklungsschritt

Der KG-Editor-Workstream stellt inzwischen einen implementierten Editor-View-
Vertrag in
[workflows/contracts/kg-editor.contract.json](../contracts/kg-editor.contract.json)
bereit. Das naechste Workflow-Inkrement ist ein Vertragsgenerator, der einen
KG-Case liest und zusaetzliche Workflow-Vertragsgerueste unter
[workflows/contracts/](../contracts) ohne echte Mandatsdaten erzeugt.
