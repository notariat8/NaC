# Governance With Git And GitHub

## Repository Rules And Delivery Modes

Recommended target state for production forks and sensitive process changes:

- prohibit direct pushes to `main`,
- require pull requests,
- require status checks from `Validate NaC Runtime Fixtures` and `NaC Quality Gate`,
- require review by at least one subject-matter owner,
- use signed tags for closures such as `close/2026-03`.

In the active reference repo, the owner can explicitly request direct delivery
to `main`. In that mode, a state is finished only after the strict quality gate
passes, `main` is pushed to GitHub, `HEAD` equals the GitHub target state and
the working tree is clean. This owner-direct mode does not replace protected PR
mode for production forks, sensitive subject-matter changes or external
contribution.

Recommendation for organization forks:

- mark technical process releases as `v*`,
- take upstream changes only through documented sync PRs,
- keep running matters on their start version through version binding.

## Agentic Change Discipline

Non-trivial agentic work is not negotiated directly in code. Scope, risk,
acceptance criteria and the relevant layers are clarified in a plan first. A
review then checks the plan before implementation starts.

After implementation, code review checks at least:

- whether the change follows the plan and existing repository patterns,
- whether the data, controller/logic and view layers remain consistent,
- whether error cases, tests and security concerns are covered adequately,
- whether no unnecessary new technology, duplicate structure or over-complexity
  has been introduced.

Before a merge, including owner-approved merges, the complete PR diff against
the target branch is checked. The relevant evidence is not just the last
commit, but `base...head` with file and commit list. If a PR branch starts from
another feature branch instead of the target branch, the merge is stopped, the
PR is recut, or the combined scope is documented explicitly.

For persistent or unclear failures, diagnosis comes before fixing. In that
situation, an agent must not keep trying changes until the cause is named and
the smallest sensible fix path is described.

Governance deviation on 2026-06-15: PR #139 was accepted even though the
observability branch had accidentally been based on the Q2D branch and
therefore brought Q2D into `main` together with the time ledger. PR #138 was
closed as superseded. The durable correction is the mandatory full-PR-diff
check before every merge.

## Environment Mapping

- `nac-operations`: sensitive manual execution of individual NaC process fixtures.
- `month-close`: monthly close and periodic aggregation.
- optional notary-office environments for approved specialist-system or register gates.

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

### Notarial Formation Matters

- Steps can be handled in one grouped matter or as separate process files.
- Status `needs_review` should be coupled to manual review.

### Notarial Cost Notes

- `draft -> approved` only through pull request.
- `approved -> issued` only in a protected runtime or after documented approval.
- notarial cost reviews only with documented qualification and approval.

### Bookkeeping

- Accounting entries must be balanced.
- Idempotency keys and receipt references prevent duplicate bookings.

### Notarial Notices With Tax Relation

- `prepared -> approved` always with four-eyes principle.
- `submitted` should be set only after manual approval and possible external
  notice submission.

## Role-Based Decision Logic

- Every role may open tickets.
- `low impact` without compliance effect can be self-resolved.
- `medium/high impact` or legal effect requires review or approval.
- Qualification duties take priority over general role rights.

Reference: [policies/role-model-policy.yaml](../../policies/role-model-policy.yaml)

## Further Operating Standards

- NemoClaw target operation and agent work split:
  [docs/en/architecture/nemoclaw-operating-model.md](architecture/nemoclaw-operating-model.md)
- NaC on-prem agent runtime on `notoclaw01`:
  [docs/en/architecture/nac-onprem-agent-runtime.md](architecture/nac-onprem-agent-runtime.md)
- Notarial on-prem connector boundaries:
  [docs/en/architecture/notarial-onprem-connector-boundaries.md](architecture/notarial-onprem-connector-boundaries.md)
- Matter-data classification and redaction boundary:
  [docs/en/architecture/matter-data-classification-redaction.md](architecture/matter-data-classification-redaction.md)
- Private operating frame and private-payload gate:
  [docs/en/architecture/private-operating-frame-gate.md](architecture/private-operating-frame-gate.md)
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
