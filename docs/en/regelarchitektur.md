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
| Completion and finished state | Prevents local intermediate states from being called finished. | hard | `nac doctor --profile strict`, `git status`, `HEAD` versus `origin/main` |
| Git delivery | Separates production PR approval from owner-direct work in the active reference repo. | mode-dependent | branch protection/PR in production mode, push+clean check in reference mode |
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
| Owner-direct mode | Active reference repo when the owner explicitly asks for direct delivery. | `main` is validated, pushed to GitHub, `HEAD` equals `origin/main`, and the working tree is clean. |

For production notary or organization forks, protected PR mode is the target
state. Owner-direct mode is not permission to store production matter data or
make sensitive subject-matter changes without review.

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
