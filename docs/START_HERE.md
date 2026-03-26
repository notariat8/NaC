# START_HERE: Einfuehrung ohne IT-Vorkenntnisse

## Ziel dieses Dokuments

Dieses Dokument hilft Entscheidern (z. B. Notar, Anwalt, Steuerberater), das Musterrepo als Startpunkt fuer ein eigenes Business-OS zu nutzen.

Sie muessen nicht alle Markdown-Dateien lesen. Fuer den Start reicht der gefuehrte Pfad in `docs/vscode-first-user-path.md` inklusive Formular-Wizard.
Der Wizard arbeitet zustandsbehaftet ueber mehrere Tage und bindet GitHub-Login, Rolle und BPMN-Referenz je Frage ein.

## Begriffsrahmen fuer den Start

- Das Zielmodell ist `Organization as Code (OaC)`.
- Die Steuerung erfolgt ueber `Enterprise GitOps`.
- `OaC8` ist die konkrete Umsetzung in diesem Repository.
- Plattformname: `Enterprise Control Plane`.
- Referenz: `docs/organization-as-code-positioning.md`

## Warum zuerst ein Muster und dann Einfuehrung

- Prozesse werden erst sauber beschrieben und geprueft.
- Danach erfolgt die Einfuehrung im Pilotbetrieb.
- So sinken Risiko, Reibung und Fehlentscheidungen.

## Die ersten 7 Schritte

1. Legen Sie ein eigenes Unternehmens-Repository an.
2. Uebernehmen Sie dieses Muster als Startversion.
3. Definieren Sie Rollen fuer Vorschlag, Pruefung und Freigabe.
4. Aktivieren Sie in `policies/process-policy.yaml` die passenden Branchenmodule.
   Standard fuer den MVP in diesem Repo: `software_company`, `notary`, `wealth_management`.
   Zusaetzlicher MVP-Use-Case: `property_management`.
5. Legen Sie in `policies/culture-policy.yaml` die Sprach- und Gender-Regel fest.
6. Bestaetigen Sie den verbindlichen Technikstack in `policies/technology-policy.yaml`.
7. Bestaetigen Sie Datenschutz- und Secret-Regeln in `policies/data-protection-policy.yaml`.
8. Definieren Sie generische und branchenspezifische Rollen in `policies/role-model-policy.yaml`.
9. Definieren Sie Repo-/Issue-Zugriff und Gastregeln in `policies/access-control-policy.yaml`.
10. Aktivieren Sie revisionssicheren Event-Journal-Betrieb nach `policies/revisionssicherheit-eventstream-policy.yaml`.
11. Fahren Sie den lokalen Startcheck (`docs/startup-verification.md`).
12. Starten Sie das passende Onboarding-Prompt unter `prompts/onboarding/`.
13. Fahren Sie einen Pilot mit 1-2 Kernprozessen vor Vollausrollung.
14. Legen Sie das Betriebsmodell nach `docs/fork-and-release-operating-model.md` verbindlich fest.
15. Definieren Sie den Release-Sync nach `docs/release-sync-playbook.md`.
16. Aktivieren Sie Mischbetrieb-Regeln nach `docs/parallelbetrieb-version-binding.md`.
17. Waehlen Sie die Arbeits-Cadence nach `docs/arbeitsmodell-agile-cadence.md` (Methode `agile|kanban`, Taktoptionen dokumentieren).

Hinweis: Fachlich verbindliche Prozessdarstellungen liegen als BPMN-2.0-Quelle unter `bpmn/`.

## Verfuegbare Branchen-Onboarding-Prompts

- `prompts/onboarding/law-firm-first-setup.md`
- `prompts/onboarding/notary-first-setup.md`
- `prompts/onboarding/property-management-first-setup.md`
- `prompts/onboarding/software-company-first-setup.md`
- `prompts/onboarding/tax-office-first-setup.md`
- `prompts/onboarding/wealth-management-first-setup.md`
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

## Betriebsdokumente fuer Unternehmens-Forks

- `docs/fork-and-release-operating-model.md`
- `docs/release-sync-playbook.md`
- `docs/parallelbetrieb-version-binding.md`
- `docs/issue-taxonomie-pro-repo.md`
- `docs/einfuehrung-greenfield-brownfield.md`
- `docs/service-business-core-vertical-blueprint.md`
- `docs/vertical-starter-prozesskatalog.md`
- `docs/repo-refactor-plan-single-repo-modules.md`
- `docs/arbeitsmodell-agile-cadence.md`
- `docs/access-and-issue-operations.md`
- `docs/revisionssicherheit-eventstreaming.md`
- `docs/eventstream-implementation-templates.md`
- `docs/eventstream-runbook-azure.md`
- `docs/eventstream-runbook-aws.md`
- `docs/eventstream-runbook-gcp.md`
- `docs/eventstream-runbook-oci.md`
- `docs/tenant-ownership-and-eventlock-service.md`
- `docs/avv-checkliste-eventlock-saas.md`
- `docs/function8-service-catalog.md`
- `docs/third-party-operations-and-exit.md`
- `docs/organization-as-code-positioning.md`

## Verbandsmodell und Testat

Ein Verband kann eine konkrete Prozessversion pruefen und empfehlen. Wichtig ist, dass sich ein Testat immer auf eine exakt benannte Version bezieht.
