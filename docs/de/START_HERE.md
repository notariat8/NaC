# START_HERE: Operativer Einstieg in NoC

Status: verbindlicher Startpfad
Letzte inhaltliche Anpassung: 2026-05-15

## Warum dieses Dokument neben dem README existiert

[README.md](../../README.md) und [docs/de/README.md](README.md) sind Projektuebersicht und Index. Dieses
Dokument ist die operative Startsequenz fuer Arbeit im laufenden NoC-Projekt.

[START_HERE.md](START_HERE.md) bleibt deshalb notwendig, hat aber eine andere Aufgabe als das
README:

| Dokument | Aufgabe |
| --- | --- |
| [README.md](../../README.md) | Repo-Uebersicht, Produktstruktur, Quick Checks, aktuelle Build-Kommandos. |
| [docs/de/README.md](README.md) | Deutsche fachliche Orientierung und Dokumentenindex. |
| [docs/de/START_HERE.md](START_HERE.md) | Verbindlicher Arbeitsstart fuer neue Sitzungen, neue Mitwirkende und Agenten. |

Dieses Repo ist kein externer Vorschlag mehr. Es ist der aktive Projektstand fuer
`Notariat as Code` mit `NoC` als konkreter Enterprise Control Plane.

## Wann START_HERE zu verwenden ist

Dieses Dokument ist zu verwenden:

- beim Start einer neuen Arbeitssitzung,
- vor produktiven Aenderungen an Code, Doku, Policies, Plugins, Workflows oder
  Usecases,
- nach einem Branch-Wechsel oder Pull,
- wenn ein neuer Mitwirkender oder Agent in das Repo einsteigt,
- vor einem Push, wenn unklar ist, welche Gates und Gantts betroffen sind.

## Verbindliche Startsequenz

1. Repo-Regeln lesen:
   - [AGENTS.md](../../AGENTS.md), sofern im Workspace vorhanden.
   - [.github/copilot-instructions.md](../../.github/copilot-instructions.md)
   - [.cursor/rules/](../../.cursor/rules)
2. Projektstatus lesen:
   - [roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md)
   - [roadmap/GANTT.md](../../roadmap/GANTT.md)
   - [docs/de/minimum-requirements.md](minimum-requirements.md)
   - bei Themenarbeit zusaetzlich [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md) oder
     [usecases/GANTT.md](../../usecases/GANTT.md)
3. Aktuellen Git-Zustand pruefen:

   ```bash
   git status --short --branch
   ```

4. Aktive Runtime pruefen:

   ```bash
   python scripts/notary_kg.py --repo-root . status
   ```

5. Strikten lokalen Gate ausfuehren, bevor ein Stand als push-ready gilt:

   ```bash
   python scripts/startup_check.py --profile base --ide auto --run-tests
   python scripts/quality_gate.py --profile strict
   ```

Bei Plugin- oder Notariatsarbeitsplatz-Arbeit zusaetzlich das passende Profil
ausfuehren:

```bash
python scripts/startup_check.py --profile plugin-dev --ide auto
python scripts/startup_check.py --profile notary-workstation --ide auto
```

## Arbeitsmodus

NoC wird als Software entwickelt. Konzeptarbeit ist nur dann vollstaendig, wenn
sie mindestens eine passende Umsetzungsflaeche mitpflegt:

- Runtime-Code unter [src/](../../src)
- Skripte unter [scripts/](../../scripts)
- Tests unter [tests/](../../tests)
- Plugin-Artefakte unter [plugins/](../../plugins)
- Workflow-Vertraege unter [workflows/contracts/](../../workflows/contracts)
- KG-Artefakte unter [knowledge-graph/](../../knowledge-graph)
- Roadmap-/Gantt-Status unter [roadmap/](../../roadmap), [plugins/](../../plugins), [workflows/](../../workflows) oder
  [usecases/](../../usecases)

## Produktstruktur

| Bereich | Zweck |
| --- | --- |
| [plugins/](../../plugins) | Installierbare Plugin-Artefakte fuer GPT Store, Workspace oder lokale Integration. |
| [workflows/](../../workflows) | Skills, Workflow-Vertraege und deterministische Python-Workflows. |
| [usecases/](../../usecases) | Konkrete notarielle Vorgangsarten und Pilotpakete. |
| [knowledge-graph/](../../knowledge-graph) | Statische KG/DB fuer offene Informationen, Dokumente, Entscheidungen, Gates und Nachweise. |
| [docs/de/eventstream/](eventstream) | Event-Journal, EventLock und Cloud-Runbooks. |
| [docs/de/issues/](issues) | Issue-Taxonomie, Issue-Betrieb und Public-Backlog. |
| [docs/de/operations/](operations) | Fork/Release, Upstream-Sync, Version-Binding, Arbeitsmodell und Repo-Konsolidierung. |
| [docs/de/service-model/](service-model) | Core/Vertical-Struktur, Provider-Leistungen, Tenant-Ownership und Exit. |
| [src/](../../src) | Ausfuehrbare Python-Runtime. |
| [scripts/](../../scripts) | Lokale und CI-nahe Entwicklerwerkzeuge. |
| [policies/](../../policies) | Verbindliche Governance-, Rollen-, Technik-, Datenschutz- und SBOM-Regeln. |
| [sbom/](../../sbom) | Maschinenlesbare SBOM-/AI-SBOM-Artefakte fuer Runtime, Infrastruktur und lokale Abhaengigkeiten. |

## Aktuelle Entwicklerkommandos

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/validate_knowledge_graph.py
python scripts/startup_check.py --profile base --ide auto --run-tests
python scripts/quality_gate.py --profile strict
```

## Push-Regel

Jeder Push muss [roadmap/GANTT.md](../../roadmap/GANTT.md) aktualisieren. Aenderungen unter
[plugins/](../../plugins), [workflows/](../../workflows) oder [usecases/](../../usecases) muessen zusaetzlich das jeweilige
Themen-Gantt aktualisieren:

- [plugins/GANTT.md](../../plugins/GANTT.md)
- [workflows/GANTT.md](../../workflows/GANTT.md)
- [usecases/GANTT.md](../../usecases/GANTT.md)

## Lokalisierungsregel

Deutsch und Englisch sind Standardsprachen. Aenderungen an lokalisierten
Inhalten muessen immer beide Sprachpfade pflegen:

- [docs/de/](.)
- [docs/en/](../en)
- [prompts/de/](../../prompts/de)
- [prompts/en/](../../prompts/en)

Die Paritaet wird mit [scripts/validate_language_parity.py](../../scripts/validate_language_parity.py) geprueft.

## Abschlussregel

Ein Update gilt erst als abgeschlossen, wenn es validiert, committed, zu GitHub
gepusht und in den Zielbranch gemerged wurde. Lokale Aenderungen und unge-mergte
PR-Branches sind Zwischenstand.
