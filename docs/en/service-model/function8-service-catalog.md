# Function8 Service Catalog For NaC

## Goal

This document lists all Function8 services in the `NaC` context transparently
and publicly traceably. Services that require a DPA must be marked as such and
linked to the required artifacts.

## Catalog Principle

- Every service has a stable `service_id`.
- Every service explicitly states whether a DPA is required.
- Every service is linked with policies, runbooks and exit path.
- No hidden operating dependencies outside this repository.

## Service Catalog

| service_id | service_name | service_type | dpa_required | data_scope | required_policies | runbook_references | portability_notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `f8-eventlock-saas` | EventLock-as-a-Service | `managed_saas` | yes | event journal and metadata | [policies/revisionssicherheit-eventstream-policy.yaml](../../../policies/revisionssicherheit-eventstream-policy.yaml), [policies/tenant-ownership-policy.yaml](../../../policies/tenant-ownership-policy.yaml), [policies/provider-open-services-policy.yaml](../../../policies/provider-open-services-policy.yaml) | [docs/en/eventstream/revisionssicherheit.md](../eventstream/revisionssicherheit.md), [docs/en/eventstream/implementation-templates.md](../eventstream/implementation-templates.md), [docs/en/eventstream/runbook-aws.md](../eventstream/runbook-aws.md), [docs/en/eventstream/runbook-azure.md](../eventstream/runbook-azure.md), [docs/en/eventstream/runbook-gcp.md](../eventstream/runbook-gcp.md), [docs/en/eventstream/runbook-oci.md](../eventstream/runbook-oci.md) | dedicated subinstance per customer, documented exit |
| `f8-nac-governance-pack` | Governance and Policy Pack | `documentation_and_controls` | no | governance metadata | [policies/process-policy.yaml](../../../policies/process-policy.yaml), [policies/role-model-policy.yaml](../../../policies/role-model-policy.yaml), [policies/access-control-policy.yaml](../../../policies/access-control-policy.yaml) | [docs/en/governance.md](../governance.md), [docs/en/issues/operations.md](../issues/operations.md) | fully repository-based, transferable to third parties |
| `f8-onboarding-pack` | Onboarding and introduction materials | `documentation` | no | onboarding metadata | [policies/onboarding-flow.json](../../../policies/onboarding-flow.json), [policies/provider-open-services-policy.yaml](../../../policies/provider-open-services-policy.yaml) | [docs/en/START_HERE.md](../START_HERE.md), [docs/en/vscode-copilot-start.md](../vscode-copilot-start.md), [docs/en/platform-onboarding-matrix.md](../platform-onboarding-matrix.md) | openly documented, no proprietary lock-in |

## DPA Reference

For services with `dpa_required = yes`:

- [docs/en/avv-checkliste-eventlock-saas.md](../avv-checkliste-eventlock-saas.md)
  is mandatory.
- Subprocessors, regions, retention and incident notification paths must be
  documented.

## Maintenance Process

1. Add new service only by PR.
2. Assign unique `service_id`.
3. Explain DPA relevance.
4. Complete runbook and policy references.
5. Document exit and replaceability note.
