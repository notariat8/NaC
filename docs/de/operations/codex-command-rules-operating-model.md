# Codex Command Rules Operating Model

Status: aktive MVP-Schicht für Command-Governance.

## Zweck

Wiederkehrende Command-Freigaben sollen als wiederverwendbare Command-Profile
modelliert werden, nicht als Ad-hoc-Chatentscheidung. NaC nutzt
GREEN/YELLOW/RED-Profile, damit Routine-Reads und lokale Validierung weiter
laufen können, während Owner-Gates für Merge, destruktive Aktionen, Secrets,
Credentials, Live-Tenant-Kanten und produktive Daten erhalten bleiben.

Maschinenlesbare Quelle:
[policies/codex-command-rules-policy.json](../../../policies/codex-command-rules-policy.json).

Codex-Rules-Artefakt:
[.codex/rules/default.rules](../../../.codex/rules/default.rules).

Kontext-Router:
[agent-context/index.json](../../../agent-context/index.json) führt diese
Command Rules als On-Demand-Guardrails. Runtime-Command-Ausgaben bleiben
task-lokale Evidence und sind keine gemeinsame Memory-Quelle.

## Profile

| Profil | Entscheidung | Beispiele |
| --- | --- | --- |
| GREEN | allow | `git status`, `git diff`, `gh pr checks`, lokale Validatoren, `rg` |
| YELLOW | prompt | `git push`, `gh pr create`, `gh pr merge`, Branch-Cleanup, owner-approved synthetische M365-Gates |
| RED | block | `git reset --hard`, `git checkout --`, `rm -rf`, Entra-Credential-Mutation, `terraform apply`, privilegierter produktiver Apply |

## Guardrails

- Rules ersetzen keine Owner-Freigabe für PR-Merges.
- Rules autorisieren keine Secrets, Zertifikatsrotation oder Entra-Credentials.
- Rules autorisieren keine produktiven SharePoint-/Teams-Writes außerhalb eines
  dedizierten owner-approved Commands.
- Rules aktivieren keine Hooks und verändern nicht `~/.codex/config.toml`.
- Rules erweitern weder Dateisystem- noch Netzwerkzugriff.

## Verification / Verifikation

```bash
python3 scripts/validate_codex_command_rules_operating_model.py
python3 -m unittest tests.test_codex_command_rules_operating_model
python3 scripts/quality_gate.py --profile strict
```
