# Verification Contracts

Verification contracts are executable definitions of done for recurring NaC
workflows. They do not replace domain contracts. They bind domain decisions,
required context, invariants, checks, evidence and failure behavior so an agent
can prove that a slice is complete.

## Active Contracts

- [codex-agent-context.verification.json](codex-agent-context.verification.json):
  operating-model verification for progressive disclosure, memory, hooks,
  subagent guardrails and agent-readable context.
- [m365-matter-access-delegation.verification.json](m365-matter-access-delegation.verification.json):
  domain verification pilot for M365 matter visibility, timeboxed deputy access,
  Graph REST-only request plans, redacted release-gate evidence and owner-gated
  live-write boundaries.

## Agent Indexes

- [agent-context/decision-index.json](../../agent-context/decision-index.json)
  records accepted decisions that explain why domain guardrails exist.
- [agent-context/invariant-index.json](../../agent-context/invariant-index.json)
  records guardrails that validators must keep enforced.
