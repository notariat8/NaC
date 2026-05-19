# Datenrepo: demo8notariat

NaC trennt Produktlogik und Vorgangsdaten. Das Produktrepo `ofunk/NaC` enthält
Usecases, BPMN-Modelle, Plugins, Regeln, Validatoren und Dokumentation. Das
Datenrepo `ofunk/demo8notariat` ist ein getrenntes Ziel für synthetische Demo-
und Testdaten.

## Ordnerlage

Der lokale Clone soll neben NaC liegen:

```text
/home/ubuntu/NaC
/home/ubuntu/demo8notariat
```

Das Datenrepo wird nicht als Unterordner von NaC geführt. Dadurch können
Vorgangsdaten nicht versehentlich im Produktrepo landen.

## Initialisierung

```bash
python scripts/nac.py tenant init \
  --repo ../demo8notariat \
  --name demo8notariat \
  --remote-url https://github.com/ofunk/demo8notariat.git
```

Der Befehl legt ein Manifest `.nac-tenant.json`, Standardordner und
Hinweisdateien an. Das Manifest markiert das Repo im Demo-Modus.

## Status Prüfen

```bash
python scripts/nac.py tenant status --repo ../demo8notariat
```

Die Prüfung zeigt Manifest, Git-Status, Remote und vorhandene Demo-Vorgänge.

## Demo-Daten Schreiben

```bash
python scripts/nac.py tenant write-demo immobilienkaufvertrag \
  --repo ../demo8notariat \
  --case-id DEMO-2026-0001
```

NaC erzeugt daraus eine synthetische Vorgangsdatei unter
`daten/demo/DEMO-2026-0001/case.json`. Die Datei enthält nur leere,
metadata-only Arbeitsstände aus dem NaC-Usecase. Echte Mandatsdaten, PINs,
Kartenrohdaten, Zugangsdaten, Ausweisdaten und Registerauszüge sind verboten.

## GitHub Heute, Sovereign Git Später

Für Demo-Daten ist GitHub in Ordnung. Für produktive Notariatsdaten ist GitHub
hier nicht das Zielsystem. Produktiv braucht das Datenrepo einen geprüften
Sovereign-/DSGVO-Git-Anbieter oder eine gleichwertige lokale Git-Infrastruktur.

Der NaC-Vertrag bleibt gleich:

```bash
python scripts/nac.py tenant status --repo <datenrepo>
python scripts/nac.py tenant write-demo <usecase> --repo <datenrepo>
```

Beim Wechsel ändert sich der Git-Remote des Datenrepos, nicht das Produktrepo
NaC.
