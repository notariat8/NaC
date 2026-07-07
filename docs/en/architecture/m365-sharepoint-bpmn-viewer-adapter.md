# M365 SharePoint BPMN Viewer Adapter

Status: contract-first decision
Last content update: 2026-07-07

## Purpose

NaC can later show BPMN processes in SharePoint without making SharePoint the
leading BPMN source, BPMN modeler or workflow engine. The clean starting point
is a read-only SPFx web part with `bpmn-js` in viewer-only mode. This web part
renders approved BPMN XML models and, optionally, reviewed status metadata
from SharePoint lists.

The active MVP data path remains Teams, Microsoft 365 group and SharePoint
team site through Microsoft Graph REST. This adapter is only a display and
navigation surface on the same M365 work surface.

## Decision

The MVP does not build a SharePoint plugin or BPMN modeler now. NaC first
defines only the contract for a later `NaC BPMN Viewer`:

```text
Git BPMN templates
  -> Python validation and pull request review
    -> approved BPMN model copy or pointer
      -> SharePoint document library "BPMN Models"
        -> SPFx Web Part with bpmn-js Viewer
          -> read-only process page in SharePoint
```

This is deliberately smaller than a full modeler. Editing stays in the local
NaC BPMN-js editor and in the pull-request process. SharePoint only displays
what has already been approved.

## SharePoint Surface

The later SharePoint site may receive two additional artifacts:

| Artifact | Purpose |
| --- | --- |
| `BPMN Models` | Document library for approved BPMN XML copies or pointers |
| `Prozessregister` | List for process name, owner, status, version, review date and model link |

The web part may read approved BPMN XML files. It must not read matter
document contents, mandate values, secrets or productive specialist-system
data. Status overlays are allowed only as reviewed metadata, for example from
`AufgabenFristen`, `AuditJournalLite`, `DokumentRegister` or a later
`Prozessregister`.

For this MVP slice there is only an optional provisioning plan at
`deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json`. Its status is
`optional_plan_only_no_live_apply`: `nac m365 teams-sharepoint
bpmn-viewer-plan --format json` renders the planned library, list and columns,
but does not run a live apply against Microsoft 365 and does not extend the
required MVP SharePoint schema.

The first SPFx slice is source-only under `spfx/nac-bpmn-viewer`. The command
`nac m365 teams-sharepoint spfx-bpmn-viewer-skeleton --format json` renders the
skeleton, the synthetic render fixture and the MCP request plans for
`bpmn_model_get`, `process_register_list` and `bpmn_viewer_overlay_get`. This
slice does not build an SPFx package, does not create `package-lock.json`, does
not use the App Catalog and does not run a Graph or tenant apply.

The runtime-readiness slice also remains offline:
`nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json`
checks the boundaries for SPFx packaging, App Catalog deployment and the later
Graph content read of approved `.bpmn` files. `PASSED` means only that the
guardrails are intact. It does not approve packaging, App Catalog upload,
tenant apply or live BPMN content reads. Those steps remain owner gates with a
separate PR, rollback plan and redacted evidence.

## Graph REST Boundary

All access runs through Microsoft Graph REST v1.0 or an MCP server that also
uses Microsoft Graph REST internally. Legacy SharePoint REST APIs, CSOM, PnP
and Microsoft Graph SDKs remain blocked.

Allowed endpoint families for the viewer contract:

- `GET /sites/{site-id}/drives`
- `GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/content`
- `GET /sites/{site-id}/lists/{list-id}/items`
- `GET /sites/{site-id}/lists/{list-id}/items/{item-id}`

The content read is limited to approved BPMN XML models. It is not permission
to read matter document contents or mandate payloads.
Before a later live read, at least `ApprovalStatus=Approved`,
`ViewerEnabled=true`, `ContainsMatterData=false`, an allowed `NacDataClass` and
the `BpmnXmlSha256` check against the loaded XML must pass.

## Why SPFx

SharePoint Online is not a neutral file host where modern pages should
reliably execute arbitrary HTML or JavaScript apps. Custom Script is restricted
in SharePoint Online for security reasons. An SPFx web part is the appropriate
SharePoint delivery shape for client-side components.

`bpmn-js` is suitable for rendering BPMN 2.0 XML in the browser. NaC uses only
the viewer here. The modeler, saving, locking, XML round-tripping, versioning
and approvals are a separate later scope.

## Blocked

This adapter must not:

- write or save BPMN XML,
- start or execute workflow instances,
- mutate SharePoint schema, Teams or memberships,
- read matter document contents or mandate payloads,
- store secrets,
- use Custom Script or loose HTML embedding as the product path,
- use legacy SharePoint APIs, CSOM, PnP or Graph SDKs,
- replace pull-request review and Python validation.

## Relationship To MCP

No new MCP server is needed now. If the viewer later uses MCP, it uses the
existing `teams-sharepoint-data-mcp` boundary. Possible read-only tools are:

- `bpmn_model_get`
- `process_register_list`
- `bpmn_viewer_overlay_get`

These tools remain read-only, redact metadata and do not return matter
document contents. In the current runtime they are request-plan tools; the
owner-gated live-read mode remains limited to `case_get` and `document_list`.

## Relationship To The BPMN-js Editor

The existing BPMN-js editor contract remains the editing and governance
boundary. The SharePoint adapter is a display projection for approved models,
not the source, editor or execution engine.

## Validation

The contract is enforced by these checks:

```bash
python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
python3 -m unittest tests.test_m365_bpmn_viewer_runtime_readiness
python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton
python3 -m unittest tests.test_m365_bpmn_viewer_provisioning
python3 -m unittest tests.test_m365_sharepoint_bpmn_viewer_adapter
python3 scripts/quality_gate.py --profile strict
```
