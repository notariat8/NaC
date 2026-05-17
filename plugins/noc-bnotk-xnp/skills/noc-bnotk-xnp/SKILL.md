---
name: noc-bnotk-xnp
description: Nach noc-cyberjack-rfid nutzen, wenn Online-HRA, Handelsregister, XNotar oder Notariatssoftware XNP-Authentifizierungsbereitschaft, Amtstaetigkeitskontext, API-Key-Vorhandensein ohne Werte oder Nachweisplaene braucht.
---

# NoC XNP-Notariatspruefung

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Run after `noc-cyberjack-rfid` for notary-side XNP readiness,
Amtstaetigkeitskontext checks, XNotar handoff planning and metadata-only
evidence. Do not store credentials or perform filings without reviewed connector
code and approval.

## Einsatzgrenze

Laufzeitmodus: `local-xnp-auth-gate`.

Dieser installierbare lokale Codex-Skill ist das XNP-Gate fuer notarielle
Online-HRA- und Register-Workflows. `noc-cyberjack-rfid` muss zuerst laufen,
weil XNP-Login-Tests von Kartenleser-, BNotK-SAK-lite- oder XNP-Kartenpfad- und
secureFramework-Readiness abhaengen. Standard ist Planvorschau, lokale
Ausfuehrung, ausdrueckliche menschliche Freigabe und Evidence-Metadaten.
Externe Schreibaktionen sind verboten, solange kein separat gepruefter Connector
diese Aktion implementiert.

## Erlaubte Arbeit

- Lokale XNP-Readiness, aktuellen lokalen Authentifizierungsstatus und
  Schnittstellenstatus dokumentieren.
- Vom Repository-Root aus `python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --json`
  ausfuehren, um einen lokalen XNP-Reader-Prompt-Preflight fuer den
  cyberJack-Pfad zu erzeugen.
- `--probe-morris-api` ergaenzen, wenn der Betreiber ausdruecklich will, dass
  das darunterliegende `noc-cyberjack-rfid`-Gate morris-Localhost-API und
  PC/SC-List-Readers prueft.
- Boolesche Praesenz lokaler Konfiguration ohne Werte erfassen.
- Lokale XNotar-/Register-Uebergabeschritte fuer Notariatssoftware vorbereiten.

## Verbotene Arbeit

- Passwoerter, PINs, private Schluessel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- Lokale XNP-Authentifizierung, Amtstaetigkeitskontext-Validierung,
  menschliches Review, Register-, Postfach- oder notarielle Kontrollen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdruecklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Geschuetzte Portale scrapen oder veroeffentlichte Nutzungslimits umgehen.

## Ablauf

1. Modus einordnen: Buerger-Preflight oder notarieller Workstation-Workflow.
2. Abgeschlossene `noc-cyberjack-rfid`-Karten-/SAK-Readiness bestaetigen oder den
   lokalen XNP-Reader-Prompt-Preflight fuer eine Evidence-Vorschau ausfuehren.
3. Fuer notarielle Workflows lokale XNP-Installation, lokalen Login, Nutzerrolle
   und Amtstaetigkeitskontext vor Handelsregister-Arbeit pruefen.
4. XNotar-/Registermodul oder Austauschordner-Route, lokalen Admin-Owner und
   Schnittstellenstatus des Herstellers pruefen.
5. Vor jeder lokalen oder externen Aktion eine lesbare Day1-Planvorschau erstellen.
6. Fuer regulierte Einreichungen, Registeranmeldungen, notarielle Aktionen oder
   Cloud-Aenderungen ausdrueckliche menschliche Freigabe einholen.
7. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, lokale
   Readiness, Reader-Prompt-Route, Quelle, Hash, Entscheidung, Ergebnis und
   Follow-up-Owner.
8. Fuer Day2 Drift, abgelaufene Zugriffe, fehlgeschlagene Checks,
   Versionsaenderungen und Rezertifizierungsaufgaben melden.

## Rueckgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Plan`, `Approval
Needed`, `Evidence` und `Day2 Follow-up`. Wenn etwas nicht fortgesetzt werden
kann, gehoert es unter `Approval Needed` mit Verweis auf
[docs/de/plugin-operations/account-and-approval-requests.md](../../../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../../../docs/en/plugin-operations/account-and-approval-requests.md).

## Quellplan

- [docs/de/plugin-plans/bnotk-xnp-notariatssoftware.md](../../../../docs/de/plugin-plans/bnotk-xnp-notariatssoftware.md)
- [docs/en/plugin-plans/bnotk-xnp-notariatssoftware.md](../../../../docs/en/plugin-plans/bnotk-xnp-notariatssoftware.md)
