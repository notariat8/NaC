# NoC: Notariat as Code mit Enterprise Control Plane

Dieses Repository zeigt, wie ein Unternehmen als deklaratives und versioniertes System betrieben werden kann (`Notariat as Code`). Fachanwender arbeiten ueber ein LLM-Frontend in natuerlicher Sprache, waehrend Git, Pull Requests, Reviews, Actions und signierte Abschluesse die verbindliche Prozessfuehrung uebernehmen. `NoC` ist dabei die konkrete Auspraegung als Enterprise Control Plane.

## Kernidee

- Das LLM erzeugt aus Prompts strukturierte Prozessantraege.
- Git repraesentiert den offiziellen Lebenszyklus eines Geschaeftsvorgangs.
- Python validiert fachliche Regeln und fuehrt wiederholbare Prozesse deterministisch aus.
- GitHub Actions orchestrieren Checks, Freigaben, periodische Jobs und Artefakt-Erzeugung.

## Positionierung

- Architekturmodell: `Notariat as Code`
- Betriebsprinzip: `Enterprise GitOps`
- konkrete Umsetzung in diesem Repo: `NoC`
- Plattformname: `Enterprise Control Plane`
- Referenz: `docs/de/organization-as-code-positioning.md`

## Meine konkrete Empfehlung

Wenn du das ernsthaft als Produkt, Plattform oder internes Transformationsmodell aufziehen willst, wuerde ich es so framen:

- Begriff: `Notariat as Code`
- Plattformname: `Enterprise Control Plane`
- erstes Produktversprechen: "Team-, Rollen- und Zugriffsaenderungen laufen deklarativ, auditierbar und automatisiert ueber Git."

Das ist konkret, glaubwuerdig und gross genug, um das Paradigma zu zeigen.

Der Ein-Satz-Pitch:

Notariat as Code ist ein Betriebsmodell, in dem Unternehmensstruktur, Policies und operative Aenderungen deklarativ in Git beschrieben und ueber eine Enterprise Control Plane in reale Systeme reconciled werden.

## Prozessklassen

- `formation`: Gruendung, Rollen, Register- und Fristenschritte
- `invoice`: Angebot, Rechnungsentwurf, Freigabe, Versand, Zahlung
- `bookkeeping`: Buchungssatz, Kontierung, Belegbezug, Monatsabschluss
- `tax`: Steuerfall, Aggregation, Voranmeldung, Abgabevorbereitung
- `team`, `role_change`, `joiner_mover`: MVP-Startset fuer Org/Access/Tooling-Onboarding

## Repository-Struktur

- `docs/de/` erklaert das fachliche Modell und die Architektur.
- `roadmap/GANTT.md` zeigt den globalen Fortschritt fuer Plugins, Workflows und Usecases.
- `plugins/GANTT.md`, `workflows/GANTT.md` und `usecases/GANTT.md` zeigen den Fortschritt je Themenbereich.
- `plugins/` enthaelt installierbare Plugin-Artefakte fuer GPT-Store-Pruefung oder Workspace-Installation.
- `workflows/` enthaelt installierbare Skills und deterministische Python-Workflows fuer Notariatsablaeufe.
- `usecases/` enthaelt konkrete notarielle Usecases wie Online-GmbH-Gruendung, AO52-Gemeinnuetzigkeitsgruendung, Grundstueckskaufvertrag und Testament.
- `docs/de/fachanwender-guide.md` erklaert das Modell ohne IT-Vorkenntnisse.
- `docs/de/START_HERE.md` fuehrt neue Nutzer durch die Einfuehrung.
- `docs/de/vscode-copilot-start.md` ist der Startpfad fuer VS Code + GitHub Copilot.
- `docs/de/vscode-first-user-path.md` fuehrt Erstnutzer mit einem Formularpfad.
- `docs/de/copilot-quickstart-15min.md` ist die 15-Minuten-Kurzanleitung fuer Copilot.
- `docs/de/platform-onboarding-matrix.md` sichert plattformuebergreifende Synchronitaet.
- `docs/de/fork-and-release-operating-model.md` definiert Upstream/Fork/Domaenen-Betrieb.
- `docs/de/release-sync-playbook.md` beschreibt den verbindlichen Upstream-Sync-Ablauf.
- `docs/de/parallelbetrieb-version-binding.md` regelt Alt-/Neu-Mischbetrieb je Vorgangsstart.
- `docs/de/issue-taxonomie-pro-repo.md` definiert Issue-Fuehrung ueber mehrere Repos.
- `docs/de/einfuehrung-greenfield-brownfield.md` trennt Einfuehrungspfade fuer Greenfield/Brownfield.
- `docs/de/service-business-core-vertical-blueprint.md` beschreibt Core-und-Vertical-Struktur fuer Dienstleister.
- `docs/de/vertical-starter-prozesskatalog.md` liefert Starter-Prozesse fuer fuenf Verticals.
- `docs/de/repo-refactor-plan-single-repo-modules.md` beschreibt Zielstruktur und Migration in einem Repo.
- `docs/de/arbeitsmodell-agile-cadence.md` definiert Arbeits-Cadence fuer `agile` und `kanban`.
- `docs/de/access-and-issue-operations.md` regelt Rollen, Zugriffe und repo-uebergreifende Issue-Uebersicht.
- `docs/de/revisionssicherheit-eventstreaming.md` definiert revisionssicheren Event-Journal-Betrieb.
- `docs/de/eventstream-implementation-templates.md` liefert konkrete AWS-/Azure-/GCP-/OCI-Implementierungsvorlagen.
- `docs/de/eventstream-runbook-azure.md` ist das konkrete Azure-Betriebsrunbook.
- `docs/de/eventstream-runbook-aws.md` ist das konkrete AWS-Betriebsrunbook.
- `docs/de/eventstream-runbook-gcp.md` ist das konkrete GCP-Betriebsrunbook.
- `docs/de/eventstream-runbook-oci.md` ist das konkrete OCI-Betriebsrunbook.
- `docs/de/tenant-ownership-and-eventlock-service.md` beschreibt Tenant-Owner- und Service-Modell.
- `docs/de/avv-checkliste-eventlock-saas.md` liefert die AVV-Checkliste fuer EventLock-SaaS.
- `docs/de/function8-service-catalog.md` listet alle Function8-Leistungen transparent.
- `docs/de/third-party-operations-and-exit.md` beschreibt Drittbetrieb und Exit ohne Lock-in.
- `docs/de/organization-as-code-positioning.md` schaerft den Begriffsrahmen Notariat/GitOps/NoC.
- `docs/de/gpt-marketplace-operating-model.md` trennt Public-GPT-Store-, Action-, Workspace-App- und lokale Plugin-Kanaele.
- `docs/de/noc-enterprise-control-plane-mvp.md` beschreibt MVP-Scope, 6-Monats-Plan und KPI-Set.
- `docs/de/quality-gate.md` beschreibt den deterministischen Pruefpfad fuer lokale und CI-Gates.
- `docs/de/technology-decision.md` beschreibt verbindliche Technikentscheidungen.
- `docs/de/sbom-products.md` beschreibt SBOM-Produkte und Lizenzmodell.
- `docs/de/public-readiness.md` enthaelt den Public-Go-Live-Status.
- `docs/de/issue-backlog-public.md` enthaelt priorisierte Public-Issues.
- `docs/de/startup-verification.md` beschreibt den lokalen Startcheck.
- `docs/de/role-model.md` enthaelt Rollen, Qualifikationen und Approval-Matrix.
- `docs/de/github-identity-role-model.md` erklaert GitHub-Login zu Rollenreferenz.
- `prompts/de/` enthaelt Prompt-Standards fuer das LLM-Frontend.
- `prompts/de/onboarding/` enthaelt gefuehrte Einfuehrungs-Prompts je Branche.
- `prompts/de/onboarding/vscode-first-user-assistant.md` ist der gefuehrte Erstnutzer-Prompt.
- `scripts/startup_check.py` prueft Setup, Policies und optional Tests.
- `scripts/onboarding_wizard.py` speichert Onboarding-Status ueber mehrere Tage/Personen.
- `policies/` enthaelt Kultur-, Sprach- und Prozessvorgaben.
- `policies/technology-policy.yaml` definiert den verbindlichen Technikstack.
- `policies/data-protection-policy.yaml` definiert Datenschutz- und Secret-Regeln.
- `policies/sbom-policy.yaml` definiert den verbindlichen SBOM-Standard.
- `policies/role-model-policy.yaml` definiert Rollenrechte und Qualifikations-Gates.
- `policies/access-control-policy.yaml` definiert verbindlich Zugriff, Sichtbarkeit und Gastregeln.
- `policies/revisionssicherheit-eventstream-policy.yaml` definiert Eventstream- und WORM-Pflichten.
- `policies/tenant-ownership-policy.yaml` definiert Tenant-Ownership und Provider/Kunden-Verantwortung.
- `policies/provider-open-services-policy.yaml` erzwingt offene Leistungsdokumentation und Ersetzbarkeit.
- `policies/onboarding-flow.json` definiert Fragen, Phasen und Rollenwissen fuer Onboarding.
- `policies/onboarding-diagrams.json` definiert BPMN-/Mermaid-Referenzen je Frage.
- `policies/github-identity-registry.json` mappt GitHub-Login auf technische Rollen.
- `.cursor/rules/` enthaelt persistente Cursor-Regeln fuer das Vorgehen.
- `.cursor/rules/11-cloud-runbook-parity.mdc` erzwingt Pflegeparitaet fuer AWS, Azure, GCP, OCI.
- `.cursor/rules/12-open-service-portability.mdc` erzwingt offene Leistungsdoku und Ersetzbarkeit.
- `schemas/` definiert strukturierte Prozessantraege.
- `bpmn/` enthaelt fachlich verbindliche BPMN-2.0-Quellmodelle.
- `processes/` enthaelt beispielhafte fachliche Instanzen.
- `src/business_os/` enthaelt die Python-Engine.
- `.github/workflows/` enthaelt Governance- und Runtime-Workflows.
- `.github/workflows/sbom-export.yml` erzeugt SBOM-Artefakte fuer Releases.
- `.github/copilot-instructions.md` enthaelt Repository-Anweisungen fuer Copilot.
- `.github/ISSUE_TEMPLATE/` enthaelt strukturierte Issue-Formulare.
- `.github/workflows/governance-policy-sync.yml` erzwingt Policy-zu-Rule-Synchronitaet.

## Schnellstart

```bash
python -m business_os validate processes/invoices/2026/REQ-2026-0001.json
python -m business_os render-summary processes/invoices/2026/REQ-2026-0001.json
python -m business_os monthly-close --year 2026 --month 3
```

## Betriebsmodell

1. Ein Fachanwender beschreibt einen Vorgang per Prompt.
2. Das LLM erstellt einen Prozessantrag als JSON-Datei und eroeffnet einen Branch oder Pull Request.
3. Die Python-Engine validiert Schema, Zustandsuebergaenge und Idempotenz.
4. GitHub Actions fuehren automatische Checks aus und fordern Freigaben an.
5. Nach dem Merge nach `main` gilt der Vorgang als verbindlich freigegeben und kann exportiert, archiviert oder periodisch aggregiert werden.

## Governance

- `main` ist geschuetzt und wird nur per Pull Request aktualisiert.
- Jeder Push muss `roadmap/GANTT.md` aktualisieren; Aenderungen unter `plugins/`, `workflows/` oder `usecases/` muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.
- Sensible Schritte wie Steuerabgabe oder Zahlungsfreigabe erhalten manuelle Reviewer-Gates.
- Tags und Releases repraesentieren Monats- oder Quartalsabschluesse.
- Erzeugte Artefakte koennen als Actions-Artefakte archiviert werden.
- Laufende Vorgaenge bleiben auf der beim Start gebundenen Prozessversion.

## Hinweise

Dieses Repo ist ein Referenzsystem. Es ersetzt kein vorgeschriebenes Fachsystem, sondern zeigt, wie Git als Orchestrierungs-, Kontroll- und Nachweisschicht fuer kaufmaennische Prozesse dienen kann.

## Lizenz

Dieses Repository steht unter `GPL-3.0` (siehe `LICENSE`).

## Empfohlene Lesereihenfolge fuer Nicht-IT

1. `docs/de/fachanwender-guide.md` fuer Zielbild, Nutzen und Einfuehrung.
2. `docs/de/START_HERE.md` fuer den konkreten Start im eigenen Unternehmen.
3. `docs/de/business-os.md` fuer Rollen, Prozesslogik und Grenzen.
4. `docs/de/governance.md` fuer Freigabe- und Nachweispflichten.

## Branchen-Onboarding

- Kanzlei: `prompts/de/onboarding/law-firm-first-setup.md`
- Notariat: `prompts/de/onboarding/notary-first-setup.md`
- Hausverwaltung: `prompts/de/onboarding/property-management-first-setup.md`
- Softwareunternehmen: `prompts/de/onboarding/software-company-first-setup.md`
- Steuerbuero: `prompts/de/onboarding/tax-office-first-setup.md`
- Vermoegensverwaltung: `prompts/de/onboarding/wealth-management-first-setup.md`
- VS Code + Copilot Start: `prompts/de/onboarding/vscode-copilot-business-os-setup.md`

Default fuer synchrone MVP-Pfade in diesem Repo:

- `software_company`
- `notary`
- `wealth_management`

Zusaetzlicher MVP-Use-Case:

- `property_management`

## Plattform-Regel

Konzeptaenderungen werden immer fuer Cursor und VS Code + Copilot synchron gepflegt.

## Startcheck

Vor produktiver Arbeit:

`python scripts/startup_check.py --ide auto --run-tests`

## Technik-Regel

In diesem Musterrepo sind nur Techniken aus `policies/technology-policy.yaml` zulaessig.

## Datenschutz-Regel

In diesem Musterrepo sind keine echten personenbezogenen Daten oder Secrets zulaessig.
