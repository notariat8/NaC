# Eventstream-Implementierung: Referenz-Templates

## Ziel

Dieses Dokument liefert ein direkt nutzbares Umsetzungsraster fuer revisionssicheren Eventstream-Betrieb mit vier verbindlichen Plattformvarianten:

- Template A: AWS (Kafka/MSK + S3 Object Lock)
- Template B: Azure (Event Hubs + Immutable Blob)
- Template C: GCP (Pub/Sub + GCS Retention Lock)
- Template D: OCI (Streaming + Object Storage Retention)

Grundlage: `policies/revisionssicherheit-eventstream-policy.yaml`

## Gemeinsames Sollmodell

### Pflichtpipeline

1. GitHub Events (Org Audit, Issues, Projects, Approvals)
2. Ingest Gateway (Webhook Signaturpruefung, AuthN/AuthZ)
3. Event Broker (durable stream)
4. Normalizer (einheitliches Event-Envelope + Hash-Chain)
5. Immutable Journal Store (WORM)
6. Evidence Index (Suche/Pruefberichte)
7. Daily Anchor (Signatur + Kettenabschluss)

### Event Envelope (Minimum)

- `event_id`
- `event_time_utc`
- `source_system`
- `org_repo`
- `object_type` / `object_id`
- `actor_login`
- `action`
- `payload_hash`
- `prev_hash`
- `event_hash`
- `signature_ref`

## Template A: Kafka + S3 Object Lock

### Bausteine

- Ingest: abgesicherter Webhook-Service (z. B. Python/FastAPI)
- Broker: Kafka (mind. 3 Broker)
- Journal Store: S3 Bucket mit Object Lock `Compliance`
- Evidence Index: OpenSearch/Elasticsearch oder SQL-Index
- Signaturdienst: KMS-gestuetzte Signatur des Daily Anchors

### Mindestparameter

- Kafka Retention (operativ): 30-90 Tage
- WORM Retention (rechtlich): mindestens gem. Policy, z. B. 10 Jahre
- DLQ aktiviert: ja
- TLS intern/extern: verpflichtend
- Idempotenz: `event_id` + dedup cache
- Daily Anchor Zeit: 23:59 UTC

### Rollen

- `stream_operator`: betreibt Ingest/Broker
- `journal_custodian`: verantwortet WORM und Aufbewahrung
- `security_operator`: Schluessel, Zertifikate, Monitoring
- `audit_reader`: read-only Zugriff auf Evidence Index
- `compliance_owner`: Freigabe von Retention- und Legal-Hold-Aenderungen

## Template B: Azure Event Hubs + Immutable Blob

### Bausteine

- Ingest: abgesicherter Webhook-Service (App Service/Container)
- Broker: Azure Event Hubs
- Journal Store: Azure Blob mit Immutable Policy + optional Legal Hold
- Evidence Index: Azure Data Explorer / SQL / Search
- Signaturdienst: Key Vault Sign Operations fuer Daily Anchor

### Mindestparameter

- Event Hubs Capture optional fuer Rohstrom
- Blob Immutable Retention: mindestens gem. Policy, z. B. 10 Jahre
- Legal Hold Prozess: dokumentiert und getestet
- DLQ/Poison-Handling: verpflichtend
- Private Networking/Firewalling: aktiv
- Daily Anchor Zeit: 23:59 UTC

### Rollen

- `platform_operator`: betreibt Event Hubs und Ingest
- `storage_custodian`: verwaltet Immutable Policies
- `security_operator`: Key Vault und Identitaeten
- `audit_reader`: read-only Evidence-Zugriff
- `compliance_owner`: Freigaben fuer Aufbewahrung/Legal Hold

## Betriebsparameter (alle Templates)

- Monitoring:
  - Ingest-Fail-Rate
  - DLQ-Anteil
  - Event-Lag
  - Daily-Anchor Erfolgsquote
- Kontrollzyklen:
  - taegliche Integritaetspruefung (Hash-Chain konsistent)
  - monatliche Rechte-/Rollenrezertifizierung
  - quartalsweiser Restore-Test

## Mindest-Sicherheitskontrollen

- Webhook-Signaturpruefung zwingend
- mTLS/TLS fuer alle Transportwege
- getrennte Betriebsrollen (SoD)
- keine Loeschrechte auf Journalobjekte vor Retention-Ende
- Schluesselrotation und dokumentierte Notfallprozesse

## Einfuehrung in 4 Phasen

1. **Pilot**
   - ein Vertical, ein Case-Repo, ein Org-Project
2. **Stabilisierung**
   - DLQ-Handling, Observability, Anchor-Reports
3. **Rollout**
   - alle relevanten Repos und Events anbinden
4. **Audit Readiness**
   - Restore-Test, Nachweispaket, Verfahrensfreigabe

## Betriebsentscheidungsvorlage

Jedes Unternehmen dokumentiert vor Go-Live:

- gewaehltes Template (`A` oder `B`)
- verantwortliche Rollen (namentlich)
- Retention-Frist
- Legal-Hold-Verfahren
- Audit-Lesepfad und Eskalationsweg

## Detaillierte Runbooks

- Azure-Zielvariante: `docs/eventstream-runbook-azure.md`
- AWS-Zielvariante: `docs/eventstream-runbook-aws.md`
- GCP-Zielvariante: `docs/eventstream-runbook-gcp.md`
- OCI-Zielvariante: `docs/eventstream-runbook-oci.md`

## Plattform-Paritaet (verbindlich)

- Aenderungen an Eventstream-, Revisionssicherheits- oder Journal-Standards muessen fuer **AWS, Azure, GCP, OCI** synchron gepflegt werden.
- Einseitige Pflege nur einer Plattform ist nicht zulaessig.
