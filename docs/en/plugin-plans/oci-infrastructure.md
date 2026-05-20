# Plugin Plan: OCI Infrastructure

Status: `proposed`

## Goal

OCI is connected locally from WSL and can serve NaC as infrastructure and
evidence platform:

- OCI CLI for local administration,
- Resource Manager for Terraform/OpenTofu stacks,
- OCI Streaming and Object Storage for audit-proof eventstreams,
- Vault for signatures and key references.

## Day 0

- Install OCI CLI locally.
- Create local API key, upload public key to OCI, keep private key local.
- Maintain `~/.oci/config` locally.
- Check access:

```bash
oci iam region list
oci iam region-subscription list --tenancy-id <tenancy_ocid>
```

- Do not commit OCI keys or configs to the repository.

## Day 1

- Create Resource Manager stack for first IaC configuration.
- Concretize the OCI eventstream runbook:
  [docs/en/eventstream/runbook-oci.md](../eventstream/runbook-oci.md)
- Create minimum plan for:
  - compartment structure,
  - IAM policies for operator, audit reader and break glass,
  - Object Storage bucket for evidence,
  - Streaming stream for event journal,
  - Vault key for daily anchors.
- Apply Terraform/OpenTofu code only after plan review.

## Day 2

- Rotate API keys.
- Use Resource Manager drift detection or refresh-only plan.
- Document cost and quota limits.
- Check retention, legal hold and evidence read path.
- Reconcile manual OCI console interventions in Git.

## Connector Boundaries

The OCI connector may:

- read OCI metadata,
- trigger Resource Manager plans,
- document evidence and drift status,
- apply approved stacks.

The OCI connector must not:

- write private keys to the repository,
- manually modify Resource Manager state,
- change retention or legal-hold rules without review,
- reuse Omnistation keys or remote keys.

## Acceptance Criteria

- OCI CLI works locally in WSL.
- Private keys remain local.
- Resource Manager or remote state is decided before team use.
- Eventstream and evidence components are linked with runbooks.
