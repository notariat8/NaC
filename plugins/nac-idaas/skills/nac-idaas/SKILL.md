---
name: nac-idaas
description: Nutzen, wenn deutsche eID-Prüfungsbereitschaft, AusweisApp-orientierte Identitätsprüfung, Datenminimierung verifizierter Angaben, Einwilligungs-/Auditnachweise oder IAM-Projektionsbereitschaft für Entra ID, Oracle IAM oder SCIM-Ziele in regulierten NaC-Ablaufen geplant werden.
---

# eID-Prüfung

Deutsch ist die führende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Plan German eID readiness, AusweisApp-oriented checks,
verified-claim minimization, consent/audit evidence and IAM projection readiness
for Entra ID, Oracle IAM and SCIM targets. Do not execute production eID or IAM
writes without reviewed connector code and approval.

## Einsatzgrenze

Laufzeitmodus: `local-eid-iam-readiness-companion`.

Dieser Skill plant eID- und IAM-Projektionsworkflows. Er führt keine
produktiven eID-Transaktionen aus, speichert keine Ausweisdokumente, schreibt
nicht in IAM-Systeme und startet keine externen API-Aufrufe, solange kein
separat geprüfter Connector diese Aktion implementiert. Standard ist
Planvorschau, metadatenbasierte Evidence und menschliche Freigabe vor jeder
externen oder personenbezogenen Verarbeitung.

## Erlaubte Arbeit

- Verifikationszweck, Akteursrolle, Tenant, Zielanwendung, Datenklasse und
  Review-Owner einordnen.
- Minimale Claim-Sets definieren, zum Beispiel `fullName`, `dateOfBirth` oder
  `ageOverX`, `verificationLevel`, `verificationSource`, `verifiedAt` und
  `consentPurpose`.
- Deutsche eID- und AusweisApp-Readiness-Checklisten vorbereiten.
- IAM-Projektions-Readiness für Entra ID, Oracle IAM und SCIM-Ziele
  vorbereiten.
- API- und Event-Verträge in Trockenlauf-Form prüfen.
- Metadatenbasierte Evidence-Vorlagen für Consent, Verifikation, Projektion,
  Widerruf und Day2-Follow-up erstellen.

## Verbotene Arbeit

- eID-Rohdaten, vollständige Ausweisdokument-Dumps, Steuer-IDs, Secrets,
  private Schlüssel, Zertifikatsmaterial, Access Tokens, Einmalcodes oder
  Session-Cookies in Git speichern.
- Echte Identitätsdaten oder personenbezogene Client-Daten an ein LLM senden,
  solange keine ausdrücklich freigegebene Datenverarbeitungsgrundlage besteht.
- Produktive eID-Transaktionen starten, in IAM-Systeme schreiben oder
  geschützte Identity-APIs aufrufen, solange kein geprüfter Connector und
  keine menschliche Freigabe vorliegen.
- Verifizierte Claims über den dokumentierten Zweck hinaus wiederverwenden.

## Ablauf

1. Geschäftskontext, Zweck, Tenant, Zielsystem, Akteursrolle, Reviewer-Rolle
   und Datenklasse einordnen.
2. Minimales Claim-Set und erwartete Aufbewahrung für den konkreten Zweck
   definieren.
3. Readiness für AusweisApp, Client-App-Redirects, Webhook- oder Polling-Modus,
   Consent-Text, Audit-Speicher und Tenant-Isolation prüfen.
4. Wenn IAM-Projektion gewünscht ist, Zieltyp einordnen: `entra`, `oracle`
   oder `scim`.
5. Vor jeder externen oder personenbezogenen Verarbeitung eine Planvorschau
   erstellen.
6. Vor produktiven eID-, IAM- oder API-Aktionen ausdrückliche menschliche
   Freigabe einholen.
7. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, Zweck,
   Claim-Set-Version, Tenant, Zielsystem, Entscheidung, Ergebnis und
   Follow-up-Owner.
8. Für Day2 abgelaufene Assertions, Widerrufe, fehlgeschlagene Projektionen,
   Retention-Drift und Connector-Rezertifizierungsaufgaben melden.

## Rückgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Claim Set`,
`Projection`, `Approval Needed`, `Evidence` und `Day2 Follow-up`.

## Quellplan

- [docs/de/plugin-plans/idaas-plugin-integration.md](../../../../docs/de/plugin-plans/idaas-plugin-integration.md)
- [docs/en/plugin-plans/idaas-plugin-integration.md](../../../../docs/en/plugin-plans/idaas-plugin-integration.md)
