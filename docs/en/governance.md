# Governance With Git And GitHub

## Repository Rules

Recommended target state for `main`:

- prohibit direct pushes to `main`,
- require pull requests,
- require status checks from `Validate Business Processes`,
- require review by at least one subject-matter owner,
- use signed tags for closures such as `close/2026-03`.

Recommendation for organization forks:

- mark technical process releases as `v*`,
- take upstream changes only through documented sync PRs,
- keep running matters on their start version through version binding.

## Environment Mapping

- `business-operations`: sensitive manual execution of individual processes.
- `month-close`: monthly close and periodic aggregation.
- optional `tax-submission`: final approval stage before external tax filing.

## Subject-Matter Mapping

| Git/GitHub mechanism | Subject-matter meaning |
| --- | --- |
| Branch | business matter in progress |
| Pull request | formal request requiring approval |
| Review | subject-matter approval |
| Action run | documented machine execution |
| Artifact | exported evidence or report |
| Tag | closure state |
| Release | published, versioned evidence |

## Practical Rules Per Domain

### Formation

- Steps can be handled in one grouped matter or as separate process files.
- Status `needs_review` should be coupled to manual review.

### Invoicing

- `draft -> approved` only through pull request.
- `approved -> issued` only in a protected runtime or after documented approval.
- RVG-related invoices only with documented qualification and approval.

### Bookkeeping

- Accounting entries must be balanced.
- Idempotency keys and receipt references prevent duplicate bookings.

### Tax

- `prepared -> approved` always with four-eyes principle.
- `submitted` should be set only after manual approval and possible external
  filing.

## Role-Based Decision Logic

- Every role may open tickets.
- `low impact` without compliance effect can be self-resolved.
- `medium/high impact` or legal effect requires review or approval.
- Qualification duties take priority over general role rights.

Reference: [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Further Operating Standards

- Fork model and responsibilities:
  [docs/en/operations/fork-and-release-operating-model.md](operations/fork-and-release-operating-model.md)
- Sync cycle and PR gates:
  [docs/en/operations/release-sync-playbook.md](operations/release-sync-playbook.md)
- Mixed operation and audit evidence:
  [docs/en/operations/parallelbetrieb-version-binding.md](operations/parallelbetrieb-version-binding.md)
- Cross-repository issue handling:
  [docs/en/issues/taxonomy.md](issues/taxonomy.md)
- Roles, access and central task overview:
  [docs/en/issues/operations.md](issues/operations.md)
- Audit-proof event journal:
  [docs/en/eventstream/revisionssicherheit.md](eventstream/revisionssicherheit.md)
- Concrete platform templates:
  [docs/en/eventstream/implementation-templates.md](eventstream/implementation-templates.md)
- Azure runbook:
  [docs/en/eventstream/runbook-azure.md](eventstream/runbook-azure.md)
- AWS runbook:
  [docs/en/eventstream/runbook-aws.md](eventstream/runbook-aws.md)
- GCP runbook:
  [docs/en/eventstream/runbook-gcp.md](eventstream/runbook-gcp.md)
- OCI runbook:
  [docs/en/eventstream/runbook-oci.md](eventstream/runbook-oci.md)
- Tenant-owner and service model:
  [docs/en/service-model/tenant-ownership-and-eventlock-service.md](service-model/tenant-ownership-and-eventlock-service.md)
- Function8 service catalog:
  [docs/en/service-model/function8-service-catalog.md](service-model/function8-service-catalog.md)
- Third-party operation and exit without lock-in:
  [docs/en/service-model/third-party-operations-and-exit.md](service-model/third-party-operations-and-exit.md)
