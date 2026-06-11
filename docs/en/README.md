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
  authenticated web app, OCI Identity Domains, card gates and mobile secure document links.
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
- [docs/en/notarsoftware-datenmodell.md](notarsoftware-datenmodell.md) derives
  the open matter model from common notary-software building blocks.
- [qms/README.md](../../qms/README.md) defines the QMS/ISO 9001 layer with
  quality policy, objectives, audit program and evidence mapping.
- [docs/en/eventstream/](eventstream) contains event-journal, EventLock and cloud-runbook documentation.
- [docs/en/issues/](issues) contains issue taxonomy, issue operations and public backlog.
- [docs/en/operations/](operations) contains fork/release, upstream sync, version-binding and repository consolidation docs.
- [docs/en/service-model/](service-model) contains notarial scope, operating services, tenant and exit docs.
- [policies/](../../policies) contains binding governance, technology, language, privacy, and role policies.
- [schemas/](../../schemas) defines structured process requests.
- [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json) defines the implemented KG editor contract for the usecase-local knowledge graphs.
- [workflows/contracts/codex-parallel-review.contract.json](../../workflows/contracts/codex-parallel-review.contract.json) defines the contract for explicit parallel Codex reviews with read-only agent profiles and fresh validation.
- [workflows/contracts/secure-document-link.contract.json](../../workflows/contracts/secure-document-link.contract.json) defines the minimum boundary for mobile upload and read links to an object store, database blob or OneDrive.
- [processes/](../../processes) contains legacy runtime fixtures; product examples live only in [usecases/](../../usecases).
- [src/business_os/](../../src/business_os) contains the legacy deterministic process engine behind the NaC CLI.
- [.github/workflows/](../../.github/workflows) contains governance and runtime workflows.
- [.cursor/rules/](../../.cursor/rules) and [.github/copilot-instructions.md](../../.github/copilot-instructions.md) mirror agent-facing rules.

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
- VS Code + Copilot: [prompts/en/onboarding/vscode-copilot-notariat-setup.md](../../prompts/en/onboarding/vscode-copilot-notariat-setup.md)

The synchronous MVP path in this repository is `notary`. Subject-matter
examples are derived only from [usecases/](../../usecases).
