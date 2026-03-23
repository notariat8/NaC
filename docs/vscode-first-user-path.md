# VS Code: Erstnutzer-Pfad

## Muss ich alles lesen?

Nein. Sie muessen nicht alle Markdown-Dateien lesen.

Empfohlener Minimalpfad:

1. `docs/START_HERE.md`
2. `docs/vscode-copilot-start.md`
3. Start mit Formular-Wizard statt Volllektuere

## Schritt 1: Startfrage klaeren

Sie klaeren zuerst:

- Gruendung (`founding`) oder Bestandsunternehmen (`existing`)?

Diese Entscheidung steuert den restlichen Fragepfad.

## Schritt 2: Stateful Onboarding starten

Starten Sie den Wizard:

```bash
python scripts/onboarding_wizard.py start --session out/onboarding/session.json --actor-name "Max Beispiel" --actor-role "prozessverantwortung" --github-login "ofunk-nvidia" --mode existing
```

Fortschritt pruefen:

```bash
python scripts/onboarding_wizard.py status --session out/onboarding/session.json
```

Plan exportieren:

```bash
python scripts/onboarding_wizard.py export-plan --session out/onboarding/session.json --output out/onboarding/plan.md
```

Audit-Bundle finalisieren (immutable Nachweise mit Hash):

```bash
python scripts/onboarding_wizard.py finalize --session out/onboarding/session.json --output-dir out/onboarding/final --export-pdf
```

## Schritt 3: Zusammenarbeit ueber mehrere Tage

- Jeder Beitrag wird mit Rolle, Name und Zeitstempel gespeichert.
- Mehrere Personen koennen dieselbe Session-Datei fortsetzen.
- Rollen- und Qualifikationsmodell bleibt verbindlich.

## Schritt 4: Von Analyse zu Pilot

Wenn alle Fragen beantwortet sind:

1. Pilotprozesse festlegen
2. Rollen/Qualifikationen finalisieren
3. ersten Pull Request fuer den Pilot anlegen
