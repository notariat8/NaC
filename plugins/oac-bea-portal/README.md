# OaC beA Portal

Local beA workflow companion for readiness, mailbox/eEB task planning, Client Security checks and evidence capture without storing PINs, card data, mailbox secrets or mandate content in Git.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm mailbox owner, user role, card/token readiness and Client Security availability.

## Day1

- Create human-approved send/receive/eEB plan and evidence checklist.

## Day2

- Track Client Security versions, failed sends, eEB deadlines and export integrity.

## Required Accounts And Approvals

- beA mailbox access
- beA card or approved authentication method
- beA Client Security on local workstation
- Firm policy for eEB and exports

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
