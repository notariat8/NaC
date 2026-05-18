# Python-Workflows

Status: aktive Entwicklung

Dieser Ordner ist die deterministische Python-Workflow-Schicht. Python ist die
Ausführungs- und Validierungsschicht für wiederholbare Notariatsworkflows.

Python-Workflows müssen bereitstellen:

- schemagestützte Eingaben und Ausgaben
- Idempotenzschlüssel
- Freigabe-Gates
- Trockenlauf- oder Planvorschau-Modus
- reine Metadaten-Nachweissätze
- keine Speicherung echter Secrets oder echter personenbezogener Daten

## Implementierte Runtime-Oberfläche

Die erste implementierte Runtime ist [src/notary_kg/](../../src/notary_kg). Sie
liest die usecase-lokalen statischen notariellen KG-Dateien und stellt
ausführbare Readiness-/Status-Sichten sowie die erste sichere No-code-
Editor-View bereit.

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

## Nächster Entwicklungsschritt

Der KG-Editor-Workstream stellt inzwischen einen implementierten Editor-View-
Vertrag in
[workflows/contracts/kg-editor.contract.json](../contracts/kg-editor.contract.json)
bereit. Das nächste Workflow-Inkrement ist ein Vertragsgenerator, der einen
KG-Case liest und zusätzliche Workflow-Vertragsgerüste unter
[workflows/contracts/](../contracts) ohne echte Mandatsdaten erzeugt.
