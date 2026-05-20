# Datenrepo: demo8notariat

NaC trennt Produktlogik und Notariatsdaten. Das Produktrepo `ofunk/NaC` enthält
Usecases, BPMN-Modelle, Plugins, Regeln, Validatoren und Dokumentation. Das
Datenrepo `ofunk/demo8notariat` ist ein getrenntes Ziel für Akten, Beteiligte,
Dokumente, Ereignisse, Exporte und spätere produktive Datenstände.

Für die Demo werden synthetische Daten geschrieben. Das Modell ist aber so
angelegt, dass es später auch personenbezogene, fallbezogene und dokumentnahe
Daten abbilden kann.

## Ordnerlage

Der lokale Clone soll neben NaC liegen:

```text
/home/ubuntu/NaC
/home/ubuntu/demo8notariat
```

Das Datenrepo wird nicht als Unterordner von NaC geführt. Dadurch können
Akten- und Personendaten nicht versehentlich im Produktrepo landen.

## Modellprinzip

Die führende Struktur ist JSON mit stabilen IDs. Große Dateien bleiben als
Dateien erhalten.

| Objekt | Pfad | Zweck |
| --- | --- | --- |
| Akte | `akten/<jahr>/<akten_id>/akte.json` | Aktenzeichen, Status, Notar, Beteiligte, Dokumente, Pointer. |
| Person oder Organisation | `personen/<person_id>.json` | Stammdaten, Rollen, Anzeigename und Klassifikation. |
| Dokument | `dokumente/<document_id>/metadata.json` | Titel, Typ, Aktenbezug, Dateipfade, Klassifikation. |
| Binärdatei | `dokumente/<document_id>/original/*` | PDF, JPG, Scan oder andere Originaldatei. |
| Aktenereignis | `akten/<jahr>/<akten_id>/ereignisse.jsonl` | Chronologie innerhalb einer Akte. |
| Journal | `journal/<jahr>/<monat>/<datum>.jsonl` | Repo-weite Ereignisfolge. |
| Index | `index/*.json` | Leselisten für Webapp, Suche und Codex. |

Die Akte enthält nicht alle Daten inline. Sie verweist auf IDs:

```json
{
  "matter_id": "UVZ-2026-0001",
  "participant_person_ids": ["PER-DEMO-VERKAEUFER-ANNA-BERGER"],
  "document_ids": ["DOC-DEMO-2026-0001-GRUNDBUCH"]
}
```

Codex und die Webapp laden zuerst `akte.json` und folgen danach den IDs zu
Personen, Dokumenten und Ereignissen. So bleibt jede Datei klein, diffbar und
auch nach vielen Bearbeitergenerationen lesbar.

## Initialisierung

```bash
python scripts/nac.py tenant init \
  --repo ../demo8notariat \
  --name demo8notariat \
  --remote-url https://github.com/ofunk/demo8notariat.git
```

Der Befehl legt Manifest, Modellbeschreibung, Standardordner und
Hinweisdateien an.

## Status Prüfen

```bash
python scripts/nac.py tenant status --repo ../demo8notariat
```

Die Prüfung zeigt Manifest, Git-Status, Remote, Demo-Vorgänge, Akten, Personen
und Dokumente.

## Musterakte Schreiben

```bash
python scripts/nac.py tenant write-sample-akte \
  --repo ../demo8notariat \
  --akten-id UVZ-2026-0001
```

NaC erzeugt eine synthetische Immobilienkaufvertragsakte mit Akte, Beteiligten,
Dokumentmetadaten, Platzhaltern für PDF/JPG-Dateien, Ereignislog und Indizes.

Der ältere Befehl `tenant write-demo` bleibt als KG-basierter Demo-Export
erhalten:

```bash
python scripts/nac.py tenant write-demo immobilienkaufvertrag \
  --repo ../demo8notariat \
  --case-id DEMO-2026-0001
```

## GitHub Heute, Sovereign Git Später

Für die Demo kann GitHub genutzt werden. Für produktive Notariatsdaten soll
derselbe Modellvertrag auf einen geprüften Sovereign-/DSGVO-Git-Anbieter oder
eine gleichwertige lokale Git-Infrastruktur umziehen.

Beim Wechsel ändert sich der Git-Remote des Datenrepos, nicht das Produktrepo
NaC und nicht die Aktenstruktur.
