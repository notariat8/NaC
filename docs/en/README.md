# NoC: Notariat as Code with Enterprise Control Plane

This repository shows how an organization can be operated as a declarative,
versioned system. Users express business intent through an LLM frontend, while
Git, pull requests, reviews, GitHub Actions, and deterministic Python checks
provide the binding process control.

## Core Idea

- The LLM turns natural-language requests into structured process requests.
- Git represents the official lifecycle of a business change.
- Python validates rules and runs repeatable deterministic checks.
- GitHub Actions orchestrate checks, approvals, scheduled jobs, and artifacts.

## Project Positioning

This repository is the active project state for `Notariat as Code` with `NoC`
as the concrete Enterprise Control Plane.

Binding positioning:

- Term: `Notariat as Code`
- Platform name: `Enterprise Control Plane`
- First product promise: "Notarial case types, plugins, workflows, roles,
  approvals and evidence run declaratively, auditable and automated through
  Git."
- Current development state: [roadmap/BUILD_NOW.md](../../roadmap/BUILD_NOW.md)

One-sentence pitch:

Notariat as Code is an operating model in which notarial case types, plugins,
workflows, policies and operational changes are described declaratively in Git
and moved into verifiable execution through an Enterprise Control Plane.

## Multilingual Maintenance

Language-specific content is maintained under ISO-639 folder codes:

- German: [docs/de/](../de), [prompts/de/](../../prompts/de)
- English: [docs/en/](.), [prompts/en/](../../prompts/en)

`de` and `en` are mandatory. Every localized change must update both languages,
regardless of the language used in the prompt. The binding rule is defined in
[policies/language-policy.yaml](../../policies/language-policy.yaml) and checked by [scripts/validate_language_parity.py](../../scripts/validate_language_parity.py).

## Repository Structure

- [docs/en/](.) contains English documentation.
- [docs/de/](../de) contains German documentation.
- [prompts/en/](../../prompts/en) contains English prompt templates.
- [prompts/de/](../../prompts/de) contains German prompt templates.
- [roadmap/GANTT.md](../../roadmap/GANTT.md) tracks global progress for plugins, workflows, and usecases.
- [plugins/GANTT.md](../../plugins/GANTT.md), [workflows/GANTT.md](../../workflows/GANTT.md), and [usecases/GANTT.md](../../usecases/GANTT.md) track area progress.
- [plugins/](../../plugins) contains installable plugin artifacts for GPT Store review or workspace installation.
- [workflows/](../../workflows) contains installable skills and deterministic Python workflows for notary-office operations.
- [usecases/](../../usecases) contains concrete notarial scenarios such as online GmbH formation, AO52 nonprofit software-company formation, real-estate purchase contracts, and testaments. Each usecase owns its own KG/DB structure as `knowledge-graph.graph.json` and `knowledge-graph.md` in the matching usecase folder.
- [docs/en/gpt-marketplace-operating-model.md](gpt-marketplace-operating-model.md) separates public GPT Store, Actions, workspace app, and local plugin channels.
- [docs/en/minimum-requirements.md](minimum-requirements.md) defines minimum requirements for the base workspace, plugin development and local notary workstation.
- [docs/en/datenschutz-avv-dpa.md](datenschutz-avv-dpa.md) defines the AVV/DPA section for OpenAI-backed processing.
- [docs/en/sbom-for-ai.md](sbom-for-ai.md) defines the repository-wide AI-SBOM track aligned with BSI/G7 guidance.
- [docs/en/kg-editor-workstream.md](kg-editor-workstream.md) defines the no-code KG editor,
  patch principle and sidecar-editor path for subject-matter staff.
- [docs/en/eventstream/](eventstream) contains event-journal, EventLock and cloud-runbook documentation.
- [docs/en/issues/](issues) contains issue taxonomy, issue operations and public backlog.
- [docs/en/operations/](operations) contains fork/release, upstream sync, version-binding and repository consolidation docs.
- [docs/en/service-model/](service-model) contains core/vertical, provider, tenant and exit docs.
- [policies/](../../policies) contains binding governance, technology, language, privacy, and role policies.
- [schemas/](../../schemas) defines structured process requests.
- [workflows/contracts/kg-editor.contract.json](../../workflows/contracts/kg-editor.contract.json) defines the implemented KG editor contract for the usecase-local knowledge graphs.
- [processes/](../../processes) contains example business process instances.
- [src/business_os/](../../src/business_os) contains the Python engine.
- [.github/workflows/](../../.github/workflows) contains governance and runtime workflows.
- [.cursor/rules/](../../.cursor/rules) and [.github/copilot-instructions.md](../../.github/copilot-instructions.md) mirror agent-facing rules.

## Quick Start

```bash
python -m business_os validate processes/invoices/2026/REQ-2026-0001.json
python -m business_os render-summary processes/invoices/2026/REQ-2026-0001.json
python -m business_os monthly-close --year 2026 --month 3
```

For a full local gate:

```bash
python scripts/quality_gate.py --profile strict
```

Every push must update [roadmap/GANTT.md](../../roadmap/GANTT.md). Changes under [plugins/](../../plugins),
[workflows/](../../workflows), or [usecases/](../../usecases) must also update the matching area Gantt.

## Recommended Reading Order

1. [docs/en/START_HERE.md](START_HERE.md)
2. [docs/en/fachanwender-guide.md](fachanwender-guide.md)
3. [docs/en/business-os.md](business-os.md)
4. [docs/en/governance.md](governance.md)
5. [docs/en/quality-gate.md](quality-gate.md)

## Onboarding Prompts

- Law firm: [prompts/en/onboarding/law-firm-first-setup.md](../../prompts/en/onboarding/law-firm-first-setup.md)
- Notary office: [prompts/en/onboarding/notary-first-setup.md](../../prompts/en/onboarding/notary-first-setup.md)
- Property management: [prompts/en/onboarding/property-management-first-setup.md](../../prompts/en/onboarding/property-management-first-setup.md)
- Software company: [prompts/en/onboarding/software-company-first-setup.md](../../prompts/en/onboarding/software-company-first-setup.md)
- Tax office: [prompts/en/onboarding/tax-office-first-setup.md](../../prompts/en/onboarding/tax-office-first-setup.md)
- Wealth management: [prompts/en/onboarding/wealth-management-first-setup.md](../../prompts/en/onboarding/wealth-management-first-setup.md)
- VS Code + Copilot: [prompts/en/onboarding/vscode-copilot-business-os-setup.md](../../prompts/en/onboarding/vscode-copilot-business-os-setup.md)
