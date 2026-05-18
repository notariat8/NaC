---
name: nac-bnotk-xnp
description: Nach nac-cyberjack-rfid nutzen, wenn Online-HRA, Handelsregister, XNotar oder Notariatssoftware XNP-Authentifizierungsbereitschaft, Amtstätigkeitskontext, API-Key-Vorhandensein ohne Werte oder Nachweispläne braucht.
---

# XNP-Prüfung

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Run after `nac-cyberjack-rfid` for notary-side XNP readiness,
Amtstätigkeitskontext checks, XNotar handoff planning and metadata-only
evidence. Do not store credentials or perform filings without reviewed connector
code and approval.

## Einsatzgrenze

Laufzeitmodus: `local-xnp-auth-gate`.

Dieser installierbare lokale Codex-Skill ist das XNP-Gate für notarielle
Online-HRA- und Register-Workflows. `nac-cyberjack-rfid` muss zuerst laufen,
weil XNP-Login-Tests von Kartenleser-, BNotK-SAK-lite- oder XNP-Kartenpfad- und
secureFramework-Readiness abhängen. Standard ist Planvorschau, lokale
Ausführung, ausdrückliche menschliche Freigabe und Evidence-Metadaten.
Externe Schreibaktionen sind verboten, solange kein separat geprüfter Connector
diese Aktion implementiert.

## Erlaubte Arbeit

- Lokale XNP-Readiness, aktuellen lokalen Authentifizierungsstatus und
  Schnittstellenstatus dokumentieren.
- Vom Repository-Root aus `python plugins\nac-bnotk-xnp\scripts\reader_prompt.py --json`
  ausführen, um einen lokalen XNP-Reader-Prompt-Preflight für den
  cyberJack-Pfad zu erzeugen.
- `--probe-morris-api` ergänzen, wenn der Betreiber ausdrücklich will, dass
  das darunterliegende `nac-cyberjack-rfid`-Gate morris-Localhost-API und
  PC/SC-List-Readers prüft.
- Boolesche Praesenz lokaler Konfiguration ohne Werte erfassen.
- Lokale XNotar-/Register-Übergabeschritte für Notariatssoftware vorbereiten.

## Verbotene Arbeit

- Passwörter, PINs, private Schlüssel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- Lokale XNP-Authentifizierung, Amtstätigkeitskontext-Validierung,
  menschliches Review, Register-, Postfach- oder notarielle Kontrollen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdrücklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Geschützte Portale scrapen oder veröffentlichte Nutzungslimits umgehen.

## Ablauf

1. Modus einordnen: Bürger-Preflight oder notarieller Workstation-Workflow.
2. Abgeschlossene `nac-cyberjack-rfid`-Karten-/SAK-Readiness bestätigen oder den
   lokalen XNP-Reader-Prompt-Preflight für eine Evidence-Vorschau ausführen.
3. Für notarielle Workflows lokale XNP-Installation, lokalen Login, Nutzerrolle
   und Amtstätigkeitskontext vor Handelsregister-Arbeit prüfen.
4. XNotar-/Registermodul oder Austauschordner-Route, lokalen Admin-Owner und
   Schnittstellenstatus des Herstellers prüfen.
5. Vor jeder lokalen oder externen Aktion eine lesbare Day1-Planvorschau erstellen.
6. Für regulierte Einreichungen, Registeranmeldungen, notarielle Aktionen oder
   Cloud-Änderungen ausdrückliche menschliche Freigabe einholen.
7. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, lokale
   Readiness, Reader-Prompt-Route, Quelle, Hash, Entscheidung, Ergebnis und
   Follow-up-Owner.
8. Für Day2 Drift, abgelaufene Zugriffe, fehlgeschlagene Checks,
   Versionsänderungen und Rezertifizierungsaufgaben melden.

## Rückgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Plan`, `Approval
Needed`, `Evidence` und `Day2 Follow-up`. Wenn etwas nicht fortgesetzt werden
kann, gehört es unter `Approval Needed` mit Verweis auf
[docs/de/plugin-operations/account-and-approval-requests.md](../../../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../../../docs/en/plugin-operations/account-and-approval-requests.md).

## Quellplan

- [docs/de/plugin-plans/bnotk-xnp-notariatssoftware.md](../../../../docs/de/plugin-plans/bnotk-xnp-notariatssoftware.md)
- [docs/en/plugin-plans/bnotk-xnp-notariatssoftware.md](../../../../docs/en/plugin-plans/bnotk-xnp-notariatssoftware.md)
