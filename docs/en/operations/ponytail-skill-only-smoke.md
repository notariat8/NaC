# Ponytail Skill-Only Smoke

Status: prepared, not executed
Last content update: 2026-06-29

## Purpose

This runbook prepares a later Ponytail skill-only smoke on `notoclaw01`. It
does not install Ponytail, does not enable Codex lifecycle hooks and does not
start OpenClaw runtime activation.

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

## Before Owner Apply

Before actual execution, the Project Manager must obtain an owner apply gate.
The apply text must include at least:

- target host `notoclaw01-host`,
- target path `/home/ubuntu/nac-target-control`,
- Ponytail upstream and observed version,
- planned skill-only action,
- confirmation: no hooks, no runtime activation, no secrets, no matter data,
  no GitHub/OCI write.

## Evidence Template

The later smoke uses
[workflows/evidence-templates/ponytail-skill-only-smoke.md](../../../workflows/evidence-templates/ponytail-skill-only-smoke.md).
Filled evidence belongs on the target system under
`/home/ubuntu/nac-target-control/evidence/` and may contain only non-sensitive
metadata.

## Completion Criterion

The smoke is complete only when the evidence confirms:

- Ponytail remains `candidate_not_installed`,
- lifecycle hooks remain disabled,
- OpenClaw runtime activation remains blocked,
- all NaC governance, owner-gate and validator duties remain effective,
- no NaC repository change remains open from the smoke.
