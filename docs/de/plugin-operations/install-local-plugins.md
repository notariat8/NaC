# Lokale NoC-Plugins installieren

## Zweck

Die Plugin-Suite ist repo-lokal und mit NoC versioniert. Marketplace-Metadaten
liegen in [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json);
Plugin-Wurzeln liegen unter [plugins/](../../../plugins).

## Day0-Validierung

```bash
cd ~/NoC
python3 scripts/validate_plugins.py
PYTHONPATH=src python3 scripts/quality_gate.py --profile standard
```

## Lokales Installationsmuster

1. Codex mit Workspace `~/NoC` oeffnen.
2. Pruefen, dass [.agents/plugins/marketplace.json](../../../.agents/plugins/marketplace.json)
   die gewuenschten Plugins listet.
3. Fuer notariatsseitige Online-HRA-Arbeit zuerst `noc-cyberjack-rfid`,
   danach `noc-bnotk-xnp` und danach `noc-handelsregister` installieren.
4. Falls die Codex-Umgebung es unterstuetzt, aus dem repo-lokalen Marketplace
   installieren.
5. Pruefen, dass das installierte Card-Plugin den Anzeigenamen
   `NoC Card SAK Gate` und den Quellpfad `./plugins/noc-cyberjack-rfid` hat.
6. Pruefen, dass das installierte XNP-Plugin den Anzeigenamen
   `NoC Notary XNP Gate` und den Quellpfad `./plugins/noc-bnotk-xnp` hat.
7. Falls die Umgebung nur home-lokale Marketplaces unterstuetzt, die geprueften
   Plugin-Ordner und Marketplace-Eintraege erst nach Freigabe kopieren; die
   Quelle der Wahrheit bleibt dieses Repository.

## Operative Grenze

Die aktuellen Plugins sind installierbare Skill-Plugins. Sie enthalten keine
direkten externen Schreibadapter, Portalautomatisierung, Karten-Zugriffe,
Zertifikatshandling oder Secret-Speicherung. Das erfordert jeweils einen
separat geprueften Connector-PR.

Fuer Online-HRA ist `noc-cyberjack-rfid` das installierbare Card/SAK-Gate und
`noc-bnotk-xnp` der installierbare XNP-Readiness- und Authentifizierungsgate-
Companion. Sie authentifizieren nicht eigenstaendig als Notar, speichern keine
PINs oder Notar-Credentials, loesen keine XNotar-Importe aus und reichen keine
Anmeldungen ein.
