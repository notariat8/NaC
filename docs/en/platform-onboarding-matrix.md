# Codex Onboarding Matrix

## Goal

Ensure that concept, rule and onboarding changes are maintained synchronously
for the active Codex path.

## Mandatory Paths

| Platform | Mandatory files |
| --- | --- |
| Codex | [AGENTS.md](../../AGENTS.md), [.codex/agents/](../../.codex/agents), [docs/en/START_HERE.md](START_HERE.md), [docs/en/plugin-plans/README.md](plugin-plans/README.md) |

## Shared Core

The following content must remain equivalent between policy, AGENTS.md and
Codex profiles:

- compliance and governance principles,
- review and approval logic,
- culture and language policy,
- onboarding order for non-IT users,
- notarial scope, canonical usecases and related onboarding prompts,
- local execution location for NaC: `~/NaC` in WSL,
- plugin and connector planning model.

## Change Rule

For every conceptual change:

1. Update core content.
2. Update the Codex agent path.
3. Check links in [README.md](../../README.md) and
   [docs/en/START_HERE.md](START_HERE.md).

## Current Synchronous MVP Default

- `notary`:
  [prompts/en/onboarding/notary-first-setup.md](../../prompts/en/onboarding/notary-first-setup.md)

Non-notarial domain sets are outside NaC scope. Subject-matter examples come
only from [usecases/](../../usecases), for example real-estate purchase contract
or signature certification.
