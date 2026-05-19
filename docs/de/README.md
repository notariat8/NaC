# NaC: Notariat as Code mit Enterprise Control Plane

Dieses Repository zeigt, wie ein Unternehmen als deklaratives und versioniertes System betrieben werden kann (`Notariat as Code`). Fachanwender arbeiten über ein LLM-Frontend in natürlicher Sprache, während Git, Pull Requests, Reviews, Actions und signierte Abschlüsse die verbindliche Prozessführung übernehmen. `NaC` ist dabei die konkrete Ausprägung als Enterprise Control Plane.

## Kernidee

- Das LLM erzeugt aus Prompts strukturierte Prozessanträge.
- Git repräsentiert den offiziellen Lebenszyklus eines Geschäftsvorgangs.
- Python validiert fachliche Regeln und führt wiederholbare Prozesse deterministisch aus.
- GitHub Actions orchestrieren Checks, Freigaben, periodische Jobs und Artefakt-Erzeugung.

## Positionierung

- Architekturmodell: `Notariat as Code`
- Betriebsprinzip: `Enterprise GitOps`
- konkrete Umsetzung in diesem Repo: `NaC`
- Plattformname: `Enterprise Control Plane`
- Referenz: [docs/de/organization-as-code-positioning.md](organization-as-code-positioning.md)

## Projektpositionierung

Dieses Repository ist der aktive Projektstand für `Notariat as Code` mit `NaC`
als konkreter Enterprise Control Plane.

Verbindliche Positionierung:

- Begriff: `Notariat as Code`
- Plattformname: `Enterprise Control Plane`
- erstes Produktversprechen: "Notarielle Vorgangsarten, Plugins, Workflows,
  Rollen, Freigaben und Nachweise laufen deklarativ, auditierbar und
  automatisiert über Git."
- aktueller Entwicklungsstand: [roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md)

Ein-Satz-Pitch:

Notariat as Code ist ein Betriebsmodell, in dem notarielle Vorgangsarten,
Plugins, Workflows, Policies und operative Änderungen deklarativ in Git
beschrieben und über eine Enterprise Control Plane in prüfbare Ausführung
überführt werden.

## Zielgruppen-Einstieg

| Zielgruppe | Startpfad |
| --- | --- |
| Notariat und fachliche Entscheidung | [docs/de/notar-start.md](notar-start.md) |
| Office-Admin und IT-Betrieb | [docs/de/betriebsstart.md](betriebsstart.md) |
| Fachsystem- und Integrationsseite | [docs/de/integration-start.md](integration-start.md) |
| Prüfung und Standardisierung | [pruefung-standardisierung-start.md](pruefung-standardisierung-start.md) |
| Entwicklung und Maintainer | [docs/de/START_HERE.md](START_HERE.md) |

Schnelle Orientierung: [cli.md](cli.md), [ausfuehrungsmodell.md](ausfuehrungsmodell.md),
[docs/de/reifegrad.md](reifegrad.md), [docs/de/glossar.md](glossar.md) und
[docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md).

## Prozessklassen

- `formation`: Gründung, Rollen, Register- und Fristenschritte
- `invoice`: Angebot, Rechnungsentwurf, Freigabe, Versand, Zahlung
- `bookkeeping`: Buchungssatz, Kontierung, Belegbezug, Monatsabschluss
- `tax`: Steuerfall, Aggregation, Voranmeldung, Abgabevorbereitung
- `team`, `role_change`, `joiner_mover`: MVP-Startset für Org/Access/Tooling-Onboarding

## Repository-Struktur

### Produktbereiche

- [plugins/](../../plugins) enthält installierbare Plugin-Artefakte für GPT-Store-Prüfung
  oder Workspace-Installation.
- [workflows/](../../workflows) enthält installierbare Skills und deterministische
  Python-Workflows für Notariatsabläufe.
- [usecases/](../../usecases) enthält konkrete notarielle Usecases; jeder Usecase
  führt seine eigene KG/DB-Struktur als `knowledge-graph.graph.json` und
  `knowledge-graph.md` im jeweiligen Usecase-Ordner.

### Dokumentation

- [docs/de/notar-start.md](notar-start.md): fachlicher Einstieg für Notariate und Entscheider.
- [docs/de/betriebsstart.md](betriebsstart.md): privater Fork, lokale Checks und Betriebsgrenzen.
- [docs/de/integration-start.md](integration-start.md): Fachsystem-, Plugin- und Connector-Pfad.
- [pruefung-standardisierung-start.md](pruefung-standardisierung-start.md): Nachvollziehbarkeit für Prüfung und Standardisierung.
- [ausfuehrungsmodell.md](ausfuehrungsmodell.md): wie Bürooberfläche und
  prüfbarer NaC-Kern zusammenspielen.
- [cli.md](cli.md): technische `nac`-Steuerfläche hinter der Bürooberfläche,
  erste Befehle und Architekturregel für neue Funktionen.
- [bpmn-js-business-layer.md](bpmn-js-business-layer.md): warum der Business
  Layer BPMN-first, bpmn-js-editiert und Python-validiert wird.
- [lokaler-webserver.md](lokaler-webserver.md): lokaler Einstieg für grafische
  BPMN- und KG-Ausgaben.
- [webapp-ohne-zugriff.md](webapp-ohne-zugriff.md): bebilderte Erklärung der
  Operator-Webapp für Leser ohne lokale Webapp.
- [docs/de/reifegrad.md](reifegrad.md): Matrix für heute nutzbar, pilotfähig, geplant und bewusst gesperrt.
- [docs/de/glossar.md](glossar.md): Begriffe für Nicht-Technik-Leser.
- [docs/de/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md): ein durchgehender Vorgang ohne echte Mandatsdaten.
- [docs/de/START_HERE.md](START_HERE.md): verbindlicher operativer Einstieg.
- [docs/de/fachanwender-guide.md](fachanwender-guide.md): fachliche Einführung ohne IT-Vorkenntnisse.
- [docs/de/minimum-requirements.md](minimum-requirements.md): Mindestvoraussetzungen für Base,
  Plugin-Entwicklung und lokalen Notariatsarbeitsplatz.
- [docs/de/eventstream/](eventstream): Event-Journal, EventLock und Cloud-Runbooks.
- [docs/de/issues/](issues): Issue-Taxonomie, Issue-Betrieb und Public-Backlog.
- [docs/de/operations/](operations): Fork/Release, Upstream-Sync, Version-Binding,
  Arbeitsmodell und Repo-Konsolidierung.
- [docs/de/service-model/](service-model): Core/Vertical-Struktur, Provider-Leistungen,
  Tenant-Ownership und Exit.
- [docs/de/plugin-plans/](plugin-plans): Plugin- und Connector-Pläne.
- [docs/de/plugin-operations/](plugin-operations): operative Plugin-Nutzung und Prüfpfade.
- [docs/de/sbom-for-ai.md](sbom-for-ai.md) und [docs/de/sbom-products.md](sbom-products.md): AI-SBOM und
  klassische SBOM-Produkte.
- [docs/de/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md) und
  [docs/de/avv-checkliste-eventlock-saas.md](avv-checkliste-eventlock-saas.md): Datenschutz, AVV und DPA.
- [docs/de/kg-editor-workstream.md](kg-editor-workstream.md): no-code KG-Editor
  für Fachpersonal, Patch-Prinzip und Sidecar-Editor-Pfad.
- [docs/de/datenrepo-demo8notariat.md](datenrepo-demo8notariat.md): getrenntes
  Demo-Datenrepo für synthetische NaC-Vorgänge und späteren Sovereign-Git-Wechsel.

### Governance Und Runtime

- [roadmap/GANTT.md](../../roadmap/GANTT.md) zeigt den globalen Fortschritt für Plugins, Workflows und
  Usecases.
- [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md) und [usecases/GANTT.md](../../usecases/GANTT.md) zeigen den
  Fortschritt je Themenbereich.
- [policies/](../../policies) enthält Kultur-, Sprach-, Prozess-, Technik-, Datenschutz-,
  Rollen-, Zugriffs-, SBOM- und Provider-Regeln.
- [.cursor/rules/](../../.cursor/rules) und [.github/copilot-instructions.md](../../.github/copilot-instructions.md) spiegeln die
  verbindlichen Agentenregeln.
- [schemas/](../../schemas), [bpmn/](../../bpmn), [processes/](../../processes), [src/](../../src) und [scripts/](../../scripts) enthalten
  strukturierte Prozessanträge, Prozessmodelle, Beispiele, Runtime und lokale
  Werkzeuge.
- [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json)
  beschreibt den implementierten KG-Editor-Vertrag für die usecase-lokalen
  Knowledge Graphs.
- [.github/workflows/](../../.github/workflows) enthält Governance-, Runtime-, SBOM- und
  Cloud-Parity-Workflows.

## Schnellstart

```bash
python scripts/nac.py status
python scripts/nac.py process validate processes/invoices/2026/REQ-2026-0001.json
python scripts/nac.py process render-summary processes/invoices/2026/REQ-2026-0001.json
python scripts/nac.py process monthly-close --year 2026 --month 3
```

## Betriebsmodell

1. Ein Fachanwender beschreibt einen Vorgang per Prompt.
2. Das LLM erstellt einen Prozessantrag als JSON-Datei und eröffnet einen Branch oder Pull Request.
3. Die Python-Engine validiert Schema, Zustandsübergänge und Idempotenz.
4. GitHub Actions führen automatische Checks aus und fordern Freigaben an.
5. Nach dem Merge nach `main` gilt der Vorgang als verbindlich freigegeben und kann exportiert, archiviert oder periodisch aggregiert werden.

## Governance

- `main` ist geschützt und wird nur per Pull Request aktualisiert.
- Jeder Push muss [roadmap/GANTT.md](../../roadmap/GANTT.md) aktualisieren; Änderungen unter [plugins/](../../plugins), [workflows/](../../workflows) oder [usecases/](../../usecases) müssen zusätzlich das jeweilige Themen-Gantt aktualisieren.
- Sensible Schritte wie Steuerabgabe oder Zahlungsfreigabe erhalten manuelle Reviewer-Gates.
- Tags und Releases repräsentieren Monats- oder Quartalsabschlüsse.
- Erzeugte Artefakte können als Actions-Artefakte archiviert werden.
- Laufende Vorgänge bleiben auf der beim Start gebundenen Prozessversion.

## Hinweise

Dieses Repo ist ein Referenzsystem. Es ersetzt kein vorgeschriebenes Fachsystem, sondern zeigt, wie Git als Orchestrierungs-, Kontroll- und Nachweisschicht für kaufmännische Prozesse dienen kann.

## Lizenz

NaC trennt Software- und Dokumentationslizenz:

- Code, Plugins, Workflows, Validatoren, Schemas und ausführbare Beispiele:
  `AGPL-3.0-or-later`
- Dokumentation, Diagramme, Policies, Roadmap, Prompts und fachliche Usecases:
  `CC-BY-4.0`

Die verbindliche Zuordnung steht in [LICENSES/README.md](../../LICENSES/README.md).
Bitte die Attribution aus [NOTICE](../../NOTICE), [AUTHORS.md](../../AUTHORS.md)
und [CITATION.cff](../../CITATION.cff) erhalten. Marken- und Namensgrenzen
stehen in [TRADEMARK.md](../../TRADEMARK.md).

## Empfohlene Lesereihenfolge für Nicht-IT

1. [docs/de/fachanwender-guide.md](fachanwender-guide.md) für Zielbild, Nutzen und Einführung.
2. [docs/de/START_HERE.md](START_HERE.md) für den konkreten Start im eigenen Unternehmen.
3. [docs/de/business-os.md](business-os.md) für Rollen, Prozesslogik und Grenzen.
4. [docs/de/governance.md](governance.md) für Freigabe- und Nachweispflichten.

## Branchen-Onboarding

- Kanzlei: [prompts/de/onboarding/law-firm-first-setup.md](../../prompts/de/onboarding/law-firm-first-setup.md)
- Notariat: [prompts/de/onboarding/notary-first-setup.md](../../prompts/de/onboarding/notary-first-setup.md)
- Hausverwaltung: [prompts/de/onboarding/property-management-first-setup.md](../../prompts/de/onboarding/property-management-first-setup.md)
- Softwareunternehmen: [prompts/de/onboarding/software-company-first-setup.md](../../prompts/de/onboarding/software-company-first-setup.md)
- Steuerbüro: [prompts/de/onboarding/tax-office-first-setup.md](../../prompts/de/onboarding/tax-office-first-setup.md)
- Vermögensverwaltung: [prompts/de/onboarding/wealth-management-first-setup.md](../../prompts/de/onboarding/wealth-management-first-setup.md)
- VS Code + Copilot Start: [prompts/de/onboarding/vscode-copilot-business-os-setup.md](../../prompts/de/onboarding/vscode-copilot-business-os-setup.md)

Default für synchrone MVP-Pfade in diesem Repo:

- `software_company`
- `notary`
- `wealth_management`

Zusätzlicher MVP-Use-Case:

- `property_management`

## Plattform-Regel

Konzeptänderungen werden immer für Cursor und VS Code + Copilot synchron gepflegt.

## Startcheck

Vor produktiver Arbeit:

`python scripts/nac.py doctor --profile strict`

Für Plugin-Entwicklung:

`python scripts/startup_check.py --profile plugin-dev --ide auto`

Für Kartenleser-, morris- und XNP-nahe Arbeit:

`python scripts/startup_check.py --profile notary-workstation --ide auto`

## Technik-Regel

In diesem Musterrepo sind nur Techniken aus [policies/technology-policy.yaml](../../policies/technology-policy.yaml) zulässig.

## Datenschutz-Regel

In diesem Musterrepo sind keine echten personenbezogenen Daten oder Secrets zulässig.
