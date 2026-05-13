# OaC Regulated Industry Plugins

This directory contains installable repo-local Codex plugins for OaC regulated-industry workflows. The first suite focuses on lawyers, notaries, tax workflows and cloud evidence operations.

## Installable Plugins

- `oac-regulated-core`: Shared regulated-industry workflow guardrails.
- `oac-handelsregister`: HRA-first online register application readiness.
- `oac-bnotk-xnp`: Local XNP companion for notarial workflows.
- `oac-bea-portal`: beA workflow and evidence companion.
- `oac-elster-eric`: ELSTER and ERiC workflow companion.
- `oac-cyberjack-rfid`: Local card-reader readiness companion.
- `oac-grundbuch-portal`: Land register access and evidence companion.
- `oac-oci-evidence`: OCI landing-zone evidence and audit companion.

## Safety Model

- Plugins default to local companion, dry-run, plan-preview and metadata-only evidence.
- External write adapters are not enabled in this MVP.
- Missing accounts or approvals are tracked in `docs/plugin-operations/account-and-approval-requests.md`.
- Validate with `python3 scripts/validate_plugins.py` before publishing or installing.
