# NaC: Notariat as Code mit Enterprise Control Plane

Dieses Repository zeigt, wie ein Notariat notarielle Vorgangsarten deklarativ,
versioniert und prüfbar führen kann (`Notariat as Code`). Fachanwender arbeiten
über ein LLM-Frontend in natürlicher Sprache, während Git, Pull Requests,
Reviews, Actions und signierte Abschlüsse die verbindliche Prozessführung
übernehmen. `NaC` ist dabei die konkrete Ausprägung als Enterprise Control
Plane.

## Kernidee

- Das LLM erzeugt aus Prompts strukturierte Prozessanträge.
- Git repräsentiert den offiziellen Lebenszyklus eines notariellen Vorgangs.
- Python validiert fachliche Regeln und führt wiederholbare Prüfungen deterministisch aus.
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
- Regelarchitektur und Härtegrade: [docs/de/regelarchitektur.md](regelarchitektur.md)

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

## Usecase-Klassen

Produktbeispiele kommen ausschließlich aus [usecases/](../../usecases), zum Beispiel:

- `immobilienkaufvertrag`
- `unterschriftsbeglaubigung`
- `online-gmbh-gruendung`
- `handelsregisteranmeldung`

Ältere JSON-Prozessartefakte unter [processes/](../../processes) sind technische
Runtime-Fixtures und keine zusätzlichen fachlichen NaC-Beispiele.

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
- [authenticated-webapp-operating-model.md](authenticated-webapp-operating-model.md):
  Zielbild für GitHub Pages als statische Leseschicht, authentifizierte Webapp,
  OCI-Identity-Domains, Karten-Gates und mobile sichere Dokumentlinks.
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
- [docs/de/service-model/](service-model): Notariats-Scope, Betriebsleistungen,
  Tenant-Ownership und Exit.
- [docs/de/plugin-plans/](plugin-plans): Plugin- und Connector-Pläne.
- [docs/de/plugin-operations/](plugin-operations): operative Plugin-Nutzung und Prüfpfade.
- [docs/de/sbom-for-ai.md](sbom-for-ai.md) und [docs/de/sbom-products.md](sbom-products.md): AI-SBOM und
  klassische SBOM-Produkte.
- [docs/de/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md) und
  [docs/de/avv-checkliste-eventlock-saas.md](avv-checkliste-eventlock-saas.md): Datenschutz, AVV und DPA.
- [docs/de/openai-enterprise-eu-residency.md](openai-enterprise-eu-residency.md):
  Beschaffungs- und Freigabepfad für ChatGPT Enterprise, API-EU-Datenresidenz
  und Codex-Kosten.
- [docs/de/itil5-mapping.md](itil5-mapping.md): Einordnung von NaC gegen ITIL 5 als
  Betriebs-, Revisions- und Audit-Sprache ohne Zertifizierungsbehauptung.
- [docs/de/kg-editor-workstream.md](kg-editor-workstream.md): no-code KG-Editor
  für Fachpersonal, Patch-Prinzip und Sidecar-Editor-Pfad.
- [docs/de/codex-parallel-review-workflow.md](codex-parallel-review-workflow.md):
  expliziter Parallel-Review mit read-only Codex-Agenten für KG, BPMN,
  Governance, Doku-Parität und Validierung.
- [docs/de/datenrepo-demo8notariat.md](datenrepo-demo8notariat.md): getrenntes
  Demo-Datenrepo für synthetische NaC-Vorgänge und späteren Sovereign-Git-Wechsel.
- [docs/de/demo/](demo/): Notarkammer-Demo-Einstieg mit Preflight,
  Live-Runbook, 60-Minuten-Skript, XNP/BPMN-Grenzen und Fallbacks.
- [docs/de/notarsoftware-datenmodell.md](notarsoftware-datenmodell.md): Herleitung
  des offenen Aktenmodells aus typischen Notarsoftware-Bausteinen.
- [docs/de/architecture/nemoclaw-operating-model.md](architecture/nemoclaw-operating-model.md):
  Arbeitsteilung zwischen Project Manager, `brev01`-Entwicklung und
  `notoclaw01`-Zielbetrieb.
- [docs/de/architecture/nac-onprem-agent-runtime.md](architecture/nac-onprem-agent-runtime.md):
  Zielsystemvertrag für NaC als On-Prem-Agent-Runtime mit NemoClaw/OpenClaw,
  Target-Control, Connector-Stubs und Owner-Gates.
- [docs/de/architecture/notarial-onprem-connector-boundaries.md](architecture/notarial-onprem-connector-boundaries.md):
  notarielle On-Prem-Connector-Grenzen für XNP/SNP, XNotar,
  cyberJack/Kartenarbeitsplatz, Register und Grundbuch ohne Live-Apply.
- [docs/de/architecture/matter-data-classification-redaction.md](architecture/matter-data-classification-redaction.md):
  Mandatsdaten-Klassifikation und Redaktionsgrenze für GitHub, `notoclaw01`,
  Webapp-Status, ATP-Metadaten und spätere private Runtime-Speicher.
- [docs/de/architecture/private-operating-frame-gate.md](architecture/private-operating-frame-gate.md):
  privater Betriebsrahmen und Private-Payload-Gate vor echter
  Mandatsdatenverarbeitung.
- [docs/de/architecture/private-payload-target-design.md](architecture/private-payload-target-design.md):
  logisches Envelope-/Pointer-Zielbild für spätere private Payloads ohne Apply.
- [docs/de/architecture/private-payload-access-policy.md](architecture/private-payload-access-policy.md):
  Rollen-, Zweck- und Zugriffsmatrix für spätere private Payloads ohne
  Live-Zugriff.
- [docs/de/architecture/legal-model-customization-readiness.md](architecture/legal-model-customization-readiness.md):
  Readiness-Vertrag für spätere Legal-Nemotron-Modellanpassung ohne
  Trainingsstart.
- [docs/de/architecture/legal-source-inventory-license-tdm.md](architecture/legal-source-inventory-license-tdm.md):
  Quelleninventar-, Lizenz- und TDM-Gate für spätere Legal-Nemotron- oder
  Rechtsgraph-Arbeit ohne Quellentext-Ingestion.
- [docs/de/architecture/legal-model-evaluation-benchmark.md](architecture/legal-model-evaluation-benchmark.md):
  Benchmark-Blueprint für spätere Legal-Nemotron-Evaluationen ohne
  Benchmark-Datensatz, Modelllauf oder Qualitätsbehauptung.
- [qms/README.md](../../qms/README.md): QMS-/ISO-9001-Schicht mit
  Qualitätspolitik, Zielen, Auditprogramm und Nachweismapping.

### Governance Und Runtime

- [roadmap/GANTT.md](../../roadmap/GANTT.md) zeigt den globalen Fortschritt für Plugins, Workflows und
  Usecases.
- [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md) und [usecases/GANTT.md](../../usecases/GANTT.md) zeigen den
  Fortschritt je Themenbereich.
- [policies/](../../policies) enthält Kultur-, Sprach-, Prozess-, Technik-, Datenschutz-,
  Rollen-, Zugriffs-, SBOM- und Drittbetriebsregeln.
- [.cursor/rules/](../../.cursor/rules) und [.github/copilot-instructions.md](../../.github/copilot-instructions.md) spiegeln die
  verbindlichen Agentenregeln.
- [schemas/](../../schemas), [bpmn/](../../bpmn), [processes/](../../processes), [src/](../../src) und [scripts/](../../scripts) enthalten
  strukturierte Prozessanträge, Prozessmodelle, technische Fixtures, Runtime
  und lokale Werkzeuge.
- [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json)
  beschreibt den implementierten KG-Editor-Vertrag für die usecase-lokalen
  Knowledge Graphs.
- [workflows/contracts/codex-parallel-review.contract.json](../../workflows/contracts/codex-parallel-review.contract.json)
  beschreibt den Vertrag für explizite, parallele Codex-Reviews mit
  read-only Agentprofilen und frischer Validierung.
- [workflows/contracts/nac-onprem-agent-runtime.contract.json](../../workflows/contracts/nac-onprem-agent-runtime.contract.json)
  beschreibt den Vertrag für NaC als On-Prem-Agent-Runtime auf `notoclaw01`
  mit Target-Control-Pfaden, Connector-Stubs und Owner-Gates.
- [workflows/contracts/notarial-onprem-connector-boundaries.contract.json](../../workflows/contracts/notarial-onprem-connector-boundaries.contract.json)
  beschreibt XNP/SNP-, XNotar-, Kartenarbeitsplatz-, Register- und
  Grundbuchpfade als lokale Readiness- und redigierte Evidence-Grenzen.
- [workflows/contracts/matter-data-classification-redaction.contract.json](../../workflows/contracts/matter-data-classification-redaction.contract.json)
  beschreibt Mandatsdaten-Klassifikation, Redaktionsnachweise und
  Speichergrenzen zwischen GitHub, `notoclaw01`, Webapp-Status,
  ATP-Metadaten und privatem Betriebsrahmen.
- [workflows/contracts/private-operating-frame-gate.contract.json](../../workflows/contracts/private-operating-frame-gate.contract.json)
  beschreibt den Gate-Vertrag für spätere private Payloads mit Datenschutz-,
  Rollen-, Speicher-, Verschlüsselungs-, Retention-, Audit- und Owner-Gates.
- [workflows/contracts/private-payload-target-design.contract.json](../../workflows/contracts/private-payload-target-design.contract.json)
  beschreibt das logische Envelope-/Pointer-Zielbild für private Payloads
  ohne DDL-Artefakt, Apply oder private Beispieldaten.
- [workflows/contracts/private-payload-access-policy.contract.json](../../workflows/contracts/private-payload-access-policy.contract.json)
  beschreibt Rollen, Zwecke, Zugriffsmatrix, Step-up, Human Review, Audit und
  globale Ablehnungen für spätere private Payloads ohne Live-Zugriff.
- [workflows/contracts/secure-document-link.contract.json](../../workflows/contracts/secure-document-link.contract.json)
  beschreibt die Mindestgrenze für mobile Upload- und Leselinks auf Object
  Store, Datenbank-Blob oder OneDrive.
- [workflows/contracts/legal-model-customization-readiness.contract.json](../../workflows/contracts/legal-model-customization-readiness.contract.json)
  beschreibt Quellen-, Lizenz-, Benchmark-, Evaluation-, Model-Card-,
  AI-SBOM- und Owner-Apply-Gates für spätere Legal-Nemotron-Anpassungen.
- [workflows/contracts/legal-source-inventory-license-tdm.contract.json](../../workflows/contracts/legal-source-inventory-license-tdm.contract.json)
  beschreibt Quelleninventar-, Lizenz- und TDM-Gates vor jeder
  Quellentext-Ingestion, Benchmark-Generierung, Evaluation oder
  Modellanpassung.
- [workflows/contracts/legal-model-evaluation-benchmark.contract.json](../../workflows/contracts/legal-model-evaluation-benchmark.contract.json)
  beschreibt Quellenhierarchie, Holdout-Regeln, Aufgabenfamilien,
  BYOB/MCQ- und `eval/model_eval`-Routing für spätere
  Legal-Nemotron-Evaluationen ohne Benchmark-Datensatz oder Modelllauf.
- [.github/workflows/](../../.github/workflows) enthält Governance-, Runtime-, SBOM- und
  Cloud-Parity-Workflows.

## Schnellstart

```bash
python scripts/nac.py status
python scripts/nac.py kg case immobilienkaufvertrag
python scripts/nac.py bpmn show immobilienkaufvertrag
python scripts/nac.py bpmn validate
```

## Betriebsmodell

1. Ein Fachanwender beschreibt einen Vorgang per Prompt.
2. Das LLM erstellt einen Prozessantrag als JSON-Datei und eröffnet einen Branch oder Pull Request.
3. Die Python-Engine validiert Schema, Zustandsübergänge und Idempotenz.
4. GitHub Actions führen automatische Checks aus und fordern Freigaben an.
5. Nach dem Merge nach `main` gilt der Vorgang als verbindlich freigegeben und kann exportiert, archiviert oder periodisch aggregiert werden.

## Governance

- Produktive Forks und sensible Prozessänderungen nutzen geschützten `main`,
  Pull Request und Review. Im aktiven Referenzrepo ist Owner-Direct auf `main`
  möglich, wenn der Owner direkte Lieferung ausdrücklich beauftragt; Details
  stehen in [docs/de/regelarchitektur.md](regelarchitektur.md).
- [roadmap/GANTT.md](../../roadmap/GANTT.md) wird bei Roadmap-, Scope-, Status-, Meilenstein- oder Build-Board-Änderungen aktualisiert; Änderungen unter [plugins/](../../plugins), [workflows/](../../workflows) oder [usecases/](../../usecases) aktualisieren das jeweilige Themen-Gantt nur bei fachlicher Scope-, Status- oder Meilensteinwirkung.
- Sensible Schritte wie Beurkundung, Unterschriftsbeglaubigung oder Auszahlungsvoraussetzungen
  erhalten manuelle Reviewer-Gates.
- Tags und Releases repräsentieren Monats- oder Quartalsabschlüsse.
- Erzeugte Artefakte können als Actions-Artefakte archiviert werden.
- Laufende Vorgänge bleiben auf der beim Start gebundenen Prozessversion.

## Hinweise

Dieses Repo ist ein Referenzsystem. Es ersetzt kein vorgeschriebenes Fachsystem, sondern zeigt, wie Git als Orchestrierungs-, Kontroll- und Nachweisschicht für notarielle Vorgänge dienen kann.

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
3. [docs/de/notariat-as-code.md](notariat-as-code.md) für Rollen, Usecase-Logik und Grenzen.
4. [docs/de/governance.md](governance.md) für Freigabe- und Nachweispflichten.

## Notariats-Onboarding

- Notariat: [prompts/de/onboarding/notary-first-setup.md](../../prompts/de/onboarding/notary-first-setup.md)
- VS Code + Copilot Start: [prompts/de/onboarding/vscode-copilot-notariat-setup.md](../../prompts/de/onboarding/vscode-copilot-notariat-setup.md)

Default für den synchronen MVP-Pfad in diesem Repo: `notary`.
Fachliche Beispiele werden nur aus [usecases/](../../usecases) abgeleitet.

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
