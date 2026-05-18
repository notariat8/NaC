---
name: nac-elster-eric
description: Nutzen, wenn ELSTER, ERiC, Mein Unternehmenskonto oder Steuer-Einreichungsnachweise vorbereitet werden, besonders vor regulierter Übermittlung oder Hersteller-Onboarding.
---

# ELSTER/ERiC

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Prepare ELSTER, ERiC, Mein Unternehmenskonto and tax-filing
readiness workflows as approval-bound dry runs. Do not store tax credentials or
perform regulated transmissions without reviewed connector code and approval.

## Einsatzgrenze

Laufzeitmodus: `local-tax-workflow-companion`.

Dieser Skill begleitet regulierte Steuer- und ELSTER-nahe Arbeit. Standard ist
Planvorschau, lokale Ausführung, ausdrückliche menschliche Freigabe und
Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange kein separat
geprüfter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Einreichungs-Readiness, Fristen und Evidence-Checklisten vorbereiten.
- Lokale Credential-Grenze und ERiC-Herstelleranforderungen erfassen.
- Vom Nutzer gelieferte Übertragungs- oder PDF-Evidence-Metadaten importieren.

## Verbotene Arbeit

- Passwörter, PINs, private Schlüssel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- Menschliches Review für regulierte Einreichungen, Register-, Postfach- oder
  notarielle Aktionen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdrücklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Geschützte Portale scrapen oder veröffentlichte Nutzungslimits umgehen.

## Ablauf

1. Vorgang, Akteursrolle, Reviewer-Rolle, Datenklasse und Zielsystem einordnen.
2. Day0-Voraussetzungen prüfen und fehlende Accounts oder Freigaben nennen.
3. Vor jeder lokalen oder externen Aktion eine lesbare Day1-Planvorschau erstellen.
4. Für regulierte Einreichungen, Registerabrufe, Postfachaktionen, notarielle
   Aktionen oder Cloud-Änderungen ausdrückliche menschliche Freigabe einholen.
5. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, Quelle, Hash,
   Entscheidung, Ergebnis und Follow-up-Owner.
6. Für Day2 Drift, abgelaufene Zugriffe, fehlgeschlagene Checks,
   Versionsänderungen und Rezertifizierungsaufgaben melden.

## Rückgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Plan`, `Approval
Needed`, `Evidence` und `Day2 Follow-up`. Wenn etwas nicht fortgesetzt werden
kann, gehört es unter `Approval Needed` mit Verweis auf
[docs/de/plugin-operations/account-and-approval-requests.md](../../../../docs/de/plugin-operations/account-and-approval-requests.md)
und
[docs/en/plugin-operations/account-and-approval-requests.md](../../../../docs/en/plugin-operations/account-and-approval-requests.md).

## Quellplan

- [docs/de/plugin-plans/elster-developer-plugin-integration.md](../../../../docs/de/plugin-plans/elster-developer-plugin-integration.md)
- [docs/en/plugin-plans/elster-developer-plugin-integration.md](../../../../docs/en/plugin-plans/elster-developer-plugin-integration.md)
