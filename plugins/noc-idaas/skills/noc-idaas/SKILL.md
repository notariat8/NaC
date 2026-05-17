---
name: noc-idaas
description: Nutzen, wenn deutsche eID-Pruefungsbereitschaft, AusweisApp-orientierte Identitaetspruefung, Datenminimierung verifizierter Angaben, Einwilligungs-/Auditnachweise oder IAM-Projektionsbereitschaft fuer Entra ID, Oracle IAM oder SCIM-Ziele in regulierten NoC-Ablaufen geplant werden.
---

# NoC eID- und IAM-Begleiter

Deutsch ist die fuehrende fachliche Skill-Sprache. Technische Namen, Ordner,
Commands und IDs bleiben englisch/ASCII.

## Englische Kurzfassung

English summary: Plan German eID readiness, AusweisApp-oriented checks,
verified-claim minimization, consent/audit evidence and IAM projection readiness
for Entra ID, Oracle IAM and SCIM targets. Do not execute production eID or IAM
writes without reviewed connector code and approval.

## Einsatzgrenze

Laufzeitmodus: `local-eid-iam-readiness-companion`.

Dieser Skill plant eID- und IAM-Projektionsworkflows. Er fuehrt keine
produktiven eID-Transaktionen aus, speichert keine Ausweisdokumente, schreibt
nicht in IAM-Systeme und startet keine externen API-Aufrufe, solange kein
separat gepruefter Connector diese Aktion implementiert. Standard ist
Planvorschau, metadatenbasierte Evidence und menschliche Freigabe vor jeder
externen oder personenbezogenen Verarbeitung.

## Erlaubte Arbeit

- Verifikationszweck, Akteursrolle, Tenant, Zielanwendung, Datenklasse und
  Review-Owner einordnen.
- Minimale Claim-Sets definieren, zum Beispiel `fullName`, `dateOfBirth` oder
  `ageOverX`, `verificationLevel`, `verificationSource`, `verifiedAt` und
  `consentPurpose`.
- Deutsche eID- und AusweisApp-Readiness-Checklisten vorbereiten.
- IAM-Projektions-Readiness fuer Entra ID, Oracle IAM und SCIM-Ziele
  vorbereiten.
- API- und Event-Vertraege in Trockenlauf-Form pruefen.
- Metadatenbasierte Evidence-Vorlagen fuer Consent, Verifikation, Projektion,
  Widerruf und Day2-Follow-up erstellen.

## Verbotene Arbeit

- eID-Rohdaten, vollstaendige Ausweisdokument-Dumps, Steuer-IDs, Secrets,
  private Schluessel, Zertifikatsmaterial, Access Tokens, Einmalcodes oder
  Session-Cookies in Git speichern.
- Echte Identitaetsdaten oder personenbezogene Client-Daten an ein LLM senden,
  solange keine ausdruecklich freigegebene Datenverarbeitungsgrundlage besteht.
- Produktive eID-Transaktionen starten, in IAM-Systeme schreiben oder
  geschuetzte Identity-APIs aufrufen, solange kein gepruefter Connector und
  keine menschliche Freigabe vorliegen.
- Verifizierte Claims ueber den dokumentierten Zweck hinaus wiederverwenden.

## Ablauf

1. Geschaeftskontext, Zweck, Tenant, Zielsystem, Akteursrolle, Reviewer-Rolle
   und Datenklasse einordnen.
2. Minimales Claim-Set und erwartete Aufbewahrung fuer den konkreten Zweck
   definieren.
3. Readiness fuer AusweisApp, Client-App-Redirects, Webhook- oder Polling-Modus,
   Consent-Text, Audit-Speicher und Tenant-Isolation pruefen.
4. Wenn IAM-Projektion gewuenscht ist, Zieltyp einordnen: `entra`, `oracle`
   oder `scim`.
5. Vor jeder externen oder personenbezogenen Verarbeitung eine Planvorschau
   erstellen.
6. Vor produktiven eID-, IAM- oder API-Aktionen ausdrueckliche menschliche
   Freigabe einholen.
7. Nur Evidence-Metadaten erfassen: Zeitstempel, Akteursrolle, Zweck,
   Claim-Set-Version, Tenant, Zielsystem, Entscheidung, Ergebnis und
   Follow-up-Owner.
8. Fuer Day2 abgelaufene Assertions, Widerrufe, fehlgeschlagene Projektionen,
   Retention-Drift und Connector-Rezertifizierungsaufgaben melden.

## Rueckgabeformat

Nutze knappe Abschnitte mit stabilen Labels: `Readiness`, `Claim Set`,
`Projection`, `Approval Needed`, `Evidence` und `Day2 Follow-up`.

## Quellplan

- [docs/de/plugin-plans/idaas-plugin-integration.md](../../../../docs/de/plugin-plans/idaas-plugin-integration.md)
- [docs/en/plugin-plans/idaas-plugin-integration.md](../../../../docs/en/plugin-plans/idaas-plugin-integration.md)
