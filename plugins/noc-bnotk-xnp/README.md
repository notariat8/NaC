# NoC BNotK XNP

Installable local Codex plugin for notaries and notary-office workstations. It gates Online HRA and other notary-side register workflows after `noc-cyberjack-rfid` has confirmed the local card-reader, BNotK SAK lite or XNP-card-path and secureFramework prerequisites. It then checks local XNP readiness, local authentication and Amtstaetigkeitskontext attestation, XNotar/register-package handoff readiness, API-key presence attestation and evidence flow while keeping XNP credentials out of SaaS and Git.

## Status

Installable MVP plugin scaffold. For notary-side Handelsregister or HRA workflows, this plugin comes after `noc-cyberjack-rfid` and before `noc-handelsregister` in the repo-local Codex marketplace. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Is installable from `.agents/plugins/marketplace.json` for the Notary/XNP gate use case.
- Requires completed `noc-cyberjack-rfid` card/SAK readiness before XNP login testing.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Treats local XNP login and Amtstaetigkeitskontext as the gate before register workflow automation.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm XNP installed on the same workstation/user context.
- Confirm `noc-cyberjack-rfid` readiness for card, security-class-3 reader, SAK lite/XNP card path and secureFramework.
- Confirm local XNP login, user role and Amtstaetigkeitskontext are available without storing values.
- Confirm XNotar module or exchange-folder route for register workflows.
- Confirm notarial software vendor support and local admin ownership.

## Day1

- Create local authentication gate, XNotar handoff readiness plan and evidence shell without credential values.

## Day2

- Recertify local interface status after XNP or notarial software updates.

## Required Accounts And Approvals

- BNotK/XNP access for the notary office
- Completed `noc-cyberjack-rfid` card/SAK readiness
- Local XNP login and active Amtstaetigkeitskontext
- XNotar/register module or exchange-folder route
- Notarial software vendor interface approval
- Local workstation admin approval

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
