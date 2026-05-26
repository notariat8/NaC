# GitHub-First Agentic Operating Model

Status: Design-Spezifikation
Datum: 2026-05-26

## Ausgangspunkt

NaC nutzt bereits Git, Pull Requests, Reviews, Actions, Issue-Taxonomie,
Organization Projects und ein revisionssicheres Event-Journal. Die aktuelle
Lücke liegt nicht in einem fehlenden Werkzeug, sondern in der operativen
Verbindlichkeit: Agentische Arbeit soll für den Owner auf GitHub sichtbar und
steuerbar sein, ohne dass der Fortschritt aus Repo-Diffs, Mermaid- oder
Gantt-Dateien rekonstruiert werden muss.

GitHub Projects ist dafür geeignet, weil Issues und Pull Requests direkt als
Projekt-Items geführt werden können, Projects eigene Felder und Views
unterstützen und `gh project` über den Scope `project` automatisierbar ist.
NaC vermeidet dabei bewusst eine Abhängigkeit von GitHub Projects Classic oder
Preview-only Issue Fields. Verwendet werden stabile Project-Felder und
verlinkte Issues/Pull Requests.

## Entscheidung

GitHub wird die primäre operative Steuerungsfläche für agentische NaC-Arbeit:

- Issues beschreiben Auftrag, Kontext, Akzeptanzkriterien und Risiken.
- Pull Requests beschreiben die konkrete Änderung, Validierung und Reviewspur.
- GitHub Projects zeigt Status, Track, Priorität, Risiko, Delivery Mode und
  Blocker.
- GitHub Actions und Required Checks bilden das technische Abschlussgate.
- Repo-Policies, Dokumente, Commits, Tags und das Event-Journal bleiben die
  auditierbare Wahrheit.

Gantt- und Mermaid-Dateien bleiben erlaubt, werden aber nicht mehr als
primäre Fortschrittsoberfläche behandelt. Sie sind Snapshots oder
Release-/Roadmap-Artefakte. Der laufende Arbeitsstand soll auf GitHub sichtbar
sein.

## Nichtziele

- Kein Ersatz der Policy-Dateien durch Project-Felder.
- Keine Mandatsdaten, Secrets, PINs, Tokens oder privaten Dokumentinhalte in
  Issues, PRs, Project-Feldern oder Kommentaren.
- Kein Umgehen von Review-, Branchschutz-, Secret-Scan- oder Quality-Gates.
- Keine Pflicht, für reine Tippfehler oder lokale Mini-Klarstellungen künstlich
  Issues zu erzeugen, sofern keine Governance-, Scope-, Status- oder
  Roadmap-Wirkung entsteht.

## Operating Surface

Das Zielbild ist ein Organization Project, zum Beispiel `NaC Control Plane`,
unter `notariat8`. Dieses Project ist die erste Ansicht für den Owner.

Pflichtfelder:

| Feld | Typ | Zweck |
| --- | --- | --- |
| `Status` | single select | `Inbox`, `Ready`, `In Progress`, `Review`, `Blocked`, `Done` |
| `Track` | single select | `Governance`, `Runtime`, `KG`, `BPMN`, `Operator`, `Plugins`, `Security`, `Docs`, `CI`, `Release` |
| `Work Type` | single select | `Feature`, `Bug`, `Governance`, `Spike`, `Ops`, `Security`, `Docs` |
| `Risk Gate` | single select | `None`, `Privacy`, `Secrets`, `Workflow`, `Policy`, `External Service`, `Human Approval` |
| `Delivery Mode` | single select | `Owner Direct`, `Protected PR`, `Sync PR` |
| `Priority` | single select | `P0`, `P1`, `P2`, `P3` |
| `Size` | single select | `S`, `M`, `L` |
| `Iteration` | iteration | Arbeitsfenster für laufende Planung |
| `Due Date` | date | nur wenn echte Frist oder Meilensteinbindung besteht |

Empfohlene Views:

- `Owner Board`: alle aktiven Items, gruppiert nach `Status`.
- `Now`: `Status` in `Ready`, `In Progress`, `Review`, ohne `Done`.
- `Blocked`: alle blockierten Items mit sichtbarem Blocker-Kommentar.
- `Governance And Security`: `Track` in `Governance`, `Security`, `CI`.
- `Release Readiness`: Items mit Release-, Gantt- oder Versionierungswirkung.
- `My Agent Work`: Items, die dem aktuellen Agenten oder technischen Login
  zugeordnet sind.

## Issue-Regeln

Nichttriviale Arbeit beginnt mit genau einem führenden Issue. Ein Issue ist
nicht nur ein Ticket, sondern der kleinste nachvollziehbare Auftrag.

Pflichtinhalt eines führenden Issues:

- Ziel und fachlicher Nutzen.
- Scope und explizite Nichtziele.
- Akzeptanzkriterien.
- Risiko-/Datenschutz-/Secret-Einschätzung.
- Erwarteter Delivery Mode.
- Validierungsplan.
- Project-Zuordnung und Pflichtfelder.

Issue-Typen:

| Typ | Nutzung |
| --- | --- |
| `Feature` | neue fachliche oder technische Funktion |
| `Bug` | fehlerhaftes Verhalten oder gebrochenes Gate |
| `Governance` | Policy-, Regel-, Rollen- oder Betriebsmodell-Änderung |
| `Spike` | Recherche oder Entscheidungsarbeit ohne sofortige Produkt-Änderung |
| `Ops` | Betrieb, Auth, Projects, Labels, Branchschutz, Releases |
| `Security` | Secret-, Datenschutz-, Berechtigungs- oder Supply-Chain-Themen |
| `Docs` | Doku-Änderung mit fachlicher Steuerungswirkung |

Abgeleitete Issues in anderen Repos müssen das führende Issue verlinken.
Das entspricht der vorhandenen Issue-Taxonomie und verhindert verteilte
Schatten-Backlogs.

## Branch- und PR-Regeln

Standard für agentische Änderungen:

1. Führendes Issue klären oder erzeugen.
2. Project-Felder setzen.
3. Branch erstellen:
   - `agent/<issue-number>-<short-slug>` für normale Agentenarbeit.
   - `sync/<issue-number>-<short-slug>` für Upstream- oder Fork-Sync.
   - `hotfix/<issue-number>-<short-slug>` nur bei P0/P1-Fehlern.
4. Draft Pull Request öffnen, sobald die Änderungsrichtung sichtbar ist.
5. PR mit Issue verlinken und Project-Item ergänzen.
6. Lokale Validierung im PR dokumentieren.
7. Required Checks abwarten.
8. Review/Merge je Delivery Mode.
9. Project-Status auf `Done` erst nach Merge oder Owner-Direct-Zielbranch,
   sauberem Workspace und erfolgreichen `remote_ci_checks` setzen.

Owner-Direct auf `main` bleibt für das aktive Referenzrepo erlaubt, wenn der
Owner direkte Lieferung ausdrücklich beauftragt. Auch dann wird bei
nichttrivialer Arbeit ein Issue geführt und das Project aktualisiert. Die
Abschlussregel bleibt unverändert hart: lokal validiert, committed, gepusht,
`HEAD` entspricht `origin/main`, Workspace sauber, Required Checks grün.

## Autonomie-Voraussetzungen

Damit ein Agent möglichst autonom arbeiten kann, braucht er:

- GitHub CLI/App-Zugriff mit `repo`, `workflow`, `project` und, für
  Organisationseinordnung, `read:org`.
- Erlaubnis, im vereinbarten Scope Issues, Labels, Branches, Draft PRs,
  PR-Kommentare und Project-Felder zu erstellen oder zu aktualisieren.
- Einen benannten Project-Owner und eine Project-Nummer oder URL.
- Klare Delivery-Mode-Regel je Repo: `Protected PR`, `Owner Direct` oder
  `Sync PR`.
- Verbot, Secrets oder echte Mandatsdaten in GitHub-Oberflächen zu schreiben.
- Eskalationsregel für Blocker: Project-Status `Blocked`, kurzer Kommentar mit
  fehlender Entscheidung, kein stilles Abweichen von Policy.

Wenn eine Regel die Arbeit blockiert, gilt die Governance-Regel des Owners:
Zuerst prüfen, ob die Regel richtig aber unvollständig umgesetzt ist oder ob
die Regel selbst falsch ist und angepasst werden muss. Stilles Abweichen ist
kein valider Delivery Mode.

## Policy-Änderungen

Die Implementierung soll `policies/process-policy.yaml` um einen Abschnitt
`github_first_operating_model` erweitern. Dieser Abschnitt definiert:

- GitHub Project als operative Fortschrittsoberfläche.
- Pflicht-Issue für nichttriviale Arbeit.
- Pflicht-PR für produktive Forks und sensible Prozessänderungen.
- Owner-Direct-Ausnahme im aktiven Referenzrepo mit Issue-/Project-Spur.
- Required Project-Felder und minimale Views.
- Abschluss nur nach `remote_ci_checks`.
- Verbot von Secrets und Mandatsdaten in Issues, PRs und Project-Feldern.

Die Spiegel müssen synchronisiert werden:

- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/00-core-governance.mdc`
- `.cursor/rules/02-agent-common-workflows.mdc`
- `docs/de/regelarchitektur.md`
- `docs/en/regelarchitektur.md`
- `docs/de/issues/operations.md`
- `docs/en/issues/operations.md`
- `docs/de/operations/README.md`
- `docs/en/operations/README.md`

## Validierung

Neue oder erweiterte Tests sollen sicherstellen:

- Die Process Policy enthält `github_first_operating_model`.
- Required Project-Felder und Delivery Modes sind maschinenlesbar vorhanden.
- Regelarchitektur und Agentenflächen spiegeln die GitHub-first-Regel.
- Datenschutz-/Secret-Regeln gelten auch für GitHub Issues, PRs und Projects.
- Language Parity für deutsche und englische Dokumente bleibt erhalten.

Bestehende Pflichtvalidierung bleibt:

- `python -m unittest`
- `scripts/validate_governance_sync.py`
- `scripts/validate_language_parity.py`
- `scripts/validate_doc_links.py`
- `scripts/privacy_lint.py`
- `scripts/quality_gate.py --profile strict`
- GitHub Required Checks auf dem Zielstand

## Umsetzungsschritte

1. Policy-Test für `github_first_operating_model` rot schreiben.
2. Process Policy und Spiegel aktualisieren.
3. Issue-Operations-Dokumente um Project-Felder, Views und Autonomie-Regeln
   erweitern.
4. Optional Issue-Templates und PR-Template nachziehen, falls noch nicht
   ausreichend strukturiert.
5. GitHub Project über UI oder `gh project` anlegen und Felder erstellen.
6. Erstes führendes Issue für die nächste NaC-Änderung anlegen und dem
   Project zuordnen.
7. Validierung lokal und remote abschließen.

## Referenzen

- GitHub CLI `gh project`: https://cli.github.com/manual/gh_project
- GitHub Project-Felder: https://docs.github.com/issues/planning-and-tracking-with-projects/understanding-fields
- Items zu Projects hinzufügen: https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-items-in-your-project/adding-items-to-your-project
