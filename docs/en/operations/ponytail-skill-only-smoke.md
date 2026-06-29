# Ponytail Skill-Only Smoke

Status: executed, passed
Last content update: 2026-06-29

## Purpose

This runbook describes the owner-gated Ponytail skill-only smoke on
`notoclaw01`. The smoke was executed and passed on 2026-06-29. It does not
install Ponytail, does not enable Codex lifecycle hooks and does not start
OpenClaw runtime activation.

The smoke may only check whether Ponytail fits the NaC target-control boundary
as an optional skill candidate. The binding sources remain the
[NaC on-prem agent runtime contract](../architecture/nac-onprem-agent-runtime.md)
and the AI-SBOM boundary in [sbom-for-ai.md](../sbom-for-ai.md).

## Allowed Scope

- check public Ponytail metadata against the values recorded in the NaC repo,
- document target-system paths for a later skill-only test,
- prepare a non-sensitive evidence document from the template,
- confirm that no matter data, secrets, hooks or runtime activation are used.

## Blocked

- no Codex plugin installation,
- no Codex or Claude lifecycle hooks,
- no OpenClaw runtime activation,
- no GitHub or OCI write access from the target system,
- no real matter data, personal data, PINs, tokens, keys or certificate
  material,
- no shortening of security, privacy, owner-gate, test or validator duties.

## Owner Apply

Before every actual execution, the Project Manager must obtain an owner apply
gate. The execution on 2026-06-29 used this gate:

`Owner Apply Approval for Ponytail skill-only smoke on notoclaw01-host using /home/ubuntu/nac-target-control, no install, no lifecycle hooks, no OpenClaw runtime activation, no secrets, no mandate data, no GitHub or OCI write`

Future apply texts must include at least:

- target host `notoclaw01-host`,
- target path `/home/ubuntu/nac-target-control`,
- Ponytail upstream and observed version,
- planned skill-only action,
- confirmation: no hooks, no runtime activation, no secrets, no matter data,
  no GitHub/OCI write.

## Evidence Template

The smoke uses
[workflows/evidence-templates/ponytail-skill-only-smoke.md](../../../workflows/evidence-templates/ponytail-skill-only-smoke.md).
Filled evidence lives on the target system under
`/home/ubuntu/nac-target-control/evidence/` and may contain only non-sensitive
metadata.

## Execution Evidence 2026-06-29

- Target host: `notoclaw01-host`
- Evidence: `/home/ubuntu/nac-target-control/evidence/ponytail-skill-only-smoke-2026-06-29.md`
- Result: `passed`
- Public upstream version: `v4.8.4`
- Installation performed: no
- Lifecycle hooks enabled: no
- OpenClaw runtime activation performed: no
- GitHub or OCI write from target system: no
- NaC repository change required: no
- Owner input required: no

## Completion Criterion

The smoke is complete because the evidence confirms:

- Ponytail remains `candidate_not_installed`,
- lifecycle hooks remain disabled,
- OpenClaw runtime activation remains blocked,
- all NaC governance, owner-gate and validator duties remain effective,
- no NaC repository change remains open from the smoke.
