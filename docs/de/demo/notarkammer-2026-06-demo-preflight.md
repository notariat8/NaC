# Notarkammer-Demo 2026-06: XNP-Preflight und Audit-Spur

Status: owner-freier Protected-PR-Track für die 1h-Live-Demo.

Diese Checkliste wird vor der Vorstellung ausgeführt und als Demo-Nachweis
abgelegt. Sie schuetzt die Live-Demo vor Ad-hoc-Debugging, echten Mandatsdaten,
lokaler Karten-/XNP-Improvisation und nicht freigegebenen Betriebsaktionen.
Alle Beispiele bleiben synthetisch; es gilt ausdruecklich: no real mandate
data, no secrets, no release, no apply, no runtime change, no cloud change.

## Zeitplan CET

| CET-Zeit | Ziel | Ergebnis |
| --- | --- | --- |
| T-03:00 | Frisches Browserprofil öffnen, Cache vermeiden, Demo-Tabs vorbereiten. | Fünf Tabs sind geladen oder als Fallback markiert. |
| T-02:30 | Lokalen Kartenleser-/SAK-Pfad für XNP als Readiness-Gate prüfen. | Evidence zeigt `ready`, `manual_review` oder Stop-Line. |
| T-02:00 | XNP-Localhost, XNotar-Austauschordner und XJustiz-Paketgrenze prüfen. | Nur nicht-sensitive Status- und Hash-Nachweise liegen vor. |
| T-01:30 | 1h-Demo-Skript mit den sichtbaren Browser- und Arbeitsplatzständen abgleichen. | Keine neue Storyline wird begonnen. |
| T-01:00 | Stop-Lines laut lesen und Browser-Tabs final sortieren. | Demo kann ohne Live-Debugging starten. |
| T-00:15 | Nur noch Read-only-Sichtung, keine Änderungen mehr. | Praesentationsfenster bleibt stabil. |

## Browser-Checks

Alle Checks laufen in einem frischen Browserfenster ohne gespeicherte Sitzung.

1. `https://notariat8.de`
   - Erwartung: Startseite laedt und zeigt keine echten Mandatsdaten.
   - Fallback: Bereits geladene Startseite nutzen; nicht live deployen.
2. `https://notariat8.de/prozessmodell.html`
   - Erwartung: Immobilienkaufvertrag, Dauerlogik und kritischer Pfad sind
     sichtbar.
   - Fallback: Lokalen Screenshot oder bereits geöffneten Tab verwenden.
3. `https://app.notariat8.de/healthz`
   - Erwartung: Status ist kurz und unkritisch, zum Beispiel `ok`.
   - Fallback: Health-Tab schliessen und den Fail-Closed-Workspace zeigen.
4. `https://app.notariat8.de/login`
   - Erwartung: Anmeldung oeffnet, aber es werden keine echten Zugangsdaten
     eingegeben.
   - Fallback: Login nicht debuggen; auf Prozessmodell und Workspace-Grenze
     wechseln.
5. `https://app.notariat8.de/workspace`
   - Erwartung: Ohne gültige Sitzung bleibt der Arbeitsbereich geschlossen.
   - Fallback: Genau diesen Zustand als Sicherheitsnachweis erklären.

## XNP- und Kartenleser-Gates

Diese Gates dürfen nur lokal am freigegebenen Arbeitsplatz geprüft werden.
NaC steuert XNP, Kartenleser, SAK lite, secureFramework oder PIN-Eingabe nicht
aus der Cloud.

| Gate | Erwartung | Evidence |
| --- | --- | --- |
| BNotK-Karte und Kartenleser | Sicherheitsklasse-3-Leser ist lokal verfügbar; PIN wird nur am Leser oder in der lokalen zertifizierten Komponente eingegeben. | `nac-cyberjack-rfid`-Readiness ohne PIN, Kartendaten oder Rohattribute. |
| RFID für BNotK-Chipkartenpfad | Kontaktloser Pfad ist ausgeschaltet, sofern kein eigener kontaktloser Usecase freigegeben ist. | Manuelle Attestation oder lokaler Readiness-Status. |
| PC/SC, SAK lite oder XNP-Kartenpfad | Treiber, PC/SC und Kartenpfad sind lokal plausibel bereit. | Minimierte Statusliste; keine System-Secrets. |
| XNP-Localhost | XNP ist nur lokal erreichbar; erlaubter Portbereich bleibt `12774` bis `12784`. | Host, Portbereich und Erreichbarkeitsstatus; kein API-Key, kein Login-Token. |
| Lokale XNP-Anmeldung | Nutzerrolle und Amtstaetigkeitskontext werden nur lokal bestätigt. | Ja/Nein-Attestation; keine Session-Werte. |
| XNotar-Modul | Für Registerfaelle ist der Austauschordner bekannt und schreibend nur nach Owner-Freigabe nutzbar. | Pfadstatus als Hash oder Platzhalter; keine Dokumentinhalte. |
| XJustiz-Paketgrenze | Paketstruktur wird nur synthetisch oder mit leerem Testpaket erklärt. | Schema-/Strukturstatus; keine Urkunden-, UVZ-, VVZ- oder Registerinhalte. |

## Audit-Spur

Die Demo-Audit-Spur besteht aus einem Protected PR, Testausgaben und
minimierten Evidence-Artefakten. Sie ist kein Betriebsjournal und keine
Mandatsakte.

- Protected PR enthält nur Dokumentation und Tests.
- Evidence-IDs dürfen synthetisch sein, zum Beispiel `DEMO-XNP-2026-06-001`.
- Zeitstempel, Commit-SHA, Branch und Testergebnis werden dokumentiert.
- Pfade, Ports und Reader-Fingerprints werden nur gehasht oder als Status
  beschrieben.
- Keine PIN, kein API-Key, kein Login-Token, keine Kartenrohdaten und keine
  Urkundeninhalte werden in Git, PR-Kommentaren oder LLM-Kontext abgelegt.
- Jede Abweichung wird als `ready`, `manual_review` oder `blocked` markiert.

## Fallback-Entscheidungen

| Lage | Entscheidung |
| --- | --- |
| Public-Seite langsam, Prozessmodell-Tab vorhanden | Auf vorhandenen Tab wechseln und offen sagen: "Wir zeigen die geprüfte Demo-Sicht." |
| Login braucht laenger als zwei Minuten | Nicht warten, Workspace fail-closed zeigen. |
| Kartenleser, PC/SC, SAK lite oder secureFramework unklar | XNP-/Kartenpfad nicht zeigen; nur das Preflight-Gate und die Stop-Line erklären. |
| XNP-Localhost nicht erreichbar | Keine Portsuche im Termin; Status `manual_review` oder `blocked` dokumentieren. |
| XNotar-Austauschordner oder XJustiz-Struktur nicht sicher abgegrenzt | Kein Paket öffnen; nur synthetische Paketgrenze erklären. |
| Lokaler Editor ist nicht verfügbar | Öffentliche Prozessmodellseite verwenden, GitHub-PR nur als Governance-Nachweis nennen. |
| Netzwerk schwankt | Keine neuen Tabs öffnen; nur geladene Demo-Tabs verwenden. |

## Stop-Lines

- Stop-Line: "Wir debuggen jetzt nicht live; die Demo zeigt den geprüften
  Prozesspfad."
- Stop-Line: "Ohne Sitzung bleibt der Arbeitsbereich geschlossen. Das ist hier
  der gewünschte Sicherheitsnachweis."
- Stop-Line: "XNP, XNotar und XJustiz bleiben lokal und werden nur gezeigt,
  wenn Kartenpfad, Rolle und Evidence vorher gruen sind."
- Stop-Line: "Für die Kammer-Vorstellung verwenden wir ausschließlich
  synthetische Demo-Daten."
- Stop-Line: "Diese Demo enthält keine Release-, Apply-, Runtime- oder
  Cloud-Aktion."

## Owner-Gates

Diese Punkte bleiben offene Owner-Gates und werden nicht im owner-freien Track
entschieden:

- Freigabe der finalen 1h-Erzählung durch Demo-Owner.
- Freigabe, ob ein echter Login im Termin gezeigt wird oder nur der
  geschlossene Workspace.
- Freigabe, ob ein lokaler XNP-Arbeitsplatz überhaupt gezeigt wird.
- Freigabe des finalen Browserfensters unmittelbar vor Start.
- Merge-Entscheidung für diesen geschuetzten PR.

## PR-Track

- Branch: `agent/notarkammer-demo-preflight-audit`.
- Scope: nur `docs/de/demo/`, `docs/en/demo/` und `tests/`.
- Checks: Language Parity, Documentation Links und Strict Quality Gate.
- Keine OCI-, Runtime-, Release-, Apply- oder Infrastruktur-Änderungen.
- Keine echten Personen-, Akten-, Urkunden-, Ausweis-, Register- oder
  Grundstücksdaten verwenden.
