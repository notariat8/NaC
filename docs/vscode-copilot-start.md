# VS Code + GitHub Copilot: Startleitfaden

## Ziel

Dieser Leitfaden zeigt, wie ein Unternehmen dieses Musterrepo ohne Cursor mit VS Code und GitHub Copilot nutzt.

Wenn Sie als Erstnutzer nicht alle Dokumente lesen wollen, nutzen Sie den gefuehrten Pfad:
`docs/vscode-first-user-path.md`

## Voraussetzungen

- GitHub-Organisation oder Unternehmenskonto
- VS Code installiert
- Git installiert
- GitHub Copilot Lizenz aktiv

## Einrichtung in 8 Schritten

1. Erstellen Sie ein eigenes Repository fuer Ihr Unternehmen.
2. Uebernehmen Sie dieses Muster als Basis (Template oder Fork).
3. Oeffnen Sie das Repo in VS Code.
4. Installieren und aktivieren Sie GitHub Copilot im Editor.
5. Lesen Sie `docs/START_HERE.md` und bestaetigen Sie die Policies unter `policies/`.
6. Nutzen Sie ein Onboarding-Prompt aus `prompts/onboarding/` fuer Ihre Branche.
7. Starten Sie mit einem Pilotprozess und pruefen Sie den Pull-Request-Workflow.
8. Fuehren Sie erst nach erfolgreichem Pilot den breiten Rollout durch.

## Empfohlener Copilot-Startprompt

```text
Lies zuerst folgende Dateien und erklaere mir dann die naechsten 3 Schritte ohne IT-Fachsprache:
- docs/START_HERE.md
- docs/fachanwender-guide.md
- policies/process-policy.yaml
- policies/culture-policy.yaml
- policies/technology-policy.yaml

Danach:
1) Frage mich nach Unternehmensart und Prioritaetsprozessen.
2) Schlage passende Branchenmodule vor.
3) Erstelle einen 30-Tage-Pilotplan fuer Rechnung und Buchfuehrung.
```

## Operative Regeln fuer Copilot-Nutzung

- Prozessaenderungen nur als Pull Request.
- Bei sensiblen Schritten immer Review einplanen.
- Jede Aenderung mit Zweck, Risiko und Verantwortlichem dokumentieren.
- Kultur- und Sprachregeln aus `policies/culture-policy.yaml` verbindlich einhalten.

## Wenn das Muster nicht passt

- Erfassen Sie die Abweichung als Change Request.
- Testen Sie die neue Variante im Pilot.
- Uebernehmen Sie sie versioniert in Ihr Unternehmensmodell.
- Optional: geben Sie bewahrte Verbesserungen an das Referenzmuster zurueck.
