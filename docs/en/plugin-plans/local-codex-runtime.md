# Plugin Plan: Local Codex Runtime

Status: `proposed`

## Ziel

Codex soll NoC lokal im echten Workspace `~/NoC` bearbeiten.
Die lokale Sitzung ist der Ausfuehrungsort fuer Planerzeugung, Git-Operationen, Tests und spaetere Fachintegrationen.

## Nicht-Ziele

- Keine NoC-Ausfuehrung aus Omnistation.
- Keine Kopie lokaler Secrets auf Remote-Hosts.
- Keine Umgehung von GitHub-/Browser-/OCI-Callbacks ueber SSH-Bruecken.

## Day0

- Codex Desktop mit Workspace `\\wsl$\\Ubuntu\\home\\ofunk\\NoC` starten.
- Repo aktualisieren:

```bash
cd ~/NoC
git pull
```

- Startcheck ausfuehren:

```bash
python3 scripts/startup_check.py --ide auto --run-tests
```

- Fehlende lokale Tools dokumentieren und lokal installieren.

## Day1

- Plugin-Plaene lokal in `docs/en/plugin-plans/` regenerieren.
- Aenderungen nur ueber Branch, Review und Merge nach `main` fuehren.
- Bei Konzeptaenderungen Cursor- und VS-Code-Copilot-Pfade synchron halten.
- Plan Preview als Markdown erzeugen, bevor ein Connector echte Zielsysteme veraendert.

## Day2

- Regelmaessig `git pull`, Startcheck und Tests ausfuehren.
- Lokale Tool-Versionen dokumentieren, wenn sie fuer Reproduzierbarkeit relevant sind.
- Defekte Integrationen als Issue erfassen, nicht durch Remote-Ausfuehrung kaschieren.
- Drift zwischen Repo und Zielsystemen in Git sichtbar machen.

## Lokale Mindesttools

- `git`
- `python3`
- `python` Alias oder kompatibler Command, falls Startup-Check ihn verlangt
- `gh`
- `code`
- optional `pandoc`

## Akzeptanzkriterien

- Codex sieht `/home/ofunk/NoC` als Arbeitsverzeichnis.
- `git status --short --branch` ist lokal ausfuehrbar.
- Startcheck wird lokal gefahren und seine Ergebnisse sind bekannt.
- Plugin-Plaene koennen lokal geaendert, committed und gepusht werden.
