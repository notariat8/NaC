---
name: noc-cyberjack-rfid
description: Zuerst nutzen, wenn XNP-Login oder Online-HRA BNotK-Kartenbereitschaft, cyberJack-Leserpruefung, RFID-aus-Bestaetigung, Sicherheitsklasse-3-Leser, SAK-lite-/XNP-Kartenpfad, secureFramework, lokale XNP-Schnittstelle, PC/SC, Treiberversionen, Firmware-Hinweise oder Nachweismetadaten braucht.
---

# NoC Karten- und SAK-Pruefung

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Use first for notary-side card, cyberJack reader, RFID-off,
SAK-lite, secureFramework, XNP local-interface and PC/SC readiness checks. The
skill creates metadata-only evidence and never captures PINs, API keys or card
data.

## Einsatzgrenze

Laufzeitmodus: `local-card-sak-gate`.

Dieser installierbare lokale Codex-Skill ist das erste Gate vor XNP-Login-Tests
fuer notarielle Online-HRA-Arbeit. Standard ist Planvorschau, lokale
Ausfuehrung, ausdrueckliche menschliche Freigabe und Evidence-Metadaten.
Externe Schreibaktionen sind verboten, solange kein separat gepruefter Connector
diese Aktion implementiert.

## Erlaubte Arbeit

- Lokale Karten-, kompatible Sicherheitsklasse-3-Leser-, RFID-aus-,
  SAK-lite-/XNP-Kartenpfad-, secureFramework- und XNP-Local-Interface-Readiness
  vorbereiten.
- Vom Repository-Root aus `python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json`
  ausfuehren, um eine lokale Readiness-Evidence-Vorschau zu erzeugen.
- `python plugins\noc-cyberjack-rfid\scripts\check_readiness.py --json --probe-morris-api`
  ausfuehren, wenn der Betreiber ausdruecklich die lokale morris-Localhost-API
  und den PC/SC-List-Readers-Pfad ohne Kartendaten pruefen will.
- Anonymisierte Leser-Fingerprints und Treiberversion-Metadaten erfassen.
- morris-SID-/Auth-Werte nur als Hashes erfassen und nie rohe
  Autorisierungsdaten in Evidence offenlegen.
- PIN- oder Kartenprobleme an den menschlichen Betreiber routen, ohne Werte zu
  erfragen.
- Nur nicht geheime XNP-Local-Interface-Metadaten wie Aktivstatus und
  Localhost-Portbereich erfassen.

## Verbotene Arbeit

- Passwoerter, PINs, private Schluessel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- XNP-Local-Interface-API-Keys, Login-Daten, Zertifikatsmaterial, Kartenwerte
  oder verschluesselte Key-Blobs in Git speichern.
- Menschliches Review fuer regulierte Einreichungen, Register-, Postfach- oder
  notarielle Aktionen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdruecklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Geschuetzte Portale scrapen oder veroeffentlichte Nutzungslimits umgehen.

## Ablauf

1. Ziel einordnen: XNP-Login-Test, Online-HRA-Gate, beA-/BNotK-Precheck oder
   anderer Karten-Workflow.
2. Day0-Voraussetzungen soweit moeglich mit dem lokalen Readiness-Skript
   pruefen: BNotK-Chip-/Signaturkarte, kompatibler Sicherheitsklasse-3-Leser,
   RFID deaktiviert, PC/SC, Treiber, BNotK SAK lite oder XNP-Kartenpfad,
   secureFramework und XNP-Local-Interface-Konfiguration.
3. Vor jeder lokalen oder externen Aktion eine lesbare Day1-Planvorschau erstellen.
4. Fuer PIN-Prompt, Zertifikatsauswahl, XNP-Login-Test oder notarielle Aktion
   ausdrueckliche menschliche Freigabe einholen.
5. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, nicht geheimer
   Leser-Fingerprint-Hash, RFID-aus-Status, Komponenten-Readiness,
   XNP-Local-Interface-Aktiv-/Port-Metadaten, Entscheidung, Ergebnis und
   Follow-up-Owner.
6. Fuer Day2 Drift, abgelaufene Zugriffe, fehlgeschlagene Checks,
   Versionsaenderungen und Rezertifizierungsaufgaben melden.

## Rueckgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Plan`, `Approval
Needed`, `Evidence` und `Day2 Follow-up`. Wenn etwas nicht fortgesetzt werden
kann, gehoert es unter `Approval Needed` mit Verweis auf
[docs/de/plugin-operations/account-and-approval-requests.md](../../../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../../../docs/en/plugin-operations/account-and-approval-requests.md).

## Quellplan

- [docs/de/plugin-plans/cyberjack-rfid-plugin-integration.md](../../../../docs/de/plugin-plans/cyberjack-rfid-plugin-integration.md)
- [docs/en/plugin-plans/cyberjack-rfid-plugin-integration.md](../../../../docs/en/plugin-plans/cyberjack-rfid-plugin-integration.md)
