# NaC Build Now

Status: active development
Last update: 2026-07-29
Branch: `main`

## What Is Being Built

NaC is now in implementation mode. The first executable development increment is
the notarial KG runtime:

```bash
python scripts/notary_kg.py --repo-root . status
python scripts/notary_kg.py --repo-root . case bautraegervertrag
python scripts/notary_kg.py --repo-root . editor-view immobilienkaufvertrag
```

The runtime reads the usecase-local static KG files, summarizes development
readiness and exposes case-level open questions, gates, documents and plugin
dependencies. The editor view renders the same KG as safe forms and checklists
for Fachpersonal without exposing `value` fields.

## Current Executable Surface

| Surface | Status | Evidence |
| --- | --- | --- |
| Case-local KG files | Implemented | `usecases/*/knowledge-graph.graph.json`, `usecases/*/knowledge-graph.md` |
| KG validator | Implemented | `scripts/validate_knowledge_graph.py` |
| KG runtime package | Implemented | `src/notary_kg/` |
| BusinessCaseType S3 runtime | Done offline (#614) | Completion requires `business_case_type_get`, content-based catalog version, purpose-bound aliases, isolated caches, contracts, negative tests and strict validation; no Graph or tenant access in S3. |
| BusinessCaseType S4b Graph Write Edge | Done offline (#694) | Five bounded operations, separate `Sites.Selected`/`write` identity contract, dedupe, ETags, S5 hash binding, persistent reconciliation, and `business-case-type-write-dry-run`; live Graph calls and tenant writes remain zero, production composition and live write remain owner-gated. |
| BusinessCaseType S4c Graph Write Composition | Done offline (#698) | SQLite generation-CAS/evidence state, injected Graph REST v1.0 transport and synthetic credential port compose all five operations with crash/restart blocking; socket/DNS, external credential reads, live Graph and tenant writes remain zero. |
| BusinessCaseType S4d-S4g Production Edge | Done offline (#700/#702/#704/#708/#709) | Owner-bound live boundary, production-adapter readiness, exact identity inspection, trusted-local replay/evidence separation and create-only Azure Blob WORM REST are composed and verified offline. Central PostgreSQL evidence, broker, signature anchor, durable reconciliation, irreversible WORM lock and live activation remain blocked. |
| KG CLI | Implemented | `scripts/notary_kg.py`, `notary-kg` after package install |
| KG editor view | Implemented | `src/notary_kg/editor.py`, `schemas/kg-editor-patch.schema.json`, `workflows/contracts/kg-editor.contract.json` |
| Workflow contract draft generator | Implemented | `src/notary_kg/workflow_contract.py`, `nac kg workflow-contract <slug>`, `tests/test_notary_kg.py` |
| GmbH/UG pilot intake checklist | Implemented | `src/notary_kg/pilot_checklist.py`, `nac kg pilot-checklist online-gmbh-gruendung`, `tests/test_notary_kg.py` |
| XNP reader workflow gate | Implemented | `nac plugins xnp-workflow-gate --evidence out/xnp-reader-prompt.json`, `tests/test_xnp_workflow_gate.py` |
| Developer CI PR comment | Implemented | `scripts/render_quality_gate_comment.py`, `.github/workflows/quality-gate.yml`, `tests/test_render_quality_gate_comment.py` |
| Legal Graph source pilot | Implemented | `workflows/legal-graph/sources/*-primary-source.json`, `nac legal-graph sources`, `tests/test_legal_graph.py` |
| Legal Source Inventory CLI | Implemented | `nac legal-graph source-inventory`, `workflows/contracts/legal-source-inventory-license-tdm.contract.json`, `tests/test_legal_graph.py` |
| Legal Source Inventory review depth | Implemented | `review_depth` in `workflows/contracts/legal-source-inventory-license-tdm.contract.json`, `nac legal-graph source-inventory --format json` |
| Legal Graph contract validator | Implemented | `scripts/validate_legal_graph_contracts.py`, strict quality gate |
| Legal model customization gates | Implemented | `workflows/contracts/legal-research-connectors.contract.json`, `workflows/contracts/legal-model-customization-readiness.contract.json`, `workflows/contracts/legal-model-evaluation-benchmark.contract.json`, strict quality gate |
| Legal Model Card AI-SBOM Delta gate | Implemented | `workflows/contracts/legal-model-card-ai-sbom-delta.contract.json`, `scripts/validate_legal_model_card_ai_sbom_delta.py`, strict quality gate |
| Legal Model Card proposal status | Implemented | `workflows/legal-model/model-card-proposals/legal-nemotron-metadata-only.model-card.json`, `nac legal-graph model-card-proposal`, `scripts/validate_legal_model_card_proposal.py` |
| Legal AI-SBOM delta proposal status | Implemented | `workflows/legal-model/ai-sbom-deltas/legal-nemotron-metadata-only.ai-sbom-delta.json`, `nac legal-graph ai-sbom-delta-proposal`, `scripts/validate_legal_ai_sbom_delta_proposal.py` |
| AI-SBOM export mapping status | Implemented | `sbom/ai/nac-ai-sbom-export-mapping.json`, `nac ai-sbom export-mapping`, `scripts/validate_ai_sbom_export_mapping.py` |
| Unit tests | Implemented | `tests/test_notary_kg.py` |
| Strict quality gate | Active | `python scripts/quality_gate.py --profile strict` |
| Microsoft-first / on-prem AI target architecture | Planned baseline implemented | `docs/de/architecture/microsoft-first-onprem-target-architecture.md`, `workflows/contracts/microsoft-first-onprem-target-architecture.contract.json`, `scripts/validate_microsoft_first_onprem_target_architecture.py` |
| M365 MVP test environment in `notary_team_01` | Final BFF live closure pending (#620/#632) | The 2026-07-14 baseline one-shot passed site-scoped SPFx/Teams deployment plus synthetic Graph REST v1.0 write, readback and cleanup. The bounded BFF endpoint/scope/site grant exists; a current complete 12-step run, idempotency, full tamper matrix and SharePoint/Teams render evidence remain open. |
| SPFx roles and deadline cockpit | Implemented offline (#710) | Read-only roles/deputy state, explicit-time deadline traffic light, task filters, Current/Selected BPMN navigation, retry/empty states, container-responsive light/dark layout, 82 SPFx tests and six synthetic visual-contract evidence views; no tenant access or write path. |
| Azure Functions BFF for the M365 test environment | Final live closure pending (#620/#632) | Python/FastAPI, Entra validation, Graph v1.0 projection, deployment and bounded permissions are prepared. Close only after the current complete 12-step run, idempotency, tamper matrix and SharePoint/Teams render evidence pass. |

## Sprint 0 Development Board

| ID | Work item | Status | Done means |
| --- | --- | --- | --- |
| DEV-0001 | Case-local static KGs for Top-10, Next-10 and active intake usecases | Done | Every usecase folder has one JSON graph and one review Markdown file. |
| DEV-0002 | KG validator in strict quality gate | Done | `knowledge_graph` appears in strict quality output. |
| DEV-0003 | Executable KG status CLI | Done | CLI summarizes catalogs, cases and open nodes. |
| DEV-0004 | Case-level KG CLI view | Done | CLI returns one case by slug and fails unknown slugs. |
| DEV-0005 | No-code KG editor view and patch contract | Done | CLI returns four safe editor tabs, patch actions and blocked `value` fields. |
| DEV-0006 | Workflow contract generator from KG | Done | `nac kg workflow-contract <slug>` generates a draft contract skeleton for one case without real mandate data. |
| DEV-0007 | First pilot workflow: GmbH/UG formation | Done | `nac kg pilot-checklist online-gmbh-gruendung` reads the KG node and creates a deterministic intake checklist without real mandate data. |
| DEV-0008 | First plugin-bound workflow: XNP reader prompt gate | Done | `nac plugins xnp-workflow-gate` consumes `nac-bnotk-xnp` reader-prompt evidence without copying prompt text, secrets, PINs, card data or mandate data. |
| DEV-0009 | Developer CI comment renderer | Done | PR comments show build status, check summary and KG readiness from usecase-local graphs without mandate data. |
| DEV-0010 | Legal Graph primary-source pilot without commentary access | Done | `nac legal-graph sources` reports Erbrecht, Familienrecht and Gesellschaftsrecht as metadata-only, with commentary access, provider queries and credentials blocked. |
| DEV-0011 | Legal Nemotron fine-tuning source and evaluation plan | Done | Records NVIDIA Nemotron Legal, Rechtsquelle concept framing and `recht.bund.de` BGBl data access as metadata-only candidates, adds readiness and German-law benchmark contracts, and keeps fine-tuning, checkpoint publication and legal-answer use blocked before license/TDM, source hierarchy, evaluation, model-card, AI-SBOM and owner-apply gates are approved. |
| DEV-0012 | Legal source inventory CLI status | Done | `nac legal-graph source-inventory` reports source-inventory, license and TDM gate state without source-text ingestion, benchmark generation, model calls or training. |
| DEV-0013 | Legal model-card and AI-SBOM delta gate | Done | Strict quality gate validates that later Legal-Nemotron Model Card and AI-SBOM deltas cannot publish checkpoints, include placeholders, claim legal-answer quality, store source text or use mandate data before full evidence and owner apply. |
| DEV-0014 | Legal model-card artifact proposal | Done | `nac legal-graph model-card-proposal` reports a concrete metadata-only Legal-Nemotron Model-Card proposal with candidate references, required sections, attestations and blocked actions, without training, checkpoint publication, model evaluation, source-text storage or mandate data. |
| DEV-0015 | Legal AI-SBOM delta artifact proposal | Done | `nac legal-graph ai-sbom-delta-proposal` reports a concrete metadata-only Legal-Nemotron AI-SBOM delta proposal with components, candidates, attestations and blocked actions, without runtime activation, endpoint activation, training, checkpoint publication, source-text storage or mandate data. |
| DEV-0016 | AI-SBOM baseline export mapping | Done | `nac ai-sbom export-mapping` reports CycloneDX JSON and SPDX JSON target mappings for the repo-wide AI-SBOM baseline while release export, external SBOM tool execution, mandate data, secrets and release binding remain blocked before owner apply. |
| DEV-0017 | Legal source inventory review depth | Done | `nac legal-graph source-inventory --format json` now reports per-source review depth for seed metadata, license terms, TDM/bulk access, attribution, storage boundary and next required review while ingestion, benchmark generation, model evaluation, training and mandate data remain blocked. |
| DEV-0018 | BusinessCaseType S3 offline runtime | Done offline (#614) | `AC-S3-01` through `AC-S3-06`, contracts, CLI, validator, negative tests, strict gate, independent review and Protected PR checks pass without Graph, credentials or tenant access. |
| DEV-0019 | BusinessCaseType S4 Graph Read Edge | Done offline (#617) | `AC-S4-01` through `AC-S4-07`; exact `Sites.Selected` plus site grant `read`, same-filter paging, no collection `If-None-Match`, redaction/viewer isolation, offline CLI, contracts, validator and tests. |
| DEV-0020 | BusinessCaseType S5 offline migration | Done offline (#619) | Inventory dry run, exact legacy mapping, idempotent backfill planning, persistent quarantine, deterministic snapshots, stable final scans and N-1 replay pass without credentials, HTTP, Graph or tenant writes. |
| DEV-0021 | M365 MVP test environment live closure in `notary_team_01` | Final BFF live closure pending (#620/#632) | Preserve the passed 2026-07-14 baseline and close only after a current 12-step BFF run proves idempotency, assigned/deputy/deny plus workspace/matter/purpose/filter tamper rejection, SharePoint/Teams rendering and redacted evidence. |
| DEV-0022 | Azure Functions BFF offline deployment readiness | Ready offline (#620) | The central readiness command reports `READY`; source, token validation, fixed Graph adapters, Function package, Bicep, managed identity, CORS, storage network and health endpoints pass tests and validators without Azure, Entra or Graph writes. |
| DEV-0023 | BusinessCaseType S6b Azure Blob WORM adapter | Ready offline (#693) | On-prem publisher, authoritative tenant-bound Azure immutable evidence copy, version-bound create/conflict/readback, delete-free writer role, dedicated Bicep, offline lock contract, CLI, validator and tests; deployment and policy lock remain blocked. |
| DEV-0024 | BusinessCaseType S4b bounded Graph Write Edge | Done offline (#694) | Exactly five operations, separate `Sites.Selected`/`write` identity boundary, create deduplication, fresh ETags, S5 hash binding, persistent reconciliation, synthetic redacted CLI, contracts, validator and tests pass with zero credential reads, live factories, Graph calls or tenant writes. Production composition and live write remain owner-gated. |
| DEV-0025 | BusinessCaseType S4c offline write composition | Done offline (#698) | Local SQLite generation-CAS and redacted evidence, injected exact Graph REST v1.0 transport, credential port, five-operation composition smoke and crash/restart tests pass with zero socket/DNS, external credential reads, live Graph calls or tenant writes. Live identity, central durability and tenant execution remain owner-gated. |
| DEV-0026 | BusinessCaseType S4d live write boundary | Done offline (#700) | Owner/hash/target/principal gate, separate read-only inspection and `Sites.Selected/write` token factory ports, S6-v0.2 operation evidence, S6b Azure WORM composition and five-operation one-shot smoke pass offline. Production adapters and the first synthetic tenant write remain owner-gated. |
| DEV-0027 | BusinessCaseType S4e live write readiness | Done offline (#702) | Exact provisioning, writer and BFF identity requirements plus required production ports are executable as a fail-closed readiness assessment; no live authorization is produced. |
| DEV-0028 | BusinessCaseType S4f partial production adapters | Done offline (#704) | Exact owner verifier, certificate writer factory, redirect-free Graph REST and trusted-local SQLite evidence staging are implemented without central completion authority. |
| DEV-0029 | BusinessCaseType S4g production edge composition | Done offline (#709) | Redacted identity inspection, exact site roles, trusted-local database separation and strict Azure Blob WORM REST transport are composed; live activation remains blocked on the enumerated central controls. |
| DEV-0030 | SPFx role and deadline cockpit | Implemented offline (#710) | Pure explicit-time view model, assigned/deputy role visibility, task filters, Current/Selected BPMN consistency, fail-closed retry, responsive light/dark UI and versioned synthetic screenshot evidence; live tenant deployment is unchanged and separately gated. |

## Roadmap Review Notes

| Date | Topic | Decision | Follow-up trigger |
| --- | --- | --- | --- |
| 2026-06-16 | Fabro / Graphviz workflow orchestration | Not an active NaC roadmap item. Fabro complements the NaC BPMN line only as a possible future agentic execution and review harness; it does not replace BPMN 2.0 as the canonical subject-matter process source. | Revisit only if Codex Parallel Review, Time Ledger, Quality Gate or PR handoff work shows a repeated need for a durable external workflow engine. |
| 2026-06-28 | Legal Nemotron fine-tuning with public legal sources | Add as a gated roadmap track, not as an active training job. NVIDIA Nemotron Legal is an English CC-BY-4.0 pretraining dataset candidate, `Rechtsquelle` is a concept anchor for source hierarchy, and `recht.bund.de` is an official BGBl publication access path. | Continue only with source inventory, license/TDM review, model-card delta, AI-SBOM update, approved runnable config and owner apply approval; never use mandate data or treat generated answers as legal truth. |
| 2026-06-29 | Legal Nemotron gates after PRs 326-328 | Mark source candidates, readiness gates and German-law evaluation benchmark as implemented planning contracts. This closes the planning-board item without enabling training, dataset generation, checkpoint publication or legal-answer automation. | Next work item must be a separate gated contract or implementation PR for source inventory, model-card delta, AI-SBOM delta or approved benchmark generation. |
| 2026-06-29 | Immutable.js for editor state | Defer. Immutable.js can be reconsidered only as a future frontend/editor state tool for undo, redo, snapshots and deterministic proposal diffs; it is not an audit, governance, retention, WORM, signature or notarial truth layer. No dependency or architecture change now. | Revisit only when NaC starts a real React, BPMN-js or xyflow editor-sidecar implementation and can keep exported artifacts as canonical JSON, BPMN or XML with hash, validator, PR review and event-journal evidence. |
| 2026-06-30 | Legal Graph primary-source pilot status | Close DEV-0010 as implemented because the CLI exposes three metadata-only primary-source manifests and the Legal-Graph validator enforces no-commentary, no-fulltext, no-credential and review-gate boundaries. | Continue Legal Graph work only with a separate contract or implementation PR for source inventory depth, model-card delta, AI-SBOM delta, benchmark generation or licensed commentary connectors. |
| 2026-06-30 | Legal Source Inventory CLI status | Add a direct `nac legal-graph source-inventory` status surface for the existing source-inventory/license/TDM gate so the next Legal-Nemotron source review step is executable without ingestion. | Continue only with separate PRs for source inventory depth, model-card delta, AI-SBOM delta, approved benchmark generation or licensed commentary connector activation gates. |
| 2026-06-30 | Legal Model Card AI-SBOM delta | Add a strict, metadata-only gate for later Legal-Nemotron Model Card and AI-SBOM delta evidence without enabling training, evaluation execution, checkpoint publication or legal-answer quality claims. | Continue only with source inventory depth, approved benchmark generation, concrete model-card artifact proposal or AI-SBOM baseline update in separate PRs; owner apply remains required before any runtime, checkpoint or quality claim. |
| 2026-06-30 | Legal Model Card artifact proposal | Add the first concrete Legal-Nemotron Model-Card proposal artifact and CLI status, still metadata-only and blocked from training, evaluation, checkpoint publication, runtime activation or legal-answer quality claims. | Continue only with source inventory depth, approved benchmark generation, concrete AI-SBOM delta proposal or licensed commentary connector activation gates; owner apply remains required before any runtime, checkpoint or quality claim. |
| 2026-06-30 | Legal AI-SBOM delta artifact proposal | Add the first concrete Legal-Nemotron AI-SBOM delta proposal artifact and CLI status, still metadata-only and blocked from runtime activation, endpoint activation, training, evaluation, checkpoint publication or legal-answer quality claims. | Continue only with source inventory depth, approved benchmark generation, AI-SBOM baseline export mapping or licensed commentary connector activation gates; owner apply remains required before any runtime, checkpoint or quality claim. |
| 2026-06-30 | AI-SBOM baseline export mapping | Select CycloneDX JSON and SPDX JSON as machine-readable target profiles for the repo-wide AI-SBOM baseline and expose the status through CLI and strict quality gate. | Continue only with a separate owner-apply-gated release-binding PR; no external SBOM tooling, published release artifact, mandate data or secrets are enabled by this mapping. |
| 2026-06-30 | Legal Source Inventory review depth | Extend the source inventory from simple source status to per-source review depth without ingestion. | Continue with source-license/TDM evidence, approved benchmark generation or licensed commentary connector gates in separate PRs; owner apply remains required before any ingestion, corpus preparation, evaluation, training or release binding. |
| 2026-07-11 | Microsoft-first / on-prem AI target architecture | Teams, SPFx, SharePoint, Entra and Graph REST v1.0 form the Microsoft edge; Python/FastAPI, deterministic workflows, NeMo Agent Toolkit, PostgreSQL, outbox/broker and the evidence publisher remain on-prem; the authoritative WORM evidence copy is tenant-bound Azure Blob immutable storage. Temporal is a timeboxed candidate spike, not a selected platform. | Complete S3/S4, then run the durable-workflow spike before selecting an engine; live, credential and deployment actions remain separately owner-gated. |
| 2026-07-05 | M365 application-owned privileged change path | Add as the next iteration for the Teams/SharePoint data plane. Standard users stay least-privilege; Teams, SharePoint schema, site permission and membership mutations move behind a controlled provisioning app/API. Direct Graph app owners are users or service principals, so `technical_owner_user` or a service principal is the technical owner anchor while `nac_platform_admins` is the governance group. | Implement as a separate owner-gated PR: dedicated provisioning app, technical app owner anchor, governance group, Graph REST mutation API, `Sites.Selected` runtime grants, drift/export evidence and explicit audit records. |
| 2026-07-11 | BusinessCaseType S3 runtime | Start the viewer-independent offline runtime under Issue #612. CatalogVersion is content-based, runtime lifecycle is explicit, aliases are purpose-bound and registry/cache validation fails closed. | Mark implemented only after AC-S3-01 through AC-S3-06, contracts, CLI, validator, negative tests, strict gate, independent review and Protected PR checks pass; Graph REST integration remains S4. |
| 2026-07-14 | M365 MVP test environment live one-shot | Preserve the owner-approved `notary_team_01` baseline under #620; it did not verify the later BFF cutover. | Issue #632 supplied the bounded endpoint, `Matter.Read`, runtime `Sites.Selected` and site role `read`. Complete one current owner-gated 12-step closure run before marking #620 done. |
| 2026-07-29 | BusinessCaseType S4b bounded Graph Write Edge | Mark domain, plan, edge, synthetic redacted dry-run CLI, contracts, validator and tests as implemented offline under #694. This closes the offline write-edge implementation, not the productive path. | Production factory/credential composition, Entra/permission changes and every live Graph or SharePoint write require a separate owner-gated slice; keep the BFF UAMI at `Sites.Selected`/`read`. |
| 2026-07-29 | BusinessCaseType S4c offline write composition | Compose S4b with local SQLite generation-CAS/evidence state and injected exact Graph REST v1.0/token/HTTP ports under #698. The five-operation smoke proves restart safety without network or tenant access. | The next live slice must bind an owner-approved write identity and central evidence/durability choice; no tenant execution is implied by S4c. |
| 2026-07-29 | BusinessCaseType S4d live write boundary | Compose S4c with a cycle-free owner-plan binding, separate least-privilege write identity inspection/factory and complete S6/S6b evidence publication before local closure under #700. | Bind production identity, outbox, broker, signature and reconciliation adapters in one later owner gate, then execute exactly one synthetic write in `notary_team_01`; no broader workspace or permission change is implied. |

## Local Developer Commands

```bash
python scripts/quality_gate.py --profile strict
python scripts/validate_kg_editor.py
python scripts/validate_knowledge_graph.py
python scripts/nac.py legal-graph sources --format json
python scripts/nac.py legal-graph source-inventory --format json
python scripts/nac.py legal-graph model-card-proposal --format json
python scripts/nac.py legal-graph ai-sbom-delta-proposal --format json
python scripts/nac.py ai-sbom export-mapping --format json
python scripts/validate_legal_model_customization_readiness.py
python scripts/validate_legal_model_card_ai_sbom_delta.py
python scripts/validate_legal_model_card_proposal.py
python scripts/validate_legal_ai_sbom_delta_proposal.py
python scripts/validate_ai_sbom_export_mapping.py
python scripts/validate_legal_model_evaluation_benchmark.py
python scripts/notary_kg.py --repo-root . --format json status
python scripts/notary_kg.py --repo-root . --format json editor-view immobilienkaufvertrag
python scripts/notary_kg.py --repo-root . --format json workflow-contract immobilienkaufvertrag
python scripts/notary_kg.py --repo-root . --format json pilot-checklist online-gmbh-gruendung
python scripts/nac.py plugins xnp-workflow-gate --json
python scripts/render_quality_gate_comment.py --input out/quality/status.json --output out/quality/comment.md
```

## Rule

New conceptual work must be paired with at least one of these executable
changes:

- Python runtime code
- validator or quality gate coverage
- unit tests
- workflow contract scaffold
- plugin script or schema
- CI/reporting integration
