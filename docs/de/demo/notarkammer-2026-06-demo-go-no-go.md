# Notarkammer-Demo 2026-06: Go/No-Go-Matrix

Status: Vorführentscheidung für die Notarkammer-Demo. Diese Matrix ersetzt
kein Review und keine Freigabe; sie verhindert nur spontane Live-Entscheidungen
im Termin.

## Entscheidung

| Bereich | Go | Warn | Stop |
| --- | --- | --- | --- |
| Öffentliche Seite | `notariat8.de` und Prozessmodell laden. | Seite lädt langsam, aber ohne interne Begriffe. | Seite zeigt interne Anbieter-, Cloud-, Secret- oder Mandatsdaten. |
| Prozessmodell | Immobilienkaufvertrag, Dauer, Parallelität, kritischer Pfad und XNP-Grenzen sind sichtbar. | Nur Screenshot oder Fallback-Evidence verfügbar. | Prozessmodell nicht erklärbar oder verweist auf produktive XNP-/Registeraktion. |
| App-Health | `/healthz` ist erreichbar oder der Status ist als technische Grenze erklärbar. | Healthcheck langsam oder kurzzeitig nicht verfügbar. | Diagnose würde Secrets, Wallets, DSN oder Anbieterbetrieb öffnen. |
| Login | Login-Seite öffnet und bleibt nutzerverständlich. | Login bleibt fail-closed; Prozesspfad wird weiter gezeigt. | Callback-Werte, Tokens, Claims oder Zugangsdaten wären sichtbar. |
| Workspace | Ohne geprüfte Sitzung geschlossen oder mit metadata-only Status. | Fail-closed ist langsam, aber fachlich erklärbar. | Voller Arbeitsbereich oder Mandatsdaten würden ohne Gate sichtbar. |
| XNP/Kartenleser | Nur lokale Readiness-Grenze oder vorbereitete Evidence. | Lokaler Arbeitsplatz ist nicht verfügbar; Grenze wird erklärt. | Produktive XNP-, Signatur-, Register- oder Grundbuchhandlung würde ausgelöst. |
| Evidence | Redigierte Evidence ist vorbereitet und geprüft. | Einzelne Evidence fehlt; fallback auf Skript. | Evidence enthält Namen, Aktenwerte, Loginfelder, Callback-Werte oder Payloads. |

## Vorführentscheidung

- **Go:** Alle Kernbereiche sind `Go`, oder höchstens ein Bereich steht auf
  `Warn` und hat eine vorbereitete Fallback-Evidence.
- **Warn-Go:** Zwei Warnungen sind erlaubt, wenn die Kernlinie weiterhin
  sichtbar bleibt: BPMN, XNP-Grenze, geschützter Einstieg, fail-closed Grenze.
- **No-Go:** Jeder `Stop` beendet den Live-Pfad. Dann nur noch vorbereitete
  Screenshots, Skript und Q&A verwenden.

## Nicht verhandelbare Stop-Lines

- Keine echten Mandatsdaten, Ausweise, Urkunden, Registerdaten oder
  Grundstücksdaten.
- Keine Tokens, Claims, Callback-Werte, Secrets, PINs, Wallets oder DSN.
- Keine produktive XNP-, XNotar-, Register- oder Grundbuchhandlung.
- Keine Anbieter-, Cloud- oder interne Betriebsdetails auf Nutzerflächen.
- Kein JSON-Endpunkt als Benutzeroberfläche.

## Nachweis

Vor Start der Demo werden festgehalten:

- Datum/Uhrzeit in CET/CEST.
- Smoke-Ergebnis mit `summary-only`.
- Evidence-IDs aus dem Fallback-Manifest.
- Entscheidung `Go`, `Warn-Go` oder `No-Go`.
- Name der Person, die die Vorführentscheidung getroffen hat.
