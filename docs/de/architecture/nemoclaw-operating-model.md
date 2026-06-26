# NemoClaw-Betriebsmodell

Status: verbindliche Koordinationsregel
Letzte inhaltliche Anpassung: 2026-06-26

## Zweck

Dieses Betriebsmodell trennt Entwicklung, Projektkoordination und
NemoClaw-Zielbetrieb für NaC. Es verhindert, dass ein Zielsystem-Agent lokal
„fertig“ meldet, obwohl im Gesamtprozess noch Code, Review, Release oder
Owner-Freigabe fehlt.

## Rollen und Arbeitsorte

| Rolle | Arbeitsort | Aufgabe | Darf nicht |
| --- | --- | --- | --- |
| Project Manager | Hauptchat auf `brev01` | Scope, Architekturentscheidungen, Akzeptanzkriterien, Handoffs und Owner-Fragen koordinieren. | Target-Smokes als Gesamtfertigstellung ausgeben. |
| Dev Agent | NaC-Workspace auf `brev01` | Code, Doku, Verträge, Tests, PRs, CI und Releases umsetzen. | Produktive Zielsysteme direkt durch lokale Hotfixes verändern. |
| Target Operator | `notoclaw01-host` in `/home/ubuntu/nac-target-control` | NemoClaw/OpenClaw-Zielsystem, Agent-Manifest, lokale Runtime-Smokes, Evidence und Runbooks prüfen. | NaC-Plattformcode entwickeln, pushen oder PRs als Standard erstellen. |
| Owner | Owner-Chat oder explizite Approval-Nachricht | Architektur-, Release-, Apply-, Secret- und Betriebsfreigaben geben. | Implizite Freigaben ersetzen. |

Der Project Manager ist der führende Koordinator. Solange der Owner keinen
anderen Thread benennt, arbeitet diese Rolle im Hauptchat, der die
repo-übergreifende Lage, `brev01`, GitHub, OCI und `notoclaw01` koordiniert.
Der Target-Operator-Thread auf `notoclaw01-host` ist operativer Zielsystemlauf,
nicht Projektleitung.

## Zugriff auf das NaC-Repository

`notoclaw01-host` darf einen read-only Spiegel des NaC-Repositorys verwenden,
wenn Zielsystem-Smokes, Manifest-Prüfungen oder Release-Vergleiche den
Quellstand benötigen.

Verbindliche Grenzen:

- kein Push-Recht für `notoclaw01-host` als Standard,
- keine GitHub-Write-Tokens auf dem Zielsystem,
- keine PR-Erstellung durch den Target Operator, solange der Owner dies nicht
  ausdrücklich für einen Einzelfall freigibt,
- keine Secrets, PINs, Kartenmaterialien, Mandatsdaten oder privaten Schlüssel
  in `/home/ubuntu/nac-target-control`,
- Zielsystem-Schreibzugriffe bleiben auf `/home/ubuntu/nac-target-control`
  und NemoClaw-/OpenClaw-Runtimepfade begrenzt.

Wenn der read-only Spiegel Authentifizierung benötigt, stoppt der Target
Operator und meldet den konkreten Bedarf. Er darf kein Credential aus
`/home/ubuntu/.codex`, `/home/ubuntu/.nemoclaw` oder einem anderen
Runtime-State lesen.

## Pfadgrenzen auf `notoclaw01-host`

| Pfad | Bedeutung |
| --- | --- |
| `/home/ubuntu/.codex` | Codex Runtime und Konfiguration; nicht für NaC-Artefakte verwenden. |
| `/home/ubuntu/.nemoclaw` | NemoClaw State; keine GitOps-Quellartefakte ablegen. |
| `/sandbox/.openclaw/workspace-*` | OpenClaw-Agent-Workspaces; runtime-nah und nicht das NaC-Repo. |
| `/home/ubuntu/nac-target-control` | Zielsystem-Control, Runbooks, Manifeste, Smokes und nicht-sensitive Evidence. |

## Done-Regeln

### Target Operator

Der Target Operator darf `fertig` nur für seinen Zielsystem-Scope melden, wenn:

- der konkrete Target-Control-Auftrag umgesetzt ist,
- der passende Smoke oder die passende Prüfung frisch grün ist,
- die Evidence keine Secrets und keine Mandatsdaten enthält,
- keine Code-, Vertrags-, Policy-, Release- oder Architekturänderung im NaC-Repo
  nötig ist.

Wenn eine NaC-Repo-Änderung nötig ist, lautet der Status nicht `fertig`,
sondern `Handoff an Project Manager`.

### Dev Agent

Der Dev Agent folgt den Abschlussregeln aus [AGENTS.md](../../../AGENTS.md),
[docs/de/START_HERE.md](../START_HERE.md) und
[docs/de/governance.md](../governance.md). Ein Stand ist nicht fertig, solange
Validierung, Commit, Push, Delivery Mode oder verpflichtende Remote-Checks
fehlen.

### Project Manager

Der Project Manager darf `fertig` für Koordination nur melden, wenn eine
Entscheidung, ein Handoff oder ein Arbeitsauftrag vollständig geroutet ist und
der nächste Owner-Bedarf ausdrücklich benannt oder ausgeschlossen ist.

## Handoff-Format

Wenn `notoclaw01-host` Arbeit an `brev01` oder den Project Manager zurückgibt,
verwendet er dieses Format:

```text
Handoff:
Scope:
Evidence:
Impact:
Required NaC repo change:
Validation already run:
Owner input needed:
```

Wenn kein Owner-Input nötig ist, steht dort `none`.

## Routing-Regeln

| Thema | Führender Ort |
| --- | --- |
| neue Architekturentscheidung | Project-Manager-Hauptchat |
| NaC-Code, Contracts, Tests, Doku, Policies | `brev01` / NaC-Repo |
| NemoClaw CLI, OpenClaw Workspace, Target-Control-Smoke | `notoclaw01-host` |
| OCI, GitHub Release, PR, CI | `brev01` mit Owner-Gate |
| Secrets, Apply, destruktive Aktionen | Owner-Freigabe vor Ausführung |

## Stop-Regeln für den Target Operator

`notoclaw01-host` stoppt und gibt ein Handoff, wenn:

- ein NaC-Code- oder Policy-Fix erforderlich ist,
- ein GitHub-Schreibzugriff nötig wäre,
- ein Secret, Token, PIN, Kartenmaterial oder Mandatsdatum benötigt wird,
- ein produktiver Apply-, Release- oder destruktiver Schritt ansteht,
- die Frage eine Architekturentscheidung ist und nicht nur Target-Validierung.

Damit bleibt `notoclaw01-host` schnell in der Zielsystemprüfung, aber die
Gesamtfertigstellung bleibt beim Project Manager und den NaC-GitOps-Gates.
