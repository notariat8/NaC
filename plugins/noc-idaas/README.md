# NoC IDaaS

Source repository checked on 2026-05-14: `ofunk/IDaaS`

This plugin canonicalizes the former IDaaS repository into the NoC plugin layer.
It is a local regulated companion for German eID verification readiness and IAM
projection planning.

## Scope

- German eID readiness through AusweisApp-oriented flows
- verified-claim minimization
- consent and purpose-binding evidence
- IAM projection planning for Entra ID, Oracle IAM, and SCIM targets
- dry-run API and event contract review

## Boundary

This plugin does not perform production eID transactions, store identity
documents, write to IAM systems, or submit data to external services by
default. Any production connector must be separately reviewed, approved, and
bound to a data-processing agreement where personal data is involved.

## Migrated Source

The source repository contained:

- product and architecture documentation
- OpenAPI verification contract sketch
- assertion-issued event schema
- service placeholder folders for verification orchestration and IAM projection

The canonical NoC plugin material now lives here:

- `.codex-plugin/plugin.json`
- `skills/noc-idaas/SKILL.md`
- `contracts/security-boundary.json`
- `contracts/verification-api.yaml`
- `contracts/assertion-issued.schema.json`
- `docs/source-summary.md`

## Release Channel

This plugin is not automatically public-GPT-Store-ready. It must first be
classified as public GPT Store, GPT with Actions, workspace app, or local Codex
plugin according to `docs/de/gpt-marketplace-operating-model.md` and
`docs/en/gpt-marketplace-operating-model.md`.
