# Eventstream

Dieser Ordner bündelt revisionssichere Ereignisablage, EventLock-Architektur
und Cloud-Runbooks.

## Dokumente

- [revisionssicherheit.md](revisionssicherheit.md): fachliches Event-Journal- und WORM-Zielbild.
- [implementation-templates.md](implementation-templates.md): technische Umsetzungsvarianten für AWS,
  Azure, GCP und OCI.
- [runbook-aws.md](runbook-aws.md): AWS-Betriebsrunbook.
- [runbook-azure.md](runbook-azure.md): Azure-Betriebsrunbook.
- [runbook-gcp.md](runbook-gcp.md): GCP-Betriebsrunbook.
- [runbook-oci.md](runbook-oci.md): OCI-Betriebsrunbook.

## Pflegehinweis

Änderungen an einem Cloud-Runbook müssen die Paritätsregel in
[scripts/validate_cloud_runbook_parity.py](../../../scripts/validate_cloud_runbook_parity.py) erfüllen.
