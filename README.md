# NoC: Notariat as Code

Dieses Repository wird als mehrsprachige Referenz fuer `Notariat as Code`
gepflegt. Deutsch ist repo-weit die fuehrende Sprache fuer menschlich lesbare
Inhalte. Englisch ist Pflichtsprache fuer lokalisierte Spiegel, aber nur
Uebersetzung oder Orientierung. Fuer deutsches Recht und notarielle Usecases ist
Deutsch fuehrend und rechtlich bindend.

Die verbindliche Sprachregel steht in
[policies/language-policy.yaml](policies/language-policy.yaml) und wird mit
[scripts/validate_language_parity.py](scripts/validate_language_parity.py)
geprueft.

## Sprachen

- Deutsch: [docs/de/](docs/de), [prompts/de/](prompts/de)
- Englisch: [docs/en/](docs/en), [prompts/en/](prompts/en)

`de` und `en` sind verpflichtende Standardsprachen. Aenderungen an lokalisierten
Inhalten muessen beide Sprachpfade pflegen, unabhaengig von der Prompt-Sprache.
Nicht lokalisierte menschlich lesbare Inhalte, insbesondere diese GitHub-
Startseite, werden deutsch gefuehrt.

## Start

- Startpfad: [docs/de/START_HERE.md](docs/de/START_HERE.md),
  [docs/en/START_HERE.md](docs/en/START_HERE.md)
- Aktives Entwicklungsboard: [roadmap/BUILD_NOW.md](roadmap/BUILD_NOW.md)
- README: [docs/de/README.md](docs/de/README.md),
  [docs/en/README.md](docs/en/README.md)
- Mindestvoraussetzungen: [docs/de/minimum-requirements.md](docs/de/minimum-requirements.md),
  [docs/en/minimum-requirements.md](docs/en/minimum-requirements.md)
- AVV/DPA-Bereich: [docs/de/datenschutz-avv-dpa.md](docs/de/datenschutz-avv-dpa.md),
  [docs/en/datenschutz-avv-dpa.md](docs/en/datenschutz-avv-dpa.md)
- SBOM fuer AI: [docs/de/sbom-for-ai.md](docs/de/sbom-for-ai.md),
  [docs/en/sbom-for-ai.md](docs/en/sbom-for-ai.md)
- Plugin-Plaene: [docs/de/plugin-plans/README.md](docs/de/plugin-plans/README.md),
  [docs/en/plugin-plans/README.md](docs/en/plugin-plans/README.md)
- Eventstream-Runbooks: [docs/de/eventstream/README.md](docs/de/eventstream/README.md),
  [docs/en/eventstream/README.md](docs/en/eventstream/README.md)
- Issue-Betrieb: [docs/de/issues/README.md](docs/de/issues/README.md),
  [docs/en/issues/README.md](docs/en/issues/README.md)
- Betriebsmodell: [docs/de/operations/README.md](docs/de/operations/README.md),
  [docs/en/operations/README.md](docs/en/operations/README.md)
- Service-Modell: [docs/de/service-model/README.md](docs/de/service-model/README.md),
  [docs/en/service-model/README.md](docs/en/service-model/README.md)
- Globale Roadmap: [roadmap/GANTT.md](roadmap/GANTT.md)
- Plugin-Roadmap: [plugins/GANTT.md](plugins/GANTT.md)
- Workflow-Roadmap: [workflows/GANTT.md](workflows/GANTT.md)
- Usecase-Roadmap: [usecases/GANTT.md](usecases/GANTT.md)
- Usecase-lokale Knowledge Graphs: [usecases/README.md](usecases/README.md);
  jeder Vorgang fuehrt eigene Dateien `knowledge-graph.graph.json` und
  `knowledge-graph.md`, zum Beispiel
  [usecases/immobilienkaufvertrag/knowledge-graph.graph.json](usecases/immobilienkaufvertrag/knowledge-graph.graph.json)

## Produktstruktur

Dieses Repository trennt drei Produktbereiche:

- [plugins/](plugins): installierbare Plugin-Artefakte fuer GPT-Store-Pruefung,
  Workspace-Installation oder lokale Integration.
- [workflows/](workflows): wiederverwendbare Notariats-Workflows, getrennt nach
  installierbaren Skills und deterministischer Python-Ausfuehrung.
- [usecases/](usecases): konkrete notarielle Vorgangsarten wie Online-GmbH-
  Gruendung, AO52-Gemeinnuetzigkeit, Immobilienkaufvertrag oder Testament. Jeder
  Usecase besitzt seine eigene statische KG/DB fuer offene Fragen, Dokumente,
  Entscheidungen, Gates und Nachweisreferenzen.

Jeder Push muss [roadmap/GANTT.md](roadmap/GANTT.md) aktualisieren. Aenderungen
unter [plugins/](plugins), [workflows/](workflows) oder [usecases/](usecases)
muessen zusaetzlich das jeweilige Themen-Gantt aktualisieren.

OpenAI-Veroeffentlichungskanaele werden vor Release separat geprueft. Oeffentlich
installierbare GPT-Store-Pakete und workspace-interne Apps sind nicht derselbe
Zielkanal, insbesondere wenn Apps oder Actions beteiligt sind.

## Aktueller Entwicklungsmodus

NoC wird als ausfuehrbare Software entwickelt, nicht nur als Dokumentation. Die
aktuell implementierte Runtime-Oberflaeche ist die notarielle KG-CLI:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
```

Das aktive Build-Board wird in [roadmap/BUILD_NOW.md](roadmap/BUILD_NOW.md)
gepflegt.

## Aktuelle Workflow-Prioritaeten

Der Online-HRA-Pfad ist eine notarielle Gate-Kette. XNP wird erst nach lokal
stabilem Kartenpfad getestet.

| Prioritaet | Workflow | Blockiert | Sichtbares Ergebnis |
| --- | --- | --- | --- |
| P0 | `noc-cyberjack-rfid` Karten-/SAK-Gate | XNP-Login-Test | Karte, Reader, PC/SC, SAK lite/XNP-Kartenpfad und secureFramework werden lokal readiness-geprueft. |
| P0 | `noc-bnotk-xnp` XNP-Gate | HRA-/XNotar-Workflow | XNP, lokaler Login, offizieller Kontext, XNotar-Modul und Austauschordner werden readiness-geprueft. |
| P0 | `noc-handelsregister` Online-HRA-Schicht | produktionsnahes HRA-Paket | HRA-/HRB-Pfad, Pflichtdaten, Notarroute, Freigaben und Evidence-Metadaten sind vorbereitet. |
| P1 | Installierbarkeit und Validierung | Pilotbetrieb | Codex-Marketplace-Reihenfolge, Plugin-Manifeste und Validator sind stabil. |
| P2 | Folgeadapter beA, Grundbuch, ELSTER | Querschnittsausbau | zurueckgestellt, bis Karten-/SAK-, XNP- und HRA-Gates stabil sind. |

## Schnellpruefung

```bash
python scripts/quality_gate.py --profile strict
```

Das strikte Quality Gate prueft Prozessdateien, Tests, Datenschutzregeln,
Governance-Sync, Sprachregeln, Cloud-Runbook-Paritaet, Plugin-Manifeste,
AI-SBOM-Stand, Gantt-Pflege und die usecase-lokalen statischen Knowledge
Graphs.
