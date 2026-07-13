# M365 SharePoint BPMN Viewer Adapter

## Purpose

The adapter provides a visible, read-only matter projection for the synthetic `notary_team_01` test environment. The surface is a packageable SharePoint Framework web part using **SPFx 1.23.2**, **Heft**, and `bpmn-js/lib/Viewer`. It supports `SharePointWebPart` and `TeamsTab` hosts.

The mode is **viewer-only**. It does not model or save BPMN, start workflows, write SharePoint data, or process real matter data.

## Package and build contract

Package source lives under `spfx/nac-bpmn-viewer`. `package-lock.json` is required source. The reproducible build uses:

```bash
npm ci
npm run build
```

`npm run build` runs the Heft production build and `heft package-solution --production`. The generated package is `sharepoint/solution/nac-bpmn-viewer.sppkg`.

`node_modules`, `lib`, `dist`, `temp`, and `sharepoint/solution` remain ignored and untracked. Recursive source scans do not enter these paths.

## Deployment boundary

The current App Catalog deployment is **owner-approved** and **site-scoped** only for `notary_team_01`. `skipFeatureDeployment=false` enforces site installation. Tenant-wide deployment and installation into any other workspace remain blocked.

The approval covers package build, App Catalog upload, and site installation within this boundary. It does not approve production data, new permissions, or additional sites.

## Graph-free data mode

Runtime data comes only from the package-bound `package_fixture` in `fixtures/syntheticWorkspace.ts`; BPMN XML is bundled from `fixtures/sampleBpmn.ts`.

The SPFx package requests no Graph permission and contains no `MSGraphClient`, `AadHttpClient`, direct Microsoft Graph call, Graph SDK, PnP, CSOM, or legacy SharePoint API. `webApiPermissionRequests` stays absent or empty.

The projection contains synthetic status, task, deadline, and BPMN data only. **No real matter data** is read, displayed, or stored.

## UI and DOM contract

The current UI exposes its package mode directly:

- `data-nac-component="test-workspace"` identifies the test surface.
- `Synthetische Testdaten` visibly identifies the data class.
- `Keine Mandatsdaten` confirms the runtime boundary.
- A different `workspaceId` fails closed with `Workspace nicht freigegeben.`.

These markers replace the former offline render-state DOM contract. Security checks remain explicit: package source, workspace allowlist, viewer-only behavior, no writes, no Graph, and no real matter data are validated separately.

## Contracts and evidence

The authoritative artifacts are the [viewer adapter contract](../../../workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json), [SPFx package artifact](../../../deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json), and [runtime readiness](../../../deploy/m365/teams-sharepoint/nac-bpmn-viewer.runtime-readiness.json).

Run:

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
python3 -m unittest tests.test_m365_bpmn_viewer_runtime_readiness
python3 -m unittest tests.test_m365_sharepoint_bpmn_viewer_adapter
```
