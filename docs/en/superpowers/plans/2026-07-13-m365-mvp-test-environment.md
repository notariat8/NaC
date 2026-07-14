# M365 MVP Test Environment Implementation Plan

**Date:** 13 July 2026
**Issue:** [#620](https://github.com/notariat8/NaC/issues/620)
**Spec:** [M365 MVP Test Environment Design](../specs/2026-07-13-m365-mvp-test-environment-design.md)
**Delivery Mode:** Protected PR
**Live Status:** Owner-approved Live-One-Shot succeeded in `notary_team_01` on 14 July 2026; Azure BFF offline READY, live activation DEFERRED

## Target State

In the existing workspace notary_team_01, a site-scoped, installable
SPFx 1.23.2 package is visible as a SharePoint page and optionally as a Teams
app. The package-bound synthetic real-estate purchase matter shows matter
status, BPMN, two tasks, and a UTC due date. The owner-gated data-plane smoke
uses raw Graph REST v1.0 for list and item data, reads back the created records
by exact ID, writes redacted evidence, and removes only its own test records.
SPFx has no Graph permission and never calls Graph directly.

The BFF core, server-side allowlist, Entra JWT validation, raw Graph REST
`v1.0` adapters, deterministic Azure Functions package, and Bicep baseline are
implemented offline and report `READY` through
`nac m365 teams-sharepoint bff-azure-readiness`. The new SPFx package
loads dynamic matter data only from the fixed BFF endpoint through
`AadHttpClient`; only the hash-bound BPMN XML remains in the package without
matter data. The complete live sequence is hash-bound through
`nac m365 teams-sharepoint bff-azure-activation-plan`. The delegated BFF
scope, Azure deployment, site grant, and live Entra token validation remain
`DEFERRED` until the single consolidated owner gate.

## Implementation Steps

1. **Build the site-scoped package reproducibly (AC-620-01).**
   Pin SPFx 1.23.2, Heft, React, and bpmn-js; bind the lockfile; declare
   SharePointWebPart and TeamsTab; verify skipFeatureDeployment=false and an
   installable site-scoped package.
2. **Enforce the browser and API boundary (AC-620-02).**
   Block Graph permission requests and direct Graph calls from SPFx. Define a
   delegated NaC BFF scope as the only dynamic API target. The new package
   uses that boundary; live deployment remains DEFERRED until the bundled
   scope and HTTPS activation.
3. **Verify BFF identity, projection, and fail-closed behavior
   (AC-620-03, AC-620-04, AC-620-05).**
   Derive identity only from validated Entra token claims; resolve workspace,
   site, and list IDs exclusively through a server-side allowlist; return only
   redacted status, tasks, due date, and BPMN to assigned users. Deny
   unassigned users and manipulated workspace, matter, purpose, or filter
   values without an existence leak. Live token validation and live BFF
   delivery remain DEFERRED; the BFF client, DTO validation, and fail-closed
   UI states are package-ready.
4. **Protect SharePoint/Teams deployment and the Graph smoke (AC-620-06).**
   Verify package ID, SHA-256, SPFx version, site/team binding, and App Catalog
   responses. Idempotently deploy the app, page, web part, and optional Teams
   package. Write only synthetic list items through Graph REST v1.0, read them
   back by exact ID, and delete them as run-owned cleanup. Deployment,
   readback, cleanup, and evidence must be reproducible and redacted.
5. **Verify the immutable safety boundary (AC-620-07).**
   Create or change no credential, permission, or Entra scope; read or write
   no production data; and allow no action outside notary_team_01. A wrong
   workspace, missing owner approval, hash drift, or security error stops
   before the first write.
6. **Integrate the one-shot operator edge and acceptance
   (AC-620-01, AC-620-02, AC-620-03, AC-620-04, AC-620-05, AC-620-06, AC-620-07).**
   The central nac CLI combines package validation, site-scoped deployment,
   synthetic smoke, readback, cleanup, and redacted evidence. Focused tests
   including deployment and runtime environment bootstrap, contract
   verification, language parity, link validation, visual proof, the strict
   gate, and green Protected PR checks provide the evidence.

## Live Action Order

1. bind the current package and SHA-256 to the deployment gate,
2. deploy the App Catalog package site-scoped,
3. install or upgrade the app on the target site,
4. publish the test page and web part idempotently,
5. optionally publish the Teams package and install it in the exact team,
6. run the synthetic Graph smoke with readback and cleanup,
7. verify the installation and page read-only,
8. produce redacted completion evidence and visual proof.

## Stop Conditions

The run fails closed on missing permission, a security error, workspace/site/
team drift, a wrong package hash, tenant-wide deployment, a Graph permission
in the SPFx package, production-like data, incomplete readback, or failed
targeted cleanup. It does not change permissions, credentials, certificates,
or Entra scopes.

## BFF Activation after Issue #620

The offline BFF implementation belongs to this slice, including the Azure
Functions host, managed-identity IaC, storage network boundary, cost limits,
JWT/JWKS hardening, and fixed `notary_team_01` Graph projection. Public
activation happens in one consolidated owner gate: deploy Azure resources,
configure the delegated Entra scope and exact site grant, deploy the source package through Azure Functions Flex OneDeploy with `--build-remote true`, and switch SPFx to the BFF through `AadHttpClient`. The ZIP is intentionally a reproducible source package; deployment without remote build is forbidden. Until that gate, the BFF
leaves the previously deployed package version visible, while the new
repository package is fully cut over to `AadHttpClient -> NaC BFF`. SPFx must
still never call Graph directly. The `bff-azure-activation-plan` command
binds all twelve activation, access, idempotency, and evidence steps under one
SHA-256. The hash includes only Git-tracked SPFx package inputs, so local build
outputs cannot change the binding. The later live runner must build the
`.sppkg` from those inputs and record its SHA-256 as redacted evidence.
Because Entra assigns the API client ID only when the application is created,
the same approved live run must resolve exactly one application by
`api://funktion8.de/nac-bff`, read back
`api.requestedAccessTokenVersion=2` and `Matter.Read`, then bind the verified
`appId` as the exact `bffApiAudience` before Bicep deployment. The offline
plan explicitly makes no live-success claim; only the owner-gated runner may
emit `PASSED` evidence from provider responses it captured itself. Approval
is limited to the contract-bound `notary_team_01` site ID.

## Acceptance Evidence

The owner-approved Live-One-Shot completed successfully in `notary_team_01` on
14 July 2026 with the site-scoped SPFx/Heft package, SharePoint/Teams gate,
synthetic matter, BPMN, tasks/due date, role decisions, Graph REST `v1.0`
readback, and run-owned cleanup. Evidence remains synthetic and redacted.
Document pointers and `bpmn-js` lazy loading were not proven and remain open.
The BFF scope, public activation, and live Entra token validation remain
explicitly DEFERRED and are not reported as live-complete.
