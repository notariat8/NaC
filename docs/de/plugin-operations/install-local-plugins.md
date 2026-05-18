# Lokale NaC-Plugins installieren

## Zweck

Die Plugin-Suite ist repo-lokal und mit NaC versioniert. Marktplatz-Metadaten
liegen in [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json);
Plugin-Wurzeln liegen unter [plugins/](../../../plugins).

## Day0-Validierung

```bash
cd ~/NaC
python3 scripts/validate_plugins.py
python3 scripts/install_local_plugins.py --mode link
PYTHONPATH=src python3 scripts/quality_gate.py --profile standard
```

Nach dem Installationsschritt Codex beenden und mit dem Workspace `~/NaC` neu
oeffnen. Die laufende Session liest aktive Tools und Plugins beim Start ein;
repo-lokale Plugins werden nicht nachträglich in eine bereits gestartete
Session injiziert.

## Warum Eine Session Keine Plugins Zeigt

Wenn die Plugin-Ordner lokal vorhanden sind, diese Session aber keine Plugins
zeigt, sind zwei Dinge auseinandergefallen:

1. Das Repository enthält die Quelle der Wahrheit:
   [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
   und [plugins/](../../../plugins).
2. Die lokale Codex-Umgebung braucht zusätzlich eine Discovery-Spiegelung im
   home-lokalen Plugin-Root. Ohne diese Spiegelung, oder ohne Neustart nach
   der Spiegelung, sieht eine neue Session die repo-lokalen Plugins nicht.

`scripts/install_local_plugins.py --mode link` spiegelt deshalb den Marktplatz
nach `~/.agents/plugins/marketplace.json`. Die Plugin-Ordner werden unter
`~/plugins/<plugin>` verlinkt. Mit `NAC_PLUGIN_HOME=/anderer/root` kann ein
abweichender Home-Root gesetzt werden; dann liegen Marktplatz und Plugins
unter diesem Root. Der Link-Modus ist der Standard für Entwicklung, weil das
Repository die einzige Quelle der Wahrheit bleibt. Falls Symlinks in einer
Umgebung nicht erlaubt sind, ist `--mode copy` der Fallback.

Wenn `~/.agents` in einer verwalteten Codex-Session read-only gemountet ist,
den Installationsschritt im Host-Workspace beziehungsweise auf dem eigentlichen
Arbeitsplatz ausführen. Für reine Integrationsprüfungen kann ein schreibbarer
Test-Root mit `--target-root /tmp/nac-plugin-home` genutzt werden; für echte
Codex-Discovery bleibt der home-lokale Root maßgeblich.

## Lokales Installationsmuster

1. Codex mit Workspace `~/NaC` oeffnen.
2. Prüfen, dass [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
   die gewünschten Plugins listet.
3. `python3 scripts/install_local_plugins.py --mode link` ausführen.
4. Codex neu starten oder eine neue Session mit Workspace `~/NaC` oeffnen.
5. Für notariatsseitige Online-HRA-Arbeit zuerst `nac-cyberjack-rfid`,
   danach `nac-bnotk-xnp` und danach `nac-handelsregister` installieren.
6. Falls die Codex-Umgebung es unterstützt, aus dem repo-lokalen Marktplatz
   installieren.
7. Prüfen, dass das installierte Card-Plugin den Anzeigenamen
   `Karte/SAK` und den Quellpfad `./plugins/nac-cyberjack-rfid` hat.
8. Prüfen, dass das installierte XNP-Plugin den Anzeigenamen
   `XNP-Prüfung` und den Quellpfad `./plugins/nac-bnotk-xnp` hat.
9. Falls eine Umgebung nur Kopien statt Symlinks akzeptiert,
   `python3 scripts/install_local_plugins.py --mode copy --force` nach
   Freigabe nutzen; die Quelle der Wahrheit bleibt dieses Repository.

## Operative Grenze

Die aktuellen Plugins sind installierbare Skill-Plugins. Sie enthalten keine
direkten externen Schreibadapter, Portalautomatisierung, Karten-Zugriffe,
Zertifikatsverarbeitung oder Geheimnis-Speicherung. Das erfordert jeweils einen
separat geprüften Connector-PR.

Für Online-HRA ist `nac-cyberjack-rfid` die installierbare Karten- und
SAK-Prüfung und `nac-bnotk-xnp` die installierbare XNP-Bereitschafts- und
Authentifizierungsprüfung. Sie authentifizieren nicht eigenständig als Notar,
speichern keine PINs oder Zugangsdaten, loesen keine XNotar-Importe aus und
reichen keine Anmeldungen ein.
