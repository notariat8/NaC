# Rule Architecture

Status: binding explanation of the NaC rule groups

This page explains which rules block work, which rules are work discipline and
which rules are guidance only. The leading machine-readable source is
[policies/process-policy.yaml](../../policies/process-policy.yaml). Agent
surfaces such as [AGENTS.md](../../AGENTS.md), Cursor rules and
[.github/copilot-instructions.md](../../.github/copilot-instructions.md) mirror
that policy.

## Principle

NaC rules should do three things:

1. Protect matter data, secrets and professional responsibility.
2. Make changes traceable, verifiable and repeatable.
3. Avoid slowing work down through artificial required edits.

A rule is hard only when it prevents a real risk and can be checked
automatically or unambiguously. Everything else is handled as a working rule or
documentation rule.

## Rule Groups

| Group | Why | Hardness | Leading Check |
| --- | --- | --- | --- |
| Completion and finished state | Prevents local intermediate states from being called finished. | hard | `nac doctor --profile strict`, `git status`, `HEAD` versus `origin/main`, `remote_ci_checks` |
| Git delivery | Separates production PR approval from owner-direct work in the active reference repo. | mode-dependent | branch protection/PR in production mode, push+clean check in reference mode |
| GitHub-first work control | Ties non-trivial agentic work to a leading issue and visible Project board. | working rule plus completion gate | issue trail, `NaC Control Plane`, Delivery Mode, `remote_ci_checks` |
| Spec traceability | Connects issue, spec, plan, AC IDs and validation commands so spec-driven work stays checkable. | working rule plus validator gate | [workflows/contracts/spec-traceability.contract.json](../../workflows/contracts/spec-traceability.contract.json), `scripts/validate_spec_traceability.py` |
| Agentic change discipline | Prevents doom loops caused by unclear requirements, unreviewed agent changes and fixes without diagnosis. | working rule plus validator gate | `agent_workflows` in [policies/process-policy.yaml](../../policies/process-policy.yaml), plan/code review, validation evidence |
| Operator/admin handoff | Prevents unprepared requests for tenant values, secrets or portal actions. | working rule plus validator gate per integration contract | [workflows/contracts/teams-sharepoint-graph-data-plane.contract.json](../../workflows/contracts/teams-sharepoint-graph-data-plane.contract.json), runbook with hyperlinks and copy-paste commands |
| Roadmap and Gantt | Keeps delivery plan and status visible without blocking small fixes. | guidance plus render gate | `scripts/validate_gantt_progress.py` |
| Language and localization | German leads for subject matter, English is translation/orientation. | hard | `scripts/validate_language_parity.py` |
| CLI and office surface | New NaC functionality needs a verifiable operating surface. | hard for new functionality | tests, CLI call, `nac doctor --profile strict` |
| Data protection and data repository | Prevents real matter data, secrets, PINs and raw card data in the product repo. | hard | `scripts/privacy_lint.py`, data protection policy |
| Plugins, skills and agent method | Keeps local plugins installable and agent work planned. | mixed | `scripts/validate_plugins.py`, local plugin mirror, Superpowers-compatible workflow |
| Validation and doctor | Makes completion claims evidence-based. | hard | `scripts/quality_gate.py`, `nac doctor --profile strict` |

## Git Delivery Modes

NaC distinguishes two modes:

| Mode | Use | Finished Means |
| --- | --- | --- |
| Protected PR mode | Production forks, sensitive process changes, external contribution. | Branch is reviewed through PR, validated and merged into `main`. |
| Owner-direct mode | Active reference repo when the owner explicitly asks for direct delivery. | `main` is validated, pushed to GitHub, `HEAD` equals `origin/main`, the working tree is clean, and `Privacy and Secrets Guard / secret-scan`, `Privacy and Secrets Guard / privacy-lint` and `NaC Quality Gate / quality-gate` are successful. |

For production notary or organization forks, protected PR mode is the target
state. Owner-direct mode is not permission to store production matter data or
make sensitive subject-matter changes without review.

`remote_ci_checks` are part of the completion rule because local validation
does not prove that GitHub has run the same protection gates after the push.
The minimum required checks are `Privacy and Secrets Guard / secret-scan`,
`Privacy and Secrets Guard / privacy-lint` and
`NaC Quality Gate / quality-gate`.

## GitHub-first Work Control

Non-trivial agentic work is GitHub-first. A leading issue records the task,
scope, acceptance criteria, Risk Gate, Delivery Mode and validation. The
organization Project `NaC Control Plane` shows status, blockers and ownership
across the repositories each user is allowed to see.

An update is finished only when the Delivery Mode documented in the issue is
satisfied and the required `remote_ci_checks` are successful. The Project does
not bypass repository permissions: users see only issues from repositories
they can already access.

## Spec Traceability

New or changed non-trivial specs keep a checkable trail from issue to spec,
plan, AC IDs and validation commands. The machine-readable contract lives in
[workflows/contracts/spec-traceability.contract.json](../../workflows/contracts/spec-traceability.contract.json)
and is checked by `scripts/validate_spec_traceability.py`.

Historical specs without a manifest remain valid. When a spec is developed
further, it should receive a `nac-spec-traceability` block. AC IDs appear both
in the manifest and in the acceptance section so reviews and tests can point at
the same criteria.

## Agentic Change Discipline

Non-trivial work follows two separate loops:

1. `plan -> review -> fix`: requirements, architecture assumptions, scope,
   risks and acceptance criteria are clarified in text first. A fresh review
   checks the plan for gaps, contradictions, unnecessary technology and missing
   tests or approvals.
2. `implement -> review -> fix`: the implementation is checked against the
   plan, existing repository patterns, error handling, test coverage and
   security before the state is ready for acceptance.

For repeated, unclear or cross-layer failures, diagnosis comes before fixing.
An agent may change code only after the cause has been named. Changes that
touch the data, controller/logic or view layer need an explicit check that
those layers stay synchronized.

Before a merge, the full PR diff against the target branch is part of agentic
change discipline. Agents check `base...head`, the file list and the commit
list; a single HEAD commit is not enough merge evidence. If the diff contains
more scope than approved, the run stops and the branch is recut or the combined
scope is documented explicitly.

The agentic-delivery reading is: do not merely make human handoffs faster; make
handoffs machine-readable and checkable. An agentic work order should therefore
name the subject-matter source, affected usecase, relevant KG/BPMN/contract
artifacts, expected validators and required review or approval points. Risk,
legal, privacy, testing and procurement roles belong in that structure early,
not only as a late stop sign after implementation.

## Gantt Rule

Gantt files are updated when roadmap, scope, status, milestone, pilot readiness
or active build-board state changes. Small bug fixes, typo fixes, local
documentation clarifications, test/validator fixes or UI details without
roadmap impact do not need artificial Gantt changes.

A weekly update is enough for the progress picture. During the week, the Gantt
changes only when roadmap, scope, status, milestone, pilot readiness or active
build-board state actually moves.

The strict gate still checks:

- required Gantts exist,
- Mermaid Gantt blocks remain renderable on GitHub,
- possible roadmap or area impact produces guidance.

## Superpowers Compatibility

Superpowers is useful work methodology, not a NaC product dependency. The
compatible rule is:

- Open scope: explore first, then get design/plan confirmation.
- Bug: find the root cause before changing code.
- Non-trivial code change: record the test or check objective first.
- Completion: make no success claim without fresh verification.

This method complements NaC rules; it does not replace data protection,
language, license or approval rules.
