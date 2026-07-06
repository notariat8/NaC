# Regelarchitektur

Status: verbindliche Erklärung der NaC-Regelgruppen

Diese Seite erklärt, welche Regeln hart blockieren, welche Regeln
Arbeitsdisziplin sind und welche Regeln nur Orientierung geben. Führende
maschinenlesbare Quelle ist [policies/process-policy.yaml](../../policies/process-policy.yaml).
Agentenflächen wie [AGENTS.md](../../AGENTS.md) und die Codex-Agentenprofile
unter [.codex/agents/](../../.codex/agents) sind Spiegel dieser Policy.

## Grundsatz

NaC-Regeln sollen drei Dinge leisten:

1. Mandatsdaten, Secrets und fachliche Verantwortung schützen.
2. Änderungen nachvollziehbar, prüfbar und wiederholbar machen.
3. Arbeit nicht durch künstliche Pflichtänderungen verlangsamen.

Eine Regel ist nur dann hart, wenn sie ein echtes Risiko verhindert und
automatisch oder eindeutig prüfbar ist. Alles andere wird als Arbeitsregel oder
Doku-Regel geführt.

## Regelgruppen

| Gruppe | Warum | Härte | Führende Prüfung |
| --- | --- | --- | --- |
| Abschluss und Fertigmeldung | Verhindert, dass lokale Zwischenstände als fertig gelten. | hart | `nac doctor --profile strict`, `git status`, Abgleich `HEAD` gegen `origin/main`, `remote_ci_checks` |
| Git-Auslieferung | Trennt produktive PR-Freigabe von Owner-Direct-Arbeit im aktiven Referenzrepo. | modusabhängig | Branchschutz/PR im Produktivmodus, Push+Clean-Check im Referenzmodus |
| GitHub-first Arbeitssteuerung | Bindet nichttriviale agentische Arbeit an ein führendes Issue und ein sichtbares Project-Board. | Arbeitsregel plus Abschluss-Gate | Issue-Trail, `NaC Control Plane`, Delivery Mode, `remote_ci_checks` |
| Spec-Traceability | Verbindet Issue, Spec, Plan, AC-IDs und Validierungsbefehle, damit Spec-driven Arbeit prüfbar bleibt. | Arbeitsregel plus Validator-Gate | [workflows/contracts/spec-traceability.contract.json](../../workflows/contracts/spec-traceability.contract.json), `scripts/validate_spec_traceability.py` |
| Agentische Änderungsdisziplin | Verhindert Doom-Loops durch unklare Anforderungen, ungeprüfte Agentenänderungen und Fixes ohne Diagnose. | Arbeitsregel plus Validator-Gate | `agent_workflows` in [policies/process-policy.yaml](../../policies/process-policy.yaml), Plan-/Code-Review, Validierungsnachweis |
| Operator-/Admin-Handoff | Verhindert unvorbereitete Rückfragen nach Tenant-Werten, Secrets oder Portalaktionen. | Arbeitsregel plus Validator-Gate je Integrationsvertrag | [workflows/contracts/teams-sharepoint-graph-data-plane.contract.json](../../workflows/contracts/teams-sharepoint-graph-data-plane.contract.json), Runbook mit Hyperlinks und Copy-Paste-Kommandos |
| Roadmap und Gantt | Hält Lieferplan und Status sichtbar, ohne kleine Fixes zu blockieren. | Hinweis plus Render-Gate | `scripts/validate_gantt_progress.py` |
| Sprache und Lokalisierung | Deutsch führt fachlich, Englisch ist Übersetzung/Orientierung. | hart | `scripts/validate_language_parity.py` |
| CLI und Bürooberfläche | Neue NaC-Funktionalität braucht eine prüfbare Bedienkante. | hart für neue Funktionalität | Tests, CLI-Aufruf, `nac doctor --profile strict` |
| Datenschutz und Datenrepo | Verhindert echte Mandatsdaten, Secrets, PINs und Kartenrohdaten im Produktrepo. | hart | `scripts/privacy_lint.py`, Datenschutz-Policy |
| Plugins, Skills und Agentenmethodik | Hält lokale Plugins installierbar und Agentenarbeit planbar. | gemischt | `scripts/validate_plugins.py`, lokaler Plugin-Spiegel, Superpowers-kompatible Arbeitsweise |
| Validierung und Doctor | Macht Abschlussaussagen beweisbar. | hart | `scripts/quality_gate.py`, `nac doctor --profile strict` |

## Git-Auslieferungsmodi

NaC unterscheidet zwei Modi:

| Modus | Nutzung | Fertig bedeutet |
| --- | --- | --- |
| Geschützter PR-Modus | Produktive Forks, sensible Prozessänderungen, externe Mitwirkung. | Branch ist per PR reviewed, validiert und in `main` gemerged. |
| Owner-Direct-Modus | Aktives Referenzrepo, wenn der Owner direkte Lieferung ausdrücklich beauftragt. | `main` ist validiert, zu GitHub gepusht, `HEAD` entspricht `origin/main`, der Arbeitsbaum ist sauber, und `Privacy and Secrets Guard / secret-scan`, `Privacy and Secrets Guard / privacy-lint` sowie `NaC Quality Gate / quality-gate` sind erfolgreich. |

Für produktive Notariats- oder Organisations-Forks ist der geschützte PR-Modus
das Zielbild. Der Owner-Direct-Modus ist kein Freibrief für produktive
Mandatsdaten oder sensible Fachänderungen.

`remote_ci_checks` sind Teil der Abschlussregel, weil lokale Validierung nicht
beweist, dass GitHub nach dem Push dieselben Schutzgates ausführt. Mindestens
erforderlich sind `Privacy and Secrets Guard / secret-scan`,
`Privacy and Secrets Guard / privacy-lint` und
`NaC Quality Gate / quality-gate`.

## GitHub-first Arbeitssteuerung

Nichttriviale agentische Arbeit läuft GitHub-first. Ein führendes Issue hält
Auftrag, Scope, Akzeptanzkriterien, Risk Gate, Delivery Mode und Validierung
fest. Das Organization Project `NaC Control Plane` zeigt Status, Blocker und
Zuständigkeit über die jeweils sichtbaren Repos hinweg.

Fertig ist ein Update erst, wenn der im Issue dokumentierte Delivery Mode
erfüllt ist und die verpflichtenden `remote_ci_checks` erfolgreich sind. Das
Project ersetzt keine Repo-Rechte: Nutzer sehen nur Issues aus Repos, auf die
sie bereits Zugriff haben.

Jede Abschlussmeldung nennt danach trotzdem einen Abschnitt `Nächster Schritt`.
Dort steht konkret, welche technische oder operative Fortsetzung ansteht und ob
Owner-Input benötigt wird. Wenn kein Owner-Input nötig ist, wird das
ausdrücklich gesagt. Ein nächster Schritt, der ohne Owner-Input mit den
verfügbaren Werkzeugen ausführbar ist, ist kein gültiger Abschluss, sondern
weiter auszuführende Agentenarbeit. Nur konkrete externe Blocker, fehlende
Daten, Owner-Gates oder nicht verfügbare Werkzeuge dürfen als wartender
nächster Schritt stehen bleiben.

## Spec-Traceability

Neue oder geänderte nichttriviale Specs führen eine prüfbare Spur von Issue zu
Spec, Plan, AC-IDs und Validierungsbefehlen. Der maschinenlesbare Vertrag steht
in [workflows/contracts/spec-traceability.contract.json](../../workflows/contracts/spec-traceability.contract.json);
geprüft wird er mit `scripts/validate_spec_traceability.py`.

Historische Specs ohne Manifest bleiben gültig. Sobald ein Spec fachlich
weiterentwickelt wird, soll er einen `nac-spec-traceability`-Block erhalten.
Die AC-IDs stehen sowohl im Manifest als auch im Akzeptanzteil des Specs, damit
Reviews und Tests dieselben Kriterien referenzieren.

## Agentische Änderungsdisziplin

Nichttriviale Arbeit folgt zwei getrennten Schleifen:

1. `plan -> review -> fix`: Anforderungen, Architekturannahmen, Scope,
   Risiken und Akzeptanzkriterien werden erst in Text geklärt. Ein frischer
   Review prüft den Plan auf Lücken, Widersprüche, unnötige Technik und
   fehlende Tests oder Freigaben.
2. `implement -> review -> fix`: Die Umsetzung wird gegen Plan, bestehende
   Repo-Muster, Fehlerbehandlung, Testabdeckung und Sicherheit geprüft, bevor
   der Stand als abnahmefähig gilt.

Bei wiederholten, unklaren oder schichtübergreifenden Fehlern gilt:
Diagnose vor Fix. Eine Agentenänderung darf erst erfolgen, wenn die Ursache
benannt ist. Änderungen, die Daten-, Controller-/Logik- oder View-Schicht
berühren, brauchen einen expliziten Abgleich dieser Schichten.

Vor einem Merge gehört die vollständige PR-Diff gegen den Zielbranch zur
agentischen Änderungsdisziplin. Agents prüfen `base...head`, Datei- und
Commitliste; ein einzelner HEAD-Commit reicht nicht als Merge-Nachweis. Wenn
die Diff mehr Scope enthält als freigegeben, wird gestoppt und der Branch neu
geschnitten oder der kombinierte Scope ausdrücklich dokumentiert.

Die Agentic-Delivery-Lesart lautet: Nicht menschliche Übergaben schneller
machen, sondern Übergaben maschinenlesbar und prüfbar machen. Ein agentischer
Arbeitsauftrag soll deshalb die fachliche Quelle, den betroffenen Usecase, die
relevanten KG-/BPMN-/Contract-Artefakte, die erwarteten Validatoren und die
erforderlichen Review- oder Freigabepunkte benennen. Risiko-, Rechts-,
Datenschutz-, Test- und Beschaffungsrollen gehören früh in diese Struktur,
nicht erst als spätes Stoppschild nach der Umsetzung.

## Gantt-Regel

Gantt-Dateien werden aktualisiert, wenn sich Roadmap, Scope, Status,
Meilenstein, Pilotbereitschaft oder aktives Build-Board ändern. Kleine
Bugfixes, Tippfehler, lokale Doku-Klarstellungen, Test-/Validator-Fixes oder
UI-Details ohne Roadmap-Wirkung brauchen keine künstliche Gantt-Änderung.

Für das Fortschrittsbild reicht ein wöchentliches Update. Unter der Woche wird
der Gantt nur geändert, wenn sich wirklich Roadmap, Scope, Status,
Meilenstein, Pilotbereitschaft oder aktives Build-Board verschieben.

Das strikte Gate prüft trotzdem:

- Pflicht-Gantts existieren.
- Mermaid-Gantt-Blöcke bleiben auf GitHub renderfähig.
- Bei möglichen Roadmap- oder Themenwirkungen wird ein Hinweis ausgegeben.

## Superpowers-Kompatibilität

Superpowers ist eine nützliche Arbeitsmethodik, aber keine Produktabhängigkeit
von NaC. Die kompatible Regel lautet:

- Offener Scope: erst erkunden, Design/Plan bestätigen lassen.
- Fehler: erst Ursache finden, dann ändern.
- Nichttriviale Codeänderung: Test oder Prüfziel zuerst festhalten.
- Abschluss: keine Erfolgsaussage ohne frische Verifikation und ohne benannten
  nächsten Schritt; wenn dieser Schritt agentisch ausführbar ist und keinen
  Owner-Input braucht, wird er ausgeführt statt als Wartezustand gemeldet.

Diese Methode ergänzt die NaC-Regeln; sie ersetzt keine Datenschutz-,
Sprach-, Lizenz- oder Freigaberegel.
