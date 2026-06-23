# Notarkammer-Demo: Login-Checkliste

Status: kurze Demo-Checkliste für den geschützten Einstieg. Keine
Runtime-Änderung, kein Infrastruktur-Apply, keine Secrets.

## Einstieg

- Start: `https://app.notariat8.de/login`
- Nur der Login-Einstieg und die geschlossene Startgrenze sind im Scope.
- Kein Zugriff auf Mandate, Akteninhalte, Urkunden, Register- oder
  Grundstücksdaten.

## Statuspunkte

| Punkt | Zeigbar | Stopper |
| --- | --- | --- |
| Token-Austausch | Ampel- oder Textstatus ohne technische Rohwerte. | Nicht abgeschlossen, ungültig oder nicht vorführstabil. |
| Token-Prüfung | Bestätigung, dass die Anmeldung geprüft wurde. | Prüfung offen, fehlgeschlagen oder nicht belastbar. |
| Rollengate | Demo-Rolle ist für den Einstieg freigegeben. | Rolle offen, unbekannt oder nicht demo-freigegeben. |
| Sitzung | Sitzung nur redaktiert: Status, Zeitfenster, Demo-Freigabe. | Sitzung offen, nicht belastbar oder mit Rohwerten sichtbar. |

## Redaktionsgrenzen

- Keine Secrets, Tokens, Claims oder technischen Rohwerte zeigen.
- Keine Callbacks, keine Parameter oder Browser-Adressdetails zeigen.
- Keine Providerdetails, Konfigurationswerte oder Anbieterdiagnosen nennen.
- Keine Konsolen, Cloud-Ansichten oder Infrastrukturaktionen im Termin.
- Keine echten Personen-, Akten-, Urkunden-, Register- oder
  Grundstücksdaten verwenden.

## Entscheidung

- Grün: Alle vier Statuspunkte sind abgeschlossen und redaktiert zeigbar.
- Gelb: Ein Punkt ist offen; Einstieg als fail-closed erklären und auf den
  vorbereiteten Prozesspfad wechseln.
- Rot: Ein Punkt ist fehlgeschlagen oder zeigt Rohwerte; Live-Pfad stoppen,
  keine Live-Fehlersuche.
