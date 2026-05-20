# VS Code + GitHub Copilot: Start Guide

## Goal

This guide shows how an organization can use this reference repository with
VS Code and GitHub Copilot instead of Cursor. The business frame is `Notariat
as Code` with `Enterprise GitOps`; `NaC` is the concrete implementation.

If you are a first-time user and do not want to read every document, use the
guided path:
`docs/en/vscode-first-user-path.md`

## Prerequisites

- minimum requirements from `docs/en/minimum-requirements.md` fulfilled
- GitHub organization or company account
- VS Code installed
- Git installed
- Python `>= 3.11`
- GitHub CLI `gh` installed and authenticated
- Node.js/npm for plugin development
- Active GitHub Copilot license

## Setup

1. Create your own company repository.
2. Use this repository as the base version, either as a template or fork.
3. Open the repository in VS Code.
4. Install and activate GitHub Copilot in the editor.
5. Read `docs/en/START_HERE.md` and `docs/en/minimum-requirements.md`.
6. Run `python scripts/startup_check.py --profile base --ide vscode --run-tests`.
   For plugin development, also run `python scripts/startup_check.py --profile plugin-dev --ide vscode`.
   For card-reader, morris or XNP-adjacent work, also run `python scripts/startup_check.py --profile notary-workstation --ide vscode`.
7. Confirm the policies under `policies/`.
8. Use an onboarding prompt from `prompts/en/onboarding/` for your industry.
   The MVP defaults in this repository are `software_company`, `notary`, and
   `wealth_management`; the additional MVP usecase is `property_management`.
9. Start with a pilot process and verify the pull-request workflow.
10. Roll out more broadly only after the pilot succeeds.
11. Define fork, sync, and mixed-version operation through the operating
   documents in `docs/en/`.
12. Review the product structure: `plugins/` for installable artifacts,
    `workflows/` for skills and Python workflows, and `usecases/` for concrete
    notarial usecases.
13. Update `roadmap/GANTT.md` only when roadmap, scope, status, milestone or
    build-board state changes; when changing `plugins/`, `workflows/`, or
    `usecases/`, update the matching area Gantt only when area scope, status or
    milestones are affected.
14. For AI-enabled changes, review `docs/en/sbom-for-ai.md` and update
    `sbom/ai/nac-ai-sbom-draft.json`.

## Recommended Copilot Start Prompt

```text
Read these files first and then explain the next 3 steps without IT jargon:
- docs/en/START_HERE.md
- docs/en/fachanwender-guide.md
- policies/process-policy.yaml
- policies/culture-policy.yaml
- policies/technology-policy.yaml

Then:
1) Ask me for company type and priority processes.
2) Suggest matching industry modules.
3) Create a 30-day pilot plan for team, role, and access processes.
```

## Operating Rules

- Process changes only through pull requests.
- Always include review for sensitive steps.
- Document every change with purpose, risk, and owner.
- For open-scope, issue-driven work or multiple relevant solution paths, explore first, provide a short plan with purpose and risk, and ask for confirmation before editing code.
- For clear, narrowly scoped changes, direct implementation is allowed; assumptions and validation must still remain visible.
- Code changes need test or validation evidence; for non-trivial behavior, record the test, check objective or known test gap first, then implement, iterate and validate again.
- UI, frontend and other visual changes need a screenshot or comparable visual evidence before completion.
- Approval-required commands must state purpose, scope and task relevance; unclear approval requests are declined and restated concretely.
- Roadmap, scope, status, milestone or build-board changes need an updated
  global Gantt; area Gantts are needed only when area scope, status or
  milestones are affected.
- AI-enabled plugins, workflows, usecases, prompts or external model calls need
  an AI-SBOM decision.
- Local runtime, hardware and middleware dependencies must be maintained in the
  SBOM/AI-SBOM according to `docs/en/minimum-requirements.md`.
- Follow the culture and language rules from `policies/culture-policy.yaml`.

## If The Pattern Does Not Fit

- Record the deviation as a change request.
- Test the new variant in a pilot.
- Adopt it into your company model with a version reference.
- Optionally contribute proven improvements back to the reference pattern.

## Operating Documents For Company Forks

- `docs/en/operations/fork-and-release-operating-model.md`
- `docs/en/operations/release-sync-playbook.md`
- `docs/en/operations/parallelbetrieb-version-binding.md`
- `docs/en/issues/taxonomy.md`
- `docs/en/einfuehrung-greenfield-brownfield.md`
- `docs/en/service-model/core-vertical-blueprint.md`
- `docs/en/service-model/vertical-starter-process-catalog.md`
- `docs/en/operations/single-repo-refactor-plan.md`
- `docs/en/operations/agile-cadence.md`
- `docs/en/issues/operations.md`
