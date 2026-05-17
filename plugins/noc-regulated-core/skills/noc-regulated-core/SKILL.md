---
name: noc-regulated-core
description: Nutzen, wenn ein regulierter NoC-Arbeitsablauf Aufnahme, Regelpruefung, Planvorschau, menschliche Freigabe, Nachweiserfassung, Drift-Behandlung oder sicheren Rueckfallpfad braucht.
---

# NoC Schutzplanken fuer Regulierung

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Provide shared regulated-workflow guardrails for intake, policy
checks, plan previews, approval, evidence capture, drift handling and safe
fallbacks. Do not bypass review or store secrets and mandate content.

## Einsatzgrenze

Laufzeitmodus: `local-policy-companion`.

Dieser Skill ist die gemeinsame Schutzplanke fuer regulierte NoC-Workflows.
Standard ist Planvorschau, lokale Ausfuehrung, ausdrueckliche menschliche
Freigabe und Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange
kein separat gepruefter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Checklisten und Planvorschauen fuer regulierte Workflows erstellen.
- Day0-, Day1- und Day2-Kontrollen auf Plugin-Arbeit abbilden.
- Evidence-Vorlagen vorbereiten, die nur Metadaten enthalten.
- Fehlende Freigaben, Accounts oder lokale Voraussetzungen markieren.

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

- [docs/de/plugin-plans/domain-connector-runtime.md](../../../../docs/de/plugin-plans/domain-connector-runtime.md)
- [docs/en/plugin-plans/domain-connector-runtime.md](../../../../docs/en/plugin-plans/domain-connector-runtime.md)
