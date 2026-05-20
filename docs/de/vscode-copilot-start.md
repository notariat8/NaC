# VS Code + GitHub Copilot: Startleitfaden

## Ziel

Dieser Leitfaden zeigt, wie ein Unternehmen dieses Musterrepo ohne Cursor mit VS Code und GitHub Copilot nutzt.
Der fachliche Rahmen ist `Notariat as Code` mit `Enterprise GitOps`; `NoC` ist die konkrete Umsetzung.

Wenn Sie als Erstnutzer nicht alle Dokumente lesen wollen, nutzen Sie den gefuehrten Pfad:
`docs/de/vscode-first-user-path.md`

## Voraussetzungen

- Mindestvoraussetzungen aus `docs/de/minimum-requirements.md` erfuellt
- GitHub-Organisation oder Unternehmenskonto
- VS Code installiert
- Git installiert
- Python `>= 3.11`
- GitHub CLI `gh` installiert und angemeldet
- Node.js/npm fuer Plugin-Entwicklung
- GitHub Copilot Lizenz aktiv

## Einrichtung in 8 Schritten

1. Erstellen Sie ein eigenes Repository fuer Ihr Unternehmen.
2. Uebernehmen Sie dieses Muster als Basis (Template oder Fork).
3. Oeffnen Sie das Repo in VS Code.
4. Installieren und aktivieren Sie GitHub Copilot im Editor.
5. Lesen Sie `docs/de/START_HERE.md` und `docs/de/minimum-requirements.md`.
6. Fuehren Sie `python scripts/startup_check.py --profile base --ide vscode --run-tests` aus.
   Fuer Plugin-Entwicklung zusaetzlich `python scripts/startup_check.py --profile plugin-dev --ide vscode`.
   Fuer Kartenleser-, morris- oder XNP-nahe Arbeit zusaetzlich `python scripts/startup_check.py --profile notary-workstation --ide vscode`.
7. Bestaetigen Sie die Policies unter `policies/`.
8. Nutzen Sie ein Onboarding-Prompt aus `prompts/de/onboarding/` fuer Ihre Branche.
   Standard fuer den MVP in diesem Repo: `software_company`, `notary`, `wealth_management`.
   Zusaetzlicher MVP-Use-Case: `property_management`.
9. Starten Sie mit einem Pilotprozess und pruefen Sie den Pull-Request-Workflow.
10. Fuehren Sie erst nach erfolgreichem Pilot den breiten Rollout durch.
11. Definieren Sie Fork/Synchronisierung/Mischbetrieb ueber die Betriebsdokumente in `docs/de/`.
12. Pruefen Sie die Produktstruktur: `plugins/` fuer installierbare Artefakte, `workflows/` fuer Skills und Python-Workflows, `usecases/` fuer konkrete notarielle Usecases.
13. Aktualisieren Sie vor jedem Push `roadmap/GANTT.md`; bei Aenderungen an `plugins/`, `workflows/` oder `usecases/` auch das jeweilige Themen-Gantt.
14. Pruefen Sie bei AI-faehigen Aenderungen `docs/de/sbom-for-ai.md` und aktualisieren Sie `sbom/ai/nac-ai-sbom-draft.json`.

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
3) Erstelle einen 30-Tage-Pilotplan fuer Team-, Rollen- und Zugriffsprozesse.
```

## Operative Regeln fuer Copilot-Nutzung

- Prozessaenderungen nur als Pull Request.
- Bei sensiblen Schritten immer Review einplanen.
- Jede Aenderung mit Zweck, Risiko und Verantwortlichem dokumentieren.
- Bei offenem Scope, Issue-getriebener Arbeit oder mehreren relevanten Loesungswegen zuerst erkunden, Plan mit Zweck/Risiko nennen und Bestaetigung einholen.
- Bei klar beauftragten, eng abgegrenzten Aenderungen darf direkt umgesetzt werden; Annahmen und Validierung bleiben sichtbar.
- Codeaenderungen brauchen Test- oder Validierungsnachweis; bei nichttrivialem Verhalten zuerst Test, Pruefziel oder Testluecke festhalten, danach implementieren, iterieren und erneut validieren.
- UI-, Frontend- und andere visuelle Aenderungen brauchen Screenshot oder vergleichbaren visuellen Nachweis vor Abschluss.
- Genehmigungspflichtige Commands muessen Zweck, Umfang und Bezug zur Aufgabe nennen; unklare Approval-Anfragen werden abgelehnt und konkret neu gestellt.
- Jeder Push braucht ein aktualisiertes globales Gantt; Themenaenderungen brauchen zusaetzlich das jeweilige Themen-Gantt.
- AI-faehige Plugins, Workflows, Usecases, Prompts oder externe Modellaufrufe brauchen eine AI-SBOM-Entscheidung.
- Lokale Runtime-, Hardware- und Middleware-Abhaengigkeiten muessen nach `docs/de/minimum-requirements.md` in der SBOM/AI-SBOM gepflegt werden.
- Kultur- und Sprachregeln aus `policies/culture-policy.yaml` verbindlich einhalten.

## Wenn das Muster nicht passt

- Erfassen Sie die Abweichung als Change Request.
- Testen Sie die neue Variante im Pilot.
- Uebernehmen Sie sie versioniert in Ihr Unternehmensmodell.
- Optional: geben Sie bewahrte Verbesserungen an das Referenzmuster zurueck.

## Betriebsdokumente fuer Unternehmens-Fork

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
