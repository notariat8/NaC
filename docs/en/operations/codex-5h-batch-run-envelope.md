# Codex 5h Batch Run Envelope

## Purpose

The 5h batch run envelope is the operating boundary for long autonomous Codex
runs. It prevents a multi-hour batch from collapsing back into small sequential
steps while making the parallel lanes explicit.

The envelope is an offline contract. It performs no Microsoft 365, Entra,
SharePoint, Teams or GitHub merge action.

## Use

Use it when at least two independent work lanes can be prepared in parallel:

- multiple offline pull requests,
- separate worktrees for writable lanes,
- read-only subagent scouts for scope, review or validation,
- bundled owner gates at the end instead of recurring single-step prompts.

Do not use it for small single-file changes or one clear bug fix.

## Mandatory Boundaries

- No live tenant apply: no live tenant action without explicit owner approval.
- No secrets or credentials: no secret, certificate or Entra credential change.
- No destructive git or filesystem: no destructive cleanup without explicit
  approval.
- No merge without owner approval: pull requests may be prepared, but not
  merged without approval.

## Context

The envelope follows the router in
[agent-context/index.json](../../../agent-context/index.json):

- Always-on: `AGENTS.md`, policies and central invariants.
- Scoped: affected directory rules and contract guidance.
- On-demand: worktree, subagent, memory/hooks and command-rules models.
- Runtime: fresh Git status, fresh tests and fresh PR/CI output.

Runtime logs, raw output, secrets, tokens, customer or matter data are not
stored as persistent shared context.

## Worktrees And Subagents

Every writable lane needs its own worktree. Overlapping `write_scope` entries
block the envelope. With two or more independent review questions, a subagent
plan or an explicit no-split reason is required.

Subagents stay read-only unless they own their own worktree boundary.

## Verification

Standard check:

```bash
python3 scripts/validate_codex_5h_batch_run_envelope.py
python3 scripts/nac.py agent-batch validate --format json
python3 scripts/nac.py contracts verify
```

The verification contract is
[codex-5h-batch-run-envelope.verification.json](../../../workflows/verification-contracts/codex-5h-batch-run-envelope.verification.json).
