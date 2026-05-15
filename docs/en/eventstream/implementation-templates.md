# Eventstream Implementation: Reference Templates

## Goal

This document provides a directly usable implementation grid for audit-proof
eventstream operation with four binding platform variants:

- Template A: AWS, Kafka/MSK plus S3 Object Lock.
- Template B: Azure, Event Hubs plus Immutable Blob.
- Template C: GCP, Pub/Sub plus GCS Retention Lock.
- Template D: OCI, Streaming plus Object Storage retention.

Basis: [policies/revisionssicherheit-eventstream-policy.yaml](../../../policies/revisionssicherheit-eventstream-policy.yaml)

## Shared Target Model

### Mandatory Pipeline

1. GitHub events: organization audit, issues, projects, approvals.
2. Ingest gateway: webhook signature check, AuthN/AuthZ.
3. Event broker: durable stream.
4. Normalizer: uniform event envelope plus hash chain.
5. Immutable journal store: WORM.
6. Evidence index: search and audit reports.
7. Daily anchor: signature and chain closure.

### Event Envelope, Minimum

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

## Template A: Kafka Plus S3 Object Lock

### Building Blocks

- Ingest: protected webhook service, for example Python/FastAPI.
- Broker: Kafka with at least three brokers.
- Journal store: S3 bucket with Object Lock `Compliance`.
- Evidence index: OpenSearch/Elasticsearch or SQL index.
- Signature service: KMS-backed signature of the daily anchor.

### Minimum Parameters

- Kafka retention, operational: 30-90 days.
- WORM retention, legal: at least according to policy, for example 10 years.
- DLQ enabled: yes.
- TLS internal and external: mandatory.
- Idempotency: `event_id` plus dedup cache.
- Daily anchor time: 23:59 UTC.

### Roles

- `stream_operator`: operates ingest and broker.
- `journal_custodian`: owns WORM and retention.
- `security_operator`: keys, certificates, monitoring.
- `audit_reader`: read-only access to evidence index.
- `compliance_owner`: approval of retention and legal-hold changes.

## Template B: Azure Event Hubs Plus Immutable Blob

### Building Blocks

- Ingest: protected webhook service, App Service or container.
- Broker: Azure Event Hubs.
- Journal store: Azure Blob with immutable policy and optional legal hold.
- Evidence index: Azure Data Explorer, SQL or Search.
- Signature service: Key Vault sign operations for daily anchor.

### Minimum Parameters

- Event Hubs Capture optional for raw stream.
- Blob immutable retention: at least according to policy, for example 10 years.
- Legal-hold process: documented and tested.
- DLQ/poison handling: mandatory.
- Private networking/firewalling: active.
- Daily anchor time: 23:59 UTC.

### Roles

- `platform_operator`: operates Event Hubs and ingest.
- `storage_custodian`: manages immutable policies.
- `security_operator`: Key Vault and identities.
- `audit_reader`: read-only evidence access.
- `compliance_owner`: approvals for retention and legal hold.

## Operating Parameters, All Templates

- Monitoring:
  - ingest fail rate,
  - DLQ share,
  - event lag,
  - daily anchor success rate.
- Control cycles:
  - daily integrity check: hash chain consistent,
  - monthly rights and role recertification,
  - quarterly restore test.

## Minimum Security Controls

- Webhook signature check is mandatory.
- mTLS/TLS for all transport paths.
- Separated operating roles and segregation of duties.
- No deletion rights on journal objects before retention end.
- Key rotation and documented emergency processes.

## Introduction In Four Phases

1. **Pilot**
   - one vertical, one case repository, one organization project.
2. **Stabilization**
   - DLQ handling, observability, anchor reports.
3. **Rollout**
   - connect all relevant repositories and events.
4. **Audit readiness**
   - restore test, evidence package, procedure approval.

## Operating Decision Template

Each organization documents before go-live:

- chosen template, `A`, `B`, `C` or `D`,
- responsible roles by name,
- retention period,
- legal-hold procedure,
- audit read path and escalation path.

## Detailed Runbooks

- Azure target variant: [docs/en/eventstream/runbook-azure.md](runbook-azure.md)
- AWS target variant: [docs/en/eventstream/runbook-aws.md](runbook-aws.md)
- GCP target variant: [docs/en/eventstream/runbook-gcp.md](runbook-gcp.md)
- OCI target variant: [docs/en/eventstream/runbook-oci.md](runbook-oci.md)

## Platform Parity, Binding

- Changes to eventstream, audit-proof evidence or journal standards must be
  maintained synchronously for **AWS, Azure, GCP and OCI**.
- Maintaining only one platform is not allowed.
