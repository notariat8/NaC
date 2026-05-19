# START_HERE: Operativer Einstieg in NaC

Status: verbindlicher Startpfad
Letzte inhaltliche Anpassung: 2026-05-19

## Warum dieses Dokument neben dem README existiert

[README.md](../../README.md) und [docs/de/README.md](README.md) sind Projektübersicht und Index. Dieses
Dokument ist die operative Startsequenz für Arbeit im laufenden NaC-Projekt.

[START_HERE.md](START_HERE.md) bleibt deshalb notwendig, hat aber eine andere Aufgabe als das
README:

| Dokument | Aufgabe |
| --- | --- |
| [README.md](../../README.md) | Repo-Übersicht, Produktstruktur, Quick Checks, aktuelle Build-Kommandos. |
| [docs/de/README.md](README.md) | Deutsche fachliche Orientierung und Dokumentenindex. |
| [docs/de/START_HERE.md](START_HERE.md) | Verbindlicher Arbeitsstart für neue Sitzungen, neue Mitwirkende und Agenten. |

Dieses Repo ist kein externer Vorschlag mehr. Es ist der aktive Projektstand für
`Notariat as Code` mit `NaC` als konkreter Enterprise Control Plane.

## Wann START_HERE zu verwenden ist

Dieses Dokument ist zu verwenden:

- beim Start einer neuen Arbeitssitzung,
- vor produktiven Änderungen an Code, Doku, Policies, Plugins, Workflows oder
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
   - bei Themenarbeit zusätzlich [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md) oder
     [usecases/GANTT.md](../../usecases/GANTT.md)
3. Aktuellen Git-Zustand prüfen:

   ```bash
   git status --short --branch
   ```

4. Aktive Runtime prüfen:

   ```bash
   python scripts/nac.py status
   ```

5. Strikten lokalen Gate ausführen, bevor ein Stand als push-ready gilt:

   ```bash
   python scripts/startup_check.py --profile base --ide auto --run-tests
   python scripts/nac.py doctor --profile strict
   ```

Bei Plugin- oder Notariatsarbeitsplatz-Arbeit zusätzlich das passende Profil
ausführen:

```bash
python scripts/nac.py plugins validate
python scripts/nac.py plugins install --mode link
python scripts/startup_check.py --profile plugin-dev --ide auto
python scripts/startup_check.py --profile notary-workstation --ide auto
```

Nach `nac plugins install --mode link` Codex neu öffnen. Die laufende Session liest
Plugins beim Start ein und sieht repo-lokale Plugins erst nach der lokalen
Spiegelung und einem Neustart.

## Arbeitsmodus

NaC wird als Software entwickelt. Konzeptarbeit ist nur dann vollständig, wenn
sie mindestens eine passende Umsetzungsfläche mitpflegt:

- Runtime-Code unter [src/](../../src)
- Skripte unter [scripts/](../../scripts)
- Tests unter [tests/](../../tests)
- Plugin-Artefakte unter [plugins/](../../plugins)
- Workflow-Verträge unter [workflows/contracts/](../../workflows/contracts)
- KG-Artefakte direkt im jeweiligen Usecase-Ordner unter [usecases/](../../usecases)
- Roadmap-/Gantt-Status unter [roadmap/](../../roadmap), [plugins/](../../plugins), [workflows/](../../workflows) oder
  [usecases/](../../usecases)

## Produktstruktur

| Bereich | Zweck |
| --- | --- |
| [plugins/](../../plugins) | Installierbare Plugin-Artefakte für GPT Store, Workspace oder lokale Integration. |
| [workflows/](../../workflows) | Skills, Workflow-Verträge und deterministische Python-Workflows. |
| [usecases/](../../usecases) | Konkrete notarielle Vorgangsarten und Pilotpakete mit jeweils eigener statischer KG/DB als `knowledge-graph.graph.json` und `knowledge-graph.md`. |
| [docs/de/eventstream/](eventstream) | Event-Journal, EventLock und Cloud-Runbooks. |
| [docs/de/issues/](issues) | Issue-Taxonomie, Issue-Betrieb und Public-Backlog. |
| [docs/de/operations/](operations) | Fork/Release, Upstream-Sync, Version-Binding, Arbeitsmodell und Repo-Konsolidierung. |
| [docs/de/service-model/](service-model) | Core/Vertical-Struktur, Provider-Leistungen, Tenant-Ownership und Exit. |
| [src/](../../src) | Ausführbare Python-Runtime. |
| [scripts/](../../scripts) | Lokale und CI-nahe Entwicklerwerkzeuge. |
| [policies/](../../policies) | Verbindliche Governance-, Rollen-, Technik-, Datenschutz- und SBOM-Regeln. |
| [sbom/](../../sbom) | Maschinenlesbare SBOM-/AI-SBOM-Artefakte für Runtime, Infrastruktur und lokale Abhängigkeiten. |

## Aktuelle Entwicklerkommandos

```bash
python scripts/nac.py status
python scripts/nac.py kg case bautraegervertrag
python scripts/nac.py bpmn validate
python scripts/nac.py config validate
python scripts/validate_knowledge_graph.py
python scripts/nac.py plugins validate
python scripts/startup_check.py --profile base --ide auto --run-tests
python scripts/nac.py doctor --profile strict
```

## Push-Regel

Jeder Push muss [roadmap/GANTT.md](../../roadmap/GANTT.md) aktualisieren. Änderungen unter
[plugins/](../../plugins), [workflows/](../../workflows) oder [usecases/](../../usecases) müssen zusätzlich das jeweilige
Themen-Gantt aktualisieren:

- [plugins/GANTT.md](../../plugins/GANTT.md)
- [workflows/GANTT.md](../../workflows/GANTT.md)
- [usecases/GANTT.md](../../usecases/GANTT.md)

## Lokalisierungsregel

Deutsch und Englisch sind Standardsprachen. Änderungen an lokalisierten
Inhalten müssen immer beide Sprachpfade pflegen:

- [docs/de/](.)
- [docs/en/](../en)
- [prompts/de/](../../prompts/de)
- [prompts/en/](../../prompts/en)

Die Parität wird mit [scripts/validate_language_parity.py](../../scripts/validate_language_parity.py) geprüft.

## Abschlussregel

Ein Update gilt erst als abgeschlossen, wenn es validiert, committed, zu GitHub
gepusht und in den Zielbranch gemerged wurde. Lokale Änderungen und unge-mergte
PR-Branches sind Zwischenstand.
