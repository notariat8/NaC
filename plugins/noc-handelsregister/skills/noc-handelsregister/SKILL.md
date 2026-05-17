---
name: noc-handelsregister
description: Nutzen, wenn HRA-zuerst Online-Handelsregisteranmeldungen vorbereitet, Buerger-Vorpruefung und Notariatsmodus getrennt, notarielle Online-Verfahrensbereitschaft geprueft, eID-/App-Voraussetzungen dokumentiert oder nicht geheime Nachweismetadaten fuer Registerablaeufe erstellt werden.
---

# NoC Handelsregister-Begleiter

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Prepare HRA-first online Handelsregister application readiness,
notary online-procedure checks, eID/app prerequisites and metadata-only evidence.
For notary-side filings, require `noc-bnotk-xnp` first.

## Einsatzgrenze

Laufzeitmodus: `local-online-register-application-companion`.

Dieser Skill begleitet die Vorbereitung von Handelsregisteranmeldungen, nicht
den Abruf von Registerdaten. Fuer notarielle Einreichungsworkflows muss zuerst
`noc-bnotk-xnp` laufen; das lokale XNP-Authentifizierungs-Gate ist Voraussetzung
vor XNotar-/Register-Uebergaben. Standard ist Planvorschau, lokale Ausfuehrung,
ausdrueckliche Antragsteller-/Notarfreigabe und Evidence-Metadaten.
Anmeldungen, Automatisierung notarieller Systeme oder Registerabrufe sind
verboten, solange kein separat gepruefter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Einordnen, ob der gewuenschte Workflow HRA, HRB oder einen anderen
  Registerpfad betrifft.
- Buerger-Preflight von notariellem Workstation-Workflow trennen.
- HRA-first-Online-Registeranmeldungspakete und Listen fehlender Informationen
  vorbereiten.
- Notarielle Online-Verfahrens-Readiness pruefen: Bundesnotarkammer-App,
  eID-faehiger Ausweis, PIN, Videoverfahren, elektronische Signatur und
  Notartermin.
- Metadatenbasierte Evidence-Vorlagen fuer Freigaben, Paket-Readiness und
  Einreichungsergebnisse vorbereiten.

## Verbotene Arbeit

- Passwoerter, PINs, private Schluessel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- Antragstellerfreigabe, rechtliches Review, notarielles Review oder
  Signaturpruefungen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdruecklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Registerdaten abrufen, geschuetzte Portale scrapen, Einreichungen absenden
  oder notarielle Systeme automatisieren.

## Ablauf

1. Modus einordnen: Buerger-Preflight oder notarieller Workstation-Workflow.
2. Wenn notariell, `noc-bnotk-xnp`-Readiness vor Handelsregister-Paketarbeit
   verlangen.
3. Vorgang, Rechtsform, Registerpfad, Akteursrolle, Reviewer-Rolle und
   Datenklasse einordnen.
4. Wenn der Nutzer HRA nennt, aber GmbH/UG beschreibt, den wahrscheinlichen
   HRB-Mismatch markieren und Klaerung verlangen.
5. Day0-Voraussetzungen pruefen: Antragstellerbefugnis, Notarroute,
   eID-/App-Readiness, erforderliche Dokumente und Freigabe-Owner.
6. Vor jeder notariellen oder externen Aktion eine lesbare Day1-Planvorschau
   erstellen.
7. Vor Notarterminen, Signaturen oder Einreichungen ausdrueckliche Freigabe
   einholen.
8. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, Paketversion,
   Quelldokument-Hashes, Entscheidung, Ergebnis und Follow-up-Owner.
9. Fuer Day2 zurueckgewiesene Einreichungen, fehlende Anlagen,
   Identitaets-/Signaturfehler und Rezertifizierungsaufgaben melden.

## Rueckgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Application Package`,
`Approval Needed`, `Evidence` und `Day2 Follow-up`. Wenn etwas nicht fortgesetzt
werden kann, gehoert es unter `Approval Needed` mit Verweis auf
[docs/de/plugin-operations/account-and-approval-requests.md](../../../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../../../docs/en/plugin-operations/account-and-approval-requests.md).

## Quellplan

- [docs/de/plugin-plans/handelsregister-online-anmeldung.md](../../../../docs/de/plugin-plans/handelsregister-online-anmeldung.md)
- [docs/en/plugin-plans/handelsregister-online-anmeldung.md](../../../../docs/en/plugin-plans/handelsregister-online-anmeldung.md)
