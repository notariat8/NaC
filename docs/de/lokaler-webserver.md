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
| `/api/operator-config` | Lokale Operator-Konfiguration für NaC-Fork-Git und getrennten Datenrepo-Ordner. |
| `POST /api/operator-config` | Speichert lokale Operator-Konfiguration ohne Secrets oder Mandatsdaten in der Benutzerkonfiguration. |
| `/api/matters` | Liest Akten/Vorgänge aus dem konfigurierten Datenrepo inklusive Statuszählern je Usecase. |
| `POST /api/matters` | Legt eine neue Demo-Akte im konfigurierten Datenrepo an. |
| `POST /api/matters/status` | Schreibt Statuswechsel für eine bestehende Demo-Akte ins Datenrepo und Journal. |
| `/api/import-proposals` | Liest Import-Vorschläge aus dem Datenrepo-Eingang, z.B. aus Prompt-, Scan-, E-Mail- oder Fax-Auswertungen. |
| `POST /api/import-proposals` | Legt einen synthetischen Import-Vorschlag samt optional gestagten Testdateien im Datenrepo-Eingang an. |
| `POST /api/import-proposals/accept` | Übernimmt einen geprüften Import-Vorschlag als Demo-Akte und kopiert gestagte Testdateien in den Dokumentbereich. |
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
Aktenverwaltung, Kontrollansicht, Kanzlei-Workflow-Bereich,
Arbeitsplatztests und Handbuchpfad.

Technisch dient [scripts/nac_hw_bridge.py](../../scripts/nac_hw_bridge.py) die
statische Oberfläche aus [web/local-operator/](../../web/local-operator) aus
und delegiert BPMN-/KG-Routen an [src/nac_web/server.py](../../src/nac_web/server.py).
Dadurch können Bürooberfläche und Modellansichten über denselben lokalen Port
laufen, ohne Mandatsdaten oder Zugangsdaten ins Repo zu schreiben. Das
Footer-Menü `Konfig` speichert nur lokale Arbeitsstationswerte wie
NaC-Fork-Git-URL, Daten-Git-URL und Datenrepo-Ordner in der Benutzerkonfiguration;
es ändert weder Git-Remotes noch klont es Repositories automatisch. Die
Vorgangskarten bieten die primäre Tagesaktion `Akten öffnen`, die sekundäre
Aktion `Neu`, die Kontrollaktion `Checkliste prüfen` und den eingeklappten
Bereich `Kanzlei-Workflow`; Demo-Aktenfunktionen schreiben ausschließlich in
das konfigurierte Demo-Datenrepo und führen die Status `offen`, `warten` und
`abgeschlossen`.

Der Bereich `Eingang` verbindet Prompt-/Scan-/E-Mail-/Fax-Erfassung mit der
Webapp: Codex oder ein lokaler Importer schreibt zunächst nur einen
Import-Vorschlag unter `eingang/import-vorschlaege/`. Die Bürooberfläche zeigt
diesen Vorschlag mit erkannten Metadaten und Dateien an. Erst die explizite
Aktion `Übernehmen` erzeugt daraus eine Demo-Akte mit Journalereignis. Für
echte Produktivdaten bleibt Rohdokumentablage außerhalb öffentlicher Git-Repos
verpflichtend; im Demo-Modus sind nur synthetische Testdaten zulässig.

Für den Demo-Betrieb kann die Oberfläche synthetische Bilddateien direkt im
Browser auswählen, eine kleine Metadatenvorschau vorbereiten und den
Import-Vorschlag ohne Seitenreload im getrennten Datenrepo speichern. Die
sichtbaren Akten- und Eingangsdaten werden bei Fokuswechseln und periodisch
nachgeladen, damit Codex-Schreibaktionen, Uploads und die rechts geöffnete
Webapp denselben Stand zeigen.

Die Aktenansicht sucht Akten und offene Import-Vorschläge gemeinsam. Wenn für
eine Person wie `Mustermann` noch keine Akte existiert, aber ein passender
Eingang vorliegt, zeigt die Oberfläche diesen Eingang direkt im Aktenbereich
und bietet die explizite Übernahme an. Arbeitsbereiche außerhalb der
Vorgangsliste erhalten außerdem `← Zurück` und `Übersicht`, damit jede UI-Aktion
einen sichtbaren Rückweg hat.

Für die Menüführung gilt der [Operator Styleguide](operator-styleguide.md):
Vorgangskarten trennen `Aktenverwaltung`, `Kontrolle` und
`Kanzlei-Workflow`. Aktenverwaltung ist die sichtbare Tagesarbeit, Checklisten
sind Kontrollansichten, und Ablauf-/Bearbeitungsfunktionen sind
freigaberelevante Kanzlei-Stammdaten. Beim Anlegen einer Akte schreibt die
Operator-Bridge deshalb ein `workflow_binding` mit Workflow-Version,
Artefakt-Hashes und Bindungszeitpunkt in die Akte. Zusätzlich erzeugt sie pro
Akte `checkliste.json` als eingefrorenen Fallstand der Usecase-Checkliste und
liefert daraus den nächsten offenen Schritt an die Aktenübersicht.

## Geplante Endnutzer-Paketierung

Der aktuelle Entwicklerstart über `python scripts/nac.py operator --open` ist
nicht der Zielzustand für Standardnutzer. Der offene Roadmap-Punkt
`Operator-Endnutzer-Launcher paketieren` bündelt die lokale Operator-Webapp als
installierten `NaC Operator` mit eigener Laufzeit, Startmenü-Einstieg,
internem Healthcheck und geführter Auswahl des getrennten Datenrepos. Nutzer
sollen dabei keine Shell, keine Python-Kommandos, keine Curl-Tests und keine
Codex-Sandbox-Freigaben sehen.

Die Umsetzung erfolgt nach der weiteren Schärfung der Notariats-Startseite und
vor einer breiteren Pilotverteilung. Der Launcher darf weiterhin nur lokal an
`127.0.0.1` binden, schreibt Logs in die Benutzerumgebung, verwaltet die
Operator-Konfiguration unter `%LOCALAPPDATA%\NaC` und hält Produktcode,
Konfiguration und Demo-/Mandatsdaten getrennt.

## Geplante ChatGPT- und Codex-Anbindung

Für die spätere direkte Arbeit mit ChatGPT oder Codex wird nicht die
Browseroberfläche selbst zur fachlichen Wahrheit. Die Webapp bleibt die lokale
Bürooberfläche; die Chat-Integration spricht eine kleine, geprüfte
Werkzeugschicht an.

Die drei technischen Wege sind getrennt zu behandeln:

1. `Custom GPT` mit Action und HTTPS-Tunnel ist nur ein Demo-Pfad für
   synthetische Daten. Ein Tunnel zu `localhost` macht eine lokale API faktisch
   öffentlich erreichbar und ist deshalb nicht der Produktpfad für echte
   Mandatsdaten.
2. `nac-mcp` ist die Zielarchitektur. Ein lokaler oder tenantfähiger MCP-Server
   stellt geprüfte Tools wie Vorgänge lesen, Importvorschlag anlegen,
   Importvorschlag übernehmen, BPMN-Änderung vorschlagen und Quality Gate
   starten bereit. Codex kann diesen MCP-Server lokal nutzen; ChatGPT Apps SDK
   kann denselben Tool-Vertrag später mit UI-Komponenten verwenden.
3. Ein Chat direkt in der Operator-Webapp ist ein optionaler zusätzlicher
   Bedienkanal. Dann ruft ein lokaler Backend-Endpunkt die OpenAI API auf; der
   API-Schlüssel bleibt serverseitig und die lokalen Tools bleiben dieselben.

Für NaC gilt daher: Actions mit OpenAPI und Tunnel dürfen kurze Demos
ermöglichen, aber die regulierte Zielarchitektur ist MCP/App SDK mit expliziter
Authentifizierung, minimalen Tool-Rechten, Auditlog, menschlicher Bestätigung
für Schreibaktionen und strikter Trennung zwischen Produktcode und Datenrepo.
