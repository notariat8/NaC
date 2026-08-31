# Operations

This folder groups the operating model, upstream sync, version binding, work
model and repository consolidation.

Command execution guidance in this folder follows
[policies/codex-command-rules-policy.json](../../../policies/codex-command-rules-policy.json)
and [.codex/rules/default.rules](../../../.codex/rules/default.rules):
GREEN is read-only/local validation, YELLOW is prompt or owner-gated batch work,
and RED is blocked for destructive, secret, credential, deploy or productive
apply commands.

## Documents

- [fork-and-release-operating-model.md](fork-and-release-operating-model.md): company operation with a central
  upstream.
- [release-sync-playbook.md](release-sync-playbook.md): binding upstream sync process.
- [release-checklist.md](release-checklist.md): approval form for tag, release, audit artifacts and
  rollout decision of versioned process packages.
- [parallelbetrieb-version-binding.md](parallelbetrieb-version-binding.md): mixed old/new operation with version
  binding.
- [agile-cadence.md](agile-cadence.md): work method and team cadence.
- [codex-time-ledger.md](codex-time-ledger.md): local time ledger for Codex work blocks,
  tool time, approvals and repeated waiting time.
- [codex-worktree-operating-model.md](codex-worktree-operating-model.md): read-only
  worktree hygiene audit, naming scheme and owner-gated cleanup boundaries.
- [codex-subagent-operating-gate.md](codex-subagent-operating-gate.md):
  exact read-only subagent registry, runtime limits, rogue-agent blocker and
  batch/worktree split threshold; source registry:
  [agent-context/subagent-registry.json](../../../agent-context/subagent-registry.json).
- [codex-memory-hooks-operating-model.md](codex-memory-hooks-operating-model.md): memory sources,
  hook boundaries and progressive context layers without live hook activation.
- [codex-command-rules-operating-model.md](codex-command-rules-operating-model.md):
  GREEN/YELLOW/RED command governance, repo-local `.rules` and owner-gated
  command boundaries.
- [codex-5h-batch-run-envelope.md](codex-5h-batch-run-envelope.md):
  verifiable envelope for long autonomous offline batches with parallel
  worktrees, subagent scouts and bundled owner gates.
- [m365-mcp-batch-approval.md](m365-mcp-batch-approval.md): batch approval for
  prepared M365 MCP PRs and separately approved live smokes.
- [m365-matter-access-apply-live-smoke-release-lane.md](m365-matter-access-apply-live-smoke-release-lane.md):
  separate owner-gated release-lane standard for real synthetic deputy grants
  with readback, cleanup and redacted evidence.
- [agent-memory-search-qmd.md](agent-memory-search-qmd.md): optional local qmd search index
  for agent rules, release memory and runbooks without secrets or mandate data.
- [oci-runtime.md](oci-runtime.md): archived legacy runtime contract for OCI,
  ATP and OCI release paths; not part of the active M365 MVP.
- [ponytail-skill-only-smoke.md](ponytail-skill-only-smoke.md): owner-gated
  executed Ponytail skill-only smoke for `notoclaw01` with target-control
  evidence and without installation, hooks or runtime activation.
- [nac-runtime-smoke.md](nac-runtime-smoke.md): prepared owner-gated runtime
  smoke for `notoclaw01-host` with read-only NemoClaw/OpenClaw status, redacted
  evidence and without installation, onboarding, rebuild or dashboard-token
  capture.
- [repository-consolidation.md](repository-consolidation.md): migrated, open and retire-ready standalone
  repositories.
- [single-repo-refactor-plan.md](single-repo-refactor-plan.md): target structure and migration into one
  repository.
- [github-first-local-unblock-runbook.md](github-first-local-unblock-runbook.md): diagnosis and workarounds for local GitHub-first blockades (empty OAuth scopes, strict-gate runtime).
- [../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md](../superpowers/specs/2026-05-26-github-first-agentic-operating-model-design.md): GitHub-first work control for agentic issues, pull requests and Projects.
