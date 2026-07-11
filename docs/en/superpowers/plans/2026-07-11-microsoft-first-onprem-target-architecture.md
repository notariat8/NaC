# Microsoft-First, On-Prem AI Implementation Plan

**Goal:** Turn Issue #613 into verifiable product slices without making
SharePoint the workflow engine or Microsoft a cloud-AI prerequisite.

**Architecture:** Teams/SPFx/SharePoint/Entra/Graph form the Microsoft edge.
Python/FastAPI, deterministic workflows, NeMo, PostgreSQL, outbox/broker and
WORM run on-prem. Temporal and baseline modes are exclusive execution modes
with one technical truth each; WORM remains separate. Local sidecars remain
non-authoritative.

**Delivery:** Every slice has a leading issue, contract/verification, protected
PR and a separate owner gate for live, credential or deployment actions.

## Slice 1: S3/S4 Type Validation And Graph Read Port

- [ ] Complete the offline S3 BusinessCaseType runtime.
- [ ] Build the S4 Graph-v1.0 adapter with ETag, paging, redaction and a fail-closed read port.
- [ ] Use no Graph SDK, SharePoint REST, PnP or Graph Beta.
- [ ] Keep registry and viewer caches separate.

## Slice 2: Entra-Protected BFF

- [ ] Specify the FastAPI BFF contract for OBO/user context and app roles.
- [ ] Enforce role, matter, purpose and delegation binding before every operation.
- [ ] Define SPFx/AadHttpClient requests, DTO redaction and correlation IDs.
- [ ] Keep provisioning and runtime application identities separate.

## Slice 3: SPFx Read-Only Workspace

- [ ] Show matter status, tasks, deadlines and document pointers read-only.
- [ ] Integrate the existing `bpmn-js` viewer.
- [ ] Provide Teams tab and SharePoint web part from one package.
- [ ] Fix SPFx 1.22+/Heft, App Catalog, .sppkg, Teams publishing and the early admin gate.
- [ ] Pin the BPMN model version per instance and load bpmn-js using lazy loading/code splitting.
- [ ] Keep business logic, secrets, workflow timers and agentic runtime out of the browser.

## Slice 4: Durable Workflow Spike

- [ ] Fix one common synthetic scenario and measurement criteria.
- [ ] Test self-hosted Temporal/Python SDK against a Python/PostgreSQL baseline.
- [ ] Measure failure, month-long timer, human task, versioning, backup/restore,
  idempotency, HA, monitoring and operating cost.
- [ ] Make a separate ADR decision; no automatic Temporal Go.

## Slice 5: Technical Persistence And Audit

- [ ] Build the common PostgreSQL schema for domain read models, outbox, task metadata, projections and synchronization.
- [ ] In Temporal mode, use Temporal Service/Event History exclusively for execution state, timers and retries.
- [ ] In baseline mode, use PostgreSQL additionally and exclusively for workflow state, timers, leases and retries.
- [ ] Keep WORM evidence separate from technical execution truth in both modes.
- [ ] Add broker/inbox/reconciliation contracts.
- [ ] Select WORM journal, signature/anchor evidence and retention owner-gated.
- [ ] Reproduce SharePoint projections from central state.

## Slice 6: NeMo Activities And Personal Agent

- [ ] Use NeMo Agent Toolkit as the only agentic runtime behind bounded activities.
- [ ] Connect Graph, audit and local workstation MCP servers by purpose.
- [ ] Treat agent output as proposals; deterministic gates decide.
- [ ] Store no matter data in agent memory or GitHub evidence.

## Slice 7: Local Sidecars And Pilot

- [ ] Pilot Word/Track Changes, scanner, card workstation and XNP adapters.
- [ ] Encrypt short-lived caches and sign the local outbox.
- [ ] Resolve offline conflicts centrally and audibly.
- [ ] Start four first-wave cases and the 2+2 pilot after operating acceptance.

## Validation Per Slice

- focused unit, contract and security tests,
- matching standalone validator,
- `python3 scripts/nac.py contracts verify`,
- `python3 scripts/nac.py doctor --profile strict`,
- independent `base...head` review,
- live or deployment evidence only after a concrete owner gate.

