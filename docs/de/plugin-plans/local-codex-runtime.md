# Plugin Plan: Local Codex Runtime

Status: `proposed`

## Ziel

Codex soll NaC lokal im echten Workspace `~/NaC` bearbeiten.
Die lokale Sitzung ist der Ausführungsort für Planerzeugung, Git-Operationen, Tests und spätere Fachintegrationen.

## Nicht-Ziele

- Keine NaC-Ausführung aus Omnistation.
- Keine Kopie lokaler Secrets auf Remote-Hosts.
- Keine Umgehung von GitHub-/Browser-/OCI-Callbacks über SSH-Brücken.

## Day0

- Codex Desktop mit Workspace `\\wsl$\\Ubuntu\\home\\ofunk\\NaC` starten.
- Repo aktualisieren:

```bash
cd ~/NaC
git pull
```

- Startcheck ausführen:

```bash
python3 scripts/startup_check.py --ide auto --run-tests
```

- Fehlende lokale Tools dokumentieren und lokal installieren.

## Day1

- Plugin-Pläne lokal in `docs/de/plugin-plans/` regenerieren.
- Änderungen nur über Branch, Review und Merge nach `main` führen.
- Bei Konzeptänderungen Cursor- und VS-Code-Copilot-Pfade synchron halten.
- Plan Preview als Markdown erzeugen, bevor ein Connector echte Zielsysteme verändert.

## Day2

- Regelmäßig `git pull`, Startcheck und Tests ausführen.
- Lokale Tool-Versionen dokumentieren, wenn sie für Reproduzierbarkeit relevant sind.
- Defekte Integrationen als Issue erfassen, nicht durch Remote-Ausführung kaschieren.
- Drift zwischen Repo und Zielsystemen in Git sichtbar machen.

## Lokale Mindesttools

- `git`
- `python3`
- `python` Alias oder kompatibler Command, falls Startup-Check ihn verlangt
- `gh`
- `code`
- optional `pandoc`

## Akzeptanzkriterien

- Codex sieht `/home/ofunk/NaC` als Arbeitsverzeichnis.
- `git status --short --branch` ist lokal ausführbar.
- Startcheck wird lokal gefahren und seine Ergebnisse sind bekannt.
- Plugin-Pläne können lokal geändert, committed und gepusht werden.
