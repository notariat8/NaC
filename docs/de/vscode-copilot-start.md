# VS Code + GitHub Copilot: Startleitfaden

## Ziel

Dieser Leitfaden zeigt, wie ein Unternehmen dieses Musterrepo ohne Cursor mit VS Code und GitHub Copilot nutzt.
Der fachliche Rahmen ist `Notariat as Code` mit `Enterprise GitOps`; `NaC` ist die konkrete Umsetzung.

Wenn Sie als Erstnutzer nicht alle Dokumente lesen wollen, nutzen Sie den geführten Pfad:
`docs/de/vscode-first-user-path.md`

## Voraussetzungen

- Mindestvoraussetzungen aus `docs/de/minimum-requirements.md` erfüllt
- GitHub-Organisation oder Unternehmenskonto
- VS Code installiert
- Git installiert
- Python `>= 3.11`
- GitHub CLI `gh` installiert und angemeldet
- Node.js/npm für Plugin-Entwicklung
- GitHub Copilot Lizenz aktiv

## Einrichtung in 8 Schritten

1. Erstellen Sie ein eigenes Repository für Ihr Unternehmen.
2. Übernehmen Sie dieses Muster als Basis (Template oder Fork).
3. Oeffnen Sie das Repo in VS Code.
4. Installieren und aktivieren Sie GitHub Copilot im Editor.
5. Lesen Sie `docs/de/START_HERE.md` und `docs/de/minimum-requirements.md`.
6. Führen Sie `python scripts/startup_check.py --profile base --ide vscode --run-tests` aus.
   Für Plugin-Entwicklung zusätzlich `python scripts/startup_check.py --profile plugin-dev --ide vscode`.
   Für Kartenleser-, morris- oder XNP-nahe Arbeit zusätzlich `python scripts/startup_check.py --profile notary-workstation --ide vscode`.
7. Bestätigen Sie die Policies unter `policies/`.
8. Nutzen Sie ein Onboarding-Prompt aus `prompts/de/onboarding/` für Ihre Branche.
   Standard für den MVP in diesem Repo: `software_company`, `notary`, `wealth_management`.
   Zusätzlicher MVP-Use-Case: `property_management`.
9. Starten Sie mit einem Pilotprozess und prüfen Sie den Pull-Request-Workflow.
10. Führen Sie erst nach erfolgreichem Pilot den breiten Rollout durch.
11. Definieren Sie Fork/Synchronisierung/Mischbetrieb über die Betriebsdokumente in `docs/de/`.
12. Prüfen Sie die Produktstruktur: `plugins/` für installierbare Artefakte, `workflows/` für Skills und Python-Workflows, `usecases/` für konkrete notarielle Usecases.
13. Aktualisieren Sie vor jedem Push `roadmap/GANTT.md`; bei Änderungen an `plugins/`, `workflows/` oder `usecases/` auch das jeweilige Themen-Gantt.
14. Prüfen Sie bei AI-fähigen Änderungen `docs/de/sbom-for-ai.md` und aktualisieren Sie `sbom/ai/nac-ai-sbom-draft.json`.

## Empfohlener Copilot-Startprompt

```text
Lies zuerst folgende Dateien und erklaere mir dann die naechsten 3 Schritte ohne IT-Fachsprache:
- docs/de/START_HERE.md
- docs/de/fachanwender-guide.md
- policies/process-policy.yaml
- policies/culture-policy.yaml
- policies/technology-policy.yaml

Danach:
1) Frage mich nach Unternehmensart und Prioritaetsprozessen.
2) Schlage passende Branchenmodule vor.
3) Erstelle einen 30-Tage-Pilotplan für Team-, Rollen- und Zugriffsprozesse.
```

## Operative Regeln für Copilot-Nutzung

- Prozessänderungen nur als Pull Request.
- Bei sensiblen Schritten immer Review einplanen.
- Jede Änderung mit Zweck, Risiko und Verantwortlichem dokumentieren.
- Bei offenem Scope, Issue-getriebener Arbeit oder mehreren relevanten Lösungswegen zuerst erkunden, Plan mit Zweck/Risiko nennen und Bestätigung einholen.
- Bei klar beauftragten, eng abgegrenzten Änderungen darf direkt umgesetzt werden; Annahmen und Validierung bleiben sichtbar.
- Codeänderungen brauchen Test- oder Validierungsnachweis; bei nichttrivialem Verhalten zuerst Test, Prüfziel oder Testlücke festhalten, danach implementieren, iterieren und erneut validieren.
- UI-, Frontend- und andere visuelle Änderungen brauchen Screenshot oder vergleichbaren visuellen Nachweis vor Abschluss.
- Genehmigungspflichtige Commands müssen Zweck, Umfang und Bezug zur Aufgabe nennen; unklare Approval-Anfragen werden abgelehnt und konkret neu gestellt.
- Jeder Push braucht ein aktualisiertes globales Gantt; Themenänderungen brauchen zusätzlich das jeweilige Themen-Gantt.
- AI-fähige Plugins, Workflows, Usecases, Prompts oder externe Modellaufrufe brauchen eine AI-SBOM-Entscheidung.
- Lokale Runtime-, Hardware- und Middleware-Abhängigkeiten müssen nach `docs/de/minimum-requirements.md` in der SBOM/AI-SBOM gepflegt werden.
- Kultur- und Sprachregeln aus `policies/culture-policy.yaml` verbindlich einhalten.

## Wenn das Muster nicht passt

- Erfassen Sie die Abweichung als Change Request.
- Testen Sie die neue Variante im Pilot.
- Übernehmen Sie sie versioniert in Ihr Unternehmensmodell.
- Optional: geben Sie bewahrte Verbesserungen an das Referenzmuster zurück.

## Betriebsdokumente für Unternehmens-Fork

- `docs/de/operations/fork-and-release-operating-model.md`
- `docs/de/operations/release-sync-playbook.md`
- `docs/de/operations/parallelbetrieb-version-binding.md`
- `docs/de/issues/taxonomy.md`
- `docs/de/einfuehrung-greenfield-brownfield.md`
- `docs/de/service-model/core-vertical-blueprint.md`
- `docs/de/service-model/vertical-starter-process-catalog.md`
- `docs/de/operations/single-repo-refactor-plan.md`
- `docs/de/operations/agile-cadence.md`
- `docs/de/issues/operations.md`
