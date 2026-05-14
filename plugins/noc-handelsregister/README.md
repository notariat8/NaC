# NoC Handelsregister

Local HRA-first Handelsregister companion for preparing online register application packages, notary online-procedure readiness, eID/app prerequisites, approval checkpoints and metadata-only evidence. For notary-side filing workflows, start with `noc-bnotk-xnp` first. This plugin does not retrieve register data or automate protected portals.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata for online register application preparation. External submission adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Splits citizen preflight from notary-side workstation workflows.
- Requires the `noc-bnotk-xnp` gate before XNotar/register handoff work.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any notarial or submission action.
- Requires applicant approval, legal review and notarial review for online Handelsregister applications.

## Day0

- Confirm mode: citizen preflight or notary-side workstation workflow.
- For notary-side workflow, confirm `noc-bnotk-xnp` readiness first.
- Confirm legal form, register track and whether the case is HRA or HRB.
- Confirm applicant authority, notary route, Bundesnotarkammer app readiness and eID readiness.

## Day1

- Generate online application readiness plan, missing-information list and notary evidence checklist.

## Day2

- Review rejected applications, missing attachments, identity/signature failures and evidence completeness.

## Required Accounts And Approvals

- Notary appointment or notary office workflow
- Completed `noc-bnotk-xnp` readiness for notary-side workflows
- Bundesnotarkammer online procedure app
- eID-capable official ID and PIN
- Applicant and reviewer approval for the register application package

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
