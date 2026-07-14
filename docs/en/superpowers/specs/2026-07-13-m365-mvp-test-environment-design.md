# M365 MVP Test Environment Design

Status: Live deployment verified on 14 July 2026; Azure BFF offline READY, live path DEFERRED
Date: 13 July 2026
Scope: site-specific, synthetic-only test environment in workspace `notary_team_01`

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: m365-mvp-test-environment
leading_issue: https://github.com/notariat8/NaC/issues/620
risk_gate: Human Approval
delivery_mode: Protected PR
plan: docs/en/superpowers/plans/2026-07-13-m365-mvp-test-environment.md
review_gates:
  - Privacy
  - External Service
  - Human Approval
acceptance_ids:
  - AC-620-01
  - AC-620-02
  - AC-620-03
  - AC-620-04
  - AC-620-05
  - AC-620-06
  - AC-620-07
validation_commands:
  - python3 -m unittest tests.test_m365_mvp_test_environment_verification_contract
  - python3 -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton tests.test_m365_bpmn_viewer_runtime_readiness tests.test_m365_sharepoint_bpmn_viewer_adapter tests.test_m365_spfx_site_deployment tests.test_m365_mvp_test_environment_smoke tests.test_m365_mvp_test_environment_deploy tests.test_m365_test_environment_bff tests.test_m365_runtime_env_bootstrap
  - python3 scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_language_parity.py
  - python3 scripts/validate_doc_links.py
  - python3 scripts/nac.py contracts verify
  - python3 scripts/nac.py doctor --profile strict
  - git diff --check
```

## Goal

Issue #620 delivers the first visible M365 test environment for the NaC MVP.
In the existing Teams and SharePoint workspace `notary_team_01`, it presents a
fully synthetic real-estate purchase matter with a BPMN diagram, tasks, a due
date, and role decisions. The slice proves packaging, site-specific
installation, the controlled Graph data edge, readback, cleanup, and redacted
evidence. It processes no production matter, person, document, or
communication data.

## Mandatory Layer Separation

### SharePoint and Teams UI

The UI is a site-scoped SPFx `1.23.2` package with Teams hosts.
`skipFeatureDeployment` remains `false`; tenant-wide deployment is forbidden.
Initially, the package renders package-bound synthetic data only. It requests
exactly zero Microsoft Graph permissions and contains no direct Graph client,
Graph token, legacy SharePoint API, or SDK data path.

### Separate Deployment Control Plane and Data Plane

The Microsoft 365 CLI is the conscious control-plane exception for
site-specific package deployment. It may only deploy the SPFx package to the
App Catalog, install or upgrade the app on the exact site, publish the
dedicated page and web part, and deploy the derived Teams package to the exact
team. It must not read, write, or delete SharePoint list or item data and must
not change permissions, scopes, or credentials.

Synthetic seeding, targeted readback, and cleanup instead form the owner-gated
data-plane smoke. Every SharePoint list and item data operation uses raw
Microsoft Graph REST `v1.0` exclusively; legacy SharePoint data APIs and SDK
data paths are forbidden. The runner is hard-bound to `notary_team_01`, its
site and team binding, and the synthetic matter ID `NAC-SYN-MATTER-001`. It
performs no permission or credential change and fails closed on workspace,
package, hash, role, or readback drift.

### Deferred BFF Activation

Direct Microsoft Graph access from SPFx remains permanently forbidden. The
future dynamic read path is `SPFx/Teams -> NaC BFF -> Graph REST v1.0`. The BFF
enforces workspace, matter, purpose, role, and deputy boundaries server-side
and returns redacted DTOs only. Its activation is deliberately deferred in
Issue #620 until an existing public HTTPS endpoint and an existing delegated
Entra scope are available. This slice must not create or modify an Entra
permission, credential, or scope.

## Synthetic Test Matter

The visible test record is marked synthetic and non-production. It contains
only:

- matter ID `NAC-SYN-MATTER-001` and the real-estate purchase matter type,
- one package-bound BPMN 2.0 model with a canonical hash,
- two synthetic tasks linked to BPMN steps,
- at least one explicit due date represented as an ISO-8601 UTC value,
- the assigned, recorded-deputy, and unauthorized role cases.

The UI must visibly state “Synthetic test data” and “No client data”. People,
real file numbers, document content, notarial free text, tokens, and raw Graph
responses are forbidden.

## Role and Visibility Verification

The test environment verifies three separate decisions:

1. The assigned role receives access to the synthetic matter.
2. A time-valid, justified deputy receives access and yields an auditable
   decision record.
3. An unassigned role receives no access, and the response discloses neither
   the matter's existence nor its metadata.

The package-bound UI may present these cases as synthetic contract evidence.
A production identity decision may only be made by the future BFF from
validated Entra claims and server-side role bindings.

## Deployment and Cleanup

Before each action, the App Catalog and site runner validates the package ID,
package hash, SPFx version, site-scoped deployment, and target binding. It
idempotently installs or upgrades the app, creates the dedicated test page,
sets and publishes the web part, and may publish the derived Teams package to
the organization catalog and install it in the exact team.

The synthetic Graph smoke creates only the declared test matter and its tasks,
reads them back by exact identifier, and removes every list item created by
that run in a `finally` path. Existing or production entries are never
deleted. A failure produces `FAILED`, redacted evidence, and best-effort
targeted cleanup rather than an uncontrolled rollback.

## Evidence and Data Protection

Evidence includes status, correlation ID, package and BPMN hashes, technical
step and role decisions, and cleanup results. It excludes tokens,
certificates, private keys, raw Graph responses, people, documents, real file
numbers, and resolvable production references. All live actions remain
owner-gated and limited to the approved workspace.

## Acceptance Criteria

- **AC-620-01:** A reproducibly built, site-scoped and installable SPFx
  package declares the SharePointWebPart and TeamsTab hosts and sets
  skipFeatureDeployment=false.
- **AC-620-02:** SPFx never requests Microsoft Graph permissions and never
  calls Graph directly. Its only permitted dynamic API target is a delegated
  NaC BFF scope. Scope, HTTPS endpoint, and SPFx cutover remain `DEFERRED`
  until the consolidated owner gate.
- **AC-620-03:** The BFF derives user identity exclusively from a validated
  Entra access token and resolves workspace, site, and list identifiers only
  through a server-side allowlist. JWT/JWKS validation and fail-closed
  boundaries are implemented offline; live token validation remains
  `DEFERRED` until the owner gate.
- **AC-620-04:** An assigned user receives only a redacted projection of
  synthetic matter status, tasks, due date, and BPMN. This projection and the
  fixed Graph REST adapter are package-ready offline; delivery through the
  live BFF remains `DEFERRED`.
- **AC-620-05:** Unassigned users and manipulated workspace, matter, purpose,
  or filter inputs fail closed without disclosing the matter's existence or
  metadata.
- **AC-620-06:** Site-scoped SharePoint and optional Teams deployment, Graph
  REST v1.0 write/readback, run-owned cleanup, and the associated evidence
  are reproducible and redacted.
- **AC-620-07:** The slice creates no credential or permission, touches no
  production data, and performs no operation in any workspace other than
  notary_team_01.

## Delivery Status

The owner-approved Live-One-Shot completed successfully in `notary_team_01` on
14 July 2026. Verified scope comprises the site-scoped SPFx/Heft package, App
Catalog and Teams gate, shared SharePoint/Teams package path, synthetic matter
status with two tasks and a UTC due date, the read-only `bpmn-js` viewer with
BPMN binding, role decisions, Graph REST `v1.0` write/readback, and run-owned
cleanup. Document pointers and `bpmn-js` lazy loading/code splitting were not
proven and remain open.

The Azure Functions BFF is verifiable as **READY** offline with Entra JWT/JWKS
validation, a fixed Graph REST `v1.0` projection, deterministic package,
managed-identity IaC, and the central offline readiness gate. Public BFF
activation, delegated Entra scope, exact site grant, SPFx `AadHttpClient`
cutover, and live token validation remain explicitly **DEFERRED** and were not
part of the successful Live-One-Shot.

## Non-goals

- no production data and no access to another workspace,
- no Entra permission, scope, app credential, or certificate change,
- no direct Graph access from SPFx,
- no production BFF activation without an existing endpoint and scope,
- no BPMN execution by `bpmn-js`; the package renders BPMN read-only,
- no tenant-wide SPFx deployment and no automatic deletion of foreign app,
  page, Teams, or SharePoint artifacts.
