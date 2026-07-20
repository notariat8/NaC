# NaC BPMN Viewer SPFx Skeleton

Status: packageable, site-scoped, viewer-only SPFx source.

This directory defines the future SharePoint Framework web part shape for a
read-only NaC BPMN Viewer. It is not a deployable package in this slice.

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
  render component with fail-closed load and render timeouts.
- `src/webparts/nacBpmnViewer/services/NacBffClient.ts`: bounded delegated BFF
  client and canonical BPMN digest verification.

## Validation

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
```
