# Eventstream

This folder groups audit-proof event storage, EventLock architecture and cloud
runbooks.

## Documents

- [revisionssicherheit.md](revisionssicherheit.md): business target model for event journals and WORM.
- [implementation-templates.md](implementation-templates.md): implementation options for AWS, Azure, GCP and
  OCI.
- [runbook-aws.md](runbook-aws.md): AWS operating runbook.
- [runbook-azure.md](runbook-azure.md): Azure operating runbook.
- [runbook-gcp.md](runbook-gcp.md): GCP operating runbook.
- [runbook-oci.md](runbook-oci.md): OCI operating runbook.

## Maintenance Note

Changes to one cloud runbook must satisfy the parity rule in
[scripts/validate_cloud_runbook_parity.py](../../../scripts/validate_cloud_runbook_parity.py).
