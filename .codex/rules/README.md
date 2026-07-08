# NaC Codex Command Rules

This directory stores repository-local Codex command rules.

The source of truth is
[policies/codex-command-rules-policy.json](../../policies/codex-command-rules-policy.json).
The `default.rules` file mirrors the validated policy for Codex clients that
support `.rules` files.

## Risk Levels

| Level | Decision | Meaning |
| --- | --- | --- |
| GREEN | `allow` | read-only repository status, local validation and harmless search |
| YELLOW | `prompt` | PR publication, merge/cleanup and owner-approved synthetic live gates |
| RED | `block` | destructive git/filesystem, secrets, credentials, deploys, migrations and productive applies |

Rules do not replace owner gates. They also do not expand filesystem access,
network access or tenant permissions. Hooks remain separate and opt-in.
