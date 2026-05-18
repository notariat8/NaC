# Platform Matrix For Onboarding And Rules

## Goal

Ensure that concept, rule and onboarding changes are maintained synchronously
for all supported platforms.

## Mandatory Paths

| Platform | Mandatory files |
| --- | --- |
| Cursor | [AGENTS.md](../../AGENTS.md), [.cursor/rules/](../../.cursor/rules), [docs/en/START_HERE.md](START_HERE.md), [docs/en/plugin-plans/README.md](plugin-plans/README.md) |
| VS Code + Copilot | [AGENTS.md](../../AGENTS.md), [.github/copilot-instructions.md](../../.github/copilot-instructions.md), [docs/en/vscode-copilot-start.md](vscode-copilot-start.md), [docs/en/plugin-plans/README.md](plugin-plans/README.md) |

## Shared Core

The following content must remain equivalent on both platforms:

- compliance and governance principles,
- review and approval logic,
- culture and language policy,
- onboarding order for non-IT users,
- default MVP modules and related onboarding prompts,
- local execution location for NaC: `~/NaC` in WSL,
- plugin and connector planning model.

## Change Rule

For every conceptual change:

1. Update core content.
2. Update Cursor path.
3. Update VS Code Copilot path.
4. Check links in [README.md](../../README.md) and
   [docs/en/START_HERE.md](START_HERE.md).

## Current Synchronous MVP Default

- `software_company`:
  [prompts/en/onboarding/software-company-first-setup.md](../../prompts/en/onboarding/software-company-first-setup.md)
- `notary`:
  [prompts/en/onboarding/notary-first-setup.md](../../prompts/en/onboarding/notary-first-setup.md)
- `wealth_management`:
  [prompts/en/onboarding/wealth-management-first-setup.md](../../prompts/en/onboarding/wealth-management-first-setup.md)

Additional MVP usecase:

- `property_management`:
  [prompts/en/onboarding/property-management-first-setup.md](../../prompts/en/onboarding/property-management-first-setup.md)
