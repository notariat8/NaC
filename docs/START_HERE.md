# START_HERE: Einfuehrung ohne IT-Vorkenntnisse

## Ziel dieses Dokuments

Dieses Dokument hilft Entscheidern (z. B. Notar, Anwalt, Steuerberater), das Musterrepo als Startpunkt fuer ein eigenes Business-OS zu nutzen.

Sie muessen nicht alle Markdown-Dateien lesen. Fuer den Start reicht der gefuehrte Pfad in `docs/vscode-first-user-path.md` inklusive Formular-Wizard.
Der Wizard arbeitet zustandsbehaftet ueber mehrere Tage und bindet GitHub-Login, Rolle und BPMN-Referenz je Frage ein.

## Warum zuerst ein Muster und dann Einfuehrung

- Prozesse werden erst sauber beschrieben und geprueft.
- Danach erfolgt die Einfuehrung im Pilotbetrieb.
- So sinken Risiko, Reibung und Fehlentscheidungen.

## Die ersten 7 Schritte

1. Legen Sie ein eigenes Unternehmens-Repository an.
2. Uebernehmen Sie dieses Muster als Startversion.
3. Definieren Sie Rollen fuer Vorschlag, Pruefung und Freigabe.
4. Aktivieren Sie in `policies/process-policy.yaml` die passenden Branchenmodule.
5. Legen Sie in `policies/culture-policy.yaml` die Sprach- und Gender-Regel fest.
6. Bestaetigen Sie den verbindlichen Technikstack in `policies/technology-policy.yaml`.
7. Bestaetigen Sie Datenschutz- und Secret-Regeln in `policies/data-protection-policy.yaml`.
8. Definieren Sie generische und branchenspezifische Rollen in `policies/role-model-policy.yaml`.
9. Fahren Sie den lokalen Startcheck (`docs/startup-verification.md`).
10. Starten Sie das passende Onboarding-Prompt unter `prompts/onboarding/`.
11. Fahren Sie einen Pilot mit 1-2 Kernprozessen vor Vollausrollung.

Hinweis: Fachlich verbindliche Prozessdarstellungen liegen als BPMN-2.0-Quelle unter `bpmn/`.

## Verfuegbare Branchen-Onboarding-Prompts

- `prompts/onboarding/law-firm-first-setup.md`
- `prompts/onboarding/notary-first-setup.md`
- `prompts/onboarding/tax-office-first-setup.md`
- `prompts/onboarding/vscode-copilot-business-os-setup.md` (Editor-Start fuer VS Code + Copilot)
- `prompts/onboarding/vscode-first-user-assistant.md` (Formulargefuehrter Erstnutzerpfad)

## Alternative zu Cursor

Wenn Sie statt Cursor VS Code mit GitHub Copilot nutzen, starten Sie mit:

- `docs/vscode-copilot-start.md`
- `docs/vscode-first-user-path.md`
- `docs/copilot-quickstart-15min.md`
- `.github/copilot-instructions.md`

## Plattform-Synchronitaet

Konzept- und Onboarding-Aenderungen werden fuer alle Plattformen synchron gepflegt.
Uebersicht: `docs/platform-onboarding-matrix.md`

## Change Requests und gemeinsames Lernen

- Jede Verbesserung wird als Change Request dokumentiert.
- Jede Aenderung bekommt Begruendung, Review und Versionsnummer.
- Bewaehrte lokale Verbesserungen koennen in den Referenzstandard zurueckfliessen.

## Verbandsmodell und Testat

Ein Verband kann eine konkrete Prozessversion pruefen und empfehlen. Wichtig ist, dass sich ein Testat immer auf eine exakt benannte Version bezieht.
