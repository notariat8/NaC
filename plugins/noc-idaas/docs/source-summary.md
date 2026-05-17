# IDaaS Quellenzusammenfassung

Quellrepository: `ofunk/IDaaS`

## Produktthese

IDaaS ist ein deutschlandzentriertes Konzept fuer Identitaetspruefung und
IAM-Projektion. Es nutzt die deutsche eID ueber AusweisApp als Vertrauensanker
und ueberfuehrt verifizierte Claims in zweckgebundene Assertions oder
Ziel-IAM-Projektionen.

## MVP-Umfang

- API fuer Verification-Start und Status
- AusweisApp-orientierte eID-Orchestrierung
- Einwilligungs- und Audit-Erfassung
- signierte Assertions fuer Kundenanwendungen
- mindestens ein produktionsnaher IAM-Connector
- Mapping-Regeln von Claim zu Attribut

## Zielsysteme

- Microsoft Entra ID
- Oracle IAM
- SCIM-kompatible Ziele

## NoC-Adaption

Das fruehere eigenstaendige SaaS-Konzept wird jetzt als NoC-Plugin behandelt.
Das Plugin fuehrt standardmaessig Readiness-Planung, Vertragspruefung und
metadatenbasierte Nachweisfuehrung aus. Produktive eID-Transaktionen oder
IAM-Schreibvorgaenge brauchen einen separat geprueften Connector und explizite
menschliche Freigabe.
