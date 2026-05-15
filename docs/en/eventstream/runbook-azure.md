# Runbook: Azure Eventstream For Audit-Proof Evidence

## Target State

This target variant implements the audit-proof event journal on Azure:

- ingest API, webhook,
- Azure Event Hubs as stream,
- Azure Blob with immutable policy as journal,
- Key Vault for signatures,
- evidence index via Azure Data Explorer or SQL.

## Reference Components

- `ingest-api`: App Service or Container App.
- `event-broker`: Azure Event Hubs namespace plus event hub.
- `journal-store`: Storage account with immutable Blob container.
- `anchor-job`: daily signature job.
- `evidence-index`: ADX/SQL for audit queries.

## Minimum Configuration

### Event Hubs

- Partitions: 4 as starting value, adjust under load.
- Retention: 7 days; broker is transport layer only.
- Capture: optional, recommended for raw-data storage.
- Private Endpoint: active.
- TLS: active.

### Blob Journal, WORM

- Container: `event-journal`.
- Immutable policy: time-based retention, for example 3650 days.
- Delete/overwrite during retention: disabled.
- Legal-hold process: documented and tested.

### Signatures

- Key Vault key: `event-anchor-signing-key`.
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

1. GitHub sends the event to the ingest API.
2. The ingest API checks the webhook signature.
3. Valid events go to Event Hubs.
4. The normalizer reads from Event Hubs and creates hash-chained envelopes.
5. The envelope is stored append-only in immutable Blob storage.
6. Evidence index updates search fields for audits.
7. Daily anchor forms the chain closure and signs it.

## Roles And Responsibilities

- `platform_operator`: Event Hubs, ingest, deployments.
- `storage_custodian`: immutable storage, retention, legal hold.
- `security_operator`: Key Vault, secrets, certificates.
- `audit_reader`: read-only access to evidence index and anchor reports.
- `compliance_owner`: approval for retention or policy changes.

## Operating Thresholds, Start

- Event lag warning: more than 60 seconds.
- DLQ rate warning: more than 0.5 percent.
- Ingest signature errors: more than 0.1 percent per hour.
- Anchor error: zero tolerated, P1 incident.

## Emergency Procedures

1. Ingest disturbed: buffer events through retry queue, open incident.
2. Broker disturbed: switch ingest to emergency buffer.
3. Journal write disturbed: pause stream, discard no data.
4. Anchor failed: manual anchor run plus security approval.

## Go-Live Checklist

- [ ] Webhook signature check active.
- [ ] Event Hubs privately reachable.
- [ ] Immutable policy active and verified.
- [ ] Key Vault signature tested successfully.
- [ ] Daily anchor report available.
- [ ] Restore test successful.
- [ ] Role recertification documented.
