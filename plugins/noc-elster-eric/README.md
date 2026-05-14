# NoC ELSTER ERiC

Local ELSTER/ERiC workflow companion for filing readiness, local credential boundary, evidence import and manufacturer/onboarding checks without central tax credential storage.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm tax actor authorization and local ELSTER credential boundary.
- Decide whether ERiC manufacturer onboarding is in scope.

## Day1

- Create dry-run filing plan and human approval checkpoint.

## Day2

- Track ERiC version, certificates, deadlines, failed transfers and proof retention.

## Required Accounts And Approvals

- ELSTER organization or user access
- Local certificate or approved auth method
- ERiC manufacturer registration if server-side integration is pursued
- Tax representation approval

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
