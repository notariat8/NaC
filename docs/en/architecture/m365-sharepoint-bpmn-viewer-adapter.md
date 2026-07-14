# M365 SharePoint BPMN Viewer Adapter

## Purpose

The adapter provides a visible, read-only matter projection for the synthetic `notary_team_01` test environment. The surface is a packageable SharePoint Framework web part using **SPFx 1.23.2**, **Heft**, and `bpmn-js/lib/Viewer`. It supports `SharePointWebPart` and `TeamsTab` hosts.

The mode is **viewer-only**. It does not model or save BPMN, start workflows, or write SharePoint data. **No real matter data** is processed.

## Data and identity boundary

The dynamic data edge is fixed to:

```text
SPFx/Teams -> AadHttpClient -> NaC M365 BFF -> Microsoft Graph REST v1.0
```

The web part requests only delegated BFF scope `Matter.Read` for resource `api://funktion8.de/nac-bff`. The fixed MVP endpoint is `https://func-nac-bff-test-funktion8.azurewebsites.net`. The web part receives no Microsoft Graph permission, contains no `MSGraphClient`, and knows no site, list, or Graph paths.

The BFF validates the Entra token, tenant, audience, scope, workspace, matter, purpose, role, and active deputy grant server-side. Only the redacted synthetic DTO reaches the browser. BPMN XML remains a hash-bound package asset; matter, status, tasks, and deadline no longer come from a static package fixture.

## Package and build contract

Package source lives under `spfx/nac-bpmn-viewer`. `package-lock.json` is required source. The reproducible build uses:

```bash
npm ci
npm run build
```

`npm run build` runs the Heft production build and `heft package-solution --production`. The generated package is `sharepoint/solution/nac-bpmn-viewer.sppkg`.

`node_modules`, `lib`, `dist`, `temp`, and `sharepoint/solution` remain ignored and untracked. Recursive source scans do not enter these paths.

## Deployment boundary

The App Catalog deployment remains **DEFERRED** until the BFF activation succeeds. Only the consolidated activation gate may then allow upload and **site-scoped** installation for `notary_team_01`. `skipFeatureDeployment=false` enforces that site installation; tenant-wide deployment and installation into any other workspace remain blocked.

The package declares exactly one Web API request: `NaC M365 BFF` / `Matter.Read`. Additional delegated scopes, Graph permissions, production data, additional sites, and writes are forbidden.

## UI and DOM contract

- `data-nac-component="test-workspace"` identifies the test surface.
- `Synthetische Testdaten` visibly identifies the data class.
- `Keine Mandatsdaten` confirms the runtime boundary.
- A different `workspaceId` fails closed with `Workspace nicht freigegeben.`.
- Invalid, oversized, or divergent BFF responses are not rendered.

## Contracts and evidence

The authoritative artifacts are the [viewer adapter contract](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json), [SPFx package artifact](../../../deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json), and [runtime readiness](../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.runtime-readiness.json).

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
python3 -m unittest tests.test_m365_bpmn_viewer_runtime_readiness
python3 -m unittest tests.test_m365_sharepoint_bpmn_viewer_adapter
```
