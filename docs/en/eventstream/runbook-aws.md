# Runbook: AWS Eventstream For Audit-Proof Evidence

## Target State

This target variant implements the audit-proof event journal on AWS:

- ingest API, webhook,
- Kafka via MSK as stream,
- S3 Object Lock in compliance mode as journal,
- KMS for signatures,
- evidence index via OpenSearch or SQL.

## Reference Components

- `ingest-api`: ECS/Fargate or EKS service.
- `event-broker`: MSK cluster plus topics.
- `journal-store`: S3 bucket with Object Lock Compliance.
- `anchor-job`: daily signature job through Lambda or Batch.
- `evidence-index`: OpenSearch/SQL.

## Minimum Configuration

### MSK/Kafka

- Brokers: 3, multi-AZ.
- Replication factor: 3.
- `min.insync.replicas`: 2.
- Topic retention: 7-30 days.
- TLS in transit: active.
- Auth: IAM/SASL depending on architecture.

### S3 Journal, WORM

- Bucket: `event-journal-immutable`.
- Object Lock: `Compliance`.
- Default retention: for example 3650 days.
- Delete/overwrite before retention end: prohibited.
- Lifecycle only for allowed long-term storage classes.

### Signatures

- KMS key: `alias/event-anchor-signing`.
- Algorithm: `RSA_PSS_SHA_256` or organizational standard.
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

1. GitHub webhooks go to the ingest API.
2. The ingest API validates HMAC signatures.
3. Valid events are published to Kafka.
4. The normalizer consumes topics and creates hash-chained journal events.
5. Journal events are stored append-only in S3 Object Lock.
6. Evidence index is updated for queries.
7. Daily anchor closes the chain and signs the daily closure.

## Roles And Responsibilities

- `stream_operator`: MSK, ingest and consumer operation.
- `journal_custodian`: S3 Object Lock, retention, legal hold.
- `security_operator`: KMS, IAM, network access.
- `audit_reader`: read-only access to index and anchors.
- `compliance_owner`: approval for retention or legal-hold topics.

## Operating Thresholds, Start

- Consumer lag warning: more than 60 seconds.
- DLQ rate warning: more than 0.5 percent.
- HMAC signature errors: more than 0.1 percent per hour.
- Anchor error: zero tolerated, P1 incident.

## Emergency Procedures

1. Ingest disturbed: enable input queue, open incident.
2. Kafka disturbed: producer retry plus controlled buffering.
3. Journal write disturbed: stop stream, allow no event loss.
4. Anchor failed: manual signature run plus four-eyes approval.

## Go-Live Checklist

- [ ] HMAC signature check active.
- [ ] Redundant MSK configuration verified.
- [ ] S3 Object Lock Compliance active.
- [ ] KMS signature test successful.
- [ ] Daily anchor report available.
- [ ] Restore test successful.
- [ ] Role recertification documented.
