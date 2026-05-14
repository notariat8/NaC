# NoC BNotK XNP

Installable local Codex plugin for notaries and notary-office workstations. It gates Online HRA and other notary-side register workflows after `noc-cyberjack-rfid` has confirmed the local card-reader, BNotK SAK lite or XNP-card-path and secureFramework prerequisites. It can create a local XNP reader-prompt preflight for the cyberJack RFID reader, then checks local XNP readiness, local authentication and Amtstaetigkeitskontext attestation, XNotar/register-package handoff readiness, API-key presence attestation and evidence flow while keeping XNP credentials out of SaaS and Git.

## Status

Runnable local MVP. For notary-side Handelsregister or HRA workflows, this plugin comes after `noc-cyberjack-rfid` and before `noc-handelsregister` in the repo-local Codex marketplace. External write adapters are intentionally not enabled in this first version.

## Runnable Reader Prompt MVP

Run the local XNP reader-prompt preflight from the repository root:

```powershell
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --json
```

For an operator-attested workstation check:

```powershell
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --manual-card-present yes --manual-rfid-off yes --output out\xnp-reader-prompt.json
```

This does not perform an XNP login and does not call a productive XNP write endpoint. It creates a local dry-run prompt for the approved cyberJack reader route, invokes the `noc-cyberjack-rfid` readiness check, probes only XNP localhost ports `12774` to `12784`, and writes evidence according to `contracts/reader-prompt-evidence.schema.json`.

To include the active morris browser-middleware and PC/SC list-readers probe from the cyberJack gate, add:

```powershell
python plugins\noc-bnotk-xnp\scripts\reader_prompt.py --json --probe-morris-api
```

The prompt is for checking local reader response, not for activating contactless RFID in a BNotK chip-card workflow. Do not enter PINs, card values, certificates, passwords or XNP API keys into Codex.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Is installable from `.agents/plugins/marketplace.json` for the Notary/XNP gate use case.
- Requires completed `noc-cyberjack-rfid` card/SAK readiness before XNP login testing.
- Creates a local dry-run reader prompt through `scripts/reader_prompt.py` to verify the cyberJack reader path before XNP login testing.
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

- Create local reader-prompt evidence, authentication gate, XNotar handoff readiness plan and evidence shell without credential values.

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
