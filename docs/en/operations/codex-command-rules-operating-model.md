# Codex Command Rules Operating Model

Status: active MVP command-governance layer.

## Purpose

Repeated command approvals should become reusable command profiles instead of
ad hoc chat decisions. NaC uses GREEN/YELLOW/RED profiles to let routine
read-only and local-validation work continue while preserving owner gates for
merge, destructive, secret, credential, live-tenant and productive-data edges.

Machine-readable source:
[policies/codex-command-rules-policy.json](../../../policies/codex-command-rules-policy.json).

Codex rules artifact:
[.codex/rules/default.rules](../../../.codex/rules/default.rules).

Context router:
[agent-context/index.json](../../../agent-context/index.json) lists these
command rules as on-demand guardrails. Runtime command output remains
task-local evidence and is not a shared memory source.

## Profiles

| Profile | Decision | Examples |
| --- | --- | --- |
| GREEN | allow | `git status`, `git diff`, `gh pr checks`, local validators, `rg` |
| YELLOW | prompt | `git push`, `gh pr create`, `gh pr merge`, branch cleanup, owner-approved synthetic M365 gates |
| RED | block | `git reset --hard`, `git checkout --`, `rm -rf`, Entra credential mutation, `terraform apply`, privileged productive apply |

## Guardrails

- Rules do not replace owner approval for PR merges.
- Rules do not authorize secrets, certificate rotation or Entra credentials.
- Rules do not authorize productive SharePoint/Teams writes outside a dedicated
  owner-approved command.
- Rules do not activate hooks and do not mutate local `~/.codex/config.toml`.
- Rules do not expand filesystem or network access.

## Verification

```bash
python3 scripts/validate_codex_command_rules_operating_model.py
python3 -m unittest tests.test_codex_command_rules_operating_model
python3 scripts/quality_gate.py --profile strict
```
