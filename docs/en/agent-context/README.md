# Agent-Readable Context

## Purpose

NaC separates agent context into layers so Codex loads the right context at the
right time, not simply more context.

The machine-readable index is
[agent-context/index.json](../../../agent-context/index.json).
Accepted domain decisions are indexed in
[agent-context/decision-index.json](../../../agent-context/decision-index.json).
Critical invariants are indexed in
[agent-context/invariant-index.json](../../../agent-context/invariant-index.json).

## Layers

| Layer | Content | Source |
| --- | --- | --- |
| Always-on | stable invariants and navigation | [AGENTS.md](../../../AGENTS.md), policies, START_HERE |
| Scoped | directory- or domain-specific rules | [docs/AGENTS.md](../../AGENTS.md), [workflows/contracts/AGENTS.md](../../../workflows/contracts/AGENTS.md), [.codex/agents/](../../../.codex/agents) |
| On-demand | architecture, decisions, guardrails, runbooks | architecture docs, technology decision, contracts, verification contracts |
| Runtime | current prompt, tool output, logs, diffs, evidence | fresh command output and redacted run artifacts |

## Agent-Readable Artifacts

NaC uses several agent-readable artifact types:

- Maps: system shape, data plane, runtime and contract maps.
- History: technology decisions, architecture decisions, operating models.
- Guardrails: policies, CODEOWNERS, PR template, quality gate and verification contracts.
- Worktree operating model: branch isolation, read-only hygiene audit and
  owner-gated cleanup boundaries.
- Subagent operating gate: subagent registry, usage thresholds and runtime limits.
- Memory/hooks: local recall and hook boundaries without live hook activation.
- Command rules: GREEN/YELLOW/RED shell-command profiles and repo-local
  `.rules` guardrails for repeated command decisions.

These artifacts do not replace truth for mandate data or notarial decisions.
They explain architecture, boundaries and evidence.

## Verification Contracts

New agentic operating surfaces should get a verification contract when their
definition of done is discussed repeatedly. The first pilot is
[codex-agent-context.verification.json](../../../workflows/verification-contracts/codex-agent-context.verification.json).
The first domain pilot is
[m365-matter-access-delegation.verification.json](../../../workflows/verification-contracts/m365-matter-access-delegation.verification.json).
Command permission profiles are verified by
[codex-command-rules.verification.json](../../../workflows/verification-contracts/codex-command-rules.verification.json).
The compact cross-link proof for worktree, subagent, memory/hooks and command
rules gates is
[codex-agent-context-index-audit.verification.json](../../../workflows/verification-contracts/codex-agent-context-index-audit.verification.json).

Required fields:

- `applies_when.paths`
- `required_context`
- `checks`
- `invariants`
- `thresholds`
- `required_evidence`
- `pass_condition`
- `failure_behavior`
