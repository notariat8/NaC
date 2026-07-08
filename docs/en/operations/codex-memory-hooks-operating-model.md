# Codex Memory And Hooks Operating Model

## Purpose

This model separates personal recall, shared truth and automatic workflow
helpers. It does not activate hooks and does not change a local
`~/.codex/config.toml`.

## Memory Sources

| Type | Store | Rule |
| --- | --- | --- |
| Personal and stable | Codex Memory | Preferences, recurring work style, communication rules. |
| Team rule or invariant | Repository artifact | [AGENTS.md](../../../AGENTS.md), policies, contracts, runbooks. |
| Changing work state | GitHub issue/PR | Status, blockers, scope, acceptance criteria. |
| Conversation evidence | Thread/issue comment | Only as evidence or coordination history. |
| Large document set | Search index or MCP | Only with reviewed data class and access path. |
| Secrets or mandate data | do not store | Only in approved secret/payload systems. |

If a fact needs auditability or can change, Codex Memory is not the source of
truth. The agent must read it from the repository, GitHub, SharePoint/M365 or
an approved MCP.

## Hook Boundary

Hooks may start repeatable local checks, but they do not replace policy.
Suitable uses:

- formatting, linting or tests before completion,
- regenerating redacted artifacts,
- checking whether a required validator is missing.

Not suitable:

- blocking risky shell commands,
- limiting file or network permissions,
- teaching repository context,
- checking secrets or mandate data,
- starting productive M365, Entra, SharePoint or GitHub write actions.

Those boundaries remain the job of rules, permissions, owner gates, validators
and the quality gate.

## Example Configuration

The repository files under [.codex/hooks/](../../../.codex/hooks/) are
examples. They become active only when an operator explicitly references them
from the local Codex configuration.

Example local activation after review:

```toml
[[hooks.PreToolUse]]
matcher = "Bash"

[[hooks.PreToolUse.hooks]]
type = "command"
command = "/usr/bin/python3 /path/to/NaC/.codex/hooks/pre_tool_use_policy.example.py"
timeout = 30
statusMessage = "Checking NaC command hints"
```

Activation needs no repository change, but the concrete local configuration
remains an operator decision.

## Progressive Disclosure

The memory/hooks path uses the agent context index:

- Always-on: stable rules and navigation.
- Scoped: directory rules and agent profiles.
- On-demand: architecture, decisions, guardrails and runbooks.
- Runtime: current prompt, tool output, logs, diffs and evidence.

The machine-readable router is
[agent-context/index.json](../../../agent-context/index.json).

## Verification

Completion for this operating model is checked through
[codex-memory-hooks.verification.json](../../../workflows/verification-contracts/codex-memory-hooks.verification.json),
[codex-agent-context.verification.json](../../../workflows/verification-contracts/codex-agent-context.verification.json)
and `nac contracts verify`.

```bash
python3 scripts/validate_codex_memory_hooks_operating_model.py
python3 -m unittest tests.test_codex_memory_hooks_operating_model
python3 scripts/quality_gate.py --profile strict
```
