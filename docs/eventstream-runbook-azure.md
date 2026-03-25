# Runbook: Azure Eventstream fuer Revisionssicherheit

## Zielbild

Diese Zielvariante setzt das revisionssichere Event-Journal auf Azure um:

- Ingest API (Webhook)
- Azure Event Hubs (Stream)
- Azure Blob mit Immutable Policy (Journal)
- Key Vault (Signaturen)
- Evidence Index (Azure Data Explorer oder SQL)

## Referenzkomponenten

- `ingest-api`: App Service oder Container App
- `event-broker`: Azure Event Hubs Namespace + Event Hub
- `journal-store`: Storage Account mit immutable Blob Container
- `anchor-job`: taeglicher Signaturjob
- `evidence-index`: ADX/SQL fuer Auditabfragen

## Mindestkonfiguration

### Event Hubs

- Partitionen: 4 (Startwert, bei Last anpassen)
- Retention: 7 Tage (Broker nur Transportebene)
- Capture: optional, empfohlen fuer Rohdatenablage
- Private Endpoint: aktiv
- TLS: aktiv

### Blob Journal (WORM)

- Container: `event-journal`
- Immutable Policy: Time-based retention (z. B. 3650 Tage)
- Delete/Overwrite waehrend Retention: deaktiviert
- Legal Hold Prozess: dokumentiert und getestet

### Signaturen

- Key Vault Key: `event-anchor-signing-key`
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

1. GitHub sendet Event an Ingest API.
2. Ingest API prueft Webhook-Signatur.
3. Gueltige Events gehen in Event Hubs.
4. Normalizer liest aus Event Hubs und erzeugt hash-verkettete Envelopes.
5. Envelope wird append-only im immutable Blob gespeichert.
6. Evidence Index aktualisiert Suchfelder fuer Audits.
7. Daily Anchor bildet Kettenabschluss und signiert.

## Rollen und Verantwortungen

- `platform_operator`: Event Hubs, Ingest, Deployments
- `storage_custodian`: immutable Storage, Retention, Legal Hold
- `security_operator`: Key Vault, Secrets, Zertifikate
- `audit_reader`: read-only auf Evidence Index + Anchor Reports
- `compliance_owner`: Freigabe bei Retention-/Policy-Aenderungen

## Betriebsgrenzwerte (Start)

- Event-Lag Warnung: > 60 Sekunden
- DLQ-Rate Warnung: > 0.5 %
- Ingest Signaturfehler: > 0.1 % / Stunde
- Anchor-Fehler: 0 toleriert (P1 Incident)

## Notfallverfahren

1. Ingest stoert: Events puffern (Retry Queue), Incident eroefnen.
2. Broker stoert: Ingest auf Notpuffer schalten.
3. Journal-Write stoert: Stream anhalten, keine Daten verwerfen.
4. Anchor fehlgeschlagen: manueller Anchor-Run + Freigabe durch Security.

## Go-Live-Checkliste

- [ ] Webhook-Signaturpruefung aktiv
- [ ] Event Hubs private erreichbar
- [ ] Immutable Policy aktiv und verifiziert
- [ ] Key Vault Signatur erfolgreich getestet
- [ ] Daily Anchor Report vorhanden
- [ ] Restore-Test erfolgreich
- [ ] Rollenrezertifizierung dokumentiert
