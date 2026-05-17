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
- Referenz: [docs/de/organization-as-code-positioning.md](organization-as-code-positioning.md)

## Projektpositionierung

Dieses Repository ist der aktive Projektstand fuer `Notariat as Code` mit `NoC`
als konkreter Enterprise Control Plane.

Verbindliche Positionierung:

- Begriff: `Notariat as Code`
- Plattformname: `Enterprise Control Plane`
- erstes Produktversprechen: "Notarielle Vorgangsarten, Plugins, Workflows,
  Rollen, Freigaben und Nachweise laufen deklarativ, auditierbar und
  automatisiert ueber Git."
- aktueller Entwicklungsstand: [roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md)

Ein-Satz-Pitch:

Notariat as Code ist ein Betriebsmodell, in dem notarielle Vorgangsarten,
Plugins, Workflows, Policies und operative Aenderungen deklarativ in Git
beschrieben und ueber eine Enterprise Control Plane in pruefbare Ausfuehrung
ueberfuehrt werden.

## Zielgruppen-Einstieg

| Zielgruppe | Startpfad |
| --- | --- |
| Notariat und fachliche Entscheidung | [docs/de/notar-start.md](notar-start.md) |
| Office-Admin und IT-Betrieb | [docs/de/betriebsstart.md](betriebsstart.md) |
| Fachsystem- und Integrationsseite | [docs/de/integration-start.md](integration-start.md) |
| Pruefung und Standardisierung | [docs/de/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md) |
| Entwicklung und Maintainer | [docs/de/START_HERE.md](START_HERE.md) |

Schnelle Orientierung: [docs/de/reifegrad.md](reifegrad.md),
[docs/de/glossar.md](glossar.md) und
[docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md).

## Prozessklassen

- `formation`: Gruendung, Rollen, Register- und Fristenschritte
- `invoice`: Angebot, Rechnungsentwurf, Freigabe, Versand, Zahlung
- `bookkeeping`: Buchungssatz, Kontierung, Belegbezug, Monatsabschluss
- `tax`: Steuerfall, Aggregation, Voranmeldung, Abgabevorbereitung
- `team`, `role_change`, `joiner_mover`: MVP-Startset fuer Org/Access/Tooling-Onboarding

## Repository-Struktur

### Produktbereiche

- [plugins/](../../plugins) enthaelt installierbare Plugin-Artefakte fuer GPT-Store-Pruefung
  oder Workspace-Installation.
- [workflows/](../../workflows) enthaelt installierbare Skills und deterministische
  Python-Workflows fuer Notariatsablaeufe.
- [usecases/](../../usecases) enthaelt konkrete notarielle Usecases; jeder Usecase
  fuehrt seine eigene KG/DB-Struktur als `knowledge-graph.graph.json` und
  `knowledge-graph.md` im jeweiligen Usecase-Ordner.

### Dokumentation

- [docs/de/notar-start.md](notar-start.md): fachlicher Einstieg fuer Notariate und Entscheider.
- [docs/de/betriebsstart.md](betriebsstart.md): privater Fork, lokale Checks und Betriebsgrenzen.
- [docs/de/integration-start.md](integration-start.md): Fachsystem-, Plugin- und Connector-Pfad.
- [docs/de/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md): Nachvollziehbarkeit fuer Pruefung und Standardisierung.
- [docs/de/reifegrad.md](reifegrad.md): Matrix fuer heute nutzbar, pilotfaehig, geplant und bewusst gesperrt.
- [docs/de/glossar.md](glossar.md): Begriffe fuer Nicht-Technik-Leser.
- [docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md): ein durchgehender Vorgang ohne echte Mandatsdaten.
- [docs/de/START_HERE.md](START_HERE.md): verbindlicher operativer Einstieg.
- [docs/de/fachanwender-guide.md](fachanwender-guide.md): fachliche Einfuehrung ohne IT-Vorkenntnisse.
- [docs/de/minimum-requirements.md](minimum-requirements.md): Mindestvoraussetzungen fuer Base,
  Plugin-Entwicklung und lokalen Notariatsarbeitsplatz.
- [docs/de/eventstream/](eventstream): Event-Journal, EventLock und Cloud-Runbooks.
- [docs/de/issues/](issues): Issue-Taxonomie, Issue-Betrieb und Public-Backlog.
- [docs/de/operations/](operations): Fork/Release, Upstream-Sync, Version-Binding,
  Arbeitsmodell und Repo-Konsolidierung.
- [docs/de/service-model/](service-model): Core/Vertical-Struktur, Provider-Leistungen,
  Tenant-Ownership und Exit.
- [docs/de/plugin-plans/](plugin-plans): Plugin- und Connector-Plaene.
- [docs/de/plugin-operations/](plugin-operations): operative Plugin-Nutzung und Pruefpfade.
- [docs/de/sbom-for-ai.md](sbom-for-ai.md) und [docs/de/sbom-products.md](sbom-products.md): AI-SBOM und
  klassische SBOM-Produkte.
- [docs/de/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md) und
  [docs/de/avv-checkliste-eventlock-saas.md](avv-checkliste-eventlock-saas.md): Datenschutz, AVV und DPA.
- [docs/de/kg-editor-workstream.md](kg-editor-workstream.md): no-code KG-Editor
  fuer Fachpersonal, Patch-Prinzip und Sidecar-Editor-Pfad.

### Governance Und Runtime

- [roadmap/GANTT.md](../../roadmap/GANTT.md) zeigt den globalen Fortschritt fuer Plugins, Workflows und
  Usecases.
- [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md) und [usecases/GANTT.md](../../usecases/GANTT.md) zeigen den
  Fortschritt je Themenbereich.
- [policies/](../../policies) enthaelt Kultur-, Sprach-, Prozess-, Technik-, Datenschutz-,
  Rollen-, Zugriffs-, SBOM- und Provider-Regeln.
- [.cursor/rules/](../../.cursor/rules) und [.github/copilot-instructions.md](../../.github/copilot-instructions.md) spiegeln die
  verbindlichen Agentenregeln.
- [schemas/](../../schemas), [bpmn/](../../bpmn), [processes/](../../processes), [src/](../../src) und [scripts/](../../scripts) enthalten
  strukturierte Prozessantraege, Prozessmodelle, Beispiele, Runtime und lokale
  Werkzeuge.
- [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json)
  beschreibt den implementierten KG-Editor-Vertrag fuer die usecase-lokalen
  Knowledge Graphs.
- [.github/workflows/](../../.github/workflows) enthaelt Governance-, Runtime-, SBOM- und
  Cloud-Parity-Workflows.

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
- Jeder Push muss [roadmap/GANTT.md](../../roadmap/GANTT.md) aktualisieren; Aenderungen unter [plugins/](../../plugins), [workflows/](../../workflows) oder [usecases/](../../usecases) muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.
- Sensible Schritte wie Steuerabgabe oder Zahlungsfreigabe erhalten manuelle Reviewer-Gates.
- Tags und Releases repraesentieren Monats- oder Quartalsabschluesse.
- Erzeugte Artefakte koennen als Actions-Artefakte archiviert werden.
- Laufende Vorgaenge bleiben auf der beim Start gebundenen Prozessversion.

## Hinweise

Dieses Repo ist ein Referenzsystem. Es ersetzt kein vorgeschriebenes Fachsystem, sondern zeigt, wie Git als Orchestrierungs-, Kontroll- und Nachweisschicht fuer kaufmaennische Prozesse dienen kann.

## Lizenz

Dieses Repository steht unter `GPL-3.0` (siehe `LICENSE`).

## Empfohlene Lesereihenfolge fuer Nicht-IT

1. [docs/de/fachanwender-guide.md](fachanwender-guide.md) fuer Zielbild, Nutzen und Einfuehrung.
2. [docs/de/START_HERE.md](START_HERE.md) fuer den konkreten Start im eigenen Unternehmen.
3. [docs/de/business-os.md](business-os.md) fuer Rollen, Prozesslogik und Grenzen.
4. [docs/de/governance.md](governance.md) fuer Freigabe- und Nachweispflichten.

## Branchen-Onboarding

- Kanzlei: [prompts/de/onboarding/law-firm-first-setup.md](../../prompts/de/onboarding/law-firm-first-setup.md)
- Notariat: [prompts/de/onboarding/notary-first-setup.md](../../prompts/de/onboarding/notary-first-setup.md)
- Hausverwaltung: [prompts/de/onboarding/property-management-first-setup.md](../../prompts/de/onboarding/property-management-first-setup.md)
- Softwareunternehmen: [prompts/de/onboarding/software-company-first-setup.md](../../prompts/de/onboarding/software-company-first-setup.md)
- Steuerbuero: [prompts/de/onboarding/tax-office-first-setup.md](../../prompts/de/onboarding/tax-office-first-setup.md)
- Vermoegensverwaltung: [prompts/de/onboarding/wealth-management-first-setup.md](../../prompts/de/onboarding/wealth-management-first-setup.md)
- VS Code + Copilot Start: [prompts/de/onboarding/vscode-copilot-business-os-setup.md](../../prompts/de/onboarding/vscode-copilot-business-os-setup.md)

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

`python scripts/startup_check.py --profile base --ide auto --run-tests`

Fuer Plugin-Entwicklung:

`python scripts/startup_check.py --profile plugin-dev --ide auto`

Fuer Kartenleser-, morris- und XNP-nahe Arbeit:

`python scripts/startup_check.py --profile notary-workstation --ide auto`

## Technik-Regel

In diesem Musterrepo sind nur Techniken aus [policies/technology-policy.yaml](../../policies/technology-policy.yaml) zulaessig.

## Datenschutz-Regel

In diesem Musterrepo sind keine echten personenbezogenen Daten oder Secrets zulaessig.
