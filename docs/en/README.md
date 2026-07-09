# NaC: Notariat as Code with Enterprise Control Plane

This repository shows how a notary office can operate notarial case types as a
declarative, versioned and checkable system. Users express subject-matter
intent through an LLM frontend, while Git, pull requests, reviews, GitHub
Actions and deterministic Python checks provide the binding process control.

## Core Idea

- The LLM turns natural-language requests into structured notarial requests.
- Git represents the official lifecycle of a notarial matter or change.
- Python validates rules and runs repeatable deterministic checks.
- GitHub Actions orchestrate checks, approvals, scheduled jobs, and artifacts.

## Project Positioning

This repository is the active project state for `Notariat as Code` with `NaC`
as the concrete Enterprise Control Plane.

Binding positioning:

- Term: `Notariat as Code`
- Platform name: `Enterprise Control Plane`
- First product promise: "Notarial case types, plugins, workflows, roles,
  approvals and evidence run declaratively, auditable and automated through
  Git."
- Current development state: [roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md)
- Rule architecture and rule hardness: [docs/en/regelarchitektur.md](regelarchitektur.md)

One-sentence pitch:

Notariat as Code is an operating model in which notarial case types, plugins,
workflows, policies and operational changes are described declaratively in Git
and moved into verifiable execution through an Enterprise Control Plane.

## Audience Entry Paths

| Audience | Start path |
| --- | --- |
| Notary office and business decision | [docs/en/notar-start.md](notar-start.md) |
| Office admin and IT operations | [docs/en/betriebsstart.md](betriebsstart.md) |
| System and integration side | [docs/en/integration-start.md](integration-start.md) |
| Review and standardization | [docs/en/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md) |
| Development and maintainers | [docs/en/START_HERE.md](START_HERE.md) |

Quick orientation: [docs/en/cli.md](cli.md), [docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md),
[docs/en/reifegrad.md](reifegrad.md), [docs/en/glossar.md](glossar.md) and
[docs/en/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md).

## Multilingual Maintenance

Language-specific content is maintained under ISO-639 folder codes. This
English overview links only to English localized reading paths; German remains
the leading source language in its own path.

- English: [docs/en/](.), [prompts/en/](../../prompts/en)

`de` and `en` are mandatory. Every localized change must update both languages,
regardless of the language used in the prompt. The binding rule is defined in
[policies/language-policy.yaml](../../policies/language-policy.yaml) and checked by [scripts/validate_language_parity.py](../../scripts/validate_language_parity.py).

## Repository Structure

- [docs/en/](.) contains English documentation.
- [docs/en/notar-start.md](notar-start.md) is the business entry path for notary offices and decision makers.
- [docs/en/betriebsstart.md](betriebsstart.md) covers private fork setup, local checks and operating boundaries.
- [docs/en/integration-start.md](integration-start.md) covers system, plugin and connector integration.
- [docs/en/pruefung-standardisierung-start.md](pruefung-standardisierung-start.md) covers review and standardization traceability.
- [docs/en/ausfuehrungsmodell.md](ausfuehrungsmodell.md) explains how the
  office UI and the checkable NaC core work together.
- [docs/en/authenticated-webapp-operating-model.md](authenticated-webapp-operating-model.md)
  defines the target model for GitHub Pages as a static reading layer, the
  authenticated web app, Entra ID/M365 binding, card gates and mobile secure document links.
- [docs/en/cli.md](cli.md) explains the technical `nac` control surface behind
  the office UI, first commands and the architecture rule for new functionality.
- [docs/en/bpmn-js-business-layer.md](bpmn-js-business-layer.md) explains why
  the business layer becomes BPMN-first, bpmn-js-edited and Python-validated.
- [docs/en/lokaler-webserver.md](lokaler-webserver.md) describes the local entry
  point for graphical BPMN and KG outputs.
- [docs/en/webapp-ohne-zugriff.md](webapp-ohne-zugriff.md) explains the
  operator web app with screenshots for readers without local web-app access.
- [docs/en/reifegrad.md](reifegrad.md) separates usable today, pilot-ready, planned and deliberately blocked surfaces.
- [docs/en/glossar.md](glossar.md) explains terms for non-technical readers.
- [docs/en/beispiel-immobilienkaufvertrag.md](beispiel-immobilienkaufvertrag.md) shows one full case without real mandate data.
- [prompts/en/](../../prompts/en) contains English prompt templates.
- [roadmap/GANTT.md](../../roadmap/GANTT.md) tracks global progress for plugins, workflows, and usecases.
- [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md), and [usecases/GANTT.md](../../usecases/GANTT.md) track area progress.
- [plugins/](../../plugins) contains installable plugin artifacts for GPT Store review or workspace installation.
- [workflows/](../../workflows) contains installable skills and deterministic Python workflows for notary-office operations.
- [usecases/](../../usecases) contains concrete notarial scenarios such as online GmbH formation, real-estate purchase contracts, commercial-register filings, and testaments. Each usecase owns its own KG/DB structure as `knowledge-graph.graph.json` and `knowledge-graph.md` in the matching usecase folder.
- [docs/en/gpt-marketplace-operating-model.md](gpt-marketplace-operating-model.md) separates public GPT Store, Actions, workspace app, and local plugin channels.
- [docs/en/minimum-requirements.md](minimum-requirements.md) defines minimum requirements for the base workspace, plugin development and local notary workstation.
- [docs/en/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md) defines the AVV/DPA section for OpenAI-backed processing.
- [docs/en/openai-enterprise-eu-residency.md](openai-enterprise-eu-residency.md)
  defines the procurement and approval path for ChatGPT Enterprise, API EU data
  residency and Codex costs.
- [docs/en/itil5-mapping.md](itil5-mapping.md) maps NaC to ITIL 5 as operating,
  review and audit language without claiming certification.
- [docs/en/sbom-for-ai.md](sbom-for-ai.md) defines the repository-wide AI-SBOM track aligned with BSI/G7 guidance.
- [docs/en/kg-editor-workstream.md](kg-editor-workstream.md) defines the no-code KG editor,
  patch principle and sidecar-editor path for subject-matter staff.
- [docs/en/codex-parallel-review-workflow.md](codex-parallel-review-workflow.md)
  defines explicit parallel review with read-only Codex agents for KG, BPMN,
  governance, documentation parity, and validation.
- [docs/en/datenrepo-demo8notariat.md](datenrepo-demo8notariat.md) defines the
  separate demo data repository for synthetic NaC cases and a later sovereign Git move.
- [docs/en/demo/](demo/) is the Notarkammer demo entry point with preflight,
  live runbook, 60-minute script, XNP/BPMN boundaries and fallbacks.
- [docs/en/notarsoftware-datenmodell.md](notarsoftware-datenmodell.md) derives
  the open matter model from common notary-software building blocks.
- [docs/en/architecture/nemoclaw-operating-model.md](architecture/nemoclaw-operating-model.md)
  defines the work split between Project Manager, `brev01` development and
  `notoclaw01` target operation.
- [docs/en/architecture/nac-onprem-agent-runtime.md](architecture/nac-onprem-agent-runtime.md)
  is the archived legacy target-system contract for the OCI-bound NaC on-prem
  agent runtime; it is not part of the active M365 MVP path.
- [docs/en/architecture/nemo-agent-toolkit-aiq-m365.md](architecture/nemo-agent-toolkit-aiq-m365.md)
  defines the productive agentic runtime decision for NVIDIA NeMo Agent
  Toolkit / AI-Q, Microsoft 365 MCP servers and local workstation sidecars.
- [docs/en/architecture/teams-sharepoint-graph-data-plane.md](architecture/teams-sharepoint-graph-data-plane.md)
  defines the closed M365 / SharePoint MVP infrastructure baseline through
  Teams, Microsoft 365 group, SharePoint team site and Microsoft Graph REST
  without legacy SharePoint APIs or SDKs.
- [docs/en/architecture/m365-matter-access-delegation.md](architecture/m365-matter-access-delegation.md)
  defines M365 Matter Access Delegation for matter assignment, deputy grants,
  audit and `matter-access-plan` without live tenant action.
- [docs/en/architecture/m365-sharepoint-bpmn-viewer-adapter.md](architecture/m365-sharepoint-bpmn-viewer-adapter.md)
  defines the contract-first boundary for a later read-only SPFx BPMN viewer
  in SharePoint with `bpmn-js`, Microsoft Graph REST and no modeler or workflow
  execution.
- [docs/en/architecture/omnigraph-ontology-projection.md](architecture/omnigraph-ontology-projection.md)
  records the decision note for Omnigraph as a later optional ontology
  projection, not as MVP storage and not as a BPMN engine.
- [docs/en/architecture/notarial-ontology-sizing-storage.md](architecture/notarial-ontology-sizing-storage.md)
  defines the ontology sizing and storage boundary from the business-case
  inventory with SharePoint as operative MVP storage, ontology as a versioned
  projection and Graph REST as the only M365 data plane.
- [docs/en/architecture/notarial-ontology-scale-budget.md](architecture/notarial-ontology-scale-budget.md)
  defines the offline scale smoke across all business cases, BPMN sources and
  ontology projection budgets so deep modeling does not run into performance
  limits without sizing.
- [docs/en/architecture/notarial-deep-process-candidate-routing.md](architecture/notarial-deep-process-candidate-routing.md)
  routes high/medium complexity cases from the sizing contract into first-wave,
  archetype, backlog and legacy-dedupe lanes for deep BPMN and ontology
  modeling.
- [docs/en/architecture/first-wave-bpmn-outline.md](architecture/first-wave-bpmn-outline.md)
  defines the offline outline contract for the four first-wave cases with BPMN
  source, usecase-local KG, ontology projection plan and SharePoint field-gap
  plan without live apply.
- [docs/en/architecture/first-wave-bpmn-outline-gap-review.md](architecture/first-wave-bpmn-outline-gap-review.md)
  defines the offline gap review for first-wave outlines against SharePoint
  field gaps, BPMN gaps and ontology projection patch plans without live apply.
- [docs/en/runbooks/m365-cli-admin-accelerator.md](runbooks/m365-cli-admin-accelerator.md)
  defines the owner-gated CLI for Microsoft 365 admin runbook for Graph-only
  setup and smoke tests.
- [docs/en/architecture/agent-runtime-registry.md](architecture/agent-runtime-registry.md)
  is the archived legacy ATP-backed agent registry; it is not active MVP
  storage.
- [docs/en/architecture/agent-control-api.md](architecture/agent-control-api.md)
  is the archived legacy OCI/BFF API boundary for `agent.notariat8.de`.
- [docs/en/architecture/notarial-onprem-connector-boundaries.md](architecture/notarial-onprem-connector-boundaries.md)
  defines notarial on-prem connector boundaries for XNP/SNP, XNotar,
  cyberJack/card workstation, registers and land registers without live apply.
- [docs/en/architecture/matter-data-classification-redaction.md](architecture/matter-data-classification-redaction.md)
  defines matter-data classification and redaction boundaries for GitHub,
  web-app status, archived ATP metadata and later private runtime stores.
- [docs/en/architecture/private-operating-frame-gate.md](architecture/private-operating-frame-gate.md)
  defines the private operating frame and private-payload gate before real
  matter-data processing.
- [docs/en/architecture/private-payload-target-design.md](architecture/private-payload-target-design.md)
  defines the logical envelope/pointer target model for later private payloads
  without apply.
- [docs/en/architecture/private-payload-access-policy.md](architecture/private-payload-access-policy.md)
  defines the role, purpose and access matrix for later private payloads
  without live access.
- [docs/en/architecture/legal-model-customization-readiness.md](architecture/legal-model-customization-readiness.md)
  defines the readiness contract for later Legal-Nemotron model customization
  without starting training.
- [docs/en/architecture/legal-source-inventory-license-tdm.md](architecture/legal-source-inventory-license-tdm.md)
  defines the source-inventory, license and TDM gate for later Legal-Nemotron
  or legal-graph work without source-text ingestion.
- [docs/en/architecture/legal-model-evaluation-benchmark.md](architecture/legal-model-evaluation-benchmark.md)
  defines the benchmark blueprint for later Legal-Nemotron evaluations without
  generating a benchmark dataset, running a model or claiming legal quality.
- [qms/README.md](../../qms/README.md) defines the QMS/ISO 9001 layer with
  quality policy, objectives, audit program and evidence mapping.
- [docs/en/eventstream/](eventstream) contains event-journal, EventLock and cloud-runbook documentation.
- [docs/en/issues/](issues) contains issue taxonomy, issue operations and public backlog.
- [docs/en/operations/](operations) contains fork/release, upstream sync, version-binding and repository consolidation docs.
- [docs/en/operations/ponytail-skill-only-smoke.md](operations/ponytail-skill-only-smoke.md)
  records the owner-gated Ponytail skill-only smoke on `notoclaw01` without
  installation, hooks or runtime activation.
- [docs/en/service-model/](service-model) contains notarial scope, operating services, tenant and exit docs.
- [policies/](../../policies) contains binding governance, technology, language, privacy, and role policies.
- [schemas/](../../schemas) defines structured process requests.
- [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json) defines the implemented KG editor contract for the usecase-local knowledge graphs.
- [workflows/contracts/codex-parallel-review.contract.json](../../workflows/contracts/codex-parallel-review.contract.json) defines the contract for explicit parallel Codex reviews with read-only agent profiles and fresh validation.
- [workflows/contracts/nac-onprem-agent-runtime.contract.json](../../workflows/contracts/nac-onprem-agent-runtime.contract.json) is archived as the legacy contract for the inactive OCI-bound on-prem agent runtime.
- [workflows/contracts/agent-runtime-registry.contract.json](../../workflows/contracts/agent-runtime-registry.contract.json) is archived as the legacy contract for the inactive ATP-backed agent registry.
- [workflows/contracts/agent-control-api.contract.json](../../workflows/contracts/agent-control-api.contract.json) is archived as the legacy contract for the inactive OCI/BFF API boundary.
- [workflows/contracts/notarial-onprem-connector-boundaries.contract.json](../../workflows/contracts/notarial-onprem-connector-boundaries.contract.json) defines XNP/SNP, XNotar, card-workstation, register and land-register paths as local readiness and redacted evidence boundaries.
- [workflows/contracts/matter-data-classification-redaction.contract.json](../../workflows/contracts/matter-data-classification-redaction.contract.json) defines matter-data classification, redaction evidence and storage boundaries between GitHub, web-app status, archived ATP metadata and the private operating frame.
- [workflows/contracts/private-operating-frame-gate.contract.json](../../workflows/contracts/private-operating-frame-gate.contract.json) defines the gate contract for later private payloads with privacy, role, storage, encryption, retention, audit and owner gates.
- [workflows/contracts/private-payload-target-design.contract.json](../../workflows/contracts/private-payload-target-design.contract.json) defines the logical envelope/pointer target model for private payloads without a DDL artifact, apply or private example data.
- [workflows/contracts/private-payload-access-policy.contract.json](../../workflows/contracts/private-payload-access-policy.contract.json) defines roles, purposes, access matrix, step-up, human review, audit and global denials for later private payloads without live access.
- [workflows/contracts/secure-document-link.contract.json](../../workflows/contracts/secure-document-link.contract.json) defines the minimum boundary for mobile upload and read links to an object store, database blob or OneDrive.
- [workflows/contracts/legal-model-customization-readiness.contract.json](../../workflows/contracts/legal-model-customization-readiness.contract.json) defines source, license, benchmark, evaluation, model-card, AI-SBOM and owner-apply gates for later Legal-Nemotron customization.
- [workflows/contracts/legal-source-inventory-license-tdm.contract.json](../../workflows/contracts/legal-source-inventory-license-tdm.contract.json) defines source-inventory, license and TDM gates before any source-text ingestion, benchmark generation, evaluation or model customization.
- [workflows/contracts/legal-model-evaluation-benchmark.contract.json](../../workflows/contracts/legal-model-evaluation-benchmark.contract.json) defines source hierarchy, holdout rules, task families and BYOB/MCQ plus `eval/model_eval` routing for later Legal-Nemotron evaluations without a benchmark dataset or model run.
- [processes/](../../processes) contains legacy runtime fixtures; product examples live only in [usecases/](../../usecases).
- [src/business_os/](../../src/business_os) contains the legacy deterministic process engine behind the NaC CLI.
- [.github/workflows/](../../.github/workflows) contains governance and runtime workflows.
- [AGENTS.md](../../AGENTS.md) and [.codex/agents/](../../.codex/agents) mirror Codex-facing rules.
- [docs/en/agent-context/README.md](agent-context/README.md) and
  [agent-context/index.json](../../agent-context/index.json) describe
  progressive disclosure, agent-readable maps/history/guardrails and
  verification contracts.

## Quick Start

```bash
python scripts/nac.py status
python scripts/nac.py kg case immobilienkaufvertrag
python scripts/nac.py bpmn show immobilienkaufvertrag
python scripts/nac.py bpmn validate
```

For a full local gate:

```bash
python scripts/nac.py doctor --profile strict
```

[roadmap/GANTT.md](../../roadmap/GANTT.md) is updated for roadmap, scope, status,
milestone or build-board changes. Changes under [plugins/](../../plugins),
[workflows/](../../workflows), or [usecases/](../../usecases) update the
matching area Gantt only when area scope, status or milestones are affected.

## License And Attribution

NaC uses a split open-source licensing model:

- Code, plugins, workflows, validators, schemas, and runnable examples:
  `AGPL-3.0-or-later`
- Documentation, diagrams, policies, roadmap material, prompts, and notarial
  usecases: `CC-BY-4.0`

The binding mapping is documented in [LICENSES/README.md](../../LICENSES/README.md).
Please preserve attribution from [NOTICE](../../NOTICE), [AUTHORS.md](../../AUTHORS.md),
and [CITATION.cff](../../CITATION.cff). Trademark and naming boundaries are
documented in [TRADEMARK.md](../../TRADEMARK.md).

## Recommended Reading Order

1. [docs/en/START_HERE.md](START_HERE.md)
2. [docs/en/fachanwender-guide.md](fachanwender-guide.md)
3. [docs/en/notariat-as-code.md](notariat-as-code.md)
4. [docs/en/governance.md](governance.md)
5. [docs/en/quality-gate.md](quality-gate.md)

## Notary-Office Onboarding

- Notary office: [prompts/en/onboarding/notary-first-setup.md](../../prompts/en/onboarding/notary-first-setup.md)
The synchronous MVP path in this repository is `notary`. Subject-matter
examples are derived only from [usecases/](../../usecases).
