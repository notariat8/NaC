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

## Multilingual Maintenance

Language-specific content is maintained under ISO-639 folder codes:

- German: `docs/de/`, `prompts/de/`
- English: `docs/en/`, `prompts/en/`

`de` and `en` are mandatory. Every localized change must update both languages,
regardless of the language used in the prompt. The binding rule is defined in
`policies/language-policy.yaml` and checked by `scripts/validate_language_parity.py`.

## Repository Structure

- `docs/en/` contains English documentation.
- `docs/de/` contains German documentation.
- `prompts/en/` contains English prompt templates.
- `prompts/de/` contains German prompt templates.
- `roadmap/GANTT.md` tracks global progress for plugins, workflows, and usecases.
- `plugins/GANTT.md`, `workflows/GANTT.md`, and `usecases/GANTT.md` track area progress.
- `plugins/` contains installable plugin artifacts for GPT Store review or workspace installation.
- `workflows/` contains installable skills and deterministic Python workflows for notary-office operations.
- `usecases/` contains concrete notarial scenarios such as online GmbH formation, AO52 nonprofit software-company formation, real-estate purchase contracts, and testaments.
- `docs/en/gpt-marketplace-operating-model.md` separates public GPT Store, Actions, workspace app, and local plugin channels.
- `policies/` contains binding governance, technology, language, privacy, and role policies.
- `schemas/` defines structured process requests.
- `processes/` contains example business process instances.
- `src/business_os/` contains the Python engine.
- `.github/workflows/` contains governance and runtime workflows.
- `.cursor/rules/` and `.github/copilot-instructions.md` mirror agent-facing rules.

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

Every push must update `roadmap/GANTT.md`. Changes under `plugins/`,
`workflows/`, or `usecases/` must also update the matching area Gantt.

## Recommended Reading Order

1. `docs/en/START_HERE.md`
2. `docs/en/fachanwender-guide.md`
3. `docs/en/business-os.md`
4. `docs/en/governance.md`
5. `docs/en/quality-gate.md`

## Onboarding Prompts

- Law firm: `prompts/en/onboarding/law-firm-first-setup.md`
- Notary office: `prompts/en/onboarding/notary-first-setup.md`
- Property management: `prompts/en/onboarding/property-management-first-setup.md`
- Software company: `prompts/en/onboarding/software-company-first-setup.md`
- Tax office: `prompts/en/onboarding/tax-office-first-setup.md`
- Wealth management: `prompts/en/onboarding/wealth-management-first-setup.md`
- VS Code + Copilot: `prompts/en/onboarding/vscode-copilot-business-os-setup.md`
