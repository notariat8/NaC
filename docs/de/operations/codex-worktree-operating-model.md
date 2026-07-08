# Codex Worktree Operating Model

## Zweck

Git-Worktrees sind die lokale Isolationsschicht für parallele NaC-Arbeit an
mehreren Branches. Sie lösen ein anderes Problem als Subagents:

- Worktrees isolieren Dateien, Branches und lokale Testartefakte.
- Subagents teilen Analyse-, Review- oder Implementierungsarbeit innerhalb
  eines klaren Arbeitsauftrags.
- Forks sind nur für getrennte GitHub-Pfade oder externe Beitragswege gedacht.

Dieses Modell ist read-only in der Prüfung und owner-gated in der Bereinigung.
Es speichert keine Secrets, keine Tokens, keine Zertifikate und keine
Mandatsdaten.

## Namensschema

Neue Worktrees erhalten sprechende Branch- und Ordnernamen:

```bash
git worktree add ../NaC-<slug> -b <branch>
```

Regeln:

- `<slug>` beschreibt den Scope, z.B. `matter-access-policy-hardening`.
- `<branch>` folgt dem Issue-/Slice-Namen, z.B.
  `matter-access-policy-hardening`.
- Ein Worktree gehört genau zu einem Branch und zu einem fachlichen Slice.
- Worktrees sind kurzlebig und werden nach Merge oder Abbruch entfernt.

## Standardablauf

1. Issue anlegen und Scope festhalten.
2. Branch im Haupt-Checkout oder als Worktree erstellen.
3. In genau einem Worktree implementieren, testen und PR öffnen.
4. Nach Merge den Worktree-Status prüfen.
5. Bereinigung nur als owner-gated Batch ausführen.

Read-only Audit:

```bash
nac git worktree-audit
nac git worktree-audit --format json
```

Der Audit liest nur lokale Git-Metadaten. Er führt kein `git worktree remove`,
kein `git branch -d` und kein `git push origin --delete` aus.

## Cleanup-Grenze

Der Audit darf Cleanup-Kandidaten melden, aber nicht bereinigen. Diese
Befehle bleiben explizit owner-gated:

```bash
git worktree remove ../NaC-<slug>
git branch -d <branch>
git push origin --delete <branch>
```

Vor Remote-Löschung muss geprüft sein, dass kein offener Pull Request und kein
laufender Arbeitsauftrag mehr auf dem Branch liegt. Der lokale Audit nutzt
keine GitHub API und kein Netzwerk; er kann diesen PR-Status nur als
Pflichtprüfung markieren.

## Einsatzgrenze zu Subagents

Worktrees nutzen, wenn parallele Arbeit Dateien oder Branches getrennt halten
muss:

- mehrere PRs gleichzeitig vorbereiten,
- riskante Refactors getrennt vom Haupt-Slice testen,
- lokale Artefakte pro Branch isolieren.

Subagents nutzen, wenn parallele Denk- oder Review-Arbeit reicht:

- Doku-/Code-Review aus mehreren Perspektiven,
- Analyse von Architektur-, Policy- und Testoberflächen,
- fachliche Gegenprüfung ohne eigenen Branch.

Wenn beides nötig ist, bleibt der Lead-Agent verantwortlich: Subagents liefern
Review- oder Implementierungsergebnisse, der Lead-Agent integriert sie in den
jeweiligen Worktree und prüft den finalen Diff.

## Sicherheitsgrenzen

- Keine Mandatsdaten in Worktrees, Tests oder Audit-Artefakten.
- Keine Secrets oder Zertifikatsmaterialien in Branches.
- Keine Destructive-Git-Aktion ohne Owner-Freigabe.
- Keine automatische Remote-Löschung ohne offene-PR-Prüfung.
- `nac git worktree-audit` bleibt read-only und muss auch bei
  Cleanup-Kandidaten mit Exit-Code 0 ausführbar sein, damit er als Diagnose
  und nicht als Löschmechanismus funktioniert.

