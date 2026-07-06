# Legacy-Archiv: OCI/ATP und OCI-On-Prem-Agent

Status: archiviert, nicht aktiver MVP-Pfad
Datum: 2026-07-06

## Entscheidung

Der aktive NaC-MVP nutzt Microsoft 365 Teams, Microsoft-365-Gruppen und die
verbundene SharePoint-Team-Site als Datenhaltung. Zugriff und Provisioning
laufen über Microsoft Graph REST oder MCP-Server, die intern Graph REST nutzen.

OCI/ATP, OCI Functions, OCI API Gateway, OCI DevOps, OCI Identity Domains,
OCI Vault und das OCI-gebundene On-Prem-Agent-Zielbild sind für den MVP
archiviert. Sie dürfen nicht mehr als Default für Runtime, Provisioning,
Quality Gate, Agent-Workflow oder neue Bedienkanten verwendet werden.

## Archivierte Pfade

Die folgenden Artefaktfamilien gelten ab dieser Entscheidung als Legacy:

- `deploy/functions/*`
- `deploy/database/atp-*.sql`
- `workflows/contracts/oci-tenant-identity.contract.json`
- `workflows/contracts/atp-runtime-*.contract.json`
- `workflows/contracts/agent-runtime-registry.contract.json`
- `workflows/contracts/agent-control-api.contract.json`
- `workflows/contracts/nac-onprem-agent-runtime.contract.json`
- `workflows/contracts/notarial-onprem-connector-boundaries.contract.json`
- `scripts/validate_oci_tenant_identity.py`
- `scripts/validate_atp_runtime_contracts.py`
- `scripts/validate_agent_runtime_registry.py`
- `scripts/validate_agent_control_api.py`
- `scripts/validate_nac_onprem_agent_runtime.py`
- `scripts/validate_notarial_onprem_connector_boundaries.py`
- `src/nac_web/oci_*.py`
- `src/nac_identity/oci_*.py`
- `tests/test_oci_*.py`
- ATP-/OCI-spezifische Runtime- und Onboarding-Store-Tests

Konkret archiviert sind hier:

- `deploy/database/atp-agent-runtime-registry-schema.sql`
- `deploy/database/atp-onboarding-request-store.sql`
- `deploy/database/atp-runtime-anchor-schema.sql`
- `scripts/validate_atp_runtime_contracts.py`
- `src/nac_identity/onboarding_requests.py` mit ATP-/OCI-Store-Adaptern
- `src/nac_identity/session_store.py` mit `AtpSessionStore`
- `src/nac_runtime/status_source.py` mit ATP-Zeilenleser
- `tests/test_atp_*.py`
- `tests/test_onboarding_requests.py` in der früheren ATP-Store-Fassung
- `tests/test_onboarding_store_schema.py` für das frühere ATP-Onboarding-/Session-Schema
- `tests/test_notarkammer_runtime_status_source.py` in der früheren ATP-Fassung
- `workflows/contracts/atp-runtime-*.contract.json`

Diese Dateien können in der Git-Historie wiederhergestellt werden. Solange
noch Code davon abhängt, bleiben sie im Repository, aber außerhalb des
aktiven MVP-Gates.

## Aktiver Ersatz

- Contract: `workflows/contracts/teams-sharepoint-graph-data-plane.contract.json`
- Schema: `deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json`
- Python-Paket: `src/nac_m365_graph`
- Provisioner: `scripts/provision_teams_sharepoint_graph.py`
- Validator: `scripts/validate_teams_sharepoint_graph_data_plane.py`
- CLI: `nac m365 teams-sharepoint ...`

## Rückholregel

Eine Rückkehr zu OCI/ATP braucht einen neuen Owner-Beschluss mit:

- konkretem Grund gegen M365/Graph,
- Kosten- und Betriebsbewertung,
- Datenschutz- und Revisionsbewertung,
- Migration aus SharePoint/Teams,
- eigenem Quality-Gate-Profil,
- expliziter Freigabe für alle Cloud-Ressourcen.
