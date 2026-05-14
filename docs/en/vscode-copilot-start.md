# VS Code + GitHub Copilot: Start Guide

## Goal

This guide shows how an organization can use this reference repository with
VS Code and GitHub Copilot instead of Cursor. The business frame is `Notariat
as Code` with `Enterprise GitOps`; `NoC` is the concrete implementation.

If you are a first-time user and do not want to read every document, use the
guided path:
`docs/en/vscode-first-user-path.md`

## Prerequisites

- GitHub organization or company account
- VS Code installed
- Git installed
- Active GitHub Copilot license

## Setup

1. Create your own company repository.
2. Use this repository as the base version, either as a template or fork.
3. Open the repository in VS Code.
4. Install and activate GitHub Copilot in the editor.
5. Read `docs/en/START_HERE.md` and confirm the policies under `policies/`.
6. Use an onboarding prompt from `prompts/en/onboarding/` for your industry.
   The MVP defaults in this repository are `software_company`, `notary`, and
   `wealth_management`; the additional MVP usecase is `property_management`.
7. Start with a pilot process and verify the pull-request workflow.
8. Roll out more broadly only after the pilot succeeds.
9. Define fork, sync, and mixed-version operation through the operating
   documents in `docs/en/`.
10. Review the product structure: `plugins/` for installable artifacts,
    `workflows/` for skills and Python workflows, and `usecases/` for concrete
    notarial usecases.
11. Before every push, update `roadmap/GANTT.md`; when changing `plugins/`,
    `workflows/`, or `usecases/`, update the matching area Gantt as well.

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
- Every push needs an updated global Gantt; area changes also need the matching
  area Gantt.
- Follow the culture and language rules from `policies/culture-policy.yaml`.

## If The Pattern Does Not Fit

- Record the deviation as a change request.
- Test the new variant in a pilot.
- Adopt it into your company model with a version reference.
- Optionally contribute proven improvements back to the reference pattern.

## Operating Documents For Company Forks

- `docs/en/fork-and-release-operating-model.md`
- `docs/en/release-sync-playbook.md`
- `docs/en/parallelbetrieb-version-binding.md`
- `docs/en/issue-taxonomie-pro-repo.md`
- `docs/en/einfuehrung-greenfield-brownfield.md`
- `docs/en/service-business-core-vertical-blueprint.md`
- `docs/en/vertical-starter-prozesskatalog.md`
- `docs/en/repo-refactor-plan-single-repo-modules.md`
- `docs/en/arbeitsmodell-agile-cadence.md`
- `docs/en/access-and-issue-operations.md`
