# Runbook: GCP Eventstream For Audit-Proof Evidence

## Target State

This target variant implements the audit-proof event journal on GCP:

- ingest API, webhook,
- Pub/Sub as stream,
- Cloud Storage with Retention Lock as WORM journal,
- Cloud KMS for signatures,
- evidence index via BigQuery or search.

## Reference Components

- `ingest-api`: Cloud Run or GKE service.
- `event-broker`: Pub/Sub topic plus subscription.
- `journal-store`: GCS bucket with retention policy and bucket lock.
- `anchor-job`: daily signature job via Cloud Run Job or Cloud Functions.
- `evidence-index`: BigQuery or comparable search index.

## Minimum Configuration

### Pub/Sub

- Topic: `event-journal-ingest`.
- Subscription: pull, with ack deadline matching processing.
- DLQ: active, dead-letter topic.
- Message retention: 7 days as transport layer.
- CMEK optional, recommended.

### GCS Journal, WORM

- Bucket: `event-journal-immutable`.
- Retention policy: for example 3650 days.
- Bucket Lock: active, retention cannot be reduced.
- Delete/rewrite before retention end: prohibited.

### Signatures

- KMS key: `event-anchor-signing-key`.
- Algorithm: RSA-PSS, for example PS256.
- Anchor frequency: daily at 23:59 UTC.

## Event Schema, Required Fields

- `event_id`
- `event_time_utc`
- `source`
- `org`
- `repo`
- `object_type`
- `object_id`
- `actor_login`
- `action_type`
- `payload_hash`
- `previous_event_hash`
- `event_hash`
- `signature_ref`

## Event Flow

1. GitHub events arrive at the ingest API.
2. The ingest API checks the HMAC signature.
3. Valid events are published to Pub/Sub.
4. The normalizer reads from the subscription and creates hash-chained
   envelopes.
5. Envelopes are written append-only to GCS with Retention Lock.
6. Evidence index is updated for audit queries.
7. Daily anchor closes the day cryptographically.

## Roles And Responsibilities

- `platform_operator`: Cloud Run/GKE, Pub/Sub, deployments.
- `storage_custodian`: GCS retention and bucket lock.
- `security_operator`: KMS, IAM, secret management.
- `audit_reader`: read-only access to evidence index and anchor reports.
- `compliance_owner`: approvals for retention or legal-hold processes.

## Operating Thresholds, Start

- Subscriber lag warning: more than 60 seconds.
- DLQ rate warning: more than 0.5 percent.
- Ingest signature-check errors: more than 0.1 percent per hour.
- Anchor error: zero tolerated, P1 incident.

## Go-Live Checklist

- [ ] HMAC signature check active.
- [ ] Pub/Sub DLQ tested.
- [ ] GCS retention and bucket lock active.
- [ ] KMS signature test successful.
- [ ] Daily anchor report available.
- [ ] Restore test successful.
- [ ] Role recertification documented.
