# Docs Agent Router

This scoped router applies when editing files under `docs/`.

## Always Load

- [AGENTS.md](../AGENTS.md)
- [docs/de/START_HERE.md](de/START_HERE.md) or [docs/en/START_HERE.md](en/START_HERE.md)
- [agent-context/index.json](../agent-context/index.json)

## Scoped Rules

- German subject-matter content is leading; English is orientation or translation.
- Localized links stay in the same language path unless a language switch is explicit.
- Architecture decisions should link to the relevant workflow contract, validator and quality-gate evidence.
- Do not add mandate data, customer data, credentials, tokens or private document contents.

## On Demand

- For architecture maps, read the matching file under `docs/de/architecture/` and `docs/en/architecture/`.
- For operating-model changes, read the matching file under `docs/*/operations/`.
- For validation claims, read [docs/de/quality-gate.md](de/quality-gate.md) and [docs/en/quality-gate.md](en/quality-gate.md).

