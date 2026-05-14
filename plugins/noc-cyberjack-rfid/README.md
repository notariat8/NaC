# NoC Card SAK Gate

Installable local Codex plugin for notary card-readiness before XNP login and Online HRA work. It checks BNotK chip/signature card or local Schneider/SCP-card availability where deployed, security-class-3 reader readiness, PC/SC state, BNotK SAK lite or XNP card path, secureFramework readiness and evidence metadata without PIN capture or card data extraction.

## Status

Installable MVP plugin scaffold. For notary-side Online HRA, this plugin comes before `noc-bnotk-xnp`, because XNP login cannot be tested until the local card path is ready. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Is installable from `.agents/plugins/marketplace.json` before `noc-bnotk-xnp`.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Treats BNotK chip/signature card or local Schneider/SCP-card availability, class-3 reader, SAK lite/XNP and secureFramework as the gate before XNP login tests.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm BNotK chip/signature card or local Schneider/SCP-card availability without reading card values.
- Confirm security-class-3 reader model, driver source, PC/SC service and local admin path.
- Confirm BNotK SAK lite or XNP card path and secureFramework readiness.

## Day1

- Run card-reader, SAK-lite/XNP-card-path and secureFramework readiness checklist before XNP login testing.

## Day2

- Recertify card-reader, driver, firmware, PC/SC service, SAK-lite/XNP-card-path and secureFramework readiness.

## Required Accounts And Approvals

- Approved hardware procurement
- BNotK chip/signature card or local Schneider/SCP-card availability
- Security-class-3 card reader
- BNotK SAK lite or XNP card path
- secureFramework communication path
- Local workstation admin approval
- Driver/vendor support channel

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
