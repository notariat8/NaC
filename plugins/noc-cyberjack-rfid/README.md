# NoC Card SAK Gate

Installable local Codex plugin for notary card-readiness before XNP login and Online HRA work. It checks BNotK chip/signature card availability, REINER SCT cyberJack reader readiness, security-class-3 reader requirements, PC/SC state, BNotK SAK lite or XNP card path, secureFramework readiness, XNP local-interface prerequisites and evidence metadata without PIN capture or card data extraction.

## Status

Installable MVP plugin scaffold. For notary-side Online HRA, this plugin comes before `noc-bnotk-xnp`, because XNP login cannot be tested until the local card path is ready. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Is installable from `.agents/plugins/marketplace.json` before `noc-bnotk-xnp`.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Treats BNotK chip/signature card availability, compatible class-3 reader, SAK lite/XNP, secureFramework and XNP local-interface readiness as the gate before XNP login tests.
- Treats RFID as a reader capability, not as the notarial card workflow. Where the reader has an RFID function, the BNotK guidance is to keep it disabled for chip-card workflows unless a specific contactless use is explicitly needed.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm BNotK chip/signature card availability without reading card values.
- Confirm security-class-3 reader model, driver source, PC/SC service and local admin path.
- Confirm whether the reader has an RFID function and whether it is disabled for the BNotK chip-card workflow.
- Confirm BNotK SAK lite or XNP card path and secureFramework readiness.
- Confirm XNP local web-service interface readiness only as metadata: active/inactive, localhost-only binding, configured port range and whether API-key setup is required. Do not store the API key.

## Day1

- Run card-reader, RFID-off, SAK-lite/XNP-card-path, secureFramework and XNP local-interface readiness checklist before XNP login testing.

## Day2

- Recertify card-reader, driver, firmware, PC/SC service, SAK-lite/XNP-card-path and secureFramework readiness.

## Required Accounts And Approvals

- Approved hardware procurement
- BNotK chip/signature card availability
- Security-class-3 card reader
- RFID function disabled where present and not explicitly needed
- BNotK SAK lite or XNP card path
- secureFramework communication path
- XNP local interface configuration reviewed without storing API keys
- Local workstation admin approval
- Driver/vendor support channel

See `docs/de/plugin-operations/account-and-approval-requests.md` and `docs/en/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
