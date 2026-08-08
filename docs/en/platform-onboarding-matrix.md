# Platform Onboarding Matrix

## Goal

Ensure that concept, rule and onboarding changes are maintained synchronously
for the active agent platforms: Codex and pi.

## Mandatory Paths

| Platform | Mandatory files |
| --- | --- |
| Codex | [AGENTS.md](../../AGENTS.md), [.codex/agents/](../../.codex/agents), [docs/en/START_HERE.md](START_HERE.md), [docs/en/plugin-plans/README.md](plugin-plans/README.md) |
| pi | [.pi/agents/](../../.pi/agents), [.pi/settings.json](../../.pi/settings.json), [.pi/README.md](../../.pi/README.md) |

## Shared Core

The following content must remain equivalent between policy, AGENTS.md,
Codex profiles and pi subagents:

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
3. Update the pi subagent path.
4. Check links in [README.md](../../README.md) and
   [docs/en/START_HERE.md](START_HERE.md).

## Platform Mapping

The pi subagents under [.pi/agents/](../../.pi/agents) are Markdown mirrors of
the Codex profiles under [.codex/agents/](../../.codex/agents). Both are
read-only and cover the same review perspectives: scope mapper, KG, BPMN,
policy, docs-parity and validation reviewers. pi-specific capabilities (plan
mode, parallel review, PR status, autonomous completion) come through
recommended pi extensions that contributors install themselves; see
[.pi/README.md](../../.pi/README.md).

## Current Synchronous MVP Default

- `notary`:
  [prompts/en/onboarding/notary-first-setup.md](../../prompts/en/onboarding/notary-first-setup.md)

Non-notarial domain sets are outside NaC scope. Subject-matter examples come
only from [usecases/](../../usecases), for example real-estate purchase contract
or signature certification.
