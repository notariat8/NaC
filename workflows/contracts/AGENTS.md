# Contract Agent Router

This scoped router applies when editing files under `workflows/contracts/`.

## Always Load

- [AGENTS.md](../../AGENTS.md)
- [workflows/contracts/README.md](README.md)
- [agent-context/index.json](../../agent-context/index.json)

## Contract Rules

- Contracts describe deterministic boundaries, roles, gates, evidence and validation commands.
- New agent-facing operating contracts should also have a verification contract under
  [workflows/verification-contracts/](../verification-contracts/).
- Evidence fields must be redacted and must not contain mandate data, private payloads,
  credentials, tokens or certificate private material.
- Live apply, release, secret and destructive actions remain owner-gated.

## On Demand

- For Codex agent reviews, load [codex-parallel-review.contract.json](codex-parallel-review.contract.json).
- For M365 runtime work, load [teams-sharepoint-data-mcp.contract.json](teams-sharepoint-data-mcp.contract.json)
  and [teams-sharepoint-graph-data-plane.contract.json](teams-sharepoint-graph-data-plane.contract.json).
- For verification contracts, load
  [../verification-contracts/codex-agent-context.verification.json](../verification-contracts/codex-agent-context.verification.json).
