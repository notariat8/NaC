---
name: noc-oci-evidence
description: Nutzen, wenn OCI-Landing-Zone, Resource Manager, Vault, Eventstream, Audit oder Drift-Nachweise fuer regulierten NoC-Betrieb vorbereitet werden.
---

# NoC OCI-Nachweisbegleiter

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Prepare OCI landing-zone, Resource Manager, Vault, audit,
eventstream and drift evidence work as local plan previews. Do not apply cloud
changes without reviewed connector code and explicit human approval.

## Einsatzgrenze

Laufzeitmodus: `local-cloud-cli-companion`.

Dieser Skill begleitet OCI- und Nachweisarbeit in regulierten Betriebsumgebungen.
Standard ist Planvorschau, lokale Ausfuehrung, ausdrueckliche menschliche
Freigabe und Evidence-Metadaten. Externe Schreibaktionen sind verboten, solange
kein separat gepruefter Connector diese Aktion implementiert.

## Erlaubte Arbeit

- OCI-CLI-Readiness und Resource-Manager-Planreviews vorbereiten.
- Vault-, Compartment-, Audit- und Eventstream-Entscheidungen dokumentieren.
- Day2-Drift, Kosten- und Rotationsthemen nachhalten.

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

- [docs/de/plugin-plans/oci-infrastructure.md](../../../../docs/de/plugin-plans/oci-infrastructure.md)
- [docs/en/plugin-plans/oci-infrastructure.md](../../../../docs/en/plugin-plans/oci-infrastructure.md)
