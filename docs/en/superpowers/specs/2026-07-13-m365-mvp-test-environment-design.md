# M365 MVP Test Environment Design

Status: historical live acceptance verified on 14 July 2026; current read-only acceptance reconciliation `INCOMPLETE`
Date: 13 July 2026
Local contract correction: 1 October 2026
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
  - python -m unittest tests.test_m365_mvp_test_environment_verification_contract
  - python -m unittest tests.test_m365_spfx_bpmn_viewer_skeleton tests.test_m365_bpmn_viewer_runtime_readiness tests.test_m365_sharepoint_bpmn_viewer_adapter tests.test_m365_spfx_site_deployment tests.test_m365_mvp_test_environment_smoke tests.test_m365_mvp_test_environment_deploy tests.test_m365_test_environment_bff tests.test_m365_runtime_env_bootstrap
  - python scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py
  - python scripts/validate_spec_traceability.py
  - python scripts/validate_language_parity.py
  - python scripts/validate_doc_links.py
  - python scripts/nac.py contracts verify
  - python scripts/nac.py doctor --profile strict
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

Today's acceptance under #620 reconciles existing redacted current-state
evidence against the existing acceptance criteria only. The
[verification contract](../../../../workflows/contracts/m365-mvp-test-environment.verification.contract.json)
records `final_bff_live_verification` as bounded read-only reconciliation with
status `INCOMPLETE` and the
[versioned current-state evidence](../../../../workflows/verification-contracts/evidence/m365-mvp-current-state-acceptance.redacted.json).
This local correction starts no provider access, login, token refresh,
deployment, seeding, new write, or delete. Missing evidence remains open; an
offline candidate or test report is not a live receipt.

## Mandatory Layer Separation

### SharePoint and Teams UI

The UI is a site-scoped SPFx `1.23.2` package with Teams hosts.
`skipFeatureDeployment` remains `false`; tenant-wide deployment is forbidden.
Initially, the original package rendered package-bound synthetic data only. It requests
exactly zero Microsoft Graph permissions and contains no direct Graph client,
Graph token, legacy SharePoint API, or SDK data path.

### Separate Deployment Control Plane and Data Plane

The Microsoft 365 CLI is the conscious control-plane exception for
site-specific package deployment. It may only deploy the SPFx package to the
App Catalog, install or upgrade the app on the exact site, publish the
dedicated page and web part, and deploy the derived Teams package to the exact
team. It must not read, write, or delete SharePoint list or item data and must
not change permissions, scopes, or credentials.

Historical synthetic seeding, targeted readback, and cleanup form the
owner-gated data-plane smoke. This description grants no present write or
delete authority. Every SharePoint list and item data operation uses raw
Microsoft Graph REST `v1.0` exclusively; legacy SharePoint data APIs and SDK
data paths are forbidden. The runner is hard-bound to `notary_team_01`, its
site and team binding, and the synthetic matter ID `NAC-SYN-MATTER-001`. It
performs no permission or credential change and fails closed on workspace,
package, hash, role, or readback drift.

### Current BFF Acceptance Reconciliation

Direct Microsoft Graph access from SPFx remains permanently forbidden. The
dynamic read path is `SPFx/Teams -> NaC BFF -> Graph REST v1.0`. The BFF
enforces workspace, matter, purpose, role, and deputy boundaries server-side
and returns redacted DTOs only. Issue #632 provisioned the public endpoint,
`Matter.Read`, runtime `Sites.Selected`, and site role `read` under an owner
gate. The separate historical
[#632 activation contract](../../../../workflows/contracts/m365-azure-bff-live-activation.contract.json)
remains unchanged; today's #620 acceptance requires no new twelve-step
activation run and inherits no create/reuse/approve authority. Exact existing
scopes, roles, and site grants require traceable readbacks. Missing,
mismatched, duplicate, or broader bindings block; reconciliation neither
creates nor repairs them. The #739 state
`FUNCTION_DEPLOYMENT_PROVENANCE_LOST` remains terminal: no reconstruction,
resumption, or rerun of that run.

Current release/host/version binding accepts a causal chain of hash-bound
source input, successful remote-build deployment handoff, and separate
current host/version readbacks. A digest of the binary artifact built only
inside Azure is no additional requirement. Separate readbacks must neither
replace the handoff nor reconstruct #739 provenance.

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
A production identity decision may only be made by the BFF from validated
Entra claims and server-side role bindings. Current acceptance still requires
positive evidence for the time-valid, justified, recorded deputy. The negative
case independently requires a pre-decision state proving no assignment and
no valid deputy grant. A separate authenticated candidate `403` does not
replace that prestate.

## Historical Deployment and Cleanup

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
Current reconciliation verifies historical run-owned cleanup only; it creates
or deletes no new item.

## Evidence and Data Protection

Evidence includes status, correlation ID, package and BPMN hashes, technical
step and role decisions, and cleanup results. It excludes tokens,
certificates, private keys, raw Graph responses, people, documents, real file
numbers, and resolvable production references. Historical live actions remain
bound to their original approval and exact workspace. Current reconciliation
evidence records existing observations, their bindings, and open gaps, without
fabricated `PASSED` evidence.

## Acceptance Criteria

- **AC-620-01:** A reproducibly built, site-scoped and installable SPFx
  package declares the SharePointWebPart and TeamsTab hosts and sets
  skipFeatureDeployment=false.
- **AC-620-02:** SPFx never requests Microsoft Graph permissions and never
  calls Graph directly. Its only permitted dynamic API target is the NaC BFF
  `Matter.Read` scope provisioned owner-gated under Issue #632; current version
  and permission binding still require evidence.
- **AC-620-03:** The BFF derives user identity exclusively from a validated
  Entra access token and resolves workspace, site, and list identifiers only
  through a server-side allowlist. JWT/JWKS validation and fail-closed
  boundaries are implemented offline; current live token validation is checked
  against existing bound evidence.
- **AC-620-04:** An assigned user receives only a redacted projection of
  synthetic matter status, tasks, due date, and BPMN. This projection and the
  fixed Graph REST adapter are package-ready; current SharePoint and Teams
  delivery and version binding must be proven by existing live evidence. A
  time-valid, justified deputy remains a separate mandatory positive role case.
- **AC-620-05:** Unassigned users and manipulated workspace, matter, purpose,
  or filter inputs fail closed without disclosing the matter's existence or
  metadata. The unassigned negative case requires independent prestate
  evidence of no assignment and no valid deputy grant.
- **AC-620-06:** Site-scoped SharePoint and optional Teams deployment, Graph
  REST v1.0 write/readback, run-owned cleanup, and the associated evidence
  are reproducible and redacted. Current read-only reconciliation verifies
  existing deployment, readbacks, historical run-owned cleanup, and repeated
  unchanged readbacks as convergence; it performs no new write or delete.
- **AC-620-07:** Current acceptance creates or changes no credential, scope,
  role, grant, or other permission, touches no production data, and remains
  limited to `notary_team_01`. Existing readbacks must prove exact
  `Matter.Read`, runtime `Sites.Selected`, and site role `read`; missing,
  mismatched, duplicate, or broader bindings block without repair. Historical
  #632 supersession grants no present create/reuse/approve authority.

Hardening from [#681](https://github.com/notariat8/NaC/issues/681) remains
mandatory and unchanged: **AC-681-01** binds only the canonical BPMN source,
process, profile, and SHA-256 without embedded BPMN; **AC-681-02** binds every
task exactly once to a canonical BPMN task with matching `nac:kgRef`,
BusinessCaseType, and usecase-local knowledge graph; **AC-681-03** remains
offline with no tenant, permission, or credential change.

## Delivery Status

The owner-approved Live-One-Shot completed successfully in `notary_team_01` on
14 July 2026. Verified scope comprises the site-scoped SPFx/Heft package, App
Catalog and Teams gate, shared SharePoint/Teams package path, synthetic matter
status with two tasks and a UTC due date, the read-only `bpmn-js` viewer with
BPMN binding, role decisions, Graph REST `v1.0` write/readback, and run-owned
cleanup. Document pointers and `bpmn-js` lazy loading/code splitting were not
proven and remain open. The
[historical `PASSED` attestation](../../../../workflows/verification-contracts/m365-mvp-test-environment-live.verification.json)
is preserved unchanged and proves neither BFF activation nor live Entra token
validation.

The Azure Functions BFF is verifiable as **READY** offline with Entra JWT/JWKS
validation, a fixed Graph REST `v1.0` projection, deterministic package,
managed-identity IaC, and the central offline readiness gate. Issue #632
introduced the public endpoint, `Matter.Read`, runtime `Sites.Selected`, and
the exact `read` site grant under a bounded owner gate. An earlier activation
attempt ended in `FAILED_PARTIAL` at SPFx deployment; the related fix was
merged. This activation and failure history stays separate; #739 still ends
in terminal `FUNCTION_DEPLOYMENT_PROVENANCE_LOST`.

Current acceptance observations record assigned workspace/workbench/BPMN
`200`, anonymous `401`, all four workspace/matter/purpose/filter `403`, and a
separate authenticated candidate `403` on both routes in
[#620 evidence 5932777104](https://github.com/notariat8/NaC/issues/620#issuecomment-5932777104)
and [#620 evidence 5934493891](https://github.com/notariat8/NaC/issues/620#issuecomment-5934493891).
Current render observations are referenced by
[#620 evidence 5918874200](https://github.com/notariat8/NaC/issues/620#issuecomment-5918874200)
and [#762 evidence 5916031285](https://github.com/notariat8/NaC/issues/762#issuecomment-5916031285).
These observations do not establish a full `PASSED` result.

Current release-input/host/version binding, a positive valid-deputy case,
independent unassigned prestate without a valid deputy, SharePoint render
proof, and exact permission and read-only convergence evidence remain open.
Current-state acceptance stays `INCOMPLETE` until all are proven.

## Non-goals

- no production data and no access to another workspace,
- no present Entra, role, scope, grant, app credential, or certificate change,
- no direct Graph access from SPFx,
- no production BFF activation without an existing endpoint and scope,
- no BPMN execution by `bpmn-js`; the package renders BPMN read-only,
- no tenant-wide SPFx deployment and no automatic deletion of foreign app,
  page, Teams, or SharePoint artifacts,
- no new #632 activation run and no reconstruction or rerun of terminal #739
  to satisfy today's acceptance.
