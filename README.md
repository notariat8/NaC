# GITaaS: Git als Business-OS

Dieses Repository zeigt, wie Git als zentrales Betriebsmodell fuer Unternehmensprozesse genutzt werden kann. Fachanwender arbeiten ueber ein LLM-Frontend in natuerlicher Sprache, waehrend Git, Pull Requests, Reviews, Actions und signierte Abschluesse die verbindliche Prozessfuehrung uebernehmen.

## Kernidee

- Das LLM erzeugt aus Prompts strukturierte Prozessantraege.
- Git repraesentiert den offiziellen Lebenszyklus eines Geschaeftsvorgangs.
- Python validiert fachliche Regeln und fuehrt wiederholbare Prozesse deterministisch aus.
- GitHub Actions orchestrieren Checks, Freigaben, periodische Jobs und Artefakt-Erzeugung.

## Prozessklassen

- `formation`: Gruendung, Rollen, Register- und Fristenschritte
- `invoice`: Angebot, Rechnungsentwurf, Freigabe, Versand, Zahlung
- `bookkeeping`: Buchungssatz, Kontierung, Belegbezug, Monatsabschluss
- `tax`: Steuerfall, Aggregation, Voranmeldung, Abgabevorbereitung

## Repository-Struktur

- `docs/` erklaert das fachliche Modell und die Architektur.
- `docs/fachanwender-guide.md` erklaert das Modell ohne IT-Vorkenntnisse.
- `docs/START_HERE.md` fuehrt neue Nutzer durch die Einfuehrung.
- `docs/vscode-copilot-start.md` ist der Startpfad fuer VS Code + GitHub Copilot.
- `docs/copilot-quickstart-15min.md` ist die 15-Minuten-Kurzanleitung fuer Copilot.
- `docs/platform-onboarding-matrix.md` sichert plattformuebergreifende Synchronitaet.
- `docs/technology-decision.md` beschreibt verbindliche Technikentscheidungen.
- `docs/sbom-products.md` beschreibt SBOM-Produkte und Lizenzmodell.
- `docs/public-readiness.md` enthaelt den Public-Go-Live-Status.
- `docs/issue-backlog-public.md` enthaelt priorisierte Public-Issues.
- `docs/startup-verification.md` beschreibt den lokalen Startcheck.
- `docs/role-model.md` enthaelt Rollen, Qualifikationen und Approval-Matrix.
- `prompts/` enthaelt Prompt-Standards fuer das LLM-Frontend.
- `prompts/onboarding/` enthaelt gefuehrte Einfuehrungs-Prompts je Branche.
- `scripts/startup_check.py` prueft Setup, Policies und optional Tests.
- `policies/` enthaelt Kultur-, Sprach- und Prozessvorgaben.
- `policies/technology-policy.yaml` definiert den verbindlichen Technikstack.
- `policies/data-protection-policy.yaml` definiert Datenschutz- und Secret-Regeln.
- `policies/sbom-policy.yaml` definiert den verbindlichen SBOM-Standard.
- `policies/role-model-policy.yaml` definiert Rollenrechte und Qualifikations-Gates.
- `.cursor/rules/` enthaelt persistente Cursor-Regeln fuer das Vorgehen.
- `schemas/` definiert strukturierte Prozessantraege.
- `bpmn/` enthaelt fachlich verbindliche BPMN-2.0-Quellmodelle.
- `processes/` enthaelt beispielhafte fachliche Instanzen.
- `src/business_os/` enthaelt die Python-Engine.
- `.github/workflows/` enthaelt Governance- und Runtime-Workflows.
- `.github/workflows/sbom-export.yml` erzeugt SBOM-Artefakte fuer Releases.
- `.github/copilot-instructions.md` enthaelt Repository-Anweisungen fuer Copilot.
- `.github/ISSUE_TEMPLATE/` enthaelt strukturierte Issue-Formulare.

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
- Sensible Schritte wie Steuerabgabe oder Zahlungsfreigabe erhalten manuelle Reviewer-Gates.
- Tags und Releases repraesentieren Monats- oder Quartalsabschluesse.
- Erzeugte Artefakte koennen als Actions-Artefakte archiviert werden.

## Hinweise

Dieses Repo ist ein Referenzsystem. Es ersetzt kein vorgeschriebenes Fachsystem, sondern zeigt, wie Git als Orchestrierungs-, Kontroll- und Nachweisschicht fuer kaufmaennische Prozesse dienen kann.

## Lizenz

Dieses Repository steht unter `GPL-3.0` (siehe `LICENSE`).

## Empfohlene Lesereihenfolge fuer Nicht-IT

1. `docs/fachanwender-guide.md` fuer Zielbild, Nutzen und Einfuehrung.
2. `docs/START_HERE.md` fuer den konkreten Start im eigenen Unternehmen.
3. `docs/business-os.md` fuer Rollen, Prozesslogik und Grenzen.
4. `docs/governance.md` fuer Freigabe- und Nachweispflichten.

## Branchen-Onboarding

- Kanzlei: `prompts/onboarding/law-firm-first-setup.md`
- Notariat: `prompts/onboarding/notary-first-setup.md`
- Steuerbuero: `prompts/onboarding/tax-office-first-setup.md`
- VS Code + Copilot Start: `prompts/onboarding/vscode-copilot-business-os-setup.md`

## Plattform-Regel

Konzeptaenderungen werden immer fuer Cursor und VS Code + Copilot synchron gepflegt.

## Startcheck

Vor produktiver Arbeit:

`python scripts/startup_check.py --ide auto --run-tests`

## Technik-Regel

In diesem Musterrepo sind nur Techniken aus `policies/technology-policy.yaml` zulaessig.

## Datenschutz-Regel

In diesem Musterrepo sind keine echten personenbezogenen Daten oder Secrets zulaessig.
