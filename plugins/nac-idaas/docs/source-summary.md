# IDaaS Quellenzusammenfassung

Quellrepository: `ofunk/IDaaS`

## Produktthese

IDaaS ist ein deutschlandzentriertes Konzept für Identitätsprüfung und
IAM-Projektion. Es nutzt die deutsche eID über AusweisApp als Vertrauensanker
und überführt verifizierte Claims in zweckgebundene Assertions oder
Ziel-IAM-Projektionen.

## MVP-Umfang

- API für Verification-Start und Status
- AusweisApp-orientierte eID-Orchestrierung
- Einwilligungs- und Audit-Erfassung
- signierte Assertions für Kundenanwendungen
- mindestens ein produktionsnaher IAM-Connector
- Mapping-Regeln von Claim zu Attribut

## Zielsysteme

- Microsoft Entra ID
- Oracle IAM
- SCIM-kompatible Ziele

## NaC-Adaption

Das fruehere eigenständige SaaS-Konzept wird jetzt als NaC-Plugin behandelt.
Das Plugin führt standardmäßig Readiness-Planung, Vertragsprüfung und
metadatenbasierte Nachweisführung aus. Produktive eID-Transaktionen oder
IAM-Schreibvorgänge brauchen einen separat geprüften Connector und explizite
menschliche Freigabe.
