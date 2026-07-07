# NaC BPMN Viewer SPFx Skeleton

Status: offline source skeleton only.

This directory defines the future SharePoint Framework web part shape for a
read-only NaC BPMN Viewer. It is not a deployable package in this slice.

## Boundary

- Uses `bpmn-js/lib/Viewer`, not the modeler.
- Renders only approved BPMN XML fixtures or future approved BPMN content after
  a separate owner gate.
- Mirrors `teams-sharepoint-data-mcp` request-plan shapes only.
- Does not execute Microsoft Graph requests.
- Does not write BPMN XML, SharePoint list items, documents, Teams settings or
  process instances.
- Does not include an SPFx package, lockfile, build output or app-catalog
  deployment artifact.

## Current Files

- `package.json`: dependency metadata for the future SPFx package, not an
  installed Node workspace.
- `config/package-solution.json`: solution identity skeleton with deployment
  disabled.
- `src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts`: web part shell.
- `src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx`: viewer-only
  render component.
- `src/webparts/nacBpmnViewer/services/BpmnViewerRequestPlan.ts`: MCP
  request-plan boundary.
- `src/webparts/nacBpmnViewer/fixtures/sampleBpmn.ts`: synthetic BPMN fixture.

## Validation

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
```
