# NoC Regulated Industry Plugins

This directory contains installable repo-local Codex plugins for NoC regulated-industry workflows. The first suite focuses on lawyers, notaries, tax workflows and cloud evidence operations.

## Installable Plugins

- `noc-regulated-core`: Shared regulated-industry workflow guardrails.
- `noc-idaas`: German eID verification and IAM projection readiness companion.
- `noc-cyberjack-rfid`: Local card and SAK-lite gate before XNP login.
- `noc-bnotk-xnp`: Local XNP authentication gate after card readiness.
- `noc-pkcs7-certbundle`: Local PKCS#7/P7B certificate-bundle evidence without signing.
- `noc-handelsregister`: HRA-first online register application readiness after mode decision.
- `noc-bea-portal`: beA workflow and evidence companion.
- `noc-elster-eric`: ELSTER and ERiC workflow companion.
- `noc-grundbuch-portal`: Land register access and evidence companion.
- `noc-oci-evidence`: OCI landing-zone evidence and audit companion.

## Safety Model

- Plugins default to local companion, dry-run, plan-preview and metadata-only evidence.
- External write adapters are not enabled in this MVP.
- Missing accounts or approvals are tracked in `docs/de/plugin-operations/account-and-approval-requests.md` and `docs/en/plugin-operations/account-and-approval-requests.md`.
- Validate with `python3 scripts/validate_plugins.py` before publishing or installing.

## Progress Tracking

Plugin progress is tracked in `plugins/GANTT.md` and rolled up into
`roadmap/GANTT.md`. Every plugin change must update both files before it is
push-ready.

## Marketplace Boundary

Public GPT Store packages and workspace-only app installations are separate
release targets. Each plugin must be checked against the current OpenAI
publishing rules before public release, and actions must retain valid privacy
and terms URLs.
