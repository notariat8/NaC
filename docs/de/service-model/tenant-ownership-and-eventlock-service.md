# Tenant Ownership und EventLock-as-a-Service

## Fragestellung

Wer sollte Cloud-Tenant-Owner für revisionssicheren Eventstream sein, und ist ein zentraler EventLock-Service durch Function8 sinnvoll?

## Kurzantwort

Ja, ein zentraler EventLock-as-a-Service ist für Non-IT-Organisationen sinnvoll, **wenn** pro Kunde eine dedizierte Subinstanz mit separaten Schlüsseln und isolierter Aufbewahrung betrieben wird.

## Empfohlenes Zielmodell

Empfehlung: `provider_managed_dedicated_subtenant`

- Function8 betreibt die Plattform zentral (Betrieb, Security-Baseline, SLA).
- Jeder Kunde erhält eine dedizierte Subinstanz (Namespace/Account) mit separatem Journal.
- Jeder Kunde erhält tenant-spezifische Schlüssel und immutable Retention.
- Kritische Änderungen (Retention, Legal Hold) nur mit Dual Control.

## Warum dieses Modell gut passt

- reduziert Adminaufwand für Notare/Kanzleien ohne tiefes Cloud-Know-how,
- hält Compliance-Forderungen durch Isolation und klare Verantwortungsmatrix,
- ermöglicht standardisierte, wiederholbare Auditprozesse über viele Kunden.

## Verantwortungsmatrix

### Function8 (Provider)

- Plattformbetrieb und Monitoring
- Security-Baseline und Incident-Prozess
- Wartung von Eventstream-Komponenten

### Kunde (Mandant/Unternehmen)

- Datenklassifikation
- Legal-Hold-Entscheidungen
- Freigabe von Audit-Zugriffen
- Rollen-/Rechtefreigaben für eigene Akten

## Technische Leitplanken je Kunden-Subinstanz

- dedizierter Stream-Namespace
- dedizierter immutable Journal-Bucket/Container
- dedizierter KMS/Key-Vault/Vault Key
- dedizierter Evidence Index Bereich
- tenant-spezifische Zugriffspolicies

## Betriebsprozess bei neuen Kunden

1. Kunden-Subinstanz provisionieren.
2. Tenant-Key erzeugen und zuweisen.
3. Immutable Retention aktivieren.
4. Rollenmodell aus Fork übernehmen.
5. Audit-Lesepfad und Reporting freischalten.
6. Abnahme mit Go-Live-Checkliste pro Cloud-Runbook.

## Verbindung zu Kunden-Forks

Jeder Kunden-Fork referenziert verbindlich:

- `policies/tenant-ownership-policy.yaml`
- `policies/access-control-policy.yaml`
- `policies/revisionssicherheit-eventstream-policy.yaml`

Damit bleiben Betriebsmodell, Rechte und Revisionssicherheit synchron.
