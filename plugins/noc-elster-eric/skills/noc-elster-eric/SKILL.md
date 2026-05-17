---
name: noc-elster-eric
description: Nutzen, wenn ELSTER, ERiC, Mein Unternehmenskonto oder Steuer-Einreichungsnachweise vorbereitet werden, besonders vor regulierter Uebermittlung oder Hersteller-Onboarding.
---

# NoC ELSTER-ERiC-Begleiter

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Prepare ELSTER, ERiC, Mein Unternehmenskonto and tax-filing
readiness workflows as approval-bound dry runs. Do not store tax credentials or
perform regulated transmissions without reviewed connector code and approval.

## Einsatzgrenze

Laufzeitmodus: `local-tax-workflow-companion`.

Dieser Skill begleitet regulierte Steuer- und ELSTER-nahe Arbeit. Standard ist
Planvorschau, lokale Ausfuehrung, ausdrueckliche menschliche Freigabe und
Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange kein separat
gepruefter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Einreichungs-Readiness, Fristen und Evidence-Checklisten vorbereiten.
- Lokale Credential-Grenze und ERiC-Herstelleranforderungen erfassen.
- Vom Nutzer gelieferte Uebertragungs- oder PDF-Evidence-Metadaten importieren.

## Verbotene Arbeit

- Passwoerter, PINs, private Schluessel, Zertifikatsmaterial, Session-Cookies
  oder Einmalcodes in Git speichern.
- Menschliches Review fuer regulierte Einreichungen, Register-, Postfach- oder
  notarielle Aktionen umgehen.
- Mandats- oder Client-Inhalte an ein LLM senden, solange keine ausdruecklich
  freigegebene Datenverarbeitungsgrundlage besteht.
- Geschuetzte Portale scrapen oder veroeffentlichte Nutzungslimits umgehen.

## Ablauf

1. Vorgang, Akteursrolle, Reviewer-Rolle, Datenklasse und Zielsystem einordnen.
2. Day0-Voraussetzungen pruefen und fehlende Accounts oder Freigaben nennen.
3. Vor jeder lokalen oder externen Aktion eine lesbare Day1-Planvorschau erstellen.
4. Fuer regulierte Einreichungen, Registerabrufe, Postfachaktionen, notarielle
   Aktionen oder Cloud-Aenderungen ausdrueckliche menschliche Freigabe einholen.
5. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, Quelle, Hash,
   Entscheidung, Ergebnis und Follow-up-Owner.
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

- [docs/de/plugin-plans/elster-developer-plugin-integration.md](../../../../docs/de/plugin-plans/elster-developer-plugin-integration.md)
- [docs/en/plugin-plans/elster-developer-plugin-integration.md](../../../../docs/en/plugin-plans/elster-developer-plugin-integration.md)
