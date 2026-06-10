# Kundenzentrierte DNS-Erfolgsseite

Datum: 2026-06-10

Issue: https://github.com/notariat8/NaC/issues/81

## Entscheidung

Die öffentliche DNS-Prüfseite wird nach erfolgreicher Domain-Bestätigung als
Einrichtungsstatus dargestellt, nicht als technischer Diagnose-Endpunkt. Der
Neukunde soll verstehen:

1. Die Domain ist bestätigt.
2. Die angegebene E-Mail-Adresse wird für die Einrichtung geprüft.
3. Eine Einladung wird erst nach Freigabe versendet.
4. Es werden keine Mandatsdaten, Urkunden, Ausweise, Akten oder
   Geschäftswerte erfasst.

## Kundensicht

Die Seite verwendet ausschließlich den Produktnamen `notariat8`. Interne
Repo-, Provider-, Plattform- und Rollenbegriffe bleiben aus der Kundensicht
entfernt. Insbesondere erscheinen dort keine Begriffe wie `www-n8`, `NaC`,
`Oracle`, `OCI`, `Admin-Queue`, `Tenant-Slug` oder interne Rollen.

Die Seite spiegelt die übergebenen Angaben sichtbar zurück:

- Domain,
- E-Mail-Adresse der verantwortlichen Person,
- Status der Domain-Bestätigung,
- Status der Einladung.

Damit ist klar, dass notariat8 die E-Mail-Adresse nicht errät, sondern den vom
Kunden angegebenen Wert prüft.

## Navigation

Nach erfolgreicher DNS-Prüfung wird `Einrichtungsstatus öffnen` zur primären
Weiterführung. `Erneut prüfen` bleibt als sekundäre Aktion erhalten. Die
bisherige Formulierung `Domain-Readiness öffnen` entfällt aus der
Kundensicht, weil sie wie interne Produkt- oder Prozesssprache wirkt.

## Technischer Nachweis

Der DNS-TXT-Eintrag bleibt sichtbar, aber als `Technischer Nachweis`. Er ist
nicht mehr die Hauptbotschaft der Seite. Diagnose- und Rohdaten bleiben der
internen Ansicht vorbehalten.

## Grenzen

- Keine automatische Einladung in diesem Schritt.
- Kein produktiver Identity- oder Infrastruktur-Write.
- Kein Secret, Token oder Credential in HTML, Git, Chat oder Logs.
- Kein Provider- oder Cloud-Hinweis in der Kundensicht.
- Keine Mandatsdaten in der öffentlichen Onboarding-Strecke.

## Akzeptanz

- Die Kundenseite nennt Domain und E-Mail-Adresse der verantwortlichen Person.
- Die Kundenseite zeigt `Einrichtungsstatus öffnen`.
- Die Kundenseite erklärt die nächsten Schritte als E-Mail-Prüfung,
  Freigabe und spätere Einladung.
- Die Kundenseite zeigt `Technischer Nachweis` statt einer dominanten
  DNS-Diagnose.
- Die Kundenseite enthält keine internen Begriffe oder Anbieterhinweise.
- Bestehende interne Admin- und Diagnoseansichten bleiben unverändert.
