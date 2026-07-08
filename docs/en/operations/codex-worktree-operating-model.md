# Codex Worktree Operating Model

## Purpose

Git worktrees are the local isolation layer for parallel NaC work on multiple
branches. They solve a different problem than subagents:

- Worktrees isolate files, branches and local test artifacts.
- Subagents split analysis, review or implementation work inside a scoped
  assignment.
- Forks are reserved for separate GitHub paths or external contribution flows.

This model is read-only for audits and owner-gated for cleanup. It stores no
secrets, tokens, certificates or mandate data.

## Naming

New worktrees use explicit branch and folder names:

```bash
git worktree add ../NaC-<slug> -b <branch>
```

Rules:

- `<slug>` describes the scope, for example `matter-access-policy-hardening`.
- `<branch>` follows the issue or slice name, for example
  `matter-access-policy-hardening`.
- One worktree belongs to exactly one branch and one subject-matter slice.
- Worktrees are short-lived and are removed after merge or abandonment.

## Standard Flow

1. Create an issue and record the scope.
2. Create the branch in the primary checkout or as a worktree.
3. Implement, test and open the PR in exactly one worktree.
4. After merge, inspect the worktree state.
5. Run cleanup only as an owner-gated batch.

Read-only audit:

```bash
nac git worktree-audit
nac git worktree-audit --format json
```

The audit reads only local Git metadata. It does not execute
`git worktree remove`, `git branch -d` or `git push origin --delete`.

## Cleanup Boundary

The audit may report cleanup candidates, but it must not clean them up. These
commands remain explicitly owner-gated:

```bash
git worktree remove ../NaC-<slug>
git branch -d <branch>
git push origin --delete <branch>
```

Before remote deletion, the operator must verify that no open pull request and
no active work item still points at the branch. The local audit uses no GitHub
API and no network; it can only mark this PR status check as required.

## Boundary To Subagents

Use worktrees when parallel work must keep files or branches isolated:

- prepare multiple PRs at the same time,
- test risky refactors away from the main slice,
- isolate local artifacts per branch.

Use subagents when parallel thinking or review is sufficient:

- documentation or code review from multiple perspectives,
- analysis of architecture, policy and test surfaces,
- subject-matter counter-review without a separate branch.

When both are needed, the lead agent remains accountable: subagents provide
review or implementation findings, while the lead agent integrates them into
the relevant worktree and reviews the final diff.

## Safety Boundaries

- No mandate data in worktrees, tests or audit artifacts.
- No secrets or certificate material in branches.
- No destructive Git action without owner approval.
- No automatic remote deletion without an open-PR check.
- `nac git worktree-audit` remains read-only and must return exit code 0 even
  when cleanup candidates exist, so it works as diagnostics and not as a
  cleanup mechanism.

