# Runbook: AWS Eventstream fuer Revisionssicherheit

## Zielbild

Diese Zielvariante setzt das revisionssichere Event-Journal auf AWS um:

- Ingest API (Webhook)
- Kafka (MSK) als Stream
- S3 Object Lock (Compliance Mode) als Journal
- KMS fuer Signaturen
- Evidence Index (OpenSearch oder SQL)

## Referenzkomponenten

- `ingest-api`: ECS/Fargate oder EKS Service
- `event-broker`: MSK Cluster + Topics
- `journal-store`: S3 Bucket mit Object Lock Compliance
- `anchor-job`: taeglicher Signaturjob (Lambda/Batch)
- `evidence-index`: OpenSearch/SQL

## Mindestkonfiguration

### MSK/Kafka

- Broker: 3 (Multi-AZ)
- Replication Factor: 3
- min.insync.replicas: 2
- Topic Retention: 7-30 Tage
- TLS in transit: aktiv
- Auth: IAM/SASL je Architektur

### S3 Journal (WORM)

- Bucket: `event-journal-immutable`
- Object Lock: `Compliance`
- Default Retention: z. B. 3650 Tage
- Delete/Overwrite vor Frist: verboten
- Lifecycle nur fuer zulaessige Langzeitklassen

### Signaturen

- KMS Key: `alias/event-anchor-signing`
- Algorithmus: RSA_PSS_SHA_256 (oder organisationaler Standard)
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

1. GitHub Webhooks gehen an Ingest API.
2. Ingest API validiert HMAC-Signaturen.
3. Validierte Events werden nach Kafka publiziert.
4. Normalizer konsumiert Topics und erzeugt hash-verkettete Journal-Events.
5. Journal-Events werden append-only in S3 Object Lock gespeichert.
6. Evidence Index wird fuer Abfragen aktualisiert.
7. Daily Anchor schliesst Kette und signiert den Tagesabschluss.

## Rollen und Verantwortungen

- `stream_operator`: MSK, Ingest, Consumer Betrieb
- `journal_custodian`: S3 Object Lock, Retention, Legal Hold
- `security_operator`: KMS, IAM, Netzwerkzugriffe
- `audit_reader`: read-only auf Index + Anchors
- `compliance_owner`: Freigabe bei Aufbewahrungs-/Legal-Hold-Themen

## Betriebsgrenzwerte (Start)

- Consumer Lag Warnung: > 60 Sekunden
- DLQ-Rate Warnung: > 0.5 %
- HMAC-Signaturfehler: > 0.1 % / Stunde
- Anchor-Fehler: 0 toleriert (P1 Incident)

## Notfallverfahren

1. Ingest stoert: Eingangsqueue aktivieren, Incident eroefnen.
2. Kafka stoert: Producer-Retry + kontrollierte Pufferung.
3. Journal-Write stoert: Stream stoppen, kein Eventverlust zulassen.
4. Anchor fehlgeschlagen: manueller Signaturlauf + Vier-Augen-Freigabe.

## Go-Live-Checkliste

- [ ] HMAC-Signaturpruefung aktiv
- [ ] MSK redundante Konfiguration verifiziert
- [ ] S3 Object Lock Compliance aktiv
- [ ] KMS-Signaturtest erfolgreich
- [ ] Daily Anchor Report vorhanden
- [ ] Restore-Test erfolgreich
- [ ] Rollenrezertifizierung dokumentiert
