# Regelarchitektur

Status: verbindliche Erklärung der NaC-Regelgruppen

Diese Seite erklärt, welche Regeln hart blockieren, welche Regeln
Arbeitsdisziplin sind und welche Regeln nur Orientierung geben. Führende
maschinenlesbare Quelle ist [policies/process-policy.yaml](../../policies/process-policy.yaml).
Agentenflächen wie [AGENTS.md](../../AGENTS.md), Cursor-Regeln und
[.github/copilot-instructions.md](../../.github/copilot-instructions.md) sind
Spiegel dieser Policy.

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
| Abschluss und Fertigmeldung | Verhindert, dass lokale Zwischenstände als fertig gelten. | hart | `nac doctor --profile strict`, `git status`, Abgleich `HEAD` gegen `origin/main` |
| Git-Auslieferung | Trennt produktive PR-Freigabe von Owner-Direct-Arbeit im aktiven Referenzrepo. | modusabhängig | Branchschutz/PR im Produktivmodus, Push+Clean-Check im Referenzmodus |
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
| Owner-Direct-Modus | Aktives Referenzrepo, wenn der Owner direkte Lieferung ausdrücklich beauftragt. | `main` ist validiert, zu GitHub gepusht, `HEAD` entspricht `origin/main`, und der Arbeitsbaum ist sauber. |

Für produktive Notariats- oder Organisations-Forks ist der geschützte PR-Modus
das Zielbild. Der Owner-Direct-Modus ist kein Freibrief für produktive
Mandatsdaten oder sensible Fachänderungen.

## Gantt-Regel

Gantt-Dateien werden aktualisiert, wenn sich Roadmap, Scope, Status,
Meilenstein, Pilotbereitschaft oder aktives Build-Board ändern. Kleine
Bugfixes, Tippfehler, lokale Doku-Klarstellungen, Test-/Validator-Fixes oder
UI-Details ohne Roadmap-Wirkung brauchen keine künstliche Gantt-Änderung.

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
- Abschluss: keine Erfolgsaussage ohne frische Verifikation.

Diese Methode ergänzt die NaC-Regeln; sie ersetzt keine Datenschutz-,
Sprach-, Lizenz- oder Freigaberegel.
