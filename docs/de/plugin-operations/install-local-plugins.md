# Lokale NoC-Plugins installieren

## Zweck

Die Plugin-Suite ist repo-lokal und mit NoC versioniert. Marktplatz-Metadaten
liegen in [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json);
Plugin-Wurzeln liegen unter [plugins/](../../../plugins).

## Day0-Validierung

```bash
cd ~/NoC
python3 scripts/validate_plugins.py
python3 scripts/install_local_plugins.py --mode link
PYTHONPATH=src python3 scripts/quality_gate.py --profile standard
```

Nach dem Installationsschritt Codex beenden und mit dem Workspace `~/NoC` neu
oeffnen. Die laufende Session liest aktive Tools und Plugins beim Start ein;
repo-lokale Plugins werden nicht nachtraeglich in eine bereits gestartete
Session injiziert.

## Warum Eine Session Keine Plugins Zeigt

Wenn die Plugin-Ordner lokal vorhanden sind, diese Session aber keine Plugins
zeigt, sind zwei Dinge auseinandergefallen:

1. Das Repository enthaelt die Quelle der Wahrheit:
   [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
   und [plugins/](../../../plugins).
2. Die lokale Codex-Umgebung braucht zusaetzlich eine Discovery-Spiegelung im
   home-lokalen Plugin-Root. Ohne diese Spiegelung, oder ohne Neustart nach
   der Spiegelung, sieht eine neue Session die repo-lokalen Plugins nicht.

`scripts/install_local_plugins.py --mode link` spiegelt deshalb den Marktplatz
nach `~/.agents/plugins/marketplace.json`. Die Plugin-Ordner werden unter
`~/plugins/<plugin>` verlinkt. Mit `NOC_PLUGIN_HOME=/anderer/root` kann ein
abweichender Home-Root gesetzt werden; dann liegen Marktplatz und Plugins
unter diesem Root. Der Link-Modus ist der Standard fuer Entwicklung, weil das
Repository die einzige Quelle der Wahrheit bleibt. Falls Symlinks in einer
Umgebung nicht erlaubt sind, ist `--mode copy` der Fallback.

Wenn `~/.agents` in einer verwalteten Codex-Session read-only gemountet ist,
den Installationsschritt im Host-Workspace beziehungsweise auf dem eigentlichen
Arbeitsplatz ausfuehren. Fuer reine Integrationspruefungen kann ein schreibbarer
Test-Root mit `--target-root /tmp/noc-plugin-home` genutzt werden; fuer echte
Codex-Discovery bleibt der home-lokale Root massgeblich.

## Lokales Installationsmuster

1. Codex mit Workspace `~/NoC` oeffnen.
2. Pruefen, dass [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
   die gewuenschten Plugins listet.
3. `python3 scripts/install_local_plugins.py --mode link` ausfuehren.
4. Codex neu starten oder eine neue Session mit Workspace `~/NoC` oeffnen.
5. Fuer notariatsseitige Online-HRA-Arbeit zuerst `noc-cyberjack-rfid`,
   danach `noc-bnotk-xnp` und danach `noc-handelsregister` installieren.
6. Falls die Codex-Umgebung es unterstuetzt, aus dem repo-lokalen Marktplatz
   installieren.
7. Pruefen, dass das installierte Card-Plugin den Anzeigenamen
   `NoC Karten- und SAK-Pruefung` und den Quellpfad `./plugins/noc-cyberjack-rfid` hat.
8. Pruefen, dass das installierte XNP-Plugin den Anzeigenamen
   `NoC XNP-Notariatspruefung` und den Quellpfad `./plugins/noc-bnotk-xnp` hat.
9. Falls eine Umgebung nur Kopien statt Symlinks akzeptiert,
   `python3 scripts/install_local_plugins.py --mode copy --force` nach
   Freigabe nutzen; die Quelle der Wahrheit bleibt dieses Repository.

## Operative Grenze

Die aktuellen Plugins sind installierbare Skill-Plugins. Sie enthalten keine
direkten externen Schreibadapter, Portalautomatisierung, Karten-Zugriffe,
Zertifikatsverarbeitung oder Geheimnis-Speicherung. Das erfordert jeweils einen
separat geprueften Connector-PR.

Fuer Online-HRA ist `noc-cyberjack-rfid` die installierbare Karten- und
SAK-Pruefung und `noc-bnotk-xnp` die installierbare XNP-Bereitschafts- und
Authentifizierungspruefung. Sie authentifizieren nicht eigenstaendig als Notar,
speichern keine PINs oder Zugangsdaten, loesen keine XNotar-Importe aus und
reichen keine Anmeldungen ein.
