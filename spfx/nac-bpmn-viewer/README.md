# NaC BPMN Viewer SPFx Skeleton

Status: packageable, site-scoped, viewer-only SPFx source.

This directory contains the packageable SharePoint Framework web part for the
read-only NaC BPMN Viewer. The repository can build the site-scoped `.sppkg`;
App Catalog upload, site installation, tenant access and activation remain
owner-gated operations outside this offline slice.

## Boundary

- Uses `bpmn-js/lib/Viewer`, not the modeler.
- Loads a redacted synthetic workspace DTO through the delegated NaC BFF
  `Matter.Read` boundary.
- Renders only the canonical `bpmn/immobilienkaufvertrag.bpmn` XML delivered by
  the BFF after exact-shape, size and SHA-256 verification in the browser.
- Does not execute Microsoft Graph requests in the browser.
- Does not write BPMN XML, SharePoint list items, documents, Teams settings or
  process instances.
- Includes the pinned lockfile and package definition; generated build and
  app-catalog artifacts remain ignored and untracked.

## Current Files

- `package.json` and `package-lock.json`: pinned SPFx 1.23.2 build inputs.
- `config/package-solution.json`: site-scoped solution with only the delegated
  NaC BFF `Matter.Read` request.
- `src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts`: web part shell.
- `src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx`: viewer-only
  role, deadline and task cockpit with fail-closed load/render boundaries,
  deterministic filters and separate Current/Selected BPMN markers.
- `src/webparts/nacBpmnViewer/components/WorkspaceViewModel.ts`: pure task-filter,
  role-label and deadline-state derivation from an explicitly bound timestamp.
- `src/webparts/nacBpmnViewer/services/NacBffClient.ts`: bounded delegated BFF
  client and canonical BPMN digest verification.
- `scripts/generate-role-deadline-visual-fixture.cjs`: self-contained synthetic
  offline visual contract that reuses the production stylesheet and canonical
  BPMN without tenant or BFF access. It is intentionally not React/SPFx E2E.
- `scripts/capture-role-deadline-visual-evidence.cjs`: pinned Playwright capture
  and recovery checks for six viewport/container/theme states plus a source-
  and screenshot-bound manifest.
- `scripts/validate-read-only-boundary.cjs`: positive SHA-256 production-source
  capability manifest, TypeScript-AST allowlist, and mutation tests for exactly
  one delegated `Matter.Read` BFF GET.

## Validation

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
cd spfx/nac-bpmn-viewer
npm ci --ignore-scripts
npm run build
npm run visual:fixture -- /tmp/nac-spfx-role-deadline-cockpit.html
npm run visual:capture -- /tmp/nac-spfx-role-deadline-evidence
```

The capture command uses lockfile-pinned `playwright@1.55.0` and requires its
matching Chromium installation. It writes element-cropped PNGs and
`VIS-710-manifest.json`; repository validation rejects stale source or
screenshot hashes. Component behavior remains covered by Jest/Heft rather than
being inferred from the standalone visual contract.
