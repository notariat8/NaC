# NemoClaw Operating Model

Status: binding coordination rule
Last content update: 2026-06-26

## Purpose

This operating model separates development, project coordination and
NemoClaw target operation for NaC. It prevents a target-system agent from
reporting local work as "finished" while the overall process still needs code,
review, release work or owner approval.

The technical NaC on-prem agent runtime boundary for `notoclaw01` is defined in
[docs/en/architecture/nac-onprem-agent-runtime.md](nac-onprem-agent-runtime.md)
and in the machine-readable contract
[workflows/contracts/nac-onprem-agent-runtime.contract.json](../../../workflows/contracts/nac-onprem-agent-runtime.contract.json).

## Roles And Work Locations

| Role | Work location | Responsibility | Must not |
| --- | --- | --- | --- |
| Project Manager | Main chat on `brev01` | Coordinate scope, architecture decisions, acceptance criteria, handoffs and owner questions. | Treat target smokes as overall completion. |
| Dev Agent | NaC workspace on `brev01` | Implement code, documentation, contracts, tests, PRs, CI and releases. | Modify production target systems through local hotfixes. |
| Target Operator | `notoclaw01-host` in `/home/ubuntu/nac-target-control` | Validate NemoClaw/OpenClaw target system, agent manifest, local runtime smokes, evidence and runbooks. | Develop NaC platform code, push, or create PRs by default. |
| Owner | Owner chat or explicit approval message | Approve architecture, release, apply, secret and operating decisions. | Replace explicit approvals with implied approvals. |

The Project Manager is the leading coordinator. Unless the owner names a
different thread, this role works in the main chat that coordinates the
cross-repository state, `brev01`, GitHub, OCI and `notoclaw01`. The Target
Operator thread on `notoclaw01-host` is an operational target-system run, not
project management.

## Access To The NaC Repository

`notoclaw01-host` may use a read-only mirror of the NaC repository when target
smokes, manifest checks or release comparisons need source context.

Binding boundaries:

- no push permission for `notoclaw01-host` by default,
- no GitHub write tokens on the target system,
- no PR creation by the Target Operator unless the owner explicitly approves it
  for a single case,
- no secrets, PINs, card material, matter data or private keys in
  `/home/ubuntu/nac-target-control`,
- target-system writes stay limited to `/home/ubuntu/nac-target-control` and
  NemoClaw/OpenClaw runtime paths.

If the read-only mirror needs authentication, the Target Operator stops and
reports the exact need. It must not read credentials from `/home/ubuntu/.codex`,
`/home/ubuntu/.nemoclaw` or any other runtime state.

## Path Boundaries On `notoclaw01-host`

| Path | Meaning |
| --- | --- |
| `/home/ubuntu/.codex` | Codex runtime and configuration; not used for NaC artifacts. |
| `/home/ubuntu/.nemoclaw` | NemoClaw state; no GitOps source artifacts. |
| `/sandbox/.openclaw/workspace-*` | OpenClaw agent workspaces; runtime-adjacent and not the NaC repo. |
| `/home/ubuntu/nac-target-control` | Target-control, runbooks, manifests, smokes and non-sensitive evidence. |

## Done Rules

### Target Operator

The Target Operator may report `finished` only for its target-system scope when:

- the concrete target-control request is implemented,
- the matching smoke or check is freshly green,
- the evidence contains no secrets and no matter data,
- no code, contract, policy, release or architecture change is needed in the
  NaC repository.

If a NaC repository change is needed, the status is not `finished`; it is
`handoff to Project Manager`.

### Dev Agent

The Dev Agent follows the completion rules from [AGENTS.md](../../../AGENTS.md),
[docs/en/START_HERE.md](../START_HERE.md) and
[docs/en/governance.md](../governance.md). A state is not complete while
validation, commit, push, delivery mode or mandatory remote checks are missing.

### Project Manager

The Project Manager may report coordination as `finished` only when a decision,
handoff or work assignment has been fully routed and the next owner need is
explicitly named or ruled out.

## Handoff Format

When `notoclaw01-host` hands work back to `brev01` or the Project Manager, it
uses this format:

```text
Handoff:
Scope:
Evidence:
Impact:
Required NaC repo change:
Validation already run:
Owner input needed:
```

If no owner input is needed, the value is `none`.

## Routing Rules

| Topic | Leading location |
| --- | --- |
| new architecture decision | Project Manager main chat |
| NaC code, contracts, tests, docs, policies | `brev01` / NaC repository |
| NemoClaw CLI, OpenClaw workspace, target-control smoke | `notoclaw01-host` |
| OCI, GitHub release, PR, CI | `brev01` with owner gate |
| secrets, apply, destructive actions | owner approval before execution |

## Stop Rules For The Target Operator

`notoclaw01-host` stops and returns a handoff when:

- a NaC code or policy fix is required,
- GitHub write access would be required,
- a secret, token, PIN, card material or matter data is required,
- a production apply, release or destructive step is next,
- the question is an architecture decision and not only target validation.

This keeps `notoclaw01-host` fast for target-system validation while overall
completion remains with the Project Manager and the NaC GitOps gates.
