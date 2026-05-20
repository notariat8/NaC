---
name: nac-bea-portal
description: Nutzen, wenn beA-Postfach, Versand, Eingang, eEB, Client Security oder Export-/Importnachweise für eine Kanzlei geplant werden.
---

# beA-Postfach

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Plan beA mailbox, Client Security, eEB and evidence workflows
as local, approval-bound dry runs. Do not store secrets or mandate content and do
not perform external writes without a reviewed connector.

## Einsatzgrenze

Laufzeitmodus: `local-browser-companion`.

Dieser Skill ist ein lokaler Begleiter für regulierte beA-Arbeit. Standard ist
immer Planvorschau, lokale Ausführung, ausdrückliche menschliche Freigabe und
Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange kein separat
geprüfter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- beA-Readiness und Client-Security-Checklisten vorbereiten.
- Sende-, Empfangs- und eEB-Workflowpläne für menschliche Ausführung erstellen.
- Vom Nutzer ausdrücklich gelieferte Evidence-Metadaten importieren.

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

- [docs/de/plugin-plans/bea-portal-plugin-integration.md](../../../../docs/de/plugin-plans/bea-portal-plugin-integration.md)
- [docs/en/plugin-plans/bea-portal-plugin-integration.md](../../../../docs/en/plugin-plans/bea-portal-plugin-integration.md)
