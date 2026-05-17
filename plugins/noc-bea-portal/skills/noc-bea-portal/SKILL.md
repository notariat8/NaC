---
name: noc-bea-portal
description: Nutzen, wenn beA-Postfach, Versand, Eingang, eEB, Client Security oder Export-/Importnachweise fuer eine Kanzlei geplant werden.
---

# NoC beA-Portal-Begleiter

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Plan beA mailbox, Client Security, eEB and evidence workflows
as local, approval-bound dry runs. Do not store secrets or mandate content and do
not perform external writes without a reviewed connector.

## Einsatzgrenze

Laufzeitmodus: `local-browser-companion`.

Dieser Skill ist ein lokaler Begleiter fuer regulierte beA-Arbeit. Standard ist
immer Planvorschau, lokale Ausfuehrung, ausdrueckliche menschliche Freigabe und
Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange kein separat
gepruefter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- beA-Readiness und Client-Security-Checklisten vorbereiten.
- Sende-, Empfangs- und eEB-Workflowplaene fuer menschliche Ausfuehrung erstellen.
- Vom Nutzer ausdruecklich gelieferte Evidence-Metadaten importieren.

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

- [docs/de/plugin-plans/bea-portal-plugin-integration.md](../../../../docs/de/plugin-plans/bea-portal-plugin-integration.md)
- [docs/en/plugin-plans/bea-portal-plugin-integration.md](../../../../docs/en/plugin-plans/bea-portal-plugin-integration.md)
