# NaC Runtime Smoke

Status: prepared, owner-gated not executed
Last content update: 2026-06-30

## Purpose

This runbook describes the first NaC runtime smoke on `notoclaw01-host`. It only
checks whether the prepared NemoClaw/OpenClaw target-system boundary for NaC is
observable, without installing a sandbox, onboarding again, rebuilding, or
activating production connectors.

The binding sources remain the
[NaC on-prem agent runtime contract](../architecture/nac-onprem-agent-runtime.md),
the [NemoClaw operating model](../architecture/nemoclaw-operating-model.md), and
the official NemoClaw documentation for
[Quickstart](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/get-started/quickstart.md),
[Sandbox Lifecycle](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/manage-sandboxes/lifecycle.md),
[Runtime Controls](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/manage-sandboxes/runtime-controls.md),
[Monitoring](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/monitoring/monitor-sandbox-activity.md)
and
[Credential Storage](https://docs.nvidia.com/nemoclaw/latest/user-guide/openclaw/security/credential-storage.md).

## Allowed Scope

- check the target-control path `/home/ubuntu/nac-target-control`,
- run `bin/nac-target-smoke` and `bin/nac-runtime-smoke` read-only,
- record existing NemoClaw sandboxes with `nemoclaw list` or `nemoclaw status`
  as status information only,
- run `nemoclaw <name> status` for a named sandbox,
- document OpenClaw/NemoClaw status only as a summarized and redacted result,
- write evidence from
  [workflows/evidence-templates/nac-runtime-smoke.md](../../../workflows/evidence-templates/nac-runtime-smoke.md)
  under `/home/ubuntu/nac-target-control/evidence/`.

## Public Origin

Public origin is required configuration for production smokes. The runtime
smoke must not fall back to a hardcoded or randomly generated
`trycloudflare.com` address. The allowed sources are, in this order:

1. explicitly set `NAC_PUBLIC_ORIGIN`,
2. non-sensitive target-control configuration
   `/home/ubuntu/nac-target-control/config/public-origin`.

If the public origin is missing, `bin/nac-runtime-smoke` must fail closed with a
clear status such as `blocked_missing_public_origin`. For demos or temporary
tunnels, `NAC_PUBLIC_ORIGIN=... bin/nac-runtime-smoke --summary-only` remains
allowed; the random tunnel address does not become the production default.

## Blocked

- no installation and no `curl ... | bash` installer,
- no `nemoclaw onboard`, `--recreate-sandbox`, `rebuild`, `policy-add`,
  `recover`, `connect`, `openclaw tui`, `openclaw agent` or `nemoclaw debug`,
- no retrieval or storage of an authenticated dashboard link,
- no output of gateway tokens, provider names with confidential context,
  environment values, API keys, PINs, certificate material or matter data,
- no GitHub or OCI write access from the target system,
- no XNP, card, register, signature or specialist-system apply.

If no matching sandbox exists or `nemoclaw` is not available, the smoke ends as
`blocked_missing_runtime` or `blocked_missing_cli`. That is an allowed result
and must not be fixed through installation or onboarding in the same run.

## Owner Apply

Before every actual execution, the Project Manager must obtain an owner apply
gate. The approval text must include at least:

`Owner Apply Approval for NaC runtime smoke on notoclaw01-host using /home/ubuntu/nac-target-control, read-only NemoClaw/OpenClaw status only, no install, no onboard, no rebuild, no dashboard token capture, no secrets, no mandate data, no GitHub or OCI write`

This approval authorizes only the smoke. It does not authorize later runtime
activation, installation, onboarding or a production connection.

## Expected Flow

1. Check the contract state from the NaC repository.
2. Run `/home/ubuntu/nac-target-control/bin/nac-target-smoke`.
3. Confirm the public origin from `NAC_PUBLIC_ORIGIN` or
   `/home/ubuntu/nac-target-control/config/public-origin`.
4. Run `/home/ubuntu/nac-target-control/bin/nac-runtime-smoke --summary-only`.
5. If the runtime smoke names a sandbox, check only `nemoclaw <name> status`
   read-only.
6. Write evidence with result `passed`, `blocked_missing_runtime`,
   `blocked_missing_cli`, `blocked_missing_public_origin` or `blocked_policy`.
7. Hand off to the Project Manager if a NaC repository change, architecture
   decision, secret or owner gate is needed for the next step.

## Completion Criterion

The runtime smoke is complete only when the evidence confirms:

- owner apply was present,
- no installation, onboarding, rebuild or runtime mutation was performed,
- no authenticated dashboard link or gateway token was stored,
- no secrets, personal data or matter data were captured,
- no GitHub, OCI or specialist-system write action was performed,
- required follow-up work is named as a handoff.
