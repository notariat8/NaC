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
- [codex-5h-batch-run-envelope.verification.json](codex-5h-batch-run-envelope.verification.json):
  long-batch verification for parallel offline lanes, worktree isolation,
  subagent plans, command-risk boundaries and bundled owner gates.
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

- [business-case-type-runtime.verification.json](business-case-type-runtime.verification.json):
  executable S3 acceptance contract for Issue #612 covering exact ID/alias
  resolution, registry cardinality/version/status, cache TTL/invalidation,
  viewer isolation, ETag/data minimization and CLI/strict/review evidence.

## Agent Indexes

- [agent-context/decision-index.json](../../agent-context/decision-index.json)
  records accepted decisions that explain why domain guardrails exist.
- [agent-context/invariant-index.json](../../agent-context/invariant-index.json)
  records guardrails that validators must keep enforced.

- [business-case-type-graph-read-edge.verification.json](business-case-type-graph-read-edge.verification.json): Executable S4 acceptance contract for Issue #616 covering AC-S4-01 through AC-S4-07, exact `Sites.Selected`/`read` scope, same-filter paging, no collection `If-None-Match`, redaction, viewer isolation, offline CLI and zero live Graph calls.
- [business-case-type-graph-write-edge-s4b.verification.json](business-case-type-graph-write-edge-s4b.verification.json): Executable S4b acceptance contract for Issue #694 covering the five bounded write operations, separate `Sites.Selected`/`write` identity, ETag concurrency, create deduplication, S5 hash binding, persistent reconciliation and the synthetic redacted dry-run CLI; live Graph calls and tenant writes remain zero, while production composition and live write remain owner-gated.
- [business-case-type-migration-s5.verification.json](business-case-type-migration-s5.verification.json): Executable S5 acceptance contract for Issue #618 covering AC-S5-01 through AC-S5-07, exact classification, canonical snapshots, idempotent planning, local quarantine, independently captured stable scans, pinned N/N-1 profile evaluation, explicit S5-offline readiness and zero live calls or tenant writes.
- [business-case-type-immutable-evidence-s6.verification.json](business-case-type-immutable-evidence-s6.verification.json): Executable S6a acceptance contract for Issue #687 covering AC-S6-01 through AC-S6-08, canonical evidence chains, pseudonymous ActorRef, sticky reconciliation, retention and privacy gates, zero external activity and the unchanged S7 live block without a production WORM claim.
- [business-case-type-azure-blob-worm-s6b.verification.json](business-case-type-azure-blob-worm-s6b.verification.json): Executable S6b acceptance contract for Issue #693 covering version-bound create/conflict/readback, provider-bound tenant evidence, delete-free writer RBAC, dedicated Bicep, pinned CI compilation and a separate non-executable irreversible-lock contract.
