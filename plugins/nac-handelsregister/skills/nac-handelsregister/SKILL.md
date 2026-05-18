---
name: nac-handelsregister
description: Nutzen, wenn HRA-zuerst Online-Handelsregisteranmeldungen vorbereitet, Bürger-Vorprüfung und Notariatsmodus getrennt, notarielle Online-Verfahrensbereitschaft geprüft, eID-/App-Voraussetzungen dokumentiert oder nicht geheime Nachweismetadaten für Registerabläufe erstellt werden.
---

# Register

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Prepare HRA-first online Handelsregister application readiness,
notary online-procedure checks, eID/app prerequisites and metadata-only evidence.
For notary-side filings, require `nac-bnotk-xnp` first.

## Einsatzgrenze

Laufzeitmodus: `local-online-register-application-companion`.

Dieser Skill begleitet die Vorbereitung von Handelsregisteranmeldungen, nicht
den Abruf von Registerdaten. Für notarielle Einreichungsworkflows muss zuerst
`nac-bnotk-xnp` laufen; das lokale XNP-Authentifizierungs-Gate ist Voraussetzung
vor XNotar-/Register-Übergaben. Standard ist Planvorschau, lokale Ausführung,
ausdrückliche Antragsteller-/Notarfreigabe und Evidence-Metadaten.
Anmeldungen, Automatisierung notarieller Systeme oder Registerabrufe sind
verboten, solange kein separat geprüfter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Einordnen, ob der gewünschte Workflow HRA, HRB oder einen anderen
  Registerpfad betrifft.
- Bürger-Preflight von notariellem Workstation-Workflow trennen.
- HRA-first-Online-Registeranmeldungspakete und Listen fehlender Informationen
  vorbereiten.
- Notarielle Online-Verfahrens-Readiness prüfen: Bundesnotarkammer-App,
  eID-fähiger Ausweis, PIN, Videoverfahren, elektronische Signatur und
  Notartermin.
- Metadatenbasierte Evidence-Vorlagen für Freigaben, Paket-Readiness und
  Einreichungsergebnisse vorbereiten.

## Verbotene Arbeit

- Passwörter, PINs, private Schlüssel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- Antragstellerfreigabe, rechtliches Review, notarielles Review oder
  Signaturprüfungen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdrücklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Registerdaten abrufen, geschützte Portale scrapen, Einreichungen absenden
  oder notarielle Systeme automatisieren.

## Ablauf

1. Modus einordnen: Bürger-Preflight oder notarieller Workstation-Workflow.
2. Wenn notariell, `nac-bnotk-xnp`-Readiness vor Handelsregister-Paketarbeit
   verlangen.
3. Vorgang, Rechtsform, Registerpfad, Akteursrolle, Reviewer-Rolle und
   Datenklasse einordnen.
4. Wenn der Nutzer HRA nennt, aber GmbH/UG beschreibt, den wahrscheinlichen
   HRB-Mismatch markieren und Klärung verlangen.
5. Day0-Voraussetzungen prüfen: Antragstellerbefugnis, Notarroute,
   eID-/App-Readiness, erforderliche Dokumente und Freigabe-Owner.
6. Vor jeder notariellen oder externen Aktion eine lesbare Day1-Planvorschau
   erstellen.
7. Vor Notarterminen, Signaturen oder Einreichungen ausdrückliche Freigabe
   einholen.
8. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, Paketversion,
   Quelldokument-Hashes, Entscheidung, Ergebnis und Follow-up-Owner.
9. Für Day2 zurückgewiesene Einreichungen, fehlende Anlagen,
   Identitäts-/Signaturfehler und Rezertifizierungsaufgaben melden.

## Rückgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Application Package`,
`Approval Needed`, `Evidence` und `Day2 Follow-up`. Wenn etwas nicht fortgesetzt
werden kann, gehört es unter `Approval Needed` mit Verweis auf
[docs/de/plugin-operations/account-and-approval-requests.md](../../../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../../../docs/en/plugin-operations/account-and-approval-requests.md).

## Quellplan

- [docs/de/plugin-plans/handelsregister-online-anmeldung.md](../../../../docs/de/plugin-plans/handelsregister-online-anmeldung.md)
- [docs/en/plugin-plans/handelsregister-online-anmeldung.md](../../../../docs/en/plugin-plans/handelsregister-online-anmeldung.md)
