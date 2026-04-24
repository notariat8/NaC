# Runbook: GCP Eventstream fuer Revisionssicherheit

## Zielbild

Diese Zielvariante setzt das revisionssichere Event-Journal auf GCP um:

- Ingest API (Webhook)
- Pub/Sub (Stream)
- Cloud Storage mit Retention Lock (WORM)
- Cloud KMS (Signaturen)
- Evidence Index (BigQuery oder Search)

## Referenzkomponenten

- `ingest-api`: Cloud Run oder GKE Service
- `event-broker`: Pub/Sub Topic + Subscription
- `journal-store`: GCS Bucket mit Retention Policy + Bucket Lock
- `anchor-job`: taeglicher Signaturjob (Cloud Run Job/Cloud Functions)
- `evidence-index`: BigQuery (oder vergleichbarer Suchindex)

## Mindestkonfiguration

### Pub/Sub

- Topic: `event-journal-ingest`
- Subscription: Pull (ack deadline passend zur Verarbeitung)
- DLQ: aktiv (dead-letter topic)
- Message Retention: 7 Tage (Transportebene)
- CMEK optional, empfohlen

### GCS Journal (WORM)

- Bucket: `event-journal-immutable`
- Retention Policy: z. B. 3650 Tage
- Bucket Lock: aktiv (Retention nicht reduzierbar)
- Delete/Rewrite vor Retention-Ende: verboten

### Signaturen

- KMS Key: `event-anchor-signing-key`
- Algorithmus: RSA-PSS (z. B. PS256)
- Anchor-Frequenz: taeglich 23:59 UTC

## Event-Schema (Mussfelder)

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

## Event-Fluss

1. GitHub Events treffen in der Ingest API ein.
2. Ingest API prueft HMAC-Signatur.
3. Gueltige Events werden in Pub/Sub publiziert.
4. Normalizer liest aus Subscription und bildet hash-verkettete Envelopes.
5. Envelopes werden append-only in GCS (Retention Lock) geschrieben.
6. Evidence Index wird fuer Audit-Abfragen aktualisiert.
7. Daily Anchor schliesst den Tag kryptografisch ab.

## Rollen und Verantwortungen

- `platform_operator`: Cloud Run/GKE, Pub/Sub, Deployments
- `storage_custodian`: GCS Retention/Bucket Lock
- `security_operator`: KMS, IAM, Secret Management
- `audit_reader`: read-only auf Evidence Index + Anchor Reports
- `compliance_owner`: Freigaben fuer Retention/Legal-Hold-Prozesse

## Betriebsgrenzwerte (Start)

- Subscriber Lag Warnung: > 60 Sekunden
- DLQ-Rate Warnung: > 0.5 %
- Signaturprueffehler Ingest: > 0.1 % / Stunde
- Anchor-Fehler: 0 toleriert (P1 Incident)

## Go-Live-Checkliste

- [ ] HMAC-Signaturpruefung aktiv
- [ ] Pub/Sub DLQ getestet
- [ ] GCS Retention + Bucket Lock aktiv
- [ ] KMS-Signaturtest erfolgreich
- [ ] Daily Anchor Report vorhanden
- [ ] Restore-Test erfolgreich
- [ ] Rollenrezertifizierung dokumentiert
