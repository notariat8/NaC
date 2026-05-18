# Runbook: OCI Eventstream For Audit-Proof Evidence

Parity review 2026-05-18: no OCI-specific semantic change; kept in sync with the German typography update.

## Target State

This target variant implements the audit-proof event journal on OCI:

- ingest API, webhook,
- OCI Streaming as stream,
- OCI Object Storage with retention/immutability as WORM journal,
- OCI Vault for signatures and keys,
- evidence index via OCI OpenSearch or SQL.

## Reference Components

- `ingest-api`: OCI Container Instance or OKE service.
- `event-broker`: OCI Streaming stream plus consumer group.
- `journal-store`: OCI Object Storage bucket with retention rule.
- `anchor-job`: daily signature job via Functions or container job.
- `evidence-index`: OpenSearch/SQL for audit queries.

## Minimum Configuration

### OCI Streaming

- Partitions: 3 as starting value.
- Retention: 24-168 hours as transport layer.
- Consumer group: dedicated to normalizer.
- Private Endpoints/VCN controls: active.
- TLS: active.

### Object Storage Journal, WORM

- Bucket: `event-journal-immutable`.
- Retention rule: for example 3650 days.
- Deletion/mutation before deadline: prohibited.
- Governance process for retention changes documented.

### Signatures

- Vault key: `event-anchor-signing-key`.
- Algorithm: RSA-PSS or organizational standard.
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

1. GitHub events go to the ingest API.
2. The ingest API validates the HMAC signature.
3. Valid events are written to OCI Streaming.
4. The normalizer consumes the stream and creates hash-chained journal events.
5. Journal events are written append-only to Object Storage.
6. Evidence index is updated.
7. Daily anchor is signed and stored.

## Roles And Responsibilities

- `platform_operator`: Streaming, runtime, deployments.
- `storage_custodian`: Object Storage retention/immutability.
- `security_operator`: Vault, IAM, network security.
- `audit_reader`: read-only access to evidence index and anchors.
- `compliance_owner`: approval for retention or legal-hold topics.

## Operating Thresholds, Start

- Consumer lag warning: more than 60 seconds.
- DLQ rate warning: more than 0.5 percent.
- Ingest signature errors: more than 0.1 percent per hour.
- Anchor error: zero tolerated, P1 incident.

## Go-Live Checklist

- [ ] HMAC signature check active.
- [ ] OCI Streaming failure scenarios tested.
- [ ] Object Storage retention active.
- [ ] Vault signature test successful.
- [ ] Daily anchor report available.
- [ ] Restore test successful.
- [ ] Role recertification documented.
