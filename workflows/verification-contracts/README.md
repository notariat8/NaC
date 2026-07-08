# Verification Contracts

Verification contracts are executable definitions of done for recurring NaC
workflows. They do not replace domain contracts. They bind domain decisions,
required context, invariants, checks, evidence and failure behavior so an agent
can prove that a slice is complete.

## Active Contracts

- [codex-agent-context.verification.json](codex-agent-context.verification.json):
  operating-model verification for progressive disclosure, memory, hooks,
  subagent guardrails and agent-readable context.
- [codex-agent-context-index-audit.verification.json](codex-agent-context-index-audit.verification.json):
  compact cross-link audit for worktree, subagent, memory/hooks and command
  rules gates in `agent-context/index.json` and `nac contracts verify`.
- [codex-command-rules.verification.json](codex-command-rules.verification.json):
  command-governance verification for GREEN/YELLOW/RED permission profiles,
  repo-local `.rules`, owner-gated prompts and blocked destructive commands.
- [codex-worktree-operating-model.verification.json](codex-worktree-operating-model.verification.json):
  read-only worktree-audit verification for branch isolation and owner-gated
  cleanup boundaries.
- [m365-matter-access-delegation.verification.json](m365-matter-access-delegation.verification.json):
  domain verification pilot for M365 matter visibility, timeboxed deputy access,
  Graph REST-only request plans, redacted release-gate evidence and owner-gated
  live-write boundaries.
- [m365-matter-access-apply-live-smoke-release-lane.verification.json](m365-matter-access-apply-live-smoke-release-lane.verification.json):
  release-lane verification for the separately approved synthetic SharePoint
  write/read/cleanup smoke and its explicit evidence attachment boundary.
- [m365-matter-access-apply-live-smoke-retention.verification.json](m365-matter-access-apply-live-smoke-retention.verification.json):
  retention verification for correlation-based local archives and indexes of
  redacted owner-gated apply live-smoke evidence.

## Agent Indexes

- [agent-context/decision-index.json](../../agent-context/decision-index.json)
  records accepted decisions that explain why domain guardrails exist.
- [agent-context/invariant-index.json](../../agent-context/invariant-index.json)
  records guardrails that validators must keep enforced.
