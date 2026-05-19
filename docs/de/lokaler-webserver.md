# Lokaler Webserver Für Grafische Ausgaben

Status: erster lokaler Webserver umgesetzt am 2026-05-19

## Zweck

NaC soll grafische Ausgaben nicht verstreut als Einzeldateien erzeugen. Der
lokale Webserver ist die gemeinsame Oberfläche für:

- BPMN-Prozessansichten,
- KG-Editor-Views,
- spätere bpmn-js-Bearbeitung,
- spätere Prüfberichte, Diffs und Freigabeansichten.

Der Server ist lokal gedacht. Standardmäßig bindet er an `127.0.0.1` und liest
nur Dateien aus dem aktuellen Repository.

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

## Aktuelle Routen

| Route | Inhalt |
| --- | --- |
| `/` | Lokales Dashboard mit BPMN- und KG-Links. |
| `/bpmn/<modell>` | SVG-Ansicht eines lokalen BPMN-Modells. |
| `/kg/<slug>` | Sichere KG-Editor-View ohne `value`-Felder. |
| `/api/bpmn/<modell>` | JSON-Struktur des BPMN-Modells. |
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

Der aktuelle Server rendert BPMN bereits lokal als SVG-Vorschau. Der nächste
Schritt ist, in diese lokale Oberfläche einen bpmn-js-Editor einzubetten:

1. eingeschränkte Palette,
2. NaC-Properties-Panel aus [bpmn/nac-moddle.json](../../bpmn/nac-moddle.json),
3. Speichern als BPMN-XML,
4. Prüfung mit [scripts/validate_bpmn_models.py](../../scripts/validate_bpmn_models.py),
5. Pull Request statt Direktänderung.

Damit wird bpmn-js zur Bedienoberfläche, während Python und Git die
prüfbare Governance-Schicht bleiben.
