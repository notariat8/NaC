# NaC Codex Hook Examples

This directory contains opt-in hook examples for local Codex operators.

The repository does not activate these hooks. They become active only when an
operator references them from a local Codex configuration such as
`~/.codex/config.toml`.

Allowed example scope:

- print local command hints,
- remind the operator of required validators,
- fail closed only for clearly invalid local hook input.

Out of scope:

- secrets, tokens, certificates or mandate data inspection,
- GitHub, M365, Entra or SharePoint write actions,
- branch deletion or worktree cleanup,
- replacing owner gates, permissions or the NaC quality gate.

