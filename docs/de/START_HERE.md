# START_HERE: Einfuehrung ohne IT-Vorkenntnisse

## Ziel dieses Dokuments

Dieses Dokument hilft Entscheidern (z. B. Notar, Anwalt, Steuerberater), das Musterrepo als Startpunkt fuer ein eigenes Business-OS zu nutzen.

Sie muessen nicht alle Markdown-Dateien lesen. Fuer den Start reicht der gefuehrte Pfad in `docs/de/vscode-first-user-path.md` inklusive Formular-Wizard.
Der Wizard arbeitet zustandsbehaftet ueber mehrere Tage und bindet GitHub-Login, Rolle und BPMN-Referenz je Frage ein.

## Begriffsrahmen fuer den Start

- Das Zielmodell ist `Notariat as Code (NoC)`.
- Die Steuerung erfolgt ueber `Enterprise GitOps`.
- `NoC` ist die konkrete Umsetzung in diesem Repository.
- Plattformname: `Enterprise Control Plane`.
- Referenz: `docs/de/organization-as-code-positioning.md`

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
11. Fahren Sie den lokalen Startcheck (`docs/de/startup-verification.md`).
12. Starten Sie das passende Onboarding-Prompt unter `prompts/de/onboarding/`.
13. Fahren Sie einen Pilot mit 1-2 Kernprozessen vor Vollausrollung.
14. Legen Sie das Betriebsmodell nach `docs/de/fork-and-release-operating-model.md` verbindlich fest.
15. Definieren Sie den Release-Sync nach `docs/de/release-sync-playbook.md`.
16. Aktivieren Sie Mischbetrieb-Regeln nach `docs/de/parallelbetrieb-version-binding.md`.
17. Waehlen Sie die Arbeits-Cadence nach `docs/de/arbeitsmodell-agile-cadence.md` (Methode `agile|kanban`, Taktoptionen dokumentieren).
18. Pruefen Sie die Produktstruktur: `plugins/` fuer installierbare Artefakte, `workflows/` fuer Skills und Python-Workflows, `usecases/` fuer notarielle Usecases.
19. Pruefen Sie vor jedem Push, dass `roadmap/GANTT.md` und bei Aenderungen an `plugins/`, `workflows/` oder `usecases/` auch das passende Themen-Gantt aktualisiert ist.

Hinweis: Fachlich verbindliche Prozessdarstellungen liegen als BPMN-2.0-Quelle unter `bpmn/`.

## Verfuegbare Branchen-Onboarding-Prompts

- `prompts/de/onboarding/law-firm-first-setup.md`
- `prompts/de/onboarding/notary-first-setup.md`
- `prompts/de/onboarding/property-management-first-setup.md`
- `prompts/de/onboarding/software-company-first-setup.md`
- `prompts/de/onboarding/tax-office-first-setup.md`
- `prompts/de/onboarding/wealth-management-first-setup.md`
- `prompts/de/onboarding/vscode-copilot-business-os-setup.md` (Editor-Start fuer VS Code + Copilot)
- `prompts/de/onboarding/vscode-first-user-assistant.md` (Formulargefuehrter Erstnutzerpfad)

## Alternative zu Cursor

Wenn Sie statt Cursor VS Code mit GitHub Copilot nutzen, starten Sie mit:

- `docs/de/vscode-copilot-start.md`
- `docs/de/vscode-first-user-path.md`
- `docs/de/copilot-quickstart-15min.md`
- `.github/copilot-instructions.md`

## Plattform-Synchronitaet

Konzept- und Onboarding-Aenderungen werden fuer alle Plattformen synchron gepflegt.
Uebersicht: `docs/de/platform-onboarding-matrix.md`

## Abschlussregel

Ein Update gilt erst als abgeschlossen, wenn die Aenderung validiert, committed, zu GitHub gepusht und in den Zielbranch gemerged wurde. Lokale Aenderungen oder unge-mergte PR-Branches sind nur Zwischenstand.

## Change Requests und gemeinsames Lernen

- Jede Verbesserung wird als Change Request dokumentiert.
- Jede Aenderung bekommt Begruendung, Review und Versionsnummer.
- Bewaehrte lokale Verbesserungen koennen in den Referenzstandard zurueckfliessen.

## Betriebsdokumente fuer Unternehmens-Forks

- `docs/de/fork-and-release-operating-model.md`
- `docs/de/release-sync-playbook.md`
- `docs/de/parallelbetrieb-version-binding.md`
- `docs/de/issue-taxonomie-pro-repo.md`
- `docs/de/einfuehrung-greenfield-brownfield.md`
- `docs/de/service-business-core-vertical-blueprint.md`
- `docs/de/vertical-starter-prozesskatalog.md`
- `docs/de/repo-refactor-plan-single-repo-modules.md`
- `docs/de/arbeitsmodell-agile-cadence.md`
- `docs/de/access-and-issue-operations.md`
- `docs/de/revisionssicherheit-eventstreaming.md`
- `docs/de/eventstream-implementation-templates.md`
- `docs/de/eventstream-runbook-azure.md`
- `docs/de/eventstream-runbook-aws.md`
- `docs/de/eventstream-runbook-gcp.md`
- `docs/de/eventstream-runbook-oci.md`
- `docs/de/tenant-ownership-and-eventlock-service.md`
- `docs/de/avv-checkliste-eventlock-saas.md`
- `docs/de/function8-service-catalog.md`
- `docs/de/third-party-operations-and-exit.md`
- `docs/de/organization-as-code-positioning.md`

## Verbandsmodell und Testat

Ein Verband kann eine konkrete Prozessversion pruefen und empfehlen. Wichtig ist, dass sich ein Testat immer auf eine exakt benannte Version bezieht.
