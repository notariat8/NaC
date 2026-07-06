# GitHub-First Agentic Operating Model

Status: design specification
Date: 2026-05-26

```nac-spec-traceability
schema_version: nac.spec-traceability/v0.1
spec_id: github-first-agentic-operating-model
leading_issue: thread:2026-05-26-github-first-agentic-operating-model
risk_gate: Governance
delivery_mode: Owner Direct
acceptance_ids:
  - AC-001
validation_commands:
  - python3 scripts/validate_spec_traceability.py
  - python3 scripts/validate_governance_sync.py
  - python3 scripts/quality_gate.py --profile strict
```

## Starting Point

NaC already uses Git, pull requests, reviews, Actions, an issue taxonomy,
organization projects and an audit-safe event journal. The current gap is not a
missing tool, but operational binding: agentic work should be visible and
steerable for the owner in GitHub without forcing the owner to reconstruct
progress from repository diffs, Mermaid files or Gantt files.

GitHub Projects fits this role because issues and pull requests can be tracked
as project items, Projects support custom fields and views, and `gh project`
can be automated with the `project` scope. NaC deliberately avoids depending on
GitHub Projects Classic or preview-only issue fields. The model uses stable
project fields and linked issues/pull requests.

## Decision

GitHub becomes the primary operational control surface for agentic NaC work:

- Issues describe assignment, context, acceptance criteria and risks.
- Pull requests describe the concrete change, validation and review trail.
- GitHub Projects shows status, track, priority, risk, delivery mode and
  blockers.
- GitHub Actions and required checks provide the technical completion gate.
- Repository policies, documents, commits, tags and the event journal remain
  the auditable truth.

Gantt and Mermaid files remain allowed, but they are no longer treated as the
primary progress surface. They are snapshots or release/roadmap artifacts. The
live work state should be visible in GitHub.

## Non-Goals

- No replacement of policy files by project fields.
- No matter data, secrets, PINs, tokens or private document content in issues,
  pull requests, project fields or comments.
- No bypassing review, branch protection, secret scanning or quality gates.
- No artificial issue requirement for pure typo fixes or local micro
  clarifications when they have no governance, scope, status or roadmap impact.

## Operating Surface

The target model is an organization project, for example `NaC Control Plane`,
under `notariat8`. This project is the owner's first work view.

Required fields:

| Field | Type | Purpose |
| --- | --- | --- |
| `Status` | single select | `Inbox`, `Ready`, `In Progress`, `Review`, `Blocked`, `Done` |
| `Track` | single select | `Governance`, `Runtime`, `KG`, `BPMN`, `Operator`, `Plugins`, `Security`, `Docs`, `CI`, `Release` |
| `Work Type` | single select | `Feature`, `Bug`, `Governance`, `Spike`, `Ops`, `Security`, `Docs` |
| `Risk Gate` | single select | `None`, `Privacy`, `Secrets`, `Workflow`, `Policy`, `External Service`, `Human Approval` |
| `Delivery Mode` | single select | `Owner Direct`, `Protected PR`, `Sync PR` |
| `Priority` | single select | `P0`, `P1`, `P2`, `P3` |
| `Size` | single select | `S`, `M`, `L` |
| `Iteration` | iteration | work window for active planning |
| `Due Date` | date | only when a real deadline or milestone binding exists |

Recommended views:

- `Owner Board`: all active items, grouped by `Status`.
- `Now`: `Status` in `Ready`, `In Progress`, `Review`, excluding `Done`.
- `Blocked`: all blocked items with a visible blocker comment.
- `Governance And Security`: `Track` in `Governance`, `Security`, `CI`.
- `Release Readiness`: items with release, Gantt or versioning impact.
- `My Agent Work`: items assigned to the current agent or technical login.

## Issue Rules

Nontrivial work starts with exactly one leading issue. An issue is not just a
ticket, but the smallest traceable assignment.

Required content of a leading issue:

- Goal and subject-matter value.
- Scope and explicit non-goals.
- Acceptance criteria.
- Risk/privacy/secret assessment.
- Expected delivery mode.
- Validation plan.
- Project assignment and required fields.

Issue types:

| Type | Use |
| --- | --- |
| `Feature` | new subject-matter or technical function |
| `Bug` | incorrect behavior or broken gate |
| `Governance` | policy, rule, role or operating-model change |
| `Spike` | research or decision work without immediate product change |
| `Ops` | operations, auth, projects, labels, branch protection, releases |
| `Security` | secret, privacy, permission or supply-chain topics |
| `Docs` | documentation change with operational steering impact |

Derived issues in other repositories must link to the leading issue. This
matches the existing issue taxonomy and prevents distributed shadow backlogs.

## Acceptance Criteria

- AC-001: Agentic work control remains traceable through leading issues,
  Project fields, Delivery Mode and `remote_ci_checks`.

## Branch And PR Rules

Default for agentic changes:

1. Clarify or create the leading issue.
2. Set project fields.
3. Create branch:
   - `agent/<issue-number>-<short-slug>` for normal agent work.
   - `sync/<issue-number>-<short-slug>` for upstream or fork sync.
   - `hotfix/<issue-number>-<short-slug>` only for P0/P1 defects.
4. Open a draft pull request as soon as the direction of change is visible.
5. Link the PR to the issue and project item.
6. Document local validation in the PR.
7. Wait for required checks.
8. Review/merge according to delivery mode.
9. Set project status to `Done` only after merge or owner-direct target branch,
   clean workspace and successful `remote_ci_checks`.

Owner-direct delivery to `main` remains allowed for the active reference repo
when the owner explicitly requests direct delivery. Even then, nontrivial work
keeps an issue and project trail. The completion rule remains hard: locally
validated, committed, pushed, `HEAD` equals `origin/main`, workspace clean and
required checks green.

## Autonomy Prerequisites

For an agent to work as autonomously as possible, it needs:

- GitHub CLI/app access with `repo`, `workflow`, `project` and, for
  organization context, `read:org`.
- Permission to create or update issues, labels, branches, draft PRs, PR
  comments and project fields within the agreed scope.
- A named project owner and a project number or URL.
- Clear delivery-mode rule per repository: `Protected PR`, `Owner Direct` or
  `Sync PR`.
- A ban on writing secrets or real matter data to GitHub surfaces.
- Escalation rule for blockers: project status `Blocked`, short comment with
  the missing decision, no silent policy deviation.

If a rule blocks work, the owner's governance rule applies: first determine
whether the rule is correct but incompletely implemented or whether the rule
itself is wrong and must be changed. Silent deviation is not a valid delivery
mode.

## Policy Changes

Implementation should extend `policies/process-policy.yaml` with a
`github_first_operating_model` section. This section defines:

- GitHub Project as the operational progress surface.
- Mandatory issue for nontrivial work.
- Mandatory PR for production forks and sensitive process changes.
- Owner-direct exception in the active reference repo with issue/project trail.
- Required project fields and minimum views.
- Completion only after `remote_ci_checks`.
- Ban on secrets and matter data in issues, pull requests and project fields.

The mirrors must be synchronized:

- `AGENTS.md`
- `.codex/agents/`
- `docs/de/regelarchitektur.md`
- `docs/en/regelarchitektur.md`
- `docs/de/issues/operations.md`
- `docs/en/issues/operations.md`
- `docs/de/operations/README.md`
- `docs/en/operations/README.md`

## Validation

New or extended tests should ensure:

- The process policy contains `github_first_operating_model`.
- Required project fields and delivery modes are machine-readable.
- Rule architecture and agent surfaces mirror the GitHub-first rule.
- Privacy/secret rules also apply to GitHub issues, pull requests and projects.
- Language parity for German and English documents remains intact.

Existing mandatory validation remains:

- `python -m unittest`
- `scripts/validate_governance_sync.py`
- `scripts/validate_language_parity.py`
- `scripts/validate_doc_links.py`
- `scripts/privacy_lint.py`
- `scripts/quality_gate.py --profile strict`
- GitHub required checks on the target state

## Implementation Steps

1. Write a failing policy test for `github_first_operating_model`.
2. Update the process policy and mirrors.
3. Extend issue operations documents with project fields, views and autonomy
   rules.
4. Optionally extend issue templates and the PR template if they are not
   structured enough yet.
5. Create the GitHub Project through the UI or `gh project` and add fields.
6. Create the first leading issue for the next NaC change and assign it to the
   project.
7. Complete local and remote validation.

## References

- GitHub CLI `gh project`: https://cli.github.com/manual/gh_project
- GitHub project fields: https://docs.github.com/issues/planning-and-tracking-with-projects/understanding-fields
- Adding items to projects: https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-items-in-your-project/adding-items-to-your-project
