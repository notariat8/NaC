---
name: nac-grundbuch-portal
description: Nutzen, wenn Grundbuchportalzugang, berechtigtes Interesse, landesspezifische Portalbereitschaft, Abrufnachweise oder notarielle Grundbuchabläufe geplant werden.
---

# Grundbuch

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Plan land-register portal access, legitimate-interest checks,
retrieval readiness and evidence shells as local, approval-bound workflows. Do
not automate protected portals or store uncontrolled document content.

## Einsatzgrenze

Laufzeitmodus: `local-portal-evidence-companion`.

Dieser Skill begleitet Grundbuchportal- und Nachweisarbeit. Standard ist
Planvorschau, lokale Ausführung, ausdrückliche menschliche Freigabe und
Evidence-Metadaten. Externe Schreib- oder Abrufaktionen sind verboten, solange
kein separat geprüfter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- Berechtigungs- und berechtigtes-Interesse-Checklisten vorbereiten.
- Abruf-Planvorschauen und Evidence-Huellen erstellen.
- Landesspezifische Portalunterschiede sowie Gebühren- und Kostenträger
  dokumentieren.

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

- [docs/de/plugin-plans/grundbuch-portal-plugin-integration.md](../../../../docs/de/plugin-plans/grundbuch-portal-plugin-integration.md)
- [docs/en/plugin-plans/grundbuch-portal-plugin-integration.md](../../../../docs/en/plugin-plans/grundbuch-portal-plugin-integration.md)
