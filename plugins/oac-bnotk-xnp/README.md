# OaC BNotK XNP

Local-only XNP gate for notarial workplace readiness, local authentication and Amtstaetigkeitskontext attestation, XNotar/register-package handoff readiness, API-key presence attestation and evidence flow while keeping XNP credentials out of SaaS and Git.

## Status

Installable MVP plugin scaffold. For notary-side Handelsregister or HRA workflows, this plugin comes before `oac-handelsregister`. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Treats local XNP login and Amtstaetigkeitskontext as the gate before register workflow automation.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm XNP installed on the same workstation/user context.
- Confirm local XNP login, user role and Amtstaetigkeitskontext are available without storing values.
- Confirm XNotar module or exchange-folder route for register workflows.
- Confirm notarial software vendor support and local admin ownership.

## Day1

- Create local authentication gate, XNotar handoff readiness plan and evidence shell without credential values.

## Day2

- Recertify local interface status after XNP or notarial software updates.

## Required Accounts And Approvals

- BNotK/XNP access for the notary office
- Local XNP login and active Amtstaetigkeitskontext
- XNotar/register module or exchange-folder route
- Notarial software vendor interface approval
- Local workstation admin approval

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
