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
Editor-View bereit. Die verbindliche Bedienkante für Produktdokumentation ist
jetzt die zentrale [NaC-CLI](../../docs/de/cli.md).

```bash
python scripts/nac.py kg status
python scripts/nac.py kg case bautraegervertrag
python scripts/nac.py kg editor-view immobilienkaufvertrag
python scripts/nac.py plugins actions
python scripts/nac.py plugins card-readiness
```

Direkte Skripte bleiben als interne Kompatibilität erlaubt. Neue
Workflow-Funktionen sollen aber zusätzlich über `nac` erreichbar sein.

## Nächster Entwicklungsschritt

Der KG-Editor-Workstream stellt inzwischen einen implementierten Editor-View-
Vertrag in
[workflows/contracts/kg-editor.contract.json](../contracts/kg-editor.contract.json)
bereit. Das nächste Workflow-Inkrement ist ein Vertragsgenerator, der einen
KG-Case liest und zusätzliche Workflow-Vertragsgerüste unter
[workflows/contracts/](../contracts) ohne echte Mandatsdaten erzeugt.
