# Runbook: OCI Eventstream fuer Revisionssicherheit

## Zielbild

Diese Zielvariante setzt das revisionssichere Event-Journal auf OCI um:

- Ingest API (Webhook)
- OCI Streaming (Stream)
- OCI Object Storage mit Retention/Immutability (WORM)
- OCI Vault (Signaturen/Schluessel)
- Evidence Index (OCI OpenSearch oder SQL)

## Referenzkomponenten

- `ingest-api`: OCI Container Instance/OKE Service
- `event-broker`: OCI Streaming Stream + Consumer Group
- `journal-store`: OCI Object Storage Bucket mit Retention Rule
- `anchor-job`: taeglicher Signaturjob (Functions/Container Job)
- `evidence-index`: OpenSearch/SQL fuer Auditabfragen

## Mindestkonfiguration

### OCI Streaming

- Partitions: 3 (Startwert)
- Retention: 24-168h (Transportebene)
- Consumer Group: dediziert fuer Normalizer
- Private Endpoints/VCN Controls: aktiv
- TLS: aktiv

### Object Storage Journal (WORM)

- Bucket: `event-journal-immutable`
- Retention Rule: z. B. 3650 Tage
- Loeschung/Mutation vor Frist: verboten
- Governance-Prozess fuer Retention-Aenderungen dokumentiert

### Signaturen

- Vault Key: `event-anchor-signing-key`
- Algorithmus: RSA-PSS (organisationaler Standard)
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

1. GitHub Events gehen an Ingest API.
2. Ingest API validiert HMAC-Signatur.
3. Gueltige Events werden in OCI Streaming geschrieben.
4. Normalizer konsumiert Stream und erstellt hash-verkettete Journal-Events.
5. Journal-Events werden append-only in Object Storage geschrieben.
6. Evidence Index wird aktualisiert.
7. Daily Anchor wird signiert und abgelegt.

## Rollen und Verantwortungen

- `platform_operator`: Streaming, Runtime, Deployments
- `storage_custodian`: Object Storage Retention/Immutability
- `security_operator`: Vault, IAM, Netzwerkabsicherung
- `audit_reader`: read-only auf Evidence Index + Anchors
- `compliance_owner`: Freigabe bei Retention-/Legal-Hold-Themen

## Betriebsgrenzwerte (Start)

- Consumer Lag Warnung: > 60 Sekunden
- DLQ-Rate Warnung: > 0.5 %
- Ingest Signaturfehler: > 0.1 % / Stunde
- Anchor-Fehler: 0 toleriert (P1 Incident)

## Go-Live-Checkliste

- [ ] HMAC-Signaturpruefung aktiv
- [ ] OCI Streaming Ausfallszenarien getestet
- [ ] Object Storage Retention aktiv
- [ ] Vault-Signaturtest erfolgreich
- [ ] Daily Anchor Report vorhanden
- [ ] Restore-Test erfolgreich
- [ ] Rollenrezertifizierung dokumentiert
