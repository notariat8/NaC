# NoC: Notariat as Code

This repository is maintained as a multilingual `Notariat as Code` reference.
Language-specific documentation and prompts use ISO-639 folder codes.

## Languages

- German: `docs/de/`, `prompts/de/`
- English: `docs/en/`, `prompts/en/`

`de` and `en` are mandatory standard languages. Any change to localized content
must update both languages, regardless of the language used in the prompt.

The binding rule is defined in `policies/language-policy.yaml` and checked by
`scripts/validate_language_parity.py`.

## Start

- German start path: `docs/de/START_HERE.md`
- English start path: `docs/en/START_HERE.md`
- German README: `docs/de/README.md`
- English README: `docs/en/README.md`
- AVV/DPA section: `docs/de/datenschutz-avv-dpa.md`, `docs/en/datenschutz-avv-dpa.md`
- Plugin plans: `docs/de/plugin-plans/README.md`, `docs/en/plugin-plans/README.md`
- Global roadmap: `roadmap/GANTT.md`
- Plugin roadmap: `plugins/GANTT.md`
- Workflow roadmap: `workflows/GANTT.md`
- Usecase roadmap: `usecases/GANTT.md`

## Product Structure

This repository now separates three product layers:

- `plugins/`: installable plugin artifacts for public GPT Store checks or
  workspace/internal app installation.
- `workflows/`: reusable notary-office workflows, split into installable skills
  and deterministic Python execution.
- `usecases/`: concrete notarial scenarios such as online GmbH formation,
  AO52 nonprofit software-company formation, real-estate purchase contracts,
  and testaments.

Every push must update `roadmap/GANTT.md`. Changes below `plugins/`,
`workflows/`, or `usecases/` must also update the matching area Gantt.

OpenAI publication channels must be checked before release. Public GPT Store
packages and workspace-only apps are not the same delivery target, especially
when apps or actions are involved.

## Current Workflow Priorities

The online HRA path is a notarial gate chain. XNP should only be tested after
the local card path is ready.

| Priority | Workflow | Blocks | Visible outcome |
| --- | --- | --- | --- |
| P0 | `noc-cyberjack-rfid` Card/SAK Gate | XNP login test | Card, reader, PC/SC, SAK lite/XNP card path, and secureFramework are readiness-checked locally |
| P0 | `noc-bnotk-xnp` XNP Gate | HRA/XNotar workflow | XNP, local login, official context, XNotar module, and exchange folder are readiness-checked |
| P0 | `noc-handelsregister` Online HRA Layer | production-near HRA package | HRA/HRB path, mandatory data, notary route, approvals, and evidence metadata are prepared |
| P1 | Installability and validation | pilot operation | Codex marketplace order, plugin manifests, and validator are stable |
| P2 | Follow-up adapters beA, land register, ELSTER | cross-domain expansion | deferred until Card/SAK, XNP, and HRA gates are stable |

## Quick Check

```bash
python scripts/quality_gate.py --profile strict
```

The strict quality gate validates process files, tests, privacy rules,
governance sync, language parity, cloud runbook parity, and plugin manifests.
