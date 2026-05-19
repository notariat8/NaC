# Lokaler Webserver Für Grafische Ausgaben

Status: BPMN-Editor- und Speicherfläche ergänzt am 2026-05-19

## Zweck

NaC soll grafische Ausgaben nicht verstreut als Einzeldateien erzeugen. Der
lokale Webserver ist die gemeinsame Oberfläche für:

- BPMN-Prozessansichten,
- KG-Editor-Views,
- bpmn-js-nahe BPMN-Bearbeitung,
- spätere Prüfberichte, Diffs und Freigabeansichten.

Der Server ist lokal gedacht. Standardmäßig bindet er an `127.0.0.1` und liest
nur Dateien aus dem aktuellen Repository.

Für Leser ohne Zugriff auf die laufende Webapp gibt es eine bebilderte
Erklärung der Oberfläche unter [webapp-ohne-zugriff.md](webapp-ohne-zugriff.md).

## Start

```bash
python scripts/nac.py web
```

Danach im Browser öffnen:

```text
http://127.0.0.1:8765/
```

Optional:

```bash
python scripts/nac.py web --open
```

Der ältere Direkteinstieg `python scripts/nac_web.py --repo-root .` bleibt
kompatibel. Die Produktdokumentation führt aber über `nac`, damit jede
grafische Oberfläche denselben zentralen Bedienpfad nutzt.

Die lokale Operator-Bridge unter `python scripts/nac.py operator --open`
delegiert dieselben BPMN-/KG-Routen zusätzlich auf Port `8766`, damit die
Operator-Webapp die Modelle direkt öffnen kann.

## Aktuelle Routen

| Route | Inhalt |
| --- | --- |
| `/` | Lokales Dashboard mit BPMN- und KG-Links. |
| `/bpmn/<modell>` | SVG-Ansicht eines lokalen BPMN-Modells. |
| `/bpmn/<modell>/edit` | Lokale BPMN-Editorfläche mit bpmn-js-Ladepfad und XML-Fallback. |
| `/kg/<slug>` | Sichere KG-Editor-View ohne `value`-Felder. |
| `/api/bpmn/<modell>` | JSON-Struktur des BPMN-Modells. |
| `/api/bpmn/<modell>/xml` | BPMN-XML plus SHA-256 zum konfliktarmen Speichern. |
| `POST /api/bpmn/<modell>/xml` | Speichert BPMN-XML nur, wenn `base_sha256` zum aktuellen Repo-Stand passt. |
| `/api/bpmn-moddle` | NaC-moddle-Descriptor für bpmn-js. |
| `/api/kg/<slug>` | JSON-Struktur der KG-Editor-View. |
| `/healthz` | einfacher Gesundheitscheck. |

## Sicherheitsgrenzen

- Keine echten Mandatsdaten in das öffentliche Repository schreiben.
- Keine Secrets, PINs, Tokens oder API-Keys im Webserver anzeigen.
- Standardbindung bleibt `127.0.0.1`.
- Kein automatischer Merge, keine produktive Fachsystemaktion, keine
  Einreichung aus der lokalen Ansicht.
- Änderungen bleiben später Pull-Request-basiert: Patch, Validierung, Diff,
  Bestätigung und Review.

## Beziehung Zu bpmn-js

Der Server rendert BPMN lokal als SVG-Vorschau und stellt zusätzlich eine
Editorfläche unter `/bpmn/<modell>/edit` bereit. Die Seite lädt das aktuelle
BPMN-XML aus `/api/bpmn/<modell>/xml`, hält den SHA-256 des geladenen Stands
und speichert nur, wenn dieser Hash noch aktuell ist. Dadurch bleiben
Browseränderungen versionierbar und konfliktarm.

Die Editorfläche kann bpmn-js mit dem Descriptor
[bpmn/nac-moddle.json](../../bpmn/nac-moddle.json) laden; wenn bpmn-js im
Browser nicht verfügbar ist, bleibt der XML-Fallback nutzbar. Vor Merge bleibt
die Prüfung mit [scripts/validate_bpmn_models.py](../../scripts/validate_bpmn_models.py)
verbindlich. Git und Review entscheiden, nicht der Browser.

## Operator-Webapp Für Das Büro

Neben `nac web` gibt es `nac operator --open`. Diese Oberfläche ist
usecase-zentriert: Sie startet mit Vorgangskarten, Suchfeld,
Checklisten-/Ablauf-/Bearbeiten-Links, Arbeitsplatztests und Handbuchpfad.

Technisch dient [scripts/nac_hw_bridge.py](../../scripts/nac_hw_bridge.py) die
statische Oberfläche aus [web/local-operator/](../../web/local-operator) aus
und delegiert BPMN-/KG-Routen an [src/nac_web/server.py](../../src/nac_web/server.py).
Dadurch können Bürooberfläche und Modellansichten über denselben lokalen Port
laufen, ohne Mandatsdaten oder Zugangsdaten ins Repo zu schreiben.
