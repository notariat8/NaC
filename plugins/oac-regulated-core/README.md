# OaC Regulated Core

Shared local workflow, safety boundary, plan-preview, approval and evidence guidance for OaC plugins used by law firms, notaries and adjacent regulated operations.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm matter type, actor role, reviewer role and data boundary.
- Confirm local workspace and Git remote are clean.

## Day1

- Produce plan preview and evidence template before any external action.

## Day2

- Review drift, expired approvals, failed controls and account recertification.

## Required Accounts And Approvals

- GitHub repository write access
- Approved reviewer roster
- Evidence storage decision

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
