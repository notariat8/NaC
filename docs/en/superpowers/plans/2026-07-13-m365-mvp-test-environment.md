# M365 MVP Test Environment Implementation Plan

**Date:** 13 July 2026  
**Issue:** [#620](https://github.com/notariat8/NaC/issues/620)  
**Spec:** [M365 MVP Test Environment Design](../specs/2026-07-13-m365-mvp-test-environment-design.md)  
**Delivery Mode:** Protected PR

## Target State

In the existing workspace notary_team_01, a site-scoped, installable
SPFx 1.23.2 package is visible as a SharePoint page and optionally as a Teams
app. The package-bound synthetic real-estate purchase matter shows matter
status, BPMN, two tasks, and a UTC due date. The owner-gated data-plane smoke
uses raw Graph REST v1.0 for list and item data, reads back the created records
by exact ID, writes redacted evidence, and removes only its own test records.
SPFx has no Graph permission and never calls Graph directly.

The BFF core, server-side allowlist, and fail-closed contracts are implemented
offline. The delegated BFF scope, public deployment, and live Entra token
validation remain DEFERRED while no existing scope and public HTTPS endpoint
are available.

## Implementation Steps

1. **Build the site-scoped package reproducibly (AC-620-01).**
   Pin SPFx 1.23.2, Heft, React, and bpmn-js; bind the lockfile; declare
   SharePointWebPart and TeamsTab; verify skipFeatureDeployment=false and an
   installable site-scoped package.
2. **Enforce the browser and API boundary (AC-620-02).**
   Block Graph permission requests and direct Graph calls from SPFx. Define a
   delegated NaC BFF scope as the only future dynamic API target, with
   activation DEFERRED while no existing scope and HTTPS endpoint are
   available.
3. **Verify BFF identity, projection, and fail-closed behavior
   (AC-620-03, AC-620-04, AC-620-05).**
   Derive identity only from validated Entra token claims; resolve workspace,
   site, and list IDs exclusively through a server-side allowlist; return only
   redacted status, tasks, due date, and BPMN to assigned users. Deny
   unassigned users and manipulated workspace, matter, purpose, or filter
   values without an existence leak. Live token validation and live BFF
   delivery remain DEFERRED; the package-bound projection is package-ready.
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

The BFF core implementation belongs to this slice; its public activation does
not. Activation happens in a separate owner-gated scope only after an existing
public HTTPS endpoint and an existing delegated Entra scope are proven. The
BFF then replaces the package-bound UI data source without changing the rule
that SPFx must never call Graph directly.

## Acceptance Evidence

The package-ready slice is accepted when AC-620-01 through AC-620-07 are
covered with their exact semantics in the machine-readable verification
contract, all focused tests and validators pass, the package builds
reproducibly, and deployment/smoke evidence is synthetic and redacted only.
The BFF scope, public activation, and live token validation remain explicitly
DEFERRED and are not reported as live-complete.
