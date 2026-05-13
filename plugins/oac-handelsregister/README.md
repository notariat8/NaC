# OaC Handelsregister

Local HRA-first Handelsregister companion for preparing online register application packages, notary online-procedure readiness, eID/app prerequisites, approval checkpoints and metadata-only evidence. This plugin does not retrieve register data or automate protected portals.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata for online register application preparation. External submission adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any notarial or submission action.
- Requires applicant approval, legal review and notarial review for online Handelsregister applications.

## Day0

- Confirm legal form, register track and whether the case is HRA or HRB.
- Confirm applicant authority, notary route, Bundesnotarkammer app readiness and eID readiness.

## Day1

- Generate online application readiness plan, missing-information list and notary evidence checklist.

## Day2

- Review rejected applications, missing attachments, identity/signature failures and evidence completeness.

## Required Accounts And Approvals

- Notary appointment or notary office workflow
- Bundesnotarkammer online procedure app
- eID-capable official ID and PIN
- Applicant and reviewer approval for the register application package

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
