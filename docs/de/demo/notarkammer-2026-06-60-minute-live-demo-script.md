# Notarkammer-Demo 2026-06: 60-Minuten-Live-Test-Drehbuch

Status: Operatives Drehbuch für den Demotag. Ziel ist live zeigbar in 60
Minuten, nicht perfekt. Protected PR only; keine produktive Einreichung, keine
echten Mandatsdaten, keine Secrets.

## Purpose

Dieses Drehbuch führt die Notarkammer-Demo als Live-Test. Es nennt
Browser-Startpunkte, Reihenfolge, erwartete sichtbare Ergebnisse und
Failover-Karten. Die Demo zeigt öffentliche Prozesssicht, geschützten Einstieg,
lokale Fachsystemgrenzen und ein prüfbares NaC-Gate.

## Safety Frame

- Protected PR only: Änderungen und Nachweise laufen über Branch, Review und
  Pull Request.
- Keine produktive Einreichung: keine Registereinreichung, keine
  Grundbuchkommunikation und keine Fachsystemaktion aus der Demo heraus.
- Keine echten Mandatsdaten: keine Personen-, Urkunden-, Ausweis-, Register-
  oder Grundstücksdaten öffnen.
- Keine Secrets: keine Zugangsdaten, PINs, Tokens, Schlüssel oder internen
  Betriebsdetails zeigen.
- Der Vorführende debuggt nicht live; do not debug live. Bei Abweichungen gilt die passende
  Failover Card.

## Browser Start Points

| Reihenfolge | Startpunkt | Expected visible result | Operator-Satz |
| --- | --- | --- | --- |
| 1 | `https://notariat8.de` | public start page lädt; keine Mandatsdaten sichtbar. | "Das ist die öffentliche Einstiegssicht." |
| 2 | `https://notariat8.de/prozessmodell.html` | process model lädt mit Immobilienkaufvertrag, Dauerlogik und kritischem Pfad. | "Hier wird der Ablauf prüfbar, nicht produktiv ausgeführt." |
| 3 | `https://app.notariat8.de/healthz` | nicht-sensitiver Status oder geschlossene Grenze. | "Der Status ist nur ein technischer Vorcheck ohne Fachinhalt." |
| 4 | `https://app.notariat8.de/login` | Login oder OIDC-Zwischenseite; keine echten Zugangsdaten eingeben. | "Login wird nur mit Demofreigabe fortgesetzt." |
| 5 | `https://app.notariat8.de/workspace` | protected workspace bleibt ohne freigegebene Sitzung geschlossen. | "Fail-closed ist hier ein erwartetes Sicherheitsergebnis." |

## 60-Minute Live Order

| Zeit | Aktion | Expected visible result | Wenn es nicht klappt |
| --- | --- | --- | --- |
| 0-5 | `https://notariat8.de` öffnen. | public start page ist sichtbar, ohne Akten- oder Mandatsbezug. | Failover: www-n8 does not load. |
| 5-15 | `https://notariat8.de/prozessmodell.html` öffnen. | process model zeigt Immobilienkaufvertrag, Rollen, Dauer und kritischen Pfad. | Failover: BPMN viewer does not load. |
| 15-25 | Am Prozessmodell erklären: Notar, Mitarbeitende, Mandantenschnittstelle, Evidence und Gate. | Das Publikum sieht, welche Schritte offen, geprüft oder blockiert sind. | Beim Screenshot bleiben; keine Live-Reparatur. |
| 25-35 | XNP/Kartenleser/Register/Grundbuch als Grenzen erklären. | Kein Fachsystem öffnet produktiv; sichtbar ist nur die Zugriffspunkt-Logik. | Failover: XNP/card reader is unavailable. |
| 35-45 | `https://app.notariat8.de/healthz`, dann `https://app.notariat8.de/login` zeigen. | Status oder Login/OIDC-Grenze erscheint; keine echten Zugangsdaten. | Failover: app login only shows the OIDC interstitial. |
| 45-52 | `https://app.notariat8.de/workspace` zeigen. | protected workspace ist nur mit freigegebener Sitzung erreichbar; sonst fail-closed. | Geschlossene Grenze als Demo-Ergebnis erklären. |
| 52-55 | Kurzer Vergleich: Unterschriftsbeglaubigung als kleinerer Prozess. | Gleiche Gate-Logik, weniger Prozessschritte. | Vergleich mündlich halten. |
| 55-60 | Abschluss. | Sichtbare Evidence: Browserpfade, Grenzen, Protected PR, keine produktive Einreichung. | Stop-Line nutzen und Fragen aufnehmen. |

## Failover Cards

### www-n8 does not load

1. Nicht live debuggen.
2. Bereits geöffneten Tab oder vorbereiteten Screenshot verwenden; use a
   prepared screenshot.
3. Danach direkt `https://notariat8.de/prozessmodell.html` versuchen.
4. Wenn auch das nicht lädt, den 20-Minuten-Fallback aus dem bestehenden
   Runbook sprechen und die PR-Nachweise zeigen.

### app login only shows the OIDC interstitial

1. Keine Zugangsdaten eingeben und keinen Login erzwingen.
2. Die OIDC-Zwischenseite als Schutzgrenze erklären.
3. Nur bei expliziter Demofreigabe fortsetzen.
4. Ohne Freigabe zu `https://app.notariat8.de/workspace` wechseln und
   fail-closed zeigen.

### XNP/card reader is unavailable

1. Keine Live-XNP-Aktion starten.
2. XNP is a local workstation boundary.
3. Kartenleser/card reader is an access point, kein NaC-Datenspeicher.
4. Gate im Talktrack als `manual_review` oder `blocked` markieren.
5. Register is an external destination und Grundbuch/land register is an
   external destination; NaC löst keine produktive Fachsystemhandlung aus.

### BPMN viewer does not load

1. Nicht live debuggen.
2. Auf vorbereiteten Screenshot oder bestehendes Runbook wechseln.
3. Sichtbare Aussage beibehalten: Prozessmodell, Evidence, Gate und
   Fachsystemgrenze.
4. Wenn nötig, das Gate als `blocked` erklären und zum geschützten Einstieg
   wechseln.

## Boundaries And Access Points

- XNP is a local workstation boundary: NaC beschreibt Readiness und
  Übergabepunkte, steuert XNP aber nicht produktiv.
- Kartenleser/card reader is an access point: Der Kartenleser bleibt lokal am
  freigegebenen Arbeitsplatz.
- Register is an external destination: Handelsregister- und Vereinsregisterwege
  sind externe Zielsysteme mit menschlicher Freigabe.
- Grundbuch/land register is an external destination: Grundbuchzugriffe bleiben
  außerhalb von NaC und ohne Demo-Einreichung.
- XNP does not deliver land-register data to NaC.
- XNotar/XJustiz ist eine Paket- und Austauschgrenze, keine versteckte
  Automatisierung.
- no productive submission, no real mandate data, no secrets.

## Closing Evidence

Am Ende werden nur diese Nachweise gezeigt oder genannt:

- Browser-Startpunkte und sichtbare Ergebnisse.
- Protected PR only als Änderungs- und Auditspur.
- Lokale XNP-/Kartenleser-Grenze.
- Register- und Grundbuchgrenze als externe Zugriffspunkte.
- Failover-Ergebnis: Screenshot, OIDC-Grenze, `manual_review`, `blocked` oder
  fail-closed.

