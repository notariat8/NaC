# OaC OCI Evidence

OCI evidence companion for landing-zone Day0 checks, Resource Manager plan review, eventstream/audit journal design, Vault boundary and Day2 drift/cost controls.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm tenancy, compartment, region, local OCI CLI profile and least-privilege policy.

## Day1

- Create plan preview and evidence wiring before any apply.

## Day2

- Run drift, cost, audit, rotation and break-glass reviews.

## Required Accounts And Approvals

- OCI tenancy access
- Compartment admin or delegated policy
- Vault/key-management approval
- Budget owner
- Audit retention owner

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
