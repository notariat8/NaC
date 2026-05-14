# START HERE: Introduction Without IT Background

## Purpose

This document helps decision makers use this reference repository as a starting
point for their own Business OS. You do not need to read every Markdown file
before starting.

## Conceptual Frame

- The target model is `Notariat as Code (NoC)`.
- The operating model is `Enterprise GitOps`.
- `NoC` is the implementation in this repository.
- The platform name is `Enterprise Control Plane`.

## Multilingual Rule

This repository is maintained in ISO-639 language folders:

- German: `docs/de/`, `prompts/de/`
- English: `docs/en/`, `prompts/en/`

`de` and `en` are mandatory. Every localized change must update both languages,
regardless of the language used in the prompt.

## First Steps

1. Create your own company repository.
2. Use this repository as the starting version.
3. Define roles for proposal, review, and approval.
4. Confirm the active industry modules in `policies/process-policy.yaml`.
5. Confirm culture, language, technology, privacy, and role policies.
6. Run the local startup check from `docs/en/startup-verification.md`.
7. Start the matching onboarding prompt under `prompts/en/onboarding/`.
8. Run a pilot with 1-2 core processes before full rollout.
9. Define the operating model using `docs/en/fork-and-release-operating-model.md`.
10. Define release sync and mixed-version operation using the related runbooks.

## Available Onboarding Prompts

- `prompts/en/onboarding/law-firm-first-setup.md`
- `prompts/en/onboarding/notary-first-setup.md`
- `prompts/en/onboarding/property-management-first-setup.md`
- `prompts/en/onboarding/software-company-first-setup.md`
- `prompts/en/onboarding/tax-office-first-setup.md`
- `prompts/en/onboarding/wealth-management-first-setup.md`
- `prompts/en/onboarding/vscode-copilot-business-os-setup.md`
- `prompts/en/onboarding/vscode-first-user-assistant.md`

## Change Requests and Learning

- An update is complete only after the change has been validated, committed, pushed to GitHub, and merged into the target branch. Local changes and unmerged PR branches are only work in progress.
- Every improvement is documented as a change request.
- Every change gets a rationale, review, and version reference.
- Useful local improvements can flow back into the reference standard.
