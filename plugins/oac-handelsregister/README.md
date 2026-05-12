# OaC Handelsregister

Local Handelsregister research companion for dry-run search planning, source tracking, rate-limit discipline and evidence capture without adopting unreviewed third-party code as production dependency.

## Status

Installable MVP plugin scaffold. The plugin provides local Codex skill guidance, a machine-readable security contract and marketplace metadata. External write adapters are intentionally not enabled in this first version.

## Install Boundary

- Runs as a local Codex plugin from this repository.
- Keeps secrets, PINs, certificates, portal sessions and mandate content outside Git.
- Produces plan previews and evidence metadata before any sensitive action.
- Requires human approval for regulated submissions, portal actions, notarial actions and cloud applies.

## Day0

- Confirm lawful research purpose and source terms.
- Confirm whether Registerportal or another approved source is used.

## Day1

- Generate dry-run search plan and manual evidence checklist.

## Day2

- Review source terms, rate limits, retrieval logs and rejected searches.

## Required Accounts And Approvals

- Registerportal user access if required
- License review for any third-party client
- Rate-limit owner approval

See `docs/plugin-operations/account-and-approval-requests.md` for the consolidated request list.
