# Codex Subagent Operating Gate

Status: active MVP guardrail for parallel Codex review work.

Slug: `codex-subagent-operating-gate`.

## Purpose

Subagents save time only when they are bounded, registered and used for
independent review work. NaC uses a fail-closed registry so agentic batching can
run without repeatedly renegotiating the same safety boundary.

Registry:
[agent-context/subagent-registry.json](../../../agent-context/subagent-registry.json).

Workflow contract:
[workflows/contracts/codex-parallel-review.contract.json](../../../workflows/contracts/codex-parallel-review.contract.json).

Runtime limits:
[.codex/config.toml](../../../.codex/config.toml) sets `max_threads = 6`,
`max_depth = 1` and `job_max_runtime_seconds = 1800`.

## Use Threshold

Use subagents when at least two independent review questions exist and the
coordination cost is lower than the expected review value. Use worktrees instead
when parallel implementation needs separate branches or isolated file edits.

The lead Codex run remains accountable for the final diff, validation evidence,
owner-gate wording and PR state.

## Context Isolation

Every NaC subagent is started with `fork_context: false`. Full-history forks
are prohibited. The lead run passes only the bounded task, relevant paths,
issue or pull request, and applicable rules. If that context is insufficient,
the scoped prompt is extended; the complete parent task is not copied.
Completed subagents are closed immediately.

This rule prevents long parent tasks from being duplicated into a new session
file for every reviewer. It is part of the fail-closed validator, not merely an
operator recommendation.

## Registry Boundary

- Only profiles listed in the registry may be used.
- `.codex/agents/*.toml` must match the registry exactly.
- Every registered profile is `read-only` and must say `Do not edit files.`
- Unknown or extra agent profiles fail closed.
- Subagents may return findings, evidence gaps and suggested checks; they do
  not perform live applies, releases, credential changes or cleanup actions.

## Prohibited Delegation

Never delegate secrets, certificate private material, real mandate data,
productive M365 writes, Entra app credentials, release apply work or destructive
git cleanup to subagents.

## Verification

```bash
python3 scripts/validate_codex_subagent_operating_gate.py
python3 -m unittest tests.test_codex_subagent_operating_gate
python3 scripts/quality_gate.py --profile strict
```
