# Eventstream

Dieser Ordner buendelt revisionssichere Ereignisablage, EventLock-Architektur
und Cloud-Runbooks.

## Dokumente

- `revisionssicherheit.md`: fachliches Event-Journal- und WORM-Zielbild.
- `implementation-templates.md`: technische Umsetzungsvarianten fuer AWS,
  Azure, GCP und OCI.
- `runbook-aws.md`: AWS-Betriebsrunbook.
- `runbook-azure.md`: Azure-Betriebsrunbook.
- `runbook-gcp.md`: GCP-Betriebsrunbook.
- `runbook-oci.md`: OCI-Betriebsrunbook.

## Pflegehinweis

Aenderungen an einem Cloud-Runbook muessen die Paritaetsregel in
`scripts/validate_cloud_runbook_parity.py` erfuellen.
