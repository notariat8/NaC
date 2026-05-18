---
name: nac-regulated-core
description: Nutzen, wenn ein regulierter NaC-Arbeitsablauf Aufnahme, Regelprüfung, Planvorschau, menschliche Freigabe, Nachweiserfassung, Drift-Behandlung oder sicheren Rückfallpfad braucht.
---

# Regulierung

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Provide shared regulated-workflow guardrails for intake, policy
checks, plan previews, approval, evidence capture, drift handling and safe
fallbacks. Do not bypass review or store secrets and mandate content.

## Einsatzgrenze

Laufzeitmodus: `local-policy-companion`.

Dieser Skill ist die gemeinsame Schutzplanke für regulierte NaC-Workflows.
Standard ist Planvorschau, lokale Ausführung, ausdrückliche menschliche
Freigabe und Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange
kein separat geprüfter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Checklisten und Planvorschauen für regulierte Workflows erstellen.
- Day0-, Day1- und Day2-Kontrollen auf Plugin-Arbeit abbilden.
- Evidence-Vorlagen vorbereiten, die nur Metadaten enthalten.
- Fehlende Freigaben, Accounts oder lokale Voraussetzungen markieren.

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

- [docs/de/plugin-plans/domain-connector-runtime.md](../../../../docs/de/plugin-plans/domain-connector-runtime.md)
- [docs/en/plugin-plans/domain-connector-runtime.md](../../../../docs/en/plugin-plans/domain-connector-runtime.md)
