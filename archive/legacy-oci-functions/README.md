# Legacy-Archiv: OCI Tenant Identity und OCI Functions Runtime

Status: archiviert, nicht aktiver MVP-Pfad
Datum: 2026-07-06

## Entscheidung

Der aktive MVP nutzt Microsoft 365 Teams, Microsoft-365-Gruppen, SharePoint
Team Sites und Microsoft Graph REST/MCP. Die OCI Functions Runtime, der
OCI Public Runtime Wrapper und die OCI Tenant Identity Apply-Artefakte sind
damit nicht mehr Teil des aktiven Runtime-, Test- oder Provisioning-Pfads.

## Archivierte Pfade

- `deploy/functions/nac-app/*`
- `deploy/functions/nac-public-app/*`
- `src/nac_identity/oci_tenant.py`
- `src/nac_web/oci_functions.py`
- `src/nac_web/oci_minimal_public.py`
- `src/nac_web/oci_public_functions.py`
- `scripts/validate_oci_tenant_identity.py`
- `tests/test_oci_functions_adapter.py`
- `tests/test_oci_role_lookup.py`
- `tests/test_oci_tenant_identity.py`
- `workflows/contracts/oci-tenant-identity.contract.json`

## Aktiver Ersatz

- Tenant-Readiness: `src/nac_identity/tenant_readiness.py`
- Customer-Tenant-Plan: `src/nac_identity/customer_onboarding.py`
- Lokale Web-/M365-Planansicht: `src/nac_web/server.py`
- M365 Datenebene: `workflows/contracts/teams-sharepoint-graph-data-plane.contract.json`
- M365 Validator: `scripts/validate_teams_sharepoint_graph_data_plane.py`

## Rückholregel

Eine Reaktivierung dieser OCI-Schicht braucht einen neuen Owner-Beschluss.
Sie darf nicht implizit über Imports, Tests, Quality-Gates oder Deploy-Builds
in den aktiven MVP zurückkehren.
